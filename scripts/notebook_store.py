"""Notebook tracking: read/write data/notebooks.yaml."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scripts.utils import DATA_DIR


NOTEBOOKS_PATH = DATA_DIR / "notebooks.yaml"


def load_notebooks() -> list[dict]:
    if not NOTEBOOKS_PATH.exists():
        return []
    with open(NOTEBOOKS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("notebooks", []) or []


def save_notebooks(notebooks: list[dict]) -> None:
    NOTEBOOKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTEBOOKS_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"notebooks": notebooks}, f, default_flow_style=False, allow_unicode=True)


def get_paper_notebook_map(notebooks: list[dict]) -> dict:
    """Return {paper_id: [notebook_dicts]} mapping."""
    mapping: dict[str, list[dict]] = {}
    for nb in notebooks:
        for pid in nb.get("paper_ids", []):
            mapping.setdefault(pid, []).append(nb)
    return mapping


def _next_id(notebooks: list[dict]) -> str:
    max_num = 0
    for nb in notebooks:
        nid = nb.get("id", "")
        if nid.startswith("nb-"):
            try:
                num = int(nid[3:])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"nb-{max_num + 1:03d}"


def create_notebook_entry(name: str, paper_ids: list[str]) -> dict:
    notebooks = load_notebooks()
    entry = {
        "id": _next_id(notebooks),
        "name": name,
        "created": date.today().isoformat(),
        "url": "",
        "paper_ids": paper_ids,
    }
    notebooks.append(entry)
    save_notebooks(notebooks)
    return entry


def remove_papers_from_notebooks(paper_ids: list[str]) -> None:
    """Remove paper IDs from all notebooks' paper_ids lists."""
    ids_to_remove = set(paper_ids)
    notebooks = load_notebooks()
    changed = False
    for nb in notebooks:
        pids = nb.get("paper_ids", [])
        filtered = [pid for pid in pids if pid not in ids_to_remove]
        if len(filtered) != len(pids):
            nb["paper_ids"] = filtered
            changed = True
    if changed:
        save_notebooks(notebooks)


def update_notebook_url(notebook_id: str, url: str) -> dict | None:
    notebooks = load_notebooks()
    for nb in notebooks:
        if nb["id"] == notebook_id:
            nb["url"] = url
            save_notebooks(notebooks)
            return nb
    return None
