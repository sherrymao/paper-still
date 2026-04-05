"""Fetch papers from arXiv + enrich with OpenAlex citations.

Usage:
    # Fetch for a specific direction (uses config/search.yaml defaults)
    python -m scripts.fetch --direction post_training

    # Custom query override
    python -m scripts.fetch --direction post_training --query "direct preference optimization"

    # Adjust time window and result count
    python -m scripts.fetch --direction world_models --days 60 --limit 50

    # Fetch all directions
    python -m scripts.fetch --all
"""

from __future__ import annotations

import argparse
import re
import ssl
import time
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

import arxiv
import requests
import urllib3
import yaml

from scripts.loader import load_all_papers, load_config
from scripts.models import VALID_DIRECTIONS
from scripts.utils import OUTPUT_DIR, CONFIG_DIR

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CANDIDATES_DIR = OUTPUT_DIR / "candidates"


def _auto_importance(citations: int, affiliations: list, notable_affiliations: list) -> str:
    """Heuristic importance based on citations and affiliations."""
    notable_set = set(a.lower() for a in notable_affiliations)
    has_notable = any(a.lower() in notable_set for a in affiliations)
    if citations >= 50 or has_notable:
        return 'high'
    if citations == 0 and not has_notable:
        return 'low'
    return 'medium'


def load_search_config() -> dict:
    return load_config("search.yaml")


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract clean arXiv ID from entry_id URL. e.g. http://arxiv.org/abs/2501.12345v1 -> 2501.12345"""
    m = re.search(r'(\d{4}\.\d{4,5})', entry_id)
    return m.group(1) if m else entry_id.split('/')[-1].split('v')[0]


def _fetch_openalex_citations(arxiv_id: str, delay: float = 0.1) -> Optional[int]:
    """Fetch citation count from OpenAlex for a given arXiv ID."""
    clean_id = _extract_arxiv_id(arxiv_id)
    url = "https://api.openalex.org/works"
    params = {
        'filter': f'ids.arxiv:{clean_id}',
        'mailto': 'explorer@example.com',
    }
    try:
        resp = requests.get(url, params=params, timeout=10, verify=False)
        if resp.status_code == 200:
            results = resp.json().get('results', [])
            if results:
                return results[0].get('cited_by_count', 0)
        return None
    except Exception:
        return None


def _title_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    """Check if two titles are similar enough to be considered duplicates."""
    a_clean = re.sub(r'[^a-z0-9 ]', '', a.lower().strip())
    b_clean = re.sub(r'[^a-z0-9 ]', '', b.lower().strip())
    return SequenceMatcher(None, a_clean, b_clean).ratio() >= threshold


def _first_sentence(text: str) -> str:
    """Extract the first sentence from text for core_contribution."""
    if not text:
        return ''
    text = text.strip().replace('\n', ' ')
    m = re.match(r'(.+?[.!?])(?:\s|$)', text)
    if m:
        return m.group(1).strip()
    return text[:200].strip()


def _is_arxiv_available() -> bool:
    """Quick probe to check if arXiv API is responding (not rate-limited)."""
    try:
        probe = requests.get(
            "https://export.arxiv.org/api/query",
            params={"search_query": "cat:cs.AI", "max_results": "1"},
            timeout=8,
            verify=False,
        )
        return probe.status_code == 200
    except Exception:
        return False


def _fetch_openalex_search(
    keywords: list[str],
    direction: str,
    days: int = 30,
    limit: int = 30,
) -> list[dict]:
    """Fallback fetcher using OpenAlex API, restricted to arXiv papers.

    Searches OpenAlex with keyword query but filters to arXiv source only
    (source ID s4306400194), so results have proper arXiv IDs, abstracts,
    and submission dates.
    """
    cutoff = date.today() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    # OpenAlex search: join keywords for broad matching
    query_str = " ".join(keywords[:5])
    print(f"  [OpenAlex fallback] Query: {query_str[:100]}")
    print(f"  Window: since {cutoff_str} | Limit: {limit}")

    # Load existing for dedup
    existing = load_all_papers()
    existing_titles = [p.title.lower().strip() for p in existing]
    existing_arxiv_ids = set()
    for p in existing:
        if p.links.paper:
            aid = _extract_arxiv_id(p.links.paper)
            if aid:
                existing_arxiv_ids.add(aid)

    notable_entities = load_config("notable_entities.yaml")
    notable_affiliations = notable_entities.get('affiliations', [])

    # Filter to arXiv source only (s4306400194) for quality + proper dates
    # OpenAlex per_page max is 200; use cursor pagination for larger requests
    url = "https://api.openalex.org/works"
    page_size = min(limit, 200)
    params = {
        'search': query_str,
        'per_page': page_size,
        'filter': f'from_publication_date:{cutoff_str},primary_location.source.id:s4306400194',
        'sort': 'cited_by_count:desc',
        'mailto': 'explorer@example.com',
    }

    works = []
    remaining = limit
    page = 1
    while remaining > 0:
        params['per_page'] = min(remaining, page_size)
        params['page'] = page
        try:
            resp = requests.get(url, params=params, timeout=30, verify=False)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAlex API error: HTTP {resp.status_code}")
            data = resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f"OpenAlex request failed: {e}")

        page_results = data.get('results', [])
        if not page_results:
            break
        works.extend(page_results)
        remaining -= len(page_results)
        page += 1
        if len(page_results) < params['per_page']:
            break
    results = []
    skipped_dup = 0

    for w in works:
        title = (w.get('display_name') or '').replace('\n', ' ').strip()
        if not title:
            continue

        # Extract arXiv ID from locations
        arxiv_id = ''
        for loc in (w.get('locations') or []):
            landing = loc.get('landing_page_url') or ''
            m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', landing)
            if m:
                arxiv_id = m.group(1)
                break

        # Dedup
        if arxiv_id and arxiv_id in existing_arxiv_ids:
            skipped_dup += 1
            continue
        if any(_title_similar(title, t) for t in existing_titles):
            skipped_dup += 1
            continue

        pub_date = w.get('publication_date') or date.today().isoformat()

        # Extract authors with affiliations
        authors = []
        author_affiliations = []
        for authorship in (w.get('authorships') or []):
            author = authorship.get('author', {})
            name = author.get('display_name', '')
            if name:
                authors.append(name)
            for inst in (authorship.get('institutions') or []):
                inst_name = inst.get('display_name', '')
                if inst_name and inst_name not in author_affiliations:
                    author_affiliations.append(inst_name)

        # Reconstruct abstract from inverted index
        abstract = ''
        inv_abstract = w.get('abstract_inverted_index')
        if inv_abstract:
            word_positions = []
            for word, positions in inv_abstract.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = ' '.join(wd for _, wd in word_positions)[:500]

        citations = w.get('cited_by_count') or 0

        # Detect notable affiliations from abstract + author institutions
        search_text = (abstract + ' ' + ' '.join(author_affiliations)).lower()
        affiliations_detected = []
        for aff in notable_affiliations:
            if aff.lower() in search_text:
                affiliations_detected.append(aff)

        paper_link = f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else ''
        try:
            year = int(pub_date[:4])
        except (ValueError, IndexError):
            year = date.today().year
        id_suffix = arxiv_id.replace('.', '') if arxiv_id else str(len(results) + 1).zfill(5)

        entry = {
            'id': f'{direction}-{year}-{id_suffix}',
            'title': title,
            'title_cn': '',
            'authors': authors,
            'affiliations': affiliations_detected,
            'date': pub_date,
            'venue': '',
            'links': {
                'paper': paper_link,
                'code': '',
                'blog': '',
                'demo': '',
            },
            'direction': direction,
            'tags': [],
            'category': 'method',
            'citations': citations,
            'is_open_source': False,
            'is_deployed': False,
            'core_contribution': _first_sentence(abstract),
            'summary': abstract,
            'key_results': [],
            'importance': _auto_importance(citations, affiliations_detected, notable_affiliations),
            'read_status': 'unread',
        }
        results.append(entry)
        existing_titles.append(title.lower().strip())

    print(f"  Found {len(results)} new papers (skipped {skipped_dup} duplicates)")
    return results


def _parse_arxiv_url(url: str) -> Optional[str]:
    """Extract arXiv ID from a URL like arxiv.org/abs/2501.12345 or arxiv.org/pdf/2501.12345."""
    m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', url)
    return m.group(1) if m else None


def _fetch_openalex_by_url(url: str) -> Optional[dict]:
    """Fetch a single work from OpenAlex by URL lookup."""
    encoded = requests.utils.quote(url, safe='')
    api_url = f"https://api.openalex.org/works/{encoded}"
    try:
        resp = requests.get(api_url, params={'mailto': 'explorer@example.com'}, timeout=15, verify=False)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def _scrape_webpage_meta(url: str) -> dict:
    """Scrape title and description from a webpage's HTML meta tags.

    Returns a dict with 'title', 'description', 'authors' (best-effort).
    Raises RuntimeError if the page cannot be fetched.
    """
    try:
        resp = requests.get(url, timeout=15, verify=False, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AIResearchTracker/1.0)',
        })
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Could not fetch URL: {e}")

    html = resp.text
    result = {'title': '', 'description': '', 'authors': []}

    # Extract og:title or <title>
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.IGNORECASE)
    if m:
        result['title'] = m.group(1).strip()
    else:
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if m:
            result['title'] = m.group(1).strip()

    # Extract og:description or meta description
    m = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    if m:
        result['description'] = m.group(1).strip()

    # Extract author from meta tag (best-effort)
    m = re.search(r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']author["\']', html, re.IGNORECASE)
    if m:
        result['authors'] = [a.strip() for a in m.group(1).split(',') if a.strip()]

    return result


def _openalex_work_to_paper(w: dict, direction: str, notable_affiliations: list) -> dict:
    """Convert an OpenAlex work object into a paper dict."""
    title = (w.get('display_name') or '').replace('\n', ' ').strip()
    pub_date = w.get('publication_date') or date.today().isoformat()

    # Extract arXiv ID from locations
    arxiv_id = ''
    for loc in (w.get('locations') or []):
        landing = loc.get('landing_page_url') or ''
        m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', landing)
        if m:
            arxiv_id = m.group(1)
            break

    authors = []
    author_affiliations = []
    for authorship in (w.get('authorships') or []):
        author = authorship.get('author', {})
        name = author.get('display_name', '')
        if name:
            authors.append(name)
        for inst in (authorship.get('institutions') or []):
            inst_name = inst.get('display_name', '')
            if inst_name and inst_name not in author_affiliations:
                author_affiliations.append(inst_name)

    # Reconstruct abstract from inverted index
    abstract = ''
    inv_abstract = w.get('abstract_inverted_index')
    if inv_abstract:
        word_positions = []
        for word, positions in inv_abstract.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        abstract = ' '.join(wd for _, wd in word_positions)[:500]

    citations = w.get('cited_by_count') or 0

    search_text = (abstract + ' ' + ' '.join(author_affiliations)).lower()
    affiliations_detected = []
    for aff in notable_affiliations:
        if aff.lower() in search_text:
            affiliations_detected.append(aff)

    paper_link = f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else (w.get('id') or '')
    try:
        year = int(pub_date[:4])
    except (ValueError, IndexError):
        year = date.today().year
    id_suffix = arxiv_id.replace('.', '') if arxiv_id else str(abs(hash(title)) % 100000).zfill(5)

    return {
        'id': f'{direction}-{year}-{id_suffix}',
        'title': title,
        'title_cn': '',
        'authors': authors,
        'affiliations': affiliations_detected,
        'date': pub_date,
        'venue': '',
        'links': {
            'paper': paper_link,
            'code': '',
            'blog': '',
            'demo': '',
        },
        'direction': direction,
        'tags': [],
        'category': 'method',
        'citations': citations,
        'is_open_source': False,
        'is_deployed': False,
        'core_contribution': _first_sentence(abstract),
        'summary': abstract,
        'key_results': [],
        'importance': _auto_importance(citations, affiliations_detected, notable_affiliations),
        'read_status': 'unread',
    }


def fetch_paper_by_url(url: str, direction: str) -> dict:
    """Fetch a single paper by URL. Supports arXiv and other URLs (via OpenAlex).

    Returns a paper dict, or raises RuntimeError on failure.
    The dict may include 'duplicate': True if the paper already exists.
    """
    if direction not in VALID_DIRECTIONS:
        raise RuntimeError(f"Invalid direction: {direction}")

    notable_entities = load_config("notable_entities.yaml")
    notable_affiliations = notable_entities.get('affiliations', [])

    # Load existing papers for dedup
    existing = load_all_papers()
    existing_titles = [p.title.lower().strip() for p in existing]
    existing_arxiv_ids = set()
    for p in existing:
        if p.links.paper:
            aid = _extract_arxiv_id(p.links.paper)
            if aid:
                existing_arxiv_ids.add(aid)

    arxiv_id = _parse_arxiv_url(url)

    if arxiv_id:
        # arXiv path
        session = requests.Session()
        session.verify = False
        client = arxiv.Client(page_size=1, delay_seconds=3.0, num_retries=3)
        client._session = session
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        if not results:
            raise RuntimeError(f"Paper not found on arXiv: {arxiv_id}")
        r = results[0]
        actual_id = _extract_arxiv_id(r.entry_id)

        # Fetch citations
        citations = 0
        c = _fetch_openalex_citations(r.entry_id)
        if c is not None:
            citations = c

        comments = getattr(r, 'comment', '') or ''
        search_text = (comments + ' ' + r.summary).lower()
        affiliations_detected = []
        for aff in notable_affiliations:
            if aff.lower() in search_text:
                affiliations_detected.append(aff)

        summary_text = r.summary.replace('\n', ' ').strip()[:500]

        paper = {
            'id': f'{direction}-{r.published.year}-{actual_id.replace(".", "")}',
            'title': r.title.replace('\n', ' ').strip(),
            'title_cn': '',
            'authors': [a.name for a in r.authors],
            'affiliations': affiliations_detected,
            'date': r.published.strftime('%Y-%m-%d'),
            'venue': '',
            'links': {
                'paper': f'https://arxiv.org/abs/{actual_id}',
                'code': '',
                'blog': '',
                'demo': '',
            },
            'direction': direction,
            'tags': [],
            'category': 'method',
            'citations': citations,
            'is_open_source': False,
            'is_deployed': False,
            'core_contribution': _first_sentence(summary_text),
            'summary': summary_text,
            'key_results': [],
            'importance': _auto_importance(citations, affiliations_detected, notable_affiliations),
            'read_status': 'unread',
        }

        # Dedup check
        if actual_id in existing_arxiv_ids:
            paper['duplicate'] = True
        elif any(_title_similar(paper['title'], t) for t in existing_titles):
            paper['duplicate'] = True

        return paper
    else:
        # Non-arXiv: try OpenAlex first, then scrape webpage
        w = _fetch_openalex_by_url(url)
        if w and w.get('display_name'):
            paper = _openalex_work_to_paper(w, direction, notable_affiliations)
        else:
            # Fallback: scrape the webpage for title/description
            meta = _scrape_webpage_meta(url)
            if not meta.get('title'):
                raise RuntimeError(f"Could not extract title from URL: {url}")

            today = date.today()
            id_suffix = str(abs(hash(url)) % 100000).zfill(5)
            paper = {
                'id': f'{direction}-{today.year}-{id_suffix}',
                'title': meta['title'],
                'title_cn': '',
                'authors': meta.get('authors', []),
                'affiliations': [],
                'date': today.isoformat(),
                'venue': '',
                'links': {
                    'paper': url,
                    'code': '',
                    'blog': '',
                    'demo': '',
                },
                'direction': direction,
                'tags': [],
                'category': 'method',
                'citations': 0,
                'is_open_source': False,
                'is_deployed': False,
                'core_contribution': _first_sentence(meta.get('description', '')),
                'summary': meta.get('description', ''),
                'key_results': [],
                'importance': 'medium',
                'read_status': 'unread',
            }

        # Dedup check
        oa_arxiv_id = ''
        link = paper.get('links', {}).get('paper', '')
        if 'arxiv.org' in link:
            oa_arxiv_id = _extract_arxiv_id(link)
        if oa_arxiv_id and oa_arxiv_id in existing_arxiv_ids:
            paper['duplicate'] = True
        elif any(_title_similar(paper['title'], t) for t in existing_titles):
            paper['duplicate'] = True

        return paper


def fetch_arxiv(
    direction: str,
    query: Optional[str] = None,
    days: int = 30,
    limit: int = 30,
) -> tuple[list[dict], str]:
    """Fetch papers from arXiv for a given direction.

    Falls back to OpenAlex if arXiv is rate-limited.
    Returns (list of dicts, source_name) where source_name is 'arxiv' or 'openalex'.
    """
    if direction not in VALID_DIRECTIONS:
        print(f"  Error: invalid direction '{direction}'. Must be one of: {', '.join(sorted(VALID_DIRECTIONS))}")
        return []

    config = load_search_config()
    dir_config = config.get('directions', {}).get(direction, {})
    citation_config = config.get('citations', {})

    # Build keywords for potential OpenAlex fallback
    fallback_keywords = [query] if query else dir_config.get('keywords', [])

    # Check arXiv availability; fallback to OpenAlex if rate-limited
    if not _is_arxiv_available():
        print("  arXiv API rate-limited, falling back to OpenAlex...")
        if not fallback_keywords:
            raise RuntimeError("arXiv rate-limited and no keywords configured for OpenAlex fallback.")
        return _fetch_openalex_search(fallback_keywords, direction, days=days, limit=limit), 'openalex'

    # Build arXiv query
    if query:
        # User-provided query override: combine with categories
        categories = dir_config.get('arxiv_categories', ['cat:cs.AI'])
        cat_query = ' OR '.join(categories)
        full_query = f'({cat_query}) AND (all:"{query}")'
    else:
        # Use config-defined categories + keywords
        categories = dir_config.get('arxiv_categories', ['cat:cs.AI'])
        keywords = dir_config.get('keywords', [])
        cat_query = ' OR '.join(categories)
        if keywords:
            kw_query = ' OR '.join(f'all:"{kw}"' for kw in keywords)
            full_query = f'({cat_query}) AND ({kw_query})'
        else:
            full_query = cat_query

    print(f"  Query: {full_query[:120]}{'...' if len(full_query)>120 else ''}")
    print(f"  Window: last {days} days | Limit: {limit}")

    # Set up client (SSL workaround)
    session = requests.Session()
    session.verify = False
    client = arxiv.Client(page_size=limit, delay_seconds=3.0, num_retries=3)
    client._session = session

    # When time window is large, use Relevance sort so arXiv returns papers
    # across the full period instead of only the most recent ones.
    sort_criterion = arxiv.SortCriterion.Relevance if days > 30 else arxiv.SortCriterion.SubmittedDate

    search = arxiv.Search(
        query=full_query,
        max_results=limit,
        sort_by=sort_criterion,
    )

    end = datetime.now(timezone.utc)
    cutoff = end - timedelta(days=days)

    # Load existing papers for dedup
    existing = load_all_papers()
    existing_titles = [p.title.lower().strip() for p in existing]
    existing_arxiv_ids = set()
    for p in existing:
        if p.links.paper:
            aid = _extract_arxiv_id(p.links.paper)
            if aid:
                existing_arxiv_ids.add(aid)

    # Load notable entities once before the loop
    notable_entities = load_config("notable_entities.yaml")
    notable_affiliations = notable_entities.get('affiliations', [])

    results = []
    skipped_dup = 0
    skipped_date = 0

    try:
        for r in client.results(search):
            # Date filter
            if r.published < cutoff or r.published > end:
                skipped_date += 1
                continue

            arxiv_id = _extract_arxiv_id(r.entry_id)

            # Dedup by arXiv ID
            if arxiv_id in existing_arxiv_ids:
                skipped_dup += 1
                continue

            # Dedup by title similarity
            if any(_title_similar(r.title, t) for t in existing_titles):
                skipped_dup += 1
                continue

            # Fetch citations if enabled
            citations = 0
            if citation_config.get('enabled'):
                c = _fetch_openalex_citations(r.entry_id, citation_config.get('batch_delay', 0.1))
                if c is not None:
                    citations = c
                time.sleep(citation_config.get('batch_delay', 0.1))

            # Detect notable entities from comments and abstract
            comments = getattr(r, 'comment', '') or ''
            search_text = (comments + ' ' + r.summary).lower()
            affiliations_detected = []
            for aff in notable_affiliations:
                if aff.lower() in search_text:
                    affiliations_detected.append(aff)

            summary_text = r.summary.replace('\n', ' ').strip()[:500]

            entry = {
                'id': f'{direction}-{r.published.year}-{arxiv_id.replace(".", "")}',
                'title': r.title.replace('\n', ' ').strip(),
                'title_cn': '',
                'authors': [a.name for a in r.authors],
                'affiliations': affiliations_detected,
                'date': r.published.strftime('%Y-%m-%d'),
                'venue': '',
                'links': {
                    'paper': f'https://arxiv.org/abs/{arxiv_id}',
                    'code': '',
                    'blog': '',
                    'demo': '',
                },
                'direction': direction,
                'tags': [],
                'category': 'method',
                'citations': citations,
                'is_open_source': False,
                'is_deployed': False,
                'core_contribution': _first_sentence(summary_text),
                'summary': summary_text,
                'key_results': [],
                'importance': _auto_importance(citations, affiliations_detected, notable_affiliations),
                'read_status': 'unread',
            }
            results.append(entry)
            existing_titles.append(r.title.lower().strip())  # prevent intra-batch dups
    except Exception as e:
        if "429" in str(e) and fallback_keywords:
            print(f"  arXiv 429 during fetch, falling back to OpenAlex...")
            return _fetch_openalex_search(fallback_keywords, direction, days=days, limit=limit), 'openalex'
        raise

    print(f"  Found {len(results)} new papers (skipped {skipped_dup} duplicates, {skipped_date} out-of-range)")
    return results, 'arxiv'


def write_candidates(direction: str, papers: list[dict], query: Optional[str] = None) -> Optional[Path]:
    """Write candidate papers to output/candidates/ as YAML."""
    if not papers:
        return None
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = CANDIDATES_DIR / f"{direction}_{today}.yaml"
    data = {'papers': papers}
    if query:
        data['fetch_query'] = query
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Fetch papers from arXiv')
    parser.add_argument('--direction', '-d', help='Research direction')
    parser.add_argument('--query', '-q', help='Custom search query (overrides config keywords)')
    parser.add_argument('--days', type=int, help='Time window in days')
    parser.add_argument('--limit', type=int, help='Max results to fetch')
    parser.add_argument('--all', action='store_true', help='Fetch all directions')
    parser.add_argument('--no-citations', action='store_true', help='Skip citation enrichment')
    args = parser.parse_args()

    config = load_search_config()
    defaults = config.get('defaults', {})
    days = args.days or defaults.get('time_window_days', 30)
    limit = args.limit or defaults.get('max_results', 30)

    if args.no_citations:
        config.setdefault('citations', {})['enabled'] = False

    if not args.all and not args.direction:
        parser.error('Specify --direction or --all')

    if args.all:
        directions = sorted(VALID_DIRECTIONS)
    else:
        if args.direction not in VALID_DIRECTIONS:
            parser.error(f"Invalid direction '{args.direction}'. Must be one of: {', '.join(sorted(VALID_DIRECTIONS))}")
        directions = [args.direction]

    for direction in directions:
        print(f"\n== Fetching: {direction} ==")
        papers, source = fetch_arxiv(direction, query=args.query, days=days, limit=limit)
        if papers:
            out = write_candidates(direction, papers, query=args.query)
            print(f"  -> Candidates written to {out}")
        else:
            print(f"  -> No new papers found")

    print(f"\nDone. Review candidates in output/candidates/, then run: make ingest")


if __name__ == '__main__':
    main()
