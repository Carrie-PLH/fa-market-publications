# Provenance: Provision Record

This repository is the record behind provisionrecord.com, a Field Assembly market record. It declares its conformance here, as §3.8 of the Field Assembly Record Standard requires.

## Standard version

Collected under the Field Assembly Record Standard **1.2** (§8, market records), effective 2026-09-23, frozen under `versions/1.2/` in the standard's repository and anchored there (entry 2026-09-23T143102Z), recorded in FA-D-20260923-04. Observations captured before the 1.2 effective date (the Lobster Monitor run of 2026-09-22 and the Egg & Butter Brief run of 2026-09-23) are pinned to 1.2 here rather than resolved by §6's date rule, because §8 describes the practice they were collected under and no earlier release does.

## What is met

- Retained release (§8.1): `tools/fetch.py` writes every response body byte for byte under `<title>/captures/<run>/<source>/`, with the response headers (Set-Cookie redacted) and a `capture.json` carrying URL, final URL, retrieval time and SHA-256. Failed fetches are recorded with the error and the source is marked FAILED or PARTIAL; nothing is substituted. A request that carries a credential records the request as written, naming the environment variable rather than its value. Byte-for-byte retention has one sharp edge: a service that rejects a credential may echo it back in the error body, and retaining that body would write the credential into the record. A response containing a secret sent with the request is therefore discarded and the fetch recorded as FAILED. Such a response is an error response, so no reading is lost. This was not hypothetical: the BLS API returned a rejected key in its error message on 2026-09-23, and the capture was removed before it was committed.
- Parsers fail visibly (§8.2): `tools/parse.py` appends rows to `<title>/data/indicators.jsonl`, each naming its capture file and hash; a parser that cannot find its pattern raises and the source is flagged PARSE_FAILED in `data/flags.jsonl`. Rows are never edited.
- The computed set (§8.3): `tools/issue.py` regenerates `numbers.json` from the rows for a named run; every figure in an edition must appear there. `tools/site.py` publishes `numbers.json`, `measures.csv`, `data.csv` and a `dictionary.md` stating each formula and rounding, with calculated rows marked, beside every published edition.
- Like with like, no causal inference, what the record does not do (§8.4, §8.5, §8.8): the methodology page of each title states the rules; the editorial standard in `CLAUDE.md` binds sessions to them.
- Editions immutable and versioned (§8.6): `edition.json` carries status, version, publication and revision dates; the site keeps every edition at its permanent address; corrections are dated on the page and the original text stays visible.
- Original observations by letter (§8.7): Lobster Monitor's consumer reference rows come read-only from the private wedding observation record, sellers appear as letters, and the letter map is on the methodology page.
- Anchoring (§3.6, PROVENANCE §chain): `tools/anchor.py` hashes the captures, data and issues of every title listed in `tools/anchor-paths.txt` into `anchors/`, with RFC 3161 tokens from two authorities. Chain entry 2026-09-22T202107Z covers the Lobster Monitor baseline run.
- Retention (§3.10): captures are never destroyed; a later run supersedes.
- Recipes (§3.11): `<title>/sources.json` is the recipe (URL, fetch method, parser, parser arguments); `config.json` carries fetch settings.

## What is not met, or not yet

- OpenTimestamps: no OTS proof exists for entry 2026-09-22T202107Z (the `ots` client was not installed at anchor time). Later anchor runs are expected to store one; the gap is stated on the edition page.
- Reviewer attribution (§3.9): the edition page carries a reviewer line from `edition.json`; no edition has published yet, so none has been reviewed for publication.
- Verification gate (§3.4): `tools/check.py` reads an issue's prose and its numbers table, pulls out every figure each asserts, and reports any that `numbers.json` does not hold at the precision the prose used. `tools/site.py` checks the built CSVs against `numbers.json`, and the editor reads the issue. What the mechanical check does not establish is that a figure was attached to the right measure: a figure equal to an unrelated stored value passes. A clean run means no figure was invented, not that every figure was used correctly.
- Corroboration (ACQUISITION §corroboration): no Internet Archive capture is triggered at fetch time. Planned.
- Titles in build without an anchor entry: the Egg & Butter Brief, Chicken Monitor, Beef Monitor, Pork Monitor and Cheddar Monitor all have a 2026-09-23 baseline run captured and parsed, and none is covered by a chain entry yet. Their capture, data and issue paths are in `tools/anchor-paths.txt`, so the next anchor run covers them.
- Chicken Monitor's wholesale weighted averages: report 3649 states the current and previous month only, so the year-over-year comparison for that series accumulates in this record from 2026-09 rather than existing at the baseline. The same holds for the CME cheese reprint in Cheddar Monitor, which carries one week per report.

## Credentials

The BLS request carries a free registration key for the public API v2. v1 is keyless but allows 25 queries per IP per day, which six titles do not fit inside; v2 allows 500 and takes a title's whole series set in one request. The key is read from the environment at fetch time, is stored outside this repository, and appears in no capture file, data file, commit or built page. `<title>/sources.json` names the environment variable, which is what makes the recipe reproducible without publishing the credential: anyone with their own free key can run the same fetch.

## Local extensions

- Weekly series use `YYYY-MM-DD` week-ending periods; monthly series `YYYY-MM`; USDA ERS forecast attributes carry no period.
- Year-over-year for weekly series is the week ending nearest to 52 weeks earlier, within four days; stated in each data dictionary.
- The wedding observation record at the path in `config.json` is read-only from here and is not part of this repository's anchor chain; its commit and file hash are recorded in each Lobster Monitor edition's `evidence.json`.
