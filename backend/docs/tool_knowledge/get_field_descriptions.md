# get_field_descriptions — Recovery Guide

## No Fields Found

When the tool returns `"No fields found for '{table_title}'`:
1. Try a shorter search term (e.g., `"INCOME"` instead of `"MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS"`)
2. Try an alternate keyword — ACS table titles use formal Census language:
   - Internet → `"INTERNET SUBSCRIPTIONS"` or `"PRESENCE AND TYPES OF INTERNET"`
   - Self-employment → `"SELF-EMPLOYMENT INCOME"`
   - Elderly households → `"PRESENCE OF PEOPLE 60 YEARS"`
   - Children households → `"PRESENCE OF PEOPLE UNDER 18"`
3. Query the metadata table directly to browse titles:
```sql
SELECT DISTINCT TABLE_TITLE, TABLE_NUMBER
FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_METADATA_CBG_FIELD_DESCRIPTIONS"
WHERE TABLE_TITLE ILIKE '%keyword%'
LIMIT 20
```

## Reading the Output

- `TABLE_NUMBER` determines the data table: prefix = first 3 chars (e.g., `B19013` → `B19` → table `2019_CBG_B19`)
- Column names in SQL are the `TABLE_ID` values — use the exact string from the TABLE_ID column, do not alter case or add/remove underscores
- **CRITICAL: Always double-quote column names in SQL.** ACS column names are mixed-case (e.g., `B19013e1`). Snowflake uppercases unquoted identifiers, causing "invalid identifier" errors. Use `"B19013e1"` not `B19013e1`.
- `FIELD_LEVEL_1` through `FIELD_LEVEL_8` describe the demographic breakdown — use these to identify which column answers the question
- `e` columns = estimates, `m` columns = margin of error. Default to `e` columns.

## Year Differences

- `2019` and `2020`: use `year="2019"` or `year="2020"`, search by `TABLE_TITLE`
- `2020_redistricting`: use `year="2020_redistricting"`, search by `COLUMN_TOPIC` (not TABLE_TITLE)
