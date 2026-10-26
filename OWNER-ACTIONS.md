# Owner actions — Provision Record

What is outstanding and what "done" looks like for each item. The weekly
scheduled task "Provision Record: what's outstanding" reads this file, checks
it against the repository's actual state, and reports only what is still open.
Keep this file current and the reminder stays useful; let it drift and the
reminder lies.

Mark an item done by deleting it. Do not tick it; a file of ticked items stops
being readable.

## Outstanding

**1. Confirm the pork fetch fix on Friday's run.**
Fixed 2026-10-25 (commit 8bf3cbc): the ESMIS archive is fetched first and the
rolling NASS path only when the archive fails, so the archive reading is OK
and PARTIAL means the archive itself failed. Tested on a scratch copy. Done
when the weekly run of 2026-10-30 reports pork `nass_hogs_pigs` OK.

**2. Fix the beef spread and fed cattle wording from the report 2700 PDF.**
Decided 2026-10-25: retain the report 2700 PDF, then fix the wording from what
it says. The fetch is in `beef/sources.json` from 2026-10-25 and the weekly
run of 2026-10-30 is the first to retain it. Read from a scratch fetch, the
PDF states the week ending Sunday, purchases from 2pm the previous Monday to
10am the current Monday, negotiated, formula, contract and grid purchases
included, live transactions also shown converted to a dressed price; it states
no unit beyond dollars. The Datamart row is dated the Tuesday it published.
So the October issue paired cutout week 2026-10-16 with cattle purchases of
the week before; the like-for-like pairing is the cattle row published the
Tuesday after the cutout's Friday. October's run (2026-10-18) predates the
2026-10-20 row, so its latest matched pair is cutout 2026-10-09 with cattle
2026-10-13. After the 2026-10-30 capture: re-pair the
spread in `issue.py`, drop "of carcass" from its note, fix the fed cattle
"week ending" label, the beef Rules line ("week ending the following
Tuesday") and the sources table ("price packers paid", "of carcass"), all
quoted from the retained PDF, and recompute beef 2026-10. Done when those
agree with the retained capture. Blocks: Beef Monitor publication.

**3. Publish the four October issues, one title at a time.**
In this order (decided 2026-10-25): Pork Monitor, Cheddar Check, Chicken
Monitor, then Beef Monitor once item 2 is done. Each: draft from
`numbers.md`, independent review against the five failure classes in
`CLAUDE.md`, apply findings, then `tools/publish.sh <title> 2026-10` and push.
One per sitting. Four drafts reviewed in one evening is how the review becomes
a rubber stamp. Done when all four have a published edition.
Gate: open. FA-D-20261018-01 superseded the measured-quarter limb of
FA-D-20260923-04 on 2026-10-18.

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

Last updated 2026-10-25. The scheduled task should check these against the
repository and say which have gone stale rather than trusting them.

- Published: Lobster Monitor Issue 0 (2026-09-25) and Issue 1 (2026-10-18,
  version 1.1 after a same-day correction); Egg & Butter Brief Issue 1
  (2026-10-18, version 1.0). Three published editions across two titles.
- Computed but unpublished: a 2026-10 issue for each of chicken, beef, pork and
  cheddar. The 2026-09-baseline scaffolds of those four and of egg-butter do
  not publish (owner decision 2026-10-25) and were regenerated under current
  tooling the same day.
- All six titles are in `RUN.titles`, so the monthly job computes numbers for
  every title on the 18th. The weekly capture runs Fridays and covers all six.
- Reviewer line in use: "reviewed <date> Carrie Schluter".
- Each of the four remaining titles' `methodology.md` carries its "What the
  series actually price" section (2026-10-25), read off the retained captures.
  They are not yet read by the editor; that read belongs to each title's review.

## Known limits a first issue must state

Not actions. Carry these into the prose when each title is written.

- **Chicken.** The report 3649 wholesale series carries no year-over-year until
  the record holds twelve months; earliest reading is 2026-08, so roughly
  August 2027. Month-over-month works now.
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
  ceased 500-pound barrel series. The 2026-10-16 DMN report prints two weekly
  averages for the same week (page 2 table against page 1); the record reads
  page 1, which matches the stated definition.
- **Beef.** See item 2. The spread has no prior-year figure either, and the
  cutout is Choice only where the cattle price is all grades.
- **Pork and beef.** The pork cutout is comprehensive (all sales types, all
  delivery periods); the beef cutout is negotiated sales delivered within 0-21
  days. Not the same kind of measure across the two titles.
- **Pork.** The cutout runs a week behind beef and cheddar because the AMS
  dataset publishes later.
- **All titles.** `tools/check.py` reads only figures carrying a unit in prose.
  Bare counts and quantities written in words pass unexamined; check those by
  hand against the computed set.
