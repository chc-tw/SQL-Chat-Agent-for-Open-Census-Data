# Agent Evaluation & Improvement

## Overview

Agent quality is maintained through an iterative validate → analyze → improve loop. The goal is to make the agent pass all 9 sampled questions (3 per difficulty level) before shipping a change.

## Prerequisites

- Backend server running locally: `uv run uvicorn app.main:app --port 8080`
- ChromaDB populated: `uv run python -m app.utils.index_metadata`

## The Loop

```
validate → analyze trace files → improve → delete traces → validate → …
```

Repeat until all 9 questions produce correct answers.

### 1. Run Validation

```bash
uv run python -m app.utils.run_validation --username chc --password chc419 --seed 42
```

This randomly samples 3 questions per level (easy / medium / hard) from `Dataset/testcase.json`, sends each question + its follow-up to the API, and prints live streaming output. Trace files are written to `backend/traces/` automatically.

Use `--seed` for reproducibility across runs. Omit it to get a fresh random sample.

### 2. Analyze Trace Files

Each trace file in `backend/traces/` is a JSON object containing:

| Field | Description |
|---|---|
| `iterations` | Array of agent steps, each with `thinking`, `tool`, `tool_input`, `tool_result` |
| `final_response` | The agent's answer to the user |
| `input_tokens` / `output_tokens` | Token counts |
| `duration_ms` | Total time |

Look for these failure patterns:

- **Empty tool result** — `search_feature_schema` returns `{"results": []}`, agent stalls
- **SQL error loop** — agent gets an identifier error, retries the same SQL unchanged
- **Geography refusal** — agent asks for clarification on an informal region name instead of proceeding
- **Hallucination** — agent answers from training knowledge when Snowflake returned nothing
- **Wrong tool arguments** — wrong collection name, blank county, wrong year

### 3. Improve

Decide where the fix belongs based on the **three-tier context model** (see `docs/context-management.md`):

| Fix type | Where to put it |
|---|---|
| Universal reasoning rule (e.g., "always proceed on ambiguous geography") | `backend/app/agent/prompts.py` — system prompt |
| Per-tool usage guidance visible every call | `TOOL_SCHEMAS[*].description` in `backend/app/agent/tools.py` |
| Recovery procedure for errors / empty results | `backend/docs/tool_knowledge/{tool_name}.md` |

**Priority rules:**
- Be conservative with the system prompt — only add a rule there if it applies regardless of which tool is being used
- Prefer enriching tool descriptions or knowledge files over touching the system prompt
- You can rewrite knowledge files entirely if the current content is wrong or misleading — keep them concise (they are injected into the context window on every recovery call)
- Do not simply append new rules — remove or consolidate outdated guidance first

### 4. Repeat

Run validation again with the same seed to test exactly the same questions:

```bash
uv run python -m app.utils.run_validation --username chc --password chc419 --seed 42
```

Continue until all 9 questions return correct, data-backed answers.

## What "Pass" Means

A question passes if:
- The agent retrieved data from Snowflake (not training knowledge)
- The final response directly answers what was asked
- No unrecovered errors in the trace (SQL errors are OK if the agent retried correctly via `fetch_knowledge`)

