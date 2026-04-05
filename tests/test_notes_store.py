"""Tests for notes_store module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.notes_store import load_notes, save_note, delete_note


@pytest.fixture(autouse=True)
def isolate_notes(tmp_path, monkeypatch):
    notes_path = tmp_path / "notes.yaml"
    monkeypatch.setattr("scripts.notes_store.NOTES_PATH", notes_path)


def test_load_empty():
    assert load_notes() == {}


def test_save_and_load():
    save_note("post_training-2026-001", "Great paper on RLHF")
    notes = load_notes()
    assert notes == {"post_training-2026-001": "Great paper on RLHF"}


def test_save_empty_deletes():
    save_note("post_training-2026-001", "Some note")
    save_note("post_training-2026-001", "")
    notes = load_notes()
    assert "post_training-2026-001" not in notes


def test_overwrite():
    save_note("post_training-2026-001", "First version")
    save_note("post_training-2026-001", "Updated version")
    notes = load_notes()
    assert notes["post_training-2026-001"] == "Updated version"


def test_delete_note():
    save_note("llm_search_retrieval-2026-001", "A note")
    delete_note("llm_search_retrieval-2026-001")
    assert "llm_search_retrieval-2026-001" not in load_notes()


def test_multiple_notes():
    save_note("post_training-2026-001", "Note 1")
    save_note("world_models-2026-002", "Note 2")
    notes = load_notes()
    assert len(notes) == 2
    assert notes["post_training-2026-001"] == "Note 1"
    assert notes["world_models-2026-002"] == "Note 2"
