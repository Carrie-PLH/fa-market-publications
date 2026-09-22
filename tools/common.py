#!/usr/bin/env python3
"""Shared helpers for Field Assembly Market Publications. Stdlib only.

Every title lives in its own directory under the repo root:
    <title>/sources.json   official sources (fetch.py) and retail letter map
    <title>/captures/      raw responses, headers, capture.json, manifest.jsonl
    <title>/data/          indicators.jsonl, flags.jsonl, runs.jsonl (append-only)
    <title>/issues/<id>/   issue.md, numbers.json, numbers.md, evidence.json
    <title>/methodology.md the public methods page
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Title:
    def __init__(self, name):
        self.name = name
        self.root = ROOT / name
        self.captures = self.root / "captures"
        self.manifest = self.captures / "manifest.jsonl"
        self.data = self.root / "data"
        self.indicators = self.data / "indicators.jsonl"
        self.flags = self.data / "flags.jsonl"
        self.runs = self.data / "runs.jsonl"
        self.issues = self.root / "issues"
        self.sources_file = self.root / "sources.json"

    def sources(self):
        return load_json(self.sources_file)["sources"]

    def retail_letters(self):
        return load_json(self.sources_file).get("retail_reference_sources", {})


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def config():
    return load_json(ROOT / "config.json")


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now_utc()).isoformat(timespec="seconds")


def run_id_from(dt):
    return dt.strftime("%Y-%m-%dT%H%M%SZ")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_jsonl(p: Path, row: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def read_jsonl(p: Path):
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))
