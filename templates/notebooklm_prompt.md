# NotebookLM Document Generation Prompt

You are generating a comprehensive research summary document for import into Google NotebookLM.

## Direction: {{ direction_name }}

## Requirements

1. **Length**: 5,000-15,000 words total
2. **Format**: Clean Markdown, no special syntax that NotebookLM cannot parse
3. **Self-contained**: All context must be within the document itself
4. **Conversational anchors**: Include questions and discussion points that NotebookLM's AI can engage with

## Structure

### 1. Field Overview (500-800 words)
- What is this research direction about?
- Why does it matter right now?
- Key challenges and open problems

### 2. Key Findings This Period (1500-3000 words)
For each highlighted paper (score >= threshold):
- What problem does it solve?
- What is the core technical contribution?
- What are the key results and why do they matter?
- How does it relate to other work in this list?

### 3. Other Notable Work (1000-2000 words)
- Brief summaries of medium-priority papers
- Group by sub-topic where possible

### 4. Trends and Observations (500-1000 words)
- Most active research sub-areas
- Emerging techniques or paradigms
- Active organizations and their focus areas
- Open source vs closed source trends

### 5. Appendix: Full Paper List
- Compact table of all papers with title, authors, venue, date, score
