"""
Builds JDA_JDS_Mumbai_Pincode_Dashboard_Lite_SubVertical.page (MUMBAI; adapted copy of the Kolkata builder) (the hosted dashboard, one folder
up from this script) from the data refresh_mumbai_dashboard.py just wrote. run_daily.bat runs the
two scripts in order; run it by hand the same way: refresh first, then this.

Inputs from that run: the pipeline's dashboard file (DASH_PATH: pipeline\\base\\... in a
SubVertical-only package, else one folder up) and pipeline\\deal_docid_rows.json.

Sub-vertical is assigned PER DOCID (per Sarvesh 2026-09-24), not per sales group:
  docid -> tbl_company_vertical_mapping_SB.sub_vertical, as-is;
  else (docid not in that snapshot, or 'no category') -> the sub_vertical of its hot_cat_info
  category (primary category, else hot category; company master tables on server 240, via
  hot_cat_info_lookup) in Sales_Manual_Group_mapping;
  else 'Untagged'.
So one sales group can sit under several sub-verticals, and the hover tooltip lists the sales
groups under each sub-vertical.

Speed: the monetizable-listings side (4M+ listings: pull + tagging + sub-vertical lookup, ~15 min)
is cached in sv_listing_cache.json and rebuilt at most every SV_CACHE_MAX_AGE_DAYS days, the same
cadence as the pipeline's own b2b_monetizable_cache.json. Daily runs only look up the deal
docids (~1-2 min). Delete sv_listing_cache.json to force a rebuild.

Writes (only data consts + header text -- the page's HTML/CSS/JS is untouched):
  DATA / JDA_DEPLOYMENT / EMP_META / DAILY + Period / Last refreshed header, copied from DASH_PATH
  DAILY.sub_vertical_by_day[day][pincode][sub_vertical] = {count, jda_count, jds_count}
  DAILY.sv_sg_by_day[day][pincode][sub_vertical][sales_group] = [deals, JDA, JDS] (joint deals 0.5 each)  (tooltip)
  MONETIZABLE_SUB_VERTICALS[pincode][sub_vertical] = {total, paid}  (top 5 + deal-referenced + Other)
  MONETIZABLE_SV_SG[pincode][sub_vertical][sales_group] = [total, paid]  (tooltip, untruncated)
If a ..\\_snapshots folder exists, it also refreshes the local SQLite snapshot there when the
listing cache is rebuilt (developer convenience, not needed for the dashboard).
"""
import datetime
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PIPE_DIR)
SV_PATH = os.path.join(ROOT, "JDA_JDS_Mumbai_Pincode_Dashboard_Lite_SubVertical.page")
SV_CACHE_PATH = os.path.join(PIPE_DIR, "sv_listing_cache.json")
SV_CACHE_MAX_AGE_DAYS = 30
SNAPSHOT_DIR = os.path.join(ROOT, "_snapshots")
TOP_N = 5

sys.path.insert(0, PIPE_DIR)
from refresh_mumbai_dashboard import (  # noqa: E402
    DASH_PATH, load_env, load_branch_pincodes, BRANCH_PINCODES_PATH, DEAL_ROWS_PATH,
    HOT_CAT_SB_TABLE, bulk_insert_ignore, tag_docids, load_catid_mapping, hot_cat_info_lookup)


def log(msg):
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] build_subvertical: {msg}", flush=True)


def const_span(content, name):
    marker = f"\nconst {name} = "
    idx = content.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    obj, off = json.JSONDecoder().raw_decode(content[start:])
    end = start + off
    if content[end] == ";":
        end += 1
    return obj, idx + 1, start, end


def get_const(content, name):
    span = const_span(content, name)
    assert span, f"const {name} not found"
    return span[0]


def set_const(content, name, payload, replaces=None):
    """Replace const `name` (or, on first run, the older const `replaces` it supersedes)."""
    span = const_span(content, name) or (replaces and const_span(content, replaces))
    assert span, f"const {name} not found"
    _, idx, _, end = span
    return content[:idx] + f"const {name} = " + json.dumps(payload, separators=(",", ":")) + ";" + content[end:]


env = load_env(os.path.join(PIPE_DIR, "db_216.env"))


def connect():
    import pymysql
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=1200)


def sb_sub_verticals(docids, bulk):
    """docid -> sub_vertical from tbl_company_vertical_mapping_SB ('no category' / blank skipped).
    bulk=True uses a scratch-table join (millions of docids); otherwise batched IN lookups."""
    out = {}
    conn = connect()
    cur = conn.cursor()
    if bulk:
        cur.execute("DROP TABLE IF EXISTS ops_analytics.sarvesh_sgmvmum_docids")
        cur.execute("CREATE TABLE ops_analytics.sarvesh_sgmvmum_docids (docid VARCHAR(100) PRIMARY KEY)")
        bulk_insert_ignore(cur, "ops_analytics.sarvesh_sgmvmum_docids", ["docid"], [(d,) for d in docids], log)
        cur.execute(f"""SELECT k.docid, s.sub_vertical FROM ops_analytics.sarvesh_sgmvmum_docids k
            JOIN {HOT_CAT_SB_TABLE} s ON s.docid = k.docid""")
        rows = cur.fetchall()
        cur.execute("DROP TABLE ops_analytics.sarvesh_sgmvmum_docids")
        conn.commit()
    else:
        rows = []
        docids = list(docids)
        for i in range(0, len(docids), 1000):
            chunk = docids[i:i + 1000]
            cur.execute(f"SELECT docid, sub_vertical FROM {HOT_CAT_SB_TABLE} WHERE docid IN ({','.join(['%s'] * len(chunk))})", chunk)
            rows.extend(cur.fetchall())
    catmap = load_catid_mapping(cur)
    conn.close()
    for d, sv in rows:
        sv = (sv or "").strip()
        if sv and sv.lower() != "no category":
            out[d] = sv
    n_sb = len(out)
    missing = [d for d in docids if d not in out]
    hot = hot_cat_info_lookup(missing)
    for d in missing:
        sv = catmap.get(hot.get(d), (None, None))[1]
        if sv:
            out[d] = sv
    log(f"sub_vertical for {len(docids)} docids: {n_sb} from SB table, {len(out) - n_sb} via hot_cat_info, "
        f"{len(docids) - len(out)} Untagged.")
    return out


def build_listing_cache():
    """Pull monetizable listings (same filters as the pipeline), tag sales group + sub-vertical,
    and aggregate to per-pincode breakdowns. ~15 min."""
    branch_pins = sorted(load_branch_pincodes(BRANCH_PINCODES_PATH))
    log(f"Rebuilding listing cache: pulling monetizable listings for {len(branch_pins)} pincodes (~6-10 min)...")
    mon_rows = None
    for attempt in range(4):
        try:
            conn = connect()
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT pincode, docid, paid FROM `db_paidcontracts`.tbl_b2b_panindia_data
                    WHERE (callable_flag = 1 OR paid <> 0) AND mask = 0 AND freeze = 0 AND closedown_flag NOT IN (1,9,10)
                      AND pincode IN ({",".join(["%s"] * len(branch_pins))})""", branch_pins)
                mon_rows = [(str(p), (d or "").strip(), paid) for p, d, paid in cur.fetchall() if p]
            conn.close()
            break
        except Exception as e:
            log(f"  pull attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    log(f"Pulled {len(mon_rows)} listing rows.")
    docids = sorted({d for _, d, _ in mon_rows if d})
    docid_to_sg = tag_docids(set(docids), env, log)
    docid_to_sv = sb_sub_verticals(docids, bulk=True)
    by_sv = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    sv_sg = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))
    for p, d, paid in mon_rows:
        sv = docid_to_sv.get(d, "Untagged") if d else "Untagged"
        sg = docid_to_sg.get(d, "Untagged") if d else "Untagged"
        for b in (by_sv[p][sv], sv_sg[p][sv][sg]):
            b[0] += 1
            if paid == 1:
                b[1] += 1
    cache = {
        "computed_at": datetime.datetime.now().isoformat(),
        "by_sv": {p: dict(m) for p, m in by_sv.items()},
        "sv_sg": {p: {sv: dict(sgm) for sv, sgm in svm.items()} for p, svm in sv_sg.items()},
    }
    with open(SV_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, separators=(",", ":"))
    log(f"Listing cache written: {SV_CACHE_PATH} ({len(cache['by_sv'])} pincodes).")
    if os.path.isdir(SNAPSHOT_DIR):
        sconn = sqlite3.connect(os.path.join(SNAPSHOT_DIR, "b2b_panindia_mumbai.db"))
        for t in ("b2b_rows", "docid_sg", "docid_sv", "snapshot_meta"):
            sconn.execute(f"DROP TABLE IF EXISTS {t}")
        sconn.execute("CREATE TABLE b2b_rows (pincode TEXT, docid TEXT, paid INTEGER)")  # raw paid 0/1/2 -- read as paid == 1
        sconn.executemany("INSERT INTO b2b_rows VALUES (?, ?, ?)", mon_rows)
        sconn.execute("CREATE INDEX idx_b2b_pincode ON b2b_rows(pincode)")
        sconn.execute("CREATE INDEX idx_b2b_docid ON b2b_rows(docid)")
        sconn.execute("CREATE TABLE docid_sg (docid TEXT PRIMARY KEY, sales_group TEXT)")
        sconn.executemany("INSERT INTO docid_sg VALUES (?, ?)", [(d, docid_to_sg.get(d, "Untagged")) for d in docids])
        sconn.execute("CREATE TABLE docid_sv (docid TEXT PRIMARY KEY, sub_vertical TEXT)")
        sconn.executemany("INSERT INTO docid_sv VALUES (?, ?)", [(d, docid_to_sv.get(d, "Untagged")) for d in docids])
        sconn.execute("CREATE TABLE snapshot_meta (pulled_at TEXT)")
        sconn.execute("INSERT INTO snapshot_meta VALUES (?)", (datetime.datetime.now().isoformat(),))
        sconn.commit()
        sconn.close()
        log("Local _snapshots SQLite refreshed.")
    return cache


def main():
    with open(DASH_PATH, encoding="utf-8") as f:
        main_html = f.read()
    with open(SV_PATH, encoding="utf-8") as f:
        sv_html = f.read()
    with open(DEAL_ROWS_PATH, encoding="utf-8") as f:
        deal_rows = json.load(f)
    daily = get_const(main_html, "DAILY")
    assert deal_rows["window_end"] == daily["window_end"], \
        f"{DEAL_ROWS_PATH} ({deal_rows['window_end']}) is not from the same run as {DASH_PATH} ({daily['window_end']})"

    cache = None
    if os.path.exists(SV_CACHE_PATH):
        with open(SV_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
        age = (datetime.datetime.now() - datetime.datetime.fromisoformat(cache["computed_at"])).total_seconds() / 86400
        if age > SV_CACHE_MAX_AGE_DAYS:
            log(f"Listing cache is {age:.1f} days old -- rebuilding.")
            cache = None
        else:
            log(f"Using listing cache ({age:.1f} days old).")
    if cache is None:
        cache = build_listing_cache()

    # ---- deals (daily) ----
    deal_docids = sorted({r[2] for r in deal_rows["rows"] if r[2]})
    docid_to_sv = sb_sub_verticals(deal_docids, bulk=False)
    deal_sg = deal_rows["docid_to_sg"]
    sub_by_day, sv_sg_by_day = {}, {}
    for row in deal_rows["rows"]:
        day, p, d, jda_flag = row[:4]
        fresh = row[4] if len(row) > 4 else None  # None = older rows without the fresh flag
        g = float(row[5]) if len(row) > 5 else 1.0   # sales = SUM(dc_genio); older rows without it count 1
        sv = docid_to_sv.get(d, "Untagged") if d else "Untagged"
        sg = deal_sg.get(d, "Untagged") if d else "Untagged"
        b = sub_by_day.setdefault(day, {}).setdefault(p, {}).setdefault(sv, {"count": 0, "jda_count": 0, "jds_count": 0})
        b["count"] += g
        if jda_flag == 1:
            b["jda_count"] += g
        elif jda_flag == 0:
            b["jds_count"] += g
        elif jda_flag == 2:  # joint JDA+JDS deal: half each, same as the pincode table
            b["jda_count"] += g / 2
            b["jds_count"] += g / 2
        if fresh is not None:
            for k in ("f_count", "f_jda", "f_jds"):
                b.setdefault(k, 0)
            if fresh == 1:
                b["f_count"] += g
                b["f_jda"] += g if jda_flag == 1 else g / 2 if jda_flag == 2 else 0
                b["f_jds"] += g if jda_flag == 0 else g / 2 if jda_flag == 2 else 0
        m = sv_sg_by_day.setdefault(day, {}).setdefault(p, {}).setdefault(sv, {})
        # [deals, JDA, JDS] (+ [freshDeals, freshJDA, freshJDS] when the fresh flag is known); joint deals 0.5 each
        c = m.setdefault(sg, [0, 0, 0, 0, 0, 0] if fresh is not None else [0, 0, 0])
        jda_w = g if jda_flag == 1 else g / 2 if jda_flag == 2 else 0
        jds_w = g if jda_flag == 0 else g / 2 if jda_flag == 2 else 0
        c[0] += g
        c[1] += jda_w
        c[2] += jds_w
        if fresh == 1 and len(c) == 6:
            c[3] += g
            c[4] += jda_w
            c[5] += jds_w
    daily["sub_vertical_by_day"] = sub_by_day
    daily["sv_sg_by_day"] = sv_sg_by_day
    log(f"Deals: {len(deal_rows['rows'])} rows assigned to sub-verticals.")

    # ---- monetizable: truncate per pincode to top 5 + every sub-vertical the deals reference ----
    deal_svs = defaultdict(set)
    for pmap in sub_by_day.values():
        for p, svmap in pmap.items():
            deal_svs[p].update(svmap)
    monetizable_sub_verticals = {}
    for p, svmap in cache["by_sv"].items():
        ranked = sorted(svmap.items(), key=lambda kv: -kv[1][0])
        keep = {sv for sv, _ in ranked[:TOP_N]} | (deal_svs.get(p, set()) & svmap.keys())
        out = {sv: {"total": b[0], "paid": b[1]} for sv, b in ranked if sv in keep}
        rest = [b for sv, b in ranked if sv not in keep]
        if rest:
            out["Other"] = {"total": sum(b[0] for b in rest), "paid": sum(b[1] for b in rest)}
        monetizable_sub_verticals[p] = out

    # ---- write ----
    for name in ("DATA", "JDA_DEPLOYMENT", "EMP_META", "BOUNDARIES"):
        sv_html = set_const(sv_html, name, get_const(main_html, name))
    sv_html = set_const(sv_html, "DAILY", daily)
    sv_html = set_const(sv_html, "MONETIZABLE_SUB_VERTICALS", monetizable_sub_verticals)
    sv_html = set_const(sv_html, "MONETIZABLE_SV_SG", cache["sv_sg"], replaces="MONETIZABLE_SALES_GROUPS")
    period = re.search(r"Period: [^<]*?(?=</p>)", main_html).group(0)
    sv_html = re.sub(r"Period: [^<]*?(?=</p>)", lambda _: period, sv_html, count=1)
    refreshed = re.search(r'<p id="lastRefreshed"[^>]*>.*?</p>', main_html, flags=re.DOTALL).group(0)
    sv_html = re.sub(r'<p id="lastRefreshed"[^>]*>.*?</p>', lambda _: refreshed, sv_html, count=1, flags=re.DOTALL)
    tmp = SV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(sv_html)
    os.replace(tmp, SV_PATH)  # atomic swap: the hosted file is never half-written
    log(f"Wrote {SV_PATH} ({len(sv_html):,} chars).")


if __name__ == "__main__":
    main()
