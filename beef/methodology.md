# Beef Monitor: methodology

This page is public. It names every source, states every rule, and explains what the record can and cannot show.

## What the publication reports

Market evidence about beef prices in the United States, from public sources, arranged so an independent restaurant, caterer, or small food buyer can check a supplier's price claim against it. Each issue has six parts: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record.

The publication does not estimate any supplier's cost, does not state whether any contractual adjustment is permitted, and does not forecast.

## Sources

Official series, fetched by script with no browser and retained byte for byte:

| Source | What it gives | Cadence and lag |
|---|---|---|
| USDA Agricultural Marketing Service, National Weekly Boxed Beef Cutout and Boxed Beef Cuts (report 2461) | The boxed beef cutout value in dollars per hundredweight of carcass, Choice and Select separately, under mandatory price reporting. The whole series comes in one request, so year-over-year is available in every issue. | Weekly, Friday, for the week just ended. |
| USDA Agricultural Marketing Service, National Weekly Fed Cattle Comprehensive (report 2700) | Weighted-average price packers paid for fed cattle, steer and heifer, live and dressed, with head count and the report's own week-over-week and year-over-year change. | Weekly, Tuesday, for the week just ended. |
| USDA National Agricultural Statistics Service, Cattle on Feed | Cattle on feed, placements, marketings and other disappearance for feedlots of 1,000 head or more, both years with NASS's own percent-of-previous-year column. | Monthly, about the 20th. |
| U.S. Bureau of Labor Statistics, public API v2 | PPI commodity indexes WPU0131 (slaughter cattle) and WPU02210133 (beef primal and subprimal cuts made in slaughtering plants). CPI-U CUUR0000SEFC (beef and veal) and CUUR0000SEFV (food away from home). Average prices in dollars per pound: APU0000FC1101 (all uncooked ground beef), APU0000FC3101 (all uncooked beef steaks). Not seasonally adjusted. | Monthly, released mid-month for the prior month. |
| USDA Economic Research Service, Food Price Outlook | Year-over-year CPI changes and forecast intervals for beef and veal, for meats, and for food away from home. Attribute text is kept verbatim. | Monthly, about the 25th. |
| USDA Agricultural Marketing Service, National Weekly Cattle and Beef Summary | The week's narrative: slaughter levels, carcass weights, demand by cut. Retained as evidence; figures quoted from it are entered by the editor and checked against the capture. | Weekly, Monday. |

### What the weekly series actually price

The cutout and the fed cattle price are narrower than the words "beef" and "cattle", and the two are not stated on the same terms. These specifications come from the retained reports themselves and are quoted here so a figure in an issue can be matched to what it prices. Where a retained file does not state something, this page says so rather than supplying it.

| Series | Specification as the report states it |
|---|---|
| Boxed beef cutout, Choice and Select, report 2461 | A value in U.S. dollars per 100 pounds, based on negotiated prices and volume of boxed beef cuts delivered within 0-21 days and on average industry cutting yields. The cuts are priced FOB plant. Choice and Select are separate columns, each headed 600-900; the report does not state what that range is measured in. The weekly figure is the report's weekly average, the simple average of the week's daily values, dated the last day of the week reported, normally a Friday. Negotiated sales only. Not Prime, branded or ungraded beef, not the price of any one cut, and not the comprehensive cutout value printed in the weekly Cattle and Beef Summary, which is a different figure. |
| Fed cattle, steer and heifer, dressed and live, report 2700 | The section the report calls Weighted Average, which divides fed cattle by class (steer and heifer, and dairy), by selling basis (live and dressed) and by grade group (lots more than 65 percent Choice, lots less than 65 percent Choice, and the total of all grades), with head count, average price, and change from the prior week and the prior year for each. The record carries the steer and heifer total of all grades on each basis, so a figure covers all grades together, and live and dressed are separate series. Not dairy cattle, which the report lists separately. The retained file states no unit, purchase type, weight range, price basis or delivery period, and does not say which days' purchases a figure covers. Its date is the day the report was published: a Tuesday since 31 March 2026, a Monday before that. The record labels the price in dollars per hundredweight, a unit taken from the source list rather than from the retained file. |
| Cattle on Feed, NASS | Thousands of head on feedlots with capacity of 1,000 or more head, United States. Cattle on feed are steers and heifers fed a ration for the slaughter market and expected to produce a carcass that will grade Select or better; cattle backgrounded only for later sale or placement are excluded. Placements are the report's placed-on-feed line, which is larger than the net placements figure it also states. Marketings are steers and heifers shipped out of feedlots to a slaughter market. Not feedlots under 1,000 head. Outside January and July the survey covers 16 States, which the report says hold about 98 percent of the cattle in such feedlots, and the previous month's estimates may be revised each month. |

An issue states the specification in its own text where a reader could otherwise take a figure for a product it does not price.

## Rules

- Compare like with like: beef by grade (Choice, Select, Prime, branded, ungraded), by carcass weight range, and by market. Cutout and retail are never averaged. An index is never converted to a price.
- A break in the boxed beef series is treated as a break. Before roughly 2015 the report carried separate 600-750 and 750-900 pound carcass columns; it now carries a single 600-900 pound column. The earlier columns are kept under their own series names and are never continued into the current one as though they were the same measure.
- Two figures reported in the same unit may be subtracted, and the result is labeled derived and stated as arithmetic. The Choice-less-Select spread and the cutout-less-dressed-cattle difference are reported this way. Neither is described as anyone's margin, because this record has no access to what it costs anyone to convert a carcass into boxes.
- Weeks do not always align. The cutout is reported for the week ending Friday and the fed cattle price for the week ending the following Tuesday; where a derived figure combines the two, both dates are stated.
- Year-over-year means the week ending nearest to 52 weeks earlier, within four days. A trailing four-week average is shown beside the single week, because a single week's cutout moves with the volume traded in it.
- A source that fails to fetch is recorded as failed. Nothing is substituted from another source.
- A parser that cannot find what it expects fails the source rather than guessing.
- Rows are never edited or deleted. A corrected reading is appended and the earlier row stays.
- A measure is added only when it helps answer a reader's question.

## What this record cannot show

Cattle and cutout can move in opposite directions for weeks at a time, and this record shows that they did without saying why. Cattle on feed placements describe a supply five or six months out and are revised. Mandatory price reporting covers negotiated and formula trade at reporting plants; it is not every transaction in the country. Nothing here establishes why a particular supplier quoted a particular price.

## Evidence and timestamps

Each issue directory holds `numbers.json` (every figure the issue quotes, regenerated from the data files), `evidence.json` (every capture file with URL, retrieval time, and SHA-256), and the issue as delivered. Capture files are hashed into an append-only chain anchored externally by RFC 3161 timestamp tokens and OpenTimestamps proofs.

An external timestamp shows that a captured file existed unchanged by the anchor date. It does not show that the source's figure was correct, or that a quoted price was available to every buyer.

The BLS request carries a free registration key. The key is read from the environment at fetch time and is never written into a capture file, a data file, or this repository. A response body that repeats the key is discarded and the fetch recorded as failed, so a rejected credential cannot enter the record.

## Corrections

Corrections are made by appending a note to the affected issue and to the next issue. The original text stays visible.
