# Cleaning log - IHME GBD 2023, PCOS prevalence

- Countries file: 408 rows, 204 locations. World file: 4 rows.
- Verified filters: prevalence, women, ages 15-49, PCOS, year 2023. (Three earlier downloads had the wrong filters and were discarded.)
- Dropped columns with a single repeated value (population group, measure, sex, age, cause, year ids). Reshaped to one row per country.
- Translated country names to ISO codes: 186 automatically (standard Spanish names), 18 by hand because IHME uses other spellings (e.g. 'Holanda' = Netherlands, 'Suazilandia' = Eswatini). All 204 unique.
- Converted rate per 100,000 to percent and to '1 in N women' for the website.
- World, women 15-49: 64,226,421 cases, 3.26% (uncertainty 2.32-4.46%). Sum of the 204 countries differs from the world total by 0.07%: the files are consistent.
- Caveat: GBD values are modelled estimates, not counts. The uncertainty intervals are wide (world: about 2.3% to 4.5%), and widest where countries have little data.
- Caveat: GBD (about 3 in 100) is lower than the WHO's 8-13 in 100 because sources use different PCOS definitions; the WHO range comes from studies using broader diagnostic criteria. Never mix the two numbers in one comparison.
- Decision: age-standardised rates were not downloaded. Because every country is compared within the same age band (15-49), the comparison is fair without them.
- Final table: 204 countries, 12 columns.