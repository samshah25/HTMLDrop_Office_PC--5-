"""Step 1b of the refresh: the deals for the appointments in cache\\raw.pkl, from the deals table, into cache\\deals.pkl,
and the MEs' HR context (days present per month, joining date, designation) into cache\\hr.pkl.

Source: server 216, db_paidcontracts.daily_deals_closed_dump (read-only). Rows with dc_genio > 0 for the businesses
that had an appointment (by parentid, and by docid = city code + parentid), from two days before the first
appointment. Both columns are indexed, so this takes seconds; the page decides which appointment each deal converts.
Days after the dump's last day come from db_paidcontracts.tbl_30_day_rolling_dealdump_data (same rows, rebuilt earlier
each morning, matched by parentid), so the morning refresh is up to date even before the dump is.
Deals closed as the Sales MIS counts them (JDS-ME: every deal row of an ME of this city that month, with or without an
appointment, MIS_SQL) also go into cache\\deals.pkl ('mis'): they are the page's 'Deals closed' since 15 Oct 2026.
HR (same server, read-only): db_paidcontracts.tbl_working_days_final_data (monthly present / active days per empcode)
and db_paidcontracts.hr_all_daily_copy_ganesh (joining date, designation, home city), for every ME in raw.pkl.

    python fetch_deals.py
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
ROLLING = "`db_paidcontracts`.`tbl_30_day_rolling_dealdump_data`"   # refreshed earlier each morning; used for days after TABLE's last
CITY_CODE = {"mumbai": "022", "delhi": "011", "kolkata": "033", "chennai": "044", "bangalore": "080", "hyderabad": "040",
             "pune": "020", "ahmedabad": "079"}


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def env_from_settings(name):
    """a login filled in pipeline\\environment.py (DB_240 / DB_216), or None"""
    try:
        sys.path.insert(0, PIPE)
        import environment
    except ImportError:
        return None
    d = getattr(environment, name, None) or {}
    if str(d.get("MYSQL_HOST", "")).strip() and str(d.get("MYSQL_USER", "")).strip():
        return {k: str(v).strip() for k, v in d.items()}
    return None


def load_env():
    """The server 216 login: pipeline\\db_216.env, the file named by ME_DEALS_DB_ENV, or DB_216 in pipeline\\environment.py."""
    path = os.path.join(PIPE, "db_216.env")
    if not os.path.exists(path):
        path = os.environ.get("ME_DEALS_DB_ENV", "")
    if not path or not os.path.exists(path):
        s = env_from_settings("DB_216")
        if s:
            return s
        sys.exit("Missing the server 216 login: fill DB_216 in pipeline\\environment.py (or create pipeline\\db_216.env from its template). See SETUP.md.")
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    ix = raw["cols"].index("parentid")
    pids = {str(r[ix]).strip() for r in raw["rows"] if r[ix]}
    ap = os.path.join(CACHE, "api_rows.pkl")          # businesses on the provisional days (fetch_api.py)
    if os.path.exists(ap):
        api = pickle.load(open(ap, "rb"))
        pids |= {str(r[api["cols"].index("parentid")]).strip() for r in api["rows"] if r[api["cols"].index("parentid")]}
    pids = sorted(pids)
    code = CITY_CODE.get(str(raw["city"]).lower(), "")
    start = raw["fy"] - datetime.timedelta(days=2)
    env = load_env()
    t0 = time.time()
    c = pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                        password=env["MYSQL_PASSWORD"], connect_timeout=15, read_timeout=600)
    cur = c.cursor()
    rows, seen = [], set()
    for i in range(0, len(pids), 1000):
        ch = pids[i:i + 1000]
        ph = ",".join(["%s"] * len(ch))
        docs = [code + p for p in ch] if code else ch
        cur.execute(f"""SELECT dealclosed_date, parentid, TRIM(docid), dc_genio, me, jda_flag, final_datacity, version
                        FROM {TABLE} WHERE (parentid IN ({ph}) OR TRIM(docid) IN ({ph})) AND dealclosed_date >= %s AND dc_genio > 0""",
                    ch + docs + [start])
        for r in cur.fetchall():
            key = (r[0], r[1], r[2], r[7], str(r[4]))
            if key not in seen:
                seen.add(key)
                rows.append(r)
    # The newest days (2026-10-12): db_paidcontracts.tbl_30_day_rolling_dealdump_data is rebuilt every morning before
    # the deals dump, with the same columns (no docid) and the same rows (checked row by row for Mumbai, 12 Sept -
    # 10 Oct). Its deals are added only for the days after the dump's last day, so nothing is counted twice. While it is
    # being rebuilt the query can fail or come back empty; then the dump alone is used.
    dump_to = None
    cur.execute(f"SELECT MAX(dealclosed_date) FROM {TABLE}")
    dump_to = cur.fetchone()[0]
    recent = {"to": None, "rows": 0}
    if dump_to:
        try:
            for i in range(0, len(pids), 1000):
                ch = pids[i:i + 1000]
                ph = ",".join(["%s"] * len(ch))
                cur.execute(f"""SELECT dealclosed_date, parentid, '' AS docid, dc_genio, me, jda_flag, final_datacity, version
                                FROM {ROLLING} WHERE parentid IN ({ph}) AND dealclosed_date > %s AND dc_genio > 0""", ch + [dump_to])
                for r in cur.fetchall():
                    key = (r[0], r[1], r[2], r[7], str(r[4]))
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)
                        recent["rows"] += 1
                        recent["to"] = max(recent["to"] or r[0], r[0])
        except pymysql.MySQLError as e:
            log(f"The 30-day rolling deals table could not be read ({e}); using the deals dump only.")
    mis, mis_to, names = fetch_mis_deals(cur, raw, dump_to)
    c.close()
    deals = []
    for day, pid, doc, n, me, jf, city, _v in rows:
        p = (pid or "").strip() or (doc[len(code):] if code and doc and doc.startswith(code) else doc)
        deals.append((day if isinstance(day, datetime.date) else day.date(), p, float(n or 0), str(me or ""), int(jf or 0)))
    out = {"deals": deals, "from": start, "pulled": datetime.datetime.now(), "businesses": len(pids),
           "dump_to": dump_to, "recent_to": recent["to"], "recent_rows": recent["rows"],
           "mis": mis, "mis_to": mis_to, "names": names}
    log(f"Deals dump runs to {dump_to}; the rolling table added {recent['rows']:,} deal rows"
        + (f" for {dump_to + datetime.timedelta(days=1)} to {recent['to']}" if recent["to"] else " (nothing newer)"))
    tmp = os.path.join(CACHE, "deals.pkl.tmp")
    pickle.dump(out, open(tmp, "wb"))
    os.replace(tmp, os.path.join(CACHE, "deals.pkl"))
    log(f"Deals for {len(pids):,} businesses: {len(deals):,} deal rows since {start} ({time.time() - t0:.0f}s). Saved cache\\deals.pkl")
    fetch_hr(raw, env, {m[3] for m in mis})


# The Sales MIS 'Deals Closed' (JDS-ME) rule, matched to the unit on 13 Oct 2026 (checks\mis_deals_closed_jds_me.sql):
# every deal row (one per payment version, dc_genio) with jda_flag 0 or 3 and an ME, in ANY final_datacity, whose ME was
# an ME of this city in the deal's month (tbl_working_days_final_data: city, emptype ME, team not Corporate / JDA; no row
# for that month -> the HR master's city). Deals with no appointment behind them (no TME: the MIS's 'Cold Call') count too.
MIS_SQL = """SELECT d.dealclosed_date, TRIM(d.parentid), d.dc_genio, TRIM(LEADING '0' FROM TRIM(d.me)), TRIM(IFNULL(d.tme, '')),
                    TRIM(IFNULL(d.final_team_type_name, '')), d.jda_flag
             FROM {table} d
             LEFT JOIN (SELECT TRIM(LEADING '0' FROM TRIM(empcode)) AS emp, year_no, month_no,
                               MAX(city) AS city, MAX(emptype) AS emptype, MAX(team_type_name) AS team
                        FROM db_paidcontracts.tbl_working_days_final_data
                        WHERE year_no * 100 + month_no >= %s GROUP BY 1, 2, 3) w
                    ON w.emp = TRIM(LEADING '0' FROM TRIM(d.me))
                   AND w.year_no = YEAR(d.dealclosed_date) AND w.month_no = MONTH(d.dealclosed_date)
             LEFT JOIN (SELECT TRIM(LEADING '0' FROM TRIM(empcode)) AS emp, MAX(city) AS city
                        FROM db_paidcontracts.hr_all_daily_copy_ganesh GROUP BY 1) h
                    ON h.emp = TRIM(LEADING '0' FROM TRIM(d.me))
             WHERE d.dealclosed_date {when}
               AND d.jda_flag IN (0, 3)
               AND TRIM(IFNULL(d.me, '')) <> ''
               AND (   (w.emp IS NOT NULL AND w.city = %s AND w.emptype = 'ME' AND w.team NOT IN ('Corporate', 'JDA'))
                    OR (w.emp IS NULL AND h.city = %s))"""


def fetch_mis_deals(cur, raw, dump_to):
    """Deals closed as the Sales MIS counts them, since the start of the year; days after the dump's last day from the
    30-day rolling table (same rows). Returns [(day, parentid, dc_genio, me, tme, team, jda_flag)], the last day, and
    the HR names of those MEs."""
    t0 = time.time()
    city, ym = str(raw["city"]).strip().title(), raw["fy"].year * 100 + raw["fy"].month
    out = []
    cur.execute(MIS_SQL.format(table=TABLE, when="BETWEEN %s AND %s"), (ym, raw["fy"], dump_to or raw["end"], city, city))
    out += cur.fetchall()
    if dump_to:
        try:
            cur.execute(MIS_SQL.format(table=ROLLING, when="> %s"), (ym, dump_to, city, city))
            out += cur.fetchall()
        except pymysql.MySQLError as e:
            log(f"The 30-day rolling deals table could not be read for the MIS deals ({e}); deals dump only.")
    mis = [(d if isinstance(d, datetime.date) and not isinstance(d, datetime.datetime) else d.date(), pid or "", float(dc or 0), me, tme, team, int(jf or 0))
           for d, pid, dc, me, tme, team, jf in out]
    mis_to = max((m[0] for m in mis), default=None)
    names = {}
    codes = sorted({m[3] for m in mis})
    for i in range(0, len(codes), 1000):
        ch = codes[i:i + 1000]
        cur.execute(f"""SELECT TRIM(LEADING '0' FROM TRIM(empcode)), empname FROM db_paidcontracts.hr_all_daily_copy_ganesh
                        WHERE TRIM(LEADING '0' FROM TRIM(empcode)) IN ({','.join(['%s'] * len(ch))})""", ch)
        names.update({c: " ".join(str(n or "").split()) for c, n in cur.fetchall()})
    log(f"Deals closed, Sales MIS rule (JDS-ME, {city} MEs): {sum(m[2] for m in mis):,.2f} since {raw['fy']} to {mis_to}, "
        f"{len(mis):,} deal rows, {len(codes):,} MEs ({time.time() - t0:.0f}s)")
    return mis, mis_to, names


def fetch_hr(raw, env, more=()):
    """Days present per month (to compare appointment volume fairly) and joining date / designation / home city, for the
    MEs in raw.pkl and the MEs with deals closed (more: codes without leading zeros)."""
    t0 = time.time()
    ix = raw["cols"].index("me")
    codes = {str(r[ix]).strip() for r in raw["rows"] if r[ix]}
    have = {c.lstrip("0") for c in codes}
    codes = sorted(codes | {c for c in more if c and c not in have})
    months = []
    y, m = raw["fy"].year, raw["fy"].month
    while (y, m) <= (raw["end"].year, raw["end"].month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    c = pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                        password=env["MYSQL_PASSWORD"], connect_timeout=15, read_timeout=600)
    cur = c.cursor()
    days, master = {}, {}
    for i in range(0, len(codes), 1000):
        ch = codes[i:i + 1000]
        ph = ",".join(["%s"] * len(ch))
        for yy, mm in months:
            cur.execute(f"""SELECT TRIM(empcode), present_days, active_days, emptype, city FROM db_paidcontracts.tbl_working_days_final_data
                            WHERE year_no = %s AND month_no = %s AND TRIM(empcode) IN ({ph})""", [yy, mm] + ch)
            for code, pres, act, et, city in cur.fetchall():
                prev = days.get((code, yy, mm))
                if prev is None or float(pres or 0) > prev[0]:      # one row per person and month; keep the fuller one
                    days[(code, yy, mm)] = (float(pres or 0), float(act or 0), str(et or ""), str(city or ""))
        cur.execute(f"""SELECT TRIM(empcode), date_of_joining, date_of_leaving, emp_status, designation, city
                        FROM db_paidcontracts.hr_all_daily_copy_ganesh WHERE TRIM(empcode) IN ({ph})""", ch)
        for code, doj, dol, st, des, city in cur.fetchall():
            day = lambda v: v.date() if isinstance(v, datetime.datetime) else v if isinstance(v, datetime.date) else None
            master[code] = (day(doj), day(dol), int(st or 0), " ".join(str(des or "").split()), " ".join(str(city or "").split()))
    c.close()
    out = {"days": days, "master": master, "months": months, "pulled": datetime.datetime.now()}
    tmp = os.path.join(CACHE, "hr.pkl.tmp")
    pickle.dump(out, open(tmp, "wb"))
    os.replace(tmp, os.path.join(CACHE, "hr.pkl"))
    log(f"HR for {len(codes):,} MEs: {len({k[0] for k in days}):,} with days present, {len(master):,} with joining dates "
        f"({time.time() - t0:.0f}s). Saved cache\\hr.pkl")


if __name__ == "__main__":
    sys.exit(main())
