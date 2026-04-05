"""YAML data loader: load, merge, and filter paper entries."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from scripts.models import PaperEntry, VALID_DIRECTIONS
from scripts.utils import DATA_DIR, CONFIG_DIR


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_direction_meta(direction: str) -> dict:
    meta_path = DATA_DIR / direction / "_meta.yaml"
    if meta_path.exists():
        return load_yaml(meta_path)
    return {}


def load_papers_from_file(path: Path) -> list[PaperEntry]:
    data = load_yaml(path)
    if data is None:
        return []
    # Support both top-level list and {papers: [...]} format
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and "papers" in data:
        entries = data["papers"]
    else:
        return []
    return [PaperEntry.from_dict(e) for e in entries if e]


def load_direction(direction: str) -> list[PaperEntry]:
    dir_path = DATA_DIR / direction
    if not dir_path.exists():
        return []
    papers = []
    for f in sorted(dir_path.glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        papers.extend(load_papers_from_file(f))
    return papers


def load_all_papers() -> list[PaperEntry]:
    papers = []
    for direction in VALID_DIRECTIONS:
        papers.extend(load_direction(direction))
    return papers


def filter_papers(
    papers: list[PaperEntry],
    direction: Optional[str] = None,
    category: Optional[str] = None,
    importance: Optional[str] = None,
    tags: Optional[list[str]] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
    is_open_source: Optional[bool] = None,
    is_deployed: Optional[bool] = None,
    min_citations: Optional[int] = None,
) -> list[PaperEntry]:
    result = papers
    if direction:
        result = [p for p in result if p.direction == direction]
    if category:
        result = [p for p in result if p.category == category]
    if importance:
        result = [p for p in result if p.importance == importance]
    if tags:
        tag_set = set(tags)
        result = [p for p in result if tag_set.intersection(p.tags)]
    if since:
        result = [p for p in result if p.date >= since]
    if until:
        result = [p for p in result if p.date <= until]
    if is_open_source is not None:
        result = [p for p in result if p.is_open_source == is_open_source]
    if is_deployed is not None:
        result = [p for p in result if p.is_deployed == is_deployed]
    if min_citations is not None:
        result = [p for p in result if p.citations >= min_citations]
    return result


def load_config(name: str) -> dict:
    path = CONFIG_DIR / name
    return load_yaml(path)
