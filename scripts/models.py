"""Data models for paper entries."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path
from typing import List, Optional

import yaml


def _load_directions_from_config() -> set:
    """Load direction names from config/taxonomy.yaml."""
    config_path = Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        dirs = data.get("directions", [])
        if dirs:
            return set(dirs)
    return {"post_training", "world_models", "llm_search_retrieval"}


VALID_DIRECTIONS = _load_directions_from_config()
VALID_CATEGORIES = {"method", "survey", "benchmark", "system", "analysis"}
VALID_IMPORTANCE = {"high", "medium", "low"}
VALID_READ_STATUS = {"unread", "skimmed", "read", "deep-read"}


@dataclass
class Links:
    paper: str = ""
    code: str = ""
    blog: str = ""
    demo: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Links":
        if data is None:
            return cls()
        return cls(
            paper=data.get("paper", "") or "",
            code=data.get("code", "") or "",
            blog=data.get("blog", "") or "",
            demo=data.get("demo", "") or "",
        )


@dataclass
class PaperEntry:
    id: str
    title: str
    authors: list[str]
    affiliations: list[str]
    date: date
    direction: str
    tags: list[str]
    category: str
    core_contribution: str
    summary: str
    title_cn: str = ""
    venue: str = ""
    links: Links = field(default_factory=Links)
    citations: int = 0
    is_open_source: bool = False
    is_deployed: bool = False
    key_results: list[str] = field(default_factory=list)
    importance: str = "medium"
    read_status: str = "unread"
    fetch_batch: str = ""
    score: Optional[float] = None
    computed_score: Optional[float] = None
    score_adjusted: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "PaperEntry":
        d = dict(data)
        # Parse links
        d["links"] = Links.from_dict(d.get("links"))
        # Parse date
        if isinstance(d.get("date"), str):
            d["date"] = date.fromisoformat(d["date"])
        elif not isinstance(d.get("date"), date):
            d["date"] = date.today()
        # Defaults for optional list fields
        d.setdefault("key_results", [])
        d.setdefault("tags", [])
        d.setdefault("authors", [])
        d.setdefault("affiliations", [])
        # Remove unknown keys
        valid_keys = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**d)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "title_cn": self.title_cn,
            "authors": self.authors,
            "affiliations": self.affiliations,
            "date": self.date.isoformat(),
            "venue": self.venue,
            "links": {
                "paper": self.links.paper,
                "code": self.links.code,
                "blog": self.links.blog,
                "demo": self.links.demo,
            },
            "direction": self.direction,
            "tags": self.tags,
            "category": self.category,
            "citations": self.citations,
            "is_open_source": self.is_open_source,
            "is_deployed": self.is_deployed,
            "core_contribution": self.core_contribution,
            "summary": self.summary,
            "key_results": self.key_results,
            "importance": self.importance,
            "read_status": self.read_status,
            "fetch_batch": self.fetch_batch,
        }
