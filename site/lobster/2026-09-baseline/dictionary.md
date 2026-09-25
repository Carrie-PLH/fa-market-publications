# Lobster Monitor, Issue 0: September 2026 baseline: data dictionary

Files in this directory hold the record behind the edition. `data.csv` is source-reported data as parsed from the retained files; `measures.csv` is what the edition quotes, including the figures Field Assembly calculated; `numbers.json` and `evidence.json` are the same record as kept in the repository. Values keep the precision they were parsed or computed at; the edition text rounds for display.

Data run: `2026-09-22T201642Z`. Information available as of 22 September 2026. Rows in data.csv: 1080.

License: Field Assembly's tables, calculations and documentation here are CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); cite the edition. Files under `evidence/` are third-party source material and keep their publishers' terms.

## data.csv

One row per series and period, from the data run named above. A series is a monthly (`YYYY-MM`) or weekly (`YYYY-MM-DD`, week ending) series; forecast-table rows from USDA ERS carry no period and are labeled by attribute text in `series_id`.

| Column | Meaning |
|---|---|
| series_id | Identifier. BLS series codes are used as published (for example `WPU02230503`); Field Assembly identifiers are lowercase with underscores and say what was derived (for example `..._usd_per_lb` from value divided by quantity) |
| series_title | Plain description, with the reporting basis (not seasonally adjusted, preliminary, derived) |
| period | Observation period. Monthly `YYYY-MM`; weekly `YYYY-MM-DD` is the week-ending date; empty for forecast-table attributes |
| value | Numeric value as parsed. Empty when the source published a non-numeric marker; the marker is kept in `notes` |
| unit | Unit as reported or as derived: `index`, `USD per lb`, `kg`, `lb`, `USD`, `Percent`, `Percent change`, `cents per dozen` |
| source_id | The source in `sources.json` and on the methodology page |
| source_label | The source's class: OFFICIAL STATISTIC, OFFICIAL MARKET REPORT, or FOOD-COST INDICATOR |
| source_url | URL fetched (the final URL after any redirect) |
| captured_at | Retrieval time, UTC, ISO 8601 |
| evidence_path | The retained file, byte for byte, under `evidence/` in this directory |
| sha256 | SHA-256 of that file |
| notes | Preliminary flags, derivation arithmetic, restatement notes, or the source's own marker text |

Missing values: an empty `value` cell means the source published no numeric value for that period. No value is imputed, interpolated, or carried forward.

## measures.csv

Every figure in `numbers.json`, flattened to one row per leaf with a dotted key. `kind` says whether the row is a Field Assembly calculation or a value or label carried from a source. Calculations:

- `yoy_pct`: (latest − same period a year earlier) ÷ same period a year earlier × 100, rounded to one decimal. The same month for monthly series; for weekly series the week ending nearest to 52 weeks earlier, within four days.
- `vs_two_years_pct`: the same against two years earlier.
- `change_pct` on peaks, annual totals and year-to-date sums: the same formula on the two values named beside it.
- Unit values: dollars divided by quantity, with kilograms converted at 2.20462262 lb per kg where the series says `per lb`. The arithmetic is in the `notes` column of data.csv.
- Annual and year-to-date sums add the monthly rows in data.csv for the months named.
- Averages over a window are unweighted means of the weeks listed beside them.

Index series are indexes, not prices. A change in an index is a change in the index.

## Sources in this data run

| source_id | Source | Class | Page |
|---|---|---|---|
| `maine_dmr_landings` | Maine DMR: lobster landings by month, county, and zone (PDF) | OFFICIAL STATISTIC (annual publication of monthly pounds and value) | https://www.maine.gov/dmr/fisheries/commercial/landings-program/landings-data |
| `noaa_foss_trade` | NOAA Fisheries FOSS trade data: live lobster imports (Homarus spp.) | OFFICIAL STATISTIC (monthly import value; not a retail price) | https://www.fisheries.noaa.gov/foss/f?p=215:2::::: |
| `bls` | U.S. Bureau of Labor Statistics: PPI and CPI series (public API v1) | FOOD-COST INDICATOR (index, not a lobster price) | https://data.bls.gov/timeseries/WPU02230503 |
| `usda_ers_fpo` | USDA ERS Food Price Outlook (CPI forecast table) | FOOD-COST INDICATOR (official forecast table) | https://www.ers.usda.gov/data-products/food-price-outlook |

Reports issued separately by one institution are not independent corroboration of each other.

## observations.csv

Original Field Assembly observations: advertised prices on the public pages of Maine sellers, captured on scheduled dates with page screenshots retained in a private record. Sellers appear by letter; the letter-to-seller mapping is on the methodology page.

| Column | Meaning |
|---|---|
| seller_letter | Seller, as lettered on the methodology page |
| observed_date | Date of capture (UTC) |
| usd_per_lobster | Advertised price for one lobster of the stated specification, US dollars. Counter and pickup sellers only; direct-ship prices, which include shipping, are excluded from this file |
| availability | Availability status as shown on the page at capture, if recorded |
| product_category, shell_type, size_class_lb, quantity, channel | The reference specification. Like is compared with like; no yield or size conversion is applied |

## evidence/

The retained source files with their HTTP response headers (Set-Cookie redacted at capture), and `capture.json` for each source with URL, time and SHA-256. Under `evidence/anchors/`: the timestamp chain entry that covers these files, its manifest of hashes, and the RFC 3161 tokens. A token attests that the entry hash existed at the stated time; it does not attest that any source's figure was correct.
