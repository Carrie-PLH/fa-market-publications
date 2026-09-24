#!/usr/bin/env python3
"""One routine run for a Provision Record title: due check, fetch, parse, issue, anchor, preview, commit.

Launched every day by launchd (tools/run-pass.sh). For each title listed in
config.json RUN.titles it does nothing unless an issue is due: the record's
newest month of the title's PPI series (RUN.<title>.ppi_series) is older than
last month, today's day of month is at or past RUN.<title>.earliest_day, and
no issues/<YYYY-MM>/ exists yet. BLS releases the PPI on a moving mid-month
date, so the daily fire polls from earliest_day until the new month appears.
Lobster's earliest_day is the 16th so that both seller observation passes of
the month (1st and 15th) are in the record before the numbers are computed.

Steps when due (per title):
  1. tools/anchor.py upgrade   collect pending OpenTimestamps attestations (also on idle days)
  2. tools/fetch.py --title    evidence to <title>/captures/<run_id>/
  3. tools/parse.py            indicator rows appended
  4. check                     the newest PPI month must be the expected one, else NOT_RELEASED
  5. tools/issue.py            <title>/issues/<YYYY-MM>/ numbers, numbers.md, evidence
  6. tools/anchor.py run       manifest, chain entry, RFC 3161 tokens, OTS proof
  7. tools/site.py --include-drafts --out site-preview
  8. git commit                only the routine's own paths

Never done here: writing issue.md, setting an issue published, building
site/, deploying. Those are tools/publish.sh, run by a person.

Usage:
  python3 tools/run.py            # run what is due
  python3 tools/run.py --force    # run every listed title now (never an existing issue)
  python3 tools/run.py --status   # print schedule state and last run
  python3 tools/run.py --check    # exit 0 if anything is due, 1 if not

Exit codes: 0 ok; 2 ran but a source FAILED/PARTIAL or a parser failed; 3 a step crashed.
Copied in shape from Materials Monitor's tools/run.py.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, Title, append_jsonl, config, iso, read_jsonl  # noqa: E402

TZ = ZoneInfo("America/New_York")
LOGS = ROOT / "logs"
ROUTINE = ROOT / "logs" / "routine.jsonl"


def prev_month(d):
    y, m = d.year, d.month - 1
    return f"{y - 1 if m == 0 else y}-{12 if m == 0 else m:02d}"


def newest_month(t, sid):
    best = ""
    for r in read_jsonl(t.indicators):
        if r["series_id"] == sid and r.get("period") and r.get("value") is not None:
            best = max(best, r["period"])
    return best or None


def state(cfg):
    today = datetime.now(TZ).date()
    expected = prev_month(today)
    issue_id = f"{today.year}-{today.month:02d}"
    out = {"today": today.isoformat(), "expected_ppi_month": expected, "issue_id": issue_id, "titles": {}}
    for slug in cfg["RUN"]["titles"]:
        rc = cfg["RUN"][slug]
        t = Title(slug)
        have = newest_month(t, rc["ppi_series"])
        exists = (t.issues / issue_id / "numbers.json").exists()
        out["titles"][slug] = {"ppi_series": rc["ppi_series"], "newest_ppi_month": have, "earliest_day": rc["earliest_day"],
                               "issue_exists": exists,
                               "due": (have or "") < expected and today.day >= rc["earliest_day"] and not exists}
    out["due"] = any(v["due"] for v in out["titles"].values())
    return out


def step(name, cmd, log):
    log.write(f"\n== {name}: {' '.join(cmd)}\n"); log.flush()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log.write(r.stdout); log.write(r.stderr); log.flush()
    return r


def run_title(slug, st, cfg, py, log, force):
    t = Title(slug)
    ts = st["titles"][slug]
    row = {"started_at": iso(), "title": slug, "issue_id": st["issue_id"], "expected_ppi_month": st["expected_ppi_month"],
           "status": "OK", "steps": {}, "forced": force}
    if ts["issue_exists"]:
        row["status"] = "SKIPPED_EXISTS"
        append_jsonl(ROUTINE, row | {"finished_at": iso()})
        print(f"{slug}: issue {st['issue_id']} already exists; not recomputed")
        return 0
    r = step(f"{slug} fetch", [py, "tools/fetch.py", "--title", slug], log)
    if r.returncode != 0:
        row["status"] = "CRASHED"; append_jsonl(ROUTINE, row | {"finished_at": iso()}); return 3
    summary = json.loads(r.stdout.strip().splitlines()[-1])
    run_id = summary["run_id"]
    row["run_id"] = run_id
    row["steps"]["fetch"] = {"failed": summary["failed"], "partial": summary["partial"]}
    r = step(f"{slug} parse", [py, "tools/parse.py", "--title", slug, "--run-id", run_id], log)
    if r.returncode != 0:
        row["status"] = "CRASHED"; append_jsonl(ROUTINE, row | {"finished_at": iso()}); return 3
    psum = json.loads(r.stdout.strip().splitlines()[-1])
    row["steps"]["parse"] = psum["sources"]
    bad = bool(summary["failed"] or summary["partial"] or any(v.get("status") != "OK" for v in psum["sources"].values()))
    have = newest_month(t, ts["ppi_series"])
    row["newest_ppi_month"] = have
    if (have or "") < st["expected_ppi_month"] and not force:
        row["status"] = "NOT_RELEASED" if not bad else "WARN"
        step("anchor run", [py, "tools/anchor.py", "run", "--note", f"routine {slug}: BLS {st['expected_ppi_month']} not yet released"], log)
        step("git add", ["git", "add", f"{slug}/captures", f"{slug}/data", "anchors"], log)
        step("git commit", ["git", "commit", "-q", "-m", f"Routine {slug} {run_id}: fetch; BLS {st['expected_ppi_month']} not yet released"], log)
        append_jsonl(ROUTINE, row | {"finished_at": iso()})
        print(f"{slug}: BLS {st['expected_ppi_month']} not yet released (newest {have}); captured and stopped")
        return 2 if bad else 0
    r = step(f"{slug} issue", [py, "tools/issue.py", "--title", slug, "--issue", st["issue_id"], "--run-id", run_id], log)
    if r.returncode != 0:
        row["status"] = "CRASHED"; append_jsonl(ROUTINE, row | {"finished_at": iso()}); return 3
    step("anchor run", [py, "tools/anchor.py", "run", "--note", f"routine {slug}: {st['issue_id']} numbers computed from {run_id}"], log)
    step("site preview", [py, "tools/site.py", "--include-drafts", "--out", "site-preview"], log)
    step("git add", ["git", "add", f"{slug}/captures", f"{slug}/data", f"{slug}/issues/{st['issue_id']}", "anchors"], log)
    step("git commit", ["git", "commit", "-q", "-m", f"Routine {slug} {run_id}: {st['issue_id']} numbers computed, anchored"], log)
    if bad:
        row["status"] = "WARN"
    append_jsonl(ROUTINE, row | {"finished_at": iso()})
    print(f"{slug}: {st['issue_id']} draft numbers ready in {slug}/issues/{st['issue_id']}/ (numbers.md, evidence.json); preview in site-preview/")
    return 2 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cfg = config()
    st = state(cfg)
    if a.status:
        rows = read_jsonl(ROUTINE)
        print(json.dumps({"state": st, "last_run": rows[-1] if rows else None}, indent=1)); return 0
    if a.check:
        return 0 if st["due"] else 1
    LOGS.mkdir(exist_ok=True)
    py = sys.executable
    if not st["due"] and not a.force:
        with open(LOGS / "idle.log", "a") as log:
            step("anchor upgrade", [py, "tools/anchor.py", "upgrade"], log)
        print("nothing due: " + "; ".join(f"{s} newest {v['newest_ppi_month']} expected {st['expected_ppi_month']} earliest day {v['earliest_day']} issue exists {v['issue_exists']}" for s, v in st["titles"].items()))
        return 0
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    rc = 0
    with open(LOGS / f"run-{run_id}.log", "w") as log:
        step("anchor upgrade", [py, "tools/anchor.py", "upgrade"], log)
        for slug, ts in st["titles"].items():
            if ts["due"] or a.force:
                rc = max(rc, run_title(slug, st, cfg, py, log, a.force))
    return rc


if __name__ == "__main__":
    sys.exit(main())
