# Field Assembly Market Publications

Subscription publications that combine public data into documented explanations of what is happening to food costs, written for the buyer on the other side of a supplier's price claim. The research tools here are private. Customers pay for the publications.

Promise across all titles: a clear account of what's happening to food costs, and the evidence behind it.

## Titles

| Directory | Title | Status |
|---|---|---|
| `lobster/` | Lobster Monitor | Issue 0 (September 2026 baseline) drafted |

Planned: Egg & Butter Brief, Beef Monitor. See `config.json` for the registry.

## Layout

    config.json              title registry, fetch settings, retail reference path
    tools/fetch.py           fetch every official source for a title, retain evidence
    tools/parse.py           parse a fetch run into <title>/data/indicators.jsonl
    tools/issue.py           compute an issue's numbers and evidence manifest
    tools/anchor.py          external timestamp anchoring (Field Assembly convention)
    <title>/sources.json     official sources and the retail seller letter map
    <title>/captures/<run>/  raw responses, headers, capture.json; manifest.jsonl
    <title>/data/            indicators.jsonl, flags.jsonl, runs.jsonl (append-only)
    <title>/issues/<id>/     issue.md, numbers.json, numbers.md, evidence.json
    <title>/methodology.md   the public methods page
    anchors/                 timestamp chain, tokens, proofs

## Issue cycle

    python3 tools/fetch.py --title lobster                       # after the mid-month BLS PPI release
    python3 tools/parse.py --title lobster --run-id <run>
    python3 tools/issue.py --title lobster --issue <YYYY-MM-slug> --run-id <run>
    # write or revise <title>/issues/<id>/issue.md against numbers.md
    python3 tools/anchor.py run --note "<issue id>"
    git add -A && git commit

Every figure in an issue must appear in that issue's `numbers.json`. The editor reviews the evidence and interpretation before publication.

## Origin

Forked from the private wedding lobster monitor (`../ABS wedding/lobster-monitor`), which remains the evidence record for the September 25, 2027 wedding. This repository copies its official-source fetch and parse code and its anchoring convention. Retail scrapers stay in the wedding repo; this repository reads that record read-only for consumer reference rows and publishes sellers by letter.

## Never

Never edit or delete anything under `<title>/captures/`, `<title>/data/*.jsonl`, `anchors/`, or a published issue's `evidence.json`. Supersede with a later run. Never write to the wedding repository from here.
