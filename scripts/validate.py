"""Data validation and quality checks."""

from __future__ import annotations

import re
from collections import Counter

from scripts.models import (
    PaperEntry,
    VALID_DIRECTIONS,
    VALID_CATEGORIES,
    VALID_IMPORTANCE,
    VALID_READ_STATUS,
)
from scripts.loader import load_all_papers, load_config


class ValidationError:
    def __init__(self, paper_id: str, field: str, message: str):
        self.paper_id = paper_id
        self.field = field
        self.message = message

    def __repr__(self):
        return f"[{self.paper_id}] {self.field}: {self.message}"


def validate_paper(paper: PaperEntry, taxonomy: dict = None) -> list[ValidationError]:
    errors = []
    pid = paper.id

    # Required fields
    if not paper.id:
        errors.append(ValidationError(pid, "id", "ID is empty"))
    if not paper.title:
        errors.append(ValidationError(pid, "title", "Title is empty"))
    if not paper.authors:
        errors.append(ValidationError(pid, "authors", "Authors list is empty"))
    if not paper.direction:
        errors.append(ValidationError(pid, "direction", "Direction is empty"))
    if not paper.core_contribution:
        errors.append(ValidationError(pid, "core_contribution", "Core contribution is empty"))
    if not paper.summary:
        errors.append(ValidationError(pid, "summary", "Summary is empty"))

    # Enum validation
    if paper.direction and paper.direction not in VALID_DIRECTIONS:
        errors.append(ValidationError(pid, "direction", f"Invalid direction: {paper.direction}"))
    if paper.category and paper.category not in VALID_CATEGORIES:
        errors.append(ValidationError(pid, "category", f"Invalid category: {paper.category}"))
    if paper.importance not in VALID_IMPORTANCE:
        errors.append(ValidationError(pid, "importance", f"Invalid importance: {paper.importance}"))
    if paper.read_status not in VALID_READ_STATUS:
        errors.append(ValidationError(pid, "read_status", f"Invalid read_status: {paper.read_status}"))

    # Tag validation
    if taxonomy:
        valid_tags = set()
        for tag_list in taxonomy.get("tags", {}).values():
            valid_tags.update(tag_list)
        for tag in paper.tags:
            if tag not in valid_tags:
                errors.append(ValidationError(pid, "tags", f"Unknown tag: {tag}"))

    # URL format
    for link_name in ["paper", "code", "blog", "demo"]:
        url = getattr(paper.links, link_name, "")
        if url and not re.match(r"https?://", url):
            errors.append(ValidationError(pid, f"links.{link_name}", f"Invalid URL: {url}"))

    # Citation sanity
    if paper.citations < 0:
        errors.append(ValidationError(pid, "citations", "Citations cannot be negative"))

    return errors


def validate_all() -> list[ValidationError]:
    papers = load_all_papers()
    taxonomy = load_config("taxonomy.yaml")
    errors = []

    # Per-paper validation
    for paper in papers:
        errors.extend(validate_paper(paper, taxonomy))

    # ID uniqueness
    id_counts = Counter(p.id for p in papers)
    for pid, count in id_counts.items():
        if count > 1:
            errors.append(ValidationError(pid, "id", f"Duplicate ID (appears {count} times)"))

    return errors


def validate_and_report() -> tuple[bool, str]:
    errors = validate_all()
    if not errors:
        return True, "All validations passed."
    lines = [f"Found {len(errors)} validation error(s):"]
    for e in errors:
        lines.append(f"  - {e}")
    return False, "\n".join(lines)


if __name__ == "__main__":
    ok, report = validate_and_report()
    print(report)
    raise SystemExit(0 if ok else 1)
