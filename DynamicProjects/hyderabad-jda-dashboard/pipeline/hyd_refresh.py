r"""
Pull the data for the Hyderabad JDA dashboard into pipeline\hyd_data.json. main.py runs this, then puts the data
into the page; you never run it yourself.

Sources:
- Presentations: the presentation feed (internal, no login), one day at a time. Every day read is saved in
  pipeline\pres_store\ (Hyderabad-branch pincodes only); only the last 14 days are fetched again. The feed keeps about
  6 months, so older days exist only in that folder: NEVER DELETE IT.
- Sales (optional): db_paidcontracts.daily_deals_closed_dump, through pipeline\db_216.env. Without that file the page
  shows presentations only and says so.
- Category YoY deals (optional, same login): ops_analytics.tbl_modified_deal_level_data joined with
  vertical_owner.tbl_company_vertical_mapping_SB on docid, using SUM(dc_genio) for current FY vs same dates last FY.
  Incremental refresh: pre-aggregated daily totals are stored in pipeline\cat_deals_cache.json.gz (no raw deal rows).
  Each daily run fetches only missing LY dates + the last 14 days (and any missing gaps) of TY, pruning older FYs.
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
import csv
import datetime
import gzip
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
MODIFIED_DEALS = "`ops_analytics`.`tbl_modified_deal_level_data`"
CAT_MAP = "`vertical_owner`.`tbl_company_vertical_mapping_SB`"
CAT_CACHE_PATH = os.path.join(PIPE_DIR, "cat_deals_cache.json.gz")
CAT_RECHECK_DAYS = 14   # re-fetch only the last 14 days of TY for late clearances; older TY & all fetched LY days stay cached
CAT_CSV_DIR = os.path.join(PIPE_DIR, "category_data")
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


CAT_ACRONYMS = {
    "jdmart": "JDMart", "re": "RE", "b2b": "B2B", "b2c": "B2C", "it": "IT", "ac": "AC", "tv": "TV",
    "cctv": "CCTV", "led": "LED", "ro": "RO", "uv": "UV", "gst": "GST", "ca": "CA", "ivf": "IVF",
    "ent": "ENT", "pvc": "PVC", "upvc": "UPVC", "cnc": "CNC", "pg": "PG", "dj": "DJ", "hr": "HR",
    "pr": "PR", "atm": "ATM", "gps": "GPS", "ev": "EV", "dth": "DTH", "ngo": "NGO", "rto": "RTO",
    "cab": "Cab", "bbq": "BBQ", "diy": "DIY", "cnc": "CNC", "plc": "PLC", "erp": "ERP", "crm": "CRM",
}


def pretty_cat(s, fallback="Unmapped"):
    t = " ".join(str(s or "").strip().split())
    if not t or t.lower() in ("\\n", "null", "none"):
        return fallback
    words = []
    for w in t.split(" "):
        low = w.lower()
        if low in CAT_ACRONYMS:
            words.append(CAT_ACRONYMS[low])
        elif w in ("&", "-", "/", "of", "and", "in", "for", "on", "to"):
            words.append(w.lower() if words else w.title())
        else:
            words.append(w.title())
    return " ".join(words)


def loc_bucket(pin, main_remote, pin_area, areas):
    """4 mutually exclusive scope buckets matching the dashboard's Branch/Main/Remote/Telangana/Andhra filters:
    0 = Hyderabad Main (TS), 1 = Telangana Remote (TS), 2 = Andhra Pradesh Remote (AP), 3 = Other Remote."""
    p = str(pin or "").strip().split(".")[0]
    if p in pin_area:
        a = areas[pin_area[p]]
        if a["main"] == 1:
            return 0
        return 1 if a["state"] == "TS" else (2 if a["state"] == "AP" else 3)
    if str(main_remote or "").strip() == "1":
        return 0
    if p.startswith("50"):
        return 1
    if p[:2] in ("51", "52", "53"):
        return 2
    return 3


def fy_mmdd(ds):
    """Monotonic Indian FY month-day integer: Apr 1 = 401 .. Dec 31 = 1231, Jan 1 = 1301 .. Mar 31 = 1531."""
    m, d = int(ds[5:7]), int(ds[8:10])
    return (m + (12 if m < 4 else 0)) * 100 + d


def year_back(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:   # 29 Feb
        return d.replace(year=d.year - 1, day=28)


def iter_dates(a, b):
    d = a
    while d <= b:
        yield d
        d += datetime.timedelta(days=1)


def date_span_chunks(dates):
    """Group sorted datetime.date list into contiguous (start_iso, end_iso) spans, split by month."""
    if not dates:
        return []
    spans = []
    s = p = dates[0]
    for d in dates[1:]:
        if (d - p).days == 1:
            p = d
        else:
            spans.append((s, p))
            s = p = d
    spans.append((s, p))
    chunks = []
    for a, b in spans:
        chunks.extend(month_chunks(a.isoformat(), b.isoformat()))
    return chunks


def load_cat_cache():
    if os.path.exists(CAT_CACHE_PATH):
        try:
            with gzip.open(CAT_CACHE_PATH, "rt", encoding="utf-8") as f:
                c = json.load(f)
            if isinstance(c, dict) and isinstance(c.get("days"), dict):
                return c
        except Exception as e:
            log(f"WARNING: could not read {CAT_CACHE_PATH} ({e}); starting fresh cache.")
    return {"version": 1, "cats": [], "subcats": [], "days": {}}


def save_cat_cache(cache):
    tmp = CAT_CACHE_PATH + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(cache, f, separators=(",", ":"))
    os.replace(tmp, CAT_CACHE_PATH)


def merge_raw_rows_into_cache(cache, raw_rows, doc_cat, pin_area, areas, fetched_dates):
    """Aggregate raw deal tuples into compact daily totals in cache['days'] (no raw deals stored)."""
    cat_ix = {c: i for i, c in enumerate(cache["cats"])}
    sub_ix = {(cache["cats"][ci], s): i for i, (ci, s) in enumerate(cache["subcats"])}

    def get_sub_idx(cat, sub):
        ci = cat_ix.get(cat)
        if ci is None:
            ci = len(cache["cats"])
            cache["cats"].append(cat)
            cat_ix[cat] = ci
        si = sub_ix.get((cat, sub))
        if si is None:
            si = len(cache["subcats"])
            cache["subcats"].append([ci, sub])
            sub_ix[(cat, sub)] = si
        return si

    by_day = {ds: defaultdict(lambda: [0.0, 0.0]) for ds in fetched_dates}
    matched = 0
    for ds, docid, pin, mr, fresh, flag, team, dc, rv in raw_rows:
        if ds not in by_day or dc <= 0:
            continue
        cinfo = doc_cat.get(docid)
        if cinfo:
            matched += 1
            cat = pretty_cat(cinfo[0], "No Category")
            sub = pretty_cat(cinfo[1], "Other")
        else:
            cat, sub = "Unmapped", "Unmapped"
        si = get_sub_idx(cat, sub)
        loc = loc_bucket(pin, mr, pin_area, areas)
        fr = 1 if str(fresh).strip() == "1" else 0
        jt = 1 if str(team or "").strip().upper() == "JDA" else 0
        # rv_3yr repeats on both rows of a joint (jda_flag=2) deal; halving gives 1x total RV and 0.5x JDA share
        rv_w = rv * (0.5 if int(flag or 1) == 2 else 1.0)
        acc = by_day[ds][(loc, si, fr, jt)]
        acc[0] += dc
        acc[1] += rv_w

    for ds, agg in by_day.items():
        cache["days"][ds] = [[loc, si, fr, jt, round(dc, 2), round(rv)]
                             for (loc, si, fr, jt), (dc, rv) in sorted(agg.items())]
    return matched


def prune_cat_cache(cache, keep_from_iso):
    """Drop dates older than last FY start so the cache never grows across old years."""
    old = [ds for ds in cache["days"] if ds < keep_from_iso]
    for ds in old:
        del cache["days"][ds]
    return len(old)


def seed_cat_cache_from_csv(cache, pin_area, areas):
    """One-time seed from exported CSVs in pipeline\\category_data\\ when no cache exists yet."""
    f25 = os.path.join(CAT_CSV_DIR, "hyd_2025_deals.csv")
    f26 = os.path.join(CAT_CSV_DIR, "hyd_2026_deals.csv")
    fcat = os.path.join(CAT_CSV_DIR, "hyd_2025_2026_categories.csv")
    if not (os.path.exists(f25) and os.path.exists(f26) and os.path.exists(fcat)):
        return False

    doc_cat = {}
    with open(fcat, encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        ix_d, ix_v, ix_sv = hdr.index("docid"), hdr.index("vertical"), hdr.index("sub_vertical")
        for row in r:
            if len(row) <= max(ix_d, ix_v, ix_sv):
                continue
            did = row[ix_d].strip()
            if did and did not in doc_cat:
                doc_cat[did] = (row[ix_v].strip(), row[ix_sv].strip())

    def load_deals(path):
        out = []
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                dc = to_float(row.get("dc_genio"))
                if dc <= 0 or str(row.get("fresh") or "").strip() not in ("0", "1"):
                    continue
                fl = int(to_float(row.get("jda_flag")) or 1)
                if fl not in (1, 2):
                    continue
                ds = (row.get("dealclosed_date") or "").strip()[:10]
                if len(ds) == 10:
                    out.append((
                        ds, (row.get("docid") or "").strip(), (row.get("pincode") or "").strip(),
                        (row.get("branch_main_remote") or "").strip(), (row.get("fresh") or "").strip(),
                        fl, (row.get("final_team_type_name") or "").strip(), dc, to_float(row.get("rv_3yr")),
                    ))
        return out

    ly_rows, ty_rows = load_deals(f25), load_deals(f26)
    fetched = set()
    for rows in (ly_rows, ty_rows):
        if rows:
            ds_list = sorted(r[0] for r in rows)
            for d in iter_dates(datetime.date.fromisoformat(ds_list[0]), datetime.date.fromisoformat(ds_list[-1])):
                fetched.add(d.isoformat())
    matched = merge_raw_rows_into_cache(cache, ly_rows + ty_rows, doc_cat, pin_area, areas, fetched)
    log(f"Seeded {CAT_CACHE_PATH} from CSVs: {len(fetched)} days ({matched}/{len(ly_rows) + len(ty_rows)} rows matched)")
    return True


def update_cat_cache_sql(cache, env, pin_area, areas, ty_start, ty_end, ly_start, ly_end, full=False):
    """Incrementally fetch ONLY missing LY dates and missing/recent (last 14d) TY dates from MySQL."""
    days_map = cache["days"]
    recheck_from = max(ty_start, ty_end - datetime.timedelta(days=CAT_RECHECK_DAYS - 1))
    if full:
        ly_need = list(iter_dates(ly_start, ly_end))
        ty_need = list(iter_dates(ty_start, ty_end))
    else:
        ly_need = [d for d in iter_dates(ly_start, ly_end) if d.isoformat() not in days_map]
        ty_need = [d for d in iter_dates(ty_start, ty_end) if d >= recheck_from or d.isoformat() not in days_map]

    need_dates = sorted(set(ly_need) | set(ty_need))
    if not need_dates:
        log("Categories (incremental SQL): all TY and LY dates already cached; 0 SQL queries needed.")
        return False

    chunks = date_span_chunks(need_dates)
    raw_rows = []
    for a, b in chunks:
        conn = db_connect(env)
        with conn.cursor() as cur:
            cur.execute(f"""SELECT dealclosed_date, TRIM(IFNULL(docid, '')), TRIM(IFNULL(pincode, '')),
                                   branch_main_remote, fresh, jda_flag, TRIM(IFNULL(final_team_type_name, '')),
                                   dc_genio, IFNULL(rv_3yr, 0)
                            FROM {MODIFIED_DEALS}
                            WHERE dealclosed_date BETWEEN %s AND %s
                              AND sales_branch = %s
                              AND dc_genio > 0
                              AND fresh IN (0, 1)
                              AND jda_flag IN (1, 2)""", (a, b, BRANCH))
            for day, docid, pin, mr, fresh, flag, team, dc, rv in cur.fetchall():
                ds = day.isoformat() if hasattr(day, "isoformat") else str(day)[:10]
                raw_rows.append((ds, docid, pin, mr, fresh, int(flag or 1), team, to_float(dc), to_float(rv)))
        conn.close()

    docids = sorted({r[1] for r in raw_rows if r[1]})
    doc_cat = {}
    if docids:
        conn = db_connect(env)
        with conn.cursor() as cur:
            for i in range(0, len(docids), 1000):
                ch = docids[i:i + 1000]
                ph = ",".join(["%s"] * len(ch))
                cur.execute(f"""SELECT TRIM(docid),
                                       MAX(TRIM(IFNULL(vertical, ''))),
                                       MAX(TRIM(IFNULL(sub_vertical, '')))
                                FROM {CAT_MAP}
                                WHERE docid IN ({ph})
                                GROUP BY TRIM(docid)""", ch)
                for did, v, sv in cur.fetchall():
                    if did:
                        doc_cat[did] = (v, sv)
        conn.close()

    fetched_isos = {d.isoformat() for d in need_dates}
    matched = merge_raw_rows_into_cache(cache, raw_rows, doc_cat, pin_area, areas, fetched_isos)
    pruned = prune_cat_cache(cache, ly_start.isoformat())
    log(f"Categories (incremental SQL): fetched {len(ly_need)} LY + {len(ty_need)} TY days ({len(chunks)} chunk(s), "
        f"{len(raw_rows)} deal rows, {matched} cat-matched, {len(docids)} docids); pruned {pruned} old days")
    return True


def build_cat_deals_from_cache(cache, ty_start, ty_end, ly_start, ly_end, source):
    """Pack compact dashboard JSON from the pre-aggregated daily cache for TY vs LY."""
    ly_a, ly_b = ly_start.isoformat(), ly_end.isoformat()
    ty_a, ty_b = ty_start.isoformat(), ty_end.isoformat()
    old_cats, old_subs = cache["cats"], cache["subcats"]

    cat_tot, sub_tot = Counter(), Counter()
    agg_rows = []
    ly_dates, ty_dates = [], []

    for ds, entries in sorted(cache["days"].items()):
        if ly_a <= ds <= ly_b:
            yr = 0
            if entries:
                ly_dates.append(ds)
        elif ty_a <= ds <= ty_b:
            yr = 1
            if entries:
                ty_dates.append(ds)
        else:
            continue
        if not entries:
            continue
        mmdd = fy_mmdd(ds)
        for loc, si, fr, jt, dc, rv in entries:
            ci, sub = old_subs[si]
            cat = old_cats[ci]
            cat_tot[cat] += dc
            sub_tot[(cat, sub)] += dc
            agg_rows.append((yr, mmdd, loc, cat, sub, fr, jt, dc, rv))

    if not ly_dates or not ty_dates:
        return None

    tail_cats = {"No Category", "Unmapped"}
    cats = sorted(cat_tot, key=lambda c: (1 if c in tail_cats else 0, -cat_tot[c], c))
    cat_ix = {c: i for i, c in enumerate(cats)}
    sub_keys = sorted(sub_tot, key=lambda cs: (cat_ix[cs[0]], -sub_tot[cs], cs[1]))
    sub_ix = {cs: i for i, cs in enumerate(sub_keys)}
    subcats = [[cat_ix[c], s] for c, s in sub_keys]

    packed = [[yr, mmdd, loc, sub_ix[(cat, sub)], fr, jt, round(dc, 2), round(rv)]
              for yr, mmdd, loc, cat, sub, fr, jt, dc, rv in agg_rows]

    c_start_k = max(fy_mmdd(ty_dates[0]), fy_mmdd(ly_dates[0]))
    c_end_k = min(fy_mmdd(ty_dates[-1]), fy_mmdd(ly_dates[-1]))
    fmt_k = lambda k: f"{(k // 100 - (12 if k // 100 > 12 else 0)):02d}-{k % 100:02d}"
    common_start, common_end = fmt_k(c_start_k), fmt_k(c_end_k)
    log(f"Categories ({source}): {len(cats)} categories, {len(subcats)} sub-categories, {len(packed)} agg rows | "
        f"LY {ly_dates[0]}..{ly_dates[-1]}, TY {ty_dates[0]}..{ty_dates[-1]}, common {common_start}..{common_end}")
    return {
        "source": source,
        "ty_year": ty_start.year,
        "ly_year": ly_start.year,
        "ty_start": ty_dates[0],
        "ty_end": ty_dates[-1],
        "ly_start": ly_dates[0],
        "ly_end": ly_dates[-1],
        "common_start": common_start,
        "common_end": common_end,
        "common_start_k": c_start_k,
        "common_end_k": c_end_k,
        "cats": cats,
        "subcats": subcats,
        "rows": packed,
    }


def load_category_deals(env, pin_area, areas, notes, full=False):
    end_d = datetime.date.fromisoformat(WINDOW_END)
    fy_year = end_d.year if end_d.month >= 4 else end_d.year - 1
    ty_start, ty_end = datetime.date(fy_year, 4, 1), end_d
    ly_start, ly_end = datetime.date(fy_year - 1, 4, 1), year_back(end_d)

    cache = load_cat_cache()
    changed = False
    if not cache["days"] and not full:
        if seed_cat_cache_from_csv(cache, pin_area, areas):
            prune_cat_cache(cache, ly_start.isoformat())
            changed = True

    source = "cache"
    if env:
        try:
            if update_cat_cache_sql(cache, env, pin_area, areas, ty_start, ty_end, ly_start, ly_end, full=full):
                changed = True
            source = "sql"
        except Exception as e:
            log(f"WARNING: category YoY SQL failed ({type(e).__name__}: {e}); using cached daily aggregates.")
            if not cache["days"]:
                notes.append("Category YoY deals could not be read this time.")
    if changed:
        save_cat_cache(cache)

    return build_cat_deals_from_cache(cache, ty_start, ty_end, ly_start, ly_end, source)


def main():
    cat_only = "--cat-only" in sys.argv
    full_cat = "--full-cat-refresh" in sys.argv
    pin_area, areas, city_area = load_geo()
    env_file = find_env()
    env = load_env(env_file) if env_file else None

    if cat_only:
        if not os.path.exists(OUT_PATH):
            sys.exit(f"Cannot run --cat-only: {OUT_PATH} does not exist yet.")
        log("=== Hyderabad dashboard category-only refresh ===")
        with open(OUT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        notes = []
        cat_deals = load_category_deals(env, pin_area, areas, notes, full=full_cat)
        if not cat_deals:
            sys.exit("Category YoY data could not be loaded from SQL, cache, or pipeline\\category_data.")
        data["cat_deals"] = cat_deals
        data.setdefault("meta", {})["has_categories"] = True
        tmp = OUT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp, OUT_PATH)
        log(f"Updated cat_deals in {OUT_PATH} ({len(cat_deals['cats'])} categories, {len(cat_deals['subcats'])} sub-categories)")
        return

    log(f"=== Hyderabad dashboard refresh: {WINDOW_START} to {WINDOW_END} ===")
    log(f"{len(pin_area)} Hyderabad-branch pincodes in {len(areas)} areas")
    days, recs, names, mgr_names = read_presentations(pin_area)
    if not days:
        sys.exit("No presentation days read: is this PC on the office network or VPN?")

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
    cat_deals = load_category_deals(env, pin_area, areas, notes, full=full_cat)

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
                 "has_hr": bool(hr), "has_roster": any(v["jda"] for v in hr.values()),
                 "has_categories": bool(cat_deals), "notes": notes},
        "days": days,
        "areas": areas,
        "mgrs": [[m, mgr_names[m]] for m in mgrs],
        "reps": [{"id": e, "name": names[e], "first": first_seen.get(e, ""),
                  **({k: v for k, v in hr[e].items() if v not in ("", None) and k != "hname" and not (k == "jda" and not v)} if e in hr else {})} for e in reps],
        "rd": rd,
        "sales": [[day_ix[d], rep_ix[e], round(v)] for (d, e), v in sorted(rep_sales.items()) if d in day_ix and e in rep_ix],
        "area_sales": [[day_ix[d], a, round(v)] for (d, a), v in sorted(area_sales.items()) if d in day_ix],
        **({"cat_deals": cat_deals} if cat_deals else {}),
    }
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, OUT_PATH)
    log(f"Wrote {OUT_PATH}: {len(days)} days, {len(reps)} reps, {len(mgrs)} managers, {len(rd)} rep-days")


if __name__ == "__main__":
    main()
