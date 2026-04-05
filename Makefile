.PHONY: all validate test html status clean install fetch fetch-all ingest ingest-dry serve notebook-register notebook-list

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

all: validate html

validate:
	$(PYTHON) -m scripts.validate

test:
	$(PYTHON) -m pytest tests/ -v

html:
	$(PYTHON) -m scripts.report_html

# Fetch papers from arXiv. Examples:
#   make fetch direction=post_training
#   make fetch direction=world_models query="video prediction" days=60 limit=50
#   make fetch-all
fetch:
	$(PYTHON) -m scripts.fetch --direction $(direction) $(if $(query),--query "$(query)") $(if $(days),--days $(days)) $(if $(limit),--limit $(limit))

fetch-all:
	$(PYTHON) -m scripts.fetch --all $(if $(days),--days $(days)) $(if $(limit),--limit $(limit))

# Ingest reviewed candidates into data store
ingest:
	$(PYTHON) -m scripts.ingest

ingest-dry:
	$(PYTHON) -m scripts.ingest --dry-run

serve:
	$(PYTHON) -m scripts.server --port 5001

notebook-register:
	$(PYTHON) -c "\
from scripts.notebook_store import update_notebook_url;\
nb = update_notebook_url('$(id)', '$(url)');\
print('Updated:', nb) if nb else print('Notebook not found: $(id)');\
"

notebook-list:
	$(PYTHON) -c "\
from scripts.notebook_store import load_notebooks;\
nbs = load_notebooks();\
print(f'=== {len(nbs)} Notebooks ===');\
[print(f\"  {nb['id']}: {nb['name']} ({len(nb.get('paper_ids',[]))} papers) {'-> ' + nb['url'] if nb.get('url') else '(no URL)'}\") for nb in nbs];\
"

status:
	@$(PYTHON) -c "\
from scripts.loader import load_direction, load_all_papers;\
from scripts.models import VALID_DIRECTIONS;\
import os;\
print('=== Data Coverage ===');\
total=0;\
[print(f'  {d}: {len(load_direction(d))} papers') or total.__class__.__init__ for d in sorted(VALID_DIRECTIONS)];\
papers=load_all_papers();\
print(f'  Total: {len(papers)} papers');\
print();\
print('=== Output Status ===');\
[print(f'  {sub}: {len(os.listdir(os.path.join(\"output\",sub))) if os.path.isdir(os.path.join(\"output\",sub)) else 0} file(s)') for sub in ['html','candidates']];\
"

clean:
	rm -rf output/html/* output/candidates/*.yaml output/candidates/done/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
