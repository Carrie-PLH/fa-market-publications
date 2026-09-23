#!/usr/bin/env python3
"""Build the Provision Record site (site/) from the record. Stdlib only.

Reads config.json, each title's methodology.md, sources.json, data files,
and issues/<id>/{edition.json, issue.md, numbers.json, evidence.json}.
Writes static pages with stable URLs:

    /                              home: latest board, register of titles
    /archive/                      every published edition, by title and date
    /about/  /reuse/               what this is; how to cite and reuse
    /<title>/                      publication page: latest edition, archive, sources
    /<title>/methodology/          the public methods page
    /<title>/<edition>/            permanent edition page
    /<title>/<edition>/data.csv    every indicator row in the edition's data run
    /<title>/<edition>/measures.csv  the calculated measures the edition quotes
    /<title>/<edition>/observations.csv  original observations (where a title has them)
    /<title>/<edition>/dictionary.md   column definitions and calculation rules
    /<title>/<edition>/numbers.json, evidence.json, issue.md  the record as kept
    /<title>/<edition>/evidence/   the retained source files, byte for byte
    /<title>/<edition>/evidence/anchors/  the timestamp chain entry, manifest and tokens

An edition is built when edition.json says status "published". Drafts and
scaffolds are listed as such and get no page, no downloads, and no link,
unless --include-drafts is given, which writes to the --out directory with
a visible draft banner and noindex. The deployable tree is site/; deploy.sh
publishes it only when run by hand.

Usage:
    python3 tools/site.py                      # build site/ from published editions
    python3 tools/site.py --include-drafts --out site-preview
"""

import argparse
import csv
import html
import io
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, Title, config, load_json, read_jsonl  # noqa: E402

BASE = "https://provisionrecord.com"
CSS = (ROOT / "site-src" / "style.css").read_text()
MARK = ('<svg viewBox="0 0 48 48" aria-hidden="true"><rect width="48" height="48" fill="#14110f"/>'
        '<g transform="translate(4,4)"><path d="M12,0 L12,12 L0,12 M28,0 L28,12 L40,12 M12,40 L12,28 L0,28 '
        'M28,40 L28,28 L40,28" fill="none" stroke="#dda08f" stroke-width="4.2"/>'
        '<rect x="17.3" y="17.3" width="5.4" height="5.4" fill="#dda08f"/></g></svg>')

# Titles the site lists that have no directory yet. Status text is stated as it stands.
PLANNED = [
    {"slug": "beef", "name": "Beef Monitor", "for": "Independent restaurants, caterers, small food buyers",
     "src": "USDA AMS Market News · USDA ERS livestock outlook · BLS PPI and CPI",
     "status": "Sources assessed", "note": "No edition yet"},
    {"slug": "pork", "name": "Pork Monitor", "for": "Restaurants, barbecue businesses, caterers",
     "src": "USDA AMS Market News · USDA ERS · BLS PPI",
     "status": "Assessment pending", "note": "Public-source feasibility not yet reviewed"},
    {"slug": "chicken", "name": "Chicken Monitor", "for": "Restaurants, caterers, food-service businesses",
     "src": "USDA AMS Market News · USDA ERS · BLS PPI",
     "status": "Assessment pending", "note": "Public-source feasibility not yet reviewed"},
    {"slug": "coffee", "name": "Coffee Current", "for": "Independent cafés, small roasters, hospitality buyers",
     "src": "ICO composite indicator · USDA FAS coffee reports · BLS PPI and CPI",
     "status": "Sources assessed", "note": "No edition yet"},
]
ORDER = ["lobster", "beef", "pork", "chicken", "egg-butter", "coffee"]
TITLE_FOR = {"lobster": "Caterers, event planners, seafood buyers",
             "egg-butter": "Bakeries, pastry shops, breakfast businesses"}
TITLE_SRC = {"lobster": "Maine DMR landings · NOAA FOSS trade · BLS PPI and CPI · USDA ERS outlook · Field Assembly observation record",
             "egg-butter": "USDA AMS egg and dairy reports · USDA NASS · USDA ERS · BLS PPI and CPI"}


def esc(s):
    return html.escape(str(s), quote=True)


def dlong(iso):
    """2026-09-22 -> 22 September 2026"""
    if not iso:
        return "—"
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {d.strftime('%B')} {d.year}"


# ---------- a small Markdown renderer for the repository's own files ----------

def inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(text, wide_tables=False):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    out, para, table, ul = [], [], [], []

    def flush_para():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    def flush_table():
        if table:
            rows = [r for r in table if not re.match(r"^\|?\s*:?-{2,}", r)]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            h = "".join(f"<th>{inline(c)}</th>" for c in cells[0])
            b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
            is_numbers = cells[0] and cells[0][0].lower().startswith("measure")
            cls = ' class="tablewrap wide"' if (wide_tables or is_numbers) else ' class="tablewrap"'
            tcls = ' class="numbers"' if is_numbers else ""
            out.append(f'<div{cls}><table{tcls}><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
            table.clear()

    def flush_ul():
        if ul:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in ul) + "</ul>")
            ul.clear()

    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith("|"):
            flush_para(); flush_ul(); table.append(s); continue
        flush_table()
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            flush_para(); flush_ul()
            lvl = len(m.group(1)) + 0  # '#' in a file is the page title; render as h1 only on the page shell
            tag = {1: "h1", 2: "h2", 3: "h3"}[lvl]
            out.append(f"<{tag}>{inline(m.group(2))}</{tag}>")
            continue
        if re.match(r"^\s*-\s+", s):
            flush_para(); ul.append(re.sub(r"^\s*-\s+", "", s)); continue
        if not s.strip():
            flush_para(); flush_ul(); continue
        para.append(s.strip())
    flush_para(); flush_table(); flush_ul()
    return "\n".join(out)


# ---------- page shell ----------

def shell(title, body, *, path, description, noindex=False, dateline=None):
    canonical = BASE + path
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    dl = ""
    if dateline:
        dl = f'<div class="dateline"><span>{dateline[0]}</span><span>{dateline[1]}</span></div>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{esc(title)}</title>
<link rel="canonical" href="{canonical}">
<meta name="description" content="{esc(description)}">
{robots}<style>
{CSS}</style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="top">
  <a class="brand" href="/" aria-label="Provision Record, home">
    {MARK}
    <span><span class="imprint">Field Assembly · Food Market Publications</span><br><span class="name">Provision Record</span></span>
  </a>
  <nav aria-label="Primary">
    <a href="/#titles">Titles</a>
    <a href="/archive/">Archive</a>
    <a href="/about/">About</a>
    <a href="/reuse/">Cite and reuse</a>
  </nav>
</header>
{dl}
<main id="main-content">
{body}
</main>
<footer>
  <div class="sf-top">
    <div class="sf-brand">
      {MARK}
      <div class="sf-tag">Provision Record<br>Food market publications, a free public resource from<br><a href="https://fieldassembly.net">Field Assembly</a><br>A publisher of maintained reference and evidence works</div>
    </div>
    <div class="sf-nav">
      <div class="sf-col">
        <span class="sf-label">Publications</span>
        <a href="/lobster/">Lobster Monitor</a>
        <a href="/egg-butter/">Egg &amp; Butter Brief</a>
        <a href="/#titles">All titles</a>
        <a href="/archive/">Archive of editions</a>
      </div>
      <div class="sf-col">
        <span class="sf-label">This site</span>
        <a href="/about/">About</a>
        <a href="/reuse/">Cite and reuse</a>
        <a href="/lobster/methodology/">Lobster Monitor methodology</a>
        <a href="/egg-butter/methodology/">Egg &amp; Butter Brief methodology</a>
      </div>
      <div class="sf-col">
        <span class="sf-label">Field Assembly</span>
        <a href="https://fieldassembly.net">Home</a>
        <a href="https://fieldassembly.net/standard">The Record Standard</a>
        <a href="https://fieldassembly.net/contact">Contact</a>
        <a href="https://fieldassembly.net/privacy">Privacy</a>
        <a href="https://fieldassembly.net/accessibility">Accessibility</a>
      </div>
    </div>
  </div>
  <div class="sf-bottom">
    <span>© 2026 Field Assembly LLC · Massachusetts · provisionrecord.com</span>
    <span>Corrections are made on the record.</span>
  </div>
</footer>
</body>
</html>
"""


WRITTEN = set()


def write(out, path, content):
    p = out / path.strip("/")
    if path.endswith("/") or not Path(path).suffix:
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, "utf-8")
    WRITTEN.add(p)


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    WRITTEN.add(dst)


# ---------- the record ----------

class Edition:
    def __init__(self, title, slug, issue_id):
        self.title, self.slug, self.id = title, slug, issue_id
        d = title.issues / issue_id
        self.dir = d
        self.meta = load_json(d / "edition.json") if (d / "edition.json").exists() else {"status": "scaffold"}
        self.numbers = load_json(d / "numbers.json") if (d / "numbers.json").exists() else None
        self.evidence = load_json(d / "evidence.json") if (d / "evidence.json").exists() else None
        self.issue_md = (d / "issue.md").read_text() if (d / "issue.md").exists() else ""
        self.status = self.meta.get("status", "scaffold")
        self.run_id = (self.numbers or {}).get("run_id")

    @property
    def path(self):
        return f"/{self.slug}/{self.id}/"

    @property
    def url(self):
        return BASE + self.path

    @property
    def name(self):
        return self.meta.get("edition_title", self.id)

    def data_as_of(self):
        if not self.evidence:
            return None
        return max(c["fetched_at"] for c in self.evidence["captures"] if c.get("fetched_at"))[:10]

    def anchor(self):
        """The first anchor chain entry whose manifest lists this edition's numbers.json."""
        want = f"{self.slug}/issues/{self.id}/numbers.json"
        for e in read_jsonl(ROOT / "anchors" / "chain.jsonl"):
            mf = ROOT / "anchors" / e["entry"]["manifest_file"]
            if mf.exists() and want in mf.read_text():
                eid = e["entry"]["id"]
                tsa = sorted((ROOT / "anchors" / "tsa").glob(f"{eid}-*.tsr"))
                ots = sorted((ROOT / "anchors" / "ots").glob(f"{eid}*.ots"))
                return {"entry": e, "manifest": mf, "tsa": tsa, "ots": ots}
        return None


def citation(ed, cfg_name):
    pub = ed.meta.get("published")
    when = dlong(pub) if pub else "unpublished draft"
    ver = f", version {ed.meta['version']}" if ed.meta.get("version") else ""
    rev = f", revised {dlong(ed.meta['revised'])}" if ed.meta.get("revised") else ""
    return (f"Field Assembly. {cfg_name}, {ed.name}. Provision Record, {when}{ver}{rev}. {ed.url}")


# ---------- CSV and dictionary ----------

DATA_COLUMNS = ["series_id", "series_title", "period", "value", "unit", "source_id", "source_label",
                "source_url", "captured_at", "evidence_path", "sha256", "notes"]


def write_data_csv(ed, out):
    rows = [r for r in read_jsonl(ed.title.indicators) if r["run_id"] == ed.run_id]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=DATA_COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in sorted(rows, key=lambda r: (r["series_id"], r.get("period") or "")):
        r = dict(r)
        r["value"] = "" if r.get("value") is None else repr(float(r["value"])) if isinstance(r["value"], float) else r["value"]
        r["period"] = r.get("period") or ""
        if r.get("evidence_path"):  # repository path -> the copy beside this file
            r["evidence_path"] = "evidence/" + str(Path(r["evidence_path"]).relative_to(f"{ed.slug}/captures/{ed.run_id}"))
        w.writerow(r)
    write(out, ed.path + "data.csv", buf.getvalue())
    return len(rows)


def flat_measures(n):
    """numbers.json -> rows (measure, key, period, value, unit-less). Nested dicts are flattened
    with dotted keys so nothing is lost; lists are JSON-encoded."""
    rows = []
    skip = {"issue", "title", "run_id", "computed_at", "retail_reference"}

    def walk(prefix, v):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(f"{prefix}.{k}" if prefix else k, x)
        elif isinstance(v, list):
            rows.append((prefix, json.dumps(v)))
        else:
            rows.append((prefix, "" if v is None else v))
    for k, v in n.items():
        if k in skip:
            continue
        walk(k, v)
    return rows


def write_measures_csv(ed, out):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["measure", "value", "kind"])
    for k, v in flat_measures(ed.numbers):
        kind = "calculated" if re.search(r"pct$|_avg|change|decline|derived|ytd|implied", k) else "source-reported or period label"
        w.writerow([k, v, kind])
    write(out, ed.path + "measures.csv", buf.getvalue())


def write_observations_csv(ed, out):
    rr = (ed.numbers or {}).get("retail_reference") or {}
    if not rr.get("sellers"):
        return False
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    spec = rr.get("reference_series", {})
    w.writerow(["seller_letter", "observed_date", "usd_per_lobster", "availability", "product_category", "shell_type", "size_class_lb", "quantity", "channel"])
    for s in rr["sellers"]:
        for o in s["observations"]:
            w.writerow([s["seller"], o["date"], o["usd_per_lobster"], o.get("availability") or "",
                        spec.get("product_category", ""), spec.get("shell_type", ""), spec.get("size_class", ""),
                        spec.get("quantity", ""), "counter or pickup"])
    write(out, ed.path + "observations.csv", buf.getvalue())
    return True


def dictionary_md(ed, cfg_name, n_rows, has_obs):
    src_lines = []
    for s in ed.title.sources():
        src_lines.append(f"| `{s['id']}` | {s['name']} | {s['label']} | {s.get('page_url','')} |")
    obs = ""
    if has_obs:
        obs = """
## observations.csv

Original Field Assembly observations: advertised prices on the public pages of Maine sellers, captured on scheduled dates with page screenshots retained in a private record. Sellers appear by letter; the letter-to-seller mapping is on the methodology page.

| Column | Meaning |
|---|---|
| seller_letter | Seller, as lettered on the methodology page |
| observed_date | Date of capture (UTC) |
| usd_per_lobster | Advertised price for one lobster of the stated specification, US dollars. Counter and pickup sellers only; direct-ship prices, which include shipping, are excluded from this file |
| availability | Availability status as shown on the page at capture, if recorded |
| product_category, shell_type, size_class_lb, quantity, channel | The reference specification. Like is compared with like; no yield or size conversion is applied |
"""
    return f"""# {cfg_name}, {ed.name}: data dictionary

Files in this directory hold the record behind the edition. `data.csv` is source-reported data as parsed from the retained files; `measures.csv` is what the edition quotes, including the figures Field Assembly calculated; `numbers.json` and `evidence.json` are the same record as kept in the repository. Values keep the precision they were parsed or computed at; the edition text rounds for display.

Data run: `{ed.run_id}`. Information available as of {dlong(ed.meta.get('information_available_as_of'))}. Rows in data.csv: {n_rows}.

License: Field Assembly's tables, calculations and documentation here are CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); cite the edition. Files under `evidence/` are third-party source material and keep their publishers' terms.

## data.csv

One row per series and period, from the data run named above. A series is a monthly (`YYYY-MM`) or weekly (`YYYY-MM-DD`, week ending) series; forecast-table rows from USDA ERS carry no period and are labeled by attribute text in `series_id`.

| Column | Meaning |
|---|---|
| series_id | Identifier. BLS series codes are used as published (for example `WPU02230503`); Field Assembly identifiers are lowercase with underscores and say what was derived (for example `..._usd_per_lb` from value divided by quantity) |
| series_title | Plain description, with the reporting basis (not seasonally adjusted, preliminary, derived) |
| period | Observation period. Monthly `YYYY-MM`; weekly `YYYY-MM-DD` is the week-ending date; empty for forecast-table attributes |
| value | Numeric value as parsed. Empty when the source published a non-numeric marker; the marker is kept in `notes` |
| unit | Unit as reported or as derived: `index`, `USD per lb`, `kg`, `lb`, `USD`, `Percent`, `Percent change`, `cents per dozen` |
| source_id | The source in `sources.json` and on the methodology page |
| source_label | The source's class: OFFICIAL STATISTIC, OFFICIAL MARKET REPORT, or FOOD-COST INDICATOR |
| source_url | URL fetched (the final URL after any redirect) |
| captured_at | Retrieval time, UTC, ISO 8601 |
| evidence_path | The retained file, byte for byte, under `evidence/` in this directory |
| sha256 | SHA-256 of that file |
| notes | Preliminary flags, derivation arithmetic, restatement notes, or the source's own marker text |

Missing values: an empty `value` cell means the source published no numeric value for that period. No value is imputed, interpolated, or carried forward.

## measures.csv

Every figure in `numbers.json`, flattened to one row per leaf with a dotted key. `kind` says whether the row is a Field Assembly calculation or a value or label carried from a source. Calculations:

- `yoy_pct`: (latest − same period a year earlier) ÷ same period a year earlier × 100, rounded to one decimal. The same month for monthly series; for weekly series the week ending nearest to 52 weeks earlier, within four days.
- `vs_two_years_pct`: the same against two years earlier.
- `change_pct` on peaks, annual totals and year-to-date sums: the same formula on the two values named beside it.
- Unit values: dollars divided by quantity, with kilograms converted at 2.20462262 lb per kg where the series says `per lb`. The arithmetic is in the `notes` column of data.csv.
- Annual and year-to-date sums add the monthly rows in data.csv for the months named.
- Averages over a window are unweighted means of the weeks listed beside them.

Index series are indexes, not prices. A change in an index is a change in the index.

## Sources in this data run

| source_id | Source | Class | Page |
|---|---|---|---|
{chr(10).join(src_lines)}

Reports issued separately by one institution are not independent corroboration of each other.
{obs}
## evidence/

The retained source files with their HTTP response headers (Set-Cookie redacted at capture), and `capture.json` for each source with URL, time and SHA-256. Under `evidence/anchors/`: the timestamp chain entry that covers these files, its manifest of hashes, and the RFC 3161 tokens. A token attests that the entry hash existed at the stated time; it does not attest that any source's figure was correct.
"""


# ---------- pages ----------

def numbers_table_html(ed):
    md = (ed.dir / "numbers.md").read_text() if (ed.dir / "numbers.md").exists() else ""
    return md_to_html(md)


def edition_page(ed, cfg_t, out, draft_mode):
    name = cfg_t["name"]
    body_md = ed.issue_md
    # The issue file starts with the title lines; the page shell carries them.
    body_md = re.sub(r"^# .*?\n\n\*\*.*?\*\*\n.*?\n\n", "", body_md, count=1, flags=re.S)
    n_rows = write_data_csv(ed, out)
    write_measures_csv(ed, out)
    has_obs = write_observations_csv(ed, out)
    dictionary = dictionary_md(ed, name, n_rows, has_obs)
    write(out, ed.path + "dictionary.md", dictionary)
    for f in ("numbers.json", "evidence.json", "issue.md", "numbers.md", "edition.json"):
        if (ed.dir / f).exists():
            write(out, ed.path + f, (ed.dir / f).read_text())
    # retained source files
    ev_out = out / ed.slug / ed.id / "evidence"
    for c in ed.evidence["captures"]:
        if c.get("path"):
            src = ROOT / c["path"]
            dst = ev_out / Path(c["path"]).relative_to(f"{ed.slug}/captures/{ed.run_id}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy(src, dst)
            hp = src.with_name(src.name.rsplit(".", 1)[0] + ".headers.txt")
            if hp.exists():
                copy(hp, dst.with_name(hp.name))
    for cj in (ROOT / ed.slug / "captures" / ed.run_id).glob("*/capture.json"):
        d = ev_out / cj.parent.name
        d.mkdir(parents=True, exist_ok=True)
        copy(cj, d / "capture.json")
    anc = ed.anchor()
    anchor_html = ""
    if anc:
        ad = ev_out / "anchors"
        ad.mkdir(parents=True, exist_ok=True)
        eid = anc["entry"]["entry"]["id"]
        copy(ROOT / "anchors" / "entries" / f"{eid}.json", ad / f"{eid}.json")
        copy(anc["manifest"], ad / anc["manifest"].name)
        for t in anc["tsa"]:
            copy(t, ad / t.name)
            q = t.with_suffix(".tsq")
            if q.exists():
                copy(q, ad / q.name)
        for o in anc["ots"]:
            copy(o, ad / o.name)
        tsa_names = ", ".join(re.sub(r"^.*Z-(.*)\.tsr$", r"\1", t.name) for t in anc["tsa"])
        ots_line = ("An OpenTimestamps proof is stored alongside." if anc["ots"]
                    else "No OpenTimestamps proof was produced for this entry; the RFC 3161 tokens are the external attestation.")
        anchor_html = f"""<p>Timestamp chain entry <code>{eid}</code>, {anc['entry']['entry']['file_count']} files, anchored {esc(anc['entry']['entry']['utc'][:19])}Z with RFC 3161 tokens from {esc(tsa_names)}. {ots_line} Files: <a href="evidence/anchors/{eid}.json">entry</a>, <a href="evidence/anchors/{anc['manifest'].name}">manifest</a>, tokens {', '.join(f'<a href="evidence/anchors/{t.name}">{esc(t.name)}</a>' for t in anc['tsa'])}.</p>
<p>A timestamp shows that these files existed unchanged by that time. It does not show that a source's figure was correct, or that an advertised price was available to every buyer.</p>"""
    else:
        anchor_html = "<p>No timestamp chain entry covers this edition's files yet.</p>"

    cite = citation(ed, name)
    pub = ed.meta.get("published")
    status_line = "Published" if pub else "Draft, not yet published"
    banner = ""
    if ed.status != "published":
        banner = f'<div class="notice"><b>Draft</b>This edition has not been published. Figures and text may change before publication. {esc(ed.meta.get("notes",""))}</div>'
    rec_links = []
    for c in ed.evidence["captures"]:
        if c.get("path"):
            rel = Path(c["path"]).relative_to(f"{ed.slug}/captures/{ed.run_id}")
            rec_links.append(f'<li><a href="evidence/{rel}">{esc(rel)}</a><span>{esc(c["url"])} · retrieved {esc(c["fetched_at"][:19])}Z · SHA-256 {esc(c["sha256"][:16])}…</span></li>')
    retail = (ed.numbers or {}).get("retail_reference", {}).get("record")
    retail_html = ""
    if retail and retail.get("sha256"):
        retail_html = f'<li><span>Field Assembly observation record (private repository): commit <code>{esc(retail["git_commit"][:12])}</code>, file SHA-256 <code>{esc(retail["sha256"][:16])}…</code>. The observations used are in observations.csv.</span></li>'
    body = f"""
<article class="article">
  <div class="kicker"><a href="/{ed.slug}/">{esc(name)}</a> · {esc(status_line)}</div>
  <h1>{esc(ed.name)}</h1>
  {banner}
  <dl class="meta">
    <div><dt>Publication date</dt><dd>{esc(dlong(pub)) if pub else "Not yet published"}</dd></div>
    <div><dt>Version</dt><dd>{esc(ed.meta.get("version") or "—")}{(" · revised " + esc(dlong(ed.meta["revised"]))) if ed.meta.get("revised") else ""}</dd></div>
    <div><dt>Information available as of</dt><dd>{esc(dlong(ed.meta.get("information_available_as_of")))}</dd></div>
    <div><dt>Data run</dt><dd class="num">{esc(ed.run_id)}</dd></div>
    <div><dt>Permanent URL</dt><dd class="num">{esc(ed.url)}</dd></div>
    <div><dt>Reviewer</dt><dd>{esc(ed.meta["reviewer"]) if ed.meta.get("reviewer") else "Review pending before publication"}</dd></div>
  </dl>
  <div class="prose">
{md_to_html(body_md)}
  </div>
  <div class="apparatus">
    <div>
      <h2>Suggested citation</h2>
      <div class="cite" id="cite">{esc(cite).replace(esc(ed.url), f'<span class="url">{esc(ed.url)}</span>')}</div>
      <button class="copy" type="button" data-copy="cite">Copy citation</button>
      <p>Cite the edition and its version. If a later revision changes a figure, the revision is dated on this page and the original text stays visible. Field Assembly's text and tables here are licensed <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>; source files under <code>evidence/</code> keep their publishers' terms. See <a href="/reuse/">Cite and reuse</a>.</p>
    </div>
    <div>
      <h2>Download</h2>
      <ul class="files">
        <li><a href="data.csv">data.csv</a><span>Every indicator row in data run {esc(ed.run_id)}: {n_rows} rows, source-reported values at parsed precision</span></li>
        <li><a href="measures.csv">measures.csv</a><span>Every figure the edition quotes, calculated measures marked</span></li>
        {"<li><a href='observations.csv'>observations.csv</a><span>Original Field Assembly price observations used in the consumer reference row</span></li>" if has_obs else ""}
        <li><a href="dictionary.md">dictionary.md</a><span>Column definitions, units, calculation rules, missing-value convention</span></li>
        <li><a href="numbers.json">numbers.json</a> · <a href="evidence.json">evidence.json</a> · <a href="issue.md">issue.md</a><span>The record as kept in the repository</span></li>
      </ul>
    </div>
  </div>
  <div class="record">
    <h2>The record behind this edition</h2>
    <p>Each retained file is the response as received, byte for byte, with its HTTP headers beside it and its SHA-256 in <code>evidence.json</code>. Reports issued separately by one institution are not independent corroboration of each other. Methods and source list: <a href="/{ed.slug}/methodology/">{esc(name)} methodology</a>.</p>
    <details><summary>Retained source files ({len(rec_links)})</summary>
      <ul class="files">
        {"".join(rec_links)}
        {retail_html}
      </ul>
    </details>
    <details><summary>Timestamp record</summary>
      {anchor_html}
    </details>
  </div>
  </div>
</article>
<script>
document.querySelectorAll('button.copy').forEach(function(b){{b.addEventListener('click',function(){{var t=document.getElementById(b.dataset.copy).innerText;navigator.clipboard.writeText(t).then(function(){{b.textContent='Copied';b.dataset.done='1';setTimeout(function(){{b.textContent='Copy citation';b.dataset.done='';}},2000);}});}});}});
</script>
"""
    write(out, ed.path, shell(f"{ed.name} · {name} · Provision Record", body, path=ed.path,
                              description=f"{name}, {ed.name}: dated food-market evidence with sources, calculations and downloadable tables.",
                              noindex=(ed.status != "published"),
                              dateline=(f"<b>{esc(name)}</b> · {esc(ed.name)}", f"Data run {esc(ed.run_id)} · information as of {esc(dlong(ed.meta.get('information_available_as_of')))}")))


def publication_page(slug, cfg_t, editions, out, draft_mode):
    name = cfg_t["name"]
    visible = [e for e in editions if e.status == "published" or (draft_mode and e.status == "draft")]
    latest = visible[-1] if visible else None
    items = []
    for e in reversed(editions):
        if e.status == "published" or (draft_mode and e.status == "draft"):
            d = e.meta.get("published") or e.meta.get("information_available_as_of")
            items.append(f'<li><span class="d">{esc(dlong(d))}</span><span class="t"><a href="{e.path}">{esc(e.name)}</a><small>Data run {esc(e.run_id)}</small></span><span class="s">{"published" if e.status == "published" else "draft"}</span></li>')
        else:
            label = {"draft": "Drafted, publication pending", "scaffold": "Numbers computed, text not yet written"}.get(e.status, e.status)
            items.append(f'<li><span class="d">{esc(dlong(e.meta.get("information_available_as_of")))}</span><span class="t">{esc(e.name)}<small>{esc(label)}. {esc(e.meta.get("notes",""))}</small></span><span class="s">{esc(e.status)}</span></li>')
    latest_html = (f'<p>Latest edition: <a href="{latest.path}">{esc(latest.name)}</a>. Each edition keeps its own permanent address; this page always points at the most recent one and never replaces an earlier one.</p>'
                   if latest else "<p>No edition has been published yet. The methodology and source list are public now; the first edition will be listed here with its permanent address when it publishes.</p>")
    srcs = "".join(f"<tr><td>{esc(s['name'])}</td><td>{esc(s['label'])}</td><td><a href=\"{esc(s.get('page_url',''))}\">{esc(s.get('page_url',''))}</a></td></tr>" for s in Title(slug).sources())
    body = f"""
<article class="article">
  <div class="kicker">Publication</div>
  <h1>{esc(name)}</h1>
  <p class="standfirst">{esc(cfg_t.get("audience",""))} Market evidence from public sources, arranged so that a price claim can be checked against it. Nothing here is a supplier's cost, and nothing here says whether a contractual adjustment is permitted.</p>
  <div class="prose">
    <h2>Editions</h2>
    {latest_html}
    <ul class="editions">{"".join(items)}</ul>
    <h2>Sources</h2>
    <p>Fetched by script, retained byte for byte, and listed with each edition. The full method, including comparison rules and the letter map for any original observations, is on the <a href="/{slug}/methodology/">methodology page</a>.</p>
    <div class="tablewrap wide"><table><thead><tr><th>Source</th><th>Class</th><th>Page</th></tr></thead><tbody>{srcs}</tbody></table></div>
  </div>
</article>
"""
    write(out, f"/{slug}/", shell(f"{name} · Provision Record", body, path=f"/{slug}/",
                                   description=f"{name}: editions, sources and methodology. {cfg_t.get('audience','')}"))
    meth = (ROOT / slug / "methodology.md").read_text()
    meth = re.sub(r"^# .*\n", "", meth, count=1)
    body = f"""
<article class="article">
  <div class="kicker"><a href="/{slug}/">{esc(name)}</a> · Methodology</div>
  <h1>{esc(name)}: methodology</h1>
  <div class="prose">
{md_to_html(meth, wide_tables=True)}
  </div>
</article>
"""
    write(out, f"/{slug}/methodology/", shell(f"Methodology · {name} · Provision Record", body, path=f"/{slug}/methodology/",
                                              description=f"How {name} is compiled: sources, comparison rules, evidence and corrections."))


def board_rows(ed):
    """Rows for the home page board from the edition's numbers.md (the same table the edition shows)."""
    md = (ed.dir / "numbers.md").read_text()
    rows = [r for r in md.splitlines() if r.startswith("|") and not r.startswith("|---") and not r.startswith("| Measure")]
    out = []
    for r in rows:
        c = [x.strip() for x in r.strip().strip("|").split("|")]
        if len(c) < 5:
            continue
        chg = c[3]
        cls = "flat" if chg in ("—", "0.0%") else ("down" if chg.startswith("-") or chg.startswith("−") else "up")
        def vp(x):
            m = re.match(r"^(.*?)\s*\((.*)\)$", x)
            return f"{esc(m.group(1))}<span>{esc(m.group(2))}</span>" if m else esc(x)
        out.append(f'<tr><td class="measure">{esc(c[0])}</td><td class="num">{vp(c[1])}</td><td class="num">{vp(c[2])}</td><td class="num chg {cls}">{esc(chg.replace("-", "−", 1) if chg.startswith("-") else chg)}</td><td>{esc(c[4])}</td></tr>')
    return "".join(out)


def home_page(cfg, editions_by, out, draft_mode):
    # board: most recent lobster edition whose numbers exist (draft allowed: the figures are the record, the text is what waits)
    lob = [e for e in editions_by.get("lobster", []) if e.numbers]
    board = ""
    if lob:
        e = lob[-1]
        link = (f'<a class="primary" href="{e.path}">Read the edition</a>' if (e.status == "published" or draft_mode)
                else '<a class="primary" href="/lobster/">About Lobster Monitor</a>')
        state = "Published edition" if e.status == "published" else "Baseline figures; the edition text is drafted and pending publication"
        board = f"""
    <div class="board-head">
      <h2>Lobster Monitor · the board</h2>
      <span class="as-of">{esc(e.name)} · {esc(state)}</span>
    </div>
    <div class="tablewrap">
    <table class="prices">
      <thead><tr><th>Measure</th><th class="num">Latest</th><th class="num">Year earlier</th><th class="num">Change</th><th>Source</th></tr></thead>
      <tbody>{board_rows(e)}</tbody>
    </table>
    </div>
    <div class="board-notes">
      <p>Year over year means the same month a year earlier. Live prices are never converted to meat prices. Index series are indexes, not prices. Every figure is in the edition's downloadable tables with its source file and retrieval time.</p>
    </div>
    <div class="board-cta">
      {link}
      <a class="quiet" href="/lobster/methodology/">Methodology</a>
    </div>"""
    # register
    reg = []
    for i, slug in enumerate(ORDER, 1):
        if slug in cfg["titles"]:
            t = cfg[slug]
            eds = editions_by.get(slug, [])
            pub = [e for e in eds if e.status == "published"]
            if pub:
                st, note = f"{len(pub)} edition{'s' if len(pub) > 1 else ''} published", f"Latest: {pub[-1].name}"
            elif any(e.status == "draft" for e in eds):
                st, note = "Baseline edition drafted", "Publication pending; methodology and sources public"
            elif eds:
                st, note = "In development", "Sources verified and captured; first edition not yet written"
            else:
                st, note = "In development", "Sources verified"
            reg.append(f'<tr><td class="no">{i:02d}</td><td class="title"><a href="/{slug}/">{esc(t["name"])}</a></td><td class="for">{esc(TITLE_FOR.get(slug,""))}</td><td class="src">{esc(TITLE_SRC.get(slug,""))}</td><td class="status"><b>{esc(st)}</b><span>{esc(note)}</span></td></tr>')
        else:
            p = next(x for x in PLANNED if x["slug"] == slug)
            reg.append(f'<tr><td class="no">{i:02d}</td><td class="title">{esc(p["name"])}</td><td class="for">{esc(p["for"])}</td><td class="src">{esc(p["src"])}</td><td class="status"><b>{esc(p["status"])}</b><span>{esc(p["note"])}</span></td></tr>')
    body = f"""
<section class="board" aria-labelledby="h1">
  <div class="inner">
    <h1 id="h1">A dated record of what is happening to food costs, and the evidence behind it.</h1>
    <p class="lede">Provision Record assembles public food-market data into short, dated editions: what changed, compared with which period, what might explain it, and what the figures can and cannot establish. Every edition has a permanent address, a suggested citation, downloadable tables, and the source files it was written from. No account, payment, or email address is needed to read or download anything here.</p>
    {board}
  </div>
</section>

<section class="section" id="titles" aria-labelledby="h-titles">
  <div class="section-no">01<small>The register</small></div>
  <div class="section-body">
    <h2 id="h-titles">Six titles, one method</h2>
    <p>Each title follows a small set of dependable public sources and five to seven measures, chosen because someone buying, reporting on, or studying that product asks about them. Several reports from one institution are not treated as independent corroboration. A measure is added only when it answers a reader's question.</p>
    <div class="tablewrap">
    <table class="register">
      <thead><tr><th></th><th>Title</th><th>Written with</th><th>Core public sources</th><th>Status</th></tr></thead>
      <tbody>{"".join(reg)}</tbody>
    </table>
    </div>
    <p class="register-foot">Status is stated as it stands. A title is listed when its sources have been examined, not when an edition exists. Core sources are the working set and may change; each edition names the exact releases it used. "Written with" names the readers whose questions shaped the measures; the editions are for anyone.</p>
  </div>
</section>

<section class="section section--raise" id="edition" aria-labelledby="h-edition">
  <div class="section-no">02<small>An edition</small></div>
  <div class="section-body">
    <h2 id="h-edition">What an edition contains, and what comes with it</h2>
    <p>Every edition of every title has the same six parts, in the same order: the read, the numbers, the explanation, the uncertainty, the buyer's question, and the record. Observations, calculations, and interpretation are kept apart. An index is not a quoted price; an import unit value is not a retail price; a public market measure is not any particular supplier's cost.</p>
    <p>Beside the text, each edition page carries a suggested citation with a copy button; CSV tables of the source-reported data and the calculated measures, at full precision, with a data dictionary; the retained source files with their retrieval times and hashes; and the timestamp record that shows when those files existed. Corrections are dated on the page and the original text stays visible.</p>
    <p class="dim">Editions state market evidence. They do not say whether a contractual adjustment is permitted, do not find that any price is unfair, and do not forecast.</p>
  </div>
</section>

<section class="section" id="method" aria-labelledby="h-method">
  <div class="section-no">03<small>Method</small></div>
  <div class="section-body">
    <h2 id="h-method">Public sources, retained evidence, dated claims</h2>
    <p>These publications extend Field Assembly's standing practice: first-party sources, quoted exactly and dated; every capture retained and externally timestamped; evidence kept apart from judgment; corrections made on the record.</p>
    <div class="method">
      <div><h3>Sources</h3><p>Free government statistics and official market reports, plus a small set of original price observations where a title has them. No paid data subscriptions. No product listings maintained by the hundred. Like is compared with like: grade, cut, size, unit, geography, and purchasing channel.</p></div>
      <div><h3>Evidence</h3><p>Each edition ships with the source versions used, publication and retrieval dates, the calculations, and the edition as delivered. Files are hashed into an append-only chain anchored by RFC 3161 timestamp tokens, and by OpenTimestamps proofs where one was produced.</p></div>
      <div><h3>Limits</h3><p>A timestamp shows a captured record existed by a date. It does not show a source's figure was correct or that a quoted price was available to every buyer. Copying a public statistic creates nothing; the work here is selection, consistent comparison, transparent calculation, and preserved context.</p></div>
    </div>
  </div>
</section>

<section class="updates" id="updates" aria-labelledby="h-upd">
  <div class="inner">
    <div class="section-no">04<small>Updates</small></div>
    <div>
      <h2 id="h-upd">Everything is on the site. Email is optional.</h2>
      <p>New editions appear in the <a href="/archive/">archive</a> and on each title's page. To be told by email when an edition publishes, write with the title in the subject line; the message is a notification and nothing more. Nothing on this site is withheld from readers who do not write.</p>
      <span class="addr">hello@fieldassembly.net</span>
    </div>
  </div>
</section>
"""
    write(out, "/", shell("Provision Record", body, path="/",
                          description="Provision Record, Field Assembly's food market publications: a free, dated public record of what is happening to lobster, beef, pork, chicken, egg and butter, and coffee costs, with sources, calculations and downloadable tables.",
                          dateline=("<b>Free public resource</b> · dated editions", "Field Assembly · Food Market Publications")))


def archive_page(cfg, editions_by, out, draft_mode):
    items = []
    for slug in ORDER:
        for e in reversed(editions_by.get(slug, [])):
            if e.status == "published" or (draft_mode and e.status == "draft"):
                d = e.meta.get("published") or e.meta.get("information_available_as_of")
                items.append(f'<li><span class="d">{esc(dlong(d))}</span><span class="t"><a href="{e.path}">{esc(cfg[slug]["name"])}: {esc(e.name)}</a><small>Data run {esc(e.run_id)} · version {esc(e.meta.get("version") or "—")}</small></span><span class="s">{"published" if e.status == "published" else "draft"}</span></li>')
    lst = f'<ul class="editions">{"".join(items)}</ul>' if items else "<p>No edition has been published yet. Titles with a drafted or scaffolded edition are listed on their own pages.</p>"
    body = f"""
<article class="article">
  <div class="kicker">Archive</div>
  <h1>Every edition, by title and date</h1>
  <p class="standfirst">Each edition keeps its permanent address. A later edition never replaces an earlier one; a correction is dated on the affected page and the original text stays visible.</p>
  <div class="prose">{lst}
  <h2>Titles</h2>
  <ul>{"".join(f'<li><a href="/{s}/">{esc(cfg[s]["name"])}</a></li>' for s in ORDER if s in cfg["titles"])}</ul>
  </div>
</article>
"""
    write(out, "/archive/", shell("Archive · Provision Record", body, path="/archive/", description="Every published edition of Provision Record's food-market publications, by title and date."))


def about_page(out):
    body = """
<article class="article">
  <div class="kicker">About</div>
  <h1>What Provision Record is</h1>
  <p class="standfirst">A free public resource from Field Assembly: dated editions that bring scattered public food-market evidence together, explain what it means and where it stops, and preserve the record they were written from.</p>
  <div class="prose">
    <h2>What it is for</h2>
    <p>Most people who need food-market evidence need it once: someone examining one price increase, writing one article, checking one claim about food inflation, or reconstructing what was known at a particular time. An edition is written so that one reading answers the question it can answer and says plainly what it cannot.</p>
    <p>The contribution is selection, consistent comparison, transparent calculation, preserved source versions, original observations where a title has them, and accessible interpretation. The government statistics themselves are public; copying them makes nothing. The archive may become more useful as it grows, because it supports questions that were not anticipated when the data was collected, but age alone does not make data valuable.</p>
    <h2>Who it may serve</h2>
    <p>Food buyers, caterers, bakeries, restaurants, and community organizations, who want market context for purchasing and budgeting, a way to examine the explanation offered for a proposed increase, and better-informed questions to put to a supplier.</p>
    <p>Journalists, who want to check claims about food inflation, separate a broad category trend from a particular commodity, and find historical context with traceable figures.</p>
    <p>Researchers, students, and public-interest organizations, who want to examine seasonal patterns and disruptions, compare movements at different stages of a market, reconstruct what information was available at a given time, and reproduce, challenge, or extend a published analysis.</p>
    <p>Members of the public investigating a consequential purchase or price adjustment, or wanting to understand how food prices are measured and why different measures diverge.</p>
    <p>These are anticipated uses. They are not claims that these readers already use or endorse the project.</p>
    <h2>What an edition does not do</h2>
    <p>An edition does not determine whether a contractual adjustment is permitted, does not find that a price is unfair, and does not forecast. It reports associations between series carefully and does not turn simultaneous movements into causal claims. Product grades, cuts, sizes, shell types, units, locations, purchasing channels, and market stages are kept distinct: an index is not a quoted price, an import unit value is not a retail price, and a public market measure is not a particular supplier's cost.</p>
    <h2>How it is made</h2>
    <p>Each title follows a small set of dependable, accessible public sources, fetched by script and retained byte for byte, with automation assisting collection and calculation and a person writing the edition. There are no paid data subscriptions and no attempt to track hundreds of individual listings. The method for each title is on its methodology page, and every edition names the exact releases it used.</p>
    <h2>Relationship to Field Assembly</h2>
    <p>Provision Record is published by Field Assembly LLC, a Massachusetts publisher of maintained reference and evidence works. It follows the same practice as Field Assembly's other works: first-party sources, retained evidence, dated claims, and corrections on the record. Contact: hello@fieldassembly.net.</p>
  </div>
</article>
"""
    write(out, "/about/", shell("About · Provision Record", body, path="/about/", description="What Provision Record is, who it may serve, what an edition does and does not do, and how it is made."))


def reuse_page(out):
    body = """
<article class="article">
  <div class="kicker">Cite and reuse</div>
  <h1>How to cite an edition, and what may be reused</h1>
  <p class="standfirst">Every edition has a permanent address, a version, and a suggested citation with a copy button. The tables and source files behind it can be downloaded from the same page.</p>
  <div class="prose">
    <h2>Citing</h2>
    <p>Cite the edition, not the site. The suggested form is:</p>
    <p><em>Field Assembly. Lobster Monitor, Issue 0: September 2026 baseline. Provision Record, [publication date], version 1.0. https://provisionrecord.com/lobster/2026-09-baseline/</em></p>
    <p>The publication date and version on the edition page are the ones to cite. If an edition is revised, the revision date and new version appear on the page, the original text stays visible, and the correction is noted in the next edition. An edition page states the date its information was available as of, separately from its publication date, because sources release on their own schedules and revise their own figures afterward.</p>
    <h2>What is ours and what is not</h2>
    <p>Two kinds of material appear on every edition page. The source material (statistical releases, market reports, trade data) belongs to its publishers and is reproduced here as retained evidence; it stays subject to whatever terms its publisher applies, and nothing on this site relicenses it. Field Assembly's own material is the edition text, the selection and arrangement of measures, the calculated figures and their documentation, and the original price observations.</p>
    <h2>Reuse terms</h2>
    <p>Field Assembly's own material on this site (edition text, the selection and arrangement of measures, calculated figures and their documentation, data dictionaries, and original price observations) is licensed under <a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International (CC BY 4.0)</a>. You may copy, redistribute, adapt, and build on it for any purpose, including commercially, provided you give credit (the suggested citation is enough), link to the license, and say whether you changed anything. Owner decision of 23 September 2026.</p>
    <p>The license does not cover the third-party source material reproduced under <code>evidence/</code>, which stays subject to its publisher's terms. Most of it is published by United States federal agencies; check the agency's own statement before redistributing it. Nothing on this site relicenses another publisher's work.</p>
    <p>The license does not permit implying that Field Assembly endorses your use or your conclusions. A figure quoted out of its edition should carry the edition's date, because later editions and later source revisions may change it.</p>
    <h2>Checking our work</h2>
    <p>Each edition's <code>data.csv</code> holds the source-reported rows the edition was computed from, <code>measures.csv</code> holds every figure the edition quotes with calculated measures marked, and <code>dictionary.md</code> defines the columns and states each formula. The retained source files, with their retrieval times and SHA-256 hashes, are under <code>evidence/</code>, together with the timestamp record. A timestamp shows those files existed unchanged by a date; it does not certify that a source's figure was correct. If you find an error, write to hello@fieldassembly.net; corrections are made on the record.</p>
  </div>
</article>
"""
    write(out, "/reuse/", shell("Cite and reuse · Provision Record", body, path="/reuse/", description="How to cite a Provision Record edition, what material is Field Assembly's, and the reuse terms."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--include-drafts", action="store_true")
    a = ap.parse_args()
    out = ROOT / a.out
    cfg = config()
    before = {p for p in out.rglob("*") if p.is_file()} if out.exists() else set()
    out.mkdir(parents=True, exist_ok=True)
    WRITTEN.clear()
    editions_by = {}
    for slug in cfg["titles"]:
        t = Title(slug)
        eds = []
        if t.issues.exists():
            for d in sorted(t.issues.iterdir()):
                if d.is_dir():
                    eds.append(Edition(t, slug, d.name))
        editions_by[slug] = eds
    built = []
    for slug in cfg["titles"]:
        publication_page(slug, cfg[slug], editions_by[slug], out, a.include_drafts)
        for e in editions_by[slug]:
            if e.status == "published" or (a.include_drafts and e.status == "draft"):
                edition_page(e, cfg[slug], out, a.include_drafts)
                built.append(e.path)
    home_page(cfg, editions_by, out, a.include_drafts)
    archive_page(cfg, editions_by, out, a.include_drafts)
    about_page(out)
    reuse_page(out)
    write(out, "/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    pages = sorted(str(p.relative_to(out)) for p in out.rglob("index.html"))
    unlisted = {e.path.strip("/") + "/index.html" for eds in editions_by.values() for e in eds if e.status != "published"}
    urls = "".join(f"<url><loc>{BASE}/{p[:-10]}</loc></url>" for p in pages if p not in unlisted)
    write(out, "/sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    stale = sorted(str(p.relative_to(out)) for p in (before - WRITTEN))
    if stale:
        print(f"stale files not written by this build (remove by hand): {stale}", file=sys.stderr)
    print(json.dumps({"out": str(out), "pages": len(pages), "editions_built": built, "stale": stale}))


if __name__ == "__main__":
    sys.exit(main())
