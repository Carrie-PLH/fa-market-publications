#!/usr/bin/env bash
#
# One observation pass for the Lobster Monitor record: capture every seller
# page (HTML, headers, screenshot, PDF via headless Chrome), parse the
# observations, and commit the record. launchd calls this on the 1st and 15th
# (tools/com.fieldassembly.lobster-observations.plist); a person can call it too.
# Copied in shape from the wedding lobster monitor's run-pass.sh. Anchoring is
# done by the repository's own tools/anchor.py run, which covers this record.
#
# Usage: tools/run-pass.sh
set -euo pipefail
OBS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$OBS/../.." && pwd)"
cd "$OBS"
mkdir -p logs
PY="${PYTHON:-/opt/homebrew/bin/python3}"
[[ -x "$PY" ]] || PY="$(command -v python3)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/Library/Python/3.14/bin:$HOME/.local/bin:/usr/bin:/bin"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$OBS/logs/run-$STAMP.log"
{
  echo "== capture $(date -u +%FT%TZ)"
  out="$("$PY" tools/capture.py 2>&1)"; echo "$out"
  RUN="$(echo "$out" | tail -1 | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
  echo "== parse $RUN"
  "$PY" tools/parse.py --run-id "$RUN" 2>&1
  echo "== anchor"
  (cd "$REPO" && "$PY" tools/anchor.py run --note "lobster observations $RUN" 2>&1)
  echo "== commit"
  (cd "$REPO" && git add lobster/observations/captures lobster/observations/data anchors && git commit -q -m "Lobster observations $RUN" 2>&1 || true)
  echo "EXIT 0"
} > "$LOG" 2>&1 || {
  echo "EXIT $?" >> "$LOG"
  echo "$(date -u +%FT%TZ) run failed, see $LOG" >> logs/alerts.log
  /usr/bin/osascript -e "display notification \"Capture or parse failed. See lobster/observations/logs/.\" with title \"Lobster observations run needs attention\" sound name \"Basso\"" || true
}
# a failed or partial source is a WARN even when the pass finished
if grep -qE "FAILED|PARSE_FAILED|FLAG " "$LOG"; then
  echo "$(date -u +%FT%TZ) warnings in $LOG" >> logs/alerts.log
  /usr/bin/osascript -e "display notification \"A seller failed to capture or parse, or a flag was raised. See lobster/observations/logs/.\" with title \"Lobster observations run needs attention\" sound name \"Basso\"" || true
fi
echo "$(date -u +%FT%TZ) run log $LOG" >> logs/launcher.log
