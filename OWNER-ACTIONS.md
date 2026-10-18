# Owner actions — Provision Record

What is outstanding and what "done" looks like for each item. The weekly
scheduled task "Provision Record: what's outstanding" reads this file, checks
it against the repository's actual state, and reports only what is still open.
Keep this file current and the reminder stays useful; let it drift and the
reminder lies.

Mark an item done by deleting it. Do not tick it; a file of ticked items stops
being readable.

## Outstanding

**1. Methodology specifications for chicken, beef, pork, cheddar.**
Each needs the section the Egg & Butter page now has, naming what its series
actually price, read off the retained captures rather than written from memory:
boxed beef Choice and Select 600-900 lb, fed cattle dressed and live, the pork
primals and the cutout, cheddar 40-pound block mandatory reporting against CME
spot, and the report 3649 parts definitions. Done when each of the four
`<title>/methodology.md` files has that section.
Blocks: publication of that title.

**2. Pork `nass_hogs_pigs` reports PARTIAL on every run.**
The rolling `Todays_Reports` path 404s and the ESMIS archive fallback quietly
succeeds, so the reading is fine and the alarm is permanent. Reorder the fetch
so the archive is tried first and PARTIAL means something again. Done when a
weekly run reports pork with no PARTIAL.

**3. Publish the four October issues, one title at a time.**
Chicken Monitor, Beef Monitor, Pork Monitor, Cheddar Check. Each: draft from
`numbers.md`, independent review against the five failure classes in
`CLAUDE.md`, apply findings, then `tools/publish.sh <title> 2026-10` and push.
One per sitting. Four drafts reviewed in one evening is how the review becomes
a rubber stamp. Done when all four have a published edition.
Gate: open. FA-D-20261018-01 superseded the measured-quarter limb of
FA-D-20260923-04 on 2026-10-18.

**4. Decide whether the four September baselines publish.**
They are scaffolds computed under superseded tooling: before the report 3649
period fix, the accumulating-sources fix, the rounding rule and the evidence
manifest. Lobster published its baseline as Issue 0, so there is precedent
either way. Recommendation on file: do not publish them, let each title's first
live edition be the first written under current tooling, and regenerate the
baselines so they are not stale artifacts. Done when decided, either way.
Not blocking anything.

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

Last updated 2026-10-18. The scheduled task should check these against the
repository and say which have gone stale rather than trusting them.

- Published: Lobster Monitor Issue 0 (2026-09-25) and Issue 1 (2026-10-18,
  version 1.1 after a same-day correction); Egg & Butter Brief Issue 1
  (2026-10-18, version 1.0). Three published editions across two titles.
- Computed but unpublished: a 2026-10 issue for each of chicken, beef, pork and
  cheddar, and a 2026-09-baseline scaffold for each of those four plus
  egg-butter.
- All six titles are in `RUN.titles`, so the monthly job computes numbers for
  every title on the 18th. The weekly capture runs Fridays and covers all six.
- Reviewer line in use: "reviewed <date> Carrie Schluter".

## Known limits a first issue must state

Not actions. Carry these into the prose when each title is written.

- **Chicken.** The report 3649 wholesale series carries no year-over-year until
  the record holds twelve months; earliest reading is 2026-08, so roughly
  August 2027. Month-over-month works now.
- **Cheddar.** Same for the CME reprint, roughly September 2027. The NDPSR
  500-pound barrel series has published no price since 2025-05-31 and is held
  as history, not a current price.
- **Beef.** The derived cutout-less-fed-cattle spread has mismatched weeks and
  no prior-year figure. Decide whether it earns its place before publishing.
- **Pork.** The cutout runs a week behind beef and cheddar because the AMS
  dataset publishes later.
- **All titles.** `tools/check.py` reads only figures carrying a unit in prose.
  Bare counts and quantities written in words pass unexamined; check those by
  hand against the computed set.
