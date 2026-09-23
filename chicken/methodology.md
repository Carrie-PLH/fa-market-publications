# Chicken Monitor: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about chicken prices in the United States, from public sources, arranged so a restaurant, caterer, or food-service buyer can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| U.S. Bureau of Labor Statistics, public API v2 | PPI commodity indexes WPU0141 (slaughter chickens) and WPU022203 (young chickens, whole and in parts, after processing). CPI-U CUUR0000SEFF01 (chicken) and CUUR0000SEFV (food away from home). Average prices in dollars per pound: APU0000706111 (fresh whole chicken), APU0000FF1101 (boneless breast), APU0000706212 (bone-in legs). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Agricultural Marketing Service, Monthly National Chicken Report (report 3649) | Volume-weighted average wholesale prices in cents per pound, with the pounds traded behind each one, by cut and by market: boneless skinless breast, tenderloins, whole wings, drumsticks, leg quarters, bone-in and boneless thighs, and the national composite whole bird. Each report states the current and previous month; the year-over-year comparison for this series accumulates in this record from the first capture, September 2026. | Monthly, first business day, for the month just ended. |
| USDA Agricultural Marketing Service, Weekly Young Chickens Slaughtered Under Federal Inspection (NW_PY002) | Head slaughtered by live-weight class and average live weight, with the comparable week a year earlier and year-to-date totals for both years as the report states them. | Weekly, Thursday, for the week ending the prior Saturday. Preliminary when so marked. |
| USDA Economic Research Service, retail prices for beef, pork and poultry cuts | The ERS wholesale broiler composite, the retail broiler composite, and the spread between them, monthly, in cents per pound. | Monthly, about four weeks after the month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals for poultry, for meats, poultry and fish, and for food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |
| USDA Agricultural Marketing Service, National Broiler Market At-a-Glance (report 2740) | Daily narrative on supply, demand and movement by cut, domestic and export. Retained as evidence; figures quoted from it are entered by the editor and checked against the capture. | Daily. |

Two notes on what is not double counted. The ERS retail file also carries chicken retail prices, but those rows are BLS average prices restated by ERS; this publication takes only the three broiler composites, which ERS computes itself, and quotes the BLS average prices from BLS. Separately issued reports from one institution are not treated as independent corroboration of each other.

## Rules

- Compare like with like: chicken by cut, by market (domestic or export), by state (fresh or frozen), and by delivery basis (FOB or delivered). Wholesale and retail are never averaged. A whole-bird price and a boneless breast price are never combined. An index is never converted to a price.
- A weighted average is reported with the volume it was weighted by, because a thinly traded cut and a heavily traded one do not carry the same weight of evidence.
- Year-over-year means the same month a year earlier for monthly series. Where a source states its own year-ago figure, that figure is recorded as the source's statement and named as such in the series title, because the report does not give the date of the week it is comparing against.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## What this record cannot show

Live-weight slaughter and ready-to-cook product are different things, and a change in average live weight changes how much meat a given number of birds yields. Weekly slaughter figures marked preliminary are revised. The forward availability figures USDA publishes from chick placements are estimates USDA makes, not measurements, and are not used here. Nothing in this record establishes why a particular supplier quoted a particular price.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

The BLS request carries a free registration key. The key is read from the environment at fetch time and is never written into a capture file, a data file, or this repository; the retained record of the request names the variable it came from and not its value.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
