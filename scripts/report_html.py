"""Generate HTML dashboard from paper data."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.loader import load_all_papers, load_direction_meta
from scripts.scorer import score_papers, get_highlights
from scripts.models import VALID_DIRECTIONS
from scripts.notebook_store import load_notebooks, get_paper_notebook_map
from scripts.notes_store import load_notes
from scripts.random_notes_store import load_random_notes
from scripts.batch_store import load_batch_meta
from scripts.score_adjustments_store import load_score_adjustments
from scripts.utils import OUTPUT_DIR, STATIC_DIR, ensure_output_dirs


def generate_html_dashboard():
    ensure_output_dirs()
    papers = load_all_papers()
    adjustments = load_score_adjustments()
    scored = score_papers(papers, adjustments=adjustments)
    highlights = get_highlights(scored)

    # Group by direction
    by_direction = {}
    for d in VALID_DIRECTIONS:
        meta = load_direction_meta(d)
        dir_papers = [p for p in scored if p.direction == d]
        by_direction[d] = {
            "meta": meta,
            "papers": dir_papers,
            "count": len(dir_papers),
            "avg_score": sum(p.score or 0 for p in dir_papers) / len(dir_papers) if dir_papers else 0,
            "open_source": sum(1 for p in dir_papers if p.is_open_source),
            "deployed": sum(1 for p in dir_papers if p.is_deployed),
        }

    # Compute fetch batches
    all_batches = sorted(set(p.fetch_batch for p in scored if p.fetch_batch), reverse=True)
    batches_data = {}
    for batch in all_batches:
        batch_papers = [p for p in scored if p.fetch_batch == batch]
        by_dir = {}
        for d in VALID_DIRECTIONS:
            meta = load_direction_meta(d)
            dir_papers = [p for p in batch_papers if p.direction == d]
            if dir_papers:
                by_dir[d] = {"meta": meta, "papers": dir_papers, "count": len(dir_papers)}
        batches_data[batch] = {"directions": by_dir, "count": len(batch_papers)}

    notebooks = load_notebooks()
    paper_nb_map = get_paper_notebook_map(notebooks)
    notes = load_notes()
    random_notes = load_random_notes()
    batch_meta = load_batch_meta()

    env = Environment(loader=FileSystemLoader(str(STATIC_DIR)))
    template = env.get_template("template.html")
    html = template.render(
        title="AI Research Tracker",
        generated=date.today().isoformat(),
        total_papers=len(scored),
        total_highlights=len(highlights),
        directions=by_direction,
        highlights=highlights,
        all_papers=scored,
        paper_notebook_map=paper_nb_map,
        notes=notes,
        random_notes=random_notes,
        all_batches=all_batches,
        batches_data=batches_data,
        batch_meta=batch_meta,
    )

    out = OUTPUT_DIR / "html" / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    generate_html_dashboard()
    print("HTML dashboard generated.")
