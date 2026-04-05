"""Tests for random notes store."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.random_notes_store import load_random_notes, save_random_note, delete_random_note


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.random_notes_store.RANDOM_NOTES_PATH", tmp_path / "random_notes.yaml")


def test_load_empty():
    assert load_random_notes() == []


def test_save_and_load():
    n = save_random_note("Hello world", tags=["idea"])
    assert n["text"] == "Hello world"
    assert n["tags"] == ["idea"]
    assert n["id"].startswith("rn-")
    notes = load_random_notes()
    assert len(notes) == 1
    assert notes[0]["id"] == n["id"]


def test_update():
    n = save_random_note("First version", tags=["draft"])
    updated = save_random_note("Second version", tags=["final"], note_id=n["id"])
    assert updated["id"] == n["id"]
    assert updated["text"] == "Second version"
    assert updated["tags"] == ["final"]
    notes = load_random_notes()
    assert len(notes) == 1


def test_delete():
    n = save_random_note("To delete")
    assert delete_random_note(n["id"])
    assert load_random_notes() == []


def test_delete_nonexistent():
    assert not delete_random_note("rn-fake")


def test_ordering():
    save_random_note("First")
    save_random_note("Second")
    notes = load_random_notes()
    assert notes[0]["text"] == "Second"
    assert notes[1]["text"] == "First"
