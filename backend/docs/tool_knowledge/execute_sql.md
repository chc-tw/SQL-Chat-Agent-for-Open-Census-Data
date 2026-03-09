# execute_sql — Recovery Guide

## Invalid Identifier Error (column not found)

When you see: `SQL compilation error: invalid identifier 'COLUMN_NAME'`

**This almost always means you forgot to double-quote the ACS column name.**

ACS column names are mixed-case (e.g., `B19013e1`, `B03002e1`). Snowflake uppercases all unquoted identifiers, so `B19013e1` becomes `B19013E1`, which does not exist.

**Fix: always double-quote ACS column names in SQL:**
```sql
-- WRONG (Snowflake reads this as B19013E1):
SUM(B19013e1)

-- CORRECT:
SUM("B19013e1")
```

**Recovery steps:**
1. Run `SELECT * FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{same_table}" LIMIT 5` to see the real column names
2. Use the exact column names from that result, wrapped in double-quotes
3. Rewrite your query using only column names confirmed from step 1

## Empty Results

When your query returns 0 rows:
1. Verify the FIPS code is correct — re-run search_fips_codes if unsure
2. Check that FIPS values are zero-padded strings: `'06073'` not `'6073'`
3. Try removing WHERE filters one at a time to find which filter eliminates all rows
4. Confirm the table exists by running `SELECT COUNT(*) FROM {table}`

## Table Not Found

When you see: `Object '{table}' does not exist`
1. Check the full qualified path: `US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"`
2. Verify the table name uses the correct year prefix and TABLE_NUMBER prefix
3. Example: TABLE_NUMBER `B19013` → prefix = first 3 chars = `B19` → table = `2019_CBG_B19`
4. Do NOT use the full TABLE_NUMBER as the table prefix — only the first 3 characters

## Patterns Table Columns

The `2019_CBG_PATTERNS` table columns include:
- `RAW_VISIT_COUNT` — total visits to POIs in the CBG
- `RAW_VISITOR_COUNT` — unique visitors
- `DISTANCE_FROM_HOME` — median distance traveled (JSON)
- `RELATED_SAME_MONTH_BRAND` — same-month brand co-visits (JSON array — not aggregatable directly)
- `BUCKETED_DWELL_TIMES` — visit duration distribution (JSON)

Always use `SELECT * FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_PATTERNS" LIMIT 5` to confirm exact column names before querying.
