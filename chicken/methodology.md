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

### What the series actually price

Report 3649 names each cut in a word or two and states less about it than a buyer's specification would. These specifications come from the retained reports themselves and are quoted here so a figure in an issue can be matched to a product. The report sets every row under a heading that gives the product group, the market, fresh or frozen, the word "Conventional", and the delivery basis, and the record keeps each row under its heading, so the same cut under another heading is another series. For no cut does the report state a grade, a pack, a trim or a size, and it does not define "Conventional" or spell out its abbreviations "B/S" and "WOG". Each row carries a price range, a weighted average ("Wtd Avg") and the pounds traded ("1,000 lbs"); the report does not say what the average is weighted by or which sales it includes.

| Series | Specification as the report states it |
|---|---|
| Boneless skinless breast, report 3649 | The row "Breast - B/S" among the parts. Domestic, fresh, conventional, FOB. Not frozen, not delivered, and not the line-run breast or the breast with ribs, which the report prices on rows of their own. |
| Tenderloins, same report | The row "Tenderloins". Domestic, fresh, conventional, FOB. Not frozen, not delivered. |
| Whole wings, same report | The row "Wings - Whole". Domestic, fresh, conventional, FOB. The report carries no row for wing portions, so this is not a price for cut wings. |
| Drumsticks, same report | The row "Drumsticks". Domestic, fresh, conventional, FOB. Not bone-in legs, which the report prices separately as "Legs - Bone-in". |
| Leg quarters, same report | The row "Leg quarters - Bulk". Domestic, fresh, conventional, FOB, and bulk as the row says; the report does not say what the bulk pack is. A domestic price: the report's export rows carry no leg quarters. |
| Thighs, same report | Two rows, "Thighs - Bone-in" and "Thighs - B/S", kept as two series. Domestic, fresh, conventional, FOB. The bone-in row trades the fewest pounds of any row in the report, so its average rests on very little volume. |
| National composite whole bird, same report | The row "National Composite Whole Bird" among the whole birds. Domestic, fresh, conventional, and delivered, where every parts row above is FOB, so the whole bird and the parts are not priced on one delivery basis. The report does not say what the composite combines; in each retained report its pounds equal the WOG and whole-body national composites added together, and its price is their pound-weighted average. Not a price for any one bird size, which the report gives on rows of its own. |
| Reporting month, same report | The report states its period as "Report For:" a start and an end date. Its month is a block of whole weeks that can begin in one calendar month and end in the next: the September 2026 report covers 8/31/2026 to 10/2/2026. The record files each block under the month holding most of its days. |
| Young chickens slaughtered, NW_PY002 | Young chickens slaughtered under federal inspection, counted in thousands of head, in four weight classes in pounds, with an average live weight for each class and for the total. Birds and live weight, not pounds of meat. The report says the lightest class is normally marketed bone-in into fast food and food service and may include Cornish hens, and the heaviest is normally marketed deboned or as roasters. Its year-ago figure is a "comparable week" it does not date. The week is marked preliminary, and the record holds the figure as first published. |
| Broiler composites, ERS retail price file | Three items named "Wholesale broiler composite", "Retail broiler composite" and "Wholesale-retail broiler spread", in cents per pound, with ERS as their source. The file does not say which cuts or weights make up either composite, or at what point the wholesale composite is priced. The wholesale composite is not the report 3649 national composite whole bird, and the spread is the difference between two composites, not anyone's margin. |

An issue states the specification in its own text where a reader could otherwise take a figure for a product it does not price.

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
