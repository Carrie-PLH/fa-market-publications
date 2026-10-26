# Pork Monitor: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about pork prices in the United States, from public sources, arranged so a restaurant, barbecue business, or caterer can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| USDA Agricultural Marketing Service, National Weekly Pork Report FOB Plant, comprehensive (report 2680) | The pork carcass cutout in dollars per hundredweight and each of the six primals separately: loin, butt, picnic, rib, ham and belly, under mandatory price reporting. The whole series comes in one request, so year-over-year is available in every issue. | Weekly, Monday, for the week ending the prior Friday. |
| USDA National Agricultural Statistics Service, Quarterly Hogs and Pigs | All hogs and pigs, the breeding herd, and market hogs by weight group, both years with NASS's own percent-of-previous-year column. | Quarterly, late March, June, September and December. |
| U.S. Bureau of Labor Statistics, public API v2 | PPI commodity indexes WPU0132 (slaughter hogs) and WPU02210444 (pork, fresh and frozen, unprocessed, all cuts, made in slaughtering plants). CPI-U CUUR0000SEFD (pork) and CUUR0000SEFV (food away from home). Average prices in dollars per pound: APU0000FD3101 (all pork chops), APU0000704111 (sliced bacon). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals for pork, for meats, and for food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |
| USDA Agricultural Marketing Service, Weekly Pork and Beef Variety Meat Report | Variety meats and the week's trading context. Retained as evidence; figures quoted from it are entered by the editor and checked against the capture. | Weekly. |

### What the weekly series actually price

The cutout and the six primals are narrower than the word "pork", and none of them is the price of a cut a buyer orders. A buyer whose product is a particular cut should read them with that in mind. These specifications come from the reports themselves and are quoted here so a figure in an issue can be matched to a product.

| Series | Specification as the report states it |
|---|---|
| Pork carcass cutout, report 2680 | The estimated value of a standard 215-pound carcass, 55 to 56 percent lean with 0.55 to 0.70 inches of backfat at the last rib, from barrows and gilts only, in dollars per 100 pounds, FOB plant. It is built from the prices and volume of pork cuts delivered and from average industry cutting yields, over one week of market activity, Monday to Friday, across all destinations including export and all sales types, delivery periods, refrigeration types and packaging styles, except specialty pork products. Whole-carcass trades in the week, if there are any, are averaged in at one to one. Not a price paid for hogs, not sow or boar pork, and not negotiated sales only. |
| Loin, butt, picnic, rib, ham and belly primal values, same report | The estimated value of each primal on the same carcass, in dollars per 100 pounds, FOB plant, over the same week, sales types and delivery periods, based on the individual cuts and their prices. The report does not list which cuts make up each primal or give the cutting yields, and it does not say whether a primal value is per 100 pounds of that primal or of carcass. Not the price of any single cut: a belly value is not a bacon price, and a loin value is not a price for chops. |
| Hog inventory, Quarterly Hogs and Pigs | Head on hand in the United States on March 1, June 1, September 1 and December 1, in thousands, estimated from a survey of producers: all hogs and pigs, those kept for breeding, and market hogs, with market hogs split into four weight groups, under 50 pounds, 50 to 119, 120 to 179, and 180 pounds and over. The report does not say whether the weights are live weights. A count of animals, not slaughter and not a price. Estimates for the previous four quarters are subject to revision at each release, so one date can carry two values, and each row names the release it came from. The pig crop and farrowing figures the same report publishes are not parsed into this record. |

An issue states the specification in its own text where a reader could otherwise take a figure for a product it does not price.

## Rules

- Compare like with like: pork by primal and by market basis. The carcass cutout and a single primal are different measures and are never averaged together. Wholesale and retail are never averaged. An index is never converted to a price.
- A price claim about pork is usually a claim about one primal. Each issue reports the carcass cutout and every primal beside it, and names which primal moved most on the year, because belly and rib move very differently from ham and a claim framed as "pork" may rest on one of them.
- Year-over-year means the week ending nearest to 52 weeks earlier, within four days. A trailing four-week average is shown beside the single week.
- Each quarterly hog inventory is dated to the year of the column it appears under, December 1 included: the release of September 24, 2026 prints the December 1 inventory under 2025, and its state table titles the same figure December 1, 2025. The December-preceding-year convention in that report applies to its farrowing and pig crop tables, which this record does not parse.
- Cells NASS leaves blank because an estimation period has not begun are skipped, never read as zero.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## What this record cannot show

The hog inventory is quarterly, so for most of any quarter the most recent supply figure is already weeks old. Mandatory price reporting covers trade at reporting plants; it is not every transaction in the country. A cutout value is an estimated value of a whole carcass built from the prices of its cuts, not the price of any cut a buyer orders. Whole carcasses do trade, but thinly: report 2680 for the week ending 2026-10-09 lists 6.21 carcass loads against 5,793 loads of cuts, trimmings and processed product. Nothing here establishes why a particular supplier quoted a particular price.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

The BLS request carries a free registration key. The key is read from the environment at fetch time and is never written into a capture file, a data file, or this repository. A response body that repeats the key is discarded and the fetch recorded as failed, so a rejected credential cannot enter the record.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
