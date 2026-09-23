# Egg & Butter Brief

**Issue 0: September 2026 baseline**
Field Assembly Market Publications · SCAFFOLD, not a draft · Data run `2026-09-23T124524Z`

<!-- Scaffold written by tools on 2026-09-23. The editor writes each section from numbers.md. No figure may appear in the prose that is not in numbers.json. Publication of this issue is gated by FA-D-20260923-01: not before Lobster Monitor's first post-baseline issue or a first paid subscription. -->

This issue sets the baseline. Later issues report what changed against it. It is written for anyone facing a supplier's egg or butter price claim: a bakery quoted an increase, a pastry shop asked to accept a surcharge, a breakfast business comparing distributors. It reports market evidence. It does not estimate any supplier's cost and draws no conclusion about any contract.

## The read

<!-- Three paragraphs. What egg-specific and butter-specific prices did against a year ago; the longer picture (the 2025 egg peak and how far prices have fallen from it: numbers.json ppi_chicken_eggs_24m_peak); seasonality and the dates a claim compares. -->

## The numbers

| Measure | Latest | Same period, prior year | Change | Source |
|---|---|---|---|---|
| PPI, chicken eggs (index) | 149.0 (2026-08) | 367.0 (2025-08) | -59.4% | BLS WPU0171 |
| CPI, eggs (index) | 276.5 (2026-08) | 359.1 (2025-08) | -23.0% | BLS CUUR0000SEFH |
| PPI, butter (index) | 105.4 (2026-08) | 172.0 (2025-08) | -38.7% | BLS WPU0232 |
| CPI, butter (index) | 293.8 (2026-08) | 320.2 (2025-08) | -8.3% | BLS CUUR0000SS10011 |
| CPI, food away from home (index) | 397.9 (2026-08) | 384.9 (2025-08) | +3.4% | BLS CUUR0000SEFV |
| Average layers during the month (thousand) | 382,801 (2026-08) | 366,028 (2025-08) | +4.6% | USDA NASS Chickens and Eggs |
| Table egg production (million eggs) | 8,121.6 (2026-08) | 7,662.8 (2025-08) | +6.0% | USDA NASS Chickens and Eggs |
| Butter, wholesale weighted average ($/lb, week ending) | 1.4920 (2026-09-12) | 2.1400 (2025-09-13) | -30.3% | USDA AMS NDPSR |
| Butter, wholesale weighted average, trailing 4-week ($/lb) | 1.4829 | 2.3111 | -35.8% | USDA AMS NDPSR |
| CME Grade AA butter, weekly average ($/lb, week ending) | 1.3590 (2026-09-18) | — | — | CME via USDA AMS Dairy Market News |
| Shell eggs, Large, national delivered warehouse (cents/dozen, week ending) | 72.94 (2026-09-19; prior week 73.94) | — (—) | — | USDA AMS report 2848 |
| Shell eggs, Large, Midwest paid to producers (cents/dozen, week ending) | 47.00 (2026-09-19; prior week 48.00) | — (—) | — | USDA AMS report 2848 |

<!-- Two-year comparisons where the record allows them: see vs_two_years_pct in numbers.json. -->

## The explanation

<!-- Farm price, delivered wholesale price, retail index: the same egg at three points in the chain. Butter: mandatory-reporting weighted average against the CME cash market. Supply: layers and production against a year ago (nass_layers_avg, nass_table_egg_production). USDA outlook: ers_food_price_outlook. -->

## The uncertainty

<!-- The weekly shell egg series has no year-ago row until September 2027; only the prior week is in the report. NDPSR weeks are restated for four weeks. CME figures are USDA's reprint. Indices are not prices. -->

## The buyer's question

<!-- Which product (size, grade, channel; butter grade and pack); which dates; which evidence. -->

## The record

Sources and retrieval, run `2026-09-23T124524Z`:

- bls / WPU0171: https://api.bls.gov/publicAPI/v1/timeseries/data/WPU0171 (fetched 2026-09-23T12:45:24Z, OK)
- bls / WPU0232: https://api.bls.gov/publicAPI/v1/timeseries/data/WPU0232 (fetched 2026-09-23T12:45:26Z, OK)
- bls / CUUR0000SEFH: https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SEFH (fetched 2026-09-23T12:45:28Z, OK)
- bls / CUUR0000SS10011: https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SS10011 (fetched 2026-09-23T12:45:31Z, OK)
- bls / CUUR0000SEFV: https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SEFV (fetched 2026-09-23T12:45:33Z, OK)
- ams_shell_egg / pdf: https://www.ams.usda.gov/mnreports/ams_2848.pdf (fetched 2026-09-23T12:45:35Z, OK)
- ams_egg_overview / pdf: https://www.ams.usda.gov/mnreports/ams_3725.pdf (fetched 2026-09-23T12:45:37Z, OK)
- ams_ndpsr / butter: https://mpr.datamart.ams.usda.gov/services/v1.1/reports/2993/Butter%20Prices%20and%20Sales (fetched 2026-09-23T12:45:40Z, OK)
- ams_ndpsr / pdf: https://www.ams.usda.gov/mnreports/dywdairyproductssales.pdf (fetched 2026-09-23T12:45:43Z, OK)
- ams_dmn_weekly / pdf: https://www.ams.usda.gov/mnreports/dywweeklyreport.pdf (fetched 2026-09-23T12:45:46Z, OK)
- nass_chickens_eggs / txt: https://www.nass.usda.gov/Publications/Todays_Reports/reports/ckeg0926.txt (fetched 2026-09-23T12:45:49Z, OK)
- usda_ers_fpo / landing: https://www.ers.usda.gov/data-products/food-price-outlook (fetched 2026-09-23T12:45:52Z, OK)
- usda_ers_fpo / cpi_csv: https://www.ers.usda.gov/media/6460/changes-in-consumer-price-indexes-2024-through-2027.csv?v=17526 (fetched 2026-09-23T12:45:54Z, OK)

Method: every figure in this issue appears in `numbers.json`, regenerated from the data files by `tools/issue.py`. Every capture file, its URL, retrieval time, and SHA-256 are listed in `evidence.json`. Capture files are hashed into an external timestamp chain (RFC 3161 and OpenTimestamps) that proves they existed unchanged by the anchor date. An external timestamp shows when a captured record existed. It does not show that a source's figure was correct or that a quoted price was available to every buyer.

Corrections: none.

Next issue: after the Bureau of Labor Statistics releases September producer price indexes in mid-October 2026.
