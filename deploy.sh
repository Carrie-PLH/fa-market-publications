#!/usr/bin/env bash
# The only supported way to publish the Food Market Publications site.
# Direct upload of site/ to the Cloudflare Pages project, run by hand.
# No connected repository, no CI. Only site/ is published; everything else
# in this repository (captures, data, issues, tools) is working material.
# Mirrors ~/Projects/Field Assembly/FA homepage/deploy.sh and DEPLOYMENT.md.
set -euo pipefail
cd "$(dirname "$0")"

# Refuse to publish anything git has not recorded (owner rule, 2026-11-17).
# wrangler uploads site/ as it sits on disk, so an edit another session has in
# flight is published by whoever deploys next; that day a Rules & Record
# deploy made for one page published an uncommitted edit to another. site/ is
# generated here (tools/site.py), so a rebuild is committed before it ships.
# Untracked files count. The remedy is a commit by whoever owns the change,
# never a stash, revert or delete of another session's files.
dirty="$(git status --porcelain -- site/)"
if [ -n "$dirty" ]; then
  echo "REFUSED: site/ has changes git has not recorded:"
  echo "$dirty" | sed 's/^/        /'
  echo "Nothing was published. Commit these, or wait for the session that"
  echo "owns them to commit, then run deploy.sh again."
  exit 1
fi
export PATH="$HOME/.nvm/versions/node/v24.13.0/bin:$PATH"
# security.txt must be RFC 9116-valid and not expiring (FA-D-20260911-05,
# wired here 2026-10-14). Refuses when Expires is past or within 60 days; the
# fix is the same tool with --renew, on the same day as every other site.
python3 ../field-assembly-standard/tools/securitytxt-check.py
wrangler pages deploy site --project-name fa-market-publications --branch main --commit-dirty=true
