#!/usr/bin/env bash
# The only supported way to publish the Food Market Publications site.
# Direct upload of site/ to the Cloudflare Pages project, run by hand.
# No connected repository, no CI. Only site/ is published; everything else
# in this repository (captures, data, issues, tools) is working material.
# Mirrors ~/Projects/Field Assembly/FA homepage/deploy.sh and DEPLOYMENT.md.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.nvm/versions/node/v24.13.0/bin:$PATH"
# security.txt must be RFC 9116-valid and not expiring (FA-D-20260911-05,
# wired here 2026-10-14). Refuses when Expires is past or within 60 days; the
# fix is the same tool with --renew, on the same day as every other site.
python3 ../field-assembly-standard/tools/securitytxt-check.py
wrangler pages deploy site --project-name fa-market-publications --branch main --commit-dirty=true
