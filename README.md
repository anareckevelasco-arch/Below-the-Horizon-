# Below the Horizon

An awareness project about women's health and PCOS (now renamed PMOS).
A single web page (`index.html`) built from three data sets, cleaned and joined with Python.

## How to run

All the data work is in one file, `below_the_horizon.py`. Put it in the same folder as the raw data and `index.html`, then run:

```
python below_the_horizon.py
```

It runs six steps in order (each step saves files the next one reads):

| Step | Reads | Writes | What it does |
|---|---|---|---|
| 1 | `PCOS_data.csv` (Kaggle) | `pcos_clean.csv`, `cleaning_log.md` | Cleans the Kerala symptom data that grounds the quiz signs |
| 2 | Hologic / Gallup Excel | `hologic_clean.csv.gz`, `hologic_summary.json`, `cleaning_log_hologic.md` | Turns the Excel report into one tidy table |
| 3 | `hologic_summary.json` | `country_facts.json` | Picks one check-up line per country (z-scores) |
| 4 | two IHME CSVs | `pcos_prevalence_clean.csv`, `pcos_prevalence_summary.json`, `cleaning_log_ihme.md` | Cleans PCOS prevalence for 204 countries |
| 5 | outputs of 2, 3, 4 | `map_data.json`, `analysis_log_map.md` | Joins Gallup + IHME by ISO code and tests the conclusion |
| 6 | `map_data.json`, `pcos_prevalence_summary.json` | `index.html` | Copies the results into the page |

Requirements: `pip install pandas numpy scipy openpyxl pycountry`

`pcos_summary.json` (from step 1) was used by an earlier version of the page (the binoculars) and is no longer shown.

## The page

`index.html` is self-contained: no server, no API. It loads two drawing libraries (d3 and topojson-client) from public CDNs, so it needs an internet connection.
The world shapes come from world-atlas (Natural Earth 1:50m), simplified once with:

```
npx toposimplify -p 0.02 countries-50m.json -o world.json
```

## Data sets

- Kottarathil, P. Polycystic ovary syndrome (PCOS). Kaggle, 2020. 541 women, 10 hospitals in Kerala, India.
- Hologic Global Women's Health Index 2020-2024, conducted by Gallup. Women 15+, 144 countries.
- IHME Global Burden of Disease 2023: PCOS prevalence, women 15-49, 204 countries.
