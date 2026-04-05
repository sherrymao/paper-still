"""Generate self-contained HTML briefing pages from selected papers."""

from __future__ import annotations

import re
from datetime import date

from jinja2 import Environment, FileSystemLoader

from scripts.loader import load_all_papers
from scripts.scorer import score_papers
from scripts.notes_store import load_notes
from scripts.utils import OUTPUT_DIR, STATIC_DIR


def generate_briefing(paper_ids: list[str], title: str = "Research Briefing") -> dict:
    """Generate a briefing HTML file. Returns {filename, path, paper_count}."""
    papers = load_all_papers()
    scored = score_papers(papers)
    id_set = set(paper_ids)
    selected = [p for p in scored if p.id in id_set]
    selected.sort(key=lambda p: p.score or 0, reverse=True)

    notes = load_notes()

    env = Environment(loader=FileSystemLoader(str(STATIC_DIR)), autoescape=True)
    template = env.get_template("briefing_template.html")
    html = template.render(
        title=title,
        generated=date.today().isoformat(),
        papers=selected,
        notes=notes,
    )

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "briefing"
    filename = f"{slug}-{date.today().isoformat()}.html"
    out_dir = OUTPUT_DIR / "briefings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_text(html, encoding="utf-8")

    return {"filename": filename, "path": str(out_path), "paper_count": len(selected)}
