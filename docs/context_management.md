# Context Management Strategy

## The Problem

As the agent handles more question types, the knowledge needed to use tools correctly grows. Putting everything in the system prompt causes two problems: the prompt becomes large enough that the model ignores instructions buried in the middle, and guidance for one tool bleeds into reasoning about unrelated tools.

## Three-Tier Solution

### Tier 1 — System Prompt
**What:** Universal reasoning rules that apply regardless of which tools are used.
**Lives in:** `backend/app/agent/prompts.py` → `AGENT_SYSTEM_PROMPT`
**Examples:**
- Geography defaults (informal region names → pick a reasonable county and proceed)
- Data integrity (never answer from training knowledge)
- fetch_knowledge trigger (call before retrying any failed tool)

### Tier 2 — Tool Descriptions
**What:** Per-tool usage guidance visible every iteration at zero extra cost.
**Lives in:** `TOOL_SCHEMAS[*].function.description` in `backend/app/agent/tools.py`
**Examples:**
- Collection names for `search_feature_schema`
- FIPS string format for `search_fips_codes`
- Year/column differences for `get_field_descriptions`

Tool descriptions are always in context when the model decides which tool to call and how — no extra round trips.

### Tier 3 — Knowledge Files (Reactive)
**What:** Hard/edge-case recovery guides loaded only when a tool fails.
**Lives in:** `backend/docs/tool_knowledge/{tool_name}.md`
**Loaded by:** `fetch_knowledge` tool — model calls it after an error or empty result, before retrying.

| File | Covers |
|---|---|
| `search_fips_codes.md` | No matches, ambiguous names, multi-county regions |
| `search_feature_schema.md` | Empty results fallback (direct SQL, known table titles) |
| `get_field_descriptions.md` | No fields found, reading output, year differences |
| `execute_sql.md` | Invalid identifier recovery, empty results, patterns columns |

## Why This Works

**Happy path** — tool descriptions are enough, zero extra iterations.

**Error path** — one extra iteration max: `fetch_knowledge` → retry with guidance.

**Scale** — adding new edge cases means editing a `.md` file, not touching the system prompt or code.
