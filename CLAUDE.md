# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A full-stack Census Chat Agent: a React frontend + FastAPI backend that lets users ask natural language questions about the US Open Census dataset (2019–2020) stored in Snowflake. The backend runs a ReAct agent (claude-sonnet-4-6) that resolves geography → looks up feature schemas → writes and executes SQL → streams results back via SSE.

---

## Commands

### Backend (`backend/`)

```bash
# Run dev server (auto-reload)
uv run uvicorn app.main:app --reload --port 8080

# Verify imports / sanity check
uv run python -c "from app.main import app; print('OK')"

# Install dependencies
uv sync
```

No test suite exists yet. Use the import check above to validate changes.

### Frontend (`frontend/`)

```bash
pnpm dev          # Vite dev server on :5173
pnpm build        # tsc + vite build
pnpm tsc --noEmit # Type-check only (use this to verify TS changes)
```

---

## Environment Setup

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Purpose |
|---|---|
| `SNOWFLAKE_*` | Snowflake connection (account, user, password, warehouse, database, schema) |
| `ANTHROPIC_API_KEY` | For the ReAct agent (sonnet-4-6) and guardrails/reranking (haiku-4-5) |
| `OPENAI_API_KEY` | For embeddings (`text-embedding-3-large`) used by ChromaDB feature search |
| `JWT_SECRET` / `USERS` | Auth — `USERS` is a JSON array `[{"username":"...","password":"..."}]` |
| `GCP_PROJECT_ID` | Firestore project for chat history persistence |

GCP auth uses Application Default Credentials (`gcloud auth application-default login`).

ChromaDB vector store lives at `backend/chroma_db/` (local persistent directory, not in git). It must be populated before the feature search tool works.

---

## Architecture

### Request Flow

```
Browser → POST /api/chat/sessions/{id}/messages
  → check_guardrails (haiku, with last 6 messages for context)  [blocks if off-topic]
  → save user message to Firestore
  → EventSourceResponse streams:
      run_agent() [ReAct loop, sonnet-4-6]
        step_start → thinking_delta → tool_use → tool_result → ... → done → trace
      + concurrent asyncio.Task: generate_session_title (haiku) → session_rename event
```

### Backend Modules

- **`app/agent/runner.py`** — The ReAct loop. Calls Anthropic streaming API, dispatches tools via `asyncio.to_thread`, yields SSE event dicts. After the loop, writes a trace JSON to `backend/traces/` and yields a `trace` event.
- **`app/agent/tools.py`** — Four tools: `search_fips_codes` (batched county+state pairs → Snowflake FIPS lookup), `search_feature_schema` (ChromaDB vector search → haiku reranking), `get_field_descriptions` (Snowflake metadata query), `execute_sql` (SELECT-only Snowflake execution).
- **`app/agent/prompts.py`** — All LLM prompt strings in one place: `AGENT_SYSTEM_PROMPT`, `GUARDRAIL_SYSTEM_PROMPT`, `FEATURE_RERANK_PROMPT_TEMPLATE`, `SESSION_TITLE_PROMPT`.
- **`app/agent/guardrails.py`** — Async haiku-based content filter. Passes recent chat history as context so follow-up questions aren't blocked.
- **`app/api/chat.py`** — SSE endpoint. Owns the guardrails → save → stream pipeline. Generates session titles concurrently with the agent.
- **`app/services/`** — `anthropic_client.py` (both `AsyncAnthropic` and sync `Anthropic`), `snowflake_client.py`, `chromadb_client.py`, `embedding_client.py` (OpenAI), `firestore_client.py`.

### SSE Protocol

Every `data:` field is always `json.dumps()`-encoded (even strings) to prevent newline truncation. Frontend always `JSON.parse(event.data)`.

Event types: `step_start`, `thinking_delta`, `tool_use`, `tool_result`, `done`, `trace`, `error`, `session_rename`.

### Frontend Hooks

- **`useChat(sessionId, onRename?)`** — Manages message state, streams SSE events, prevents race condition where Firestore session load overwrites locally-added messages (`sentInSessionRef`).
- **`useSession(isLoggedIn)`** — Session list CRUD + `renameSession` for in-place title updates.

### Snowflake Data Model

All tables are prefixed: `US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"`.

- Population: `{year}_CBG_{TABLE_ID_prefix}` (e.g. `2019_CBG_B01`) — sharded by year + 3-char prefix
- Metadata: `{year}_METADATA_CBG_FIPS_CODES`, `{year}_METADATA_CBG_FIELD_DESCRIPTIONS`
- FIPS codes are strings — never cast to integer (leading zeros like `06` for California).

### LLM Models

| Model | Role |
|---|---|
| `claude-sonnet-4-6` | Main ReAct agent |
| `claude-haiku-4-5-20251001` | Guardrails, feature reranking, session title generation |
| `text-embedding-3-large` | ChromaDB embeddings (via OpenAI) |

### Auth

JWT-based. Users defined statically in `AUTH_USERS` env var (JSON array). No database — all user data lives in Firestore under `users/{username}/sessions/{session_id}/messages`.
