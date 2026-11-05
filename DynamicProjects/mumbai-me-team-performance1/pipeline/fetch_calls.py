"""Step 3b of the refresh (30 Oct 2026, the TME funnel in TME mode): the TMEs' dialer calls, per TME and day, into
cache\\calls.pkl.

Source: server 120, sounak_db.tbl_dialer_data_<city>_<yyyymm> (one table a month; read-only). The user's rules (31 Oct 2026):
  calls dialed = rows whose agent (call_agent_login_id = employee code) is a TME: emptype 'TME' in
                 db_paidcontracts.tbl_working_days_final_data (server 216) for the call's month. A month HR has no rows
                 for yet uses the latest month HR has.
  connected    = call_trunk_duration > 0 AND call_end_type_name in CONNECTED below (the list as the user gave it; the
                 dialer's names compare without case, so 'IVR call' = 'IVR Call').
  (Before 31 Oct: calls = every row with an agent, connected = an outcome only got by talking; 6.3% of the calls.)
A Sunday call counts on the Saturday before, as the appointments do. The dialer counts are kept per agent and day for every
agent, so the TME check is made on each run with HR as it is then. Months before last month are pulled once and kept
(cache\\calls2_<yyyymm>.pkl; calls_<yyyymm>.pkl were the old rule); last month and this month are pulled on every run.

    python fetch_calls.py

The logins: server 120 = pipeline\\db_120.env, the file named by ME_CALLS_DB_ENV, or DB_120 in pipeline\\environment.py;
server 216 = pipeline\\db_216.env, ME_DEALS_DB_ENV, or DB_216. Without the 120 login the step says so and stops (the page
is then built without calls); without the 216 login the calls are kept unchecked and the step says so.
"""
import datetime
import os
import pickle
import sys
import time

import pymysql

PIPE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(PIPE, "cache")
CONNECTED = ("Testing", "Client Disconnected Call", "IVR call", "Discard Call", "Company Closed", "Paid Client", "Call To Me",
             "Not Interested", "Call Back", "Follow Up", "Allocate Appointment", "Appointment Allocated to JDA",
             "Other City Data", "Other TME Data", "Inbound Call Data Not Found", "Invalid Data", "Not Contactable",
             "Non Sales Data", "Lead/Call Price High", "Wrong Number", "Freezed Contract", "Error", "Do Not Disturb",
             "Not In Business", "Appointment Refixed")
RULE = "calls dialed: the agent is a TME in HR that month; connected: trunk duration > 0 and one of the user's end types (31 Oct 2026)"


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def load_env(file, var, attr):
    """a server login: pipeline\\<file>, the file named by <var>, or <attr> in pipeline\\environment.py; else None"""
    path = os.path.join(PIPE, file)
    if not os.path.exists(path):
        path = os.environ.get(var, "")
    if path and os.path.exists(path):
        env = {}
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
        return env
    try:
        sys.path.insert(0, PIPE)
        import environment
        d = getattr(environment, attr, None) or {}
        if str(d.get("MYSQL_HOST", "")).strip() and str(d.get("MYSQL_USER", "")).strip():
            return {k: str(v).strip() for k, v in d.items()}
    except ImportError:
        pass
    return None


def connect(env):
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, read_timeout=1800, ssl_disabled=True)


def tme_months(env, fy, city):
    """{(year, month): {employee code: HR city}} of the people with emptype 'TME' in tbl_working_days_final_data"""
    c = connect(env)
    cur = c.cursor()
    cur.execute("""SELECT TRIM(LEADING '0' FROM TRIM(empcode)), year_no, month_no, MAX(city)
                   FROM db_paidcontracts.tbl_working_days_final_data
                   WHERE emptype = 'TME' AND year_no * 100 + month_no >= %s GROUP BY 1, 2, 3""", [fy.year * 100 + fy.month])
    out = {}
    for code, y, m, hc in cur.fetchall():
        if code:
            out.setdefault((int(y), int(m)), {})[str(code)] = str(hc or "")
    c.close()
    return out


def main():
    env = load_env("db_120.env", "ME_CALLS_DB_ENV", "DB_120")
    if not env:
        log("No server 120 login (DB_120 in pipeline\\environment.py, or pipeline\\db_120.env): the page is built without the TMEs' calls.")
        return 3
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    city = str(raw["city"]).strip().lower()
    fy, end = raw["fy"], raw["end"]
    today = datetime.date.today()
    keep_before = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)   # months before last month are kept
    months, y, m = [], fy.year, fy.month
    while (y, m) <= (end.year, end.month):
        months.append(datetime.date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    rows, pulled = [], []
    conn = None
    for mo in months:
        ym = f"{mo.year}{mo.month:02d}"
        cp = os.path.join(CACHE, f"calls2_{ym}.pkl")
        if mo < keep_before and os.path.exists(cp):
            rows += pickle.load(open(cp, "rb"))
            continue
        t0 = time.time()
        if conn is None:
            conn = connect(env)
        cur = conn.cursor()
        try:
            cur.execute(f"""SELECT TRIM(LEADING '0' FROM TRIM(call_agent_login_id)), DATE(call_start_date), COUNT(*),
                                   SUM(call_trunk_duration > 0 AND call_end_type_name IN ({', '.join(['%s'] * len(CONNECTED))}))
                            FROM sounak_db.tbl_dialer_data_{city}_{ym} WHERE call_agent_login_id <> '' GROUP BY 1, 2""", CONNECTED)
        except pymysql.err.ProgrammingError as e:   # the month's table is not there (yet)
            log(f"{ym}: no dialer table ({e.args[0]}); skipped")
            continue
        got = []
        for a, d, n, c in cur.fetchall():
            if not a or not d:
                continue
            if d.weekday() == 6:   # Sunday -> the Saturday before
                d -= datetime.timedelta(days=1)
            got.append((str(a), d, int(n), int(c or 0)))
        pickle.dump(got, open(cp + ".tmp", "wb")); os.replace(cp + ".tmp", cp)
        rows += got
        pulled.append(ym)
        log(f"{ym}: {sum(r[2] for r in got):,} calls with an agent, {sum(r[3] for r in got):,} connected, "
            f"{len({r[0] for r in got}):,} agents ({time.time() - t0:.0f}s)")
    if conn is not None:
        conn.close()
    rows = [r for r in rows if fy <= r[1] <= end]
    # calls dialed = the TMEs' calls: the agent has emptype 'TME' in HR in the call's month (the user, 31 Oct 2026)
    e216 = load_env("db_216.env", "ME_DEALS_DB_ENV", "DB_216")
    checked, stats = False, {}
    if e216:
        hr = tme_months(e216, fy, city)
        latest = max(hr) if hr else None
        for mo in months:
            k = (mo.year, mo.month)
            if k not in hr and latest:
                log(f"HR has no TME rows for {mo:%b %Y} yet: that month's calls use {datetime.date(latest[0], latest[1], 1):%b %Y}'s TMEs")
        allc, allk = sum(r[2] for r in rows), sum(r[3] for r in rows)
        keep, away = [], 0
        for r in rows:
            k = (r[1].year, r[1].month)
            tm = hr.get(k) if k in hr else hr.get(latest, {})
            if r[0] in tm:
                keep.append(r)
                if tm[r[0]].strip().lower() != city:
                    away += r[2]
        stats = {"agent_calls": allc, "agent_conn": allk, "tme_calls": sum(r[2] for r in keep), "tme_conn": sum(r[3] for r in keep),
                 "other_city_calls": away}
        log(f"TME check (HR emptype 'TME'): {stats['tme_calls']:,} of {allc:,} calls with an agent are by TMEs "
            f"({allc - stats['tme_calls']:,} by other agents left out); {away:,} of the TMEs' calls are by TMEs whose HR city that month is not {city.title()}")
        rows, checked = keep, True
    else:
        log("No server 216 login (DB_216): the calls are NOT checked against HR's TMEs this run.")
    out = {"rows": rows, "pulled": datetime.datetime.now(), "to": max((r[1] for r in rows), default=None),
           "connected": list(CONNECTED), "rule": RULE, "tme_checked": checked, "stats": stats}
    pickle.dump(out, open(os.path.join(CACHE, "calls.pkl.tmp"), "wb"))
    os.replace(os.path.join(CACHE, "calls.pkl.tmp"), os.path.join(CACHE, "calls.pkl"))
    log(f"Calls since {fy}: {sum(r[2] for r in rows):,} ({sum(r[3] for r in rows):,} connected) by {len({r[0] for r in rows}):,} "
        f"{'TMEs' if checked else 'agents'}, to {out['to']}; pulled {', '.join(pulled) or 'none'} (the rest from the cache). Saved cache\\calls.pkl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
