"""Tests for the scoring engine."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.models import PaperEntry, Links
from scripts.scorer import score_paper, score_papers, get_highlights, score_citations
from scripts.loader import load_papers_from_file

FIXTURES = Path(__file__).parent / "fixtures"


def make_paper(**kwargs):
    defaults = dict(
        id="test-001",
        title="Test Paper",
        authors=[],
        affiliations=[],
        date=date.today(),
        direction="post_training",
        tags=[],
        category="method",
        core_contribution="test",
        summary="test",
        links=Links(),
    )
    defaults.update(kwargs)
    return PaperEntry(**defaults)


def test_score_citations():
    config = {
        "weights": {
            "citation": [
                {"range": [0, 10], "score": 0},
                {"range": [10, 50], "score": 5},
                {"range": [50, 200], "score": 15},
                {"range": [200, 999999], "score": 30},
            ]
        }
    }
    assert score_citations(0, config) == 0
    assert score_citations(5, config) == 0
    assert score_citations(10, config) == 5
    assert score_citations(49, config) == 5
    assert score_citations(50, config) == 15
    assert score_citations(199, config) == 15
    assert score_citations(200, config) == 30
    assert score_citations(1000, config) == 30


def test_open_source_bonus():
    p1 = make_paper(is_open_source=False)
    p2 = make_paper(is_open_source=True)
    s1 = score_paper(p1)
    s2 = score_paper(p2)
    assert s2 > s1
    assert s2 - s1 == 10  # open_source weight


def test_deployed_bonus():
    p1 = make_paper(is_deployed=False)
    p2 = make_paper(is_deployed=True)
    s1 = score_paper(p1)
    s2 = score_paper(p2)
    assert s2 - s1 == 20  # deployed weight


def test_notable_affiliation_bonus():
    p1 = make_paper(affiliations=["Unknown Lab"])
    p2 = make_paper(affiliations=["OpenAI"])
    s1 = score_paper(p1)
    s2 = score_paper(p2)
    assert s2 > s1


def test_notable_author_bonus():
    p1 = make_paper(authors=["Nobody"])
    p2 = make_paper(authors=["John Schulman"])
    s1 = score_paper(p1)
    s2 = score_paper(p2)
    assert s2 > s1


def test_top_venue_bonus():
    p1 = make_paper(venue="Workshop")
    p2 = make_paper(venue="NeurIPS")
    s1 = score_paper(p1)
    s2 = score_paper(p2)
    assert s2 - s1 == 10


def test_importance_bonus():
    p_low = make_paper(importance="low")
    p_med = make_paper(importance="medium")
    p_high = make_paper(importance="high")
    assert score_paper(p_high) > score_paper(p_med) > score_paper(p_low)


def test_recency_bonus():
    p_recent = make_paper(date=date.today())
    p_old = make_paper(date=date.today() - timedelta(days=60))
    p_ancient = make_paper(date=date.today() - timedelta(days=120))
    s_recent = score_paper(p_recent)
    s_old = score_paper(p_old)
    s_ancient = score_paper(p_ancient)
    assert s_recent > s_old
    assert s_old > s_ancient


def test_score_papers_sorted():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    scored = score_papers(papers)
    scores = [p.score for p in scored]
    assert scores == sorted(scores, reverse=True)


def test_highlights_threshold():
    papers = load_papers_from_file(FIXTURES / "sample_papers.yaml")
    highlights = get_highlights(papers, threshold=40)
    for p in highlights:
        assert p.score >= 40


def test_score_deterministic():
    p = make_paper(citations=100, is_open_source=True, affiliations=["OpenAI"])
    s1 = score_paper(p)
    s2 = score_paper(p)
    assert s1 == s2


def test_score_papers_with_adjustments():
    p1 = make_paper(id="adj-001", importance="low")
    p2 = make_paper(id="adj-002", importance="high")
    adjustments = {"adj-001": 99.0}
    scored = score_papers([p1, p2], adjustments=adjustments)
    # adj-001 should have the adjusted score and be first
    assert scored[0].id == "adj-001"
    assert scored[0].score == 99.0
    assert scored[0].score_adjusted is True
    assert scored[0].computed_score is not None
    assert scored[0].computed_score != 99.0
    # adj-002 should use computed score
    assert scored[1].score_adjusted is False
    assert scored[1].score == scored[1].computed_score


def test_score_papers_empty_adjustments():
    p = make_paper(id="no-adj-001")
    scored = score_papers([p], adjustments={})
    assert scored[0].score_adjusted is False
    assert scored[0].score == scored[0].computed_score
