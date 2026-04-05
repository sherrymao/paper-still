# AI Research Tracker

A personal tool for tracking, scoring, and summarizing AI research papers. Fetch from arXiv, organize by research direction, and generate reports, dashboards, and NotebookLM-ready documents.

Your paper data and notes are gitignored — each user builds their own collection.

## Features

- **arXiv fetching** with OpenAlex citation enrichment and deduplication
- **Multi-direction tracking** — ships with Post-Training, World Models, LLM Search & Retrieval, and LLM Recommendation; easily extensible
- **Automated scoring** based on citations, affiliations, venue, open-source status, and manual importance
- **Interactive dashboard** (Flask) with paper selection, notes, NotebookLM integration, and briefing export
- **Static HTML dashboard** for quick browsing without a server
- **Markdown reports**, highlight lists, and NotebookLM-optimized documents
- **Candidate review workflow** — fetch, review, ingest, report

## Prerequisites

- Python 3.8+
- pip

## Quick Start

```bash
# Install dependencies
make install

# Fetch papers from arXiv (pick a direction)
make fetch direction=post_training

# Review candidates in output/candidates/, delete unwanted papers, add tags
# Then ingest into the data store
make ingest

# Validate data and generate all outputs
make validate
make all

# Open the static dashboard
open output/html/dashboard.html

# Or start the interactive dashboard
make serve
# -> http://localhost:5001
```

## Configuration

All configuration lives in `config/`:

| File | Purpose |
|------|---------|
| `config/search.yaml` | arXiv categories and keywords per direction |
| `config/scoring.yaml` | Scoring weights and highlight threshold |
| `config/taxonomy.yaml` | Valid directions, categories, and tags |
| `config/notable_entities.yaml` | Notable affiliations and researchers (score boost) |

## Adding Research Directions

The system ships with 4 directions but supports any number. To add a new one:

1. Add the slug to `directions:` in `config/taxonomy.yaml` and define its tags
2. Add arXiv categories and keywords in `config/search.yaml`
3. Create `data/{direction}/_meta.yaml` with direction metadata

Then `make fetch direction=your_new_direction` and proceed as usual. All outputs automatically pick up new directions.

If using [Claude Code](https://claude.com/claude-code), the `/add-direction` skill automates this interactively.

## Interactive Dashboard

Start the Flask server with `make serve` for the full interactive experience:

- **Paper notes** — per-paper reading notes, saved to `data/notes.yaml`
- **Paper selection** — checkboxes with bulk select per direction
- **Add to NotebookLM** — copy paper URLs and summaries for import into NotebookLM
- **Export Briefing** — generate self-contained HTML briefing pages with selected papers and your notes
- **My Notes** — standalone notes (ideas, TODOs) with tag and date filtering
- **By Fetch** — browse papers grouped by fetch batch with query metadata

The static dashboard (`make html`) supports read-only browsing of all data.

## Claude Code Integration

*Optional.* This project includes [Claude Code](https://claude.com/claude-code) configuration for AI-assisted workflows:

- `/add-direction` — interactively add a new research direction
- Agent role definitions in `agents/` for sub-agent workflows
- `CLAUDE.md` with project context for code assistance

These files are inert if you don't use Claude Code.

## Project Structure

```
├── data/                        # Paper data (YAML, per-direction monthly files)
│   ├── {direction}/_meta.yaml   #   Direction metadata (tracked in git)
│   └── {direction}/YYYY-MM.yaml #   Paper entries (gitignored, user-specific)
├── config/                      # Configuration files
├── scripts/                     # Python modules
│   ├── fetch.py                 #   arXiv fetcher + OpenAlex citations
│   ├── ingest.py                #   Candidate → data store merger
│   ├── scorer.py                #   Scoring engine
│   ├── validate.py              #   Data validation
│   ├── server.py                #   Flask REST API
│   ├── report_html.py           #   HTML dashboard generator
│   ├── report_notebooklm.py     #   NotebookLM documents
│   ├── briefing.py              #   HTML briefing generator
│   └── ...                      #   Store modules (notes, notebooks, batches, scoring)
├── templates/                   # Paper entry template
├── tests/                       # pytest test suite
├── static/                      # HTML/CSS templates
├── output/                      # Generated outputs (gitignored)
├── Makefile                     # Command entry point
├── CLAUDE.md                    # Claude Code project instructions
└── TUTORIAL.md                  # Detailed usage tutorial
```

## Development

```bash
make test       # Run the test suite
make validate   # Validate data integrity
make status     # Show data coverage stats
make clean      # Remove generated outputs (not data)
```

## All Commands

```
make install          Install dependencies
make status           Show data coverage and output status
make fetch            Fetch papers from arXiv (direction= days= limit= query=)
make fetch-all        Fetch all directions
make ingest           Ingest reviewed candidates into data store
make ingest-dry       Preview ingestion (dry run)
make validate         Validate data
make all              Generate all outputs
make html             Generate static HTML dashboard
make serve            Start interactive Flask dashboard (localhost:5001)
make test             Run tests
make clean            Remove generated outputs
make notebook-list    List NotebookLM notebook records
make notebook-register  Register a NotebookLM URL (id= url=)
```

## License

[MIT](LICENSE)
