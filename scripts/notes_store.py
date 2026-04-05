"""Notes store: read/write data/notes.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.utils import DATA_DIR


NOTES_PATH = DATA_DIR / "notes.yaml"


def load_notes() -> dict[str, str]:
    """Load {paper_id: note_text} mapping."""
    if not NOTES_PATH.exists():
        return {}
    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("notes", {}) or {}


def save_note(paper_id: str, text: str) -> str:
    """Save or delete a note. Returns the text."""
    notes = load_notes()
    text = text.strip()
    if text:
        notes[paper_id] = text
    else:
        notes.pop(paper_id, None)
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"notes": notes}, f, default_flow_style=False, allow_unicode=True)
    return text


def delete_note(paper_id: str) -> None:
    """Delete a note."""
    save_note(paper_id, "")
