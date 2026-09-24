#!/usr/bin/env bash
#
# Publish an issue, by hand, after the editor has written issue.md and set
# "status": "published", "published": "<date>" and a reviewer in edition.json.
#
#   tools/publish.sh lobster 2026-10
#
# Steps: figure check, anchor run (so the anchored text is the published
# text), build site/, commit, deploy. Stops at the first failure.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
T="${1:?title, e.g. lobster}"; ED="${2:?issue id, e.g. 2026-10}"
PY="${PYTHON:-/opt/homebrew/bin/python3}"
[[ -x "$PY" ]] || PY="$(command -v python3)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/Library/Python/3.14/bin:$HOME/.local/bin:/usr/bin:/bin"
status="$("$PY" -c "import json;print(json.load(open('$T/issues/$ED/edition.json'))['status'])")"
[[ "$status" == "published" ]] || { echo "edition.json status is '$status', not 'published'; set it (and published date, reviewer) first"; exit 1; }
"$PY" tools/check.py --title "$T" --issue "$ED"
"$PY" tools/anchor.py run --note "publish $T $ED"
rm -rf site
"$PY" tools/site.py
git add "$T/issues/$ED" anchors site
git commit -q -m "Publish $T $ED" || true
./deploy.sh
echo "published $T $ED; push with: git push origin master"
