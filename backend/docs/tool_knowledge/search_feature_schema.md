# search_feature_schema — Recovery Guide

## Empty Results

When `search_feature_schema` returns `{"results": []}`:

**Option A — Use get_field_descriptions as fallback**

Call `get_field_descriptions` with a known ACS table title. Common titles to try:
- Income: `MEDIAN HOUSEHOLD INCOME IN THE PAST 12 MONTHS`
- Self-employment income: `AGGREGATE SELF-EMPLOYMENT INCOME`
- Internet: `PRESENCE AND TYPES OF INTERNET SUBSCRIPTIONS IN HOUSEHOLD`
- Internet computers: `COMPUTERS IN HOUSEHOLD`
- Age/sex: `SEX BY AGE`
- Race: `RACE`
- Housing tenure: `TENURE`
- Education: `EDUCATIONAL ATTAINMENT FOR THE POPULATION 25 YEARS AND OVER`
- Households with elderly: `HOUSEHOLDS BY PRESENCE OF PEOPLE 60 YEARS AND OVER BY HOUSEHOLD TYPE`
- Households with children: `HOUSEHOLDS BY PRESENCE OF PEOPLE UNDER 18 YEARS BY HOUSEHOLD TYPE`

**Option B — Query the metadata table directly**

Run SQL against the field descriptions table:
```sql
SELECT DISTINCT TABLE_TITLE, TABLE_NUMBER
FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_METADATA_CBG_FIELD_DESCRIPTIONS"
WHERE TABLE_TITLE ILIKE '%income%'
LIMIT 20
```
Replace `%income%` with the relevant keyword. This always works even when ChromaDB is unavailable.

## Wrong Collection

If you searched `2019` or `2020` but need patterns data, use `2019_patterns` collection.
If you searched `2019_patterns` but need demographic data, use `2019` or `2020`.

Patterns columns (use collection `2019_patterns`):
- Visit counts, visitor counts, dwell times, distance from home, brand co-visits

Demographic columns (use collection `2019` or `2020`):
- Income, age, race, housing, education, employment, internet access
