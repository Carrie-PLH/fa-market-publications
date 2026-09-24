# Market Publications — operating notes for Claude sessions

Read `README.md` first. This file covers what a session needs to act.

## What this is

A Field Assembly repository for Provision Record, a free public resource (FA-D-20260923-02). Public output is the built site: edition text, numbers, downloadable tables, retained source files, timestamp records and methodology pages. Sellers are letters in public output. Lobster Monitor's consumer observations come from `lobster/observations/` (this repository's own record, from 2026-09-26; see its README) and, for dates before that, from the wedding lobster monitor at `~/Projects/websites/ABS wedding/lobster-monitor` (absolute path in the gitignored `.fa-retail-root`), a separate private evidence record: read it, never write to it, never add it to the Field Assembly portfolio checkpoint. The observation tools under `lobster/observations/tools/` run only on the Mac (headless Chrome).

## Where things run

`tools/fetch.py` needs only outbound HTTPS: it runs on the Mac, in the Cowork VM, or in the cloud sandbox. `tools/anchor.py run` needs network for the timestamp authorities. `tools/issue.py` needs the wedding record on disk only for an edition whose month includes observations before 2026-09-26; when it runs in the Cowork VM it resolves the Mac path under `$HOME/mnt/`, or set `FA_RETAIL_ROOT`. `lobster/observations/tools/` needs the Mac (headless Chrome).

## Never edit the record

Nothing under `<title>/captures/`, `<title>/data/*.jsonl`, or `anchors/` is edited or deleted. A bad fetch is superseded by a later run. `sources.json` gains sources or marks them retired; it never loses one.

## Fail visibly

A fetch failure is a fact about the transport. Record it and let the next run retry. A parser that cannot find its pattern fails the source. Report the full failure count.

## Site

`tools/site.py` builds `site/` from the record and publishes only editions whose `edition.json` says `published`. Never write pages into `site/` by hand. Never build drafts into `site/`; preview them with `--include-drafts --out site-preview`. Never remove paid-model language by editing built pages; edit `tools/site.py`.

## Issues

An issue is written by a person from `numbers.md`; the prose never carries a figure absent from `numbers.json`. Sellers in the retail reference are letters in issue text and named only in `methodology.md`. The audience is the buyer facing a supplier's price claim. The issue states market evidence and draws no conclusion about any contract.

## Decision requests

Present options in recommended order, recommendation first, with a brief reason.
