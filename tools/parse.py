#!/usr/bin/env python3
"""Parse one fetch run into indicator rows. Append-only.

Reads <title>/captures/<run_id>/<source>/capture.json, applies the parser
named in sources.json, and appends rows to <title>/data/indicators.jsonl.
Every row points at the exact capture file and its SHA-256. A parser that
cannot find what it expects raises ParseFailure; the source is recorded as
PARSE_FAILED in data/flags.jsonl, never guessed at. Rows are never edited.

Usage:
    python3 tools/parse.py --title lobster --run-id <id>

Parsers foss_trade, bls_api, ers_fpo are forked from the wedding lobster
monitor. dmr_landings_pdf is new: Maine DMR monthly landings (pounds, value)
and the derived ex-vessel price per pound.
"""

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, Title, append_jsonl, iso, load_json, read_jsonl  # noqa: E402

LB_PER_KG = 2.20462262


class ParseFailure(Exception):
    pass


def fetch_entry(rec, name):
    return next((f for f in rec["fetches"] if f["name"] == name), None)


def read_fetch(rec, name):
    f = fetch_entry(rec, name)
    if not f or f["status"] != "OK":
        raise ParseFailure(f"fetch '{name}' not available: {(f or {}).get('error')}")
    return f, (ROOT / f["path"]).read_bytes()


# ---------- NOAA FOSS trade ----------

def p_foss_trade(rec, src, args):
    out = []
    for f in rec["fetches"]:
        if f["status"] != "OK":
            continue
        items = json.loads((ROOT / f["path"]).read_bytes()).get("items", [])
        by = {}
        for it in items:
            name = it.get("name", "")
            if not all(w in name for w in args["expect_name_contains"]):
                raise ParseFailure(f"unexpected commodity name '{name}' for HTS "
                                   f"{it.get('hts_number')}")
            period = f"{it['year']}-{it['month']}"
            scopes = ["US_ALL_DISTRICTS"]
            if "PORTLAND" in (it.get("custom_district_name") or ""):
                scopes.append("PORTLAND_ME")
            for scope in scopes:
                d = by.setdefault((period, scope), {"kilos": 0.0, "val": 0.0, "rows": 0})
                d["kilos"] += float(it.get("kilos") or 0)
                d["val"] += float(it.get("val") or 0)
                d["rows"] += 1
        for (period, scope), d in sorted(by.items()):
            if d["kilos"] <= 0:
                continue
            per_lb = d["val"] / d["kilos"] / LB_PER_KG
            out.append(dict(series_id=f"foss_imp_live_homarus_{scope.lower()}_usd_per_lb",
                            series_title=f"NOAA FOSS imports, live lobster Homarus spp. "
                                         f"(HTS 0306320010), {scope}: implicit unit value USD/lb",
                            period=period, value=round(per_lb, 4), unit="USD per lb",
                            evidence_fetch=f["name"],
                            notes=f"val {d['val']:.0f} USD / kilos {d['kilos']:.0f} / "
                                  f"{LB_PER_KG} lb per kg; {d['rows']} rows summed."))
            out.append(dict(series_id=f"foss_imp_live_homarus_{scope.lower()}_kilos",
                            series_title=f"NOAA FOSS imports, live lobster Homarus spp., "
                                         f"{scope}: kilos",
                            period=period, value=round(d["kilos"], 0), unit="kg",
                            evidence_fetch=f["name"], notes=f"{d['rows']} rows summed."))
    if not out:
        raise ParseFailure("no FOSS rows parsed")
    return out


# ---------- BLS API v1 ----------

def p_bls_api(rec, src, args):
    out = []
    for f in rec["fetches"]:
        if f["status"] != "OK":
            continue
        j = json.loads((ROOT / f["path"]).read_bytes())
        if j.get("status") != "REQUEST_SUCCEEDED":
            raise ParseFailure(f"{f['name']}: BLS status {j.get('status')} {j.get('message')}")
        for s in j["Results"]["series"]:
            sid = s["seriesID"]
            for d in s["data"]:
                if not d["period"].startswith("M") or d["period"] == "M13":
                    continue
                prelim = any(fn.get("code") == "P" for fn in d.get("footnotes", []) if fn)
                try:
                    val = float(d["value"])
                    note = "preliminary" if prelim else ""
                except (TypeError, ValueError):
                    val, note = None, f"value not numeric as published: {d['value']!r}"
                out.append(dict(series_id=sid, series_title=args["titles"].get(sid, sid),
                                period=f"{d['year']}-{d['period'][1:]}", value=val,
                                unit="index", evidence_fetch=f["name"], notes=note))
    if not out:
        raise ParseFailure("no BLS rows parsed")
    return out


# ---------- USDA ERS Food Price Outlook ----------

ERS_CATEGORIES = {"food away from home", "fish and seafood", "all food", "food at home"}


def _xlsx_rows(body):
    import xml.etree.ElementTree as ET
    import zipfile
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    t_tag = "{%s}t" % ns["m"]
    z = zipfile.ZipFile(io.BytesIO(body))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter(t_tag)))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for r in sheet.iter("{%s}row" % ns["m"]):
        cells = {}
        for c in r.findall("m:c", ns):
            colref = re.match(r"[A-Z]+", c.get("r")).group(0)
            v = c.find("m:v", ns)
            if v is not None:
                cells[colref] = shared[int(v.text)] if c.get("t") == "s" else v.text
            elif c.get("t") == "inlineStr":
                cells[colref] = "".join(x.text or "" for x in c.iter(t_tag))
        rows.append(cells)
    return rows


def _ers_clean_header(h):
    h = re.sub(r"\s*\d/(?:,\s*\d/)*\s*$", "", h.strip())
    h = re.sub(r"\((percent(?:age change)?)\)", "", h, flags=re.I)
    return re.sub(r"\s+", " ", h).strip()


def p_ers_fpo(rec, src, args):
    f, body = read_fetch(rec, "cpi_csv")
    out = []
    if body[:4] == b"PK\x03\x04":
        rows = _xlsx_rows(body)
        header = next((r for r in rows
                       if (r.get("A") or "").strip() == "Consumer Price Index item"), None)
        if not header:
            raise ParseFailure("xlsx: header row 'Consumer Price Index item' not found")
        for r in rows:
            cat = (r.get("A") or "").strip()
            if cat.lower() not in ERS_CATEGORIES:
                continue
            for colref, htext in header.items():
                if colref == "A" or not htext:
                    continue
                try:
                    val = float(r.get(colref))
                except (TypeError, ValueError):
                    continue
                unit = "Percent" if "(percent)" in htext.lower() else "Percent change"
                attr = _ers_clean_header(htext)
                out.append(dict(series_id=f"ers_fpo|{cat}|{attr}",
                                series_title=f"USDA ERS Food Price Outlook: {cat} — {attr}",
                                period=None, value=val, unit=unit, evidence_fetch="cpi_csv",
                                notes="xlsx column header, footnote markers removed"))
    else:
        text = body.decode("utf-8-sig", "ignore")
        reader = csv.DictReader(text.splitlines())
        if not reader.fieldnames or "Attribute" not in reader.fieldnames:
            raise ParseFailure(f"csv: unexpected header {reader.fieldnames}")
        for row in reader:
            cat = next((row[k] for k in ("Disaggregate", "Low-level", "Mid-level",
                                         "Aggregate", "Top-level") if row.get(k)), "")
            if cat.strip().lower() not in ERS_CATEGORIES:
                continue
            attr = (row.get("Attribute") or "").strip()
            try:
                val = float(row.get("Value"))
            except (TypeError, ValueError):
                continue
            out.append(dict(series_id=f"ers_fpo|{cat.strip()}|{attr}",
                            series_title=f"USDA ERS Food Price Outlook: {cat.strip()} — {attr}",
                            period=None, value=val, unit=(row.get("Unit") or "").strip(),
                            evidence_fetch="cpi_csv", notes="attribute text verbatim"))
    if not out:
        raise ParseFailure("no ERS rows matched expected categories")
    return out


# ---------- Maine DMR landings PDF ----------

def _pdf_text(body):
    """Text of a PDF with layout preserved. pdftotext (poppler) first, then
    pdfplumber if installed. No silent fallback: raises if neither exists."""
    if shutil.which("pdftotext"):
        p = subprocess.run(["pdftotext", "-layout", "-", "-"], input=body,
                           capture_output=True, check=True)
        return p.stdout.decode("utf-8", "ignore")
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise ParseFailure("no PDF text extractor: install poppler (pdftotext) or pdfplumber")
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        return "\n".join((pg.extract_text(layout=True) or "") for pg in pdf.pages)


DMR_MONTH_ROW = re.compile(r"^\s*(\d{4})\s+(\d{1,2})\s+([\d,]+)\s+\$([\d,]+)")


def p_dmr_landings_pdf(rec, src, args):
    """Maine DMR 'Lobster Landings By Month' table: year, month, pounds, value.
    The month table is the left-most block on each page, so it is the only
    block whose row starts with 'YYYY M'. County and zone blocks are ignored.
    Ex-vessel USD/lb = value / pounds, computed here and labeled derived."""
    f, body = read_fetch(rec, "pdf")
    text = _pdf_text(body)
    m = re.search(r"as of\s+(\d{1,2}/\d{1,2}/\d{4})", text)
    asof = m.group(1) if m else None
    prelim_years = set(re.findall(r"\*(\d{4}) data are preliminary", text))
    seen, out = set(), []
    for line in text.splitlines():
        r = DMR_MONTH_ROW.match(line)
        if not r:
            continue
        y, mo, lb, usd = r.group(1), int(r.group(2)), int(r.group(3).replace(",", "")), \
            int(r.group(4).replace(",", ""))
        if not 1 <= mo <= 12 or (y, mo) in seen:
            continue
        seen.add((y, mo))
        period = f"{y}-{mo:02d}"
        note = f"DMR file as of {asof}." + (" Preliminary." if y in prelim_years else "")
        out.append(dict(series_id="dmr_maine_lobster_landings_lb",
                        series_title="Maine DMR: lobster landings, pounds (statewide, by month)",
                        period=period, value=float(lb), unit="lb", evidence_fetch="pdf",
                        notes=note))
        out.append(dict(series_id="dmr_maine_lobster_landings_value_usd",
                        series_title="Maine DMR: lobster landings, ex-vessel value USD (statewide, by month)",
                        period=period, value=float(usd), unit="USD", evidence_fetch="pdf",
                        notes=note))
        if lb > 0:
            out.append(dict(series_id="dmr_maine_lobster_ex_vessel_usd_per_lb",
                            series_title="Maine DMR: lobster ex-vessel price USD/lb (derived: value / pounds)",
                            period=period, value=round(usd / lb, 4), unit="USD per lb",
                            evidence_fetch="pdf",
                            notes=note + f" Derived from {usd} USD / {lb} lb."))
    if len(seen) < 12:
        raise ParseFailure(f"DMR month table: only {len(seen)} rows matched")
    return out


PARSERS = {"foss_trade": p_foss_trade, "bls_api": p_bls_api, "ers_fpo": p_ers_fpo,
           "dmr_landings_pdf": p_dmr_landings_pdf}


def flag(t, run_id, source_id, kind, detail):
    append_jsonl(t.flags, {"run_id": run_id, "source_id": source_id, "flag": kind,
                           "detail": detail, "logged_at": iso()})
    print(f"    FLAG {kind}: {detail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    t = Title(a.title)
    run_dir = t.captures / a.run_id
    if not run_dir.is_dir():
        sys.exit(f"no capture run at {run_dir}")
    t.data.mkdir(exist_ok=True)
    existing = {(r["run_id"], r["series_id"], r.get("period"), r.get("value"))
                for r in read_jsonl(t.indicators)}
    summary = {"run_id": a.run_id, "sources": {}}
    for src in t.sources():
        cap = run_dir / src["id"] / "capture.json"
        if not cap.exists():
            continue
        rec = load_json(cap)
        print(f"  {src['id']:<22}", end="", flush=True)
        if rec["status"] == "FAILED":
            print("FAILED_CAPTURE")
            flag(t, a.run_id, src["id"], "FAILED_CAPTURE", "; ".join(rec["errors"])[:400])
            summary["sources"][src["id"]] = {"status": "FAILED_CAPTURE"}
            continue
        try:
            rows = PARSERS[src["parser"]](rec, src, src.get("parser_args") or {})
        except ParseFailure as e:
            print(f"PARSE_FAILED: {e}")
            flag(t, a.run_id, src["id"], "PARSE_FAILED", str(e))
            summary["sources"][src["id"]] = {"status": "PARSE_FAILED", "error": str(e)}
            continue
        n = 0
        for r in rows:
            f = fetch_entry(rec, r.pop("evidence_fetch")) or {}
            key = (a.run_id, r["series_id"], r.get("period"), r.get("value"))
            if key in existing:
                continue
            existing.add(key)
            append_jsonl(t.indicators, {
                "run_id": a.run_id, "captured_at": rec["captured_at"],
                "observation_type": "CONTEMPORANEOUS_CAPTURE",
                "source_id": src["id"], "source_label": src["label"],
                "evidence_path": f.get("path"), "sha256": f.get("sha256"),
                "source_url": f.get("final_url") or f.get("requested_url")} | r)
            n += 1
        st = rec["status"]
        print(f"{st} ({n} indicator rows)")
        summary["sources"][src["id"]] = {"status": st, "rows": n}
    append_jsonl(t.runs, summary | {"parsed_at": iso()})
    print(json.dumps(summary))


if __name__ == "__main__":
    sys.exit(main())
