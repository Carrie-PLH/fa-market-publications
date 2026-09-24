#!/usr/bin/env python3
"""Shared helpers for the lobster monitor. Stdlib only.

Paths, hashing, JSONL append, size-text parsing, and the size-class rule.
Everything that more than one tool needs lives here so the rule is applied
identically at parse time and at report time.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "captures"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
MANIFEST = CAPTURES / "manifest.jsonl"
OBSERVATIONS = DATA / "observations.jsonl"
OBSERVATIONS_CSV = DATA / "observations.csv"
INDICATORS = DATA / "indicators.jsonl"
RUNS = DATA / "runs.jsonl"
REGISTRY = DATA / "product_registry.json"

CONTEMPORANEOUS = "CONTEMPORANEOUS_CAPTURE"
HISTORICAL = "HISTORICAL_RECONSTRUCTED"

OBSERVATION_FIELDS = [
    "observation_id", "run_id", "captured_at", "observation_type",
    "source_id", "source_name", "source_label", "source_url",
    "product_key", "product_name", "product_category", "lobster_origin",
    "shell_type", "advertised_size", "minimum_weight_lb", "maximum_weight_lb",
    "size_class", "quantity", "package_weight_lb", "unit_of_sale",
    "listed_price", "currency", "normalized_price_per_lb",
    "normalized_price_per_lobster", "normalized_price_per_tail",
    "shipping_cost", "shipping_included", "promotional_price",
    "regular_price", "on_sale", "availability_status",
    "comparability_series", "series_class", "source_stated_date",
    "evidence_path", "screenshot_path", "pdf_path", "raw_capture_path",
    "sha256", "notes",
]


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def config():
    return load_json(ROOT / "config.json")


def sources():
    return load_json(ROOT / "sources.json")["sources"]


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


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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


# ---------- size parsing ----------

FRACTIONS = {"¼": ".25", "½": ".5", "¾": ".75", "⅛": ".125", "⅜": ".375",
             "⅝": ".625", "⅞": ".875"}


def _norm_size_text(t: str) -> str:
    t = t.replace("&#8211;", "-").replace("–", "-").replace("—", "-")
    t = t.replace("&nbsp;", " ").replace("\xa0", " ")
    for k, v in FRACTIONS.items():
        # "1 ¼" -> "1.25", "¼" alone -> "0.25"
        t = re.sub(r"(\d)\s*" + k, r"\1" + v, t)
        t = t.replace(k, "0" + v)
    # "1 1/4" -> "1.25"; "1/4" alone left as is
    t = re.sub(r"(\d)\s+1/4\b", r"\1.25", t)
    t = re.sub(r"(\d)\s+1/2\b", r"\1.5", t)
    t = re.sub(r"(\d)\s+3/4\b", r"\1.75", t)
    t = re.sub(r"(\d)\s+1/8\b", r"\1.125", t)
    return t


NUM = r"(\d+(?:\.\d+)?)"
UNIT = r"\s*(?:lbs?\.?|pounds?|#)"


def parse_size(text: str):
    """Return (min_lb, max_lb, single_nominal) from advertised size text.

    A range like "1.21 - 1.45 lbs" gives (1.21, 1.45, False). A single
    weight like "1.25 lb" gives (1.25, None, True). Unparseable text gives
    (None, None, False); nothing is inferred.
    """
    if not text:
        return None, None, False
    t = _norm_size_text(text)
    m = re.search(NUM + r"\s*(?:-|to)\s*" + NUM + UNIT, t, re.I)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if a <= b:
            return a, b, False
    m = re.search(NUM + UNIT + r"\s*\+", t, re.I)
    if m:
        return float(m.group(1)), None, False  # "1.75 lb+" open-ended
    m = re.search(NUM + UNIT, t, re.I)
    if m:
        return float(m.group(1)), None, True
    # bare number followed by size word e.g. "1.25 (medium)" not accepted
    return None, None, False


def size_class(min_lb, max_lb, single, tolerance=0.05):
    """Canonical size class for cross-source comparison.

    Rule: the class is the nearest quarter-pound to the minimum stated
    weight, accepted only when within `tolerance` lb of it. Single nominal
    weights map to themselves. Anything else is "other". The rule is
    deliberately narrow so unlike sizes are not merged.
    """
    if min_lb is None:
        return "unsized"
    q = round(min_lb * 4) / 4
    if abs(q - min_lb) <= tolerance + 1e-9:
        return f"{q:.2f}"
    return "other"


def clean_html_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", html)
    t = t.replace("&#8211;", "–").replace("&nbsp;", " ").replace("&amp;", "&")
    t = t.replace("&#8217;", "'").replace("&#8216;", "'")
    return re.sub(r"\s+", " ", t).strip()
