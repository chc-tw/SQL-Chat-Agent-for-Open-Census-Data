# search_fips_codes — Recovery Guide

## No Matches Returned

When a location returns `"matches": []`:
1. Try a shorter or more partial county name (e.g., `"San Diego"` instead of `"San Diego County"`)
2. Try the state abbreviation if you used the full name, or vice versa
3. If both county and state are set but no match, try with only the state to see what counties exist
4. FIPS codes are strings — STATE_FIPS is 2 digits, COUNTY_FIPS is 5 digits (combined state+county)

## Informal Region Names

When the user mentions a multi-county region, batch all counties in a single call:
- Puget Sound: King, Pierce, Snohomish, Kitsap (all WA)
- Inland Northwest: Spokane (WA), Kootenai (ID)
- Bay Area: San Francisco, Alameda, Santa Clara, Contra Costa, San Mateo (all CA)
- Greater Boston: Suffolk, Middlesex, Norfolk, Essex (all MA)

## Ambiguous County Names

Some county names exist in multiple states — always provide the state to disambiguate:
- "Orange County" exists in CA, FL, NY, TX, and others
- "Washington County" exists in nearly every state
- "Jefferson County" exists in 26 states
