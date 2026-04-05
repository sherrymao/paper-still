"""Ingest reviewed candidate papers into the main data store.

Reads candidate YAML files from output/candidates/, merges into
data/{direction}/YYYY-MM.yaml, and moves processed files to output/candidates/done/.

Usage:
    # Ingest all candidate files
    python -m scripts.ingest

    # Ingest a specific file
    python -m scripts.ingest --file output/candidates/post_training_2026-03-24.yaml

    # Dry run (show what would be ingested)
    python -m scripts.ingest --dry-run
"""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

import yaml

from scripts.loader import load_all_papers, load_papers_from_file
from scripts.models import VALID_DIRECTIONS
from scripts.batch_store import save_batch_meta
from scripts.utils import OUTPUT_DIR, DATA_DIR

CANDIDATES_DIR = OUTPUT_DIR / "candidates"
DONE_DIR = CANDIDATES_DIR / "done"


def load_candidate_file(path: Path) -> tuple[str, list[dict], str]:
    """Load a candidate YAML file. Returns (direction, papers_dicts, fetch_query)."""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data:
        return '', [], ''
    papers = data.get('papers', [])
    if not papers:
        return '', [], ''
    direction = papers[0].get('direction', '')
    fetch_query = data.get('fetch_query', '')
    return direction, papers, fetch_query


def get_next_seq(direction: str, year: int, existing_ids: set[str]) -> int:
    """Find the next available sequence number for a direction+year."""
    prefix = f'{direction}-{year}-'
    max_seq = 0
    for pid in existing_ids:
        if pid.startswith(prefix):
            try:
                seq = int(pid[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass
    return max_seq + 1


def ingest_file(path: Path, dry_run: bool = False) -> int:
    """Ingest a single candidate file. Returns number of papers ingested."""
    direction, papers, fetch_query = load_candidate_file(path)
    if not papers:
        print(f"  Skip {path.name}: no papers")
        return 0

    if direction not in VALID_DIRECTIONS:
        print(f"  Skip {path.name}: invalid direction '{direction}' (must be one of: {', '.join(sorted(VALID_DIRECTIONS))})")
        return 0

    # Load existing IDs for dedup
    existing = load_all_papers()
    existing_ids = {p.id for p in existing}

    # Determine target month file
    today = date.today()
    target_file = DATA_DIR / direction / f"{today.year}-{today.month:02d}.yaml"

    # Load existing target file if present
    if target_file.exists():
        with open(target_file, 'r', encoding='utf-8') as f:
            target_data = yaml.safe_load(f) or {}
        existing_entries = target_data.get('papers', [])
    else:
        existing_entries = []

    # Assign proper sequential IDs and filter already-existing
    next_seq = get_next_seq(direction, today.year, existing_ids)
    new_entries = []
    for p in papers:
        # Skip if ID already exists
        if p.get('id') in existing_ids:
            continue
        # Skip papers with empty core_contribution (user deleted during review)
        if not p.get('title', '').strip():
            continue
        # Assign a clean sequential ID
        p['id'] = f'{direction}-{today.year}-{next_seq:03d}'
        p['fetch_batch'] = today.isoformat()
        next_seq += 1
        new_entries.append(p)

    if not new_entries:
        print(f"  Skip {path.name}: all papers already exist or filtered")
        return 0

    if dry_run:
        print(f"  Would ingest {len(new_entries)} papers from {path.name} -> {target_file}")
        for p in new_entries:
            print(f"    {p['id']}: {p['title'][:70]}")
        return len(new_entries)

    # Merge and write
    all_entries = existing_entries + new_entries
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, 'w', encoding='utf-8') as f:
        yaml.dump({'papers': all_entries}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Record batch metadata
    save_batch_meta(today.isoformat(), direction, query=fetch_query)

    # Move candidate file to done/
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(DONE_DIR / path.name))

    print(f"  Ingested {len(new_entries)} papers from {path.name} -> {target_file.name}")
    return len(new_entries)


def ingest_papers(direction: str, papers: list[dict]) -> int:
    """Ingest papers directly (from web UI). Returns number of papers ingested."""
    if not papers:
        return 0
    if direction not in VALID_DIRECTIONS:
        return 0

    existing = load_all_papers()
    existing_ids = {p.id for p in existing}

    today = date.today()
    target_file = DATA_DIR / direction / f"{today.year}-{today.month:02d}.yaml"

    if target_file.exists():
        with open(target_file, 'r', encoding='utf-8') as f:
            target_data = yaml.safe_load(f) or {}
        existing_entries = target_data.get('papers', [])
    else:
        existing_entries = []

    next_seq = get_next_seq(direction, today.year, existing_ids)
    new_entries = []
    for p in papers:
        if p.get('id') in existing_ids:
            continue
        if not p.get('title', '').strip():
            continue
        p['id'] = f'{direction}-{today.year}-{next_seq:03d}'
        p['fetch_batch'] = today.isoformat()
        p['direction'] = direction
        next_seq += 1
        new_entries.append(p)

    if not new_entries:
        return 0

    all_entries = existing_entries + new_entries
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, 'w', encoding='utf-8') as f:
        yaml.dump({'papers': all_entries}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return len(new_entries)


def delete_papers(paper_ids: list[str]) -> int:
    """Delete papers from the data store by ID. Returns count of papers deleted."""
    if not paper_ids:
        return 0
    ids_to_delete = set(paper_ids)
    deleted = 0
    for direction in VALID_DIRECTIONS:
        dir_path = DATA_DIR / direction
        if not dir_path.exists():
            continue
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            if yaml_file.name == "_meta.yaml":
                continue
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            papers = data.get('papers', [])
            if not papers:
                continue
            filtered = [p for p in papers if p.get('id') not in ids_to_delete]
            removed = len(papers) - len(filtered)
            if removed > 0:
                deleted += removed
                if filtered:
                    with open(yaml_file, 'w', encoding='utf-8') as f:
                        yaml.dump({'papers': filtered}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                else:
                    yaml_file.unlink()
    return deleted


def main():
    parser = argparse.ArgumentParser(description='Ingest candidate papers into data store')
    parser.add_argument('--file', '-f', help='Specific candidate file to ingest')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be ingested without writing')
    args = parser.parse_args()

    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"File not found: {args.file}")
            return
        files = [p]
    else:
        if not CANDIDATES_DIR.exists():
            print("No candidates directory found. Run `make fetch` first.")
            return
        files = sorted(CANDIDATES_DIR.glob('*.yaml'))

    if not files:
        print("No candidate files found. Run `make fetch` first.")
        return

    total = 0
    for f in files:
        if f.parent.name == 'done':
            continue
        total += ingest_file(f, dry_run=args.dry_run)

    action = "Would ingest" if args.dry_run else "Ingested"
    print(f"\n{action} {total} papers total.")
    if not args.dry_run and total > 0:
        print("Run `make validate` to check data quality.")


if __name__ == '__main__':
    main()
