"""Step 1 of the refresh: pull ME appointments for the ME team dashboard into cache\\raw.pkl.

Source: server 240, datagrowth.tbl_final_data_appt (read-only). Rows: the city's ME appointments (jda_flag 0, and 3 = B2B, as the Sales MIS counts them) from
1 April of the financial year, both those given to an ME (given_count = 1) and those not counted (given_count = 0:
cancelled, refixed, marked fake...; the review page shows them per ME). The build steps keep given_count = 1 as the
appointments. The timing columns (booked, slot, outcome entered, deal entered) feed the review page's record checks.
"""
import datetime
import os
import pickle
import sys
import time

import pymysql

PIPE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(PIPE, "cache")
CITY = os.environ.get("ME_CITY", "")
if not CITY:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import environment
        CITY = getattr(environment, "CITY", "") or "mumbai"
    except ImportError:
        CITY = "mumbai"
TABLE = "`datagrowth`.`tbl_final_data_appt`"
COLS = ["to_date", "parentid", "companyname", "tme", "tmename", "me", "mename", "me_manager", "me_manager_code",
        "tme_team_type_name", "tme_manager", "final_disposition_name", "disposition_name", "attended_count",
        "dealclosed_count", "dc_genio", "ecs_flag", "me_section", "me_grade",
        "given_count", "tme_section", "allocationtime", "actiontime", "allocationType", "entry_date", "given_date",
        "attended_date", "dealclosed_date", "data_city", "sub_disposition_value", "me_team_type_name", "jda_flag"]


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
    """The server 240 login: pipeline\\db_240.env, the file named by ME_DB_ENV, or DB_240 in pipeline\\environment.py."""
    path = os.path.join(PIPE, "db_240.env")
    if not os.path.exists(path):
        path = os.environ.get("ME_DB_ENV", "")
    if not path or not os.path.exists(path):
        s = env_from_settings("DB_240")
        if s:
            return s
        sys.exit("Missing the server 240 login: fill DB_240 in pipeline\\environment.py (or create pipeline\\db_240.env from its template). See SETUP.md.")
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main():
    env = load_env()
    os.makedirs(CACHE, exist_ok=True)
    today = datetime.date.today()
    fy = datetime.date(today.year if today.month >= 4 else today.year - 1, 4, 1)
    t0 = time.time()
    for attempt in range(3):
        try:
            c = pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                                password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=1800)
            cur = c.cursor()
            cur.execute(f"""SELECT {', '.join(COLS)} FROM {TABLE}
                            WHERE final_datacity = %s AND to_date >= %s AND jda_flag IN (0, 3)""", (CITY, fy))
            rows = cur.fetchall()
            c.close()
            break
        except pymysql.err.OperationalError as e:
            log(f"Attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                raise
            time.sleep(15)
    end = max(r[0] for r in rows) if rows else None
    given = sum(1 for r in rows if r[COLS.index("final_disposition_name")] != "Not Counted/Cancelled")
    log(f"{CITY}: {given:,} appointments given and {len(rows) - given:,} not counted, {fy} to {end} ({time.time() - t0:.0f}s)")
    raw = {"city": CITY, "fy": fy, "end": end, "cols": COLS, "rows": rows, "pulled": datetime.datetime.now()}
    tmp = os.path.join(CACHE, "raw.pkl.tmp")
    pickle.dump(raw, open(tmp, "wb"))
    os.replace(tmp, os.path.join(CACHE, "raw.pkl"))
    log("Saved cache\\raw.pkl")


if __name__ == "__main__":
    main()
