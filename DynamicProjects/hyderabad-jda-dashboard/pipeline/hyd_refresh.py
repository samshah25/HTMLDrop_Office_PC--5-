r"""
Pull the data for the Hyderabad JDA dashboard into pipeline\hyd_data.json. main.py runs this, then puts the data
into the page; you never run it yourself.

Sources:
- Presentations: the presentation feed (internal, no login), one day at a time. Every day read is saved in
  pipeline\pres_store\ (Hyderabad-branch pincodes only); only the last 14 days are fetched again. The feed keeps about
  6 months, so older days exist only in that folder: NEVER DELETE IT.
- Sales (optional): db_paidcontracts.daily_deals_closed_dump, through pipeline\db_216.env. Without that file the page
  shows presentations only and says so.
- HR (optional, same login): db_paidcontracts.hr_all_daily_copy_ganesh, updated daily. It decides who is an ACTIVE
  JDA on each day: team_type JDA with a customer-facing section, an HR city in the Hyderabad branch, joined on or
  before that day and not left before it (date_of_leaving; emp_status 0 = left). It also gives joining date (tenure). Without the login, active = presented in the last 15 days.

Counting rules (same as the Mumbai dashboard):
- a presentation counts when Employee Type is JDA or Both and Points or Revenue is above 0;
- sales = SUM(dc_genio) with fresh IN (0,1); jda_flag 1 counts in full to the JDA, 2 (JDA + JDS joint) counts half.

Geography (from pincode_city_data_city_branch.xlsx, Branch == "Hyderabad"):
- state: pincodes starting 50 are Telangana, 51-53 Andhra Pradesh, anything else "Other";
- Telangana district: the reference file's Data City, rolled up to the 8 old districts (TS_DISTRICT below);
  Hyderabad (with Tandur, old Rangareddy) is the main city, everything else is remote;
- Andhra Pradesh: the Data City as it is.
"""
import datetime
import json
import re
import os
import sys
from collections import Counter, defaultdict

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPE_DIR)
import pres_store  # noqa: E402

BRANCH = "Hyderabad"
WINDOW_START = "2026-04-21"   # the first day the feed still had when this kit was made (23 Oct 2026)
WINDOW_END = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
REF_PATH = os.path.join(PIPE_DIR, "pincode_city_data_city_branch.xlsx")
ENV_PATH = os.path.join(PIPE_DIR, "db_216.env")
# On a web host that serves this folder (HTML Drop), the login must not stay here: when pipeline\keep_login_private
# exists, the first run moves db_216.env to a private folder in the user's home and reads it from there afterwards.
PRIVATE_ENV = os.path.join(os.path.expanduser("~"), ".hyd_jda_dashboard", "db_216.env")


def find_env():
    if os.path.exists(os.path.join(PIPE_DIR, "keep_login_private")):
        if os.path.exists(ENV_PATH):
            os.makedirs(os.path.dirname(PRIVATE_ENV), exist_ok=True)
            os.replace(ENV_PATH, PRIVATE_ENV)
            log("Moved db_216.env out of the served folder into the private folder.")
        return PRIVATE_ENV if os.path.exists(PRIVATE_ENV) else None
    return ENV_PATH if os.path.exists(ENV_PATH) else None
OUT_PATH = os.path.join(PIPE_DIR, "hyd_data.json")
LOG_PATH = os.path.join(PIPE_DIR, "refresh_log.txt")
DEALS = "`db_paidcontracts`.`daily_deals_closed_dump`"
HR = "`db_paidcontracts`.`hr_all_daily_copy_ganesh`"
# who HR counts as a field JDA: team_type JDA and a customer-facing section (JDA Sales Managers and Retention are not;
# they still count on a day they present)
JDA_SECTION = "facing"   # "JDA Customer Facing", "JDA Team Leader + Cust. Facing"
LEFT_STATUS = {"0"}   # emp_status: 1 = working, 0 = left (a 0 with no date_of_leaving is treated as gone for the whole window)

MAIN_CITY = "Hyderabad"
TS_DISTRICT = {   # Telangana Data City -> one of Hyderabad + the 8 remote districts
    "Hyderabad": "Hyderabad", "Tandur": "Hyderabad",
    "Warangal": "Warangal", "Jangaon": "Warangal", "Mahbubabad": "Warangal", "Narsampet": "Warangal",
    "Karimnagar": "Karimnagar", "Peddapalli": "Karimnagar", "Jagtial": "Karimnagar", "Sircilla": "Karimnagar",
    "Koratla": "Karimnagar",
    "Khammam": "Khammam", "Palvancha": "Khammam", "Aswaraopet": "Khammam", "Bhadrachalam": "Khammam",
    "Manuguru": "Khammam", "Kothagudem": "Khammam",
    "Nizamabad": "Nizamabad", "Kamareddy": "Nizamabad", "Armoor": "Nizamabad",
    "Nalgonda": "Nalgonda", "Suryapet": "Nalgonda", "Huzurnagar": "Nalgonda",
    "Medak": "Medak", "Sangareddy": "Medak", "Siddipet": "Medak", "Zahirabad": "Medak",
    "Mahabubnagar": "Mahabubnagar", "Gadwal": "Mahabubnagar", "Alampur": "Mahabubnagar", "Atmakur": "Mahabubnagar",
    "Adilabad": "Adilabad", "Mancherial": "Adilabad", "Nirmal": "Adilabad", "Asifabad": "Adilabad",
}
TS_ORDER = ["Hyderabad", "Warangal", "Karimnagar", "Khammam", "Nizamabad", "Nalgonda", "Medak", "Mahabubnagar", "Adilabad"]


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env(path):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_geo():
    """{pincode: area index}, the area list [{name, state, main}] and {lower-case city name: area index}."""
    import openpyxl
    rows = openpyxl.load_workbook(REF_PATH, read_only=True, data_only=True)["Sheet1"].iter_rows(values_only=True)
    h = next(rows)
    ip, idc, ib = h.index("Pincode"), h.index("Data City"), h.index("Branch")
    ic = h.index("City") if "City" in h else None
    pin_area, unmapped, city_votes = {}, Counter(), defaultdict(Counter)
    for r in rows:
        if str(r[ib] or "").strip() != BRANCH or r[ip] is None:
            continue
        pin = str(r[ip]).strip().split(".")[0]
        if len(pin) != 6 or not pin.isdigit():
            continue
        dc = " ".join(str(r[idc] or "").split()).title()
        if pin.startswith("50"):
            name = TS_DISTRICT.get(dc)
            if name is None:
                unmapped[dc] += 1
                name = dc or "Telangana - other"
            area = (name, "TS")
        elif pin[:2] in ("51", "52", "53"):
            area = (dc + " (AP mandals)" if dc in TS_DISTRICT else dc or "Andhra - other", "AP")
        else:
            area = (dc or "Other", "OT")
        pin_area[pin] = area
        for nm in {dc, " ".join(str(r[ic] or "").split()).title() if ic is not None else ""} - {""}:
            city_votes[nm.lower()][area] += 1
    if unmapped:
        log(f"Note: Telangana data cities not in TS_DISTRICT (kept under their own name): {dict(unmapped)}")
    names = sorted(set(pin_area.values()), key=lambda a: ({"TS": 0, "AP": 1, "OT": 2}[a[1]],
                                                           TS_ORDER.index(a[0]) if a[0] in TS_ORDER else 99, a[0]))
    idx = {a: i for i, a in enumerate(names)}
    areas = [{"name": n, "state": s, "main": int(s == "TS" and n == MAIN_CITY)} for n, s in names]
    city_area = {c: idx[v.most_common(1)[0][0]] for c, v in city_votes.items()}
    city_area.setdefault("secunderabad", idx[(MAIN_CITY, "TS")])
    return {p: idx[a] for p, a in pin_area.items()}, areas, city_area


def minutes(ts):
    """'2026-10-13 23:46:47' -> 1426 (minutes after midnight), or None."""
    try:
        hh, mm = ts.strip()[11:16].split(":")
        return int(hh) * 60 + int(mm)
    except (ValueError, IndexError):
        return None


def read_presentations(pin_area):
    store = pres_store.PresStore(os.path.join(PIPE_DIR, "pres_store"), lambda p: p in pin_area, log)
    start, end = datetime.date.fromisoformat(WINDOW_START), datetime.date.fromisoformat(WINDOW_END)
    days, recs = [], defaultdict(lambda: {"times": [], "areas": Counter(), "new": 0, "paid": 0, "mgr": Counter()})
    names, mgr_names = {}, {}
    d = start
    while d <= end:
        text = store.day_text(d, end)
        ds = d.isoformat()
        d += datetime.timedelta(days=1)
        if not text or not text.strip():
            continue
        lines = text.strip("\n").split("\n")
        header = lines[0].rstrip("\r").split("\t")
        ix = {k: i for i, k in enumerate(header)}
        if "Pincode" not in ix or "Employee Id" not in ix:
            continue
        n_day = 0
        for line in lines[1:]:
            parts = line.rstrip("\r").split("\t")
            if len(parts) != len(header):
                continue
            col = lambda k: parts[ix[k]].strip() if k in ix else ""
            if col("Employee Type") not in ("JDA", "Both"):
                continue
            pin = col("Pincode")
            if pin not in pin_area or not (to_float(col("Points")) > 0 or to_float(col("Revenue")) > 0):
                continue
            emp = col("Employee Id")
            if not emp:
                continue
            r = recs[(ds, emp)]
            t = minutes(col("Appointment Date"))
            if t is not None:
                r["times"].append(t)
            r["areas"][pin_area[pin]] += 1
            ctype = col("Contract Type")
            r["new"] += ctype.startswith("New")
            r["paid"] += "- Paid" in ctype or "Upgraded" in ctype
            names[emp] = " ".join(col("Employee Name").split()).title()
            mcode = col("Reporting Manager Code")
            if mcode:
                r["mgr"][mcode] += 1
                mgr_names[mcode] = " ".join(col("Reporting Manager Name").split()).title()
            n_day += 1
        if n_day:
            days.append(ds)
    log(f"Presentations: {len(days)} days with Hyderabad JDA presentations, {len(recs)} rep-days, {len(names)} reps "
        f"({store.summary()})")
    return days, recs, names, mgr_names


def db_connect(env):
    import pymysql
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, ssl_disabled=True, read_timeout=300)


def month_chunks(a, b):
    s, e = datetime.date.fromisoformat(a), datetime.date.fromisoformat(b)
    while s <= e:
        nxt = (s.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        yield s.isoformat(), min(e, nxt - datetime.timedelta(days=1)).isoformat()
        s = nxt


def read_sales(env, reps, pin_area):
    """({(day, emp): JDA sales}, {(day, area): JDA sales in the branch}). Rep sales count wherever the deal was;
    area sales count deals in the branch's pincodes, whoever made them."""
    rep_sales, area_sales = defaultdict(float), defaultdict(float)
    codes = sorted(reps)
    for a, b in month_chunks(WINDOW_START, WINDOW_END):
        conn = db_connect(env)
        with conn.cursor() as cur:
            ph = ",".join(["%s"] * len(codes))
            cur.execute(f"""SELECT dealclosed_date, pincode, dc_genio, jda_flag, TRIM(me)
                            FROM {DEALS}
                            WHERE dealclosed_date BETWEEN %s AND %s AND dc_genio > 0 AND fresh IN (0,1)
                              AND jda_flag IN (1,2)
                              AND (pincode BETWEEN '500000' AND '535999' OR TRIM(me) IN ({ph}))""", [a, b] + codes)
            rows = cur.fetchall()
        conn.close()
        for day, pin, g, flag, me in rows:
            ds = day.isoformat() if hasattr(day, "isoformat") else str(day)[:10]
            amt = float(g or 0) * (1 if flag == 1 else 0.5)
            if me in reps:
                rep_sales[(ds, me)] += amt
            pin = str(pin or "").strip()
            if pin in pin_area:
                area_sales[(ds, pin_area[pin])] += amt
        log(f"Sales {a}..{b}: {len(rows)} JDA deal rows")
    return rep_sales, area_sales


def read_hr(env, reps, city_area):
    """Every branch field JDA in HR (who is active on which day), plus HR details for anyone who presented.
    Returns {empcode: {...}}; "jda": 1 marks the people on the HR JDA list."""
    day = lambda v: v.strftime("%Y-%m-%d") if hasattr(v, "strftime") and v.year > 1900 else ""
    tidy = lambda v: " ".join(str(v or "").split())
    conn = db_connect(env)
    with conn.cursor() as cur:
        cur.execute(f"""SELECT TRIM(empcode), empname, designation, section, team_type, city, work_location,
                               date_of_joining, date_of_leaving, emp_status FROM {HR}
                        WHERE team_type = 'JDA' OR TRIM(empcode) IN ({','.join(['%s'] * len(reps))})""", sorted(reps))
        rows = cur.fetchall()
    conn.close()
    out, sections, status = {}, Counter(), Counter()
    for code, name, des, sec, team, city, wl, doj, dol, st in rows:
        city, wl, sec = tidy(city), tidy(wl), tidy(sec)
        area = city_area.get(wl.lower(), city_area.get(city.lower()))
        if area is not None and tidy(team) == "JDA":
            sections[sec] += 1
        is_jda = area is not None and tidy(team) == "JDA" and JDA_SECTION in sec.lower()
        if not (is_jda or code in reps):
            continue
        left = day(dol) if dol and not isinstance(dol, str) else ""
        if not left and str(st) in LEFT_STATUS:
            left = "1900-01-01"
        if is_jda:
            status["working" if st == 1 else "left"] += 1
        out[code] = {"desig": tidy(des), "section": sec, "joined": day(doj) if doj and not isinstance(doj, str) else "",
                     "left": left, "status": st, "city": (wl or city).title(), "hname": tidy(name).title(),
                     "jda": int(is_jda), "harea": area}
    log(f"HR: {sum(v['jda'] for v in out.values())} branch field JDAs on the HR list ({dict(status)}); "
        f"HR details for {sum(c in out for c in reps)} of {len(reps)} people who presented")
    log(f"HR sections of team_type JDA in branch cities (only sections with '{JDA_SECTION}' count): {dict(sections.most_common())}")
    return out


def main():
    log(f"=== Hyderabad dashboard refresh: {WINDOW_START} to {WINDOW_END} ===")
    pin_area, areas, city_area = load_geo()
    log(f"{len(pin_area)} Hyderabad-branch pincodes in {len(areas)} areas")
    days, recs, names, mgr_names = read_presentations(pin_area)
    if not days:
        sys.exit("No presentation days read: is this PC on the office network or VPN?")

    env_file = find_env()
    env = load_env(env_file) if env_file else None
    rep_sales, area_sales, hr, notes = {}, {}, {}, []
    if env:
        try:
            rep_sales, area_sales = read_sales(env, set(names), pin_area)
        except Exception as e:
            notes.append("Sales could not be read this time.")
            log(f"WARNING: sales not read ({type(e).__name__}: {e})")
        try:
            hr = read_hr(env, set(names), city_area)
        except Exception as e:
            notes.append("HR details could not be read this time.")
            log(f"WARNING: HR details not read ({type(e).__name__}: {e})")
    else:
        log("No pipeline\\db_216.env: presentations only (no sales, no HR tenure).")

    # JDAs on the HR list who never presented in the window are still active (they count as absent)
    for e, v in hr.items():
        if v["jda"] and e not in names and not (v["left"] and v["left"] < days[0]):   # skip people gone before the window
            names[e] = v["hname"] or e
    day_ix = {d: i for i, d in enumerate(days)}
    reps = sorted(names, key=lambda e: names[e])
    rep_ix = {e: i for i, e in enumerate(reps)}
    mgrs = sorted(mgr_names, key=lambda m: mgr_names[m])
    mgr_ix = {m: i for i, m in enumerate(mgrs)}
    first_seen = {}
    rd = []   # [day, rep, manager or -1, [[area, presentations], ...], [minutes, ...], new-contract count, paid count]
    for (ds, emp), r in sorted(recs.items()):
        if ds not in day_ix:
            continue
        first_seen.setdefault(emp, ds)
        m = r["mgr"].most_common(1)[0][0] if r["mgr"] else None
        rd.append([day_ix[ds], rep_ix[emp], mgr_ix[m] if m else -1, [[a, n] for a, n in r["areas"].most_common()],
                   sorted(r["times"]), r["new"], r["paid"]])
    data = {
        "meta": {"branch": BRANCH, "generated": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
                 "window_start": days[0], "window_end": days[-1],
                 "has_sales": bool(env) and not any(n.startswith("Sales") for n in notes),
                 "has_hr": bool(hr), "has_roster": any(v["jda"] for v in hr.values()), "notes": notes},
        "days": days,
        "areas": areas,
        "mgrs": [[m, mgr_names[m]] for m in mgrs],
        "reps": [{"id": e, "name": names[e], "first": first_seen.get(e, ""),
                  **({k: v for k, v in hr[e].items() if v not in ("", None) and k != "hname" and not (k == "jda" and not v)} if e in hr else {})} for e in reps],
        "rd": rd,
        "sales": [[day_ix[d], rep_ix[e], round(v)] for (d, e), v in sorted(rep_sales.items()) if d in day_ix and e in rep_ix],
        "area_sales": [[day_ix[d], a, round(v)] for (d, a), v in sorted(area_sales.items()) if d in day_ix],
    }
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, OUT_PATH)
    log(f"Wrote {OUT_PATH}: {len(days)} days, {len(reps)} reps, {len(mgrs)} managers, {len(rd)} rep-days")


if __name__ == "__main__":
    main()
