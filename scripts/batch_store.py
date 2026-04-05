"""Batch metadata store: records direction and query for each fetch batch."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.utils import DATA_DIR


BATCHES_PATH = DATA_DIR / "batches.yaml"


def load_batch_meta() -> dict[str, dict]:
    """Load {batch_id: {directions: [...], query: "..."}} mapping."""
    if not BATCHES_PATH.exists():
        return {}
    with open(BATCHES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("batches", {}) or {}


def save_batch_meta(batch_id: str, direction: str, query: str = "") -> dict:
    """Record metadata for a fetch batch. Appends direction if batch already exists."""
    all_meta = load_batch_meta()
    if batch_id in all_meta:
        entry = all_meta[batch_id]
        if direction not in entry.get("directions", []):
            entry.setdefault("directions", []).append(direction)
        if query and not entry.get("query"):
            entry["query"] = query
    else:
        all_meta[batch_id] = {
            "directions": [direction],
            "query": query,
        }
    BATCHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BATCHES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"batches": all_meta}, f, default_flow_style=False, allow_unicode=True)
    return all_meta[batch_id]
