#!/usr/bin/env python3
"""Check that every figure an issue quotes appears in its computed set.

Standard 1.2 §8.3 requires that an edition quote no figure absent from the
computed set. This tool checks it mechanically rather than by the editor's eye.
It reads `issue.md` and `numbers.md`, pulls out the figures each one asserts,
and reports any that cannot be found in `numbers.json`.

What counts as an asserted figure:

  In a table row, only the value cells. The first cell names the measure and
  the last names the source, and both carry numbers that are labels rather
  than claims: "40-pound block", "1,000 head", "600-900 lb", "report 2461".

  In prose, only a number carrying a unit: a percent sign, a currency symbol,
  or a following unit word. A bare number in prose is usually a year, a count
  of sellers, or a section reference.

Dates, years, series identifiers, URLs and anything inside backticks are
removed before matching, in prose and in table cells alike.

A figure is present if numbers.json holds it exactly, or holds a value equal
to it once rounded to the decimal places the prose used, so prose writing 1.58
for a stored 1.5790 passes and prose writing 1.62 does not. Signs are ignored
when matching, because prose writes a fall as a positive number as often as a
negative one. A figure written with a scale word is matched at the precision
of that scale, so "132.6 million pounds" matches a stored 132,604,691.

What this tool does not do. It checks that a figure exists somewhere in the
computed set, not that the prose attached it to the right measure: a figure
that happens to equal an unrelated stored value passes. A clean run means no
figure was invented, not that every figure was used correctly. The editor
still reads the issue.

Usage:
    python3 tools/check.py --title cheddar --issue 2026-09-baseline
    python3 tools/check.py --all
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Title, config, load_json  # noqa: E402

NUMBER = re.compile(r"(?<![\w.$-])(\d[\d,]*(?:\.\d+)?)")
UNIT_NUMBER = re.compile(
    r"(?:[$£€]\s?(\d[\d,]*(?:\.\d+)?)"
    r"|(\d[\d,]*(?:\.\d+)?)\s*(?:%|percent\b|cents\b|"
    r"(?P<scale>million|billion|thousand)\b|a pound\b|per pound\b|per lb\b|/lb\b|"
    r"per cwt\b|/cwt\b|head\b|pounds\b|lb\b|bags\b|dozen\b))")
STRIP = [
    re.compile(r"`[^`]*`"),                       # code spans: run ids, paths
    re.compile(r"https?://\S+"),                  # urls
    re.compile(r"\b[0-9a-f]{16,}\b"),             # hashes
    re.compile(r"(?:19|20)\d{2}-\d{2}(?:-\d{2})?"),   # iso periods
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s*(?:19|20)\d{2}"),
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(?:19|20)\d{2}"),
    re.compile(r"\b(?:19|20)\d{2}\b"),            # bare years
    re.compile(r"\b(?:WPU|CUUR|CUUS|APU|SEF|SS)[0-9A-Z]+\b"),  # series ids
    re.compile(r"§\s?\d+(?:\.\d+)?"),        # section references
    re.compile(r"\bFA-D-\d+-\d+\b"),
    re.compile(r"\b(?:RFC|HTS)\s?\d+\b"),
]


def scrub(s):
    for rx in STRIP:
        s = rx.sub(" ", s)
    return s


def stored_values(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            stored_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            stored_values(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.add(abs(float(obj)))
    elif isinstance(obj, str):
        # a figure stored as a string is still in the computed set: size
        # classes and some source fields come through as text
        t = obj.replace(",", "").strip().lstrip("$")
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", t):
            out.add(abs(float(t)))
    return out


def present(val, stored, places, scale=1.0):
    """A figure is present if the computed set holds it at the precision the
    prose used. `scale` is the prose's unit relative to the stored one, so
    "132.6 million pounds" matches a stored 132,604,691 pounds."""
    val = abs(val)
    for s in stored:
        t = s / scale
        if t == val or round(t, places) == round(val, places):
            return True
    return False


SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9}


def asserted_figures(text):
    """(raw, values, decimal places) for every figure the text asserts. A
    figure written with a scale word matches either the number as written or
    the number it scales to, because prose says "132.6 million pounds" for a
    computed set holding the pounds themselves."""
    out = []

    def add(raw, scale=None):
        txt = raw.replace(",", "")
        try:
            val = float(txt)
        except ValueError:
            return
        places = len(txt.split(".")[1]) if "." in txt else 0
        scales = [1.0] + ([SCALES[scale]] if scale in SCALES else [])
        out.append((raw, val, places, scales))

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("|---") or s.startswith("---"):
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 3:
                continue
            for cell in cells[1:-1]:          # value cells only
                clean = scrub(cell)
                for m in NUMBER.findall(clean):
                    sc = re.search(re.escape(m) + r"\s*(thousand|million|billion)\b", clean)
                    add(m, sc.group(1) if sc else None)
        else:
            for m in UNIT_NUMBER.finditer(scrub(s)):
                add(m.group(1) or m.group(2), m.group("scale"))
    return out


def check_issue(slug, issue_id):
    d = Title(slug).issues / issue_id
    nj = d / "numbers.json"
    if not nj.exists():
        return {"issue": f"{slug}/{issue_id}", "error": "no numbers.json"}
    stored = stored_values(load_json(nj), set())
    missing, checked = [], 0
    for name in ("issue.md", "numbers.md"):
        f = d / name
        if not f.exists():
            continue
        body = f.read_text()
        # the record section lists capture urls and hashes, not market claims
        body = re.split(r"^#{1,4}\s+(?:The record|Record)\s*$", body, flags=re.M)[0]
        for raw, val, places, scales in asserted_figures(body):
            checked += 1
            if not any(present(val, stored, places, sc) for sc in scales):
                missing.append({"file": name, "figure": raw})
    return {"issue": f"{slug}/{issue_id}", "figures_checked": checked,
            "not_in_computed_set": missing, "pass": not missing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title")
    ap.add_argument("--issue")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        targets = []
        for slug in config()["titles"]:
            t = Title(slug)
            if t.issues.exists():
                targets += [(slug, p.name) for p in sorted(t.issues.iterdir()) if p.is_dir()]
    elif a.title and a.issue:
        targets = [(a.title, a.issue)]
    else:
        sys.exit("give --title and --issue, or --all")
    results = [check_issue(s, i) for s, i in targets]
    for r in results:
        if r.get("error"):
            print(f"  ??   {r['issue']:<28} {r['error']}")
            continue
        print(f"  {'OK  ' if r['pass'] else 'FAIL'} {r['issue']:<28} "
              f"{r['figures_checked']:>4} figures checked")
        for m in r["not_in_computed_set"]:
            print(f"         {m['figure']} ({m['file']})")
    bad = [r for r in results if not r.get("pass")]
    print(json.dumps({"issues": len(results), "failing": len(bad)}))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
