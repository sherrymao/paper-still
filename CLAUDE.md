# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Track and summarize AI research progress across four directions:
- **Post-Training**: RLHF, DPO, alignment, instruction tuning
- **World Models**: Video prediction, physics simulation, embodied AI
- **LLM Search & Retrieval**: Dense retrieval, RAG, reranking, semantic search
- **LLM Recommendation**: Collaborative filtering, sequential/conversational recommendation, generative retrieval

## Quick Commands
- `make all` - Run full pipeline (validate + html)
- `make test` - Run all tests
- `make validate` - Validate data
- `make html` - Generate static HTML dashboard (for offline use)
- `make serve` - Start Flask server (interactive dashboard on port 5001, dynamic rendering)
- `make status` - Show paper counts per direction and output file status
- `make fetch direction=xxx` - Fetch papers from arXiv (CLI)
- `make fetch-all` - Fetch all directions (CLI)
- `make ingest` - Merge reviewed candidates into data store (CLI)
- `make ingest-dry` - Preview what would be ingested
- `make notebook-register id=nb-001 url=URL` - Register NotebookLM URL
- `make notebook-list` - List all notebook records

Run a single test file:
```
python -m pytest tests/test_scorer.py -v
```

## Paper Retrieval Workflow
### Web UI (preferred)
1. `make serve` → open http://localhost:5001 → go to **Fetch** tab
2. Select direction, optionally set query/days/limit, click **Fetch**
3. Review candidates: edit core_contribution, importance, tags; remove unwanted papers
4. Click **Ingest All** → papers appear immediately in All Papers tab

### CLI (alternative)
1. `make fetch direction=post_training` — fetches from arXiv + OpenAlex citations
2. Review `output/candidates/{direction}_{date}.yaml` — delete unwanted, add tags/importance
3. `make ingest` — merges into `data/{direction}/YYYY-MM.yaml`
4. `make validate && make all` — regenerate static HTML

Search config: `config/search.yaml` (per-direction arXiv categories + keywords)

## Data Entry
- Add papers to `data/{direction}/YYYY-MM.yaml` under a `papers:` list key
- Use `templates/paper_entry.yaml` as reference
- ID format: `{direction}-{year}-{seq}` (e.g., `post_training-2026-001`)
- Tags must match `config/taxonomy.yaml` (per-direction tag lists)
- `data/{direction}/_meta.yaml` holds direction-level metadata (name, description)

## Agent Roles
When using sub-agents, reference their role definitions:
- `agents/pm.md` - Planning and prioritization
- `agents/coder.md` - Data entry and script development
- `agents/reviewer.md` - Data quality and consistency
- `agents/tester.md` - Testing and validation

## Scoring
Papers are scored (0-100+) based on citations, open-source status, deployment, notable affiliations/authors, venue, manual importance, and recency. Papers scoring >= 40 are highlighted. Score weights are in `config/scoring.yaml`; notable entities (affiliations, researchers) are in `config/notable_entities.yaml`. Manual score overrides are stored in `data/score_adjustments.yaml`.

## Architecture

**Core pipeline:**
- `scripts/models.py` - `PaperEntry` dataclass + `Links`; `VALID_DIRECTIONS` loaded from `config/taxonomy.yaml`
- `scripts/loader.py` - YAML loading (`load_direction`, `load_all_papers`, `filter_papers`, `load_config`)
- `scripts/scorer.py` - Scoring engine (`score_paper`, `score_papers`, `get_highlights`)
- `scripts/validate.py` - Data validation (checks IDs, tags, required fields)
- `scripts/fetch.py` - arXiv fetcher + OpenAlex citation enrichment; outputs to `output/candidates/`
- `scripts/ingest.py` - Candidate → data store merger; `ingest_papers()` used by web UI, `delete_papers()` for removals
- `scripts/report_html.py` - Static HTML dashboard generator → `output/html/`
- `scripts/server.py` - Flask server: dynamic dashboard + REST API for fetch/ingest/notebooks/notes

**Storage helpers (each manages a single YAML file in `data/`):**
- `scripts/notebook_store.py` - NotebookLM collection tracking (`data/notebooks.yaml`)
- `scripts/notes_store.py` - Per-paper notes (`data/notes.yaml`)
- `scripts/random_notes_store.py` - Free-form research notes (`data/random_notes.yaml`)
- `scripts/score_adjustments_store.py` - Manual score overrides (`data/score_adjustments.yaml`)
- `scripts/batch_store.py` - Fetch batch metadata (`data/batch_meta.yaml`)

**Output generation:**
- `scripts/report_notebooklm.py` - Markdown doc generator for NotebookLM collections
- `scripts/briefing.py` - HTML briefing generator for selected papers → `output/briefings/`
- `scripts/utils.py` - Path constants (`DATA_DIR`, `OUTPUT_DIR`, `CONFIG_DIR`, `STATIC_DIR`)

**Template:** `static/template.html` (Jinja2, rendered by both Flask server and static generator)
