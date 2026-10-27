"""
Mumbai top-200 JDA categories (Sarvesh, 2026-09-29): deals and monetizable listings for the 200 categories the Mumbai JDAs
prioritise (pipeline/top200_categories_mumbai.csv, from 'Top 200 cats - mumbai'). An addition -- nothing existing changes.

A business counts under a category by its MAIN category: the National_catid in hot_cat_info (primary category, else hot
category) -- Sarvesh's choice, so every business counts once and totals add up.

  deals     every row of deal_docid_rows.json (this run's deals, same geography / JDA-JDS split as the dashboard, flag 10
            already counted as JDS) whose business's main category is in the 200:
            deals_by_day[day][pincode][catid] = [deals, JDA, JDS, fresh deals, fresh JDA, fresh JDS]  (joint = 0.5 each)
  listings  monetizable listings (callable_flag = 1 OR paid <> 0, same filter as the dashboard) in Mumbai-branch pincodes
            whose main category is in the 200: listings[pincode][catid] = [listings, currently paid]
            -- pulled at most every 30 days (top200_listing_cache.json), like the other listing data.
Writes pipeline/top200_data.json, which tools/build_ui_lab.py embeds in the UI lab page. Runs after the refresh:
    python build_top200.py
"""
import csv
import datetime as dt
import json
import os
import sys

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPE_DIR)
from refresh_mumbai_dashboard import (load_env, load_branch_pincodes, BRANCH_PINCODES_PATH, DEAL_ROWS_PATH,  # noqa: E402
                                      COMPANY_MASTER_TABLES)

CATS_PATH = os.path.join(PIPE_DIR, "top200_categories_mumbai.csv")
CACHE_PATH = os.path.join(PIPE_DIR, "top200_listing_cache.json")
OUT_PATH = os.path.join(PIPE_DIR, "top200_data.json")
LOG_PATH = os.path.join(PIPE_DIR, "refresh_log.txt")
CACHE_MAX_AGE_DAYS = 30


def log(msg):
    line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] build_top200: {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def connect(envfile, timeout=1800):
    import pymysql
    env = load_env(os.path.join(PIPE_DIR, envfile))
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env["MYSQL_PORT"]), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=timeout)


def main_cat_map(cats, pins):
    """docid -> main-category catid, for businesses whose main category is one of the 200. The Mumbai master is scanned
    once (~1 min); the much bigger remote-city master only for Mumbai-branch pincodes (indexed)."""
    ph = ",".join(["%s"] * len(cats))
    out = {}
    conn = connect("db_240.env")
    cur = conn.cursor()
    for table in COMPANY_MASTER_TABLES:
        schema, name = table.split(".")
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s", (schema, name))
        if not cur.fetchone():
            log(f"WARNING: {table} not found (snapshot reload?) -- skipped this run.")
            continue
        if name.endswith("_remotecity"):
            pl = sorted(pins)
            for i in range(0, len(pl), 50):
                chunk = pl[i:i + 50]
                cur.execute(f"SELECT docid, SUBSTRING_INDEX(hot_cat_info,'|##|',1) FROM {table} WHERE pincode IN ({','.join(['%s'] * len(chunk))}) "
                            f"AND SUBSTRING_INDEX(hot_cat_info,'|##|',1) IN ({ph})", chunk + cats)
                for d, c in cur.fetchall():
                    out.setdefault(d, c.strip())
        else:
            cur.execute(f"SELECT docid, SUBSTRING_INDEX(hot_cat_info,'|##|',1) FROM {table} WHERE SUBSTRING_INDEX(hot_cat_info,'|##|',1) IN ({ph})", cats)
            for d, c in cur.fetchall():
                out.setdefault(d, c.strip())
        log(f"{name}: {len(out):,} top-200 businesses so far")
    conn.close()
    return out


def build_listings(cats, pins):
    catmap = main_cat_map(cats, pins)
    conn = connect("db_216.env")
    cur = conn.cursor()
    pl = sorted(pins)
    listings, n = {}, 0
    # one query for all branch pincodes (the listings table has no pincode index: every batch would be a full scan)
    for i in range(0, len(pl), len(pl)):
        chunk = pl[i:i + len(pl)]
        cur.execute(f"""SELECT pincode, docid, paid FROM `db_paidcontracts`.tbl_b2b_panindia_data
            WHERE (callable_flag = 1 OR paid <> 0) AND mask = 0 AND freeze = 0 AND closedown_flag NOT IN (1,9,10)
              AND pincode IN ({','.join(['%s'] * len(chunk))})""", chunk)
        for p, d, paid in cur.fetchall():
            p = str(p).strip()
            c = catmap.get((d or "").strip())
            if not c or p not in pins:
                continue
            a = listings.setdefault(p, {}).setdefault(c, [0, 0])
            a[0] += 1
            if paid == 1:
                a[1] += 1
            n += 1
    conn.close()
    log(f"listings: {n:,} monetizable listings in the 200 categories across {len(listings)} pincodes")
    return listings, catmap


def main():
    cats_rows = list(csv.DictReader(open(CATS_PATH, encoding="utf-8")))
    cats = [r["national_catid"] for r in cats_rows]
    catset = set(cats)
    pins = {str(p) for p in load_branch_pincodes(BRANCH_PINCODES_PATH)}

    cache, catmap = None, None
    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH, encoding="utf-8"))
        age = (dt.datetime.now() - dt.datetime.fromisoformat(cache["computed_at"])).total_seconds() / 86400
        if age > CACHE_MAX_AGE_DAYS or cache.get("cats") != cats:
            log(f"listing cache is {age:.1f} days old or the category list changed -- rebuilding")
            cache = None
        else:
            log(f"using listing cache ({age:.1f} days old)")
    if cache is None:
        listings, catmap = build_listings(cats, pins)
        cache = {"computed_at": dt.datetime.now().isoformat(), "cats": cats, "listings": listings}
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))

    # deals: this run's deal rows, each business by its main category
    deal_rows = json.load(open(DEAL_ROWS_PATH, encoding="utf-8"))
    docids = sorted({r[2] for r in deal_rows["rows"] if r[2]})
    if catmap is None:
        # daily run: look up only the deal businesses (a few thousand), by docid
        catmap = {}
        conn = connect("db_240.env", timeout=600)
        cur = conn.cursor()
        for table in COMPANY_MASTER_TABLES:
            schema, name = table.split(".")
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s", (schema, name))
            if not cur.fetchone():
                log(f"WARNING: {table} not found -- skipped"); continue
            todo = [d for d in docids if d not in catmap]
            for i in range(0, len(todo), 1000):
                chunk = todo[i:i + 1000]
                cur.execute(f"SELECT docid, SUBSTRING_INDEX(hot_cat_info,'|##|',1) FROM {table} WHERE docid IN ({','.join(['%s'] * len(chunk))})", chunk)
                for d, c in cur.fetchall():
                    c = (c or "").strip()
                    if c in catset:
                        catmap.setdefault(d, c)
        conn.close()
    deals, n = {}, 0
    for row in deal_rows["rows"]:
        day, p, d, jf = row[:4]
        fresh = row[4] if len(row) > 4 else None
        c = catmap.get(d)
        if not c:
            continue
        g = float(row[5]) if len(row) > 5 else 1.0   # sales = SUM(dc_genio)
        jw = g if jf == 1 else g / 2 if jf == 2 else 0
        sw = g if jf == 0 else g / 2 if jf == 2 else 0
        a = deals.setdefault(day, {}).setdefault(p, {}).setdefault(c, [0, 0, 0, 0, 0, 0])
        a[0] += g; a[1] += jw; a[2] += sw
        if fresh == 1:
            a[3] += g; a[4] += jw; a[5] += sw
        n += 1
    log(f"deals: {n:,} of {len(deal_rows['rows']):,} deals are in the 200 categories")
    out = {"computed_at": dt.datetime.now().isoformat(timespec="seconds"), "window_end": deal_rows["window_end"],
           "listings_computed_at": cache["computed_at"],
           "cats": [{"rank": int(r["rank"]), "catid": r["national_catid"], "name": r["category_name"]} for r in cats_rows],
           "deals_by_day": deals, "listings": cache["listings"]}
    tmp = OUT_PATH + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), separators=(",", ":"))
    os.replace(tmp, OUT_PATH)
    log(f"wrote {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
