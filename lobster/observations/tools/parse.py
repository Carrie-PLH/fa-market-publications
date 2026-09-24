#!/usr/bin/env python3
"""Parse one capture run into observations. Append-only.

Reads captures/<run_id>/<source>/capture.json, applies the parser named in
sources.json, and appends rows to data/observations.jsonl (retail products)
and data/indicators.jsonl (official series). Every row points at the exact
capture file and its SHA-256. Failures are written as rows too: a source
whose capture failed produces FAILED_CAPTURE rows for every product it
listed before, and a product that disappears produces an UNAVAILABLE row.
A parser that cannot find what it expects raises, and the source is recorded
as PARSE_FAILED rather than guessed at.

Usage:
    python3 tools/parse.py --run-id <id> [--observation-type CONTEMPORANEOUS_CAPTURE]

Stdlib only.
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CAPTURES, CONTEMPORANEOUS, DATA, INDICATORS,  # noqa: E402
                    OBSERVATIONS, OBSERVATIONS_CSV, OBSERVATION_FIELDS, REGISTRY,
                    ROOT, append_jsonl, clean_html_text, config, iso, load_json,
                    parse_size, read_jsonl, size_class, sources)

FLAGS = DATA / "flags.jsonl"
LB_PER_KG = 2.20462262


class ParseFailure(Exception):
    pass


def fetch_entry(rec, name):
    for f in rec["fetches"]:
        if f["name"] == name:
            return f
    return None


def read_fetch(rec, name):
    f = fetch_entry(rec, name)
    if not f or f["status"] != "OK":
        raise ParseFailure(f"fetch '{name}' not available: "
                           f"{(f or {}).get('error')}")
    return f, (ROOT / f["path"]).read_bytes()


def money_minor(s, minor_unit=2):
    if s in (None, ""):
        return None
    return round(int(s) / (10 ** minor_unit), 2)


# ---------- retail parsers ----------

def p_taylor_text(rec, src, args):
    f, body = read_fetch(rec, "page")
    text = clean_html_text(body.decode("utf-8", "ignore"))
    m = re.search(r"\b(SOFT|HARD|NEW)\s+SHELL\s+Lobster\s+Prices\s+"
                  r"(\d{1,2}/\s?\d{1,2}\s?/\s?\d{4})(.{0,600})", text, re.I)
    if not m:
        raise ParseFailure("Taylor price block header not found "
                           "('<SHELL TYPE> SHELL Lobster Prices M/D/YYYY')")
    shell_word = m.group(1).upper()
    shell = {"SOFT": "soft", "NEW": "soft", "HARD": "hard"}[shell_word]
    stated_date = re.sub(r"\s", "", m.group(2))
    block = m.group(3)
    rows = []
    # e.g. "1 lb (chix) – $8.99/lb", "1 1/4 lbs – $9.99/lb", "Selects – $10.99/lb",
    # "Fresh picked lobster meat – $59.99/lb"
    for label, price in re.findall(
            r"([A-Za-z0-9 /()]+?)\s*[–-]\s*\$(\d+(?:\.\d\d)?)\s*/\s*lb", block):
        label = label.strip()
        low = label.lower()
        if "meat" in low:
            rows.append(dict(product_key="meat_fresh_picked", product_name=label,
                             product_category="meat", shell_type=None,
                             advertised_size=None, quantity=None,
                             package_weight_lb=None, unit_of_sale="per_lb",
                             listed_price=float(price), regular_price=None,
                             promotional_price=None, on_sale=None,
                             availability_status="LISTED",
                             notes="Unspecified picked lobster meat, priced per lb."))
            continue
        if "select" in low:
            key, size = "selects", "Selects"
        elif "chix" in low or low.startswith("1 lb"):
            key, size = "chix_1lb", label
        elif "1/4" in low or "1.25" in low:
            key, size = "quarters_1.25lb", label
        elif "1/2" in low or "1.5" in low:
            key, size = "halves_1.5lb", label
        else:
            key, size = re.sub(r"\W+", "_", low), label
        rows.append(dict(product_key=key, product_name=f"{shell_word} SHELL {label}",
                         product_category="live", shell_type=shell,
                         advertised_size=size, quantity=None, package_weight_lb=None,
                         unit_of_sale="per_lb", listed_price=float(price),
                         regular_price=None, promotional_price=None, on_sale=None,
                         availability_status="LISTED",
                         notes=f"Shell type from page header '{shell_word} SHELL'. "
                               f"Price per lb; in-store pickup."))
    if not rows:
        raise ParseFailure("Taylor header found but no price lines parsed")
    for r in rows:
        r["source_stated_date"] = stated_date
        r["evidence_fetch"] = "page"
    return rows


def wc_attr(text, key):
    m = re.search(re.escape(key) + r":\s*([^,]+)", text or "")
    return m.group(1).strip() if m else None


def wc_row(p, category, shell, quantity, advertised_size, key, name, note):
    prices = p["prices"]
    mu = int(prices.get("currency_minor_unit", 2))
    price = money_minor(prices.get("price"), mu)
    regular = money_minor(prices.get("regular_price"), mu)
    sale = money_minor(prices.get("sale_price"), mu)
    on_sale = bool(p.get("on_sale")) or (regular is not None and price is not None
                                         and price < regular)
    return dict(product_key=key, product_name=name, product_category=category,
                shell_type=shell, advertised_size=advertised_size,
                quantity=quantity, package_weight_lb=None,
                unit_of_sale="per_pack" if quantity else "per_listing",
                listed_price=price, regular_price=regular,
                promotional_price=sale if on_sale else None, on_sale=on_sale,
                availability_status=("IN_STOCK" if p.get("is_in_stock")
                                     else "OUT_OF_STOCK"),
                notes=note)


def p_wc_store(rec, src, args):
    rows = []
    for fname, spec in (args.get("variation_fetches") or {}).items():
        f, body = read_fetch(rec, fname)
        items = json.loads(body)
        if not isinstance(items, list):
            raise ParseFailure(f"{fname}: expected JSON list")
        for p in items:
            if p.get("parent") != spec["parent_id"]:
                raise ParseFailure(f"{fname}: variation {p.get('id')} parent "
                                   f"{p.get('parent')} != {spec['parent_id']}")
            vtext = p.get("variation") or ""
            size = wc_attr(vtext, "Size") or wc_attr(vtext, "Size of Lobsters")
            n = wc_attr(vtext, "Number of Lobsters")
            variety = wc_attr(vtext, "Lobster Meat Variety")
            qty = int(n) if n and n.isdigit() else (1 if spec["category"] == "live" and size else None)
            name = clean_html_text(p["name"])
            if variety:
                name = f"{name} ({variety})"
            key = f"var{p['id']}"
            note = f"Variation '{vtext}'."
            if spec["category"] == "live" and qty == 1 and not n:
                note += " Quantity 1 assumed from per-size listing of a single lobster."
            r = wc_row(p, spec["category"], spec["shell"], qty, size, key, name, note)
            r["evidence_fetch"] = fname
            if spec.get("unit_of_sale"):
                r["unit_of_sale"] = spec["unit_of_sale"]
                r["notes"] += " Unit: " + spec.get("unit_note", spec["unit_of_sale"]) + "."
            if spec["category"] == "meat":
                r["notes"] += " Meat variety: " + (variety or "not stated") + "."
                desc = clean_html_text(p.get("description") or "")
                mw = re.search(r"(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound)s?\s*(?:cryo\s*vac\s*)?package",
                               desc, re.I)
                if mw:
                    r["package_weight_lb"] = float(mw.group(1))
                    r["unit_of_sale"] = "per_pack"
                    r["notes"] += f" Package weight from variation description: '{desc[:80]}'."
                else:
                    r["notes"] += " Package weight not stated in variation description."
            rows.append(r)
    if args.get("simple_name_regex"):
        rx = re.compile(args["simple_name_regex"], re.I)
        found = False
        for fname in [f["name"] for f in rec["fetches"] if f["name"].startswith("products")]:
            f, body = read_fetch(rec, fname)
            for p in json.loads(body):
                name = clean_html_text(p["name"])
                if p.get("type") not in ("simple", "variable") or not rx.search(name):
                    continue
                found = True
                shell = args.get("simple_shell")
                if shell == "from_name":
                    low = name.lower()
                    shell = "hard" if "hard shell" in low else \
                        "soft" if "soft shell" in low else "unspecified"
                r = wc_row(p, args["simple_category"], shell,
                           args.get("quantity_fixed"), name, f"p{p['id']}", name,
                           ("Simple product; size read from product name."
                            if p.get("type") == "simple" else
                            "Variable product; listed price is the parent's price "
                            "(WooCommerce reports the minimum across variations); "
                            "size read from product name."))
                r["evidence_fetch"] = fname
                rows.append(r)
        if not found:
            raise ParseFailure("no simple products matched simple_name_regex")
    for pid, spec in (args.get("simple_products") or {}).items():
        f, body = read_fetch(rec, "products")
        hit = [p for p in json.loads(body) if str(p.get("id")) == pid]
        if not hit:
            rows.append(dict(product_key=f"p{pid}", product_name=spec.get("note"),
                             product_category=spec["category"], shell_type=None,
                             advertised_size=None, quantity=None,
                             package_weight_lb=None, unit_of_sale="per_listing",
                             listed_price=None, regular_price=None,
                             promotional_price=None, on_sale=None,
                             availability_status="UNAVAILABLE_NOT_LISTED",
                             notes="Configured product id not in listing.",
                             evidence_fetch="products"))
            continue
        p = hit[0]
        name = clean_html_text(p["name"])
        r = wc_row(p, spec["category"], None, spec.get("quantity"), None, f"p{pid}", name,
                   spec.get("note", ""))
        r["evidence_fetch"] = "products"
        rows.append(r)
    if not rows:
        raise ParseFailure("no rows produced")
    return rows


def shopify_variant(v, product, category, shell, fmt, qty_fixed, qty_note):
    title = v.get("title") or ""
    size, qty = None, None
    if fmt == "size_slash_qty":
        m = re.match(r"^(.*?)\s*/\s*(\d+)\s*$", title)
        if not m:
            return None
        size, qty = m.group(1).strip(), int(m.group(2))
    elif fmt == "size_only":
        size, qty = title.strip(), qty_fixed
    else:
        return None
    price = float(v["price"]) if v.get("price") not in (None, "") else None
    cmp_ = v.get("compare_at_price")
    regular = float(cmp_) if cmp_ not in (None, "") else None
    on_sale = regular is not None and price is not None and price < regular
    note = f"Shopify variant '{title}'."
    if qty_note:
        note += " " + qty_note
    return dict(product_key=f"v{v['id']}",
                product_name=f"{product['title']} — {title}",
                product_category=category, shell_type=shell,
                advertised_size=size, quantity=qty, package_weight_lb=None,
                unit_of_sale="per_pack" if qty else "per_listing",
                listed_price=price, regular_price=regular,
                promotional_price=price if on_sale else None, on_sale=on_sale,
                availability_status=("IN_STOCK" if v.get("available")
                                     else "OUT_OF_STOCK"),
                notes=note, evidence_fetch="products")


def p_shopify_products(rec, src, args):
    f, body = read_fetch(rec, "products")
    products = json.loads(body).get("products")
    if products is None:
        raise ParseFailure("no 'products' key in Shopify JSON")
    rows = []
    specs = args.get("products")
    if specs:
        for spec in specs:
            hit = [p for p in products if p.get("handle") == spec["handle"]]
            if not hit:
                raise ParseFailure(f"handle '{spec['handle']}' not in products.json")
            for v in hit[0]["variants"]:
                r = shopify_variant(v, hit[0], spec["category"], spec["shell"],
                                    spec["variant_format"],
                                    spec.get("quantity_fixed"),
                                    spec.get("quantity_note"))
                if r:
                    rows.append(r)
    else:
        rx = re.compile(args["title_regex"], re.I)
        hit = [p for p in products if rx.search(p.get("title") or "")]
        if not hit:
            raise ParseFailure("title_regex matched no products")
        for p in hit:
            for v in p["variants"]:
                r = shopify_variant(v, p, args["category"], args["shell"],
                                    args["variant_format"],
                                    args.get("quantity_fixed"),
                                    args.get("quantity_note"))
                if r:
                    rows.append(r)
    if not rows:
        raise ParseFailure("no variants parsed")
    return rows


# ---------- indicator parsers (data/indicators.jsonl) ----------

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
            for scope in ("US_ALL_DISTRICTS",
                          "PORTLAND_ME" if "PORTLAND" in (it.get("custom_district_name") or "") else None):
                if not scope:
                    continue
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
                    val = None
                    note = f"value not numeric as published: {d['value']!r}"
                out.append(dict(series_id=sid,
                                series_title=args["titles"].get(sid, sid),
                                period=f"{d['year']}-{d['period'][1:]}",
                                value=val, unit="index",
                                evidence_fetch=f["name"], notes=note))
    if not out:
        raise ParseFailure("no BLS rows parsed")
    return out


ERS_CATEGORIES = {"food away from home", "fish and seafood", "all food", "food at home"}


def _xlsx_rows(body: bytes):
    """Rows of the first worksheet of an .xlsx as lists of cell strings.

    Stdlib only (zipfile + ElementTree): the repo carries no third-party
    dependencies, and the workbook ERS publishes is a single flat sheet.
    """
    import zipfile
    import xml.etree.ElementTree as ET
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


def _ers_clean_header(h: str) -> str:
    """'July 2025 to July 2026\n(percentage change) 2/' -> 'July 2025 to July 2026'.
    Footnote markers and the unit parenthetical are dropped; the wording is
    otherwise the workbook's own."""
    h = re.sub(r"\s*\d/(?:,\s*\d/)*\s*$", "", h.strip())
    h = re.sub(r"\((percent(?:age change)?)\)", "", h, flags=re.I)
    return re.sub(r"\s+", " ", h).strip()


def p_ers_fpo(rec, src, args):
    """USDA ERS Food Price Outlook table.

    ERS links the same table as a .csv (long form: Top-level ... Attribute,
    Unit, Value) and as an .xlsx (wide form: one row per item, one column per
    attribute). The first capture followed the .xlsx link, so both are read.
    The format is detected from the bytes, not the file name.
    """
    f, body = read_fetch(rec, "cpi_csv")
    out = []
    if body[:4] == b"PK\x03\x04":
        rows = _xlsx_rows(body)
        header = None
        for r in rows:
            if (r.get("A") or "").strip() == "Consumer Price Index item":
                header = r
                break
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
                                period=None, value=val, unit=unit,
                                evidence_fetch="cpi_csv",
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


def p_evidence_only(rec, src, args):
    return []


PARSERS = {"taylor_text": p_taylor_text, "wc_store": p_wc_store,
           "shopify_products": p_shopify_products, "foss_trade": p_foss_trade,
           "bls_api": p_bls_api, "ers_fpo": p_ers_fpo,
           "evidence_only": p_evidence_only}
INDICATOR_PARSERS = {"foss_trade", "bls_api", "ers_fpo"}


# ---------- finalize ----------

def finalize(row, rec, src, run_id, obs_type, tol):
    f = fetch_entry(rec, row.pop("evidence_fetch", None) or "") or {}
    min_lb, max_lb, single = parse_size(row.get("advertised_size"))
    cls = size_class(min_lb, max_lb, single, tol) if row["product_category"] == "live" \
        else ("n/a")
    if row["product_category"] == "live" and row.get("advertised_size") and min_lb is None:
        cls = "unsized"
    price = row.get("listed_price")
    qty = row.get("quantity")
    per_lobster = per_lb = per_tail = None
    unit = row.get("unit_of_sale")
    if price is not None:
        if unit == "per_lb":
            per_lb = price
        elif unit == "per_pack" and qty and row["product_category"] == "live":
            per_lobster = round(price / qty, 2)
        elif unit == "per_pack" and qty and row["product_category"] == "tail":
            per_tail = round(price / qty, 2)
        if row.get("package_weight_lb") and row["product_category"] in ("meat",):
            per_lb = round(price / row["package_weight_lb"], 2)
    shell = row.get("shell_type") or ("unspecified" if row["product_category"] == "live" else "n/a")
    qpart = f"q{qty}" if qty else "qNA"
    series = f"{src['id']}|{row['product_category']}|{shell}|{cls}|{unit}|{qpart}"
    if row["product_category"] != "live":
        # meat and tails are distinguished by product (variety, pack), not size class
        series += f"|{row['product_key']}"
    series_class = f"{row['product_category']}|{shell}|{cls}"
    render = rec.get("render") or {}
    out = {
        "observation_id": f"{run_id}|{src['id']}|{row['product_key']}",
        "run_id": run_id, "captured_at": rec["captured_at"],
        "observation_type": obs_type,
        "source_id": src["id"], "source_name": src["name"],
        "source_label": src["label"], "source_url": f.get("final_url") or src.get("page_url"),
        "product_key": row["product_key"], "product_name": row["product_name"],
        "product_category": row["product_category"],
        "lobster_origin": src.get("origin_claim"),
        "shell_type": shell, "advertised_size": row.get("advertised_size"),
        "minimum_weight_lb": min_lb, "maximum_weight_lb": max_lb,
        "size_class": cls, "quantity": qty,
        "package_weight_lb": row.get("package_weight_lb"), "unit_of_sale": unit,
        "listed_price": price, "currency": "USD",
        "normalized_price_per_lb": per_lb,
        "normalized_price_per_lobster": per_lobster,
        "normalized_price_per_tail": per_tail,
        "shipping_cost": None, "shipping_included": src.get("shipping_included"),
        "promotional_price": row.get("promotional_price"),
        "regular_price": row.get("regular_price"), "on_sale": row.get("on_sale"),
        "availability_status": row.get("availability_status"),
        "comparability_series": series, "series_class": series_class,
        "source_stated_date": row.get("source_stated_date"),
        "evidence_path": f.get("path"),
        "screenshot_path": (render.get("png") or {}).get("path"),
        "pdf_path": (render.get("pdf") or {}).get("path"),
        "raw_capture_path": f"captures/{run_id}/{src['id']}/capture.json",
        "sha256": f.get("sha256"),
        "notes": (row.get("notes") or "") + (" " + src["shipping_note"] if src.get("shipping_note") else ""),
    }
    if min_lb is not None and not single and cls not in ("other", "unsized"):
        out["notes"] += f" Size class {cls} assigned from minimum stated weight {min_lb} lb (range)."
    return out


def status_row(src, run_id, captured_at, obs_type, reg_entry, key, status, note):
    e = reg_entry
    return {fld: None for fld in OBSERVATION_FIELDS} | {
        "observation_id": f"{run_id}|{src['id']}|{key}", "run_id": run_id,
        "captured_at": captured_at, "observation_type": obs_type,
        "source_id": src["id"], "source_name": src["name"], "source_label": src["label"],
        "source_url": src.get("page_url"), "product_key": key,
        "product_name": e.get("product_name"), "product_category": e.get("product_category"),
        "shell_type": e.get("shell_type"), "advertised_size": e.get("advertised_size"),
        "size_class": e.get("size_class"), "quantity": e.get("quantity"),
        "unit_of_sale": e.get("unit_of_sale"), "currency": "USD",
        "availability_status": status, "comparability_series": e.get("comparability_series"),
        "series_class": e.get("series_class"),
        "raw_capture_path": f"captures/{run_id}/{src['id']}/capture.json", "notes": note}


REVISION_FIELDS = ("listed_price", "unit_of_sale", "quantity", "normalized_price_per_lb",
                   "normalized_price_per_lobster", "normalized_price_per_tail",
                   "comparability_series", "series_class", "shell_type", "size_class",
                   "product_category", "availability_status")


def row_differs(a, b):
    return any(a.get(k) != b.get(k) for k in REVISION_FIELDS)


def describe_diff(a, b):
    return "; ".join(f"{k}: {a.get(k)!r} -> {b.get(k)!r}" for k in REVISION_FIELDS
                     if a.get(k) != b.get(k))


def flag(run_id, source_id, kind, detail):
    append_jsonl(FLAGS, {"run_id": run_id, "source_id": source_id, "flag": kind,
                         "detail": detail, "logged_at": iso()})
    print(f"    FLAG {kind}: {detail}")


def rebuild_csv():
    rows = read_jsonl(OBSERVATIONS)
    with open(OBSERVATIONS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OBSERVATION_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in OBSERVATION_FIELDS})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--observation-type", default=CONTEMPORANEOUS)
    ap.add_argument("--no-registry", action="store_true",
                    help="do not update product registry or emit unavailable rows "
                         "(used for historical reconstruction)")
    args = ap.parse_args()
    cfg = config()
    tol = cfg.get("SIZE_CLASS_TOLERANCE_LB", 0.05)
    run_dir = CAPTURES / args.run_id
    if not run_dir.is_dir():
        sys.exit(f"no capture run at {run_dir}")
    DATA.mkdir(exist_ok=True)
    registry = load_json(REGISTRY) if REGISTRY.exists() else {}
    existing_rows = {}
    for r in read_jsonl(OBSERVATIONS):
        base = r["observation_id"].split("#r")[0]
        existing_rows[base] = r  # last line wins: highest revision
    existing_ids = set(existing_rows)
    existing_ind = {(r["run_id"], r["series_id"], r.get("period"), r.get("value"))
                    for r in read_jsonl(INDICATORS)}
    summary = {"run_id": args.run_id, "sources": {}}
    for src in sources():
        cap = run_dir / src["id"] / "capture.json"
        if not cap.exists():
            continue
        rec = load_json(cap)
        parser = PARSERS[src["parser"]]
        reg = registry.setdefault(src["id"], {})
        print(f"  {src['id']:<22}", end="", flush=True)
        if src["parser"] in INDICATOR_PARSERS or src["parser"] == "evidence_only":
            try:
                rows = parser(rec, src, src.get("parser_args") or {})
                for r in rows:
                    f = fetch_entry(rec, r.pop("evidence_fetch")) or {}
                    ikey = (args.run_id, r["series_id"], r.get("period"), r.get("value"))
                    if ikey in existing_ind:
                        continue
                    existing_ind.add(ikey)
                    append_jsonl(INDICATORS, {
                        "run_id": args.run_id, "captured_at": rec["captured_at"],
                        "observation_type": args.observation_type,
                        "source_id": src["id"], "source_label": src["label"],
                        "evidence_path": f.get("path"), "sha256": f.get("sha256"),
                        "source_url": f.get("final_url") or f.get("requested_url")} | r)
                st = "OK" if rec["status"] == "OK" else rec["status"]
                if rec["status"] == "FAILED":
                    st = "FAILED_CAPTURE"
                print(f"{st} ({len(rows)} indicator rows)")
                summary["sources"][src["id"]] = {"status": st, "rows": len(rows)}
            except ParseFailure as e:
                print(f"PARSE_FAILED: {e}")
                flag(args.run_id, src["id"], "PARSE_FAILED", str(e))
                summary["sources"][src["id"]] = {"status": "PARSE_FAILED", "error": str(e)}
            continue

        if rec["status"] == "FAILED":
            n = 0
            if not args.no_registry:
                for key, e in reg.items():
                    row = status_row(src, args.run_id, rec["captured_at"],
                                     args.observation_type, e, key, "FAILED_CAPTURE",
                                     "Capture failed: " + "; ".join(rec["errors"])[:400])
                    if row["observation_id"] not in existing_ids:
                        append_jsonl(OBSERVATIONS, row)
                        n += 1
            print(f"FAILED_CAPTURE ({n} rows marked)")
            flag(args.run_id, src["id"], "FAILED_CAPTURE", "; ".join(rec["errors"])[:400])
            summary["sources"][src["id"]] = {"status": "FAILED_CAPTURE"}
            continue
        try:
            rows = parser(rec, src, src.get("parser_args") or {})
        except ParseFailure as e:
            n = 0
            if not args.no_registry:
                for key, e2 in reg.items():
                    row = status_row(src, args.run_id, rec["captured_at"],
                                     args.observation_type, e2, key, "PARSE_FAILED",
                                     f"Parser failed: {e}")
                    if row["observation_id"] not in existing_ids:
                        append_jsonl(OBSERVATIONS, row)
                        n += 1
            print(f"PARSE_FAILED: {e}")
            flag(args.run_id, src["id"], "PARSE_FAILED", str(e))
            summary["sources"][src["id"]] = {"status": "PARSE_FAILED", "error": str(e)}
            continue
        seen = set()
        n_new = 0
        first_run_for_source = not reg
        for row in rows:
            obs = finalize(row, rec, src, args.run_id, args.observation_type, tol)
            key = obs["product_key"]
            seen.add(key)
            if not args.no_registry:
                prior = reg.get(key)
                if prior is None:
                    obs["notes"] += " First observation of this product key."
                    if not first_run_for_source:
                        flag(args.run_id, src["id"], "NEW_PRODUCT",
                             f"{key}: '{obs['product_name']}' first seen; series {obs['comparability_series']}")
                elif prior.get("last_seen_run") == args.run_id:
                    pass  # re-parse of the same capture: a changed reading is a
                    # parser change, recorded as a ROW_REVISED revision below,
                    # not a change at the source
                else:
                    if prior["product_name"] != obs["product_name"]:
                        obs["notes"] += (f" NEEDS_REVIEW: product name changed from "
                                         f"'{prior['product_name']}'.")
                        flag(args.run_id, src["id"], "NAME_CHANGED",
                             f"{key}: '{prior['product_name']}' -> '{obs['product_name']}'")
                    if prior["comparability_series"] != obs["comparability_series"]:
                        obs["notes"] += (f" NEEDS_REVIEW: series changed from "
                                         f"{prior['comparability_series']}; excluded from "
                                         f"time series until reviewed.")
                        obs["comparability_series"] = "REVIEW|" + obs["comparability_series"]
                        flag(args.run_id, src["id"], "SERIES_CHANGED",
                             f"{key}: {prior['comparability_series']} -> {obs['comparability_series']}")
                reg[key] = {k: obs[k] for k in ("product_name", "product_category",
                                                "shell_type", "advertised_size", "size_class",
                                                "quantity", "unit_of_sale",
                                                "comparability_series", "series_class")}
                reg[key]["first_seen_run"] = (prior or {}).get("first_seen_run", args.run_id)
                reg[key]["last_seen_run"] = args.run_id
            if obs["observation_id"] in existing_ids:
                prev_row = existing_rows[obs["observation_id"]]
                if not row_differs(prev_row, obs):
                    continue
                # A corrected parser produced a different reading of the same
                # capture. The earlier row stays; this one is appended as a
                # revision and reports use the highest revision per id.
                rev = int(prev_row["observation_id"].split("#r")[1]) + 1 \
                    if "#r" in prev_row["observation_id"] else 2
                obs["notes"] += (f" REVISION r{rev} of {obs['observation_id']} after a "
                                 f"parser change; supersedes the earlier row for reporting.")
                obs["observation_id"] = f"{obs['observation_id']}#r{rev}"
                flag(args.run_id, src["id"], "ROW_REVISED",
                     f"{obs['observation_id']}: {describe_diff(prev_row, obs)}")
                append_jsonl(OBSERVATIONS, obs)
                existing_rows[obs["observation_id"].split("#r")[0]] = obs
                n_new += 1
                continue
            append_jsonl(OBSERVATIONS, obs)
            existing_ids.add(obs["observation_id"])
            existing_rows[obs["observation_id"]] = obs
            n_new += 1
        n_unavail = 0
        if not args.no_registry:
            for key, e in reg.items():
                if key in seen:
                    continue
                if e.get("last_seen_run") == args.run_id:
                    continue
                row = status_row(src, args.run_id, rec["captured_at"], args.observation_type,
                                 e, key, "UNAVAILABLE_NOT_LISTED",
                                 "Product key present in a prior run but absent from this capture. "
                                 "Absence is not a price change.")
                if row["observation_id"] not in existing_ids:
                    append_jsonl(OBSERVATIONS, row)
                    n_unavail += 1
                    flag(args.run_id, src["id"], "PRODUCT_UNAVAILABLE",
                         f"{key}: '{e.get('product_name')}' not in this capture")
        st = "OK" if rec["status"] == "OK" else "PARTIAL"
        print(f"{st} ({n_new} rows, {n_unavail} unavailable)")
        summary["sources"][src["id"]] = {"status": st, "rows": n_new, "unavailable": n_unavail}
    if not args.no_registry:
        REGISTRY.write_text(json.dumps(registry, indent=1, sort_keys=True) + "\n", "utf-8")
    rebuild_csv()
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
