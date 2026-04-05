"""Score adjustments store: read/write data/score_adjustments.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.utils import DATA_DIR


ADJUSTMENTS_PATH = DATA_DIR / "score_adjustments.yaml"


def load_score_adjustments() -> dict[str, float]:
    """Load {paper_id: adjusted_score} mapping."""
    if not ADJUSTMENTS_PATH.exists():
        return {}
    with open(ADJUSTMENTS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("adjustments", {}) or {}


def save_score_adjustment(paper_id: str, score: float) -> None:
    """Save a score adjustment for a paper."""
    adjustments = load_score_adjustments()
    adjustments[paper_id] = float(score)
    ADJUSTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ADJUSTMENTS_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"adjustments": adjustments}, f, default_flow_style=False, allow_unicode=True)


def delete_score_adjustment(paper_id: str) -> None:
    """Delete a score adjustment (revert to computed score)."""
    adjustments = load_score_adjustments()
    adjustments.pop(paper_id, None)
    ADJUSTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ADJUSTMENTS_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"adjustments": adjustments}, f, default_flow_style=False, allow_unicode=True)
