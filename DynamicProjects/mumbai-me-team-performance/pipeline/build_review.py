"""Step 2b of the refresh: the ME review page ("Mumbai ME Team Performance.html"; was jd-me-review.html until 2026-10-12), built from the same records as the team page
(records.py) plus the timing columns and HR context it needs for its checks.

What it adds to each appointment:
  times   booked (allocationtime), slot (actiontime), outcome entered (attended_date), deal entered (dealclosed_date),
          as minutes from 1 April; -1 when the table has none
  flags   record checks, decided here once so the page and this script agree:
            1  "Not available" entered 1+ hour before the booked slot (slot on the appointment day only)
            2  deal entered before the appointment was booked
            4  deal with no booking record (no allocationtime): the appointment row was made at the deal
            8  still Pending 2+ days after the appointment day (at the refresh)
           16  the same business had 2+ appointments given that day
Also: appointments not counted as given (given_count 0) per ME, and days present per ME and month (HR).

    python build_review.py          data only: swaps the data inside the existing page, keeps its design
    python build_review.py --full   rebuilds the page from the design files in pipeline\\app_review
"""
import base64
from array import array
from collections import Counter, defaultdict
import datetime
import json
import os
import pickle
import re
import sys

from records import prepare, tidy

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
APP = os.path.join(PIPE, "app_review")
FONTS = os.path.join(PIPE, "app", "fonts")
LOGO = os.path.join(PIPE, "app", "jd_logo.png")
PAGE = os.environ.get("ME_REVIEW_OUT") or os.path.join(KIT, "Mumbai ME Team Performance.html")
DATA_FORMAT = 2   # 2: deals closed as their own records (dl), Sales MIS rule (15 Oct 2026)
F_NA_EARLY, F_DEAL_BEFORE_BOOKED, F_NO_BOOKING, F_PENDING, F_SAME_DAY = 1, 2, 4, 8, 16
NA_EARLY_MIN = 60          # minutes before the slot
PENDING_DAYS = 2


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def main():
    P = prepare(PIPE, log)
    fy, end, raw = P["fy"], P["end"], P["raw"]
    MES, MGRS, TMES, TEAMS = P["MES"], P["MGRS"], P["TMES"], P["TEAMS"]
    recs, bad, deal_src, later, mg_up = P["recs"], P["bad"], P["deal_src"], P["later"], P["mg_up"]
    if "allocationtime" not in raw["cols"]:
        sys.exit("cache\\raw.pkl has no timing columns: run fetch_data.py (this version) first. The page was not changed.")
    t0 = datetime.datetime.combine(fy, datetime.time())
    mins = lambda v: int((v - t0).total_seconds() // 60) if isinstance(v, datetime.datetime) else -1
    D_end = (end - fy).days

    per_day = Counter((x[7], x[0]) for x in recs if x[7])
    flags, sl, bk, en, dc = [], [], [], [], []
    for x in recs:
        r, o, f = x[8], x[5], 0
        slot, booked, entered, dealt = r["actiontime"], r["allocationtime"], r["attended_date"], r["dealclosed_date"]
        if o == 3 and slot and entered and slot.date() == r.get("appt_date", r["to_date"]) and (slot - entered).total_seconds() >= NA_EARLY_MIN * 60:
            f |= F_NA_EARLY
        if o == 0 and booked and dealt and dealt < booked:
            f |= F_DEAL_BEFORE_BOOKED
        if o == 0 and not booked:
            f |= F_NO_BOOKING
        if o == 4 and D_end - x[0] >= PENDING_DAYS:
            f |= F_PENDING
        if x[7] and per_day[(x[7], x[0])] > 1:
            f |= F_SAME_DAY
        flags.append(f)
        sl.append(mins(slot)); bk.append(mins(booked)); en.append(mins(entered)); dc.append(mins(dealt) if o == 0 else -1)
    fc = Counter()
    for f in flags:
        for b, k in ((1, "na_early"), (2, "deal_before_booked"), (4, "no_booking"), (8, "pending"), (16, "same_day")):
            if f & b:
                fc[k] += 1
    log("Record checks since 1 April: " + ", ".join(f"{k} {v:,}" for k, v in fc.items()))

    # appointments not counted as given (cancelled, refixed, marked fake...), per ME
    NC = sorted((r for r in P["not_counted"] if r["to_date"] >= fy), key=lambda r: (r["to_date"], r["me"]))
    kinds = Counter(" ".join(str(r["disposition_name"] or "Not recorded").split()) for r in NC)
    KINDS = [k for k, _ in kinds.most_common()]
    nc = {"n": len(NC), "d": [], "me": [], "tme": [], "k": []}
    nc_co, nc_pid = [], []
    for r in NC:
        nc["d"].append((r["to_date"] - fy).days); nc["me"].append(P["me_ix"](r["me"])); nc["tme"].append(P["tme_ix"](r["tme"]))
        nc["k"].append(KINDS.index(" ".join(str(r["disposition_name"] or "Not recorded").split())))
        nc_co.append(str(r["companyname"] or "").strip()[:60]); nc_pid.append(str(r["parentid"] or ""))
    log(f"Not counted as given: {len(NC):,} ({', '.join(f'{k} {v:,}' for k, v in kinds.most_common(6))})")

    # HR: days present per ME and month, joining date, designation, home city
    hp = os.path.join(PIPE, "cache", "hr.pkl")
    city_l = str(raw["city"]).strip().lower()
    months, hr_days, hr_j, hr_des, hr_city, hr_mis = [], [], [], [], [], []
    if os.path.exists(hp):
        hr = pickle.load(open(hp, "rb"))
        months = [f"{y}-{m:02d}" for y, m in hr["months"]]
        for code, _name in MES:
            c = str(code).strip()
            mm = hr["master"].get(c)
            for y, m in hr["months"]:
                v = hr["days"].get((c, y, m))
                hr_days.append(65535 if v is None else int(round(v[0] * 10)))
                # does the Sales MIS count this ME's deals in this city that month? (fetch_deals.py MIS_SQL: the month's
                # HR row city + emptype ME, else the HR master's city) 1 yes, 0 no (another city), 2 not known
                if v is not None:
                    hr_mis.append(1 if v[3].strip().lower() == city_l and v[2].strip().upper() == "ME" else 0)
                else:
                    hr_mis.append(2 if not mm or not mm[4] else 1 if mm[4].strip().lower() == city_l else 0)
            hr_j.append(mm[0].isoformat() if mm and mm[0] else "")
            hr_des.append(tidy(mm[3]) if mm else "")
            hr_city.append(tidy(mm[4]) if mm else "")
        log(f"HR: {sum(1 for v in hr_j if v):,} of {len(MES):,} MEs with a joining date")
    else:
        log("hr.pkl is missing from the cache folder (run fetch_deals.py): no days present or tenure on the page.")

    # grade: me_grade on the ME's latest appointment (it changes with promotions)
    last_grade = {}
    for r in sorted(list(P["rows"]) + list(P["not_counted"]), key=lambda r: r["to_date"]):
        g = tidy(r.get("me_grade") or "")
        if g:
            last_grade[str(r["me"]).strip()] = g
    hr_grade = [last_grade.get(str(code).strip(), "") for code, _name in MES]
    n_att = sum(1 for x in recs if x[5] <= 2)
    DL = P["deals"]   # deals closed, Sales MIS rule (records.py): (day, me, mgr or -1, TME team, dc_genio)
    n_deal = round(sum(x[4] for x in DL), 2)
    log(f"Appointments {len(recs):,} (left out: {bad}); attended {n_att:,}; deals closed {n_deal:,.2f} "
        f"({sum(1 for x in recs if x[5] == 0):,} appointments with disposition Dealclosed)")
    if bad > len(P["rows"]) * 0.01:
        sys.exit("More than 1% of appointments have an unknown outcome; the page was not changed.")

    assert sys.byteorder == "little"
    def pack(code, values):
        return base64.b64encode(array(code, values).tobytes()).decode()
    data = {
        "meta": {"city": tidy(raw["city"]), "fy": fy.isoformat(), "end": end.isoformat(), "days": D_end + 1,
                 "refreshed": raw["pulled"].strftime("%Y-%m-%dT%H:%M"),
                 "provisional": [d.isoformat() for d in P.get("provisional", [])],
                 "check": {"given": len(recs), "attended": n_att, "deals": n_deal, "left_out": bad, "flags": dict(fc)},
                 "dealSrc": deal_src, "naEarlyMin": NA_EARLY_MIN, "pendingDays": PENDING_DAYS, "months": months,
                 "hrPulled": pickle.load(open(hp, "rb"))["pulled"].strftime("%Y-%m-%d") if months else ""},
        "mes": MES, "mgrs": MGRS, "mgUp": mg_up, "tmes": TMES, "teams": TEAMS,
        "a": {"n": len(recs), "d": pack("H", [x[0] for x in recs]), "me": pack("H", [x[1] for x in recs]),
              "mg": pack("H", [x[2] for x in recs]), "tme": pack("H", [x[3] for x in recs]),
              "tt": pack("B", [x[4] for x in recs]), "o": pack("B", [x[5] for x in recs]), "rl": pack("B", later),
              "f": pack("B", flags), "sl": pack("i", sl), "bk": pack("i", bk), "en": pack("i", en), "dc": pack("i", dc)},
        "co": [x[6] for x in recs], "pid": [x[7] for x in recs],
        "dl": {"n": len(DL), "d": pack("H", [x[0] for x in DL]), "me": pack("H", [x[1] for x in DL]),
               "mg": pack("H", [x[2] if x[2] >= 0 else 65535 for x in DL]), "tt": pack("B", [x[3] for x in DL]),
               "w": pack("f", [x[4] for x in DL]), "pid": [x[5] for x in DL]},
        "nc": {"n": nc["n"], "d": pack("H", nc["d"]), "me": pack("H", nc["me"]), "tme": pack("H", nc["tme"]), "k": pack("B", nc["k"]),
               "kinds": KINDS, "co": nc_co, "pid": nc_pid},
        "hr": {"days": pack("H", hr_days), "j": hr_j, "des": hr_des, "city": hr_city, "grade": hr_grade, "mis": pack("B", hr_mis)},
    }
    assert len(MES) < 65536 and len(TMES) < 65536 and len(MGRS) < 65535 and len(TEAMS) < 256 and len(KINDS) < 256
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    log(f"Data: {len(blob) / 1e6:.1f} MB; {len(MES):,} MEs, {len(TMES):,} TMEs")

    MARK = '<script type="application/json" id="data">'
    if "--full" not in sys.argv and os.path.exists(PAGE):
        page = open(PAGE, encoding="utf-8").read()
        fmt = re.search(r'<meta name="jd-data-format" content="(\d+)">', page)
        if not fmt or int(fmt.group(1)) != DATA_FORMAT or MARK not in page:
            sys.exit(f"{os.path.basename(PAGE)} needs a different data format; rebuild it with --full. The page has not been changed.")
        start = page.index(MARK) + len(MARK)
        page = page[:start] + blob + page[page.index("</script>", start):]
        how = "data updated; design kept"
    else:
        shell = open(os.path.join(APP, "shell.tpl"), encoding="utf-8").read()
        css = open(os.path.join(APP, "app.css"), encoding="utf-8").read()
        js = open(os.path.join(APP, "app.js"), encoding="utf-8").read()
        fonts = ""
        for f in sorted(os.listdir(FONTS)):
            mm = re.match(r"(.+)-(\d{3}|var)\.woff2$", f)
            if mm:
                weight = "100 900" if mm.group(2) == "var" else mm.group(2)
                fonts += (f"@font-face{{font-family:'{mm.group(1)}';font-style:normal;font-weight:{weight};font-display:swap;"
                          f"src:url(data:font/woff2;base64,{base64.b64encode(open(os.path.join(FONTS, f), 'rb').read()).decode()}) format('woff2');}}")
        logo = "data:image/png;base64," + base64.b64encode(open(LOGO, "rb").read()).decode()
        page = shell.replace("/*FONTS*/", fonts).replace("/*CSS*/", css).replace("/*LOGO*/", logo).replace("/*DATA*/", blob).replace("/*JS*/", js)
        page = page.replace("<head>", f'<head>\n<meta name="jd-data-format" content="{DATA_FORMAT}">', 1)
        how = "built from the design files"
    tmp = PAGE + ".tmp"
    open(tmp, "w", encoding="utf-8").write(page)
    os.replace(tmp, PAGE)
    log(f"Wrote {PAGE} ({len(page) / 1e6:.1f} MB, {how})")


if __name__ == "__main__":
    sys.exit(main())
