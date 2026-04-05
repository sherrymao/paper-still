# Tutorial: AI Research Tracker

This tutorial walks through the main workflows with concrete examples.

## 0. Setup

```bash
cd /path/to/ai-research-tracker
make install
```

Check that everything works:

```bash
make status
# === Data Coverage ===
#   llm_search_retrieval: 36 papers
#   post_training: 6 papers
#   world_models: 6 papers
#   Total: 48 papers
```

## 1. Fetching Papers from arXiv

`make fetch` is the entry point. It searches arXiv, enriches results with citation counts from OpenAlex, deduplicates against existing data, and writes candidate files for your review.

### Example A: Default fetch (one direction)

Uses keywords from `config/search.yaml`, last 30 days, up to 30 results:

```bash
make fetch direction=post_training
```

Output:
```
== Fetching: post_training ==
  Query: (cat:cs.CL OR cat:cs.LG OR cat:cs.AI) AND (all:"RLHF" OR all:"direct preference optimization" OR ...)
  Window: last 30 days | Limit: 30
  Found 18 new papers (skipped 3 duplicates, 2 out-of-range)
  -> Candidates written to output/candidates/post_training_2026-03-26.yaml
```

### Example B: Custom time window and limit

Search world_models over the last 60 days, fetch up to 50:

```bash
make fetch direction=world_models days=60 limit=50
```

### Example C: Custom query override

Ignore the default keywords in `config/search.yaml` and search with your own query:

```bash
make fetch direction=post_training query="direct preference optimization"
```

This builds the arXiv query as: `(cat:cs.CL OR cat:cs.LG OR cat:cs.AI) AND (all:"direct preference optimization")`

### Example D: Quick scan (no citation lookup)

Skip the OpenAlex API calls for faster results:

```bash
python3 -m scripts.fetch --direction llm_search_retrieval --days 7 --limit 10 --no-citations
```

### Example E: Fetch all three directions at once

```bash
make fetch-all
make fetch-all days=14 limit=20
```

This creates up to 3 candidate files in `output/candidates/`.

## 2. Reviewing Candidates

After fetching, open the candidate YAML file(s) in your editor:

```
output/candidates/
  post_training_2026-03-26.yaml
  world_models_2026-03-26.yaml
```

Each paper entry looks like:

```yaml
- id: post_training-2026-260318732
  title: "DreamerAD: Efficient RL via Latent World Model..."
  authors:
    - Alice Smith
    - Bob Jones
  affiliations:
    - MIT
  date: '2026-03-24'
  direction: post_training
  tags: []                        # <-- add tags here
  category: method
  citations: 12
  is_open_source: false           # <-- mark if open source
  is_deployed: false              # <-- mark if in production
  core_contribution: "We introduce DreamerAD, the first latent world model..."
  summary: "We introduce DreamerAD..."
  importance: medium              # <-- change to high/low
  read_status: unread
```

**What to do:**

| Action | How |
|--------|-----|
| Remove a paper you don't care about | Delete the entire `- id: ...` block |
| Mark as important | Change `importance: medium` to `importance: high` |
| Add tags | Add entries under `tags:` (see `config/taxonomy.yaml` for valid tags) |
| Mark open-source | Set `is_open_source: true` |
| Improve core_contribution | Edit the auto-generated text to be more precise |

You can also leave the file as-is and ingest everything with defaults.

## 3. Ingesting into the Data Store

### Preview first (dry run)

```bash
make ingest-dry
```

Output:
```
Would ingest 18 papers from post_training_2026-03-26.yaml -> data/post_training/2026-03.yaml
  post_training-2026-007: DreamerAD: Efficient RL via Latent World Model...
  post_training-2026-008: Comparing Developer and LLM Biases in Code Evaluation
  ...

Would ingest 18 papers total.
```

Papers get sequential IDs (continuing from existing data).

### Ingest for real

```bash
make ingest
```

The candidate file moves to `output/candidates/done/`. Papers are appended to `data/{direction}/2026-03.yaml`.

### Ingest a specific file

```bash
make ingest file=output/candidates/world_models_2026-03-26.yaml
```

## 4. Validating Data

```bash
make validate
```

Checks: required fields filled, valid enums, no duplicate IDs, URL formats, tag consistency.

If there are errors:
```
Found 3 validation error(s):
  - [post_training-2026-008] core_contribution: Core contribution is empty
  - [post_training-2026-009] tags: Unknown tag: nonexistent-tag
  - [post_training-2026-010] links.paper: Invalid URL: not-a-url
```

Fix them in the corresponding `data/{direction}/YYYY-MM.yaml` file, then re-validate.

## 5. Generating Outputs

### All at once

```bash
make all    # validate + report + highlight + notebook + html
```

### Individual outputs

```bash
make report      # -> output/reports/full_report.md
                 #    output/reports/monthly_2026-03.md

make highlight   # -> output/highlights/all_highlights.md
                 #    output/highlights/post_training_highlights.md
                 #    output/highlights/world_models_highlights.md
                 #    output/highlights/llm_search_retrieval_highlights.md

make notebook    # -> output/notebooklm/post_training_notebook.md
                 #    output/notebooklm/world_models_notebook.md
                 #    output/notebooklm/llm_search_retrieval_notebook.md

make html        # -> output/html/dashboard.html
```

### Open the HTML dashboard

```bash
open output/html/dashboard.html
```

静态 dashboard 中论文标题可点击跳转到 arXiv，高亮卡片显示 Paper / Code / Blog / Demo 链接按钮。

### Import into NotebookLM (批量方式)

Copy the content of any `output/notebooklm/*.md` file into a Google Doc, then add it as a source in NotebookLM.

## 6. 交互式 Dashboard & NotebookLM 集成

除了静态 HTML，你可以启动 Flask 服务器获得完整的交互式体验。

### 启动交互式 Dashboard

```bash
make html     # 先生成 dashboard（必须先执行一次）
make serve    # 启动 Flask server
```

打开浏览器访问 `http://localhost:5001`。

### 功能一览

交互式 Dashboard 在静态版基础上增加了：

- **论文链接** — 标题可点击跳转 arXiv，高亮卡片显示 Paper / Code / Blog / Demo 按钮
- **论文勾选** — 表格每行带 checkbox，每个方向支持全选
- **底部工具栏** — 勾选后自动出现，显示选中数量、名称输入框、"Add to NotebookLM" 和 "Export Briefing" 按钮
- **NB 徽章** — 已关联 notebook 的论文显示绿色可点击 `NB` 标记
- **论文笔记** — 每篇论文标题旁有 `Note` 按钮，展开后可编辑/保存个人笔记
- **Export Briefing** — 勾选论文后一键生成自包含的 HTML 知识页，可分享给他人
- **My Notes 标签页** — 独立的随手笔记区域，支持标签和日期筛选
- **By Fetch 增强** — 显示每次 fetch 的 direction 和 query 信息

### 工作流：将论文添加到 NotebookLM

NotebookLM 支持 URL 作为 source（自动抓取内容），但每次只能添加一个 URL。本工具辅助你高效完成这个过程：

**Step 1: 勾选论文**

在 dashboard 表格中勾选感兴趣的论文（可跨方向选择），在底部工具栏输入 collection 名称（如 "RLHF Deep Dive"）。

**Step 2: 点击 "Add to NotebookLM"**

弹出面板包含三部分：

```
┌──────────────────────────────────────────┐
│  Add to NotebookLM: "RLHF Deep Dive"    │
│                                          │
│  Step 1: Add these URLs as sources       │
│  1. REBEL: Reinforcement...  [Copy URL]  │
│  2. Constitutional AI 2.0... [Copy URL]  │
│  [Copy All URLs]                         │
│                                          │
│  Step 2: Add summary as text source      │
│  [Copy Summary to Clipboard]             │
│                                          │
│  Step 3: Register your NotebookLM URL    │
│  [ https://notebooklm.google... ] [Save] │
└──────────────────────────────────────────┘
```

- **Copy URL** — 逐个复制 URL，到 NotebookLM 中粘贴添加为 source
- **Copy All URLs** — 复制所有 URL（换行分隔），方便逐个粘贴
- **Copy Summary** — 复制自动生成的 Markdown 总结，到 NB 中粘贴作为文本 source（补充论文间的关联分析）
- **Save** — 创建 NB 后，将 NB URL 保存回系统

**Step 3: 查看 NB 标记**

```bash
make html    # 重新生成 dashboard
```

重新打开 dashboard，之前关联的论文旁会显示绿色 `NB` 徽章，点击直接跳转到 NotebookLM。

### 工作流：论文笔记

每篇论文标题旁有一个 `Note` 按钮，用于记录个人阅读笔记。

**添加/编辑笔记（交互模式）：**

1. 点击论文标题旁的 `Note` 按钮，展开编辑区域
2. 在文本框中输入笔记内容
3. 点击 `Save` 保存，笔记自动存入 `data/notes.yaml`
4. 有笔记的论文 `Note` 按钮变为蓝色高亮
5. 再次点击 `Note` 可收起编辑区域

笔记数据保存在 `data/notes.yaml`：

```yaml
notes:
  post_training-2026-001: "RLHF 的核心改进在于..."
  world_models-2026-003: "视频预测部分值得深入看"
```

笔记会被 Export Briefing 自动引用（见下节）。

### 工作流：Export Briefing（导出知识页）

勾选论文后可生成一个**自包含的 HTML 页面**，适合分享给同事或存档。Briefing 页面包含论文卡片（标题/作者/摘要/链接/标签）以及你的个人笔记。

**Step 1: 勾选论文**

在 dashboard 表格中勾选感兴趣的论文（可跨方向选择）。

**Step 2: 点击 "Export Briefing"**

底部工具栏点击蓝色 "Export Briefing" 按钮，弹出面板：

```
┌──────────────────────────────────────────┐
│  Export Briefing                         │
│                                          │
│  Briefing Title                          │
│  [ Research Briefing              ]      │
│                                          │
│  3 paper(s) selected                     │
│                                          │
│           [Generate]  [Close]            │
└──────────────────────────────────────────┘
```

输入标题（默认 "Research Briefing"），点击 `Generate`。

**Step 3: 查看 Briefing**

生成后自动在新标签页打开 briefing 页面。文件保存在 `output/briefings/` 目录下：

```
output/briefings/
  research-briefing-2026-03-26.html
  rlhf-deep-dive-2026-03-26.html
```

Briefing 页面是自包含 HTML（内联 CSS，无外部依赖），可以：
- 直接浏览器打开（无需 Flask 服务）
- 发送给同事/团队查看
- 存档到本地或网盘

**Briefing 页面内容：**

- 标题 + 生成日期 + 论文数量
- 每篇论文一个卡片，按 score 降序排列：
  - 标题（可点击跳转论文链接）
  - 作者 / 日期 / Venue / Score 徽章
  - Core contribution 摘要
  - Paper / Code / Blog / Demo 链接按钮
  - 标签
  - **My Notes** 引用块（仅在有笔记时显示）

### 工作流：My Notes（随手笔记）

Dashboard 新增了 **My Notes** 标签页，用于记录不绑定任何论文的自由笔记——灵感、想法、TODO、会议记录等。

**创建笔记：**

1. 切换到 "My Notes" 标签页
2. 在顶部文本框中输入内容
3. 输入标签（逗号分隔，如 `idea, rlhf, todo`）
4. 点击 `Save Note`

**编辑/删除：**

每条笔记卡片上有 `Edit` 和 `Delete` 按钮。Edit 会把内容加载回编辑框，修改后保存。

**筛选：**

笔记列表上方提供三种筛选器：
- **Tag 下拉** — 按标签筛选（自动从现有笔记提取）
- **From / To 日期** — 按创建日期范围筛选
- **Clear** — 清除所有筛选条件

笔记数据保存在 `data/random_notes.yaml`：

```yaml
notes:
  - id: rn-a1b2c3d4
    text: "RLHF 和 DPO 的关系可以类比为..."
    tags:
      - idea
      - rlhf
    created: "2026-03-27"
    updated: "2026-03-27"
```

### By Fetch 标签页增强

By Fetch 标签页现在显示每次 fetch 的更多信息：
- **Direction** — 该批次涉及的研究方向
- **Query** — 如果使用了自定义 query（非默认关键词），也会显示

信息来源于 `data/batches.yaml`，在 `make ingest` 时自动记录。已有数据（ingest 前导入的）不受影响，新的 ingest 会自动补充信息。

### Notebook 管理

```bash
# 查看所有 notebook 记录
make notebook-list
# === 2 Notebooks ===
#   nb-001: RLHF Deep Dive (5 papers) -> https://notebooklm.google.com/notebook/abc
#   nb-002: RAG Survey (3 papers) (no URL)

# 后续补录 NB URL（如果当时没保存）
make notebook-register id=nb-002 url="https://notebooklm.google.com/notebook/xyz"
```

Notebook 数据保存在 `data/notebooks.yaml`，格式如下：

```yaml
notebooks:
  - id: nb-001
    name: "RLHF Deep Dive"
    created: "2026-03-26"
    url: "https://notebooklm.google.com/notebook/abc"
    paper_ids:
      - post_training-2026-001
      - post_training-2026-002
      - post_training-2026-005
```

### 纯静态模式 vs 交互模式

| 功能 | 纯静态 (`make html`) | 交互式 (`make serve`) |
|------|----------------------|----------------------|
| 论文链接 | 可点击 | 可点击 |
| NB 徽章 | 显示 | 显示 |
| 勾选论文 | checkbox 可勾选但无法提交 | 完整功能 |
| 论文笔记 | 只读显示已有笔记 | 编辑/保存笔记 |
| My Notes 标签页 | 只读显示已有笔记 | 创建/编辑/删除/筛选 |
| 添加到 NotebookLM | 不可用 | 可用 |
| Export Briefing | 不可用 | 可用 |
| 注册 NB URL | 不可用（用 `make notebook-register`） | 面板中直接保存 |

静态模式适合日常浏览，交互模式适合深入研究和分享时使用。

## 7. Adding a New Research Direction

The system ships with 3 directions (`post_training`, `world_models`, `llm_search_retrieval`), but you can add more.

### Recommended: Interactive Skill (Claude Code)

In Claude Code, run:

```bash
/add-direction LLM in Recommendation
```

Claude will intelligently generate all configuration — slug, arXiv categories, keywords, taxonomy tags, and metadata — based on your description. You can review and adjust in conversation before anything is written. After confirmation, Claude writes all 3 config files, validates, and shows next steps.

This is the easiest way to add a direction: no manual file editing, no risk of format errors, and Claude's knowledge of arXiv taxonomy ensures good category/keyword choices.

### Alternative: Manual Steps

If you prefer to edit files directly, here's the complete checklist:

#### Step 1: Add to taxonomy

Edit `config/taxonomy.yaml` — add the slug to `directions:` list and add tags under `tags:`:

```yaml
directions:
  - post_training
  - world_models
  - llm_search_retrieval
  - code_generation          # <-- add here

tags:
  # ... existing tags ...
  code_generation:           # <-- add tag list
    - code-completion
    - program-synthesis
    - code-repair
    - repository-level
    - evaluation
```

`VALID_DIRECTIONS` in `scripts/models.py` loads dynamically from this file — no Python code changes needed.

#### Step 2: Add search config

Edit `config/search.yaml`, add a new block under `directions:`:

```yaml
directions:
  # ... existing directions ...
  code_generation:
    arxiv_categories:
      - "cat:cs.SE"
      - "cat:cs.CL"
      - "cat:cs.PL"
    keywords:
      - "code generation"
      - "program synthesis"
      - "code LLM"
      - "repository-level code"
```

#### Step 3: Create metadata

Create `data/code_generation/_meta.yaml`:

```yaml
direction: code_generation
name: Code Generation
name_cn: "Code Generation"
description: >
  Research on using LLMs for code generation, program synthesis,
  code repair, and repository-level understanding.
```

#### Step 4: Verify and fetch

```bash
make validate          # should pass (no papers yet is fine)
make fetch direction=code_generation
# review output/candidates/code_generation_*.yaml
make ingest
make all
```

The dashboard, reports, and all outputs will automatically pick up the new direction. Each direction gets its own section in the table view, batch view, highlights, and NotebookLM documents.

**Note**: The HTML dashboard, highlight lists, and reports iterate over `VALID_DIRECTIONS` automatically — no template changes are needed. Papers from any direction can be freely mixed in selections (NotebookLM, Briefing, etc.).

## 8. Customizing the Search

### Add new keywords

Edit `config/search.yaml`:

```yaml
directions:
  post_training:
    keywords:
      - "RLHF"
      - "DPO"
      - "GRPO"              # <-- add new keyword
      - "online RLHF"       # <-- add new keyword
```

### Add notable entities

Edit `config/notable_entities.yaml`:

```yaml
affiliations:
  - OpenAI
  - DeepSeek              # <-- papers from DeepSeek get +15 score

researchers:
  - John Schulman
  - Shunyu Yao            # <-- papers by Shunyu Yao get +10 score
```

### Adjust scoring weights

Edit `config/scoring.yaml`:

```yaml
weights:
  open_source: 10         # change to 20 if you value open-source more
  deployed: 20
  notable_affiliation: 15

highlight_threshold: 40   # lower to 30 to see more highlights
```

## 9. Common Workflows

### Weekly check-in

```bash
make fetch-all days=7 limit=30
# review output/candidates/*.yaml
make ingest
make all
open output/html/dashboard.html
```

### Deep dive on a specific topic

```bash
make fetch direction=post_training query="reward hacking" days=90 limit=50
# review and ingest
make ingest
make all
```

### 深入研究 + NotebookLM + Briefing

```bash
make fetch direction=post_training query="reward hacking" days=90 limit=50
# review and ingest
make ingest
make all
make serve                         # 启动交互式 Dashboard
# 浏览器打开 http://localhost:5001
# 1. 浏览论文，点 Note 按钮记录阅读笔记
# 2. 勾选相关论文，输入名称（如 "Reward Hacking Survey"）
# 3. 点击 "Add to NotebookLM" → 复制 URL/Summary → 导入 NB
# 4. 点击 "Export Briefing" → 输入标题 → Generate
#    → 自动打开 briefing 页面，包含论文卡片 + 你的笔记
#    → 文件保存在 output/briefings/，可直接分享
# 5. 创建完 NB 后，粘贴 NB URL → 点 Save
# 6. Ctrl+C 停止 server，运行 make html
# 7. 打开 dashboard，NB 徽章可点击跳转到 NotebookLM
```

### Quick status check

```bash
make status
make validate
```

### Start fresh

```bash
make clean    # removes all generated outputs (not data)
make all      # regenerate
```

## 10. Troubleshooting

| Problem | Solution |
|---------|----------|
| `make fetch` is slow | Add `--no-citations` via `python3 -m scripts.fetch ...` to skip OpenAlex API |
| Validation errors after ingest | Edit the data file mentioned in the error, then `make validate` |
| Duplicate papers after re-fetch | The dedup logic checks arXiv IDs + title similarity; if a paper slips through, delete it manually from the YAML |
| `make all` fails | Run `make validate` first to see what's wrong in the data |
| Want to undo an ingest | Edit `data/{direction}/YYYY-MM.yaml`, remove the unwanted entries |
| `make serve` 报错 "Dashboard not built yet" | 先运行 `make html` 生成 dashboard，再启动 server |
| NotebookLM 面板无反应 | 确保通过 `make serve` 访问（`http://localhost:5001`），静态打开不支持 API 调用 |
| Export Briefing 按钮无反应 | 同上，需要通过 Flask 交互模式访问 |
| Briefing 中没有显示笔记 | 先保存笔记（点 Note → 编辑 → Save），再 Export Briefing |
| 删除已生成的 briefing | 直接删除 `output/briefings/` 下对应的 `.html` 文件 |
| 删除一个 notebook 记录 | 编辑 `data/notebooks.yaml`，删除对应条目，再 `make html` |
| 删除一条笔记 | 交互模式下清空笔记内容并 Save，或编辑 `data/notes.yaml` 删除对应条目 |
| My Notes 标签页无法保存 | 同 NotebookLM，需要 Flask 交互模式 |
| By Fetch 没有显示 direction/query | 只有新的 ingest 会记录元数据到 `data/batches.yaml`，旧数据需手动补充 |
| 新增 direction 后 validate 报错 | 确认已在 `config/taxonomy.yaml` 的 `directions:` 列表中添加（`VALID_DIRECTIONS` 从此文件动态加载） |
