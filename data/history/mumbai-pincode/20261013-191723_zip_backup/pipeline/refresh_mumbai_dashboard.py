"""
Daily refresh for the MUMBAI JDA vs JDS pincode dashboard.
(Adapted copy of the Kolkata pipeline, 2026-09-25 -- same logic, Mumbai settings; keep the two aligned.)
Pulls fresh day-level deals (MySQL) + presentations (API) + monetizable listings,
rebuilds all derived aggregates (monthly + day-level DAILY block + per-JDA/manager
performance), and overwrites pipeline\\base\\JDA_JDS_Mumbai_Pincode_Dashboard_Lite.page in place
-- that's the one and only dashboard file in this package; it's also the file to host.

This script only ever updates the *data* embedded in that file (the DATA/DAILY/
MANAGER_TEAMS/JDA_FLAT/MANAGER_PINCODES/PINCODE_EMPLOYEES consts, plus the "Period"/
"Last refreshed" text) -- it never touches the page's HTML/CSS/JS structure. The Lite
layout (no map, no JDA-deployment-roster columns) was already baked into that file once;
there is no separate "full" dashboard behind it.

Run manually with: python refresh_mumbai_dashboard.py (run_daily.bat also builds the hosted SubVertical page)
Scheduled daily at 12:30 via Windows Task Scheduler -- see install_scheduled_task.bat.

Portable: PIPE_DIR is wherever this script itself lives. All reference files
(db_216.env, district_lookup.json, pincode_city_data_city_branch.xlsx, geonames_IN.txt)
must stay next to this script; the dashboard HTML must stay one folder up.

Geography: pincode-membership based, NOT final_datacity. Uses pincode_city_data_city_branch.xlsx
(Branch=="Mumbai" rows) as the authoritative "which pincodes belong to Mumbai branch" list.
Pulls deals closed by ANYONE for a Mumbai-branch pincode, regardless of which branch's
final_datacity the deal is tagged with. The reference file's own "Main/remote" column is ignored.
City scope: Mumbai has NO Main/Remote split (Sarvesh, 2026-09-25) -- every branch pincode is "main",
and the dashboard hides the City scope filter.
"""
import json
import os
import re
import datetime
import time
import urllib.request
import sys
from collections import defaultdict, Counter

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANCH = "Mumbai"
DASH_NAME = "JDA_JDS_Mumbai_Pincode_Dashboard_Lite.page"
# SubVertical-only packages keep this file as an internal working copy in pipeline\base\ (not
# for hosting); build_subvertical.py then builds the hosted SubVertical dashboard from it.
_BASE_DASH = os.path.join(PIPE_DIR, "base", DASH_NAME)
DASH_PATH = _BASE_DASH if os.path.exists(_BASE_DASH) else os.path.join(os.path.dirname(PIPE_DIR), DASH_NAME)
LOG_PATH = os.path.join(PIPE_DIR, "refresh_log.txt")
GEONAMES_PATH = os.path.join(PIPE_DIR, "geonames_IN.txt")

WINDOW_START = "2026-04-01"
_yesterday = datetime.date.today() - datetime.timedelta(days=1)
WINDOW_END = _yesterday.isoformat()
SEPT_START = "2026-09-01"  # JDA-deployment roster month (manually uploaded September snapshot)

BRANCH_PINCODES_PATH = os.path.join(PIPE_DIR, "pincode_city_data_city_branch.xlsx")
# Pincodes counted as Mumbai branch even though the reference file doesn't list them. None for now
# (Kolkata has three such overrides; see its pipeline).
EXTRA_BRANCH_PINCODES = set()


def load_branch_pincodes(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Sheet1"]
    headers = [c.value for c in ws[1]]
    pin_idx = headers.index("Pincode")
    branch_idx = headers.index("Branch")
    pins = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        pincode, branch = row[pin_idx], row[branch_idx]
        if pincode is None or branch is None:
            continue
        p = str(int(pincode)) if isinstance(pincode, float) else str(pincode).strip()
        if p.isdigit() and len(p) == 6 and str(branch).strip() == BRANCH:
            pins.add(p)
    return pins | EXTRA_BRANCH_PINCODES


log_lines = []
def log(msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    log_lines.append(line)


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v
    return env


def is_std(p):
    return bool(p) and p.isdigit() and len(p) == 6


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def month_range(start_str, end_str):
    start = datetime.date.fromisoformat(start_str).replace(day=1)
    end = datetime.date.fromisoformat(end_str).replace(day=1)
    months = []
    cur = start
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        cur = cur.replace(year=cur.year + 1, month=1) if cur.month == 12 else cur.replace(month=cur.month + 1)
    return months


def month_chunks(start_str, end_str):
    start = datetime.date.fromisoformat(start_str).replace(day=1)
    chunks = []
    cur = start
    end = datetime.date.fromisoformat(end_str)
    while cur <= end:
        nxt = cur.replace(year=cur.year + 1, month=1) if cur.month == 12 else cur.replace(month=cur.month + 1)
        chunk_start = max(cur, datetime.date.fromisoformat(start_str))
        chunk_end = min(nxt - datetime.timedelta(days=1), end)
        chunks.append((chunk_start.isoformat(), chunk_end.isoformat()))
        cur = nxt
    return chunks


def new_bucket():
    return {"jda_sales": 0.0, "jds_sales": 0.0, "b2b_count": 0, "anonymous_count": 0,
            "total_closed": 0, "team_breakdown": defaultdict(float),
            "rv3yr_sum": 0.0, "original_budget_sum": 0.0,
            "jds_rv3yr_sum": 0.0, "jds_original_budget_sum": 0.0}


def serialize_bucket(b):
    return {
        "jda_sales": round(b["jda_sales"], 2), "jds_sales": round(b["jds_sales"], 2),
        "b2b_count": b["b2b_count"], "anonymous_count": b["anonymous_count"], "total_closed": b["total_closed"],
        "rv3yr_sum": round(b["rv3yr_sum"], 2), "original_budget_sum": round(b["original_budget_sum"], 2),
        "jds_rv3yr_sum": round(b["jds_rv3yr_sum"], 2), "jds_original_budget_sum": round(b["jds_original_budget_sum"], 2),
        "team_breakdown": dict(b["team_breakdown"]),
    }


def upsert_const(content, name, payload):
    """Replace an existing `const NAME = ...;` in content, or insert a fresh one
    right after the DAILY const if it doesn't exist yet (first run)."""
    marker = f"const {name} = "
    idx = content.find(marker)
    if idx != -1:
        start = idx + len(marker)
        _, off = json.JSONDecoder().raw_decode(content[start:])
        end = start + off
        if content[end] == ';':
            end += 1
        return content[:idx] + marker + json.dumps(payload) + ";\n" + content[end:]
    daily_marker = "const DAILY = "
    di = content.find(daily_marker)
    assert di != -1, f"DAILY const not found (needed as insertion anchor for {name})"
    dstart = di + len(daily_marker)
    _, doff = json.JSONDecoder().raw_decode(content[dstart:])
    dend = dstart + doff
    if content[dend] == ';':
        dend += 1
    return content[:dend] + f"\nconst {name} = " + json.dumps(payload) + ";\n" + content[dend:]


GLOBAL_FREQ_CACHE_PATH = os.path.join(PIPE_DIR, "global_freq_cache.json")
GLOBAL_FREQ_CACHE_MAX_AGE_DAYS = 30
B2B_CACHE_PATH = os.path.join(PIPE_DIR, "b2b_monetizable_cache.json")
B2B_CACHE_MAX_AGE_DAYS = 30
DEAL_ROWS_PATH = os.path.join(PIPE_DIR, "deal_docid_rows.json")


def get_global_freq(cur, T, log):
    """Pan-India raw sales_group row-count frequency (step 5 tie-break input) -- the one
    unavoidable full-table scan in the tagging pipeline (~5-6 min as of 2026-09-23 against a
    109M-row table with no usable index for this). Cached to disk since this distribution
    barely moves day to day; refreshed at most every GLOBAL_FREQ_CACHE_MAX_AGE_DAYS days to
    keep the daily refresh fast, per Sarvesh's 2026-09-23 "speed this up" request."""
    if os.path.exists(GLOBAL_FREQ_CACHE_PATH):
        with open(GLOBAL_FREQ_CACHE_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        age_days = (datetime.datetime.now() - datetime.datetime.fromisoformat(cached["computed_at"])).total_seconds() / 86400
        if age_days <= GLOBAL_FREQ_CACHE_MAX_AGE_DAYS:
            log(f"Using cached pan-India global_freq ({age_days:.1f} days old, {len(cached['freq'])} sales groups).")
            return cached["freq"]
    log("Recomputing pan-India global_freq (full-table scan, cache stale or missing)...")
    cur.execute(f"""CREATE TABLE {T('global_freq')} AS
        SELECT sales_group, COUNT(*) AS gcount
        FROM vertical_owner.tbl_sales_group_tagged
        WHERE sales_group IS NOT NULL
        GROUP BY sales_group""")
    cur.execute(f"SELECT sales_group, gcount FROM {T('global_freq')}")
    freq = dict(cur.fetchall())
    with open(GLOBAL_FREQ_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"computed_at": datetime.datetime.now().isoformat(), "freq": freq}, f)
    log(f"Cached global_freq for {len(freq)} sales groups.")
    return freq


def bulk_insert_ignore(cur, table, columns, rows, log=None, batch_size=5000, upsert_col=None):
    """Chunked multi-row INSERT IGNORE. pymysql's cursor.executemany() on a multi-million-row
    list was observed (2026-09-23) inserting at only ~275 rows/sec -- far slower than a single
    batched multi-value INSERT per chunk. Builds the VALUES list explicitly instead.
    upsert_col: if given, existing rows get that column overwritten (ON DUPLICATE KEY UPDATE)
    instead of being left untouched."""
    cols = ", ".join(columns)
    total = len(rows)
    for i in range(0, total, batch_size):
        chunk = rows[i:i + batch_size]
        placeholders = ", ".join(["(" + ", ".join(["%s"] * len(columns)) + ")"] * len(chunk))
        flat_values = [v for row in chunk for v in row]
        if upsert_col:
            cur.execute(f"INSERT INTO {table} ({cols}) VALUES {placeholders} "
                        f"ON DUPLICATE KEY UPDATE {upsert_col} = VALUES({upsert_col})", flat_values)
        else:
            cur.execute(f"INSERT IGNORE INTO {table} ({cols}) VALUES {placeholders}", flat_values)
        if log and total > batch_size and (i // batch_size) % 20 == 0:
            log(f"  bulk insert into {table}: {min(i + batch_size, total)}/{total}")


HOT_CAT_SB_TABLE = "vertical_owner.tbl_company_vertical_mapping_SB"
CAT_MAPPING_TABLE = "vertical_owner.Sales_Manual_Group_mapping"


def load_catid_mapping(cur):
    """National_catid -> (Sales_group, sub_vertical) from Sales_Manual_Group_mapping (one row per catid)."""
    cur.execute(f"SELECT National_catid, Sales_group, sub_vertical FROM {CAT_MAPPING_TABLE}")
    return {str(c).strip(): ((sg or "").strip() or None, (sv or "").strip() or None) for c, sg, sv in cur.fetchall() if c is not None}


COMPANY_MASTER_TABLES = ["india_snapshot.tbl_company_master_mumbai",       # Mumbai-city (022...) docids
                         "india_snapshot.tbl_company_master_remotecity"]   # everything else (remote listings)


def hot_cat_info_lookup(docids, batch_size=1000):
    """docid -> National_catid parsed from hot_cat_info ("catid|##|Category Name") -- the
    business's primary category, or its hot category if it has no primary (NOT the same field as
    hot_category, which is always the most-searched one) -- read from the company master tables on server 240 (per Sarvesh 2026-09-24): tbl_company_master_mumbai
    only holds Mumbai-city docids, so anything not found there is looked up in
    tbl_company_master_remotecity. Both are indexed on docid. Needs pipeline\\db_240.env."""
    import pymysql
    env = load_env(os.path.join(PIPE_DIR, "db_240.env"))
    conn = pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                            password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=600)
    cur = conn.cursor()
    out = {}
    remaining = list(docids)
    for table in COMPANY_MASTER_TABLES:
        # The india_snapshot company masters are dropped and reloaded city by city on snapshot days (seen 2026-09-28):
        # a missing table is skipped, not fatal -- those docids stay Untagged and are retried on the next run.
        schema, name = table.split(".")
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s", (schema, name))
        if not cur.fetchone():
            log(f"WARNING: {table} not found (snapshot reload in progress?) -- skipped; its docids stay Untagged until the next run.")
            continue
        for i in range(0, len(remaining), batch_size):
            chunk = remaining[i:i + batch_size]
            cur.execute(f"SELECT docid, hot_cat_info FROM {table} WHERE docid IN ({','.join(['%s'] * len(chunk))})", chunk)
            for d, info in cur.fetchall():
                cat = (info or "").split("|##|")[0].strip()
                if cat.isdigit() and cat != "0":
                    out.setdefault(d, cat)
        remaining = [d for d in remaining if d not in out]
    conn.close()
    return out


def tag_docids(docids, env, log):
    """tag_docids_primary(), plus a hot_cat_info fallback for docids it leaves untagged:
    hot_cat_info category (company master tables, see hot_cat_info_lookup) ->
    Sales_group via Sales_Manual_Group_mapping
    (per Sarvesh 2026-09-24). Fallback results are NOT written to the permanent cache -- those
    docids stay 'Untagged' there, so a real tbl_sales_group_tagged assignment wins as soon as
    one appears."""
    import pymysql
    docid_to_sg = tag_docids_primary(docids, env, log)
    untagged = [d for d in docids if docid_to_sg.get(d, "Untagged") == "Untagged"]
    if not untagged:
        return docid_to_sg
    conn = pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                            password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=600)
    cur = conn.cursor()
    catmap = load_catid_mapping(cur)
    conn.close()
    hot = hot_cat_info_lookup(untagged)
    n = 0
    for d in untagged:
        sg = catmap.get(hot.get(d), (None, None))[0]
        if sg:
            docid_to_sg[d] = sg
            n += 1
    log(f"Sales-group tagging: hot_cat_info fallback tagged {n}/{len(untagged)} otherwise-untagged docids "
        f"({len(untagged) - n} remain Untagged).")
    return docid_to_sg


def tag_docids_primary(docids, env, log):
    """docid -> sales_group map for an arbitrary set of docids (used for both the deals
    population and the monetizable-listings population -- tagged together in one pass so the
    expensive parts of this pipeline only run once per refresh).
    Tagging logic (validated 2026-09-23, 0 unresolved docids for Kolkata's deal population):
    per docid, candidates = sales_group(s) tied for max num_of_categories_in_sales_group in
    vertical_owner.tbl_sales_group_tagged (ALL rows for the docid -- no callable_flag/paid filter
    on that table; per Sarvesh 2026-09-24 those flags are stale there and only the flags on
    tbl_b2b_panindia_data count, which the monetizable pull already applies); ties broken
    first by which candidate already has the most docids assigned via direct (non-tie) cases,
    then by raw pan-India row-count frequency of the sales_group name. See
    reference_db_servers_216_240_120 memory for the full spec.
    Docids cached as 'Untagged' are retried every run (cheap: indexed lookups on ~20K docids) and
    overwritten in the cache once a sales group appears for them."""
    import pymysql

    docids = sorted(docids)
    log(f"Sales-group tagging: {len(docids)} distinct docids requested.")
    if not docids:
        return {}

    conn = pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                            password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=600)
    cur = conn.cursor()
    cur.execute("USE ops_analytics")

    T = lambda name: f"ops_analytics.sarvesh_sgfeatmum_{name}"  # Mumbai-only scratch names: never collide with a Kolkata run
    CACHE_TABLE = "ops_analytics.sarvesh_docid_sg_permcache"
    names = ["deals", "docids", "pop", "dedup", "maxn", "candidates", "direct", "baseline",
             "ties", "tie_candidates", "tie_maxb", "tie_candidates2", "still_tied_after4",
             "global_freq", "step5_candidates", "step5_maxg", "step5_candidates2", "final_map"]
    for name in names:
        cur.execute(f"DROP TABLE IF EXISTS {T(name)}")

    # Permanent (never dropped) docid -> sales_group cache. A docid's category tag is stable
    # over time, so once tagged it never needs re-tagging -- each run only pays the (expensive,
    # unindexed) tie-break pipeline for docids it hasn't seen before. Per Sarvesh's 2026-09-23
    # "speed this up" request, after the monetizable-listings population turned out to be ~4M
    # docids (vs ~16-70K for deals alone) and made a from-scratch run take ~30 min.
    cur.execute(f"CREATE TABLE IF NOT EXISTS {CACHE_TABLE} (docid VARCHAR(64) PRIMARY KEY, sales_group VARCHAR(255))")

    cur.execute(f"CREATE TABLE {T('docids')} (docid VARCHAR(64) PRIMARY KEY)")
    bulk_insert_ignore(cur, T('docids'), ["docid"], [(d,) for d in docids], log)

    # 'Untagged' cache entries are not treated as final -- they're re-tried below, since the
    # tagging table can gain rows for a docid later (and pre-2026-09-24 entries were cached
    # under the old, since-removed callable_flag/paid filter).
    cur.execute(f"""SELECT k.docid, c.sales_group FROM {T('docids')} k
        JOIN {CACHE_TABLE} c ON k.docid = c.docid
        WHERE c.sales_group <> 'Untagged'""")
    cached_map = dict(cur.fetchall())
    log(f"Sales-group tagging: {len(cached_map)} already cached, {len(docids) - len(cached_map)} new/untagged docids need (re)tagging.")

    new_docids_table = f"{T('docids')}_new"
    cur.execute(f"DROP TABLE IF EXISTS {new_docids_table}")
    cur.execute(f"""CREATE TABLE {new_docids_table} AS
        SELECT k.docid FROM {T('docids')} k
        LEFT JOIN {CACHE_TABLE} c ON k.docid = c.docid
        WHERE c.docid IS NULL OR c.sales_group = 'Untagged'""")
    cur.execute(f"DROP TABLE {T('docids')}")
    cur.execute(f"RENAME TABLE {new_docids_table} TO {T('docids')}")
    cur.execute(f"SELECT COUNT(*) FROM {T('docids')}")
    n_new = cur.fetchone()[0]
    if n_new == 0:
        log("Sales-group tagging: nothing new to tag, using cache entirely.")
        for name in names:
            cur.execute(f"DROP TABLE IF EXISTS {T(name)}")
        conn.commit()
        conn.close()
        return cached_map

    cur.execute(f"""CREATE TABLE {T('pop')} AS
        SELECT t.docid, t.sales_group, t.num_of_categories_in_sales_group
        FROM vertical_owner.tbl_sales_group_tagged t
        JOIN {T('docids')} k ON t.docid = k.docid
        WHERE t.sales_group IS NOT NULL""")
    cur.execute(f"""CREATE TABLE {T('dedup')} AS
        SELECT docid, sales_group, MAX(num_of_categories_in_sales_group) AS n
        FROM {T('pop')} GROUP BY docid, sales_group""")
    cur.execute(f"""CREATE TABLE {T('maxn')} AS
        SELECT docid, MAX(n) AS maxn FROM {T('dedup')} GROUP BY docid""")
    cur.execute(f"""CREATE TABLE {T('candidates')} AS
        SELECT d.docid, d.sales_group, d.n
        FROM {T('dedup')} d JOIN {T('maxn')} m ON d.docid=m.docid AND d.n=m.maxn""")
    cur.execute(f"""CREATE TABLE {T('direct')} AS
        SELECT docid, MIN(sales_group) AS sales_group
        FROM {T('candidates')} GROUP BY docid HAVING COUNT(*)=1""")
    cur.execute(f"""CREATE TABLE {T('baseline')} AS
        SELECT sales_group, COUNT(*) AS baseline_count
        FROM {T('direct')} GROUP BY sales_group""")
    cur.execute(f"""CREATE TABLE {T('ties')} AS
        SELECT docid FROM {T('candidates')} GROUP BY docid HAVING COUNT(*)>=2""")
    cur.execute(f"""CREATE TABLE {T('tie_candidates')} AS
        SELECT c.docid, c.sales_group, COALESCE(b.baseline_count,0) AS bcount
        FROM {T('candidates')} c
        JOIN {T('ties')} t ON c.docid=t.docid
        LEFT JOIN {T('baseline')} b ON c.sales_group=b.sales_group""")
    cur.execute(f"""CREATE TABLE {T('tie_maxb')} AS
        SELECT docid, MAX(bcount) AS maxb FROM {T('tie_candidates')} GROUP BY docid""")
    cur.execute(f"""CREATE TABLE {T('tie_candidates2')} AS
        SELECT tc.docid, tc.sales_group, tc.bcount
        FROM {T('tie_candidates')} tc
        JOIN {T('tie_maxb')} m ON tc.docid=m.docid AND tc.bcount=m.maxb""")
    cur.execute(f"""CREATE TABLE {T('still_tied_after4')} AS
        SELECT docid FROM {T('tie_candidates2')} GROUP BY docid HAVING COUNT(*)>=2""")

    global_freq = get_global_freq(cur, T, log)
    cur.execute(f"DROP TABLE IF EXISTS {T('global_freq')}")
    cur.execute(f"CREATE TABLE {T('global_freq')} (sales_group VARCHAR(255), gcount INT)")
    cur.executemany(f"INSERT INTO {T('global_freq')} (sales_group, gcount) VALUES (%s, %s)", list(global_freq.items()))

    cur.execute(f"""CREATE TABLE {T('step5_candidates')} AS
        SELECT tc.docid, tc.sales_group, COALESCE(g.gcount,0) AS gcount
        FROM {T('tie_candidates2')} tc
        JOIN {T('still_tied_after4')} s ON tc.docid=s.docid
        LEFT JOIN {T('global_freq')} g ON tc.sales_group=g.sales_group""")
    cur.execute(f"""CREATE TABLE {T('step5_maxg')} AS
        SELECT docid, MAX(gcount) AS maxg FROM {T('step5_candidates')} GROUP BY docid""")
    cur.execute(f"""CREATE TABLE {T('step5_candidates2')} AS
        SELECT s.docid, s.sales_group, s.gcount
        FROM {T('step5_candidates')} s
        JOIN {T('step5_maxg')} m ON s.docid=m.docid AND s.gcount=m.maxg""")

    cur.execute(f"""SELECT COUNT(*) FROM (
        SELECT docid FROM {T('step5_candidates2')} GROUP BY docid HAVING COUNT(*)>=2) x""")
    unresolved = cur.fetchone()[0]
    if unresolved:
        log(f"WARNING: {unresolved} docid(s) still tied after the full tie-break cascade -- "
            f"these get an arbitrary (but deterministic) pick, see final_map construction.")

    cur.execute(f"""CREATE TABLE {T('final_map')} AS
        SELECT docid, sales_group FROM {T('direct')}
        UNION ALL
        SELECT docid, MIN(sales_group) AS sales_group FROM {T('tie_candidates2')}
        GROUP BY docid HAVING COUNT(*)=1
        UNION ALL
        SELECT docid, MIN(sales_group) AS sales_group FROM {T('step5_candidates2')}
        GROUP BY docid""")
    cur.execute(f"SELECT docid, sales_group FROM {T('final_map')}")
    newly_tagged = dict(cur.fetchall())
    log(f"Sales-group tagging: {len(newly_tagged)}/{n_new} new docids mapped "
        f"({n_new - len(newly_tagged)} still untagged -- cached as 'Untagged', retried next run).")

    if newly_tagged:
        # upsert: some of these were previously cached as 'Untagged' and must be overwritten
        bulk_insert_ignore(cur, CACHE_TABLE, ["docid", "sales_group"], list(newly_tagged.items()), log,
                           upsert_col="sales_group")
    # Also cache the genuinely-untagged docids as 'Untagged' -- otherwise they're indistinguishable
    # from "not yet processed" and would hit the full tie-break pipeline again every single run.
    cur.execute(f"""SELECT k.docid FROM {T('docids')} k
        LEFT JOIN {T('final_map')} f ON k.docid = f.docid
        WHERE f.docid IS NULL""")
    untagged_docids = [row[0] for row in cur.fetchall()]
    if untagged_docids:
        bulk_insert_ignore(cur, CACHE_TABLE, ["docid", "sales_group"], [(d, "Untagged") for d in untagged_docids], log)

    for name in names:
        cur.execute(f"DROP TABLE IF EXISTS {T(name)}")
    conn.commit()
    conn.close()

    docid_to_sg = dict(cached_map)
    docid_to_sg.update(newly_tagged)
    log(f"Sales-group tagging: {len(docid_to_sg)}/{len(docids)} total docids resolved "
        f"({len(cached_map)} from cache + {len(newly_tagged)} newly tagged).")
    return docid_to_sg


def compute_sales_group_by_day(deals, docid_to_sg, log):
    """Day-level sales_group deal counts per pincode, split by JDA (jda_flag==1) vs JDS
    (jda_flag==0) alongside the combined total -- the dashboard recomputes top-5-per-pincode
    client-side for whatever Period range is selected, same convention as DAILY.daily_deals /
    DAILY.daily_presence elsewhere in this file. Joint JDA+JDS deals (jda_flag==2) count 0.5 to
    each side, the same split the pincode table uses (Sarvesh, 2026-09-25); b2b/anonymous (3/10)
    count toward the combined total only."""
    sales_group_by_day = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"count": 0, "jda_count": 0, "jds_count": 0,
                                                                                     "f_count": 0, "f_jda": 0, "f_jds": 0})))
    for d in deals:
        if not d["docid"]:
            continue
        sg = docid_to_sg.get(d["docid"], "Untagged")
        b = sales_group_by_day[d["date"]][d["pincode"]][sg]
        g = float(d["dc_genio"] or 0)   # sales = SUM(dc_genio); a joint JDA+JDS deal gives half to each side
        b["count"] += g
        if d["jda_flag"] == 1:
            b["jda_count"] += g
        elif d["jda_flag"] == 0:
            b["jds_count"] += g
        elif d["jda_flag"] == 2:
            b["jda_count"] += g / 2
            b["jds_count"] += g / 2
        if d["fresh"] == 1:  # fresh-only part, so the dashboard can follow the Fresh/Renewal toggle
            b["f_count"] += g
            if d["jda_flag"] == 1:
                b["f_jda"] += g
            elif d["jda_flag"] == 0:
                b["f_jds"] += g
            elif d["jda_flag"] == 2:
                b["f_jda"] += g / 2
                b["f_jds"] += g / 2
    sales_group_by_day_out = {day: {p: {sg: dict(b) for sg, b in sgmap.items()} for p, sgmap in pmap.items()} for day, pmap in sales_group_by_day.items()}
    log(f"Sales-group day-level data: {len(sales_group_by_day_out)} days.")
    return sales_group_by_day_out


def compute_monetizable_sales_groups(monetizable_rows, docid_to_sg, log, always_keep_by_pincode=None):
    """Static (not day-level -- a listing snapshot, not a dated event) per-pincode sales_group
    breakdown of monetizable listings, with paid-listing penetration per sales group so a
    manager can see how much headroom is left to convert a given sales group.
    Truncated server-side to the top TOP_N sales groups per pincode (+ an 'Other' rollup) --
    a pincode can have hundreds of distinct sales groups among its listings, and the dashboard
    only ever displays a handful, so embedding the untruncated tail just bloats the file.
    always_keep_by_pincode (pincode -> set(sales_group)) force-keeps specific groups outside the
    top-N -- used so every sales group shown on the *deals* side of the dashboard has a matching
    paid-penetration figure available here, not just monetizable's own top sellers."""
    TOP_N = 10
    always_keep_by_pincode = always_keep_by_pincode or {}
    pincode_sg = defaultdict(lambda: defaultdict(lambda: {"total": 0, "paid": 0}))
    for pincode, docid, paid in monetizable_rows:
        sg = docid_to_sg.get(docid, "Untagged") if docid else "Untagged"
        b = pincode_sg[pincode][sg]
        b["total"] += 1
        if paid:
            b["paid"] += 1
    out = {}
    for p, sgmap in pincode_sg.items():
        ranked = sorted(sgmap.items(), key=lambda kv: -kv[1]["total"])
        keep_names = {sg for sg, _ in ranked[:TOP_N]} | (always_keep_by_pincode.get(p, set()) & sgmap.keys())
        top = [(sg, b) for sg, b in ranked if sg in keep_names]
        rest = [(sg, b) for sg, b in ranked if sg not in keep_names]
        trimmed = {sg: dict(b) for sg, b in top}
        if rest:
            other_total = sum(b["total"] for _, b in rest)
            other_paid = sum(b["paid"] for _, b in rest)
            trimmed["Other"] = {"total": other_total, "paid": other_paid}
        out[p] = trimmed
    log(f"Monetizable-listing sales-group data: {len(out)} pincodes (top {TOP_N} + Other + deal-referenced groups).")
    return out


def main():
    log("=== Mumbai dashboard daily refresh started ===")
    MONTHS = month_range(WINDOW_START, WINDOW_END)
    log(f"Window: {WINDOW_START} to {WINDOW_END} ({len(MONTHS)} month(s): {MONTHS})")

    branch_pincodes = load_branch_pincodes(BRANCH_PINCODES_PATH)
    log(f"Loaded {len(branch_pincodes)} Mumbai-branch pincodes from reference file.")

    def accepted(p):
        return p in branch_pincodes

    dl = json.load(open(os.path.join(PIPE_DIR, "district_lookup.json")))
    pin_to_districts = dl["pin_to_districts"]

    import pymysql
    env = load_env(os.path.join(PIPE_DIR, "db_216.env"))
    T = "`db_paidcontracts`.`daily_deals_closed_dump`"

    # ---------------- 1. deals, day-level (monthly chunks) ----------------
    deal_rows = []
    for c_start, c_end in month_chunks(WINDOW_START, WINDOW_END):
        log(f"Pulling deals {c_start}..{c_end} ...")
        conn = pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                                password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=120)
        QUERY = f"""
            SELECT dealclosed_date, pincode, dc_genio, jda_flag, final_team_type_name,
                   fresh, me, campaignid, original_budget, RV_3yr, docid
            FROM {T}
            WHERE pincode BETWEEN '400000' AND '421999'
              AND dealclosed_date BETWEEN '{c_start}' AND '{c_end}'
              AND dc_genio > 0
              AND fresh IN (0,1)
              AND pincode IS NOT NULL AND pincode <> ''
        """
        with conn.cursor() as cur:
            cur.execute(QUERY)
            cols = [c[0] for c in cur.description]
            chunk_rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        log(f"  -> {len(chunk_rows)} rows")
        deal_rows.extend(chunk_rows)
    log(f"Pulled {len(deal_rows)} raw deal rows.")

    deals = []
    excluded_bad_pincode = 0
    for r in deal_rows:
        p = str(r["pincode"]).strip()
        if not is_std(p) or not accepted(p):
            excluded_bad_pincode += 1
            continue
        d = r["dealclosed_date"]
        d_str = d.isoformat() if hasattr(d, "isoformat") else str(d)
        deals.append({
            "pincode": p, "date": d_str, "dc_genio": r["dc_genio"],
            # flag 10 deals are counted on the JDS side (Sarvesh, 2026-09-29); JDA flags 1 / 2 are never changed
            "jda_flag": 0 if r["jda_flag"] == 10 else r["jda_flag"],
            "final_team_type_name": r["final_team_type_name"], "fresh": r["fresh"], "me": (r.get("me") or "").strip(),
            "RV_3yr": to_float(r["RV_3yr"]), "original_budget": to_float(r["original_budget"]),
            "docid": (r.get("docid") or "").strip(),
        })
    log(f"Accepted deal rows: {len(deals)} (excluded {excluded_bad_pincode} -- pincode not in Mumbai-branch reference list)")

    daily_deals = {s: defaultdict(lambda: defaultdict(new_bucket)) for s in ("all", "fresh", "renewal")}
    rep_pin_sales = defaultdict(lambda: defaultdict(float))
    rep_pin_sales_by_day = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    split_stats = defaultdict(lambda: {"split_count": 0, "total_jda_side_deals": 0})

    for r in deals:
        day = r["date"]; p = r["pincode"]
        scenarios = ["all", "fresh" if r["fresh"] == 1 else "renewal"]
        jf = r["jda_flag"]; team = r["final_team_type_name"] or "BLANK"
        g = float(r["dc_genio"] or 0)   # sales = SUM(dc_genio) (Sarvesh 2026-09-30), not a row count
        rv3yr_val = r["RV_3yr"]; ob_val = r["original_budget"]
        if jf in (1, 2):
            emp = r["me"]
            if emp:
                sales_weight = g if jf == 1 else g / 2
                rep_pin_sales[p][emp] += sales_weight
                rep_pin_sales_by_day[day][p][emp] += sales_weight
            split_stats[p]["total_jda_side_deals"] += 1
            if jf == 2:
                split_stats[p]["split_count"] += 1
        for scn in scenarios:
            b = daily_deals[scn][day][p]
            b["total_closed"] += g
            b["rv3yr_sum"] += rv3yr_val
            b["original_budget_sum"] += ob_val
            if jf == 1:
                b["jda_sales"] += g; b["team_breakdown"]["JDA"] += g
            elif jf == 0:
                b["jds_sales"] += g
                tname = team if team != "BLANK" else "JDS - team not recorded"
                b["team_breakdown"][tname] += g
                b["jds_rv3yr_sum"] += rv3yr_val; b["jds_original_budget_sum"] += ob_val
            elif jf == 2:
                b["jda_sales"] += g / 2; b["jds_sales"] += g / 2
                tname = (team if team != "BLANK" else "Split - team not recorded") + " (split)"
                b["team_breakdown"][tname] += g
                b["jds_rv3yr_sum"] += rv3yr_val * 0.5; b["jds_original_budget_sum"] += ob_val * 0.5
            elif jf == 3:
                b["b2b_count"] += g
            elif jf == 10:
                b["anonymous_count"] += g

    daily_deals_out = {scn: {day: {p: serialize_bucket(b) for p, b in pmap.items()} for day, pmap in daily_deals[scn].items()} for scn in ("all", "fresh", "renewal")}
    log(f"daily_deals days: {len(daily_deals_out['all'])}")

    # Deal docids get tagged here (before the monetizable-listings section) so their sales_group
    # names are known in time to make sure the monetizable-listings truncation below always keeps
    # a matching entry for every sales group a pincode's deals actually reference -- otherwise the
    # "paid penetration" the dashboard shows next to a deals sales group could be missing whenever
    # that group wasn't independently in monetizable's own top-10-by-listing-count.
    deal_docids = {d["docid"] for d in deals if d["docid"]}
    docid_to_sg = tag_docids(deal_docids, env, log)
    sales_group_by_day = compute_sales_group_by_day(deals, docid_to_sg, log)
    # Deal-level (date, pincode, docid, jda_flag) rows + their sales groups, for the optional
    # ..\_rebuild_subvertical.py (per-docid sub-vertical view). Not read by this script.
    with open(DEAL_ROWS_PATH, "w", encoding="utf-8") as f:
        json.dump({"window_start": WINDOW_START, "window_end": WINDOW_END,
                   "rows": [[d["date"], d["pincode"], d["docid"], d["jda_flag"], d["fresh"], float(d["dc_genio"] or 0)] for d in deals if d["docid"]],
                   "docid_to_sg": {d: docid_to_sg.get(d, "Untagged") for d in deal_docids}}, f)
    deal_sales_groups_by_pincode = defaultdict(set)
    for day, pmap in sales_group_by_day.items():
        for p, sgmap in pmap.items():
            deal_sales_groups_by_pincode[p].update(sgmap.keys())

    # ---------------- 2. presentations, day-level ----------------
    log("Pulling presentation API, day by day...")
    BASE = "http://192.168.1.199:81/cron/presentation/cron/downloadPresentationData.php?date={}"
    start = datetime.date.fromisoformat(WINDOW_START)
    end = datetime.date.fromisoformat(WINDOW_END)
    daily_presence = {}
    emp_name = {}
    emp_mgr_counts = defaultdict(lambda: defaultdict(int))
    rep_pin_pres = defaultdict(lambda: defaultdict(int))
    rep_pin_pres_by_day = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    d = start; i = 0; n_days = (end - start).days + 1; errors = []
    while d <= end:
        i += 1
        day_str = d.isoformat()
        url = BASE.format(day_str)
        ok = False
        for attempt in range(5):
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                ok = True
                break
            except Exception as e:
                if attempt == 4:
                    errors.append((day_str, str(e)))
                else:
                    time.sleep(3 * (attempt + 1))
        if ok:
            text = text.strip("\n")
            lines = text.split("\n")
            bucket = defaultdict(lambda: {"count": 0, "employees": set(), "last_date": None})
            if lines and lines[0].strip():
                header = lines[0].rstrip("\r").split("\t")
                idx = {h: k for k, h in enumerate(header)}
                for line in lines[1:]:
                    line = line.rstrip("\r")
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) != len(header):
                        continue
                    emp_type = parts[idx.get("Employee Type", -1)] if "Employee Type" in idx else ""
                    if emp_type not in ("JDA", "Both"):
                        continue
                    pincode = (parts[idx.get("Pincode", -1)] if "Pincode" in idx else "").strip()
                    if not is_std(pincode) or not accepted(pincode):
                        continue
                    points = to_float(parts[idx.get("Points", -1)] if "Points" in idx else "")
                    revenue = to_float(parts[idx.get("Revenue", -1)] if "Revenue" in idx else "")
                    if not (points > 0 or revenue > 0):
                        continue
                    emp_id = parts[idx["Employee Id"]].strip()
                    b = bucket[pincode]
                    b["count"] += 1; b["employees"].add(emp_id); b["last_date"] = day_str
                    emp_name[emp_id] = parts[idx["Employee Name"]]
                    rep_pin_pres[pincode][emp_id] += 1
                    rep_pin_pres_by_day[day_str][pincode][emp_id] += 1
                    mgr = (parts[idx.get("Reporting Manager Name", -1)] if "Reporting Manager Name" in idx else "").strip()
                    if mgr:
                        emp_mgr_counts[emp_id][mgr] += 1
            daily_presence[day_str] = {p: {"count": b["count"], "employees": sorted(b["employees"]), "last_date": b["last_date"]} for p, b in bucket.items()}
        time.sleep(1.0)
        if i % 30 == 0:
            log(f"  presentation pull progress: {i}/{n_days} days, errors={len(errors)}")
        d += datetime.timedelta(days=1)
    log(f"Presentation pull done: {len(daily_presence)} days captured, errors={len(errors)}")
    if errors:
        log(f"  error days: {errors[:10]}")

    # ---------------- 3. monetizable listings (row-level: pincode, docid, paid -- feeds both
    # the existing per-pincode monetizable_listings count AND the new sales-group/paid-
    # penetration breakdown). Cached for B2B_CACHE_MAX_AGE_DAYS (~monthly): Sarvesh confirmed
    # 2026-09-23 this data barely moves day to day ("mota mota same"), and re-pulling it (4M+
    # rows) plus re-tagging that population was what made the daily refresh take ~30 min instead
    # of the original ~7-8. Deals/presentations above still run every day, unaffected. ----------------
    b2b_cache = None
    if os.path.exists(B2B_CACHE_PATH):
        with open(B2B_CACHE_PATH, encoding="utf-8") as f:
            b2b_cache = json.load(f)
        age_days = (datetime.datetime.now() - datetime.datetime.fromisoformat(b2b_cache["computed_at"])).total_seconds() / 86400
        if age_days > B2B_CACHE_MAX_AGE_DAYS:
            log(f"B2B/monetizable-listings cache is {age_days:.1f} days old (> {B2B_CACHE_MAX_AGE_DAYS}) -- refreshing.")
            b2b_cache = None
        else:
            log(f"Using cached B2B/monetizable-listings data ({age_days:.1f} days old).")

    if b2b_cache is None:
        log("Pulling monetizable listings (monthly refresh)...")
        MT = "`db_paidcontracts`.tbl_b2b_panindia_data"
        mon_rows = None
        for attempt in range(4):
            try:
                conn = pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                                        password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=1200)
                # Geography = Mumbai-branch pincode membership, NOT final_data_city (Sarvesh,
                # 2026-09-24). callable_flag/paid here are the only flags that count -- the
                # tagging table's own copies are ignored (see tag_docids).
                branch_pins = sorted(branch_pincodes)
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT pincode, docid, paid FROM {MT}
                        WHERE (callable_flag = 1 OR paid <> 0) AND mask = 0 AND freeze = 0 AND closedown_flag NOT IN (1,9,10)
                          AND pincode IN ({",".join(["%s"] * len(branch_pins))})
                    """, branch_pins)
                    mon_rows = cur.fetchall()
                conn.close()
                break
            except Exception as e:
                log(f"  monetizable query attempt {attempt+1} failed: {type(e).__name__}: {e}")
                if attempt == 3:
                    raise
                time.sleep(10 * (attempt + 1))
        # paid==1 only for "currently paid" -- paid==2 in this table means something other than an
        # active paid conversion (Sarvesh confirmed 2026-09-23 to exclude it from the numerator).
        monetizable_rows_raw = [(str(p), (d or "").strip(), paid == 1) for p, d, paid in mon_rows if p]
        monetizable_rows = [(p, d, paid) for p, d, paid in monetizable_rows_raw if accepted(p)]
        monetizable_by_pincode_raw = Counter(p for p, d, paid in monetizable_rows_raw)
        monetizable_by_pincode = {p: c for p, c in monetizable_by_pincode_raw.items() if accepted(p)}
        log(f"Monetizable listings pincodes: {len(monetizable_by_pincode_raw)} raw, {len(monetizable_by_pincode)} within branch territory ({len(monetizable_rows)} rows)")

        monetizable_docids = {d for _, d, _ in monetizable_rows if d}
        docid_to_sg_monetizable = tag_docids(monetizable_docids, env, log)
        monetizable_sales_groups = compute_monetizable_sales_groups(
            monetizable_rows, docid_to_sg_monetizable, log, deal_sales_groups_by_pincode)

        with open(B2B_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "computed_at": datetime.datetime.now().isoformat(),
                "monetizable_by_pincode": monetizable_by_pincode,
                "monetizable_sales_groups": monetizable_sales_groups,
            }, f)
        log("Cached B2B/monetizable-listings data for next run.")
    else:
        monetizable_by_pincode = b2b_cache["monetizable_by_pincode"]
        monetizable_sales_groups = b2b_cache["monetizable_sales_groups"]

    # ---------------- 4. monthly aggregates ----------------
    monthly_deals_acc = {s: {m: defaultdict(new_bucket) for m in MONTHS} for s in ("all", "fresh", "renewal")}
    for scn, day_map in daily_deals_out.items():
        for day, pmap in day_map.items():
            m = day[:7]
            if m not in MONTHS:
                continue
            for p, src in pmap.items():
                dst = monthly_deals_acc[scn][m][p]
                for k in ("jda_sales", "jds_sales", "b2b_count", "anonymous_count", "total_closed",
                          "rv3yr_sum", "original_budget_sum", "jds_rv3yr_sum", "jds_original_budget_sum"):
                    dst[k] += src[k]
                for k, v in src["team_breakdown"].items():
                    dst["team_breakdown"][k] += v
    monthly_deals_out = {scn: {m: {p: serialize_bucket(b) for p, b in monthly_deals_acc[scn][m].items()} for m in MONTHS} for scn in ("all", "fresh", "renewal")}

    monthly_presence_acc = {m: defaultdict(lambda: {"count": 0, "employees": set(), "last_date": None}) for m in MONTHS}
    for day, pmap in daily_presence.items():
        m = day[:7]
        if m not in MONTHS:
            continue
        for p, b in pmap.items():
            mb = monthly_presence_acc[m][p]
            mb["count"] += b["count"]; mb["employees"].update(b["employees"])
            if b["last_date"] and (not mb["last_date"] or b["last_date"] > mb["last_date"]):
                mb["last_date"] = b["last_date"]
    monthly_presence_out = {m: {p: {"count": b["count"], "employees": sorted(b["employees"]), "last_date": b["last_date"]} for p, b in pmap.items()} for m, pmap in monthly_presence_acc.items()}
    log("Rebuilt monthly_deals / monthly_presence.")

    # ---------------- 5. rep_breakdown, split_rate, manager_rollup (full window) ----------------
    emp_to_mgr = {emp: max(c.items(), key=lambda kv: kv[1])[0] for emp, c in emp_mgr_counts.items() if c}
    rep_pin_sales_merged = rep_pin_sales
    split_stats_merged = split_stats

    split_rate = {}
    for p, s in split_stats_merged.items():
        total = s["total_jda_side_deals"]
        split_rate[p] = {"split_count": s["split_count"], "total_jda_side_deals": total,
                          "split_rate_pct": round(100 * s["split_count"] / total, 1) if total else None}

    all_rep_pincodes = set(rep_pin_pres.keys()) | set(rep_pin_sales_merged.keys())
    rep_breakdown = {}
    for p in all_rep_pincodes:
        emps = set(rep_pin_pres.get(p, {}).keys()) | set(rep_pin_sales_merged.get(p, {}).keys())
        rows = [{"employee_id": emp, "employee_name": emp_name.get(emp, emp),
                 "presentations": rep_pin_pres.get(p, {}).get(emp, 0),
                 "jda_sales": round(rep_pin_sales_merged.get(p, {}).get(emp, 0.0), 2)} for emp in emps]
        rows.sort(key=lambda x: (-x["presentations"], -x["jda_sales"]))
        rep_breakdown[p] = rows
    log(f"rep_breakdown for {len(rep_breakdown)} pincodes.")

    pin_jda_all = defaultdict(float); pin_jds_all = defaultdict(float)
    for m in MONTHS:
        for p, b in monthly_deals_out["all"][m].items():
            pin_jda_all[p] += b["jda_sales"]; pin_jds_all[p] += b["jds_sales"]
    present_all = set()
    for m in MONTHS:
        present_all.update(monthly_presence_out[m].keys())
    gap_pincodes_all = set(p for p in present_all if pin_jda_all.get(p, 0) == 0 and pin_jds_all.get(p, 0) > 0)

    mgr_presentations = defaultdict(int); mgr_pins = defaultdict(set); mgr_sales = defaultdict(float)
    for p, empmap in rep_pin_pres.items():
        for emp, c in empmap.items():
            mgr = emp_to_mgr.get(emp)
            if mgr:
                mgr_presentations[mgr] += c; mgr_pins[mgr].add(p)
    for p, empmap in rep_pin_sales_merged.items():
        for emp, s in empmap.items():
            mgr = emp_to_mgr.get(emp)
            if mgr:
                mgr_sales[mgr] += s
    manager_rollup = []
    for mgr in set(mgr_presentations) | set(mgr_sales):
        pres_c = mgr_presentations.get(mgr, 0); sales_c = mgr_sales.get(mgr, 0.0); pins_m = mgr_pins.get(mgr, set())
        manager_rollup.append({"manager": mgr, "pincodes_covered": len(pins_m), "gap_pincodes": len(pins_m & gap_pincodes_all),
                                "total_presentations": pres_c, "jda_sales": round(sales_c, 1),
                                "conversion_rate_pct": round(100 * sales_c / pres_c, 2) if pres_c else None})
    manager_rollup.sort(key=lambda x: -x["gap_pincodes"])
    log(f"manager_rollup: {len(manager_rollup)} managers.")

    # ---------------- 5b. per-JDA / per-manager performance (Manager & JDA performance section) ----------------
    # Static employee metadata only -- name and (full-window majority-vote) manager assignment.
    # Counts (presentations/sales/pincodes-covered/gap-pincodes) are period-reactive and computed
    # client-side from DAILY.rep_pin_pres_by_day / DAILY.rep_pin_sales_by_day, per Sarvesh's
    # 2026-09-23 decision that this section should follow the Period filter like the main table.
    all_emps = set()
    for empmap in rep_pin_pres.values():
        all_emps.update(empmap.keys())
    for empmap in rep_pin_sales_merged.values():
        all_emps.update(empmap.keys())
    emp_meta = {emp: {"name": emp_name.get(emp, emp), "manager": emp_to_mgr.get(emp, "Unassigned")} for emp in all_emps}
    log(f"EMP_META: {len(emp_meta)} employees, {len(set(m['manager'] for m in emp_meta.values()))} managers.")

    # ---------------- 6. monthly_trend ----------------
    union_pincodes = sorted(set(rep_pin_pres) | set(rep_pin_sales_merged) | present_all | set(pin_jda_all) | set(pin_jds_all) | set(monetizable_by_pincode))
    monthly_gap_counts = []
    pincode_month_category = defaultdict(dict)
    for m in MONTHS:
        gap_count = 0
        for p in union_pincodes:
            b = monthly_deals_out["all"][m].get(p)
            jda_m = b["jda_sales"] if b else 0.0
            jds_m = b["jds_sales"] if b else 0.0
            pres_m = monthly_presence_out[m].get(p)
            present_m = bool(pres_m and pres_m["count"] > 0)
            if present_m and jda_m == 0 and jds_m > 0:
                cat = "gap"; gap_count += 1
            elif jda_m > 0 and jds_m > 0:
                cat = "both"
            elif jda_m > 0 and jds_m == 0:
                cat = "jda_only"
            elif present_m and jda_m == 0 and jds_m == 0:
                cat = "present_no_sales"
            else:
                cat = "notpresent"
            pincode_month_category[p][m] = cat
        monthly_gap_counts.append({"month": m, "gap_pincodes": gap_count})
    log(f"Monthly gap counts: {monthly_gap_counts}")

    # ---------------- 7. merge into existing DATA blob (preserve geo as static, refresh the rest) ----------------
    with open(DASH_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    def extract_const(content, name):
        marker = f"const {name} = "
        idx = content.find(marker)
        start = idx + len(marker)
        next_const = content.find("const ", start)
        s = content[start:next_const].rstrip()
        if s.endswith(";"):
            s = s[:-1]
        return json.loads(s), idx, next_const

    old_data, _, _ = extract_const(content, "DATA")

    ref_date = datetime.date.fromisoformat(WINDOW_END)
    geo_by_pin = defaultdict(list)
    new_pincodes_missing_geo = []
    for p in union_pincodes:
        if p not in old_data.get("pincode_static", {}) or not old_data["pincode_static"][p].get("geo"):
            new_pincodes_missing_geo.append(p)

    if new_pincodes_missing_geo:
        with open(GEONAMES_PATH, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 11:
                    continue
                geo_by_pin[parts[1]].append((parts[2], parts[9], parts[10]))

    # State votes (majority admin1/state per pincode) -- used for the "State" column.
    pin_state_votes = defaultdict(lambda: defaultdict(int))
    with open(GEONAMES_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 11:
                continue
            pin_state_votes[parts[1]][parts[3]] += 1

    def state_for(p):
        votes = pin_state_votes.get(p)
        return max(votes.items(), key=lambda kv: kv[1])[0] if votes else None

    pincode_static = {}
    for p in union_pincodes:
        old_ps = old_data.get("pincode_static", {}).get(p, {})
        ps = {}
        total_pres = 0; emp_set = set(); last_date = None
        for m in MONTHS:
            b = monthly_presence_out[m].get(p)
            if not b:
                continue
            total_pres += b["count"]; emp_set.update(b["employees"])
            if b["last_date"] and (not last_date or b["last_date"] > last_date):
                last_date = b["last_date"]
        ps["presentation_count"] = total_pres
        ps["distinct_jda_employees"] = len(emp_set)
        ps["last_jda_visit_date"] = last_date
        ps["days_since_last_jda_visit"] = (ref_date - datetime.date.fromisoformat(last_date)).days if last_date else None
        ps["rep_breakdown"] = rep_breakdown.get(p, [])
        sr = split_rate.get(p, {})
        ps["split_rate_pct"] = sr.get("split_rate_pct")
        ps["split_count"] = sr.get("split_count", 0)
        ps["total_jda_side_deals"] = sr.get("total_jda_side_deals", 0)
        if old_ps.get("geo"):
            ps["geo"] = old_ps["geo"]
        elif geo_by_pin.get(p):
            entries = geo_by_pin[p]
            lats = [float(e[1]) for e in entries]; lons = [float(e[2]) for e in entries]
            ps["geo"] = {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons), "sample_place": entries[0][0]}
        else:
            ps["geo"] = None
        ps["monetizable_listings"] = monetizable_by_pincode.get(p, old_ps.get("monetizable_listings", 0))
        ps["state"] = state_for(p)
        pincode_static[p] = ps

    if new_pincodes_missing_geo:
        still_missing = [p for p in new_pincodes_missing_geo if not pincode_static[p]["geo"]]
        if still_missing:
            log(f"WARNING: {len(still_missing)} pincode(s) with no geo on file (won't render on map): {still_missing}")

    # Mumbai: no Main/Remote split (Sarvesh, 2026-09-25) -- every pincode counts as main.
    main_pincodes = sorted(union_pincodes)
    log(f"Main pincodes: all {len(main_pincodes)} (Mumbai has no Main/Remote split)")

    new_data = dict(old_data)  # preserves pincodes_with_boundary (BOUNDARIES itself is untouched below)
    new_data["pincode_static"] = pincode_static
    new_data["monthly_deals"] = monthly_deals_out
    new_data["monthly_presence"] = monthly_presence_out
    new_data["manager_rollup"] = manager_rollup
    new_data["monthly_trend"] = {"months": MONTHS, "monthly_gap_counts": monthly_gap_counts, "pincode_month_category": dict(pincode_month_category)}
    new_data["union_pincodes"] = union_pincodes
    new_data["excluded_bad_pincode_deal_rows"] = excluded_bad_pincode
    new_data["months"] = MONTHS
    new_data["window_end"] = WINDOW_END
    new_data["main_pincodes"] = main_pincodes

    # Per-day, per-pincode, per-JDA presentations + JDA sales for September: feeds the dashboard's
    # "JDA deployed" / "Presentation by deployed JDA" columns (the roster is a Sept snapshot).
    sept_daily_rep = {}
    for day in sorted(set(rep_pin_pres_by_day) | set(rep_pin_sales_by_day)):
        if not (SEPT_START <= day <= WINDOW_END):
            continue
        pres_d, sales_d = rep_pin_pres_by_day.get(day, {}), rep_pin_sales_by_day.get(day, {})
        for p in set(pres_d) | set(sales_d):
            for emp in set(pres_d.get(p, {})) | set(sales_d.get(p, {})):
                sept_daily_rep.setdefault(day, {}).setdefault(p, {})[emp] = {
                    "presentations": pres_d.get(p, {}).get(emp, 0),
                    "jda_sales": round(sales_d.get(p, {}).get(emp, 0.0), 2)}
    log(f"sept_daily_rep: {len(sept_daily_rep)} September days.")

    new_daily = {
        "window_start": WINDOW_START, "window_end": WINDOW_END,
        "sept_start": SEPT_START, "sept_end": WINDOW_END,
        "daily_deals": daily_deals_out, "daily_presence": daily_presence, "sept_daily_rep": sept_daily_rep,
        "rep_pin_pres_by_day": rep_pin_pres_by_day, "rep_pin_sales_by_day": rep_pin_sales_by_day,
        "sales_group_by_day": sales_group_by_day,
    }

    def replace_const(content, name, payload):
        marker = f"const {name} = "
        idx = content.find(marker)
        start = idx + len(marker)
        next_const = content.find("const ", start)
        return content[:idx] + marker + json.dumps(payload) + ";\n" + content[next_const:]

    new_content = replace_const(content, "DATA", new_data)
    new_content = replace_const(new_content, "DAILY", new_daily)
    # JDA_DEPLOYMENT is left untouched -- preserved as-is (empty unless a roster is uploaded later)

    new_content = upsert_const(new_content, "EMP_META", emp_meta)
    new_content = upsert_const(new_content, "MONETIZABLE_SALES_GROUPS", monetizable_sales_groups)

    try:
        period_str = f"{datetime.date.fromisoformat(WINDOW_START).strftime('%-d %b %Y')} – {datetime.date.fromisoformat(WINDOW_END).strftime('%-d %b %Y')}"
    except ValueError:
        period_str = f"{datetime.date.fromisoformat(WINDOW_START).strftime('%d %b %Y')} – {datetime.date.fromisoformat(WINDOW_END).strftime('%d %b %Y')}"
    new_content = re.sub(r'Period: [^<]*?(?=</p>)', f'Period: {period_str}', new_content, count=1)

    now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    refreshed_line = f"Last refreshed: {now_str} &nbsp;|&nbsp; {len(union_pincodes)} pincodes &nbsp;|&nbsp; {len(gap_pincodes_all)} gap pincodes"
    new_content = re.sub(r'<p id="lastRefreshed"[^>]*>.*?</p>', f'<p id="lastRefreshed" style="margin-top:4px;color:#6b7690;">{refreshed_line}</p>', new_content, count=1, flags=re.DOTALL)

    with open(DASH_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    log(f"Wrote {DASH_PATH} ({os.path.getsize(DASH_PATH)} bytes).")
    log("=== Refresh complete ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {type(e).__name__}: {e}")
        raise
    finally:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(log_lines) + "\n\n")
