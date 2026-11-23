"""Step 1 of the refresh: pull the raw numbers for the JD India sales overview into cache\\raw.pkl.

Period: 1 April of the current financial year up to the latest deal date, and the same dates one year earlier, day by
day (the page adds up whatever dates are picked). The rest of last financial year is pulled by month, for the trend
line only. Database access is read-only.

Counting rules (the same as the Kolkata, Mumbai and Pan India JDA dashboards):
  deals = SUM(dc_genio), RV 3yr = SUM(RV_3yr), rows with dc_genio > 0 and fresh 0/1 only;
  jda_flag 1 JDA, 2 joint (half to JDA, half to JDS), 3 B2B, 10 anonymous, anything else JDS.
"""
import datetime
import os
import pickle
import sys
import time

import pymysql

PIPE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(PIPE, "cache")
TABLE = "`db_paidcontracts`.`daily_deals_closed_dump`"
BIG_FLOOR = 50000   # deals of RV 3yr at least this (rupees) are kept one by one, so the page can leave out big deals


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def load_env():
    """The deals database login: pipeline\\db_216.env, or the file named by JDA_DB_ENV."""
    path = os.path.join(PIPE, "db_216.env")
    if not os.path.exists(path):
        path = os.environ.get("JDA_DB_ENV", "")
    if not path or not os.path.exists(path):
        sys.exit("Missing pipeline\\db_216.env: copy db_216.env.template to db_216.env and fill in the database login (see SETUP.md).")
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def connect(env, timeout):
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=timeout)


def year_back(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:   # 29 Feb
        return d.replace(year=d.year - 1, day=28)


def valid_pin(p):
    p = str(p or "").strip()
    return p if p.isdigit() and len(p) == 6 else None


def run(env, sql, args, tries=3):
    """One read-only query, retried on a dropped connection."""
    for attempt in range(tries):
        try:
            c = connect(env, 1800)
            cur = c.cursor()
            cur.execute(sql, args)
            rows = cur.fetchall()
            c.close()
            return rows
        except pymysql.err.OperationalError as e:
            log(f"Query attempt {attempt + 1} failed: {e}")
            if attempt == tries - 1:
                raise
            time.sleep(15)


def main():
    env = load_env()
    os.makedirs(CACHE, exist_ok=True)

    end = run(env, f"SELECT MAX(dealclosed_date) FROM {TABLE} WHERE dealclosed_date <= CURDATE()", ())[0][0]
    fy = datetime.date(end.year if end.month >= 4 else end.year - 1, 4, 1)
    ly_from, ly_to = year_back(fy), year_back(end)
    ly_fy_end = fy - datetime.timedelta(days=1)
    log(f"Data to {end}. This year {fy} to {end}; last year {ly_from} to {ly_to} (by day), "
        f"{ly_to + datetime.timedelta(days=1)} to {ly_fy_end} (by month).")

    # deals by day: pincode x date x channel flag x fresh x ECS
    t0 = time.time()
    rows = run(env, f"""
        SELECT TRIM(pincode), dealclosed_date, jda_flag, fresh, IFNULL(ecs_flag_original, 0), SUM(dc_genio), SUM(RV_3yr)
        FROM {TABLE}
        WHERE (dealclosed_date BETWEEN %s AND %s OR dealclosed_date BETWEEN %s AND %s)
          AND dc_genio > 0 AND fresh IN (0,1) AND pincode IS NOT NULL AND pincode <> ''
        GROUP BY 1, 2, 3, 4, 5""", (fy, end, ly_from, ly_to))
    deals, dropped = [], [0.0, 0.0]
    for p, day, flag, fresh, ecs, n, rv in rows:
        pin = valid_pin(p)
        if not pin:
            dropped[0 if day >= fy else 1] += float(n or 0)
            continue
        deals.append((pin, day, int(flag or 0), int(fresh), 1 if int(ecs or 0) == 1 else 0, float(n or 0), float(rv or 0)))
    log(f"Deal groups: {len(deals):,} ({time.time() - t0:.0f}s); deals dropped for a pincode that is not 6 digits: "
        f"{dropped[0]:.0f} this year, {dropped[1]:.0f} last year")

    # the rest of last financial year, by month (trend line only)
    rest = []
    if ly_to < ly_fy_end:
        t0 = time.time()
        rows = run(env, f"""
            SELECT TRIM(pincode), DATE_FORMAT(dealclosed_date, '%%Y-%%m'), SUM(dc_genio), SUM(RV_3yr)
            FROM {TABLE}
            WHERE dealclosed_date BETWEEN %s AND %s
              AND dc_genio > 0 AND fresh IN (0,1) AND pincode IS NOT NULL AND pincode <> ''
            GROUP BY 1, 2""", (ly_to + datetime.timedelta(days=1), ly_fy_end))
        for p, ym, n, rv in rows:
            pin = valid_pin(p)
            if pin:
                rest.append((pin, ym, float(n or 0), float(rv or 0)))
        log(f"Last year's remaining months: {len(rest):,} pincode-months ({time.time() - t0:.0f}s)")

    # unique customers = COUNT(DISTINCT docid), from the same deal rows. Distinct counts do not add up across days or
    # places, so the page gets the customer per pincode and day (this year and last year's same dates) and counts
    # distinct ids itself; the rest of last year comes per pincode and month (trend only). Ids are numbered here.
    t0 = time.time()
    doc_ix, cust, cust_rest = {}, [], []
    def did(d):
        if d not in doc_ix:
            doc_ix[d] = len(doc_ix)
        return doc_ix[d]
    for p, day, d in run(env, f"""
            SELECT TRIM(pincode), dealclosed_date, TRIM(docid) FROM {TABLE}
            WHERE (dealclosed_date BETWEEN %s AND %s OR dealclosed_date BETWEEN %s AND %s)
              AND dc_genio > 0 AND fresh IN (0,1) AND pincode IS NOT NULL AND pincode <> ''
              AND docid IS NOT NULL AND TRIM(docid) <> ''
            GROUP BY 1, 2, 3""", (fy, end, ly_from, ly_to)):
        pin = valid_pin(p)
        if pin:
            cust.append((pin, day, did(d)))
    if ly_to < ly_fy_end:
        # by day (the page counts them by month), so each customer-day can be matched to its deal's size
        for p, day, d in run(env, f"""
                SELECT TRIM(pincode), dealclosed_date, TRIM(docid) FROM {TABLE}
                WHERE dealclosed_date BETWEEN %s AND %s
                  AND dc_genio > 0 AND fresh IN (0,1) AND pincode IS NOT NULL AND pincode <> ''
                  AND docid IS NOT NULL AND TRIM(docid) <> ''
                GROUP BY 1, 2, 3""", (ly_to + datetime.timedelta(days=1), ly_fy_end)):
            pin = valid_pin(p)
            if pin:
                cust_rest.append((pin, day, did(d)))
    log(f"Customers: {len(cust):,} pincode-day-customer rows, {len(cust_rest):,} for last year's other months, "
        f"{len(doc_ix):,} customer ids ({time.time() - t0:.0f}s)")

    # big deals, one by one, so the page can leave out deals above any amount picked (from BIG_FLOOR up). A deal is one
    # customer (docid, else parentid) on one day; its size is the RV 3yr of all its rows. Every row of such a deal
    # comes with the deal's size; the build takes these rows out of the day groups above and ships them separately.
    t0 = time.time()
    big = []
    for p, day, flag, fresh, ecs, n, rv, amt, d in run(env, f"""
            SELECT TRIM(t.pincode), t.dealclosed_date, t.jda_flag, t.fresh, IFNULL(t.ecs_flag_original, 0), t.dc_genio, t.RV_3yr, b.amt, TRIM(t.docid)
            FROM {TABLE} t JOIN (
                SELECT COALESCE(NULLIF(TRIM(docid), ''), parentid) id, dealclosed_date dt, SUM(RV_3yr) amt FROM {TABLE}
                WHERE dealclosed_date BETWEEN %s AND %s AND dc_genio > 0 AND fresh IN (0,1)
                GROUP BY 1, 2 HAVING SUM(RV_3yr) >= %s) b
              ON COALESCE(NULLIF(TRIM(t.docid), ''), t.parentid) = b.id AND t.dealclosed_date = b.dt
            WHERE t.dealclosed_date BETWEEN %s AND %s AND t.dc_genio > 0 AND t.fresh IN (0,1)
              AND t.pincode IS NOT NULL AND t.pincode <> ''""", (ly_from, end, BIG_FLOOR, ly_from, end)):
        pin = valid_pin(p)
        if pin:
            big.append((pin, day, int(flag or 0), int(fresh), 1 if int(ecs or 0) == 1 else 0, float(n or 0), float(rv or 0),
                        float(amt or 0), did(d) if d else -1))
    log(f"Deals of RV 3yr {BIG_FLOOR:,} or more: {len(big):,} rows ({time.time() - t0:.0f}s)")

    # all-India totals straight from the table, for the build's self-check
    tot = {}
    for key, a, b in (("ty", fy, end), ("ly", ly_from, ly_to)):
        n, rv, blank = run(env, f"""SELECT SUM(dc_genio), SUM(RV_3yr), SUM(IF(pincode IS NULL OR TRIM(pincode) = '', dc_genio, 0)) FROM {TABLE}
                                    WHERE dealclosed_date BETWEEN %s AND %s AND dc_genio > 0 AND fresh IN (0,1)""", (a, b))[0]
        tot[key] = (float(n or 0), float(rv or 0))
        tot[key + "_cust"] = int(run(env, f"""SELECT COUNT(DISTINCT TRIM(docid)) FROM {TABLE}
            WHERE dealclosed_date BETWEEN %s AND %s AND dc_genio > 0 AND fresh IN (0,1)
              AND TRIM(pincode) REGEXP '^[0-9]{{6}}$' AND docid IS NOT NULL AND TRIM(docid) <> ''""", (a, b))[0][0] or 0)
        dropped[0 if key == "ty" else 1] += float(blank or 0)   # deals with no pincode at all: not on the map
    log(f"Check totals: this year {tot['ty'][0]:,.1f} deals, last year {tot['ly'][0]:,.1f} deals; "
        f"without a usable pincode {dropped[0]:,.1f} / {dropped[1]:,.1f}")

    raw = {"end": end, "fy": fy, "ly_from": ly_from, "ly_to": ly_to, "deals": deals, "rest": rest, "big": big, "big_floor": BIG_FLOOR,
           "cust": cust, "cust_rest": cust_rest, "n_cust": len(doc_ix),
           "dropped": dropped, "totals": tot, "pulled": datetime.datetime.now()}
    tmp = os.path.join(CACHE, "raw.pkl.tmp")
    pickle.dump(raw, open(tmp, "wb"))
    os.replace(tmp, os.path.join(CACHE, "raw.pkl"))
    log("Saved cache\\raw.pkl")


if __name__ == "__main__":
    main()
