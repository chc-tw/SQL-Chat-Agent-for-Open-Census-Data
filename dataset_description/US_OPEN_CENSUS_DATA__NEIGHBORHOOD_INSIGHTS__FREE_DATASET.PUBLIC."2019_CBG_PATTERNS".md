---
Table: US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2019_CBG_PATTERNS"

Description: Foot traffic patterns and visit aggregates for 2019 Census Block Groups (CBGs). Use this table when the user asks about visits, visitors, origins of visitors, popular brands, or temporal popularity patterns for a CBG.
---
Columns:
CENSUS_BLOCK_GROUP: Census Block Group identifier (primary key for joining to CBG-level data).
DATE_RANGE_START: Start date of the observation window for the pattern metrics.
DATE_RANGE_END: End date of the observation window for the pattern metrics.
RAW_VISIT_COUNT: Total number of recorded visits in the date range.
RAW_VISITOR_COUNT: Total number of unique visitors in the date range.
VISITOR_HOME_CBGS: Distribution of visitors' home CBGs (origin CBGs).
VISITOR_WORK_CBGS: Distribution of visitors' work CBGs.
DISTANCE_FROM_HOME: Distance distribution between visit locations and visitors' home locations.
RELATED_SAME_DAY_BRAND: Brands frequently co-visited on the same day.
RELATED_SAME_MONTH_BRAND: Brands frequently co-visited within the same month.
TOP_BRANDS: Most-visited brands associated with the CBG.
POPULARITY_BY_HOUR: Hourly visit distribution.
POPULARITY_BY_DAY: Daily visit distribution (e.g., day of week).