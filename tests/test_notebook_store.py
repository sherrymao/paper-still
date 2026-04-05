"""Tests for notebook_store module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.notebook_store import (
    load_notebooks,
    save_notebooks,
    get_paper_notebook_map,
    create_notebook_entry,
    update_notebook_url,
    remove_papers_from_notebooks,
    _next_id,
    NOTEBOOKS_PATH,
)


@pytest.fixture
def clean_notebooks(tmp_path, monkeypatch):
    """Use a temp file for notebooks.yaml during tests."""
    nb_path = tmp_path / "notebooks.yaml"
    monkeypatch.setattr("scripts.notebook_store.NOTEBOOKS_PATH", nb_path)
    return nb_path


def test_load_empty(clean_notebooks):
    assert load_notebooks() == []


def test_save_and_load(clean_notebooks):
    entries = [{"id": "nb-001", "name": "Test", "paper_ids": ["p-001"]}]
    save_notebooks(entries)
    loaded = load_notebooks()
    assert len(loaded) == 1
    assert loaded[0]["id"] == "nb-001"


def test_get_paper_notebook_map():
    nbs = [
        {"id": "nb-001", "name": "A", "url": "https://nb.example.com/1", "paper_ids": ["p-001", "p-002"]},
        {"id": "nb-002", "name": "B", "url": "", "paper_ids": ["p-002", "p-003"]},
    ]
    mapping = get_paper_notebook_map(nbs)
    assert "p-001" in mapping
    assert len(mapping["p-001"]) == 1
    assert len(mapping["p-002"]) == 2
    assert mapping["p-003"][0]["id"] == "nb-002"


def test_next_id():
    assert _next_id([]) == "nb-001"
    assert _next_id([{"id": "nb-001"}, {"id": "nb-005"}]) == "nb-006"
    assert _next_id([{"id": "nb-099"}]) == "nb-100"


def test_create_notebook_entry(clean_notebooks):
    nb = create_notebook_entry("Test NB", ["p-001", "p-002"])
    assert nb["id"] == "nb-001"
    assert nb["name"] == "Test NB"
    assert nb["paper_ids"] == ["p-001", "p-002"]
    assert nb["url"] == ""

    # Second entry
    nb2 = create_notebook_entry("Second", ["p-003"])
    assert nb2["id"] == "nb-002"

    # Persisted
    loaded = load_notebooks()
    assert len(loaded) == 2


def test_update_notebook_url(clean_notebooks):
    create_notebook_entry("Test", ["p-001"])
    result = update_notebook_url("nb-001", "https://notebooklm.google.com/notebook/abc")
    assert result is not None
    assert result["url"] == "https://notebooklm.google.com/notebook/abc"

    # Persisted
    loaded = load_notebooks()
    assert loaded[0]["url"] == "https://notebooklm.google.com/notebook/abc"


def test_update_nonexistent(clean_notebooks):
    assert update_notebook_url("nb-999", "http://x.com") is None


def test_remove_papers_from_notebooks(clean_notebooks):
    create_notebook_entry("NB1", ["p-001", "p-002", "p-003"])
    create_notebook_entry("NB2", ["p-002", "p-004"])

    remove_papers_from_notebooks(["p-002", "p-003"])

    nbs = load_notebooks()
    assert nbs[0]["paper_ids"] == ["p-001"]
    assert nbs[1]["paper_ids"] == ["p-004"]


def test_remove_papers_from_notebooks_no_match(clean_notebooks):
    create_notebook_entry("NB1", ["p-001"])
    remove_papers_from_notebooks(["p-999"])
    nbs = load_notebooks()
    assert nbs[0]["paper_ids"] == ["p-001"]


def test_remove_papers_from_notebooks_empty(clean_notebooks):
    create_notebook_entry("NB1", ["p-001"])
    remove_papers_from_notebooks([])
    nbs = load_notebooks()
    assert nbs[0]["paper_ids"] == ["p-001"]
