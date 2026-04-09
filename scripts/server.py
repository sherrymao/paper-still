"""Flask server: REST API for interactive dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import date

from flask import Flask, jsonify, request, send_file
from jinja2 import Environment, FileSystemLoader

from scripts.loader import load_all_papers, load_direction_meta, load_config
from scripts.scorer import score_papers, score_paper, get_highlights
from scripts.models import VALID_DIRECTIONS, PaperEntry
from scripts.report_notebooklm import generate_custom_notebooklm_doc
from scripts.notebook_store import (
    load_notebooks,
    create_notebook_entry,
    update_notebook_url,
    get_paper_notebook_map,
    remove_papers_from_notebooks,
)
from scripts.notes_store import load_notes, save_note, delete_note
from scripts.score_adjustments_store import (
    load_score_adjustments,
    save_score_adjustment,
    delete_score_adjustment,
)
from scripts.random_notes_store import load_random_notes, save_random_note, delete_random_note
from scripts.briefing import generate_briefing
from scripts.batch_store import load_batch_meta, save_batch_meta
from scripts.fetch import fetch_arxiv, fetch_paper_by_url, load_search_config
from scripts.ingest import ingest_papers, delete_papers
from scripts.utils import OUTPUT_DIR, STATIC_DIR

app = Flask(__name__)

# In-memory state for pending candidates from web fetch
_pending_candidates: dict = {
    "direction": "",
    "papers": [],
    "query": "",
}


def render_dashboard() -> str:
    """Render the dashboard HTML dynamically from current data."""
    papers = load_all_papers()
    adjustments = load_score_adjustments()
    scored = score_papers(papers, adjustments=adjustments)
    highlights = get_highlights(scored)

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
    return template.render(
        title="paper-still",
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


@app.route("/")
def index():
    return render_dashboard()


@app.route("/api/papers")
def api_papers():
    papers = load_all_papers()
    adjustments = load_score_adjustments()
    scored = score_papers(papers, adjustments=adjustments)
    result = []
    for p in scored:
        d = p.to_dict()
        d["score"] = p.score
        d["computed_score"] = p.computed_score
        d["score_adjusted"] = p.score_adjusted
        result.append(d)
    return jsonify(result)


@app.route("/api/notebook/generate", methods=["POST"])
def api_notebook_generate():
    data = request.get_json(force=True)
    paper_ids = data.get("paper_ids", [])
    name = data.get("name", "Untitled Collection")
    if not paper_ids:
        return jsonify({"error": "paper_ids is required"}), 400

    # Create notebook record
    nb = create_notebook_entry(name, paper_ids)

    # Generate markdown
    markdown = generate_custom_notebooklm_doc(paper_ids, title=name)

    # Collect URLs from papers
    papers = load_all_papers()
    scored = score_papers(papers)
    id_set = set(paper_ids)
    urls = []
    for p in scored:
        if p.id in id_set:
            url = p.links.paper if p.links.paper else ""
            urls.append({"title": p.title, "url": url, "paper_id": p.id})

    return jsonify({
        "notebook_id": nb["id"],
        "markdown": markdown,
        "urls": urls,
        "paper_count": len(paper_ids),
    })


@app.route("/api/notebook/register", methods=["POST"])
def api_notebook_register():
    data = request.get_json(force=True)
    notebook_id = data.get("id", "")
    url = data.get("url", "")
    if not notebook_id:
        return jsonify({"error": "id is required"}), 400
    nb = update_notebook_url(notebook_id, url)
    if nb is None:
        return jsonify({"error": "notebook not found"}), 404
    return jsonify(nb)


@app.route("/api/notebooks")
def api_notebooks():
    return jsonify(load_notebooks())


@app.route("/api/notes")
def api_notes():
    return jsonify(load_notes())


@app.route("/api/notes", methods=["POST"])
def api_save_note():
    data = request.get_json(force=True)
    paper_id = data.get("paper_id", "")
    text = data.get("text", "")
    if not paper_id:
        return jsonify({"error": "paper_id is required"}), 400
    save_note(paper_id, text)
    return jsonify({"paper_id": paper_id, "text": text})


@app.route("/api/score-adjustments")
def api_score_adjustments():
    return jsonify(load_score_adjustments())


@app.route("/api/score-adjustments", methods=["POST"])
def api_save_score_adjustment():
    data = request.get_json(force=True)
    paper_id = data.get("paper_id", "")
    if not paper_id:
        return jsonify({"error": "paper_id is required"}), 400
    score = data.get("score")
    if score is None:
        delete_score_adjustment(paper_id)
        return jsonify({"paper_id": paper_id, "score": None, "deleted": True})
    try:
        score = float(score)
    except (TypeError, ValueError):
        return jsonify({"error": "score must be a number or null"}), 400
    save_score_adjustment(paper_id, score)
    return jsonify({"paper_id": paper_id, "score": score})


@app.route("/api/random-notes")
def api_random_notes():
    return jsonify(load_random_notes())


@app.route("/api/random-notes", methods=["POST"])
def api_save_random_note():
    data = request.get_json(force=True)
    text = data.get("text", "")
    tags = data.get("tags", [])
    note_id = data.get("id")
    if not text.strip():
        return jsonify({"error": "text is required"}), 400
    note = save_random_note(text, tags=tags, note_id=note_id)
    return jsonify(note)


@app.route("/api/random-notes/<note_id>", methods=["DELETE"])
def api_delete_random_note(note_id):
    if delete_random_note(note_id):
        return jsonify({"deleted": note_id})
    return jsonify({"error": "not found"}), 404


@app.route("/api/briefing/generate", methods=["POST"])
def api_briefing_generate():
    data = request.get_json(force=True)
    paper_ids = data.get("paper_ids", [])
    title = data.get("title", "Research Briefing")
    if not paper_ids:
        return jsonify({"error": "paper_ids is required"}), 400
    result = generate_briefing(paper_ids, title)
    return jsonify(result)


@app.route("/briefing/<filename>")
def serve_briefing(filename):
    briefing_dir = OUTPUT_DIR / "briefings"
    # Resolve to prevent path traversal
    try:
        path = (briefing_dir / filename).resolve()
    except (ValueError, OSError):
        return "Not found", 404
    if not str(path).startswith(str(briefing_dir.resolve())):
        return "Not found", 404
    if not path.exists() or not path.name.endswith(".html"):
        return "Not found", 404
    return send_file(str(path))


# --- Fetch / Review / Ingest API ---

@app.route("/api/directions")
def api_directions():
    config = load_search_config()
    dir_configs = config.get("directions", {})
    result = []
    for slug in sorted(VALID_DIRECTIONS):
        meta = load_direction_meta(slug)
        dc = dir_configs.get(slug, {})
        result.append({
            "slug": slug,
            "name": meta.get("name", slug),
            "keywords": dc.get("keywords", []),
        })
    return jsonify({"directions": result})


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    global _pending_candidates
    data = request.get_json(force=True)
    direction = data.get("direction", "")
    query = data.get("query") or None
    days = data.get("days", 30)
    limit = data.get("limit", 30)

    if direction not in VALID_DIRECTIONS:
        return jsonify({"error": f"Invalid direction: {direction}"}), 400

    try:
        papers, source = fetch_arxiv(direction, query=query, days=days, limit=limit)
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            msg = "arXiv rate limit (HTTP 429). Please wait a minute and try again."
        else:
            msg = msg[:200] if len(msg) > 200 else msg
        return jsonify({"error": f"Fetch failed: {msg}"}), 502

    # Score each candidate and sort by score descending
    for p in papers:
        entry = PaperEntry.from_dict(p)
        p['score'] = score_paper(entry)
    papers.sort(key=lambda p: p.get('score', 0), reverse=True)

    _pending_candidates = {
        "direction": direction,
        "papers": papers,
        "query": query or "",
    }
    return jsonify({
        "papers": papers,
        "count": len(papers),
        "direction": direction,
        "query_used": query or "(default keywords)",
        "source": source,
    })


@app.route("/api/candidates")
def api_candidates():
    return jsonify(_pending_candidates)


@app.route("/api/candidates/update", methods=["POST"])
def api_candidates_update():
    data = request.get_json(force=True)
    index = data.get("index")
    fields = data.get("fields", {})
    papers = _pending_candidates.get("papers", [])

    if index is None or index < 0 or index >= len(papers):
        return jsonify({"error": "Invalid index"}), 400

    for key, value in fields.items():
        papers[index][key] = value

    return jsonify(papers[index])


@app.route("/api/candidates/delete", methods=["POST"])
def api_candidates_delete():
    data = request.get_json(force=True)
    index = data.get("index")
    papers = _pending_candidates.get("papers", [])

    if index is None or index < 0 or index >= len(papers):
        return jsonify({"error": "Invalid index"}), 400

    papers.pop(index)
    return jsonify({"remaining": len(papers)})


@app.route("/api/add-paper", methods=["POST"])
def api_add_paper():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    direction = data.get("direction", "")

    if not url:
        return jsonify({"error": "url is required"}), 400
    if direction not in VALID_DIRECTIONS:
        return jsonify({"error": f"Invalid direction: {direction}"}), 400

    try:
        paper = fetch_paper_by_url(url, direction)
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 502

    duplicate = paper.pop("duplicate", False)

    # Score the paper
    entry = PaperEntry.from_dict(paper)
    paper["score"] = score_paper(entry)

    # Append to pending candidates
    _pending_candidates["papers"].append(paper)
    if not _pending_candidates["direction"]:
        _pending_candidates["direction"] = direction

    index = len(_pending_candidates["papers"]) - 1
    return jsonify({"paper": paper, "index": index, "duplicate": duplicate})


@app.route("/api/papers/delete", methods=["POST"])
def api_delete_papers():
    data = request.get_json(force=True)
    paper_ids = data.get("paper_ids", [])
    if not paper_ids:
        return jsonify({"error": "paper_ids is required"}), 400

    count = delete_papers(paper_ids)
    for pid in paper_ids:
        delete_note(pid)
    remove_papers_from_notebooks(paper_ids)

    return jsonify({"deleted": count})


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    global _pending_candidates
    default_direction = _pending_candidates.get("direction", "")
    papers = _pending_candidates.get("papers", [])
    query = _pending_candidates.get("query", "")

    if not papers:
        return jsonify({"error": "No candidates to ingest"}), 400

    # Group papers by their direction field, falling back to the default
    by_direction: dict[str, list[dict]] = {}
    for p in papers:
        d = p.get("direction", default_direction)
        by_direction.setdefault(d, []).append(p)

    total_count = 0
    directions_ingested = []
    for d, group in by_direction.items():
        if d not in VALID_DIRECTIONS:
            continue
        count = ingest_papers(d, group)
        total_count += count
        if count > 0:
            directions_ingested.append(d)
            save_batch_meta(date.today().isoformat(), d, query=query)

    # Clear pending
    _pending_candidates = {"direction": "", "papers": [], "query": ""}

    return jsonify({"ingested": total_count, "direction": default_direction, "directions": directions_ingested})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=True, threaded=True)
