"""Step 2 of the refresh: turn cache\\raw.pkl into the dashboard page (one self-contained .html).

Geography: state, district, place and location from GeoNames (first entry per pincode); branch and city from the
pincode -> branch reference file (pincode membership, as in the Kolkata, Mumbai and Pan India JDA dashboards). Every
number is computed here or in the page from the pulled data; nothing is estimated.

    python build_dashboard.py          data only: swaps the data inside the existing page, keeps its design
    python build_dashboard.py --full   rebuilds the page from the design files in pipeline\\app
"""
import base64
import csv
from array import array
import datetime
import json
import math
import os
import pickle
import re
import sys
from collections import Counter, defaultdict

import openpyxl

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
REF = os.path.join(PIPE, "reference")
APP = os.path.join(PIPE, "app")
DEFAULT_PAGE = "jd-india-sales-overview.html"
# What the page expects from this pipeline. Raise it whenever the page needs data an older pipeline does not make;
# a refresh then refuses to put old-format data into the newer page (and says so) instead of breaking it.
DATA_FORMAT = 4   # 2: unique customers (pincode x day x customer id); 3: map district per pincode (cols.dm); 4: big deals one by one

# channel of a deal from jda_flag: 1 JDA, 2 joint (half each), 3 B2B, 10 anonymous, anything else JDS
CHANNELS = ["JDA", "JDS", "B2B", "Anonymous"]
SPLIT = {1: ((0, 1.0),), 2: ((0, 0.5), (1, 0.5)), 3: ((2, 1.0),), 10: ((3, 1.0),)}


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def tidy(name):
    """'CHANDIGARH' / 'coimbatore' -> 'Chandigarh' / 'Coimbatore'; mixed case is kept as written."""
    name = " ".join(str(name or "").split())
    return name.title() if name.isupper() or name.islower() else name


STATE_NAMES = {"Pondicherry": "Puducherry", "Jammu & Kashmir": "Jammu and Kashmir",
               "Andaman & Nicobar Islands": "Andaman and Nicobar Islands"}


def dashboard_file():
    """The page to write: JDA_DASH_OUT if set; else the one .html in the kit folder (it may have been renamed for
    hosting); else the default name."""
    if os.environ.get("JDA_DASH_OUT"):
        return os.environ["JDA_DASH_OUT"]
    pages = sorted(f for f in os.listdir(KIT) if f.lower().endswith(".html"))
    return os.path.join(KIT, pages[0] if len(pages) == 1 else DEFAULT_PAGE)


# GeoNames district names that the district map spells differently or that were renamed (normalised, lower case,
# letters only). Keyed by (state, name) where the same old name exists in two states.
DISTRICT_ALIAS = {
    "allahabad": "prayagraj", "faizabad": "ayodhya", "gurgaon": "gurugram", "bengaluru": "bengaluruurban",
    "bangalore": "bengaluruurban", "bangalorerural": "bengalururural", "mohali": "sasnagar", "nawanshahr": "shahidbhagatsinghnagar",
    "ropar": "rupnagar", "jyotibaphulenagar": "amroha", "santravidasnagar": "bhadohi", "westnimar": "khargone", "eastnimar": "khandwa",
    "kvrangareddy": "rangareddy", "eastmidnapore": "purbamedinipur", "westmidnapore": "paschimmedinipur", "northdinajpur": "uttardinajpur",
    "southdinajpur": "dakshindinajpur", "tuticorin": "thoothukkudi", "cuddapah": "ysrkadapa", "kheri": "lakhimpurkheri",
    "baleswar": "balasore", "pondicherry": "puducherry", "warangal": "warangalurban", "kachchh": "kutch", "sibsagar": "sivasagar",
    "palamau": "palamu", "muktsar": "srimuktsarsahib", "firozpur": "ferozepur", "panchmahals": "panchmahal", "mahesana": "mehsana",
    "khorda": "khordha", "kanker": "uttarbastarkanker", "dantewada": "dakshinbastardantewada", "northcacharhills": "dimahasao",
    "thedangs": "dang", "debagarh": "deogarh", "sonapur": "subarnapur", "kawardha": "kabeerdham", "keonjhargarh": "kendujhar",
    "thenilgiris": "nilgiris", "paraganassouth": "southparganas", "paraganasnorth": "northparganas",   # digits are dropped
    ("Maharashtra", "raigarh"): "raigad",
}


def map_districts(C, STATES, geo):
    """Each pincode's district on the page's district map (app/india_districts.json), only among its own state's districts.
    Main source: India Post's pincode directory (reference/pincode_district_indiapost.csv: current district names and
    post office locations). GeoNames is only a fallback: it has old districts (no Palghar) and gives many pincodes a
    placeholder location shared with others (all of Bengaluru's 560xxx sit on one point).
      1. a state with one district on the map: that district;
      2. India Post's district name, matched to the map's (renames above, then a unique prefix or a close spelling);
      3. India Post's post office location: the district it lies in (on the coast or a border, the nearest);
      4. a GeoNames location no other pincode shares, then GeoNames' district name, then any GeoNames location;
      5. the usual district of the other pincodes in the same city. Else -1 (not known)."""
    import difflib
    DM = json.load(open(os.path.join(APP, "india_districts.json"), encoding="utf-8"))
    rings = [[list(zip(r[0::2], r[1::2])) for r in rs] for rs in DM["r"]]
    box = [(min(x for r in rs for x, _ in r), min(y for r in rs for _, y in r), max(x for r in rs for x, _ in r), max(y for r in rs for _, y in r)) for rs in rings]
    by_state = defaultdict(list)
    for i, s in enumerate(DM["s"]):
        by_state[s].append(i)
    norm = lambda s: re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", (s or "").lower()))
    shared = Counter((g[3], g[4]) for g in geo.values() if g[3] is not None)
    ipost = {}
    ip_file = os.path.join(REF, "pincode_district_indiapost.csv")
    if os.path.exists(ip_file):
        for r in csv.DictReader(open(ip_file, encoding="utf-8")):
            ipost[r["pincode"]] = (r["district"], float(r["lat"]) if r["lat"] else None, float(r["lon"]) if r["lon"] else None)
    else:
        log("pincode_district_indiapost.csv is missing from the reference folder: districts come from GeoNames only (less exact).")

    def inside(x, y, rs):
        c = False
        for r in rs:
            j = len(r) - 1
            for i in range(len(r)):
                xi, yi = r[i]; xj, yj = r[j]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    c = not c
                j = i
        return c

    def by_place(cand, lat, lon):
        hit = [i for i in cand if box[i][0] <= lon <= box[i][2] and box[i][1] <= lat <= box[i][3] and inside(lon, lat, rings[i])]
        return hit[0] if hit else min(cand, key=lambda i: min((lon - x) ** 2 + (lat - y) ** 2 for r in rings[i] for x, y in r))

    name_memo = {}
    def by_name(st, cand, raw_name):
        key = (st, raw_name)
        if key not in name_memo:
            k = norm(raw_name)
            k = DISTRICT_ALIAS.get((st, k), DISTRICT_ALIAS.get(k, k))
            d = None
            if k:
                ex = [c for c in cand if norm(DM["n"][c]) == k]
                # a name that starts the other counts only when the two are close in length ("Bagalkot" / "Bagalkote",
                # not "The Nilgiris" / "Theni")
                pre = [c for c in cand if (norm(DM["n"][c]).startswith(k) or k.startswith(norm(DM["n"][c])))
                       and min(len(k), len(norm(DM["n"][c]))) >= .7 * max(len(k), len(norm(DM["n"][c])))]
                if ex:
                    d = ex[0]
                elif len(pre) == 1:
                    d = pre[0]
                else:
                    sc = sorted(((difflib.SequenceMatcher(None, k, norm(DM["n"][c])).ratio(), c) for c in cand), reverse=True)
                    if sc and sc[0][0] >= .75 and (len(sc) < 2 or sc[0][0] - sc[1][0] >= .08):
                        d = sc[0][1]
            name_memo[key] = d
        return name_memo[key]

    out, how = [], Counter()
    for k in range(len(C["pin"])):
        st = STATES[C["st"][k]]
        cand = by_state.get(st, [])
        g, ip = geo.get(C["pin"][k]), ipost.get(C["pin"][k])
        lat, lon = (g[3], g[4]) if g else (None, None)
        d, why = -1, ""
        if len(cand) == 1:
            d, why = cand[0], "only district"
        elif cand and ip and by_name(st, cand, ip[0]) is not None:
            d, why = by_name(st, cand, ip[0]), "India Post district"
        elif cand and ip and ip[1] is not None:
            d, why = by_place(cand, ip[1], ip[2]), "India Post location"
        elif cand and lat is not None and shared[(lat, lon)] < 3:
            d, why = by_place(cand, lat, lon), "GeoNames own location"
        elif cand and g and by_name(st, cand, g[1]) is not None:
            d, why = by_name(st, cand, g[1]), "GeoNames district"
        elif cand and lat is not None:
            d, why = by_place(cand, lat, lon), "GeoNames shared location"
        if why:
            how[why] += 1
        out.append(d)
    # still unknown: the usual district of the other pincodes in the same city and state
    city_d = defaultdict(Counter)
    for k, d in enumerate(out):
        if d >= 0:
            city_d[(C["ci"][k], C["st"][k])][d] += 1
    for k, d in enumerate(out):
        if d < 0 and city_d[(C["ci"][k], C["st"][k])]:
            out[k] = city_d[(C["ci"][k], C["st"][k])].most_common(1)[0][0]; how["by city"] += 1
    how["not known"] = sum(1 for d in out if d < 0)
    log("Districts for pincodes: " + ", ".join(f"{k} {v:,}" for k, v in how.items()))

    # where each pincode's dot is drawn: the first of these that lies inside the pincode's district - India Post's main
    # office, a GeoNames location of its own, GeoNames' shared (approximate) location. If none does, India Post's (or
    # GeoNames') location when it is within 10 km of the district (a border drawn simpler than it is); farther than that
    # the location is wrong in the source and the dot is not drawn (its deals still count everywhere).
    def km_out(lat, lon, rs):
        best = 1e9
        for r in rs:
            for i in range(len(r)):
                (x1, y1), (x2, y2) = r[i - 1], r[i]
                dx, dy = x2 - x1, y2 - y1
                L = dx * dx + dy * dy
                t = 0 if L == 0 else max(0, min(1, ((lon - x1) * dx + (lat - y1) * dy) / L))
                best = min(best, ((lon - x1 - t * dx) * 111 * math.cos(math.radians(lat))) ** 2 + ((lat - y1 - t * dy) * 111) ** 2)
        return best ** .5
    how = Counter()
    for k in range(len(C["pin"])):
        ip, g, d = ipost.get(C["pin"][k]), geo.get(C["pin"][k]), out[k]
        own = [(ip[1], ip[2])] if ip and ip[1] is not None else []
        if g and g[3] is not None and shared[(g[3], g[4])] < 3:
            own.append((g[3], g[4]))
        approx = [(g[3], g[4])] if g and g[3] is not None and shared[(g[3], g[4])] >= 3 else []
        if d < 0:
            pick = (own + approx or [None])[0]
            how["district not known"] += 1
        else:
            pick = next((c for c in own + approx if inside(c[1], c[0], rings[d])), None)
            if pick is not None:
                how["inside its district"] += 1
            elif own and km_out(own[0][0], own[0][1], rings[d]) <= 10:
                pick = own[0]; how["within 10 km of it"] += 1
            else:
                how["location not reliable, not drawn"] += 1
        C["lat"][k], C["lon"][k] = (round(pick[0], 3), round(pick[1], 3)) if pick else (None, None)
    log("Pincode dots: " + ", ".join(f"{k} {v:,}" for k, v in how.items()))
    return out


def main():
    raw = pickle.load(open(os.path.join(PIPE, "cache", "raw.pkl"), "rb"))
    end, fy, ly_from, ly_to = raw["end"], raw["fy"], raw["ly_from"], raw["ly_to"]
    months = []
    y, m = fy.year, fy.month
    while (y, m) <= (end.year, end.month):
        months.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    # last financial year, all 12 months (Apr..Mar), for the trend's comparison line
    ly_fy = [f"{fy.year - 1 + (mm < 4)}-{mm:02d}" for mm in list(range(4, 13)) + list(range(1, 4))]

    # ---- reference: pincode -> branch, city ----
    ref = {}
    ws = openpyxl.load_workbook(os.path.join(REF, "pincode_city_data_city_branch.xlsx"), read_only=True).active
    rows = ws.iter_rows(values_only=True)
    head = [str(h).strip() for h in next(rows)]
    ip, ic, idc, ib = head.index("Pincode"), head.index("City"), head.index("Data City"), head.index("Branch")
    for r in rows:
        p = str(r[ip] or "").strip()
        if p.isdigit() and len(p) == 6 and r[ib]:
            ref[p] = (tidy(r[ib]), tidy(r[idc] or r[ic]), tidy(r[ic]))

    # ---- GeoNames: place, district, state, lat, lon (first entry per pincode) ----
    geo = {}
    for line in open(os.path.join(REF, "geonames_IN.txt"), encoding="utf-8"):
        a = line.rstrip("\n").split("\t")
        if len(a) > 10 and a[1] not in geo:
            try:
                lat, lon = float(a[9]), float(a[10])
            except ValueError:
                lat = lon = None
            geo[a[1]] = (a[2], a[5], STATE_NAMES.get(a[3], a[3]), lat, lon)

    # ---- day records: (pincode, day offset, code) with code = channel * 4 + fresh * 2 + ecs ----
    D = (end - fy).days + 1
    TY, LY = defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0])
    deal_pins = set()
    for p, day, flag, fresh, ecs, n, rv in raw["deals"]:
        ty = day >= fy
        o = (day - (fy if ty else ly_from)).days
        deal_pins.add(p)
        for ch, w in SPLIT.get(flag, ((1, 1.0),)):
            rec = (TY if ty else LY)[(p, o, ch * 4 + fresh * 2 + ecs)]
            rec[0] += n * w
            rec[1] += rv * w
    REST = defaultdict(lambda: [0.0, 0.0])
    for p, ym, n, rv in raw["rest"]:
        deal_pins.add(p)
        if ym in ly_fy:
            rec = REST[(p, ly_fy.index(ym))]
            rec[0] += n
            rec[1] += rv
    # big deals (one customer on one day with RV 3yr of at least big_floor) come out of the groups above and go to the
    # page one by one with their size, so it can leave out deals above any amount picked
    BTY, BLY, BREST = [], [], []
    cust_amt = {}                      # (customer id, day) -> size of that customer's deal that day
    for p, day, flag, fresh, ecs, n, rv, amt, d in raw.get("big", []):
        deal_pins.add(p)
        if d >= 0:
            cust_amt[(d, day)] = amt
        if day >= fy or ly_from <= day <= ly_to:
            ty = day >= fy
            o = (day - (fy if ty else ly_from)).days
            for ch, w in SPLIT.get(flag, ((1, 1.0),)):
                code = ch * 4 + fresh * 2 + ecs
                rec = (TY if ty else LY)[(p, o, code)]
                rec[0] -= n * w
                rec[1] -= rv * w
                (BTY if ty else BLY).append((p, o, code, n * w, rv * w, amt))
        elif f"{day:%Y-%m}" in ly_fy:
            m = ly_fy.index(f"{day:%Y-%m}")
            rec = REST[(p, m)]
            rec[0] -= n
            rec[1] -= rv
            BREST.append((p, m, n, rv, amt))
    for recs in (TY, LY, REST):        # what is left of each group once its big deals are out
        neg = [k for k, v in recs.items() if v[0] < -0.005]
        if neg:
            sys.exit(f"{len(neg)} day groups went below zero when big deals were taken out (e.g. {neg[0]}); the page was not changed.")
        for k in [k for k, v in recs.items() if abs(v[0]) < 0.005 and abs(v[1]) < 0.5]:
            del recs[k]
    if raw.get("big"):
        log(f"Big deals (RV 3yr {raw['big_floor']:,.0f}+) kept one by one: {len(BTY):,} this year, {len(BLY):,} last year, "
            f"{len(BREST):,} in last year's other months")
    for p, day, d in raw["cust"]:
        deal_pins.add(p)
    for p, ym, d in raw["cust_rest"]:
        deal_pins.add(p)

    pins = sorted(deal_pins)
    row = {p: i for i, p in enumerate(pins)}
    assert len(pins) < 65536
    log(f"Pincodes with deals: {len(pins):,}; days this year: {D}")

    # state for pincodes GeoNames does not know: the usual state of the other pincodes in the same city
    city_state = defaultdict(Counter)
    for p in pins:
        if p in geo and p in ref:
            city_state[ref[p][1]][geo[p][2]] += 1

    prefix_state = {3: defaultdict(Counter), 2: defaultdict(Counter)}
    for gp, g in geo.items():
        if g[2] and not gp.startswith("194"):
            prefix_state[3][gp[:3]][g[2]] += 1
            prefix_state[2][gp[:2]][g[2]] += 1

    def state_of(p):
        if p.startswith("194"):   # Ladakh's pincodes (GeoNames files them under Jammu and Kashmir)
            return "Ladakh"
        if p in geo and geo[p][2]:
            return geo[p][2]
        if p in ref and city_state[ref[p][1]]:
            return city_state[ref[p][1]].most_common(1)[0][0]
        # a pincode's first digits are its postal region: take the state of the known pincodes that share them
        for n in (3, 2):
            if prefix_state[n][p[:n]]:
                return prefix_state[n][p[:n]].most_common(1)[0][0]
        return "State not known"

    def table():
        names, ix = [], {}
        def get(v):
            if v not in ix:
                ix[v] = len(names); names.append(v)
            return ix[v]
        return names, get
    STATES, st_ix = table()
    BRANCHES, br_ix = table()
    CITIES, ci_ix = table()
    DISTRICTS, di_ix = table()

    C = defaultdict(list)
    for p in pins:
        g = geo.get(p)
        br, city, refcity = ref.get(p, ("Not mapped", "Not mapped", ""))
        C["pin"].append(p)
        C["place"].append((g[0] if g else "") or refcity or city)
        C["dist"].append(di_ix(g[1] if g and g[1] else ""))
        C["st"].append(st_ix(state_of(p))); C["br"].append(br_ix(br)); C["ci"].append(ci_ix(city))
        C["lat"].append(round(g[3], 3) if g and g[3] is not None else None)
        C["lon"].append(round(g[4], 3) if g and g[4] is not None else None)

    # ---- map district of each pincode (the district borders drawn on the page) ----
    C["dm"] = map_districts(C, STATES, geo)

    # ---- packed as little-endian typed arrays (base64) ----
    assert sys.byteorder == "little"
    def pack(code, values):
        arr = array(code, values)
        assert arr.itemsize == {"B": 1, "H": 2, "I": 4}[code]
        return base64.b64encode(arr.tobytes()).decode()
    hund = lambda v: int(round(v * 100))    # deals in hundredths (dc_genio has two decimals; joint deals make halves)
    th = lambda v: max(0, int(round(v / 1000)))   # RV in rupees thousand

    def stream(recs, two_keys=False):
        keys = sorted(recs, key=lambda k: (row[k[0]],) + tuple(k[1:]))
        n = [hund(recs[k][0]) for k in keys]
        v = [th(recs[k][1]) for k in keys]
        out = {"n": len(keys), "r": pack("H", [row[k[0]] for k in keys]), "d": pack("H" if not two_keys else "B", [k[1] for k in keys]),
               "deals": pack("I", n), "rv": pack("I", v)}
        if not two_keys:
            out["k"] = pack("B", [k[2] for k in keys])
        return out
    ty_stream, ly_stream = stream(TY), stream(LY)
    rest_stream = stream(REST, two_keys=True)

    def big_stream(recs, month=False):
        recs = sorted(recs, key=lambda x: (row[x[0]],) + tuple(x[1:]))
        out = {"n": len(recs), "r": pack("H", [row[x[0]] for x in recs]), "d": pack("B" if month else "H", [x[1] for x in recs]),
               "deals": pack("I", [hund(x[-3]) for x in recs]), "rv": pack("I", [th(x[-2]) for x in recs]),
               "a": pack("I", [min(4294967295, int(round(x[-1]))) for x in recs])}
        if not month:
            out["k"] = pack("B", [x[2] for x in recs])
        return out
    big_ty, big_ly, big_rest = big_stream(BTY), big_stream(BLY), big_stream(BREST, month=True)

    # unique customers: (pincode, day, customer id) for this year and last year, (pincode, FY month, id) for the rest
    # each customer row carries the size of its deal when that deal is big (a = rupees; 0 = an ordinary deal), so the
    # page can leave the customer out when every deal it has there is above the amount picked
    def cust_stream(tuples):
        t = sorted(set(tuples))
        big_ix = [i for i, x in enumerate(t) if x[3] > 0]          # only the few big ones carry a size (ai = row, av = rupees)
        return {"n": len(t), "r": pack("H", [x[0] for x in t]), "d": pack("H", [x[1] for x in t]), "c": pack("I", [x[2] for x in t]),
                "ai": pack("I", big_ix), "av": pack("I", [min(4294967295, int(round(t[i][3]))) for i in big_ix])}
    amt = lambda d, day: cust_amt.get((d, day), 0)
    cust_ty = cust_stream((row[p], (day - fy).days, d, amt(d, day)) for p, day, d in raw["cust"] if day >= fy)
    cust_ly = cust_stream((row[p], (day - ly_from).days, d, amt(d, day)) for p, day, d in raw["cust"] if day < fy)
    # the rest of last year comes by day (older caches: by month); a customer-month is big only if all its deals were
    rest_t = {}
    for p, when, d in raw["cust_rest"]:
        ym = when if isinstance(when, str) else f"{when:%Y-%m}"
        if ym not in ly_fy:
            continue
        a = 0 if isinstance(when, str) else amt(d, when)
        key = (row[p], ly_fy.index(ym), d)
        rest_t[key] = a if key not in rest_t else (0 if rest_t[key] == 0 or a == 0 else min(rest_t[key], a))
    cust_rest = cust_stream(k + (a,) for k, a in rest_t.items())

    # ---- self-check: what the page will add up vs the table's own totals ----
    chk = {}
    for key, recs in (("ty", TY), ("ly", LY)):
        n = (sum(hund(v[0]) for v in recs.values()) + sum(hund(x[3]) for x in (BTY if key == "ty" else BLY))) / 100
        want = raw["totals"][key][0] - raw["dropped"][0 if key == "ty" else 1]
        chk[key] = {"deals": round(n, 1), "table": round(raw["totals"][key][0], 1), "noPincode": round(raw["dropped"][0 if key == "ty" else 1], 1),
                    "ok": abs(n - want) < 1}
        log(f"Self-check {key}: page {n:,.1f} deals; table {raw['totals'][key][0]:,.1f} less {raw['dropped'][0 if key == 'ty' else 1]:,.0f} "
            f"without a valid pincode -> {'OK' if chk[key]['ok'] else 'MISMATCH'}")
    for key, ty in (("ty", True), ("ly", False)):
        n = len({d for p, day, d in raw["cust"] if (day >= fy) == ty})
        want = raw["totals"].get(key + "_cust")
        chk[key]["customers"] = n
        chk[key]["ok"] = chk[key]["ok"] and n == want
        log(f"Self-check {key} customers: page {n:,}; table COUNT(DISTINCT docid) {want:,} -> {'OK' if n == want else 'MISMATCH'}")
    if not all(c["ok"] for c in chk.values()):
        sys.exit("Totals do not match the deals table; the page was not changed. See the lines above.")

    # ---- quick periods ----
    def q_start(d):
        return datetime.date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)
    first = end.replace(day=1)
    last_m_end = first - datetime.timedelta(days=1)
    tq = q_start(end)
    last_q_end = tq - datetime.timedelta(days=1)
    presets = [("fytd", "Financial year to date", fy, end), ("tm", "This month", first, end),
               ("lm", "Last month", last_m_end.replace(day=1), last_m_end), ("tq", "This quarter", tq, end),
               ("lq", "Last quarter", q_start(last_q_end), last_q_end)]
    seen, P = set(), []
    for k, label, a0, b0 in presets:
        if a0 < fy or (a0, b0) in seen:
            continue
        seen.add((a0, b0))
        P.append({"k": k, "label": label, "a": (a0 - fy).days, "b": (b0 - fy).days})

    data = {
        "meta": {
            "end": end.isoformat(), "fy": fy.isoformat(), "lyFrom": ly_from.isoformat(), "lyTo": ly_to.isoformat(),
            "days": D, "months": months, "lyFy": ly_fy, "presets": P, "channels": CHANNELS,
            "refreshed": raw["pulled"].strftime("%Y-%m-%dT%H:%M"), "check": chk, "nCust": raw["n_cust"],
            "bigFloor": raw.get("big_floor", 0),
        },
        "states": STATES, "branches": BRANCHES, "cities": CITIES, "districts": DISTRICTS, "cols": C,
        "ty": ty_stream, "ly": ly_stream, "rest": rest_stream,
        "custTy": cust_ty, "custLy": cust_ly, "custRest": cust_rest,
        "bigTy": big_ty, "bigLy": big_ly, "bigRest": big_rest,
    }
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    log(f"Data: {len(blob) / 1e6:.1f} MB; day records {ty_stream['n']:,} this year, {ly_stream['n']:,} last year; "
        f"last year's other months {rest_stream['n']:,}")

    # ---- page ----
    out = dashboard_file()
    MARK = '<script type="application/json" id="data">'
    if "--full" not in sys.argv and os.path.exists(out):
        page = open(out, encoding="utf-8").read()
        fmt = re.search(r'<meta name="jd-data-format" content="(\d+)">', page)
        if not fmt or int(fmt.group(1)) != DATA_FORMAT or MARK not in page:
            sys.exit(f"{os.path.basename(out)} needs data format {fmt.group(1) if fmt else 'unknown'}, but this pipeline makes "
                     f"format {DATA_FORMAT}. Ask Sarvesh for the matching pipeline files. The page has not been changed.")
        start = page.index(MARK) + len(MARK)
        stop = page.index("</script>", start)
        page = page[:start] + blob + page[stop:]
        how = "data updated; design kept"
    else:
        shell = open(os.path.join(APP, "shell.tpl"), encoding="utf-8").read()
        css = open(os.path.join(APP, "app.css"), encoding="utf-8").read()
        js = "\n".join(open(os.path.join(APP, f), encoding="utf-8").read() for f in ("core.js", "app.js"))
        fonts = ""
        fdir = os.path.join(APP, "fonts")
        for f in sorted(os.listdir(fdir)) if os.path.isdir(fdir) else []:
            mm = re.match(r"(.+)-(\d{3}|var)\.woff2$", f)   # Name-600.woff2, or Name-var.woff2 for a variable font
            if mm:
                weight = "100 900" if mm.group(2) == "var" else mm.group(2)
                fonts += (f"@font-face{{font-family:'{mm.group(1)}';font-style:normal;font-weight:{weight};font-display:swap;"
                          f"src:url(data:font/woff2;base64,{base64.b64encode(open(os.path.join(fdir, f), 'rb').read()).decode()}) format('woff2');}}")
        logo = "data:image/png;base64," + base64.b64encode(open(os.path.join(APP, "jd_logo.png"), "rb").read()).decode()
        borders = open(os.path.join(APP, "india_states.json"), encoding="utf-8").read()
        districts = open(os.path.join(APP, "india_districts.json"), encoding="utf-8").read()
        page = (shell.replace("/*FONTS*/", fonts).replace("/*CSS*/", css).replace("/*LOGO*/", logo)
                     .replace("/*BORDERS*/", borders).replace("/*DISTRICTS*/", districts).replace("/*DATA*/", blob).replace("/*JS*/", js))
        page = page.replace("<head>", f'<head>\n<meta name="jd-data-format" content="{DATA_FORMAT}">', 1)
        how = "built from the design files"
    tmp = out + ".tmp"
    open(tmp, "w", encoding="utf-8").write(page)
    os.replace(tmp, out)
    log(f"Wrote {out} ({len(page) / 1e6:.1f} MB, {how})")


if __name__ == "__main__":
    sys.exit(main())
