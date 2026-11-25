"""Jaipur tenure grid: pull the raw inputs (read-only SELECTs). Rolls forward every day (23 Nov 2026, user: "I want the Jaipur
dashboard to fetch data daily"): the data end is yesterday, the financial year follows from it, and last year = the same dates.
Each step is cached in data/<step>.pkl. main.py runs every step with --refresh; the presentation history and the closed months
of the dialer are kept and only the new days / months are pulled.
    python t1_fetch.py [--refresh] [hr join deals zero appts pres dialer]
Steps
  hr      tbl_working_days_final_data (216), last FY start - this month, all branches
  join    joining date, HR master city and name from hr_all_daily_copy_ganesh (216)
  deals   daily_deals_closed_dump (216), dc_genio > 0, all branches, last FY start - data end, with the product (camp_name)
  zero    the dc_genio = 0 rows: no deal, but they carry the 'against bounce' ECS collection the sales dashboard adds
  appts   tbl_final_data_appt (240), sales-dashboard rule, per day: all branches this FY, the home branch also last FY
  pres    presentation feed per person per day from 16 Apr 2026 (JDA/Both, Points or Revenue > 0). Saved day copies are read
          first (data/pres_hist.pkl in the kit; the archive and feed_days folders here); missing days are fetched and saved
  dialer  sounak_db.tbl_dialer_data_<city>_<yyyymm> (120): calls and trunk duration per agent per day; all cities this FY, the
          home branch also the 3 months before; the current and previous month are pulled again, closed months are kept
Works in two places: here (logins from Kolkata\\pipeline) and in the colleague kit (logins in the kit's pipeline folder)."""
import os, sys, gzip, time, datetime, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.exists(os.path.join(HERE, "kitpaths.py"))           # shared kit (as the ME kit): code in pipeline\, data private
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE if KIT else os.path.join(ROOT, "Branch review", "analysis"))
from db import q  # noqa: E402  read-only helper; logins stay in the .env files, never in the code
if KIT: import kitpaths  # noqa: E402
DATA = kitpaths.DATA if KIT else os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)

HOME = "Jaipur"
D = datetime.date
END = D.today() - datetime.timedelta(days=1)                     # data end = yesterday
if "--end" in sys.argv: END = D.fromisoformat(sys.argv[sys.argv.index("--end") + 1])
FY = END.year if END.month >= 4 else END.year - 1
START, LY_START = D(FY, 4, 1), D(FY - 1, 4, 1)
PRES_FROM = D(2026, 4, 16)                                        # per-person presentation copies start 16 Apr 2026
CITIES = ["ahmedabad", "bangalore", "chandigarh", "chennai", "coimbatore", "delhi", "hyderabad", "jaipur", "kolkata", "mumbai", "pune"]
FEED = "http://192.168.1.199:81/cron/presentation/cron/downloadPresentationData.php?date={}"
ARCHIVE = os.path.join(ROOT, "JDA_Strategy_Study", "data", "feed")
FEED_DAYS = os.path.join(DATA, "feed_days") if KIT else os.path.join(ROOT, "Jaipur", "pipeline", "feed_days")
REFRESH = "--refresh" in sys.argv


def log(m):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {m}", flush=True)


def cached(name, fn, always=False):
    p = os.path.join(DATA, name + ".pkl")
    if os.path.exists(p) and not (REFRESH or always):
        log(f"{name}: cached"); return pd.read_pickle(p)
    t = time.time(); df = fn(); df.to_pickle(p); log(f"{name}: {len(df):,} rows in {time.time() - t:.0f}s"); return df


def frame(server, sql, args=None):
    cols, rows = q(server, sql, args); return pd.DataFrame(list(rows), columns=cols)


def months(a, b):
    m = D(a.year, a.month, 1)
    while m <= b:
        yield m
        m = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)


def hr():
    return frame(216, f"""SELECT TRIM(city) city, year_no, month_no, TRIM(empcode) empcode, TRIM(team_type_name) team, TRIM(emptype) emptype,
                                 main_city_flag, active_days
                          FROM db_paidcontracts.tbl_working_days_final_data
                          WHERE year_no * 100 + month_no BETWEEN {LY_START.year * 100 + LY_START.month} AND {END.year * 100 + END.month}""")


def join():
    return frame(216, """SELECT TRIM(empcode) empcode, date_of_joining, TRIM(city) city, TRIM(empname) empname FROM db_paidcontracts.hr_all_daily_copy_ganesh""")


COLS = """dealclosed_date, parentid, version, TRIM(final_datacity) city, main_city_flag, jda_flag, TRIM(final_team_type_name) team,
          TRIM(tme) tme, TRIM(me) me, dc_genio, RV_3yr, collection, ecs_flag_original, TRIM(camp_name) product"""


def deals():
    return frame(216, f"""SELECT {COLS} FROM db_paidcontracts.daily_deals_closed_dump
                          WHERE dealclosed_date >= '{LY_START}' AND dealclosed_date <= '{END}' AND dc_genio > 0""")


def zero():
    return frame(216, f"""SELECT {COLS} FROM db_paidcontracts.daily_deals_closed_dump
                          WHERE dealclosed_date >= '{LY_START}' AND dealclosed_date <= '{END}' AND dc_genio = 0""")


def appts():
    sql = """SELECT TRIM(final_datacity) city, DATE(to_date) day, TRIM(tme) tme, TRIM(me) me,
                    TRIM(IFNULL(tme_team_type_name, '')) tteam, jda_flag, main_city_flag,
                    (final_disposition_name IN ('Dealclosed', 'Follow Up', 'Not Interested')) att, COUNT(*) n
             FROM datagrowth.tbl_final_data_appt
             WHERE to_date >= '{a}' AND to_date < '{b}' AND jda_flag IN (0, 3) {city}
               AND final_disposition_name <> 'Not Counted/Cancelled'
               AND IFNULL(me_team_type_name, '') <> 'Corporate' AND IFNULL(me_section, '') NOT LIKE 'Sales (Training)%%'
             GROUP BY 1, 2, 3, 4, 5, 6, 7, 8"""
    end = END + datetime.timedelta(days=1)
    parts = []
    for m in months(START, END):                      # all branches, month by month (keeps each query short)
        nxt = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        t = time.time(); parts.append(frame(240, sql.format(a=m, b=min(nxt, end), city="")))
        log(f"appts {m:%Y-%m}: {len(parts[-1]):,} rows, {time.time() - t:.0f}s")
    t = time.time(); parts.append(frame(240, sql.format(a=LY_START, b=START, city=f"AND final_datacity = '{HOME}'")))
    log(f"appts {HOME} {LY_START} - {START}: {len(parts[-1]):,} rows, {time.time() - t:.0f}s")
    return pd.concat(parts, ignore_index=True)


def feed_text(day):
    for folder in (ARCHIVE, FEED_DAYS):
        f = os.path.join(folder, day.isoformat() + ".tsv.gz")
        if os.path.exists(f):
            return gzip.open(f, "rt", encoding="utf-8", errors="replace").read()
    text = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(FEED.format(day.isoformat()), timeout=300) as r:
                text = r.read().decode("utf-8", errors="replace")
            break
        except Exception as e:
            log(f"feed {day} attempt {attempt + 1}: {type(e).__name__}"); time.sleep(5 * (attempt + 1))
    if text is None or len(text.strip("\n").split("\n")) < 2:
        log(f"feed {day}: not available, skipped (tried again on the next run)"); return None
    os.makedirs(FEED_DAYS, exist_ok=True)
    tmp = os.path.join(FEED_DAYS, day.isoformat() + ".tsv.gz.tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as g:
        g.write(text)
    os.replace(tmp, os.path.join(FEED_DAYS, day.isoformat() + ".tsv.gz")); log(f"feed {day}: fetched and saved")
    return text


def pres():
    hist_p = os.path.join(DATA, "pres_hist.pkl")       # the kit ships the history up to its build day
    hist = pd.read_pickle(hist_p) if os.path.exists(hist_p) else pd.DataFrame(columns=["code", "day", "pres"])
    day = (max(hist.day) + datetime.timedelta(days=1)) if len(hist) else PRES_FROM
    cnt = {}
    while day <= END:
        text = feed_text(day); hdr = None
        for line in (text or "").split("\n"):
            if not line.strip(): continue
            r = line.rstrip("\r").split("\t")
            if hdr is None:
                hdr = {h.strip(): i for i, h in enumerate(r)}; ie, it, ip, ir = hdr["Employee Id"], hdr["Employee Type"], hdr["Points"], hdr["Revenue"]; continue
            if len(r) <= max(ie, it, ip, ir) or r[it].strip().lower() not in ("jda", "both"): continue
            try: ok = float(r[ip] or 0) > 0 or float(r[ir] or 0) > 0
            except ValueError: ok = False
            if ok:
                k = (r[ie].strip().lstrip("0"), day); cnt[k] = cnt.get(k, 0) + 1
        day += datetime.timedelta(days=1)
    new = pd.DataFrame([(c, d, n) for (c, d), n in cnt.items()], columns=["code", "day", "pres"])
    out = pd.concat([hist, new], ignore_index=True)
    out["pres"] = pd.to_numeric(out.pres, errors="coerce").fillna(0).astype(int)   # 24 Nov 2026: the empty history made it text
    return out


def dialer():
    parts, cur = [], END.year * 100 + END.month
    prev = (END.replace(day=1) - datetime.timedelta(days=1)); prev = prev.year * 100 + prev.month
    home_from = (START - datetime.timedelta(days=80)).replace(day=1)
    jobs = [(c, m.year * 100 + m.month) for c in CITIES for m in months(START, END)]
    jobs += [(HOME.lower(), m.year * 100 + m.month) for m in months(home_from, START - datetime.timedelta(days=1))]
    for city, ym in jobs:
        p = os.path.join(DATA, "dialer2_parts", f"{city}_{ym}.pkl")
        if os.path.exists(p) and ym not in (cur, prev):
            parts.append(pd.read_pickle(p)); continue
        t = time.time()
        where = f"WHERE call_start_date < '{END + datetime.timedelta(days=1)}'" if ym == cur else ""
        try:
            df = frame(120, f"""SELECT TRIM(call_agent_login_id) agent, DATE(call_start_date) day, COUNT(*) calls, SUM(call_trunk_duration) trunk
                                FROM sounak_db.tbl_dialer_data_{city}_{ym} {where} GROUP BY 1, 2""").assign(table_city=city)
        except Exception as e:
            log(f"dialer {city} {ym}: {type(e).__name__} {str(e)[:120]}")
            if os.path.exists(p): parts.append(pd.read_pickle(p))
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True); df.to_pickle(p); parts.append(df)
        log(f"dialer {city} {ym}: {len(df):,} agent-days, {time.time() - t:.0f}s")
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["agent", "day", "calls", "trunk", "table_city"])


def loads():
    """when each source table was last loaded (24 Nov 2026: the page's 'data up to' follows the deals table's load, so a Sunday
    or holiday with no deals still counts as covered; the last day with a deal left the page a day or two behind)"""
    rows = frame(216, """SELECT table_name, update_time FROM information_schema.tables WHERE table_schema = 'db_paidcontracts'
                         AND table_name IN ('daily_deals_closed_dump', 'tbl_working_days_final_data')""")
    try:
        rows = pd.concat([rows, frame(240, """SELECT table_name, update_time FROM information_schema.tables
                                             WHERE table_schema = 'datagrowth' AND table_name = 'tbl_final_data_appt'""")], ignore_index=True)
    except Exception as e:
        log(f"loads: server 240 load time not read ({type(e).__name__})")
    return rows


STEPS = {"hr": hr, "join": join, "deals": deals, "zero": zero, "appts": appts, "pres": pres, "dialer": dialer, "loads": loads}
if __name__ == "__main__":
    log(f"data end {END}, FY from {START}, last year from {LY_START}")
    for s in [a for a in sys.argv[1:] if a in STEPS] or list(STEPS):
        cached(s, STEPS[s], always=s in ("pres", "dialer"))
