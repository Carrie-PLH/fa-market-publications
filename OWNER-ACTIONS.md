# Owner actions — Provision Record

What is outstanding and what "done" looks like for each item. The weekly
scheduled task "Provision Record: what's outstanding" reads this file, checks
it against the repository's actual state, and reports only what is still open.
Keep this file current and the reminder stays useful; let it drift and the
reminder lies.

Mark an item done by deleting it. Do not tick it; a file of ticked items stops
being readable.

## Outstanding

Nothing outstanding as of 2026-11-02. All four October issues are published
(Pork 2026-10-25; Cheddar, Chicken and Beef 2026-11-02).

## Standing checks

These should hold at all times. Any that does not is worth reporting even when
nothing above is due.

- `python3 tools/check.py --all` passes for every issue.
- `python3 tools/anchor.py verify` reports PASS.
- `git status --porcelain` is clean.
- No title in `config.json` `RUN.titles` is missing a `ppi_series` entry.
- Every published edition's `edition.json` carries a version, a published date
  and a reviewer line.

## Where things stand

Last updated 2026-11-02. The scheduled task should check these against the
repository and say which have gone stale rather than trusting them.

- Published: Lobster Monitor Issue 0 (2026-09-25) and Issue 1 (2026-10-18,
  version 1.1 after a same-day correction); Egg & Butter Brief Issue 1
  (2026-10-18, version 1.0); Pork Monitor Issue 1 (2026-10-25, version 1.0);
  Cheddar Check Issue 1 (2026-11-02, version 1.0); Chicken Monitor Issue 1
  (2026-11-02, version 1.0); Beef Monitor Issue 1 (2026-11-02, version 1.0,
  commit ae4f576, on the 2026-10-18 run). Seven published editions across six
  titles.
- Computed but unpublished: no 2026-10 issue. The 2026-09-baseline scaffolds of
  pork, cheddar, chicken, beef and egg-butter do not publish (owner decision 2026-10-25) and were regenerated under current
  tooling the same day.
- All six titles are in `RUN.titles`, so the monthly job computes numbers for
  every title on the 18th. The weekly capture runs Fridays and covers all six.
- Reviewer line in use: "reviewed <date> Carrie Schluter".
- Pork, cheddar, chicken and beef `methodology.md` each carry a "What the
  series actually price" section (2026-10-25), read off the retained captures
  and checked in each title's October review. Beef's review corrected its
  series-break date (the single 600-900 column starts 2004, not roughly 2015);
  `beef/sources.json` still carries the old date and the words "packer margins".

## Known limits a first issue must state

Not actions. Carry these into the prose when each title is written.

- **Chicken.** The report 3649 wholesale series carries no year-over-year until
  the record holds the same reporting month a year apart; earliest reading is
  2026-08, so the first comparison is the August 2027 block, in the report
  due about the start of September 2027. Month-over-month works now.
- **Cheddar.** Same for the CME reprint, roughly September 2027. The NDPSR
  500-pound barrel series has published no price since 2025-05-31 and is held
  as history, not a current price.
- **Chicken.** The national composite whole bird is priced delivered; every
  parts row is FOB. Bone-in thighs trade about 21 to 27 thousand pounds a month,
  the thinnest row. The October report prints the boneless thigh range as
  "1.57 - 186.00", most likely a misprint for 157; quote the range with a note
  or not at all. The report never expands "B/S" or "WOG".
- **Cheddar.** The record reads `cheese_500_Price` for barrels; the retained
  file does not say whether that column or `cheese_500_Wtd_Price` is
  moisture-adjusted. The CME "Barrels" quote is a different measure from the
  ceased 500-pound barrel series. The barrel's 1.9495 (week ending
  2025-05-31) is a first print: the 2025-06-11 report restated that week and
  the three before it null, and `issue.py`'s series map skips null rows, so it
  keeps the first print. The 2026-10-16 DMN report prints two weekly
  averages for the same week (page 2 table against page 1); the record reads
  page 1, which matches the stated definition.
- **Beef.** The cutout-less-cattle spread pairs a cutout week with the report
  2700 row dated the Tuesday after it, so on the October run it is cutout
  2026-10-09 against cattle 2026-10-13 (week ending Sunday 2026-10-11), a week
  older than the cutout headline (2026-10-16); say so. The spread has no
  prior-year figure, the cutout is Choice only where the cattle price is all
  grades, and report 2700 prints prices in dollars with no weight basis (the
  per-cwt label comes from the source list). The fed cattle date is the report's
  publication date, not a week ending.
- **Pork and beef.** The pork cutout is comprehensive (all sales types, all
  delivery periods); the beef cutout is negotiated sales delivered within 0-21
  days. Not the same kind of measure across the two titles.
- **Pork.** The cutout runs a week behind beef and cheddar because the AMS
  dataset publishes later.
- **Pork and beef, from the November issue.** BLS marks October 2025 "Data
  unavailable due to the 2025 lapse in appropriations" for CPI-U and both
  average prices in pork's retained series.json, and for both CPI-U series and
  both average prices in beef's, so the October 2026 CPI and retail price rows
  will have no year-earlier value. Check other titles' CPI series the same way.
- **All titles.** `tools/check.py` reads only figures carrying a unit in prose.
  Bare counts and quantities written in words pass unexamined; check those by
  hand against the computed set.
