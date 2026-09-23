# Field Assembly Market Publications

Provision Record (provisionrecord.com): a free public resource that combines public data into dated, documented editions on what is happening to food costs, with sources, calculations, downloadable tables and retained evidence. Redirected from a paid model on 2026-09-23 (FA-D-20260923-02). No account, payment or email address is needed to read or download anything published.

Promise across all titles: a clear account of what's happening to food costs, and the evidence behind it.

## Titles

| Directory | Title | Status |
|---|---|---|
| `lobster/` | Lobster Monitor | Issue 0 (September 2026 baseline) drafted |
| `beef/` | Beef Monitor | Sources verified, baseline captured, Issue 0 scaffolded |
| `pork/` | Pork Monitor | Sources verified, baseline captured, Issue 0 scaffolded |
| `chicken/` | Chicken Monitor | Sources verified, baseline captured, Issue 0 scaffolded |
| `egg-butter/` | Egg & Butter Brief | Sources verified, baseline captured, Issue 0 scaffolded |
| `cheddar/` | Cheddar Check | Sources verified, baseline captured, Issue 0 scaffolded |

Publication of every title but Lobster Monitor is gated by FA-D-20260923-01 as amended by -02 and -04: no second title publishes a first edition until Lobster Monitor ships a post-baseline issue, and a further title enters only after the existing titles have shipped on cadence for one measured quarter.

Assessed and not scheduled: Coffee Current. Its sources verify, but only one institution publishes a coffee price, so no independent reading of it exists. See `config.json` for the registry and `tools/site.py` for the public register.

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
    <title>/issues/<id>/edition.json  status (draft | published), version, dates, revisions
    anchors/                 timestamp chain, tokens, proofs
    site-src/style.css       the site's stylesheet, inlined into every page
    tools/site.py            builds site/ from the record (published editions only)
    site/                    the deployable static site; deploy.sh publishes it by hand

## Issue cycle

    python3 tools/fetch.py --title lobster                       # after the mid-month BLS PPI release (egg-butter: same, plus weekly AMS reports)
    python3 tools/parse.py --title lobster --run-id <run>
    python3 tools/issue.py --title lobster --issue <YYYY-MM-slug> --run-id <run>
    # write or revise <title>/issues/<id>/issue.md against numbers.md
    python3 tools/anchor.py run --note "<issue id>"
    # set "status": "published", "published": "<date>" in <title>/issues/<id>/edition.json
    python3 tools/site.py                                        # rebuild site/ (preview drafts: --include-drafts --out site-preview)
    git add <paths> && git commit                                # explicit paths; never git add -A
    ./deploy.sh                                                  # only when the owner asks

Each published edition gets a permanent URL, /<title>/<id>/, with the edition text, a suggested citation, data.csv, measures.csv, observations.csv (where the title has original observations), dictionary.md, the record files, the retained source files under evidence/, and the timestamp chain entry and tokens that cover them. A correction is recorded in edition.json (revised date, version, revisions list) and in the edition text; the original text stays visible.

Every figure in an issue must appear in that issue's `numbers.json`. The editor reviews the evidence and interpretation before publication.

## Origin

Forked from the private wedding lobster monitor (`../ABS wedding/lobster-monitor`), which remains the evidence record for the September 25, 2027 wedding. This repository copies its official-source fetch and parse code and its anchoring convention. Retail scrapers stay in the wedding repo; this repository reads that record read-only for consumer reference rows and publishes sellers by letter.

## Never

Never edit or delete anything under `<title>/captures/`, `<title>/data/*.jsonl`, `anchors/`, or a published issue's `evidence.json`. Supersede with a later run. Never write to the wedding repository from here.
