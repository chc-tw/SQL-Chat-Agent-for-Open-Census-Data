This is the final implementation guide for the **Open Census Text-to-SQL Agent**. We want to build a chat agent to answer any question about the Open Census dataset. It is designed for engineers building with native LLM API SDKs (Anthropic SDK) and will guide you to construct a highly robust agent system.

---

# Open Census Text-to-SQL Agent Implementation Guide

## 0. Agent Architecture Pattern: ReAct Pattern

This system adopts the **ReAct (Reasoning + Acting)** pattern. The agent does not merely generate answers; it solves problems through a loop of “Think (Reason) -> Act (Tool Call) -> Observe”.

### Core Implementation Logic

Because you are using a native API SDK, you must maintain a `messages` array as state and continuously append new `ToolOutput` in the loop.

* **State Management:**
* `messages`: includes System Prompt, User Query, Assistant Thoughts, Tool Calls, Tool Outputs.
* `context`: accumulated FIPS codes, table schemas, SQL fragments.

* **ReAct Loop:**
1. **Thought:** The model analyzes the current state and decides the next step (do we need FIPS lookup? feature lookup? write SQL?).
2. **Action (Function Call):** The model calls a defined tool (e.g., `search_geo_fips`, `retrieve_feature_schema`, `execute_snowflake_sql`).
3. **Observation:** The system executes the tool and returns results (JSON or String) to the model.
4. **Reflection:** If the tool fails or returns empty, the model should self-correct parameters in the next Thought.

* **Context Management:**
- During development, always check whether the current step requires additional knowledge (e.g., database knowledge, operational logic). If so, do not embed it in the agent’s runtime logic; instead, write separate `.md` files to load as needed.
- Always be mindful of each agent’s context; do not pass context that the agent does not need.

---

## Phase 0:
**Objective:** 

Before everything starts, we need a guardrails to prevent malicious or irrelevant questions from user.

---

## Phase 1: Intent Identification & Resource Planning

**Objective:** Parse the user’s natural language into a structured query plan.

### Steps:

1. **Receive Input:** User Query.
2. **LLM Analysis (Router):** Call a structured-output tool (or use JSON mode).
3. **Output Spec (JSON):**
* `intent`: query intent (e.g., `retrieval`, `ranking`, `correlation`).
* `year`: target year (default to latest dataset year).
* `geo_level`: geographic level (e.g., `state`, `county`, `census_block_group`).
* `domains`: data domains involved (List: `['population', 'patterns', 'geometry', 'redistricting_population']`).
* `raw_geo_entities`: extracted geo terms. Because the resolution of record is county-level or state-level, if user provides a city name, list all counties in that city. 
* `raw_feature_concepts`: extracted feature keywords (e.g., `["median household income", "bachelor degree"]`).

---

## Phase 2: Entity Resolution & Schema Linking

This phase is the key to accuracy and must handle **geographic entities** and **data features** in parallel.

### 2.1 Geo-Resolution

**Objective:** Convert ambiguous geographic names into precise FIPS code prefixes.

**Implementation Details:**

1. **Tool Definition (`search_fips_codes`):**
* Parameters: `geo_name`, `geo_level`.

2. **Execution Logic:**
* Query the `FIPS_CODES` metadata table in Snowflake.
* Prefer fuzzy matching with `ILIKE`, or rank by `JAROWINKLER_SIMILARITY`.
* **Key requirement:** Return both FIPS code and its level. Example: “Fulton County” should return `13121` (State+County).

3. **Observation:** Obtain a clear list of FIPS codes.
4. **Implementation Detail:** FIPS Zero-Padding — the most common bug. FIPS codes are strings and must preserve leading zeros (e.g., `06` for California, not `6`). Ensure both Python and SQL treat them as strings.

### 2.2 Feature Retrieval (Hierarchical RAG)

**Objective:** From thousands of Census columns, accurately identify the needed `COLUMN_ID` and `TABLE_PREFIX`.

**Implementation Details (Revised Flow):**

1. **Step A: Concept Search via Embeddings**
* **Preparation:** Combine `TABLE_TITLE` and `TABLE_UNIVERSE` from the metadata table into a description, compute embeddings, and store in a vector DB.
* **Execution:** Convert `raw_feature_concepts` into a vector and search the vector DB.
* **Output:** Top-K most relevant `(Table Title, Table Universe)` pairs (e.g., “Sex by Age”).

2. **Step B: Detailed Schema Lookup**
* **Execution:** Use the Table Title/Universe from Step A to query the SQL metadata table (`METADATA_CBG_FIELD_DESCRIPTIONS`) for all rows under that concept.
* **Output:** All column definitions under that table (e.g., `B01001e1: Male: 5 to 9 years`, `B01001e2: Male: 10 to 14 years`). Typically dozens of fields.

3. **Step C: LLM Precise Selection**
* **Prompt:** Put the detailed field list from Step B into context.
* **Instruction:** “User asks for '{raw_feature_concepts}'. From the list below, select the exact `COLUMN_ID` and extract its `TABLE_ID` prefix (first 3 chars after 'CBG_').”
* **Output:** The selected `COLUMN_ID` (e.g., `B19013e1`) and `TABLE_PREFIX` (e.g., `B19`).

---

## Phase 3: Dynamic SQL Generation

**Objective:** Generate Snowflake-compatible SQL that handles sharding based on the gathered context.

**Prompt Strategy:**
You must define SQL Writer rules clearly in the System Prompt:

1. **Table Naming Rule (Sharding):**
* Table name format: `{year}_CBG_{table_prefix}`.
* Example: Year=2019, Prefix=B19 -> `FROM 2019_CBG_B19`.

2. **Join Logic:**
* If multiple domains are involved (e.g., Population `B19` + Patterns), `JOIN` on `census_block_group`.
* Geography tables typically join on `geo_id` or `fips`.

3. **Aggregation Rule:**
* If the requested `geo_level` (e.g., County) is higher than the native CBG level, generate `SUM()` or `AVG()` with `GROUP BY SUBSTR(fips_col, 1, 5)`.

4. **Column Selection:**
* Strictly distinguish Estimate (`e`) vs Margin of Error (`m`). Default to `e` columns only.

---

## Phase 4: Execution & Reflection Loop

**Objective:** Execute SQL and handle errors to ensure correctness.

### Loop Logic:

1. **Execute Tool (`execute_sql`):**
* Send the generated SQL to Snowflake.

2. **Observation & Correction Strategy:**
* **Scenario A: SQL Syntax Error / Object Not Found**
  * **Action:** Feed the full error message back to the LLM.
  * **Instruction:** “SQL execution failed. Fix the SQL based on the error message. Check table naming against `{year}_CBG_{prefix}`.”

* **Scenario B: Empty Result (0 rows)**
  * **Action:** Trigger reflection.
  * **Instruction:** “Result is empty. Possible causes: wrong FIPS code or overly strict WHERE clause. Try removing non-essential filters or re-check FIPS code (go back to Step 2.1).”

* **Scenario C: Data Consistency Check (Sanity Check)**
  * **Action:** Basic logic checks (e.g., population < 0?).
  * **Instruction:** “Values are abnormal. Check if the wrong column was selected (e.g., picked Margin of Error `m`).”

* **Scenario D: Success**
  * **Action:** Exit the loop and generate the final response.

3. **Termination Conditions:**
* Data successfully retrieved.
* Max retries reached (recommended 3).

---

## 5. Final Response Generation

**Objective:** Convert SQL results into human-readable answers.

* **Input:** Original User Query + final SQL + SQL results (Dataframe/JSON).
* **Prompt Requirements:**
  * Answer directly and accurately.
  * (Optional) Briefly explain the data source (e.g., “Based on 2019 ACS data...”).
  * Output in Markdown.

