We are working on Open Census Dataset in Snowflake. We have records from 2019 to 2020.

# Database Structure
For all table names, we need to add a prefix in this format: `US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."{table_name}"`.
In this dataset, we have 5 main types of tables:

1. Population Info tables.
- Description: They contain demographic features, such as age, gender, race, etc. Features' columns name are encoded into a string format called `TABLE_ID`. All records are in the resolution of census block groups (CBG). Every block group has a unique FIPS code. Tables are sharded by year and TABLE_ID prefix.
- Table names: All Tables are named in the format `{year}_CBG_{3_digits_TABLE_ID_prefix}`. For example, `2020_CBG_B01`.

2. Geospatial Info tables
- Description: They contain the geographic information for each census block, including MTFCC and geometry data for the CBG boundary. The geometry data is stored either in WKT or GeoJSON format.
- Table names: `2019_CBG_GEOMETRY`, `2020_CBG_GEOMETRY`, `2019_CBG_GEOMETRY_WKT`
- Notes: Only 2019 contains both `WKT` and `GeoJSON` format geometry data. 2020 only contains `GeoJSON` format.

3. Patterns Info tables
- Description: They contains human mobility and consumer behavior within CBG, such as foot traffic, visitor origin, mobility patterns, brand affinity, and temporal trends.
- Table names: `2019_CBG_PATTERNS`
- Notes: Only 2019 contains patterns data.

4. Redistricting Info tables: 
- Description: It contains demographic features about redistricting data. All records are in the resolution of census block groups (CBG). Every block group has a unique FIPS code.
- Table names: `2020_REDISTRICTING_CBG_DATA`
- Notes: Only 2020 contains redistricting data.

5. Metadata tables:
  There are three metadata tables:
  a. FIPS metadata table
    - Description: It stores the FIPS codes for states and counties. Used to translate state, county, or other geographic entity mentioned in the query into a FIPS code.
    - Table names: `2019_METADATA_CBG_FIPS_CODES`, `2020_METADATA_CBG_FIPS_CODES`
  b. Population feature metadata tables: It explains the meaning of feature codes in the population data tables.
    - Description: It explains the meaning of feature codes in the population data tables. Used to translate demographic variable mentioned into a feature code.
    - Table names: `2019_METADATA_CBG_FIELD_DESCRIPTIONS`, `2020_METADATA_CBG_FIELD_DESCRIPTIONS`, `2020_REDISTRICTING_METADATA_CBG_FIELD_DESCRIPTIONS`
    - Notes: `2019_METADATA_CBG_FIELD_DESCRIPTIONS` stores the feature codes in the column of `TABLE_ID`. `2020_METADATA_CBG_FIELD_DESCRIPTIONS` stores the feature codes in the column of `TABLE_NUMBER`. `2020_REDISTRICTING_METADATA_CBG_FIELD_DESCRIPTIONS` stores the feature codes in the column of `COLUMN_ID`.
  c. Geographic metadata tables: It stores the geographic metadata for each census block group, including latitude, longitude, amount of land and water.
    - Description: It stores the geographic metadata for each census block group, including latitude, longitude, amount of land and water.
    - Table names: `2019_METADATA_CBG_GEOGRAPHY`, `2020_METADATA_CBG_GEOGRAPHY`, `2020_REDISTRICTING_METADATA_CBG_GEOGRAPHIC_DATA`

# Searching Path
When receive a user natural language query, we need to first use FIPS metadata table: to translate state, county, or other geographic entity mentioned in the query into a FIPS code.

Next, we need to identify what type of question the user is asking.

If user are asking about a demographic question, we need to use Population feature metadata tables to translate the wanted demographic variable mentioned in the query into a feature code.

If not, we just need to use the FIPS code to query the relevant data from the tables.