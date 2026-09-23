# Provenance: Provision Record

This repository is the record behind provisionrecord.com, a Field Assembly market record. It declares its conformance here, as §3.8 of the Field Assembly Record Standard requires.

## Standard version

Collected under the Field Assembly Record Standard **1.2 as drafted** (§8, market records), recorded in FA-D-20260923-04. Version 1.2 is not yet released: it is frozen and anchored only on the owner's word. Until it is, the current released version is 1.1, and this work does not claim 1.1 conformance. Observations made before the 1.2 effective date are collected under the 1.2 draft and say so; an observation's standard version is pinned here rather than resolved by §6's date rule.

## What is met

- Retained release (§8.1): `tools/fetch.py` writes every response body byte for byte under `<title>/captures/<run>/<source>/`, with the response headers (Set-Cookie redacted) and a `capture.json` carrying URL, final URL, retrieval time and SHA-256. Failed fetches are recorded with the error and the source is marked FAILED or PARTIAL; nothing is substituted.
- Parsers fail visibly (§8.2): `tools/parse.py` appends rows to `<title>/data/indicators.jsonl`, each naming its capture file and hash; a parser that cannot find its pattern raises and the source is flagged PARSE_FAILED in `data/flags.jsonl`. Rows are never edited.
- The computed set (§8.3): `tools/issue.py` regenerates `numbers.json` from the rows for a named run; every figure in an edition must appear there. `tools/site.py` publishes `numbers.json`, `measures.csv`, `data.csv` and a `dictionary.md` stating each formula and rounding, with calculated rows marked, beside every published edition.
- Like with like, no causal inference, what the record does not do (§8.4, §8.5, §8.8): the methodology page of each title states the rules; the editorial standard in `CLAUDE.md` binds sessions to them.
- Editions immutable and versioned (§8.6): `edition.json` carries status, version, publication and revision dates; the site keeps every edition at its permanent address; corrections are dated on the page and the original text stays visible.
- Original observations by letter (§8.7): Lobster Monitor's consumer reference rows come read-only from the private wedding observation record, sellers appear as letters, and the letter map is on the methodology page.
- Anchoring (§3.6, PROVENANCE §chain): `tools/anchor.py` hashes `lobster/` and `egg-butter/` captures, data and issues into `anchors/`, with RFC 3161 tokens from two authorities. Chain entry 2026-09-22T202107Z covers the Lobster Monitor baseline run.
- Retention (§3.10): captures are never destroyed; a later run supersedes.
- Recipes (§3.11): `<title>/sources.json` is the recipe (URL, fetch method, parser, parser arguments); `config.json` carries fetch settings.

## What is not met, or not yet

- OpenTimestamps: no OTS proof exists for entry 2026-09-22T202107Z (the `ots` client was not installed at anchor time). Later anchor runs are expected to store one; the gap is stated on the edition page.
- Reviewer attribution (§3.9): the edition page carries a reviewer line from `edition.json`; no edition has published yet, so none has been reviewed for publication.
- Verification gate (§3.4): figures in an edition are checked against `numbers.json` by the editor, and `tools/site.py` checks the built CSVs against `numbers.json`; there is no mechanical check that every figure in the edition prose appears in the computed set. Planned.
- Corroboration (ACQUISITION §corroboration): no Internet Archive capture is triggered at fetch time. Planned.
- Egg & Butter Brief: the 2026-09-23 baseline run is captured and parsed and no edition is written; no anchor entry covers it yet.

## Local extensions

- Weekly series use `YYYY-MM-DD` week-ending periods; monthly series `YYYY-MM`; USDA ERS forecast attributes carry no period.
- Year-over-year for weekly series is the week ending nearest to 52 weeks earlier, within four days; stated in each data dictionary.
- The wedding observation record at the path in `config.json` is read-only from here and is not part of this repository's anchor chain; its commit and file hash are recorded in each Lobster Monitor edition's `evidence.json`.
