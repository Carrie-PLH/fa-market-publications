# Market Publications — operating notes for Claude sessions

Read `README.md` first. This file covers what a session needs to act.

## What this is

A Field Assembly product repository. Public output is the issue text and the methodology page. Tools and data are private. The wedding lobster monitor at `../ABS wedding/lobster-monitor` is a separate private evidence record: read it, never write to it, never add it to the Field Assembly portfolio checkpoint.

## Where things run

`tools/fetch.py` needs only outbound HTTPS: it runs on the Mac, in the Cowork VM, or in the cloud sandbox. `tools/anchor.py run` needs network for the timestamp authorities. `tools/issue.py` needs the wedding record on disk; when it runs in the Cowork VM it resolves the Mac path under `$HOME/mnt/`, or set `FA_RETAIL_ROOT`.

## Never edit the record

Nothing under `<title>/captures/`, `<title>/data/*.jsonl`, or `anchors/` is edited or deleted. A bad fetch is superseded by a later run. `sources.json` gains sources or marks them retired; it never loses one.

## Fail visibly

A fetch failure is a fact about the transport. Record it and let the next run retry. A parser that cannot find its pattern fails the source. Report the full failure count.

## Issues

An issue is written by a person from `numbers.md`; the prose never carries a figure absent from `numbers.json`. Sellers in the retail reference are letters in issue text and named only in `methodology.md`. The audience is the buyer facing a supplier's price claim. The issue states market evidence and draws no conclusion about any contract.

## Decision requests

Present options in recommended order, recommendation first, with a brief reason.
