---
Table: US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_GEOMETRY_WKT"

Description: Geographic reference table for 2019 that maps census block group identifiers to their geometry (WKT) and related FIPS/location attributes. Use this table when you need CBG polygon shapes for mapping, spatial joins, or geographic filters.
---
Columns:
STATE_FIPS: State FIPS code for the CBG.
COUNTY_FIPS: County FIPS code for the CBG.
TRACT_CODE: Census tract code within the county.
BLOCK_GROUP: Census block group number within the tract.
CENSUS_BLOCK_GROUP: Full CBG identifier (primary key used to join to other CBG tables).
STATE: State name.
COUNTY: County name.
MTFCC: MAF/TIGER Feature Class Code describing the feature type.
GEOMETRY: CBG geometry in WKT format.