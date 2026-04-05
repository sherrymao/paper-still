# Add New Research Direction

The user wants to add a new research direction: **$ARGUMENTS**

## Context

This project tracks AI research papers across multiple directions. Each direction requires entries in 3 config files + a data directory. Read existing directions as templates.

## Step 1: Understand the direction

Read these files to understand the current setup:
- `config/taxonomy.yaml` — existing directions list + per-direction tags
- `config/search.yaml` — existing arXiv categories + keywords per direction
- `data/post_training/_meta.yaml` — example metadata file

## Step 2: Generate configuration

Based on "$ARGUMENTS", intelligently determine:

1. **Slug**: lowercase, underscores, no stop words. Example: "LLM in Recommendation" -> `llm_recommendation`
2. **Display name**: Clean English name. Example: "LLM in Recommendation"
3. **Description**: 1-2 sentences describing the research area
4. **arXiv categories**: Pick the most relevant `cat:cs.*` categories (typically 2-4). Use your knowledge of arXiv taxonomy. Always format as `cat:cs.XX`.
5. **Keywords**: 6-12 search terms for arXiv API queries. Mix specific terms ("collaborative filtering LLM") and broader terms ("recommendation system"). These become arXiv `all:` query fields.
6. **Tags**: 8-15 taxonomy tags for classifying papers within this direction. Use lowercase-hyphenated format (e.g., `cold-start`, `sequential-recommendation`).

Present all generated values to the user and ask for confirmation before writing.

## Step 3: Write configuration files

After user confirms, write to these 3 locations:

### 3a. `config/taxonomy.yaml`
- Append slug to the `directions:` list
- Add a new key under `tags:` with the tag list

### 3b. `config/search.yaml`
- Add a new key under `directions:` with `arxiv_categories` and `keywords`

### 3c. `data/{slug}/_meta.yaml`
Create this new file:
```yaml
direction: {slug}
name: {display_name}
name_cn: "{display_name}"
description: >
  {description}
```

## Step 4: Validate

Run `make validate` to confirm the new direction is recognized and no errors.
Run `make status` to show it in the data coverage (should show 0 papers).

## Step 5: Summary

Tell the user:
- What was created
- Next step: `make fetch direction={slug}` to start fetching papers
- They can customize keywords/categories later by editing `config/search.yaml`
