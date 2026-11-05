"""Provisional appointments for the days the appointment table does not have yet, from the live ME allocation API.

The appointment table (datagrowth.tbl_final_data_appt) is loaded around 2 pm, so in the morning it ends the day before
yesterday. This step rebuilds the missing day(s) up to yesterday from the allocation API (the system the table itself is
built from) and writes them to cache\\api_rows.pkl in the table's own row format; records.py adds them to the pages,
marked provisional. Once the table has those days, this step removes api_rows.pkl and the pages show the table only.

Rules (checked 13 Oct 2026 against three saved states of the table: 98% of rows matched one for one; the day being filled
came out +3 / +4 / +12 against the table's own figure once it loaded):
  appointment   allocationType 25, fixed by a TME whose HR city is Mumbai (any city partition of the API), given to an ME
                (not a JDA, not Corporate / Sales (Training)), allocated before midnight
  outcome       the ME's latest action on it before midnight: 36 Follow Up, 33 Not Interested, 32 Not Available,
                2024 Not Visited, 103 Dealclosed; none = Pending
  not counted   cancelled before an outcome; Fake / Bounced / Paid Client / Details Incorrect / DND / refixed outcome;
                refixed by the ME with no outcome yet (Appointment Refixed); Not Available on a same-day allocation
                (Not Available (Online)); handed to another ME by the appointment day
  day           the appointment day, or the day the ME refixed it to
  one a month   one row per business per calendar month: the most recently allocated appointment
  deals         db_paidcontracts deals (dump + 30-day rolling table), Mumbai, jda_flag 0/3, with an ME and a TME: each
                deal version is a row; it takes over that business's appointment row on the day when there is one

API: POST http://192.168.8.121:8082/jdboxNode/bformsubmit/fetchAllocContract (read-only "fetch" pipelines).
"""
import collections
import datetime
import json
import os
import pickle
import sys
import time
import urllib.request

import pymysql

PIPE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(PIPE, "cache")
OUT = os.environ.get("ME_API_OUT") or os.path.join(CACHE, "api_rows.pkl")   # ME_API_OUT: back-tests write elsewhere
API = "http://192.168.8.121:8082/jdboxNode/bformsubmit/fetchAllocContract"
PARTITIONS = ["mumbai", "remote", "delhi", "bangalore", "pune", "ahmedabad", "chennai", "hyderabad", "kolkata"]
FIELDS = ["contractCode", "empcode", "allocationType", "allocationTime", "actionTime", "cancel_flag", "cancelledAt",
          "dispositon_type", "diposition_date", "parentcode", "team_type", "compname", "mename", "tmename", "sub_disp_val"]
OUTCOME = {36: ("Follow Up", "Follow Up"), 33: ("Not Interested", "Not Interested"), 32: ("Not Available", "Not Available (Fixed)"),
           2024: ("Not Visited", "Not Visited"), 103: ("Dealclosed", "Dealclosed")}
NOT_COUNTED = {2025: "Fake Appt", 2026: "Bounced Collection", 207: "Paid Client", 31: "Details Incorrect", 9: "Do Not Disturb",
               35: "Appointment Refixed"}
ACTIONS = {36, 32, 33, 103, 2025, 2026, 207, 31, 9, 2024}
TEAM_NAME = {"SuperCat": "Super Cat", "Revival(Expiry)": "Revival (Expiry)"}
SUB = {"9001": "Budget Constraints / Asking for Discount", "9002": "Prefers Short-Term or Trial Package", "9003": "Needs Time to Decide",
       "9004": "Checking with other vendors", "9005": "Comparing Justdial with Competitors", "9006": "Customer busy with other work/call back",
       "9008": "Will Make Payment Later", "9009": "Other", "9010": "Customer did not respond to calls (RNR)",
       "9011": "Shop/business not found at the given address", "9012": "Address details missing or incomplete in system",
       "9013": "Location falls outside serviceable area", "9014": "Other Reason", "9015": "Customer not interested due to pricing concerns",
       "9016": "Customer prefers short-term or trial package only", "9017": "Customer not convinced after checking ratings/reviews",
       "9018": "Customer received negative feedback from others", "9019": "Business is not yet started or operational", "9020": "Other Reason"}
norm = lambda e: str(e or "").strip().lstrip("0")
D = datetime.date.fromisoformat


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def api(pipeline, city):
    body = json.dumps({"pipelineArr": pipeline, "case": "fetch", "module": "ME", "isAggregate": True, "data_city": city}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(API, body, {"Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(req, timeout=300))
            if j.get("errorCode") not in (0, None):
                raise RuntimeError(j.get("errorStatus"))
            return (j.get("data") or {}).get("records", [])
        except Exception as e:
            if attempt == 2:
                raise
            log(f"API call failed ({e}); retrying")
            time.sleep(10)


def db216():
    sys.path.insert(0, PIPE)
    import fetch_deals
    env = fetch_deals.load_env()
    return pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                           password=env["MYSQL_PASSWORD"], connect_timeout=15, read_timeout=900)


def check_against_table(raw):
    """When the appointment table has loaded a day this step had filled, compare the last provisional figures with the
    table's: logged, appended to checks\\provisional_vs_table.csv, and the provisional rows archived."""
    if not os.path.exists(OUT):
        return
    api = pickle.load(open(OUT, "rb"))
    done = [d for d in api["days"] if D(d) <= raw["end"]]
    if not done:
        return
    NCD = "Not Counted/Cancelled"
    excl = lambda r: (str(r.get("me_team_type_name") or "").strip().lower() == "corporate"
                      or str(r.get("me_section") or "").strip().lower().startswith("sales (training)"))
    def side(cols, rows, day):
        rs = [r for r in (dict(zip(cols, x)) for x in rows) if str(r["to_date"]) == day and r["final_disposition_name"] != NCD and not excl(r)]
        keys = collections.Counter((r["parentid"], norm(r["me"])) for r in rs)
        return {"given": len(rs), "attended": sum(r["final_disposition_name"] in ("Dealclosed", "Follow Up", "Not Interested") for r in rs),
                "deals": sum(r["final_disposition_name"] == "Dealclosed" for r in rs)}, keys
    csv = os.path.join(os.path.dirname(PIPE), "checks", "provisional_vs_table.csv")
    os.makedirs(os.path.dirname(csv), exist_ok=True)
    new = not os.path.exists(csv)
    with open(csv, "a", encoding="utf-8") as f:
        if new:
            f.write("day,provisional_pulled,table_pulled,given_api,given_table,given_diff,attended_api,attended_table,deals_api,deals_table,same_appointments,deals_from\n")
        for day in done:
            a, ka = side(api["cols"], api["rows"], day)
            t, kt = side(raw["cols"], raw["rows"], day)
            same = sum(min(v, ka.get(k, 0)) for k, v in kt.items())
            src = "API deal records" if day in api.get("deals_from_api", []) else "deals tables"
            log(f"Check {day}: provisional (pulled {api['pulled']:%d %b %H:%M}) vs the appointment table - given {a['given']} vs {t['given']} "
                f"({a['given'] - t['given']:+d}), attended {a['attended']} vs {t['attended']}, deals {a['deals']} vs {t['deals']}, "
                f"same appointments {same} of {t['given']} (deals from {src})")
            f.write(f"{day},{api['pulled']:%Y-%m-%d %H:%M},{raw['pulled']:%Y-%m-%d %H:%M},{a['given']},{t['given']},{a['given'] - t['given']},"
                    f"{a['attended']},{t['attended']},{a['deals']},{t['deals']},{same},{src}\n")
    arch = os.path.join(CACHE, "provisional_archive")
    os.makedirs(arch, exist_ok=True)
    os.replace(OUT, os.path.join(arch, f"api_rows_{'_'.join(done)}_{api['pulled']:%Y%m%d_%H%M}.pkl"))


def main():
    args = sys.argv[1:]
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    if "--table-end" not in args:
        check_against_table(raw)
    table_end = raw["end"]
    if "--table-end" in args:                      # testing: pretend the table ends earlier
        table_end = D(args[args.index("--table-end") + 1])
    today = datetime.date.today()
    if "--today" in args:
        today = D(args[args.index("--today") + 1])
    days = [table_end + datetime.timedelta(i) for i in range(1, (today - table_end).days)]
    if not days:
        if os.path.exists(OUT):
            os.remove(OUT)
        log(f"The appointment table already runs to {table_end}: no provisional days (removed any earlier ones).")
        return
    first, last = days[0], days[-1]
    CUT = (last + datetime.timedelta(1)).isoformat() + " 00:00:00"          # as the table: everything before midnight
    log(f"Appointment table runs to {table_end}; building {first} to {last} from the allocation API (cut-off {CUT})")
    win = (first.replace(day=1) - datetime.timedelta(days=20)).isoformat() + " 00:00:00"
    proj = {"$project": {"_id": 0, **{f: 1 for f in FIELDS}}}
    t0 = time.time()
    recs = api([{"$match": {"allocationTime": {"$gte": win, "$lt": CUT}}}, proj], "mumbai")
    log(f"  mumbai partition: {len(recs):,} records since {win[:10]} ({time.time() - t0:.0f}s)")

    # reference data from the table: names, managers, sections of MEs and TMEs (their latest row)
    C = raw["cols"]
    me_info, tme_info, code_form = {}, {}, {}
    for r in sorted((dict(zip(C, x)) for x in raw["rows"]), key=lambda r: r["to_date"]):
        code_form[norm(r["me"])] = r["me"]; code_form[norm(r["tme"])] = r["tme"]
        me_info[norm(r["me"])] = {k: r.get(k) for k in ("mename", "me_manager", "me_manager_code", "me_section", "me_grade", "me_team_type_name")}
        tme_info[norm(r["tme"])] = {k: r.get(k) for k in ("tmename", "tme_team_type_name", "tme_manager", "tme_section")}

    # other city partitions: appointments for these days by any TME; kept only when the TME's HR city is Mumbai (below)
    other = []
    for city in PARTITIONS[1:]:
        o = api([{"$match": {"allocationType": 25, "allocationTime": {"$gte": win, "$lt": CUT},
                             "actionTime": {"$gte": first.replace(day=1).isoformat() + " 00:00:00"}}}, proj], city)
        other.append((city, o))
    # HR (server 216): every TME / ME code met, city / designation / section; and the monthly team table
    codes = sorted({norm(a.get("parentcode")) for a in recs if a["allocationType"] == 25} | {norm(a["empcode"]) for a in recs}
                   | {norm(a.get("parentcode")) for _, o in other for a in o} - {""})
    c = db216(); cur = c.cursor()
    hr = {}
    for i in range(0, len(codes), 1000):
        ch = codes[i:i + 1000]
        cur.execute(f"""SELECT TRIM(LEADING '0' FROM TRIM(empcode)), city, designation, section, team_type
                        FROM db_paidcontracts.hr_all_daily_copy_ganesh WHERE TRIM(LEADING '0' FROM TRIM(empcode)) IN ({','.join(['%s'] * len(ch))})""", ch)
        for e, city, des, sec, tt in cur.fetchall():
            hr[e] = (str(city or "").strip(), str(des or ""), str(sec or ""), str(tt or ""))
    months = sorted({(d.year, d.month) for d in days})
    monthly = {}
    for y, m in months:
        cur.execute("""SELECT TRIM(LEADING '0' FROM TRIM(empcode)), city, emptype, team_type_name FROM db_paidcontracts.tbl_working_days_final_data
                       WHERE year_no = %s AND month_no = %s""", (y, m))
        for e, city, et, team in cur.fetchall():
            monthly[(e, y, m)] = (str(city or ""), str(et or ""), str(team or ""))
    # deals for the days being filled: the 30-day rolling table and the dump (one row per deal version)
    deals, seen, deals_to = [], set(), None
    for table in ("db_paidcontracts.tbl_30_day_rolling_dealdump_data", "db_paidcontracts.daily_deals_closed_dump"):
        try:
            cur.execute(f"""SELECT dealclosed_date, parentid, version, dc_genio, TRIM(IFNULL(me,'')), TRIM(IFNULL(tme,'')), jda_flag
                            FROM {table} WHERE final_datacity = 'Mumbai' AND dealclosed_date BETWEEN %s AND %s AND dc_genio > 0""", (first, last))
            cur2 = c.cursor(); cur2.execute(f"SELECT MAX(dealclosed_date) FROM {table}"); mx = cur2.fetchone()[0]
            deals_to = max(deals_to or mx, mx) if mx else deals_to
            for d, pid, ver, dc, me, tme, jf in cur.fetchall():
                k = (str(d)[:10], pid, str(ver), norm(me))
                if k not in seen:
                    seen.add(k); deals.append({"day": str(d)[:10], "pid": (pid or "").strip(), "dc": float(dc or 0), "me": norm(me), "tme": norm(tme), "jda": int(jf or 0)})
        except pymysql.MySQLError as e:
            log(f"  {table} could not be read ({e}); deals from the other table only")
    c.close()
    tme_mumbai = lambda p: bool(p) and (hr.get(p) or ("",))[0] == "Mumbai"
    keep_other = []
    for city, o in other:
        k = [a for a in o if tme_mumbai(norm(a.get("parentcode")))]
        keep_other += k
        if k: log(f"  {city}: {len(k):,} appointments by Mumbai TMEs")
    if keep_other:   # their outcomes and refixes
        pids = sorted({a["contractCode"] for a in keep_other})
        for city in PARTITIONS[1:]:
            more = api([{"$match": {"contractCode": {"$in": pids}, "allocationTime": {"$gte": win, "$lt": CUT}}}, proj], city)
            recs += more

    def me_counted(me, day):
        mrow = monthly.get((me, day.year, day.month))
        if mrow:
            return mrow[1] == "ME" and mrow[2] not in ("Corporate", "JDA")
        h = hr.get(me)
        if h:
            sec = h[2].strip().lower()
            return not (sec.startswith("jda") or sec.startswith("corporate") or sec.startswith("sales (training)") or h[3] == "CO")
        info = me_info.get(me)
        return bool(info) and str(info.get("me_team_type_name") or "") not in ("Corporate", "JDA")

    # ---- the rule ----
    seen_r, A = set(), []
    for a in recs:
        k = (a["contractCode"], a["empcode"], a["allocationType"], a["allocationTime"])
        if k not in seen_r:
            seen_r.add(k); A.append(a)
    BY = collections.defaultdict(list); BYC25 = collections.defaultdict(list); NAME = {}
    for a in A:
        BY[(a["contractCode"], norm(a["empcode"]))].append(a)
        if a["allocationType"] == 25: BYC25[a["contractCode"]].append(a)
        if a.get("compname"): NAME[a["contractCode"]] = a["compname"]
    for v in list(BY.values()) + list(BYC25.values()): v.sort(key=lambda a: a["allocationTime"])
    cand = []
    for (pid, me), v in BY.items():
        t25 = [a for a in v if a["allocationType"] == 25]
        for i, a in enumerate(t25):
            tme = norm(a.get("parentcode"))
            if not tme_mumbai(tme): continue
            nxt = t25[i + 1]["allocationTime"] if i + 1 < len(t25) else "9"
            acts = [b for b in v if b["allocationType"] in ACTIONS and a["allocationTime"] < b["allocationTime"] < min(nxt, CUT)]
            if acts:
                disp, dtime, sub = acts[-1]["allocationType"], acts[-1]["allocationTime"], acts[-1].get("sub_disp_val")
            else:
                dd = a.get("diposition_date") or "9"
                disp, dtime, sub = (a.get("dispositon_type"), dd, None) if dd < CUT else (None, None, None)
                if disp == 35: disp, dtime = None, None
            cancelled = False
            if a["cancel_flag"] == 1 and disp is None:
                later = [b["allocationTime"] for b in BYC25[pid] if b["allocationTime"] > a["allocationTime"]]
                ct = a.get("cancelledAt") or (later[0] if later else None)
                cancelled = (ct < CUT) if ct else True
            refix = [b for b in v if b["allocationType"] == 35 and a["allocationTime"] < b["allocationTime"] < min(nxt, CUT)
                     and (disp is None or (dtime or "") >= b["actionTime"])]
            slot = (refix[-1] if refix else a)["actionTime"]
            day = slot[:10]
            if any(b["allocationTime"] > a["allocationTime"] and b["allocationTime"][:10] <= day and b["allocationTime"] < CUT
                   and norm(b["empcode"]) != me for b in BYC25[pid]): continue
            if not me_counted(me, D(day)): continue
            if cancelled: st, why = "ncd", "TME Cancelled"
            elif disp in NOT_COUNTED: st, why = "ncd", NOT_COUNTED[disp]
            elif refix and disp is None and tme != me: st, why = "ncd", "Appointment Refixed"
            elif disp == 32 and a["allocationTime"][:10] == a["actionTime"][:10]: st, why = "ncd", "Not Available (Online)"
            elif disp == 103: st, why = "deal", "Dealclosed"
            else: st, why = "counted", None
            cand.append({"pid": pid, "me": me, "tme": tme, "day": day, "alloc": a["allocationTime"], "slot": slot, "st": st, "why": why,
                         "disp": disp, "dtime": dtime, "sub": sub, "team": a.get("team_type") or "", "mename": a.get("mename") or "",
                         "tmename": a.get("tmename") or "", "atype": disp if disp is not None else (35 if refix else None)})
    last_in_month = {}
    for c_ in cand:
        k = (c_["pid"], c_["day"][:7])
        if k not in last_in_month or (c_["alloc"], c_["day"]) > (last_in_month[k]["alloc"], last_in_month[k]["day"]):
            last_in_month[k] = c_
    fill = {d.isoformat() for d in days}
    # the deals tables get yesterday's deals at about 10:15 am; until then a day's deals are the system's Dealclosed records (103) in the API
    no_deals = {d for d in fill if not deals_to or d > str(deals_to)}
    if "--no-deals" in sys.argv[1:]:   # testing: as at 8 am, before the deals tables have the day
        no_deals = set(fill); deals = [x for x in deals if x["day"] not in fill]
    if no_deals:
        log(f"  deals tables run to {deals_to}: deals for {', '.join(sorted(no_deals))} from the system's Dealclosed records in the allocation API (103) until they arrive")
    rows_out = [c_ for c_ in last_in_month.values() if c_["day"] in fill]
    # deals: each version is a row; it takes over the business's appointment row (same ME, same day) when there is one
    dl = [x for x in deals if x["jda"] in (0, 3) and x["me"] and x["tme"] and x["day"] in fill and me_counted(x["me"], D(x["day"]))]
    by_key = collections.defaultdict(list)
    for x in dl: by_key[(x["pid"], x["me"], x["day"])].append(x)
    out = []
    for c_ in rows_out:
        k = (c_["pid"], c_["me"], c_["day"])
        if c_["st"] == "deal" and c_["day"] in no_deals:
            out.append(dict(c_, final="Dealclosed", dispname="Dealclosed")); continue
        if c_["st"] == "deal":
            if by_key.get(k):
                by_key[k].pop(0); out.append(dict(c_, final="Dealclosed", dispname="Dealclosed"))
            continue                                                      # a deal the finance tables do not have: not in the table
        if c_["st"] == "counted" and by_key.get(k):
            by_key[k].pop(0); out.append(dict(c_, final="Dealclosed", dispname="Dealclosed")); continue
        if c_["st"] == "ncd":
            out.append(dict(c_, final="Not Counted/Cancelled", dispname=c_["why"])); continue
        fin, dn = OUTCOME.get(c_["disp"], ("Pending", "Pending"))
        out.append(dict(c_, final=fin, dispname=dn))
    if no_deals:
        # Before the deals tables have the day: an ME's Dealclosed mark (type 103) that day is a deal row when the ME has no
        # row of their own that day (back-tested 29 Sep - 13 Oct 2026 against the table):
        #  - also when the ME's appointment for it was on an earlier day: the table moves the business's row to the deal day
        #    (records.py drops the earlier row, see 'replaces')
        #  - also when the business never had a TME appointment: then the ME's own city decides (the table's row has the TME
        #    from the deals table, which the API does not have)
        #  - not when the ME's appointment for it is still to come (the deal was marked before the appointment)
        have = {(c_["pid"], c_["me"], c_["day"]) for c_ in out}

        def me_mumbai(me, day):
            mrow = monthly.get((me, day.year, day.month))
            return (mrow[0] if mrow else (hr.get(me) or ("",))[0]) == "Mumbai"
        # a Mumbai ME's Dealclosed can sit in another city's partition when the business has no Mumbai TME appointment
        # (15 Oct 2026: 3 in "bangalore"). 29 Sep - 15 Oct: 21 of 27 such records had a table row that day, about the
        # same as the "mumbai" ones without a TME appointment, so they are taken the same way.
        extra = 0
        for city in PARTITIONS[1:]:
            for a in api([{"$match": {"allocationType": 103, "allocationTime": {"$gte": min(no_deals) + " 00:00:00", "$lt": CUT}}}, proj], city):
                me, day = norm(a["empcode"]), a["allocationTime"][:10]
                k = (a["contractCode"], a["empcode"], a["allocationType"], a["allocationTime"])
                if day in no_deals and k not in seen_r and me_counted(me, D(day)) and me_mumbai(me, D(day)):
                    seen_r.add(k); BY[(a["contractCode"], me)].append(a); extra += 1
        if extra:
            log(f"  {extra} Dealclosed records of Mumbai MEs found in other cities' partitions")
        for (pid, me), v in BY.items():
            mine25 = [a for a in v if a["allocationType"] == 25]
            for a in v:
                day = a["allocationTime"][:10]
                if a["allocationType"] != 103 or day not in no_deals or a["allocationTime"] >= CUT or (pid, me, day) in have: continue
                if not me_counted(me, D(day)): continue
                if any(b["actionTime"][:10] > day and b["allocationTime"] <= a["allocationTime"] and b.get("cancel_flag") != 1 for b in mine25):
                    continue
                src = [b for b in mine25 if b["actionTime"][:10] <= day] or BYC25.get(pid, [])
                tme = norm(next((b.get("parentcode") for b in reversed(src) if b.get("parentcode")), ""))
                if tme and not tme_mumbai(tme): continue
                if not tme and not me_mumbai(me, D(day)): continue
                have.add((pid, me, day))
                by_key[(pid, me, day)].append({"pid": pid, "me": me, "tme": tme, "day": day, "dc": 1.0, "time": a["allocationTime"]})
    replaces = set()
    for k, xs in by_key.items():
        for x in xs:                                                       # deals with no appointment row of their own
            out.append({"pid": x["pid"], "me": x["me"], "tme": x["tme"], "day": x["day"], "alloc": None, "slot": x["day"] + " 12:00:00",
                        "st": "deal", "final": "Dealclosed", "dispname": "Dealclosed", "dtime": x["day"] + " 12:00:00", "sub": None,
                        "team": "", "mename": "", "tmename": "" if x["tme"] else "(no TME appointment)", "atype": None, "dc": x["dc"]})
            replaces.add((x["pid"], x["me"], x["day"]))                  # the ME's earlier row this month moves to this day
    # ---- in the table's own row format ----
    dt = lambda s: datetime.datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S") if s and len(s) >= 19 else None
    rows = []
    for x in out:
        mi = me_info.get(x["me"]) or {}
        ti = tme_info.get(x["tme"]) or {}
        att = x["final"] in ("Dealclosed", "Follow Up", "Not Interested")
        rec = {"to_date": D(x["day"]), "parentid": x["pid"], "companyname": NAME.get(x["pid"], ""),
               "tme": code_form.get(x["tme"], x["tme"]), "tmename": ti.get("tmename") or x["tmename"],
               "me": code_form.get(x["me"], x["me"]), "mename": mi.get("mename") or x["mename"],
               "me_manager": mi.get("me_manager") or "Not recorded", "me_manager_code": mi.get("me_manager_code") or "",
               "tme_team_type_name": ti.get("tme_team_type_name") or TEAM_NAME.get(x["team"], x["team"]) or "Not recorded",
               "tme_manager": ti.get("tme_manager") or "", "final_disposition_name": x["final"], "disposition_name": x["dispname"],
               "attended_count": int(att), "dealclosed_count": int(x["final"] == "Dealclosed"), "dc_genio": x.get("dc", 1.0 if x["final"] == "Dealclosed" else 0.0),
               "ecs_flag": None, "me_section": mi.get("me_section") or "", "me_grade": mi.get("me_grade") or "",
               "given_count": int(bool(x["alloc"]) and x["tme"] != x["me"]), "tme_section": ti.get("tme_section") or "",
               "allocationtime": dt(x["alloc"]), "actiontime": dt(x["slot"]), "allocationType": x["atype"], "entry_date": None,
               "given_date": dt(x["slot"]), "attended_date": dt(x["dtime"]) if att else None,
               "dealclosed_date": dt(x["dtime"]) if x["final"] == "Dealclosed" else None, "data_city": "mumbai",
               "sub_disposition_value": SUB.get(str(x["sub"] or "")), "me_team_type_name": mi.get("me_team_type_name") or "BDE",
               "jda_flag": 0}
        rows.append(tuple(rec.get(k) for k in C))
    given = collections.Counter(str(r[C.index("to_date")]) for r in rows if r[C.index("final_disposition_name")] != "Not Counted/Cancelled")
    pickle.dump({"cols": C, "rows": rows, "days": [d.isoformat() for d in days], "cut": CUT, "deals_from_api": sorted(no_deals), "replaces": sorted(replaces), "pulled": datetime.datetime.now(),
                 "table_end": table_end}, open(OUT + ".tmp", "wb"))
    os.replace(OUT + ".tmp", OUT)
    log("Provisional appointments given: " + ", ".join(f"{d} {given[d]:,}" for d in sorted(given)) + f" ({len(rows):,} rows incl. not counted). Saved cache\\api_rows.pkl")


if __name__ == "__main__":
    main()
