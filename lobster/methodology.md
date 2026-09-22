# Lobster Monitor: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about lobster prices in the United States, from public sources, arranged so a buyer can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| Maine Department of Marine Resources, Commercial Lobster Landings by month | Statewide pounds landed and ex-vessel value by month, 2004 onward. Ex-vessel price per pound is value divided by pounds, computed by Field Assembly and labeled derived. | Published about once a year in February. The latest year is preliminary. |
| NOAA Fisheries FOSS trade data, HTS 0306320010 | Monthly imports of live lobster (Homarus spp.), kilos and dollars, by customs district. Unit value is dollars divided by kilos, converted at 2.20462 lb per kg. Portland, ME is reported separately from all districts. | Monthly, about two to three months behind. Recent months are revised. |
| U.S. Bureau of Labor Statistics, public API v1 | PPI commodity indexes WPU02230503 (lobsters), WPU0223 (unprocessed and prepared seafood), WPUFD4111 (finished consumer foods). CPI-U CUUR0000SEFV (food away from home), CUUR0000SAF11 (food at home). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals by food category, including fish and seafood and food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |

Consumer reference observations come from the Field Assembly observation record: advertised prices on the public pages of eight Maine sellers, captured on scheduled dates with page screenshots and PDFs retained. In issues, sellers appear as letters. The mapping:

| Letter | Seller | Channel |
|---|---|---|
| A | Cousins Maine Lobster (online shop) | direct-ship |
| B | Get Maine Lobster (Portland, ME) | direct-ship |
| C | Greenhead Lobster (Stonington, ME) | direct-ship |
| D | Harbor Fish Market (Portland, ME) | counter, local pickup |
| E | LobsterAnywhere (Maine direct-ship) | direct-ship |
| F | Maine Lobster Now (Saco, ME) | direct-ship |
| G | Pine Tree Seafood & Produce (Scarborough, ME) | counter, local pickup |
| H | Taylor Lobster (Kittery, ME) | counter, priced per pound |

Direct-ship prices usually include overnight shipping and packaging in the listed price. Counter prices do not. The two are never averaged together. The consumer reference row in each issue uses counter sellers only, for one live hard-shell 1.25 lb lobster, so that the figure is a lobster price and not a shipping price.

## Rules

- Compare like with like: product form (live, meat, tail), size class, shell type, quantity, unit, channel, and geography. Live prices are never converted to meat prices. No yield conversion is applied.
- Year-over-year means the same month a year earlier. Seasonal movement within a year is shown but is not the basis for a year-over-year figure.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
