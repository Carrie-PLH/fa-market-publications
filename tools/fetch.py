#!/usr/bin/env python3
"""Fetch every official source for a title and retain the evidence.

Writes, under <title>/captures/<run_id>/<source_id>/:
  <fetch>.<ext>        raw response body, byte for byte
  <fetch>.headers.txt  HTTP status, final URL, response headers (Set-Cookie redacted)
  capture.json         what was fetched, when, from where, SHA-256 of every file
and appends one line per source to <title>/captures/manifest.jsonl.

No browser. Runs anywhere with outbound HTTPS. A fetch that fails is recorded
as FAILED with the error text; nothing is substituted.

Usage:
    python3 tools/fetch.py --title lobster [--source bls] [--run-id <id>]

Forked from the wedding lobster monitor's capture.py (retail scrapers and
Chrome rendering removed). Stdlib only.
"""

import argparse
import gzip
import http.cookiejar
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, Title, config, iso, now_utc, rel, run_id_from, sha256_file  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
REQUEST_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip",
}


def fetch(url, timeout, data=None, content_type=None):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    headers = dict(REQUEST_HEADERS)
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers)
    with opener.open(req, timeout=timeout) as resp:
        body = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
        return resp.status, resp.geturl(), resp.headers, body


def header_block(status, final_url, headers):
    lines = [f"# {final_url}", f"HTTP {status}"]
    dropped = 0
    for k, v in headers.items():
        if k.lower() == "set-cookie":
            dropped += 1
            continue
        lines.append(f"{k}: {v}")
    if dropped:
        lines.append(f"# {dropped} Set-Cookie header(s) redacted at capture")
    return "\n".join(lines) + "\n"


def resolve_follow(spec, done, base_url):
    """FOLLOW:<fetch-name>:<substring|re:regex> -> first matching href in that
    fetch's HTML, resolved against the fetch's final URL."""
    _, name, needle = spec.split(":", 2)
    prior = done.get(name)
    if not prior or prior.get("status") != "OK":
        raise RuntimeError(f"cannot follow link from failed fetch '{name}'")
    html = (ROOT / prior["path"]).read_text("utf-8", errors="ignore")
    if needle.startswith("re:"):
        rx = re.compile(needle[3:])
        match = lambda h: rx.search(h) is not None  # noqa: E731
    else:
        match = lambda h: needle in h  # noqa: E731
    for href in re.findall(r'href="([^"]+)"', html):
        if match(href):
            return urllib.parse.urljoin(prior["final_url"] or base_url,
                                        href.replace("&amp;", "&"))
    raise RuntimeError(f"no link containing '{needle}' in fetch '{name}'")


SECRET_PREFIX = "ENV:"


def resolve_secrets(obj, used):
    """Replace "ENV:NAME" leaves with os.environ[NAME]. Records each name in
    `used` so the retained copy of the request can name it without its value.
    A missing variable fails the fetch; nothing is substituted."""
    if isinstance(obj, dict):
        return {k: resolve_secrets(v, used) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_secrets(v, used) for v in obj]
    if isinstance(obj, str) and obj.startswith(SECRET_PREFIX):
        name = obj[len(SECRET_PREFIX):]
        val = os.environ.get(name)
        if not val:
            raise RuntimeError(f"environment variable {name} is not set")
        used.add(name)
        return val
    return obj


def redact_secrets(obj):
    """The request body as it is retained: every ENV: leaf stays as written."""
    if isinstance(obj, dict):
        return {k: redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_secrets(v) for v in obj]
    return obj


def expand_years(obj):
    """{YEAR} and {YEAR_MINUS_n} in string leaves, from the current UTC year."""
    if isinstance(obj, dict):
        return {k: expand_years(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_years(v) for v in obj]
    if isinstance(obj, str):
        y = now_utc().year
        obj = obj.replace("{YEAR}", str(y))
        obj = re.sub(r"\{YEAR_MINUS_(\d+)\}", lambda m: str(y - int(m.group(1))), obj)
    return obj


def expand_template(url):
    """{MMYY} and {MMYY_PREV}: release-month file names (NASS style), from the
    current UTC month and the month before."""
    now = now_utc()
    prev_m, prev_y = (now.month - 1 or 12), (now.year if now.month > 1 else now.year - 1)
    return (url.replace("{MMYY}", f"{now.month:02d}{now.year % 100:02d}")
               .replace("{MMYY_PREV}", f"{prev_m:02d}{prev_y % 100:02d}"))


def fetch_try(url, timeout):
    """TRY:<url1>|<url2>|...: first URL that returns 200 wins; the URLs tried
    and their errors are reported if all fail."""
    errors = []
    for cand in url[4:].split("|"):
        cand = expand_template(cand)
        try:
            return cand, fetch(cand, timeout)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{cand}: {repr(e)[:120]}")
    raise RuntimeError("all candidates failed: " + " | ".join(errors))


def capture_source(t, src, run_id, cfg):
    out_dir = t.captures / run_id / src["id"]
    out_dir.mkdir(parents=True, exist_ok=False)
    fc = cfg["FETCH"]
    record = {"run_id": run_id, "source_id": src["id"], "source_name": src["name"],
              "label": src["label"], "captured_at": iso(), "fetches": [],
              "status": "OK", "errors": []}
    done = {}
    for fspec in src["fetches"]:
        url = fspec["url"]
        entry = {"name": fspec["name"], "requested_url": url, "final_url": None,
                 "status": None, "http_status": None, "content_type": None,
                 "path": None, "headers_path": None, "sha256": None,
                 "bytes": None, "fetched_at": None, "error": None}
        try:
            if url.startswith("FOLLOW:"):
                url = resolve_follow(url, done, src.get("page_url", ""))
                entry["resolved_url"] = url
            entry["fetched_at"] = iso()
            post = None
            if fspec.get("method", "GET").upper() == "POST":
                spec_body = expand_years(fspec["body"])
                # what is retained: the request as written, secrets named not shown.
                # Recorded before the secrets are resolved, so a run that fails
                # for want of a key still says what it tried to send.
                entry["request_method"] = "POST"
                entry["request_body"] = redact_secrets(spec_body)
                used = set()
                post = json.dumps(resolve_secrets(spec_body, used)).encode()
                entry["request_secrets"] = sorted(used)
            if url.startswith("TRY:"):
                url, (status, final_url, headers, body) = fetch_try(url, fc["timeout_seconds"])
                entry["resolved_url"] = url
            else:
                status, final_url, headers, body = fetch(
                    url, fc["timeout_seconds"], data=post,
                    content_type="application/json" if post else None)
            target = out_dir / f"{fspec['name']}.{fspec['ext']}"
            target.write_bytes(body)
            hpath = out_dir / f"{fspec['name']}.headers.txt"
            hpath.write_text(header_block(status, final_url, headers), "utf-8")
            entry.update({"final_url": final_url, "status": "OK", "http_status": status,
                          "content_type": headers.get("Content-Type"),
                          "path": rel(target), "headers_path": rel(hpath),
                          "sha256": sha256_file(target), "bytes": len(body)})
        except Exception as e:  # noqa: BLE001
            entry["status"] = "FAILED"
            entry["error"] = repr(e)[:500]
            record["errors"].append(f"{fspec['name']}: {entry['error']}")
        record["fetches"].append(entry)
        done[fspec["name"]] = entry
        time.sleep(fc["request_delay_seconds"])
    n_fail = sum(1 for f in record["fetches"] if f["status"] != "OK")
    if n_fail == len(record["fetches"]):
        record["status"] = "FAILED"
    elif n_fail:
        record["status"] = "PARTIAL"
    (out_dir / "capture.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", "utf-8")
    with open(t.manifest, "a", encoding="utf-8") as f:
        f.write(json.dumps({"run_id": run_id, "source_id": src["id"],
                            "captured_at": record["captured_at"],
                            "status": record["status"],
                            "files": {x["name"]: x["sha256"] for x in record["fetches"]
                                      if x["sha256"]},
                            "errors": record["errors"]}, sort_keys=True) + "\n")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--source")
    ap.add_argument("--run-id")
    a = ap.parse_args()
    t = Title(a.title)
    cfg = config()
    run_id = a.run_id or run_id_from(now_utc())
    srcs = [s for s in t.sources() if not s.get("retired")]
    if a.source:
        srcs = [s for s in srcs if s["id"] == a.source] or sys.exit(f"unknown source {a.source}")
    t.captures.mkdir(parents=True, exist_ok=True)
    print(f"fetch {a.title} run {run_id}: {len(srcs)} sources")
    summary = []
    for s in srcs:
        print(f"  {s['id']:<22}", end="", flush=True)
        rec = capture_source(t, s, run_id, cfg)
        summary.append((s["id"], rec["status"]))
        print(rec["status"], "; ".join(rec["errors"]))
    failed = [i for i, st in summary if st == "FAILED"]
    partial = [i for i, st in summary if st == "PARTIAL"]
    print(json.dumps({"run_id": run_id, "failed": failed, "partial": partial}))


if __name__ == "__main__":
    sys.exit(main())
