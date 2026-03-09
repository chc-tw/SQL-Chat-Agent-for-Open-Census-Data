from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agent.prompts import FEATURE_RERANK_PROMPT_TEMPLATE
from app.services.anthropic_client import sync_client
from app.services.chromadb_client import chroma_client
from app.services.embedding_client import embed_text
from app.services.snowflake_client import run_query

_RERANK_MODEL = "claude-haiku-4-5-20251001"

DB_PREFIX = 'US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC'
MAX_ROWS = 50

# State name → abbreviation mapping for FIPS lookups
_STATE_ABBREVS: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

_KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "docs" / "tool_knowledge"

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_fips_codes",
        "description": (
            "Search FIPS code metadata to resolve one or more geographic locations into "
            "FIPS codes. Each location is a {county, state} pair. "
            "Providing both county and state filters most precisely — leave either blank only if truly unknown. "
            "All locations are resolved in a single call — batch all needed locations together. "
            "State full names are automatically resolved to abbreviations (e.g., 'California' → 'CA'). "
            "Returns matching rows with STATE, STATE_FIPS, COUNTY_FIPS, COUNTY per location. "
            "FIPS codes are strings — STATE_FIPS is 2 digits, COUNTY_FIPS is 5 digits (state+county combined)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "locations": {
                    "type": "array",
                    "description": (
                        "List of locations to resolve. Each entry has 'county' and 'state' — "
                        "leave either as an empty string if unknown. "
                        "Examples: [{'county': 'Fulton', 'state': 'GA'}, "
                        "{'county': 'San Diego County', 'state': ''}, "
                        "{'county': '', 'state': 'California'}]"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "county": {
                                "type": "string",
                                "description": "County name or partial name (e.g., 'Fulton', 'San Diego County'). Leave blank for state-only search.",
                            },
                            "state": {
                                "type": "string",
                                "description": "State name or abbreviation (e.g., 'GA', 'California'). Leave blank for county-only search.",
                            },
                        },
                        "required": ["county", "state"],
                    },
                    "minItems": 1,
                },
                "year": {
                    "type": "string",
                    "enum": ["2019", "2020"],
                    "description": "The dataset year to search in. Defaults to '2019'.",
                },
            },
            "required": ["locations"],
        },
    },
    {
        "name": "search_feature_schema",
        "description": (
            "Search for relevant census feature tables by semantic similarity. "
            "Searches one of four ChromaDB collections — choose the right one for your question:\n"
            "  '2019': 2019 ACS demographic fields (income, age, race, housing, education, etc.)\n"
            "  '2020': 2020 ACS demographic fields (same topics, different year)\n"
            "  '2020_redistricting': 2020 redistricting-specific population fields\n"
            "  '2019_patterns': SafeGraph CBG mobility columns (visit counts, visitor counts, distance, brand patterns)\n"
            "Returns top-K results with topic and universe. "
            "If results are empty, call fetch_knowledge('search_feature_schema') for fallback strategies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of the census feature (e.g., 'median household income', 'educational attainment', 'visit count').",
                },
                "year": {
                    "type": "string",
                    "enum": ["2019", "2020", "2020_redistricting", "2019_patterns"],
                    "description": "Which collection to search: '2019' or '2020' for ACS demographic fields, '2020_redistricting' for redistricting-specific features, '2019_patterns' for SafeGraph mobility/visit pattern columns.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return. Defaults to 5.",
                },
            },
            "required": ["query", "year"],
        },
    },
    {
        "name": "get_field_descriptions",
        "description": (
            "Get detailed column/field descriptions for a specific table title from "
            "the Snowflake metadata. Returns all column definitions so you can identify exact column names for SQL.\n"
            "Year differences:\n"
            "  '2019' and '2020': search by TABLE_TITLE (e.g., 'MEDIAN HOUSEHOLD INCOME', 'SEX BY AGE'). "
            "The returned TABLE_NUMBER prefix determines the data table (e.g., 'B19013' → prefix 'B19' → table '2019_CBG_B19').\n"
            "  '2020_redistricting': search by COLUMN_TOPIC instead of TABLE_TITLE.\n"
            "Try broad search terms if a specific title returns no results (e.g., 'INCOME' instead of 'MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_title": {
                    "type": "string",
                    "description": "The TABLE_TITLE or COLUMN_TOPIC to look up (e.g., 'Sex By Age', 'RACE').",
                },
                "year": {
                    "type": "string",
                    "enum": ["2019", "2020", "2020_redistricting"],
                    "description": "The dataset year.",
                },
            },
            "required": ["table_title", "year"],
        },
    },
    {
        "name": "execute_sql",
        "description": (
            "Execute a SQL query against Snowflake and return results. "
            "Only SELECT and WITH queries are allowed. Results are truncated to 50 rows.\n"
            "Column name rules:\n"
            "  - ACS population table column names are mixed-case (e.g., 'B01001e1', 'B19013e1'). "
            "Snowflake uppercases unquoted identifiers, so you MUST double-quote them: \"B19013e1\" not B19013e1.\n"
            "  - Always verify exact column names with SELECT * FROM {table} LIMIT 5 before writing analytical queries.\n"
            "  - FIPS filter values must be quoted strings: LEFT(CENSUS_BLOCK_GROUP, 5) = '06073' not = 6073.\n"
            "If the query fails with an invalid identifier error, call fetch_knowledge('execute_sql') before retrying."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The Snowflake SQL query to execute.",
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "fetch_knowledge",
        "description": (
            "Fetch a recovery guide for a tool that returned an error or empty results. "
            "Call this before retrying a failed tool call. "
            "Available for all four tools:\n"
            "  'search_fips_codes' — no matches, ambiguous county names, multi-county regions\n"
            "  'search_feature_schema' — empty results, fallback strategies\n"
            "  'get_field_descriptions' — no fields found, reading output, year differences\n"
            "  'execute_sql' — invalid identifier, empty results, table not found, patterns columns"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "enum": ["search_fips_codes", "search_feature_schema", "get_field_descriptions", "execute_sql"],
                    "description": "The name of the tool to fetch recovery guidance for.",
                },
            },
            "required": ["tool_name"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def search_fips_codes(locations: list[dict[str, str]], year: str = "2019") -> str:
    """
    Resolve a list of {county, state} pairs to FIPS codes in one call.
    Providing both county and state uses AND for precise matching.
    """
    table = f'{DB_PREFIX}."{year}_METADATA_CBG_FIPS_CODES"'
    all_results: list[dict] = []

    for loc in locations:
        county = loc.get("county", "").strip()
        state = loc.get("state", "").strip()

        # Resolve full state name to abbreviation
        state = _STATE_ABBREVS.get(state.lower(), state)

        if county and state:
            where = f"COUNTY ILIKE '%{county}%' AND STATE ILIKE '%{state}%'"
        elif county:
            where = f"COUNTY ILIKE '%{county}%'"
        elif state:
            where = f"STATE ILIKE '%{state}%'"
        else:
            continue  # skip blank entries

        sql = (
            f"SELECT STATE, STATE_FIPS, COUNTY_FIPS, COUNTY "
            f"FROM {table} "
            f"WHERE {where} "
            f"LIMIT 20"
        )
        try:
            rows = run_query(sql)
            label = f"{county}, {state}".strip(", ")
            all_results.append({
                "location": label,
                "matches": rows,
            })
        except Exception as e:
            all_results.append({
                "location": f"{county}, {state}".strip(", "),
                "error": str(e),
            })

    if not all_results:
        return json.dumps({"results": [], "message": "No valid locations provided."})
    return json.dumps({"results": all_results}, default=str)


def search_feature_schema(query: str, year: str = "2019", top_k: int = 5) -> str:
    """
    Vector search (top 30 candidates) + LLM reranking with claude-haiku-4-5.
    The top_k parameter controls the final number of results returned (default 5).
    """
    collection_map = {
        "2019": "2019_field_metadata",
        "2020": "2020_field_metadata",
        "2020_redistricting": "2020_redistricting_field_metadata",
        "2019_patterns": "2019_cbg_patterns_all_column",
    }
    collection_name = collection_map.get(year)
    if not collection_name:
        return json.dumps({"error": f"Unknown year: {year}"})

    try:
        collection = chroma_client.get_collection(collection_name)
    except Exception:
        return json.dumps({"error": f"Collection '{collection_name}' not found"})

    # Retrieve 30 candidates via vector search
    query_embedding = embed_text(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=30,
    )

    candidates = []
    for i in range(len(results["ids"][0])):
        candidates.append({
            "id": results["ids"][0][i],
            "topic": results["metadatas"][0][i].get("topic", ""),
            "universe": results["metadatas"][0][i].get("universe", ""),
            "document": results["documents"][0][i],
        })

    if not candidates:
        return json.dumps({"results": []})

    # LLM reranking: ask haiku to pick the most relevant results
    candidates_text = "\n".join(
        f"{i+1}. Topic: {c['topic']} | Universe: {c['universe']} | {c['document']}"
        for i, c in enumerate(candidates)
    )
    n_return = min(top_k, len(candidates))
    rerank_prompt = FEATURE_RERANK_PROMPT_TEMPLATE.format(
        query=query,
        candidates=candidates_text,
        n_return=n_return,
    )

    try:
        rerank_response = sync_client.messages.create(
            model=_RERANK_MODEL,
            max_tokens=1280,
            messages=[{"role": "user", "content": rerank_prompt}],
        )
        rerank_text = rerank_response.content[0].text.strip()
        # Extract JSON array from response
        start = rerank_text.find("[")
        end = rerank_text.rfind("]") + 1
        indices = json.loads(rerank_text[start:end]) if start >= 0 else []
        selected = [candidates[i - 1] for i in indices if 1 <= i <= len(candidates)]
    except Exception:
        # Fall back to top-k by vector distance if reranking fails
        selected = candidates[:n_return]

    matches = [
        {"topic": c["topic"], "universe": c["universe"], "document": c["document"]}
        for c in selected
    ]
    return json.dumps({"results": matches}, default=str)


def get_field_descriptions(table_title: str, year: str = "2019") -> str:
    if year == "2020_redistricting":
        table = f'{DB_PREFIX}."2020_REDISTRICTING_METADATA_CBG_FIELD_DESCRIPTIONS"'
        sql = (
            f"SELECT FIELD_NAME, COLUMN_ID, COLUMN_TOPIC, COLUMN_UNIVERSE "
            f"FROM {table} "
            f"WHERE COLUMN_TOPIC ILIKE '%{table_title}%' "
            f"LIMIT {MAX_ROWS}"
        )
    else:
        table = f'{DB_PREFIX}."{year}_METADATA_CBG_FIELD_DESCRIPTIONS"'
        sql = (
            f"SELECT TABLE_ID, TABLE_NUMBER, TABLE_TITLE, TABLE_TOPICS, TABLE_UNIVERSE, "
            f"FIELD_LEVEL_1, FIELD_LEVEL_2, FIELD_LEVEL_3, FIELD_LEVEL_4, "
            f"FIELD_LEVEL_5, FIELD_LEVEL_6, FIELD_LEVEL_7, FIELD_LEVEL_8 "
            f"FROM {table} "
            f"WHERE TABLE_TITLE ILIKE '%{table_title}%' "
            f"LIMIT {MAX_ROWS}"
        )

    try:
        rows = run_query(sql)
        if not rows:
            return json.dumps({"results": [], "message": f"No fields found for '{table_title}'"})
        return json.dumps({"results": rows}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


_VALID_KNOWLEDGE_TOOLS = {"search_fips_codes", "search_feature_schema", "get_field_descriptions", "execute_sql"}


def fetch_knowledge(tool_name: str) -> str:
    """Return the knowledge/recovery guide for a specific tool."""
    if tool_name not in _VALID_KNOWLEDGE_TOOLS:
        return json.dumps({"error": f"No knowledge file found for tool '{tool_name}'. Available: search_fips_codes, search_feature_schema, get_field_descriptions, execute_sql"})
    knowledge_file = _KNOWLEDGE_DIR / f"{tool_name}.md"
    if not knowledge_file.exists():
        return json.dumps({"error": f"Knowledge file missing for tool '{tool_name}'."})
    content = knowledge_file.read_text(encoding="utf-8")
    return json.dumps({"knowledge": content})


def execute_sql(sql: str) -> str:
    # Only allow SELECT statements for safety
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        return json.dumps({"error": "Only SELECT queries are allowed."})
    try:
        rows = run_query(sql)
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        result = {"results": rows, "row_count": len(rows)}
        if truncated:
            result["note"] = f"Results truncated to {MAX_ROWS} rows."
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Dispatch map
# ---------------------------------------------------------------------------

TOOL_DISPATCH: dict[str, callable] = {
    "search_fips_codes": lambda args: search_fips_codes(
        locations=args["locations"], year=args.get("year", "2019")
    ),
    "search_feature_schema": lambda args: search_feature_schema(
        query=args["query"], year=args.get("year", "2019"), top_k=args.get("top_k", 5)
    ),
    "get_field_descriptions": lambda args: get_field_descriptions(
        table_title=args["table_title"], year=args.get("year", "2019")
    ),
    "execute_sql": lambda args: execute_sql(sql=args["sql"]),
    "fetch_knowledge": lambda args: fetch_knowledge(tool_name=args["tool_name"]),
}
