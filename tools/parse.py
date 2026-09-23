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
and the derived ex-vessel price per pound. ndpsr_json, dmn_weekly_pdf,
ams_shell_egg_pdf and nass_ckeg_txt serve the Egg & Butter Brief. Weekly
series use a YYYY-MM-DD week-ending period; monthly series use YYYY-MM.
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
    cats = {c.lower() for c in args.get("categories", ERS_CATEGORIES)}
    out = []
    if body[:4] == b"PK\x03\x04":
        rows = _xlsx_rows(body)
        header = next((r for r in rows
                       if (r.get("A") or "").strip() == "Consumer Price Index item"), None)
        if not header:
            raise ParseFailure("xlsx: header row 'Consumer Price Index item' not found")
        for r in rows:
            cat = (r.get("A") or "").strip()
            if cat.lower() not in cats:
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
            if cat.strip().lower() not in cats:
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



# ---------- USDA AMS NDPSR (National Dairy Products Sales Report), Datamart JSON ----------

def _us_date(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    if not m:
        raise ParseFailure(f"date not MM/DD/YYYY: {s!r}")
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"


def p_ndpsr_json(rec, src, args):
    """Datamart report 2993, section 'Butter Prices and Sales'. Each published
    report (week_ending_date) restates the five most recent data weeks
    ('Week Ending Date'), so a data week appears in up to five reports. The
    row from the latest report that carries a data week is used (the most
    revised figure); the first-published figure is retained in notes."""
    f, body = read_fetch(rec, "butter")
    j = json.loads(body)
    rows = j.get("results") or []
    if not rows or "Butter_Price" not in rows[0]:
        raise ParseFailure("NDPSR: no results or Butter_Price column missing")
    best, first = {}, {}
    for r in rows:
        wk = _us_date(r.get("Week Ending Date"))
        rep = _us_date(r.get("week_ending_date"))
        try:
            price = float(r["Butter_Price"])
            sales = float(str(r["Butter_Sales"]).replace(",", ""))
        except (TypeError, ValueError, KeyError):
            continue
        if wk not in best or rep > best[wk][0]:
            best[wk] = (rep, price, sales)
        if wk not in first or rep < first[wk][0]:
            first[wk] = (rep, price, sales)
    out = []
    for wk in sorted(best):
        rep, price, sales = best[wk]
        note = f"latest revision, report week {rep}"
        if first[wk][1] != price:
            note += f"; first published {first[wk][1]} in report week {first[wk][0]}"
        out.append(dict(series_id="ndpsr_butter_usd_per_lb",
                        series_title="USDA AMS NDPSR: butter, weighted average price USD/lb (week ending)",
                        period=wk, value=round(price, 4), unit="USD per lb",
                        evidence_fetch="butter", notes=note))
        out.append(dict(series_id="ndpsr_butter_sales_lb",
                        series_title="USDA AMS NDPSR: butter, sales volume lb (week ending)",
                        period=wk, value=round(sales, 0), unit="lb",
                        evidence_fetch="butter", notes=note))
    if len(best) < 52:
        raise ParseFailure(f"NDPSR: only {len(best)} data weeks parsed")
    return out


# ---------- USDA AMS Dairy Market News weekly PDF: CME butter at a glance ----------

DMN_DATE = re.compile(r"CME GROUP CASH MARKETS \((\d{1,2})/(\d{1,2})\)")
DMN_HEAD = re.compile(r"DAIRY MARKET NEWS,\s+([A-Z]+)\s+\d{1,2}\s*[–-]\s*(\d{1,2}),\s*(\d{4})")
MONTHS = {m: i for i, m in enumerate(["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
                                      "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"], 1)}


def p_dmn_weekly_pdf(rec, src, args):
    """Page 1 'At a Glance': CME Grade AA butter Friday close and weekly average,
    as reprinted by USDA AMS. Two-column layout: pdftotext -layout interleaves
    columns, so whitespace between the words is collapsed before matching."""
    f, body = read_fetch(rec, "pdf")
    text = _pdf_text(body)
    flat = re.sub(r"[ \t]+", " ", text)
    # remove the right-hand column bleed: join lines, then match with .{0,200}? between phrases
    m = re.search(r"BUTTER: Grade AA closed at \$([\d.]+)\..{0,400}?weekly average for Grade.{0,300}?\bAA is \$([\d.]+)", flat, re.S)
    if not m:
        raise ParseFailure("DMN: butter 'At a Glance' pattern not found")
    h = DMN_HEAD.search(text)
    if not h:
        raise ParseFailure("DMN: report week header not found")
    week_end = f"{h.group(3)}-{MONTHS[h.group(1)]:02d}-{int(h.group(2)):02d}"
    note = "CME Group cash market, as reprinted by USDA AMS Dairy Market News; CME data is proprietary at source"
    return [dict(series_id="cme_butter_aa_friday_close_usd_per_lb",
                 series_title="CME Grade AA butter, Friday close USD/lb (via USDA AMS DMN)",
                 period=week_end, value=float(m.group(1)), unit="USD per lb",
                 evidence_fetch="pdf", notes=note),
            dict(series_id="cme_butter_aa_weekly_avg_usd_per_lb",
                 series_title="CME Grade AA butter, weekly average USD/lb (via USDA AMS DMN)",
                 period=week_end, value=float(m.group(2)), unit="USD per lb",
                 evidence_fetch="pdf", notes=note)]


# ---------- USDA AMS Weekly Combined Regional Shell Egg Report PDF ----------

SHELL_ROW = re.compile(r"^\s*(Extra Large|Large|Medium|Small)\s+([\d.]+)\s*-\s*([\d.]+)\s+([\d.]+)\s+([+-]?[\d.]+)\s+([\d.]+)")


def p_ams_shell_egg_pdf(rec, src, args):
    """Blocks are 'Region Shell Eggs - Caged' then a channel line, then class
    rows: range, average, change, last reported. Series per (region, channel,
    class). Period is the report week's end date."""
    f, body = read_fetch(rec, "pdf")
    text = _pdf_text(body)
    m = re.search(r"Report for:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})", text)
    if not m:
        raise ParseFailure("shell egg: 'Report for' week not found")
    week_end = _us_date(m.group(2))
    region = channel = None
    out = []
    want = args.get("want")  # list of [region, channel, class] triples, or None for all
    for line in text.splitlines():
        r = re.match(r"^\s*(\w[\w ]+?) Shell Eggs - Caged\s*$", line)
        if r:
            region = r.group(1).strip(); channel = None; continue
        c = re.match(r"^\s*(Delivered Warehouse|Delivered Store Door|Paid to Producers[^,]*), White, Cents Per Dozen", line)
        if c:
            channel = c.group(1).strip(); continue
        row = SHELL_ROW.match(line)
        if row and region and channel:
            cls = row.group(1)
            if want and [region, channel, cls] not in want:
                continue
            slug = re.sub(r"[^a-z0-9]+", "_", f"{region} {channel} {cls}".lower()).strip("_")
            out.append(dict(series_id=f"ams_shell_egg_{slug}_cents_per_dozen",
                            series_title=f"USDA AMS shell eggs, caged, white: {region}, {channel}, {cls}, average cents/dozen",
                            period=week_end, value=float(row.group(4)), unit="cents per dozen",
                            evidence_fetch="pdf",
                            notes=f"range {row.group(2)}-{row.group(3)}; change {row.group(5)}; last reported {row.group(6)}"))
    if not out:
        raise ParseFailure("shell egg: no class rows matched")
    return out


# ---------- USDA NASS Chickens and Eggs, monthly text ----------

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]


def _nass_table(text, heading):
    """Lines of the first table whose heading line starts with `heading`."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith(heading) and not re.search(r"\.{3,}\s*\d+\s*$", ln):  # skip the contents entry
            block = []
            for x in lines[i + 1:]:
                block.append(x)
                if x.strip().startswith("1/ December previous year"):
                    return block
            return block
    raise ParseFailure(f"NASS: table '{heading}' not found")


def _nass_years(block):
    for ln in block:
        m = re.findall(r"\b(20\d{2})\b", ln)
        if len(m) >= 2 and ":" in ln:
            return m
    raise ParseFailure("NASS: year header not found")


def p_nass_ckeg_txt(rec, src, args):
    f, body = read_fetch(rec, "txt")
    text = body.decode("utf-8", "ignore")
    rel = re.search(r"Released ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    note = f"NASS release {rel.group(1) if rel else 'date not found'}"
    out = []
    # layers: two columns (prior year, current year)
    blk = _nass_table(text, "Average Layers During the Month - United States")
    years = _nass_years(blk)[:2]
    n = 0
    for ln in blk:
        m = re.match(r"^\s*([A-Z][a-z]+)(?: 1/)?\s*\.+:\s*([\d,]+)?\s+([\d,]+)?", ln)
        if not m or m.group(1) not in MONTH_NAMES:
            continue
        mo = MONTH_NAMES.index(m.group(1)) + 1
        for yi, val in ((0, m.group(2)), (1, m.group(3))):
            if val is None:
                continue
            y = int(years[yi]) - (1 if m.group(1) == "December" else 0)
            out.append(dict(series_id="nass_layers_avg_thousand",
                            series_title="USDA NASS Chickens and Eggs: average layers during the month, U.S. (1,000 layers)",
                            period=f"{y}-{mo:02d}", value=float(val.replace(",", "")), unit="1,000 layers",
                            evidence_fetch="txt", notes=note)); n += 1
    # table egg production: six columns, table eggs are columns 3 and 4
    blk = _nass_table(text, "Egg Production During the Month by Type - United States")
    years = _nass_years(blk)[:2]
    for ln in blk:
        m = re.match(r"^\s*([A-Z][a-z]+)(?: 1/)?\s*\.+:\s*(.*)$", ln)
        if not m or m.group(1) not in MONTH_NAMES:
            continue
        vals = re.findall(r"[\d,]+\.\d", m.group(2))
        # column layout: total(2), table(2), hatching(2); blanks collapse, so use positions only when all six present or three (prior-year only)
        mo = MONTH_NAMES.index(m.group(1)) + 1
        if len(vals) == 6:
            pairs = ((0, vals[2]), (1, vals[3]))
        elif len(vals) == 3:
            pairs = ((0, vals[1]),)
        else:
            continue
        for yi, val in pairs:
            y = int(years[yi]) - (1 if m.group(1) == "December" else 0)
            out.append(dict(series_id="nass_table_egg_production_million",
                            series_title="USDA NASS Chickens and Eggs: table egg production during the month, U.S. (million eggs)",
                            period=f"{y}-{mo:02d}", value=float(val.replace(",", "")), unit="million eggs",
                            evidence_fetch="txt", notes=note)); n += 1
    if n < 20:
        raise ParseFailure(f"NASS: only {n} rows parsed")
    return out

def p_retain_only(rec, src, args):
    """Evidence retained for the editor; no indicator rows. Fails if the fetch failed."""
    read_fetch(rec, src["fetches"][0]["name"] if src.get("fetches") else "pdf")
    return []


PARSERS = {"retain_only": p_retain_only, "foss_trade": p_foss_trade, "bls_api": p_bls_api, "ers_fpo": p_ers_fpo,
           "dmr_landings_pdf": p_dmr_landings_pdf, "ndpsr_json": p_ndpsr_json,
           "dmn_weekly_pdf": p_dmn_weekly_pdf, "ams_shell_egg_pdf": p_ams_shell_egg_pdf,
           "nass_ckeg_txt": p_nass_ckeg_txt}


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
