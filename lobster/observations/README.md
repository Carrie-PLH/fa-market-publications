# Lobster Monitor observation record

Field Assembly's own record of advertised lobster prices on the public pages of eight Maine sellers, captured on the 1st and 15th of each month. It is the source of Lobster Monitor's consumer reference row from **2026-09-26** (`RECORD_START` in `config.json`). Sellers appear in editions by letter; the letter map is in `../sources.json` and on the methodology page.

## Origin

Forked on 2026-09-24 from the private wedding lobster monitor (`~/Projects/websites/ABS wedding/lobster-monitor`), which was built for one event and keeps running on its own schedule as evidence for that event. `tools/capture.py`, `tools/parse.py` and `tools/common.py` are copies of its tools; `sources.json` carries its eight retail sources and none of its official ones (Provision Record fetches those with `../../tools/fetch.py`). Observations before the record start come from the wedding record and are cited by file hash and git commit, as before. Neither record writes to the other.

One capture exists before the record start: `2026-09-24T213102Z`, a single-source test (Taylor Lobster) that validated the tooling in its new location. It is retained, anchored, and read by no edition.

## Layout

    config.json        record start, cadence, Chrome capture settings, size-class tolerance
    sources.json       the eight sellers: URL, fetch, parser
    tools/capture.py   fetch each page, retain HTML and headers, render screenshot and PDF with headless Chrome
    tools/parse.py     parse observations into data/observations.jsonl (append-only), keep data/product_registry.json
    tools/run-pass.sh  one pass: capture, parse, anchor (repository chain), commit
    tools/com.fieldassembly.lobster-observations.plist   launchd job, 1st and 15th at 09:45
    captures/<run>/<seller>/   page.html, page.headers.txt, page.png, page.pdf, capture.json
    data/              observations.jsonl, observations.csv, product_registry.json, flags.jsonl, runs.jsonl

`tools/issue.py` at the repository root reads this record for any observation dated on or after the record start, and the wedding record for anything earlier. `tools/site.py` publishes the captures behind an edition's observations under that edition's `evidence/observations/`.

## Install the job

    cp tools/com.fieldassembly.lobster-observations.plist ~/Library/LaunchAgents/
    launchctl bootout gui/$(id -u)/com.fieldassembly.lobster-observations 2>/dev/null; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fieldassembly.lobster-observations.plist

## Never

Never edit or delete anything under `captures/` or `data/*.jsonl`. A bad capture is superseded by the next pass. Never write to the wedding record from here.
