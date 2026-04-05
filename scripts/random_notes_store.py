"""Random notes store: standalone notes not tied to any paper."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional
import uuid

import yaml

from scripts.utils import DATA_DIR


RANDOM_NOTES_PATH = DATA_DIR / "random_notes.yaml"


def load_random_notes() -> list[dict]:
    """Load list of random notes, each: {id, text, tags, created, updated}."""
    if not RANDOM_NOTES_PATH.exists():
        return []
    with open(RANDOM_NOTES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("notes", []) or []


def _save_all(notes: list[dict]) -> None:
    RANDOM_NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RANDOM_NOTES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"notes": notes}, f, default_flow_style=False, allow_unicode=True)


def save_random_note(
    text: str,
    tags: Optional[list[str]] = None,
    note_id: Optional[str] = None,
) -> dict:
    """Create or update a random note. Returns the note dict."""
    notes = load_random_notes()
    today = date.today().isoformat()

    if note_id:
        for n in notes:
            if n["id"] == note_id:
                n["text"] = text.strip()
                n["tags"] = tags or []
                n["updated"] = today
                _save_all(notes)
                return n
        # Not found — fall through to create

    note = {
        "id": "rn-" + uuid.uuid4().hex[:8],
        "text": text.strip(),
        "tags": tags or [],
        "created": today,
        "updated": today,
    }
    notes.insert(0, note)
    _save_all(notes)
    return note


def delete_random_note(note_id: str) -> bool:
    """Delete a random note by ID. Returns True if found and deleted."""
    notes = load_random_notes()
    before = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    if len(notes) == before:
        return False
    _save_all(notes)
    return True
