"""Tests for data validation."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.models import PaperEntry, Links
from scripts.validate import validate_paper


def make_paper(**kwargs):
    defaults = dict(
        id="test-001",
        title="Test Paper",
        authors=["Author A"],
        affiliations=["Lab X"],
        date=date.today(),
        direction="post_training",
        tags=[],
        category="method",
        core_contribution="A test contribution",
        summary="A test summary",
        links=Links(),
    )
    defaults.update(kwargs)
    return PaperEntry(**defaults)


def test_valid_paper():
    p = make_paper()
    errors = validate_paper(p)
    assert len(errors) == 0


def test_missing_id():
    p = make_paper(id="")
    errors = validate_paper(p)
    assert any(e.field == "id" for e in errors)


def test_missing_title():
    p = make_paper(title="")
    errors = validate_paper(p)
    assert any(e.field == "title" for e in errors)


def test_missing_authors():
    p = make_paper(authors=[])
    errors = validate_paper(p)
    assert any(e.field == "authors" for e in errors)


def test_invalid_direction():
    p = make_paper(direction="invalid_direction")
    errors = validate_paper(p)
    assert any(e.field == "direction" for e in errors)


def test_invalid_category():
    p = make_paper(category="invalid_cat")
    errors = validate_paper(p)
    assert any(e.field == "category" for e in errors)


def test_invalid_importance():
    p = make_paper(importance="critical")
    errors = validate_paper(p)
    assert any(e.field == "importance" for e in errors)


def test_invalid_read_status():
    p = make_paper(read_status="finished")
    errors = validate_paper(p)
    assert any(e.field == "read_status" for e in errors)


def test_invalid_url():
    p = make_paper(links=Links(paper="not-a-url"))
    errors = validate_paper(p)
    assert any("links.paper" in e.field for e in errors)


def test_valid_url():
    p = make_paper(links=Links(paper="https://arxiv.org/abs/2026.00001"))
    errors = validate_paper(p)
    assert not any("links" in e.field for e in errors)


def test_negative_citations():
    p = make_paper(citations=-5)
    errors = validate_paper(p)
    assert any(e.field == "citations" for e in errors)


def test_unknown_tag():
    taxonomy = {
        "tags": {
            "post_training": ["rlhf", "dpo"],
        }
    }
    p = make_paper(tags=["unknown-tag"])
    errors = validate_paper(p, taxonomy)
    assert any(e.field == "tags" for e in errors)


def test_known_tag():
    taxonomy = {
        "tags": {
            "post_training": ["rlhf", "dpo"],
        }
    }
    p = make_paper(tags=["rlhf"])
    errors = validate_paper(p, taxonomy)
    assert not any(e.field == "tags" for e in errors)
