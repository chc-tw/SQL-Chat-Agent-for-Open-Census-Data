from __future__ import annotations

import json
from typing import Any

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

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_fips_codes",
        "description": (
            "Search FIPS code metadata to resolve a geographic name (state or county) "
            "into FIPS codes. Use ILIKE fuzzy matching on STATE and COUNTY columns. "
            "Returns matching rows with STATE, STATE_FIPS, COUNTY_FIPS, COUNTY."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "geo_name": {
                    "type": "string",
                    "description": "The geographic name to search for (e.g., 'Fulton County', 'Georgia', 'CA').",
                },
                "year": {
                    "type": "string",
                    "enum": ["2019", "2020"],
                    "description": "The dataset year to search in. Defaults to '2019'.",
                },
            },
            "required": ["geo_name"],
        },
    },
    {
        "name": "search_feature_schema",
        "description": (
            "Search for relevant census feature tables by semantic similarity. "
            "Embeds the query and searches the ChromaDB vector store for matching "
            "TABLE_TITLE / TABLE_UNIVERSE pairs. Returns top-K results with topic and universe."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of the census feature (e.g., 'median household income', 'educational attainment').",
                },
                "year": {
                    "type": "string",
                    "enum": ["2019", "2020", "2020_redistricting"],
                    "description": "The dataset year to search in. Use '2020_redistricting' for redistricting-specific features.",
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
            "the Snowflake metadata. Returns all column definitions (TABLE_ID/COLUMN_ID, "
            "field levels) so you can identify the exact column names to use in SQL."
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
            "Results are truncated to 50 rows. If the query fails, the error "
            "message is returned so you can fix and retry."
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
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def search_fips_codes(geo_name: str, year: str = "2019") -> str:
    # Resolve full state names to abbreviations
    search_term = _STATE_ABBREVS.get(geo_name.lower().strip(), geo_name)
    table = f'{DB_PREFIX}."{year}_METADATA_CBG_FIPS_CODES"'
    sql = (
        f"SELECT STATE, STATE_FIPS, COUNTY_FIPS, COUNTY "
        f"FROM {table} "
        f"WHERE STATE ILIKE '%{search_term}%' OR COUNTY ILIKE '%{search_term}%' "
        f"LIMIT 20"
    )
    try:
        rows = run_query(sql)
        if not rows:
            return json.dumps({"results": [], "message": f"No FIPS codes found for '{geo_name}'"})
        return json.dumps({"results": rows}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_feature_schema(query: str, year: str = "2019", top_k: int = 5) -> str:
    """
    Vector search (top 30 candidates) + LLM reranking with claude-haiku-4-5.
    The top_k parameter controls the final number of results returned (default 5).
    """
    collection_map = {
        "2019": "2019_field_metadata",
        "2020": "2020_field_metadata",
        "2020_redistricting": "2020_redistricting_field_metadata",
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
    rerank_prompt = (
        f"You are helping select the most relevant US Census data tables for a query.\n\n"
        f"User query: {query}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        f"Select the {n_return} most relevant candidates for answering this query. "
        f"Return only a JSON array of 1-based indices, e.g. [1, 3, 5]. "
        f"No explanation, just the JSON array."
    )

    try:
        rerank_response = sync_client.messages.create(
            model=_RERANK_MODEL,
            max_tokens=128,
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
        geo_name=args["geo_name"], year=args.get("year", "2019")
    ),
    "search_feature_schema": lambda args: search_feature_schema(
        query=args["query"], year=args.get("year", "2019"), top_k=args.get("top_k", 5)
    ),
    "get_field_descriptions": lambda args: get_field_descriptions(
        table_title=args["table_title"], year=args.get("year", "2019")
    ),
    "execute_sql": lambda args: execute_sql(sql=args["sql"]),
}
