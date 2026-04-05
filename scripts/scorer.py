"""Priority scoring engine for paper entries."""

from __future__ import annotations

from datetime import date, timedelta

from scripts.models import PaperEntry
from scripts.loader import load_config


def load_scoring_config() -> dict:
    return load_config("scoring.yaml")


def load_notable_entities() -> dict:
    return load_config("notable_entities.yaml")


def score_citations(citations: int, config: dict) -> float:
    for bracket in config["weights"]["citation"]:
        low, high = bracket["range"]
        if low <= citations < high:
            return bracket["score"]
    return 0


def score_paper(paper: PaperEntry, config: dict = None, entities: dict = None) -> float:
    if config is None:
        config = load_scoring_config()
    if entities is None:
        entities = load_notable_entities()

    weights = config["weights"]
    total = 0.0

    # Citation score
    total += score_citations(paper.citations, config)

    # Open source
    if paper.is_open_source:
        total += weights["open_source"]

    # Deployed
    if paper.is_deployed:
        total += weights["deployed"]

    # Notable affiliation
    notable_affiliations = set(entities.get("affiliations", []))
    if any(a in notable_affiliations for a in paper.affiliations):
        total += weights["notable_affiliation"]

    # Notable author
    notable_researchers = set(entities.get("researchers", []))
    if any(a in notable_researchers for a in paper.authors):
        total += weights["notable_author"]

    # Top venue
    top_venues = set(weights["top_venue"]["venues"])
    if paper.venue in top_venues:
        total += weights["top_venue"]["score"]

    # Manual importance
    importance_scores = weights["manual_importance"]
    total += importance_scores.get(paper.importance, 0)

    # Recency
    today = date.today()
    age = (today - paper.date).days
    if age <= 30:
        total += weights["recency"]["within_30_days"]
    elif age <= 90:
        total += weights["recency"]["within_90_days"]

    return total


def score_papers(papers: list[PaperEntry], adjustments: dict[str, float] = None) -> list[PaperEntry]:
    if adjustments is None:
        from scripts.score_adjustments_store import load_score_adjustments
        adjustments = load_score_adjustments()
    config = load_scoring_config()
    entities = load_notable_entities()
    for paper in papers:
        computed = score_paper(paper, config, entities)
        paper.computed_score = computed
        if paper.id in adjustments:
            paper.score = adjustments[paper.id]
            paper.score_adjusted = True
        else:
            paper.score = computed
            paper.score_adjusted = False
    return sorted(papers, key=lambda p: p.score or 0, reverse=True)


def get_highlights(papers: list[PaperEntry], threshold: float = None) -> list[PaperEntry]:
    config = load_scoring_config()
    if threshold is None:
        threshold = config.get("highlight_threshold", 40)
    scored = score_papers(papers)
    return [p for p in scored if (p.score or 0) >= threshold]
