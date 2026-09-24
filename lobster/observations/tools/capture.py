#!/usr/bin/env python3
"""Capture pass: fetch every source and retain the evidence.

For each source in sources.json this writes, under captures/<run_id>/<source_id>/:

  <fetch>.<ext>            raw response body, byte-for-byte
  <fetch>.headers.txt      HTTP status, final URL, response headers (Set-Cookie redacted)
  page.png / page.pdf      full-page screenshot and PDF of the human-readable page,
                           rendered by headless Google Chrome on this machine
  capture.json             what was fetched, when, from where, with SHA-256 of every file

and appends one line per source to captures/manifest.jsonl. Nothing under
captures/ is ever modified after it is written. A fetch that fails is recorded
as FAILED with the error text; nothing is substituted.

Usage:
    python3 tools/capture.py                 # full pass, new run id
    python3 tools/capture.py --source taylor # one source
    python3 tools/capture.py --run-id <id>   # use a given run id (run.py does this)

Stdlib only. Must run on the Mac (the machine whose Chrome renders the pages).
"""

import argparse
import fcntl
import gzip
import http.cookiejar
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CAPTURES, MANIFEST, ROOT, config, iso, now_utc, rel,  # noqa: E402
                    run_id_from, sha256_file, sources)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
REQUEST_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip",
}


class PassLock:
    """Refuse to start a pass while another is in flight (advisory lock)."""

    def __init__(self):
        self.path = ROOT / ".capture.lock"
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "a+")
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.fh.seek(0)
            sys.exit(f"another capture pass is running (lock {self.path}, "
                     f"pid {self.fh.read().strip() or 'unknown'})")
        self.fh.seek(0)
        self.fh.truncate()
        self.fh.write(str(os.getpid()))
        self.fh.flush()
        return self

    def __exit__(self, *a):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()
        try:
            self.path.unlink()
        except OSError:
            pass


def fetch(url: str, timeout: int):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(url, headers=dict(REQUEST_HEADERS))
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


def resolve_follow(spec: str, done: dict, base_url: str):
    """FOLLOW:<fetch-name>:<substring> -> first href in that fetch's HTML
    containing the substring, resolved against the fetch's final URL."""
    _, name, needle = spec.split(":", 2)
    prior = done.get(name)
    if not prior or prior.get("status") != "OK":
        raise RuntimeError(f"cannot follow link from failed fetch '{name}'")
    html = Path(ROOT / prior["path"]).read_text("utf-8", errors="ignore")
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


def chrome_render(chrome: str, url: str, out_dir: Path, width: int, height: int,
                  timeout: int, want_pdf: bool = True):
    """Screenshot and PDF via headless Chrome. Returns dict of results."""
    results = {}
    if not chrome or not Path(chrome).exists():
        return {"png": {"status": "FAILED", "error": "chrome not found"},
                "pdf": {"status": "FAILED", "error": "chrome not found"}}
    kinds = [("png", "--screenshot=", "page.png")]
    if want_pdf:
        kinds.append(("pdf", "--print-to-pdf=", "page.pdf"))
    for kind, flag, fname in kinds:
        target = out_dir / fname
        prof = tempfile.mkdtemp(prefix="lobmon-chrome-")
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--hide-scrollbars",
               f"--user-data-dir={prof}", f"--window-size={width},{height}",
               f"--timeout={timeout * 1000}",
               "--no-pdf-header-footer", f"{flag}{target}", url]
        # Chrome 152's new headless mode writes the PDF and then does not
        # exit (observed 2026-09-11 on every page tried). The run is bounded
        # and the output validated by its trailer instead of by exit status.
        note = ""
        err = ""
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout)
            err = (p.stderr or p.stdout)[-500:]
        except subprocess.TimeoutExpired:
            note = "chrome did not exit within timeout; output validated by file trailer"
        except Exception as e:  # noqa: BLE001
            err = repr(e)[:500]
        try:
            ok = target.exists() and target.stat().st_size > 0
            if ok and kind == "pdf":
                with open(target, "rb") as fh:
                    fh.seek(max(0, target.stat().st_size - 64))
                    ok = b"%%EOF" in fh.read()
            if ok and kind == "png":
                with open(target, "rb") as fh:
                    ok = fh.read(8) == b"\x89PNG\r\n\x1a\n"
            if ok:
                results[kind] = {"status": "OK", "path": rel(target),
                                 "sha256": sha256_file(target),
                                 "bytes": target.stat().st_size, "note": note}
            else:
                results[kind] = {"status": "FAILED",
                                 "error": (err or note or "no output file")[:500]}
        finally:
            shutil.rmtree(prof, ignore_errors=True)
    return results


def capture_source(src: dict, run_id: str, cfg: dict) -> dict:
    out_dir = CAPTURES / run_id / src["id"]
    out_dir.mkdir(parents=True, exist_ok=False)
    cap = cfg["CAPTURE"]
    record = {"run_id": run_id, "source_id": src["id"], "source_name": src["name"],
              "label": src["label"], "captured_at": iso(), "fetches": [],
              "render": {}, "status": "OK", "errors": []}
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
            status, final_url, headers, body = fetch(url, cap["timeout_seconds"])
            target = out_dir / f"{fspec['name']}.{fspec['ext']}"
            target.write_bytes(body)
            hpath = out_dir / f"{fspec['name']}.headers.txt"
            hpath.write_text(header_block(status, final_url, headers), "utf-8")
            entry.update({"final_url": final_url, "status": "OK",
                          "http_status": status,
                          "content_type": headers.get("Content-Type"),
                          "path": rel(target), "headers_path": rel(hpath),
                          "sha256": sha256_file(target), "bytes": len(body)})
        except Exception as e:  # noqa: BLE001
            entry["status"] = "FAILED"
            entry["error"] = repr(e)[:500]
            record["errors"].append(f"{fspec['name']}: {entry['error']}")
        record["fetches"].append(entry)
        done[fspec["name"]] = entry
        time.sleep(cap["request_delay_seconds"])

    if src.get("screenshot", True) and src.get("page_url"):
        record["render"] = chrome_render(cap["chrome_path"], src["page_url"],
                                         out_dir, cap["screenshot_width"],
                                         cap["screenshot_height"],
                                         cap.get("render_timeout_seconds", 40),
                                         src.get("render_pdf", True))
        for k, v in record["render"].items():
            if v["status"] != "OK":
                record["errors"].append(f"render {k}: {v.get('error')}")

    n_fail = sum(1 for f in record["fetches"] if f["status"] != "OK")
    if n_fail == len(record["fetches"]):
        record["status"] = "FAILED"
    elif n_fail or any(v["status"] != "OK" for v in record["render"].values()):
        record["status"] = "PARTIAL"
    (out_dir / "capture.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", "utf-8")
    manifest_row = {"run_id": run_id, "source_id": src["id"],
                    "captured_at": record["captured_at"],
                    "status": record["status"],
                    "files": {f["name"]: f["sha256"] for f in record["fetches"]
                              if f["sha256"]},
                    "render": {k: v.get("sha256") for k, v in record["render"].items()},
                    "errors": record["errors"]}
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(manifest_row, sort_keys=True) + "\n")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="capture one source id only")
    ap.add_argument("--run-id", help="run id to use (default: now, UTC)")
    args = ap.parse_args()
    cfg = config()
    run_id = args.run_id or run_id_from(now_utc())
    srcs = [s for s in sources() if not s.get("retired")]
    if args.source:
        srcs = [s for s in srcs if s["id"] == args.source]
        if not srcs:
            sys.exit(f"unknown source {args.source}")
    CAPTURES.mkdir(exist_ok=True)
    with PassLock():
        print(f"capture run {run_id}: {len(srcs)} sources")
        summary = []
        for s in srcs:
            print(f"  {s['id']:<22}", end="", flush=True)
            rec = capture_source(s, run_id, cfg)
            summary.append((s["id"], rec["status"]))
            print(rec["status"], ("; ".join(rec["errors"]) if rec["errors"] else ""))
    failed = [i for i, st in summary if st == "FAILED"]
    partial = [i for i, st in summary if st == "PARTIAL"]
    print(f"done: {len(summary)} sources, {len(failed)} FAILED, {len(partial)} PARTIAL")
    print(json.dumps({"run_id": run_id, "failed": failed, "partial": partial}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
