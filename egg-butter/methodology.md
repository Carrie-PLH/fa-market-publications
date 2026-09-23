# Egg & Butter Brief: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about egg and butter prices in the United States, from public sources, arranged so a bakery, pastry shop, or breakfast business can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| U.S. Bureau of Labor Statistics, public API v1 | PPI commodity indexes WPU0171 (chicken eggs) and WPU0232 (butter). CPI-U CUUR0000SEFH (eggs), CUUR0000SS10011 (butter), CUUR0000SEFV (food away from home). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Agricultural Marketing Service, Weekly Combined Regional Shell Egg Report (report 2848) | Weekly average wholesale prices for caged white shell eggs by region, channel and size, in cents per dozen. The issue quotes national delivered-warehouse Large (what a distributor pays) and Midwest paid-to-producers Large (what a farm receives). Each report states the week and the prior week; the year-over-year comparison for this series accumulates in this record from the first capture, September 2026. | Weekly, Friday. |
| USDA Agricultural Marketing Service, Egg Markets Overview (report 3725) | Weekly narrative naming the national loose Large price, the New York cartoned price, inventory and breaking-stock conditions. Retained as evidence; figures quoted from it are entered by the editor and checked against the capture. | Weekly, Friday. |
| USDA Agricultural Marketing Service, National Dairy Products Sales Report (report 2993) | Weighted-average price and pounds sold for butter under mandatory reporting, by week ending Saturday. Full history since 2012 in one request, so year-over-year is available in every issue. Each week is restated in the following four reports; the issue uses the latest restatement and notes the first-published figure when it differs. | Weekly, Wednesday, for the week ending the prior Saturday. |
| USDA Agricultural Marketing Service, Dairy Market News weekly report | CME Group cash market for Grade AA butter: Friday close and weekly average, as reprinted by USDA. CME data is proprietary at source; the USDA reprint is the public record of it. | Weekly, Friday. |
| USDA National Agricultural Statistics Service, Chickens and Eggs | Average layers and table egg production by month, current and prior year. | Monthly, about three weeks after the month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals for eggs, dairy products, fats and oils, and food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |

This title carries no consumer reference row. Retail egg and butter prices are advertised weekly by the same USDA office (Weekly Grocery Store Egg Feature, report 2757) and can be added if a reader's question needs them.

## Rules

- Compare like with like: eggs by size, grade, channel (paid to producer, delivered warehouse, store door) and region; butter by grade and market (mandatory-reporting weighted average, CME cash). Wholesale and retail are never averaged. An index is never converted to a price.
- Year-over-year means the same month a year earlier for monthly series, and the week ending nearest to 52 weeks earlier for weekly series. A trailing four-week average is shown beside the single week because weekly butter prices move with thin volumes.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
