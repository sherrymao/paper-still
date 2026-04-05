"""Tests for briefing generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.briefing import generate_briefing


@pytest.fixture
def briefing_dir(tmp_path, monkeypatch):
    """Redirect output to tmp_path."""
    monkeypatch.setattr("scripts.briefing.OUTPUT_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def with_notes(tmp_path, monkeypatch):
    """Set up a notes file with test data."""
    import yaml
    notes_path = tmp_path / "notes.yaml"
    yaml.dump({"notes": {"post_training-2026-001": "Great paper on RLHF"}}, open(notes_path, "w"))
    monkeypatch.setattr("scripts.briefing.load_notes", lambda: {"post_training-2026-001": "Great paper on RLHF"})
    return notes_path


def test_generate_briefing_basic(briefing_dir):
    result = generate_briefing(["post_training-2026-001"], title="Test Briefing")
    assert result["paper_count"] == 1
    assert result["filename"].startswith("test-briefing-")
    assert result["filename"].endswith(".html")
    out = Path(result["path"])
    assert out.exists()
    html = out.read_text()
    assert "Test Briefing" in html


def test_generate_briefing_with_notes(briefing_dir, with_notes):
    result = generate_briefing(["post_training-2026-001"], title="Notes Test")
    html = Path(result["path"]).read_text()
    assert "Great paper on RLHF" in html
    assert "My Notes" in html


def test_generate_briefing_empty(briefing_dir):
    result = generate_briefing([], title="Empty")
    assert result["paper_count"] == 0
    assert Path(result["path"]).exists()
