#!/usr/bin/env bash
#
# Launch tools/run.py detached and return at once. launchd calls this daily;
# a person can call it too. The run writes its own log under logs/; this
# wrapper records the launch and the exit code so a run that was killed
# (no EXIT line) can be told apart from one that finished with errors.
# Copied from the wedding lobster monitor's run-pass.sh.
#
# Usage:
#   tools/run-pass.sh            # run if an edition is due
#   tools/run-pass.sh --force    # run now
#
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
mkdir -p logs
PY="${PYTHON:-/opt/homebrew/bin/python3}"
[[ -x "$PY" ]] || PY="$(command -v python3)"

# launchd gives a minimal PATH; git and ots must be findable.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/Library/Python/3.14/bin:$HOME/.local/bin:/usr/bin:/bin"

if ! "$PY" tools/run.py --check && [[ "${1:-}" != "--force" ]]; then
  # Nothing due: run.py only collects pending OpenTimestamps attestations.
  echo "$(date -u +%FT%TZ) $("$PY" tools/run.py 2>&1 | tail -1)" >> logs/launcher.log
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$REPO/logs/launch-$STAMP.log"
# After the run: a macOS notification on any outcome that needs a person, and
# a line in logs/alerts.log. Exit 0 with a draft is the normal monthly result
# and gets a notification too, because the editor must now write the edition.
nohup bash -c '
  "$1" -u "$2/tools/run.py" "${@:4}"
  rc=$?
  echo "EXIT $rc"
  last="$(grep -E "draft numbers ready|not yet released|nothing due" "$3" | tail -1)"
  case $rc in
    0) if [[ "$last" == *"draft numbers ready"* ]]; then what="Draft ready for review: $last"; else what=""; fi;;
    2) what="WARN: source failure, parse failure, or exceptions to read. $last";;
    3) what="CRASHED: a step failed";;
    *) what="exit $rc";;
  esac
  if [[ -n "$what" ]]; then
    echo "$(date -u +%FT%TZ) rc=$rc $what log=$3" >> "$2/logs/alerts.log"
    /usr/bin/osascript -e "display notification \"${what:0:200}\" with title \"Provision Record routine\" sound name \"Basso\"" || true
  fi
' _ "$PY" "$REPO" "$LOG" "$@" > "$LOG" 2>&1 &
echo "$(date -u +%FT%TZ) launched pid $! log $LOG" >> logs/launcher.log
echo "Run started detached, PID $!. Log: $LOG (finished when last line is EXIT <code>)"
