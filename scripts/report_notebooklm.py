"""Generate NotebookLM-compatible Markdown for custom paper collections."""

from __future__ import annotations

from datetime import date

from scripts.loader import load_all_papers
from scripts.scorer import score_papers


def generate_custom_notebooklm_doc(paper_ids: list[str], title: str = None) -> str:
    """Generate NotebookLM Markdown from an arbitrary set of paper IDs, cross-direction."""
    all_papers = load_all_papers()
    scored = score_papers(all_papers)
    selected = [p for p in scored if p.id in set(paper_ids)]
    # Sort by score descending
    selected.sort(key=lambda p: p.score or 0, reverse=True)

    if not selected:
        return "# No papers found for the given IDs.\n"

    doc_title = title or "Custom Research Collection"
    lines = []
    lines.append(f"# {doc_title}\n")
    lines.append(f"*Generated: {date.today().isoformat()}*\n")
    lines.append(f"This collection contains {len(selected)} papers.\n")

    for p in selected:
        lines.append(f"## {p.title} (Score: {p.score:.0f})\n")
        lines.append(f"**Authors**: {', '.join(p.authors)}")
        lines.append(f"**Affiliations**: {', '.join(p.affiliations)}")
        lines.append(f"**Date**: {p.date} | **Direction**: {p.direction} | **Venue**: {p.venue or 'N/A'}\n")
        lines.append(f"**Core Contribution**: {p.core_contribution}\n")
        lines.append(f"{p.summary}\n")
        if p.key_results:
            lines.append("**Key Results**:")
            for r in p.key_results:
                lines.append(f"- {r}")
            lines.append("")
        flags = []
        if p.is_open_source:
            flags.append("Open Source")
        if p.is_deployed:
            flags.append("Production Deployed")
        if flags:
            lines.append(f"**Notable**: {', '.join(flags)}\n")
        lines.append("---\n")

    return "\n".join(lines)
