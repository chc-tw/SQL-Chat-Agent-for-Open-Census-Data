---
Table: US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_GEOMETRY"

Description: Geographic reference table for 2019 Census Block Groups (CBGs). Use this table when you need to map a CBG identifier to its geometry or geographic attributes, perform spatial joins, or retrieve CBG boundary data for mapping and analysis.
---
Columns:
STATE_FIPS: State FIPS code for the CBG.
COUNTY_FIPS: County FIPS code for the CBG.
TRACT_CODE: Census tract code within the county.
BLOCK_GROUP: Census block group code within the tract.
CENSUS_BLOCK_GROUP: Full CBG identifier (primary key for joining to other CBG tables).
STATE: State name.
COUNTY: County name.
MTFCC: MAF/TIGER feature class code describing the geometry.
GEOMETRY: Geometry data for the CBG boundary.