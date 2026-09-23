#!/usr/bin/env python3
"""Compute the numbers an issue quotes, from the record, and write them
beside the issue draft. The editor writes issue.md; every figure in it must
appear in numbers.json, which this tool regenerates from data files.

Writes <title>/issues/<issue_id>/:
  numbers.json   every measure, with the series, periods and values used
  numbers.md     the same as a table for the issue's "The numbers" section
  evidence.json  capture files and hashes used, and the retail record's
                 git commit and file hash

Usage:
    python3 tools/issue.py --title lobster --issue 2026-09-baseline --run-id <id>

Retail reference rows are read, never written, from the path in config.json.
Sellers are reported by letter (sources.json retail_reference_sources).
"""

import argparse
import collections
import json
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Title, config, iso, load_json, read_jsonl, sha256_file  # noqa: E402


def pct(a, b):
    return None if not a or b is None else round((b - a) / a * 100, 1)


def series_map(rows, run_id):
    """{series_id: {period: value}} from the given run (last row per key wins)."""
    out = collections.defaultdict(dict)
    for r in rows:
        if r["run_id"] == run_id and r.get("period") and r.get("value") is not None:
            out[r["series_id"]][r["period"]] = r["value"]
    return out


def yoy(sm, sid, period):
    y, m = period.split("-")
    prior = f"{int(y) - 1}-{m}"
    two = f"{int(y) - 2}-{m}"
    d = sm[sid]
    return {"period": period, "value": d.get(period),
            "prior_year_period": prior, "prior_year_value": d.get(prior),
            "yoy_pct": pct(d.get(prior), d.get(period)),
            "two_years_back_period": two, "two_years_back_value": d.get(two),
            "vs_two_years_pct": pct(d.get(two), d.get(period))}


def latest_period(sm, sid):
    return max(sm[sid]) if sm.get(sid) else None


def resolve_retail_root(configured):
    """The configured path is the Mac path. When this runs in the Cowork VM,
    connected folders are mounted under $HOME/mnt/<folder>. FA_RETAIL_ROOT
    overrides both. Fails visibly if none exists."""
    import os
    cands = [os.environ.get("FA_RETAIL_ROOT"), configured]
    home = Path.home()
    if configured.startswith("/Users/"):
        parts = Path(configured).parts  # ('/', 'Users', name, 'Projects', 'websites', ...)
        for i in range(3, len(parts)):  # any suffix may be the mounted folder
            cands.append(str(home / "mnt" / Path(*parts[i:])))
    for c in cands:
        if c and Path(c).is_dir():
            return Path(c)
    raise SystemExit(f"retail record not found; tried {cands}")


def retail_reference(cfg_t, letters, baseline_month):
    """Per-seller rows for the reference series in the baseline month, from the
    wedding record. Returns rows keyed by letter plus a flat/changed count over
    every live series the record holds for the month."""
    rr = cfg_t["retail_reference"]
    root = resolve_retail_root(rr["path"])
    obs_file = root / rr["observations"]
    rows = read_jsonl(obs_file)
    # highest revision per observation id
    latest = {}
    for r in rows:
        latest[r["observation_id"].split("#r")[0]] = r
    rows = [r for r in latest.values()
            if r.get("observation_type") == "CONTEMPORANEOUS_CAPTURE"
            and r.get("captured_at", "")[:7] == baseline_month
            and r.get("listed_price") is not None]
    spec = rr["reference_series"]
    ref = collections.defaultdict(list)
    for r in rows:
        if (r.get("product_category") == spec["product_category"]
                and r.get("shell_type") == spec["shell_type"]
                and str(r.get("size_class")) == spec["size_class"]
                and (r.get("quantity") or 1) == spec["quantity"]
                and r.get("normalized_price_per_lobster") is not None):
            ref[r["source_id"]].append((r["captured_at"][:10], r["normalized_price_per_lobster"],
                                        r.get("availability_status")))
    ref_rows = []
    for sid, obs in sorted(ref.items()):
        obs.sort()
        ref_rows.append({"seller": letters.get(sid, {}).get("letter", "?"),
                         "observations": [{"date": d, "usd_per_lobster": p, "availability": a}
                                          for d, p, a in obs],
                         "first": obs[0][1], "last": obs[-1][1],
                         "change_pct": pct(obs[0][1], obs[-1][1])})
    # flat vs changed across all live series with >= 2 observations in the month
    by_series = collections.defaultdict(list)
    for r in rows:
        if r.get("product_category") == "live" and not str(r.get("comparability_series", "")).startswith("REVIEW|"):
            by_series[r["comparability_series"]].append((r["captured_at"], r["listed_price"]))
    flat = changed = 0
    changes = []
    for s, obs in by_series.items():
        if len(obs) < 2:
            continue
        obs.sort()
        if obs[0][1] == obs[-1][1]:
            flat += 1
        else:
            changed += 1
            src = s.split("|")[0]
            changes.append({"seller": letters.get(src, {}).get("letter", "?"),
                            "series": s.split("|", 1)[1], "from": obs[0][1], "to": obs[-1][1],
                            "change_pct": pct(obs[0][1], obs[-1][1])})
    dates = sorted({r["captured_at"][:10] for r in rows})
    git = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or None
    return {"reference_series": spec, "sellers": ref_rows,
            "live_series_with_2_or_more_observations": flat + changed,
            "flat": flat, "changed": changed, "changes": changes,
            "capture_dates": dates, "sellers_observed": len({r["source_id"] for r in rows}),
            "record": {"path": rr["path"], "file": rr["observations"],
                       "sha256": sha256_file(obs_file), "git_commit": git}}


def compute_lobster(n, sm, t, cfg_t, a):
    ppi = "WPU02230503"
    n["ppi_lobsters"] = yoy(sm, ppi, latest_period(sm, ppi))
    # winter peak: max Jan-Apr of latest year vs prior year
    ly = n["ppi_lobsters"]["period"][:4]
    peaks = {}
    for y in (str(int(ly) - 1), ly):
        vals = {p: v for p, v in sm[ppi].items() if p[:4] == y and p[5:] in ("01", "02", "03", "04")}
        if vals:
            p = max(vals, key=vals.get)
            peaks[y] = {"period": p, "value": vals[p]}
    n["ppi_lobsters_winter_peak"] = peaks | {"change_pct": pct(peaks[str(int(ly) - 1)]["value"], peaks[ly]["value"]) if len(peaks) == 2 else None}
    n["ppi_seafood"] = yoy(sm, "WPU0223", latest_period(sm, "WPU0223"))
    n["ppi_finished_consumer_foods"] = yoy(sm, "WPUFD4111", latest_period(sm, "WPUFD4111"))
    n["cpi_food_away_from_home"] = yoy(sm, "CUUR0000SEFV", latest_period(sm, "CUUR0000SEFV"))
    n["cpi_food_at_home"] = yoy(sm, "CUUR0000SAF11", latest_period(sm, "CUUR0000SAF11"))

    uv = "foss_imp_live_homarus_portland_me_usd_per_lb"
    kg = "foss_imp_live_homarus_portland_me_kilos"
    lp = latest_period(sm, uv)
    n["noaa_import_unit_value_portland"] = yoy(sm, uv, lp)
    n["noaa_import_kilos_portland"] = yoy(sm, kg, lp)
    y = int(lp[:4])
    ytd = {yy: sum(v for p, v in sm[kg].items() if p[:4] == str(yy) and p[5:] <= lp[5:]) for yy in (y - 1, y)}
    n["noaa_import_kilos_portland_ytd"] = {"through_month": lp[5:], str(y - 1): ytd[y - 1], str(y): ytd[y],
                                           "change_pct": pct(ytd[y - 1], ytd[y])}

    ev = "dmr_maine_lobster_ex_vessel_usd_per_lb"
    lb = "dmr_maine_lobster_landings_lb"
    val = "dmr_maine_lobster_landings_value_usd"
    dl = latest_period(sm, ev)
    dy = int(dl[:4])
    n["dmr_ex_vessel_september"] = {str(yy): sm[ev].get(f"{yy}-09") for yy in range(dy - 5, dy + 1)}
    n["dmr_ex_vessel_september"]["yoy_pct"] = pct(sm[ev].get(f"{dy - 1}-09"), sm[ev].get(f"{dy}-09"))
    annual = {}
    for yy in range(dy - 10, dy + 1):
        L = sum(v for p, v in sm[lb].items() if p[:4] == str(yy))
        V = sum(v for p, v in sm[val].items() if p[:4] == str(yy))
        if L:
            annual[str(yy)] = {"pounds": L, "value_usd": V, "usd_per_lb": round(V / L, 2)}
    n["dmr_annual"] = annual
    peak = max(annual, key=lambda k: annual[k]["pounds"])
    n["dmr_landings_decline"] = {"peak_year": peak, "peak_pounds": annual[peak]["pounds"],
                                 "latest_year": str(dy), "latest_pounds": annual[str(dy)]["pounds"],
                                 "change_pct": pct(annual[peak]["pounds"], annual[str(dy)]["pounds"]),
                                 "latest_is_preliminary": True}
    n["dmr_latest_period"] = dl

    ers = {k: v for k, v in sm.items() if k.startswith("ers_fpo|")}
    # ERS rows carry period None; series_map dropped them. Re-read directly.
    ers_rows = [r for r in read_jsonl(t.indicators) if r["run_id"] == a.run_id and r["series_id"].startswith("ers_fpo|")]
    want = {"Fish and seafood": ["Year-over-year", "Mid point of forecast interval 2026", "Mid point of forecast interval 2027",
                                 "Lower bound of forecast interval 2027", "Upper bound of forecast interval 2027"],
            "Food away from home": ["Year-over-year", "Mid point of forecast interval 2026", "Mid point of forecast interval 2027"]}
    n["ers_food_price_outlook"] = {}
    for r in ers_rows:
        _, cat, attr = r["series_id"].split("|", 2)
        for w in want.get(cat, []):
            if attr.startswith(w) or w in attr:
                n["ers_food_price_outlook"][f"{cat} — {attr}"] = r["value"]

    bm = a.baseline_month or a.issue[:7]
    n["retail_reference"] = retail_reference(cfg_t, t.retail_letters(), bm)
    if n["retail_reference"]["sellers"]:
        lasts = [s["last"] for s in n["retail_reference"]["sellers"]]
        n["retail_reference"]["range_last"] = [min(lasts), max(lasts)]
        n["retail_reference"]["median_last"] = statistics.median(lasts)
        spec = cfg_t["retail_reference"]["reference_series"]
        n["retail_reference"]["implied_usd_per_lb_at_min_weight"] = [round(x / float(spec["size_class"]), 2) for x in n["retail_reference"]["range_last"]]



def numbers_md_lobster(n):
    dy = int(n["dmr_latest_period"][:4])
    # numbers.md
    def fm(v, d=2):
        return "—" if v is None else f"{v:,.{d}f}"
    def fp(v):
        return "—" if v is None else f"{v:+.1f}%"
    L = ["| Measure | Latest | Same period, prior year | Change | Source |", "|---|---|---|---|---|"]
    for key, label, src, d in [("ppi_lobsters", "PPI, lobsters (index)", "BLS WPU02230503", 1),
                                ("ppi_seafood", "PPI, unprocessed and prepared seafood (index)", "BLS WPU0223", 1),
                                ("cpi_food_away_from_home", "CPI, food away from home (index)", "BLS CUUR0000SEFV", 1),
                                ("noaa_import_unit_value_portland", "Live lobster imports through Portland, ME, unit value ($/lb)", "NOAA FOSS, HTS 0306320010", 2),
                                ("noaa_import_kilos_portland", "Live lobster imports through Portland, ME (kg)", "NOAA FOSS, HTS 0306320010", 0)]:
        x = n[key]
        L.append(f"| {label} | {fm(x['value'], d)} ({x['period']}) | {fm(x['prior_year_value'], d)} ({x['prior_year_period']}) | {fp(x['yoy_pct'])} | {src} |")
    s = n["dmr_ex_vessel_september"]
    L.append(f"| Maine ex-vessel price, September ($/lb, derived) | {fm(s.get(str(dy)))} ({dy}, preliminary) | {fm(s.get(str(dy-1)))} ({dy-1}) | {fp(s['yoy_pct'])} | Maine DMR landings |")
    rr = n["retail_reference"]
    if rr["sellers"]:
        L.append(f"| Consumer reference: single live hard-shell 1.25 lb, counter or pickup ($ each) | {fm(rr['range_last'][0])} to {fm(rr['range_last'][1])} ({', '.join(rr['capture_dates'])}; sellers {', '.join(x['seller'] for x in rr['sellers'])}) | — | — | Field Assembly observation record |")
    return "\n".join(L) + "\n"


def fm(v, d=2):
    return "—" if v is None else f"{v:,.{d}f}"


def fp(v):
    return "—" if v is None else f"{v:+.1f}%"


def weekly_yoy(sm, sid, period, window=4):
    """Weekly series (YYYY-MM-DD week ending): latest week against the nearest
    week ending within 4 days of one year earlier, and the trailing `window`
    week average against the same window a year earlier."""
    from datetime import date, timedelta
    d = sm[sid]
    def nearest(target):
        c = [p for p in d if abs((date.fromisoformat(p) - target).days) <= 4]
        return min(c, key=lambda p: abs((date.fromisoformat(p) - target).days)) if c else None
    latest = date.fromisoformat(period)
    prior = nearest(latest - timedelta(days=364))
    weeks = sorted(p for p in d if p <= period)[-window:]
    prior_weeks = [nearest(date.fromisoformat(w) - timedelta(days=364)) for w in weeks]
    prior_weeks = [w for w in prior_weeks if w]
    avg = round(sum(d[w] for w in weeks) / len(weeks), 4) if weeks else None
    pavg = round(sum(d[w] for w in prior_weeks) / len(prior_weeks), 4) if len(prior_weeks) == window else None
    return {"period": period, "value": d.get(period), "prior_year_period": prior,
            "prior_year_value": d.get(prior) if prior else None,
            "yoy_pct": pct(d.get(prior), d.get(period)) if prior else None,
            f"trailing_{window}wk_avg": avg, f"trailing_{window}wk_weeks": weeks,
            f"prior_year_{window}wk_avg": pavg, f"trailing_{window}wk_yoy_pct": pct(pavg, avg)}


def compute_egg_butter(n, sm, t, cfg_t, a):
    for key, sid in [("ppi_chicken_eggs", "WPU0171"), ("ppi_butter", "WPU0232"),
                     ("cpi_eggs", "CUUR0000SEFH"), ("cpi_butter", "CUUR0000SS10011"),
                     ("cpi_food_away_from_home", "CUUR0000SEFV")]:
        n[key] = yoy(sm, sid, latest_period(sm, sid))
    ppi = "WPU0171"
    # egg PPI peak within the last 24 months, for the "how far from the peak" sentence
    recent = sorted(sm[ppi])[-24:]
    pk = max(recent, key=lambda p: sm[ppi][p])
    n["ppi_chicken_eggs_24m_peak"] = {"period": pk, "value": sm[ppi][pk],
                                      "latest_vs_peak_pct": pct(sm[ppi][pk], sm[ppi][recent[-1]])}
    bw = "ndpsr_butter_usd_per_lb"
    n["ndpsr_butter_weekly"] = weekly_yoy(sm, bw, latest_period(sm, bw))
    bs = "ndpsr_butter_sales_lb"
    n["ndpsr_butter_sales_weekly"] = weekly_yoy(sm, bs, latest_period(sm, bs))
    cme = "cme_butter_aa_weekly_avg_usd_per_lb"
    n["cme_butter_aa_weekly_avg"] = {"period": latest_period(sm, cme), "value": sm[cme].get(latest_period(sm, cme))} if sm.get(cme) else None
    cl = "cme_butter_aa_friday_close_usd_per_lb"
    n["cme_butter_aa_friday_close"] = {"period": latest_period(sm, cl), "value": sm[cl].get(latest_period(sm, cl))} if sm.get(cl) else None
    for key, sid in [("shell_egg_national_warehouse_large", "ams_shell_egg_national_delivered_warehouse_large_cents_per_dozen"),
                     ("shell_egg_midwest_producer_large", "ams_shell_egg_midwest_paid_to_producers_fob_large_cents_per_dozen"),
                     ("shell_egg_northeast_warehouse_large", "ams_shell_egg_northeast_delivered_warehouse_large_cents_per_dozen")]:
        if sm.get(sid):
            lp = latest_period(sm, sid)
            n[key] = weekly_yoy(sm, sid, lp) if len(sm[sid]) > 1 else {"period": lp, "value": sm[sid][lp], "prior_year_period": None, "prior_year_value": None, "yoy_pct": None}
            # the report itself states last week's figure; carry it from the row note
            row = next((r for r in read_jsonl(t.indicators) if r["run_id"] == a.run_id and r["series_id"] == sid and r["period"] == lp), None)
            if row:
                import re
                m = re.search(r"last reported ([\d.]+)", row.get("notes", ""))
                n[key]["prior_week_value_as_reported"] = float(m.group(1)) if m else None
    for key, sid in [("nass_layers_avg", "nass_layers_avg_thousand"),
                     ("nass_table_egg_production", "nass_table_egg_production_million")]:
        n[key] = yoy(sm, sid, latest_period(sm, sid))
    ers_rows = [r for r in read_jsonl(t.indicators) if r["run_id"] == a.run_id and r["series_id"].startswith("ers_fpo|")]
    want = ["Year-over-year", "Mid point of forecast interval 2026", "Mid point of forecast interval 2027",
            "Lower bound of forecast interval 2027", "Upper bound of forecast interval 2027"]
    n["ers_food_price_outlook"] = {}
    for r in ers_rows:
        _, cat, attr = r["series_id"].split("|", 2)
        if cat in ("Eggs", "Dairy products", "Fats and oils", "Food away from home") and any(attr.startswith(w) for w in want):
            n["ers_food_price_outlook"][f"{cat} — {attr}"] = r["value"]
    n["retail_reference"] = {"record": None, "sellers": []}


def numbers_md_egg_butter(n):
    L = ["| Measure | Latest | Same period, prior year | Change | Source |", "|---|---|---|---|---|"]
    for key, label, src, d in [("ppi_chicken_eggs", "PPI, chicken eggs (index)", "BLS WPU0171", 1),
                                ("cpi_eggs", "CPI, eggs (index)", "BLS CUUR0000SEFH", 1),
                                ("ppi_butter", "PPI, butter (index)", "BLS WPU0232", 1),
                                ("cpi_butter", "CPI, butter (index)", "BLS CUUR0000SS10011", 1),
                                ("cpi_food_away_from_home", "CPI, food away from home (index)", "BLS CUUR0000SEFV", 1),
                                ("nass_layers_avg", "Average layers during the month (thousand)", "USDA NASS Chickens and Eggs", 0),
                                ("nass_table_egg_production", "Table egg production (million eggs)", "USDA NASS Chickens and Eggs", 1)]:
        x = n[key]
        L.append(f"| {label} | {fm(x['value'], d)} ({x['period']}) | {fm(x['prior_year_value'], d)} ({x['prior_year_period']}) | {fp(x['yoy_pct'])} | {src} |")
    b = n["ndpsr_butter_weekly"]
    L.append(f"| Butter, wholesale weighted average ($/lb, week ending) | {fm(b['value'], 4)} ({b['period']}) | {fm(b['prior_year_value'], 4)} ({b['prior_year_period']}) | {fp(b['yoy_pct'])} | USDA AMS NDPSR |")
    L.append(f"| Butter, wholesale weighted average, trailing 4-week ($/lb) | {fm(b['trailing_4wk_avg'], 4)} | {fm(b['prior_year_4wk_avg'], 4)} | {fp(b['trailing_4wk_yoy_pct'])} | USDA AMS NDPSR |")
    if n.get("cme_butter_aa_weekly_avg"):
        c = n["cme_butter_aa_weekly_avg"]
        L.append(f"| CME Grade AA butter, weekly average ($/lb, week ending) | {fm(c['value'], 4)} ({c['period']}) | — | — | CME via USDA AMS Dairy Market News |")
    for key, label in [("shell_egg_national_warehouse_large", "Shell eggs, Large, national delivered warehouse (cents/dozen, week ending)"),
                       ("shell_egg_midwest_producer_large", "Shell eggs, Large, Midwest paid to producers (cents/dozen, week ending)")]:
        if key in n:
            x = n[key]
            pw = x.get("prior_week_value_as_reported")
            L.append(f"| {label} | {fm(x['value'])} ({x['period']}; prior week {fm(pw)}) | {fm(x.get('prior_year_value'))} ({x.get('prior_year_period') or '—'}) | {fp(x.get('yoy_pct'))} | USDA AMS report 2848 |")
    return "\n".join(L) + "\n"


MODELS = {"lobster": compute_lobster, "egg_butter": compute_egg_butter}
NUMBERS_MD = {"lobster": numbers_md_lobster, "egg_butter": numbers_md_egg_butter}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--baseline-month", default=None, help="YYYY-MM for retail reference")
    a = ap.parse_args()
    t = Title(a.title)
    cfg = config()
    cfg_t = cfg[a.title]
    sm = series_map(read_jsonl(t.indicators), a.run_id)
    if not sm:
        sys.exit(f"no indicator rows for run {a.run_id}")
    n = {"issue": a.issue, "title": cfg_t["name"], "run_id": a.run_id, "computed_at": iso()}

    MODELS[cfg_t.get("issue_model", a.title)](n, sm, t, cfg_t, a)

    out = t.issues / a.issue
    out.mkdir(parents=True, exist_ok=True)
    (out / "numbers.json").write_text(json.dumps(n, indent=1, sort_keys=True) + "\n")

    # evidence.json: the capture files behind this run
    caps = []
    for src in t.sources():
        cj = t.captures / a.run_id / src["id"] / "capture.json"
        if cj.exists():
            rec = load_json(cj)
            for f in rec["fetches"]:
                caps.append({"source_id": src["id"], "fetch": f["name"], "url": f.get("final_url") or f["requested_url"],
                             "fetched_at": f.get("fetched_at"), "path": f.get("path"), "sha256": f.get("sha256"),
                             "status": f["status"]})
    (out / "evidence.json").write_text(json.dumps({"issue": a.issue, "run_id": a.run_id, "captures": caps,
                                                   "retail_record": n["retail_reference"]["record"]}, indent=1) + "\n")

    (out / "numbers.md").write_text(NUMBERS_MD[cfg_t.get("issue_model", a.title)](n))
    print(json.dumps(n, indent=1, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
