"""Tests for score adjustments store."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.score_adjustments_store import (
    load_score_adjustments,
    save_score_adjustment,
    delete_score_adjustment,
)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    path = tmp_path / "score_adjustments.yaml"
    monkeypatch.setattr("scripts.score_adjustments_store.ADJUSTMENTS_PATH", path)
    return path


def test_load_empty():
    assert load_score_adjustments() == {}


def test_save_and_load():
    save_score_adjustment("paper-001", 85.5)
    adj = load_score_adjustments()
    assert adj == {"paper-001": 85.5}


def test_save_multiple():
    save_score_adjustment("paper-001", 85.0)
    save_score_adjustment("paper-002", 42.0)
    adj = load_score_adjustments()
    assert len(adj) == 2
    assert adj["paper-001"] == 85.0
    assert adj["paper-002"] == 42.0


def test_overwrite():
    save_score_adjustment("paper-001", 50.0)
    save_score_adjustment("paper-001", 90.0)
    adj = load_score_adjustments()
    assert adj["paper-001"] == 90.0


def test_delete():
    save_score_adjustment("paper-001", 50.0)
    save_score_adjustment("paper-002", 60.0)
    delete_score_adjustment("paper-001")
    adj = load_score_adjustments()
    assert "paper-001" not in adj
    assert adj["paper-002"] == 60.0


def test_delete_nonexistent():
    # Should not raise
    delete_score_adjustment("fake-id")
    assert load_score_adjustments() == {}
