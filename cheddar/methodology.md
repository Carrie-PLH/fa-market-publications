# Cheddar Check: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about cheddar cheese prices in the United States, from public sources, arranged so a pizzeria, sandwich shop, or caterer can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Two block prices, and why the difference matters

A supplier who says the block market moved may mean either of two things, and they are not the same number.

The first is the CME Group cash market: a spot market for immediate loads, quoted daily, reprinted by USDA. The second is the National Dairy Products Sales Report: what cheese manufacturers actually sold at during a week, collected under mandatory reporting, published with a lag. The spot market is thinly traded and moves fast; the mandatory report is broad and moves slowly behind it. In the September 2026 baseline the two were about twenty cents a pound apart.

Each issue reports both, each with its own date, and never averages them. Where this record holds both series for the same week, it also reports the arithmetic difference, labeled derived. The difference is not a margin and is not presented as one.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| USDA Agricultural Marketing Service, National Dairy Products Sales Report (report 2993), 40-pound block cheddar | Weighted-average price and pounds sold under mandatory reporting, by week ending Saturday. Full history since 2012 in one request, so year-over-year is available in every issue. Each week is restated in the following four reports; the issue uses the latest restatement and notes the first-published figure when it differs. | Weekly, Wednesday, for the week ending the prior Saturday. |
| USDA Agricultural Marketing Service, same report, 500-pound barrel cheddar | A historical series. It ran from 2012 and carries no published price after the week ending 2025-05-31; every row since is null. It is captured and parsed so that the record shows when it stopped, and it is never used as a current price. | Ceased. |
| USDA Agricultural Marketing Service, Dairy Market News weekly report | CME Group cash market for cheese: barrels and 40-pound blocks, Friday close and weekly average, as reprinted by USDA. CME data is proprietary at source; the USDA reprint is the public record of it. Each report carries one week, so this series accumulates in this record one week per run and no history is available in a single request. | Weekly, Friday. |
| U.S. Bureau of Labor Statistics, public API v2 | PPI commodity index WPU023302 (natural cheese, except cottage cheese). CPI-U CUUR0000SEFJ02 (cheese and related products) and CUUR0000SEFV (food away from home). Average prices in dollars per pound: APU0000710212 (natural cheddar), APU0000710211 (American processed). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals for dairy products and for food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |

This title fetches and retains its own copies of the National Dairy Products Sales Report and the Dairy Market News report, which the Egg & Butter Brief also fetches, so that each edition's evidence package stands alone and can be verified without reference to another title.

### What the weekly series actually price

The block and barrel series above are narrower than the word "cheddar", and a buyer whose product differs should read them with that in mind. These specifications come from the reports themselves and are quoted here so a figure in an issue can be matched to a product. Where a report does not state an attribute, the table says so.

| Series | Specification as the report states it |
|---|---|
| 40-pound block price, National Dairy Products Sales Report | Cheddar cheese in 40-pound blocks, colored between 6 and 8 on the National Cheese Institute color chart, meeting Wisconsin State Brand, USDA Grade A, or better standards. The figure is a weighted average of the prices reporting manufacturers received, in dollars per pound, for the week ending Saturday. The report states no age, moisture content or pricing point for the cheese; it refers its definitions to the program regulations (7 CFR 1170) and to the questionnaire manufacturers complete, and this record retains neither. Not barrels, not cut, shredded or sliced cheese, and not any variety other than cheddar. |
| 40-pound block volume, same report | The pounds sold in the week by the manufacturers required to report, which the report of October 21, 2026 numbers at 17 for 40-pound blocks, among 63 entities each selling one million pounds or more of dairy products. It is not total cheddar sold or produced in the United States. |
| 500-pound barrel price, same report | Cheddar cheese in 500-pound barrels. The source section is titled "500 Pound Barrel Cheddar Cheese Prices, Sales, and Moisture Content" and carries two price columns and a weighted moisture column. The retained file names them only by column and does not say which price, if either, is adjusted to a moisture basis, or to what basis. This record reads the column named `cheese_500_Price`. The last published price is for the week ending 2025-05-31, and the current report's list of the products it collects does not include barrels. |
| CME 40-pound blocks, Dairy Market News | The CME Group cash market price for cheese in 40-pound blocks, in dollars per pound in carlot quantities, a carlot of cheese being 40,000 to 44,000 pounds. The reprint states no grade, color, age, moisture content or delivery point for the cheese, and this record does not retain CME's own terms. |
| CME barrels, same report | The same market's barrel price, in the same unit and carlot quantities. The reprint labels the row "Barrels" and states no barrel weight, grade or moisture basis. It is a current quote, and a different measure from the 500-pound barrel series above, which stopped. |
| Friday close and weekly average, both CME series | The reprint's week runs Monday to Friday. The Friday close is the closing price in the reprint's Friday column. The weekly average is, in the reprint's words, the simple average of the daily close prices for the calendar week, computed by Dairy Market News: an average of closing prices, not weighted by the number or size of trades. |

An issue states the specification in its own text where a reader could otherwise take a figure for a product it does not price.

## Rules

- Compare like with like: cheese by form (40-pound block, 500-pound barrel), by market (mandatory-reported sales, CME cash), and by grade. A spot quote and a mandatory-reported weighted average are never averaged together. Wholesale and retail are never averaged. An index is never converted to a price.
- A weighted average is reported with the pounds it was weighted by.
- Year-over-year means the week ending nearest to 52 weeks earlier, within four days, for weekly series, and the same month a year earlier for monthly series. A trailing four-week average is shown beside the single week.
- A comparison that requires two series to cover the same week is reported only once both do. Where the record cannot yet make it, the issue says so and says why, rather than comparing two different weeks.
- A series that has stopped being published is reported as having stopped, with the date of its last figure. Its last value is never carried forward.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing. A week published as null is a gap, never a zero.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## What this record cannot show

Cheddar is not mozzarella, and a pizzeria buys more of the second than the first. The mandatory report covers cheddar in two specific forms because those are what the statute requires reported; the block price is used across the dairy complex as a reference, but it is not a price for any other cheese. Mandatory reporting covers manufacturers above a size threshold, not every seller. Nothing here establishes why a particular supplier quoted a particular price.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

The BLS request carries a free registration key. The key is read from the environment at fetch time and is never written into a capture file, a data file, or this repository. A response body that repeats the key is discarded and the fetch recorded as failed, so a rejected credential cannot enter the record.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
