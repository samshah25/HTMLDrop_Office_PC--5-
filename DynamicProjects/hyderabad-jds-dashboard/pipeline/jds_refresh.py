r"""
Pull Hyderabad JDS (TME & ME) data into pipeline\jds_data.json.

Sources:
- Deals: ops_analytics.tbl_modified_deal_level_data (sales_branch='Hyderabad', dc_genio > 0, fresh IN (0,1),
  excluding JDA [final_team_type_name='JDA' or jda_flag=3] and Self Signup [jda_flag=10 / Anonymous]).
- Categories & Sales Groups: vertical_owner.tbl_company_vertical_mapping_SB joined on docid.
- Employee Names (TME & ME): db_paidcontracts.hr_all_daily_copy_ganesh (one-time lookup per unknown empcode).
- Geography: pipeline\pincode_city_data_city_branch.xlsx (Branch == "Hyderabad", TS districts + AP cities).

Counting rule:
- Total DocIDs = COUNT(DISTINCT docid) dynamically computed in the browser across any tenure, channel,
  area, Fresh/Renewal, ECS/Non-ECS, or B2B/B2C filter.
- RV & Collection weighted by min(dc_genio, 1.0) so joint JDA+JDS deals credit JDS's exact 0.5 share.
"""
import csv
import datetime
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
BRANCH = "Hyderabad"
WINDOW_END = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
REF_PATH = os.path.join(PIPE_DIR, "pincode_city_data_city_branch.xlsx")
ENV_PATH = os.path.join(PIPE_DIR, "db_216.env")
PRIVATE_ENV = os.path.join(os.path.expanduser("~"), ".hyd_jds_dashboard", "db_216.env")
SHARED_ENV = os.path.join(os.path.expanduser("~"), ".hyd_jda_dashboard", "db_216.env")
SIBLING_ENV = os.path.normpath(os.path.join(PIPE_DIR, "..", "..", "hyderabad-jda-dashboard", "pipeline", "db_216.env"))
CACHE_PATH = os.path.join(PIPE_DIR, "jds_cache.json.gz")
OUT_PATH = os.path.join(PIPE_DIR, "jds_data.json")
LOG_PATH = os.path.join(PIPE_DIR, "refresh_log.txt")
RECHECK_DAYS = 14

MODIFIED_DEALS = "`ops_analytics`.`tbl_modified_deal_level_data`"
CAT_MAP = "`vertical_owner`.`tbl_company_vertical_mapping_SB`"
HR = "`db_paidcontracts`.`hr_all_daily_copy_ganesh`"

MAIN_CITY = "Hyderabad"
TS_DISTRICT = {
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

CAT_LABELS = {
    "construction & real estate": "Construction & RE",
    "b2b": "B2B & Industrial",
    "home services": "Home Services",
    "healthcare": "Healthcare",
    "education": "Education",
    "beauty & fitness": "Beauty & Fitness",
    "events & weddings": "Events & Weddings",
    "automobiles": "Automobiles",
    "food & dining": "Food & Dining",
    "travel & transport": "Travel & Transport",
    "accommodation": "Accommodation",
    "electronics": "Electronics",
    "jdmart": "JDMart",
    "logistics & shipping": "Logistics",
    "shopping": "Shopping & Retail",
    "fashion": "Fashion & Apparel",
    "business & financial services": "Finance & Business",
    "entertainment": "Entertainment",
    "personal services": "Personal Services",
    "agriculture": "Agriculture",
    "pets": "Pets & Animals",
    "government & public services": "Govt & Public",
    "home & living": "Home & Living",
    "other": "Other",
    "no category": "No Category",
}


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def find_env():
    for p in (ENV_PATH, PRIVATE_ENV, SHARED_ENV, SIBLING_ENV):
        if os.path.exists(p):
            return p
    return None


def load_env(path):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def db_connect(env):
    import pymysql
    return pymysql.connect(
        host=env["DB_HOST"], port=int(env.get("DB_PORT", 3306)),
        user=env["DB_USER"], password=env["DB_PASS"],
        connect_timeout=20, read_timeout=300,
    )


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def clean_emp(v):
    s = str(v or "").strip()
    return "" if s in ("", "0", "999999999", "\\N", "NULL", "None") else s


def pretty_cat(name, fallback="Other"):
    raw = " ".join(str(name or "").split()).strip()
    if not raw or raw in ("\\N", "NULL", "None", "0"):
        return fallback
    low = raw.lower()
    if low in CAT_LABELS:
        return CAT_LABELS[low]
    return raw.title() if raw == low else raw


def parse_hot_cat(s):
    t = str(s or "").strip()
    if "|##|" in t:
        t = t.split("|##|", 1)[1].strip()
    return "" if t.lower() in ("", "\\n", "null", "none", "0") else t


def fy_mmdd(ds):
    m, d = int(ds[5:7]), int(ds[8:10])
    return (m if m >= 4 else m + 12) * 100 + d


def year_back(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def iter_dates(a, b):
    cur = a
    while cur <= b:
        yield cur
        cur += datetime.timedelta(days=1)


def date_span_chunks(dates, max_days=31):
    if not dates:
        return []
    dates = sorted(set(dates))
    chunks, start, prev = [], dates[0], dates[0]
    for d in dates[1:]:
        if (d - prev).days > 1 or (d - start).days >= max_days:
            chunks.append((start.isoformat(), prev.isoformat()))
            start = d
        prev = d
    chunks.append((start.isoformat(), prev.isoformat()))
    return chunks


def load_geo():
    """Return {pincode: area_idx}, areas=[{name, state, main}], fallback_idx."""
    import openpyxl
    rows = openpyxl.load_workbook(REF_PATH, read_only=True, data_only=True)["Sheet1"].iter_rows(values_only=True)
    h = next(rows)
    ip, idc, ib = h.index("Pincode"), h.index("Data City"), h.index("Branch")
    pin_area = {}
    for r in rows:
        if str(r[ib] or "").strip() != BRANCH or r[ip] is None:
            continue
        pin = str(r[ip]).strip().split(".")[0]
        if len(pin) != 6 or not pin.isdigit():
            continue
        dc = " ".join(str(r[idc] or "").split()).title()
        if pin.startswith("50"):
            name = TS_DISTRICT.get(dc, dc or "Telangana - Other")
            area = (name, "TS")
        elif pin[:2] in ("51", "52", "53"):
            area = (dc + " (AP)" if dc in TS_DISTRICT else dc or "Andhra - Other", "AP")
        else:
            area = (dc or "Other", "OT")
        pin_area[pin] = area

    names = sorted(set(pin_area.values()), key=lambda a: (
        {"TS": 0, "AP": 1, "OT": 2}[a[1]],
        TS_ORDER.index(a[0]) if a[0] in TS_ORDER else 99, a[0],
    ))
    idx = {a: i for i, a in enumerate(names)}
    areas = [{"name": n, "state": s, "main": int(s == "TS" and n == MAIN_CITY)} for n, s in names]
    # Add fallback buckets for unmapped pincodes
    def ensure_area(name, st, main=0):
        k = (name, st)
        if k not in idx:
            idx[k] = len(areas)
            areas.append({"name": name, "state": st, "main": main})
        return idx[k]
    fb = {
        "main": ensure_area("Hyderabad", "TS", 1),
        "ts": ensure_area("Telangana - Other", "TS", 0),
        "ap": ensure_area("Andhra - Other", "AP", 0),
        "ot": ensure_area("Other", "OT", 0),
    }
    return {p: idx[a] for p, a in pin_area.items()}, areas, fb


def resolve_area(pin, main_remote, pin_area, fb):
    p = str(pin or "").strip().split(".")[0]
    if p in pin_area:
        return pin_area[p]
    if str(main_remote or "").strip() == "1":
        return fb["main"]
    if p.startswith("50"):
        return fb["ts"]
    if p[:2] in ("51", "52", "53"):
        return fb["ap"]
    return fb["ot"]


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with gzip.open(CACHE_PATH, "rt", encoding="utf-8") as f:
                c = json.load(f)
            if isinstance(c, dict) and c.get("version") == 1 and isinstance(c.get("days"), dict):
                return c
        except Exception as e:
            log(f"WARNING: could not read {CACHE_PATH} ({e}); starting fresh cache.")
    return {"version": 1, "cats": [], "subcats": [], "channels": [], "emps": [], "docids": [], "days": {}}


def save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(cache, f, separators=(",", ":"))
    os.replace(tmp, CACHE_PATH)


def fill_emp_names(cache, name_map):
    updated = 0
    for item in cache.get("emps", []):
        code, cur_name = item[0], item[1]
        if code and (not cur_name or cur_name == code) and name_map.get(code):
            item[1] = name_map[code]
            updated += 1
    return updated


def fetch_hr_names_sql(env, codes):
    codes = sorted({c for c in codes if c})
    out = {}
    if not codes:
        return out
    conn = db_connect(env)
    with conn.cursor() as cur:
        for i in range(0, len(codes), 1000):
            ch = codes[i:i + 1000]
            ph = ",".join(["%s"] * len(ch))
            cur.execute(f"""SELECT TRIM(empcode), MAX(empname)
                            FROM {HR}
                            WHERE TRIM(empcode) IN ({ph})
                            GROUP BY TRIM(empcode)""", ch)
            for code, nm in cur.fetchall():
                c = str(code or "").strip()
                t = " ".join(str(nm or "").split()).title()
                if c and t:
                    out[c] = t
    conn.close()
    return out


def merge_rows_into_cache(cache, raw_rows, doc_cat, pin_area, fb, fetched_dates, name_map=None):
    """Aggregate JDS deals into compact daily records keyed by integer docid index.
    Row tuple: (ds, docid, pin, mr, fresh, ecs, b2b, jda_flag, channel, me, tme, dc, rv3, coll)."""
    name_map = name_map or {}
    cat_ix = {c: i for i, c in enumerate(cache["cats"])}
    sub_ix = {(cache["cats"][ci], s): i for i, (ci, s) in enumerate(cache["subcats"])}
    ch_ix = {c: i for i, c in enumerate(cache["channels"])}
    emp_ix = {e[0]: i for i, e in enumerate(cache["emps"])}
    doc_ix = {d: i for i, d in enumerate(cache["docids"])}

    def get_sub(cat, sub):
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

    def get_ch(ch):
        c = ch or "Other"
        i = ch_ix.get(c)
        if i is None:
            i = len(cache["channels"])
            cache["channels"].append(c)
            ch_ix[c] = i
        return i

    def get_emp(code):
        if not code:
            return -1
        ei = emp_ix.get(code)
        if ei is None:
            ei = len(cache["emps"])
            cache["emps"].append([code, name_map.get(code, "")])
            emp_ix[code] = ei
        elif not cache["emps"][ei][1] and name_map.get(code):
            cache["emps"][ei][1] = name_map[code]
        return ei

    def get_doc(docid):
        di = doc_ix.get(docid)
        if di is None:
            di = len(cache["docids"])
            cache["docids"].append(docid)
            doc_ix[docid] = di
        return di

    by_day = {ds: defaultdict(lambda: [0.0, 0.0]) for ds in fetched_dates}
    matched_docs, all_docs = set(), set()
    for ds, docid, pin, mr, fresh, ecs, b2b, fl, channel, me, tme, dc, rv3, coll in raw_rows:
        if ds not in fetched_dates or dc <= 0 or not docid:
            continue
        t_up = str(channel or "").strip().upper()
        fl_i = int(fl or 0)
        # JDS only: exclude JDA (final_team_type_name='JDA' or jda_flag=3) and Self Signup (jda_flag=10 / Anonymous)
        if t_up == "JDA" or fl_i in (3, 10) or t_up == "ANONYMOUS":
            continue
        me_c, tme_c = clean_emp(me), clean_emp(tme)
        if not me_c and not tme_c:
            continue
        # On joint JDA+JDS deals (jda_flag=2), me is the JDA partner, so keep me_i=-1 on JDS side
        me_i = -1 if fl_i == 2 else get_emp(me_c)
        tme_i = get_emp(tme_c)
        all_docs.add(docid)
        cinfo = doc_cat.get(docid)
        if cinfo:
            matched_docs.add(docid)
            cat = pretty_cat(cinfo[0], "No Category")
            sub = pretty_cat(cinfo[1], "Other")
        else:
            cat, sub = "Unmapped", "Unmapped"
        di = get_doc(docid)
        si = get_sub(cat, sub)
        ci_ch = get_ch(channel.strip() or "Other")
        ai = resolve_area(pin, mr, pin_area, fb)
        fr = 1 if str(fresh).strip() == "1" else 0
        ec = 1 if str(ecs).strip() == "1" else 0
        bb = 1 if str(b2b).strip() == "1" else 0
        # Bit-pack flags: bit0=fresh, bit1=ecs, bit2=b2b
        flags = fr | (ec << 1) | (bb << 2)
        w = min(dc, 1.0) if dc < 1.0 else 1.0
        acc = by_day[ds][(di, ai, si, ci_ch, flags, tme_i, me_i)]
        acc[0] += rv3 * w
        acc[1] += coll * w

    for ds, agg in by_day.items():
        cache["days"][ds] = [[di, ai, si, ci_ch, flags, tme_i, me_i, round(rv), round(cl)]
                             for (di, ai, si, ci_ch, flags, tme_i, me_i), (rv, cl) in sorted(agg.items())]
    return len(matched_docs), len(all_docs)


def prune_cache(cache, keep_from_iso):
    old = [ds for ds in cache["days"] if ds < keep_from_iso]
    for ds in old:
        del cache["days"][ds]
    return len(old)


def seed_from_csv(cache, pin_area, fb, seed_dir, name_map=None):
    pick = lambda *names: next((os.path.join(seed_dir, n) for n in names if os.path.exists(os.path.join(seed_dir, n))), "")
    f25 = pick("hyd_2025_deals_all.csv")
    f26 = pick("hyd_2026_deals_all.csv")
    fcat = pick("hyd_cat_group_deals_all.csv")
    fsg = pick("hyd_sales_group_deals_all.csv")
    if not (f25 and f26 and fcat):
        return False

    doc_sg = {}
    if fsg:
        sg_raw = defaultdict(dict)
        with open(fsg, encoding="utf-8-sig", errors="replace", newline="") as f:
            r = csv.reader(f)
            hdr = next(r)
            ix_d, ix_sg, ix_n = hdr.index("docid"), hdr.index("sales_group"), hdr.index("num_of_categories_in_sales_group")
            for row in r:
                if len(row) <= max(ix_d, ix_sg, ix_n):
                    continue
                did, sg, rn = row[ix_d].strip(), row[ix_sg].strip(), row[ix_n].strip()
                if not did or not sg or sg == "\\N":
                    continue
                n = int(rn) if rn.isdigit() else 0
                if sg not in sg_raw[did] or n > sg_raw[did][sg]:
                    sg_raw[did][sg] = n
        for did, mp in sg_raw.items():
            doc_sg[did] = sorted(mp.items(), key=lambda x: (-x[1], x[0]))[0][0]

    doc_cat = {}
    with open(fcat, encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        ix_d, ix_v, ix_sv = hdr.index("docid"), hdr.index("vertical"), hdr.index("sub_vertical")
        ix_tsg = hdr.index("top_sales_group_by_count") if "top_sales_group_by_count" in hdr else -1
        ix_hsg = hdr.index("hot_catinfo_sales_group") if "hot_catinfo_sales_group" in hdr else -1
        ix_hc = hdr.index("hot_cat_info") if "hot_cat_info" in hdr else -1
        for row in r:
            if len(row) <= max(ix_d, ix_v, ix_sv):
                continue
            did = row[ix_d].strip()
            if did and did not in doc_cat:
                v = row[ix_v].strip()
                tsg = row[ix_tsg].strip() if ix_tsg >= 0 and len(row) > ix_tsg else ""
                if tsg in ("0", "\\N", "NULL", "None"):
                    tsg = ""
                hsg = row[ix_hsg].strip() if ix_hsg >= 0 and len(row) > ix_hsg else ""
                if hsg in ("0", "\\N", "NULL", "None"):
                    hsg = ""
                hc = parse_hot_cat(row[ix_hc]) if ix_hc >= 0 and len(row) > ix_hc else ""
                sv = row[ix_sv].strip()
                doc_cat[did] = (v, doc_sg.get(did) or tsg or hsg or hc or sv)
    for did, sg in doc_sg.items():
        if did not in doc_cat:
            doc_cat[did] = ("Other", sg)

    def load_deals(path):
        out = []
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                dc = to_float(row.get("dc_genio"))
                if dc <= 0 or str(row.get("fresh") or "").strip() not in ("0", "1"):
                    continue
                fl = int(to_float(row.get("jda_flag")) or 0)
                ch = (row.get("final_team_type_name") or "").strip()
                if ch.upper() == "JDA" or fl in (3, 10) or ch.upper() == "ANONYMOUS":
                    continue
                ds = (row.get("dealclosed_date") or "").strip()[:10]
                if len(ds) == 10:
                    out.append((
                        ds, (row.get("docid") or "").strip(),
                        (row.get("pincode") or "").strip(), (row.get("branch_main_remote") or "").strip(),
                        (row.get("fresh") or "").strip(), (row.get("ecs_flag_original") or "").strip(),
                        (row.get("b2b") or "").strip(), fl, ch,
                        (row.get("me") or "").strip(), (row.get("tme") or "").strip(),
                        dc, to_float(row.get("rv_3yr")), to_float(row.get("collection")),
                    ))
        return out

    ly_rows, ty_rows = load_deals(f25), load_deals(f26)
    fetched = set()
    for rows in (ly_rows, ty_rows):
        if rows:
            ds_list = sorted(r[0] for r in rows)
            for d in iter_dates(datetime.date.fromisoformat(ds_list[0]), datetime.date.fromisoformat(ds_list[-1])):
                fetched.add(d.isoformat())
    matched, n_docs = merge_rows_into_cache(cache, ly_rows + ty_rows, doc_cat, pin_area, fb, fetched, name_map=name_map)
    log(f"Seeded {CACHE_PATH} from CSVs ({seed_dir}): {len(fetched)} days, {n_docs} distinct JDS docids "
        f"({matched}/{n_docs} cat-matched), {len(cache['emps'])} TME/ME codes, {len(cache['channels'])} channels")
    return True


def update_cache_sql(cache, env, pin_area, fb, ty_start, ty_end, ly_start, ly_end, full=False, name_map=None):
    days_map = cache["days"]
    recheck_from = max(ty_start, ty_end - datetime.timedelta(days=RECHECK_DAYS - 1))
    if full:
        ly_need = list(iter_dates(ly_start, ly_end))
        ty_need = list(iter_dates(ty_start, ty_end))
    else:
        ly_need = [d for d in iter_dates(ly_start, ly_end) if d.isoformat() not in days_map]
        ty_need = [d for d in iter_dates(ty_start, ty_end) if d >= recheck_from or d.isoformat() not in days_map]

    changed = False
    need_dates = sorted(set(ly_need) | set(ty_need))
    if need_dates:
        chunks = date_span_chunks(need_dates)
        raw_rows = []
        for a, b in chunks:
            conn = db_connect(env)
            with conn.cursor() as cur:
                cur.execute(f"""SELECT dealclosed_date, TRIM(IFNULL(docid, '')),
                                       TRIM(IFNULL(pincode, '')), branch_main_remote, fresh,
                                       ecs_flag_original, b2b, jda_flag,
                                       TRIM(IFNULL(final_team_type_name, '')),
                                       TRIM(IFNULL(me, '')), TRIM(IFNULL(tme, '')),
                                       IFNULL(dc_genio, 0), IFNULL(rv_3yr, 0), IFNULL(collection, 0)
                                FROM {MODIFIED_DEALS}
                                WHERE dealclosed_date BETWEEN %s AND %s
                                  AND sales_branch = %s
                                  AND dc_genio > 0
                                  AND fresh IN (0, 1)
                                  AND UPPER(TRIM(IFNULL(final_team_type_name, ''))) NOT IN ('JDA', 'ANONYMOUS')
                                  AND IFNULL(jda_flag, 0) NOT IN (3, 10)""", (a, b, BRANCH))
                for day, docid, pin, mr, fresh, ecs, b2b, flag, ch, me, tme, dc, rv3, coll in cur.fetchall():
                    ds = day.isoformat() if hasattr(day, "isoformat") else str(day)[:10]
                    raw_rows.append((ds, docid, pin, mr, fresh, ecs, b2b, int(flag or 0), ch, me, tme,
                                     to_float(dc), to_float(rv3), to_float(coll)))
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
                                           MAX(TRIM(IFNULL(top_sales_group_by_count, ''))),
                                           MAX(TRIM(IFNULL(hot_catinfo_sales_group, ''))),
                                           MAX(TRIM(IFNULL(hot_cat_info, ''))),
                                           MAX(TRIM(IFNULL(sub_vertical, '')))
                                    FROM {CAT_MAP}
                                    WHERE docid IN ({ph})
                                    GROUP BY TRIM(docid)""", ch)
                    for did, v, tsg, hsg, hc, sv in cur.fetchall():
                        if did:
                            sub = (tsg if tsg and tsg != "0" else "") or hsg or parse_hot_cat(hc) or sv
                            doc_cat[did] = (v, sub)
            conn.close()

        fetched_isos = {d.isoformat() for d in need_dates}
        matched, n_docs = merge_rows_into_cache(cache, raw_rows, doc_cat, pin_area, fb, fetched_isos, name_map=name_map)
        pruned = prune_cache(cache, ly_start.isoformat())
        log(f"JDS SQL refresh: {len(ly_need)} LY + {len(ty_need)} TY days ({len(chunks)} chunk(s), "
            f"{n_docs} distinct docids from {len(raw_rows)} rows, {matched} cat-matched); pruned {pruned} old days")
        changed = True
    else:
        log("JDS SQL refresh: all TY and LY dates already cached.")

    missing_emps = [e[0] for e in cache.get("emps", []) if e[0] and (not e[1] or e[1] == e[0])]
    if missing_emps:
        try:
            hr_names = fetch_hr_names_sql(env, missing_emps)
            if fill_emp_names(cache, hr_names):
                log(f"HR names resolved: {len(hr_names)} of {len(missing_emps)} missing emp codes")
                changed = True
        except Exception as e:
            log(f"WARNING: HR name lookup failed ({type(e).__name__}: {e})")
    return changed


def build_json_from_cache(cache, areas, ty_start, ty_end, ly_start, ly_end, source):
    ly_a, ly_b = ly_start.isoformat(), ly_end.isoformat()
    ty_a, ty_b = ty_start.isoformat(), ty_end.isoformat()
    old_cats, old_subs = cache["cats"], cache["subcats"]
    old_chs, old_emps = cache["channels"], cache["emps"]

    cat_docs, sub_docs, ch_docs, emp_docs, area_docs = (
        defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    )
    agg_rows = []
    ly_dates, ty_dates = [], []
    used_docs = {}

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
        for di, ai, si, ci_ch, flags, tme_i, me_i, rv, cl in entries:
            ci, sub = old_subs[si]
            cat = old_cats[ci]
            ch = old_chs[ci_ch]
            ndi = used_docs.get(di)
            if ndi is None:
                ndi = len(used_docs)
                used_docs[di] = ndi
            tme_k = tuple(old_emps[tme_i]) if 0 <= tme_i < len(old_emps) else None
            me_k = tuple(old_emps[me_i]) if 0 <= me_i < len(old_emps) else None
            cat_docs[cat].add((yr, ndi))
            sub_docs[(cat, sub)].add((yr, ndi))
            ch_docs[ch].add((yr, ndi))
            area_docs[ai].add((yr, ndi))
            if tme_k:
                emp_docs[tme_k].add((yr, ndi))
            if me_k:
                emp_docs[me_k].add((yr, ndi))
            agg_rows.append((yr, mmdd, ndi, ai, cat, sub, ch, flags, tme_k, me_k, rv, cl))

    if not ly_dates or not ty_dates:
        return None

    tail_cats = {"No Category", "Unmapped"}
    cats = sorted(cat_docs, key=lambda c: (1 if c in tail_cats else 0, -len(cat_docs[c]), c))
    cat_ix = {c: i for i, c in enumerate(cats)}
    sub_keys = sorted(sub_docs, key=lambda cs: (cat_ix[cs[0]], -len(sub_docs[cs]), cs[1]))
    sub_ix = {cs: i for i, cs in enumerate(sub_keys)}
    subcats = [[cat_ix[c], s] for c, s in sub_keys]

    channels = sorted(ch_docs, key=lambda c: (-len(ch_docs[c]), c))
    ch_ix = {c: i for i, c in enumerate(channels)}

    emp_keys = sorted(emp_docs, key=lambda ce: (-len(emp_docs[ce]), ce[1] or ce[0]))
    emp_ix = {ce: i for i, ce in enumerate(emp_keys)}
    emps = [[code, ename] for code, ename in emp_keys]

    used_areas = sorted(area_docs, key=lambda a: (
        0 if areas[a]["main"] else (1 if areas[a]["state"] == "TS" else 2),
        -len(area_docs[a]), areas[a]["name"],
    ))
    area_ix = {a: i for i, a in enumerate(used_areas)}
    out_areas = [areas[a] for a in used_areas]

    packed = [
        [yr, mmdd, ndi, area_ix[ai], sub_ix[(cat, sub)], ch_ix[ch], flags,
         emp_ix[tme_k] if tme_k else -1, emp_ix[me_k] if me_k else -1, rv, cl]
        for yr, mmdd, ndi, ai, cat, sub, ch, flags, tme_k, me_k, rv, cl in agg_rows
    ]

    c_start_k = max(fy_mmdd(ty_dates[0]), fy_mmdd(ly_dates[0]))
    c_end_k = min(fy_mmdd(ty_dates[-1]), fy_mmdd(ly_dates[-1]))
    fmt_k = lambda k: f"{(k // 100 - (12 if k // 100 > 12 else 0)):02d}-{k % 100:02d}"
    common_start, common_end = fmt_k(c_start_k), fmt_k(c_end_k)

    log(f"Built JDS JSON ({source}): {len(cats)} categories, {len(subcats)} sub-categories, {len(channels)} channels, "
        f"{len(out_areas)} areas, {len(emps)} TME/MEs, {len(used_docs)} distinct docids, {len(packed)} rows | "
        f"common {common_start}..{common_end}")
    return {
        "meta": {
            "branch": BRANCH,
            "generated": f"{datetime.datetime.now():%Y-%m-%d %H:%M}",
            "source": source,
            "mode": "distinct_docid",
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
        },
        "areas": out_areas,
        "channels": channels,
        "cats": cats,
        "subcats": subcats,
        "emps": emps,
        "rows": packed,
    }


def load_known_names():
    """Opportunistically pick up employee names from sibling JDA dashboard JSON if present offline."""
    names = {}
    sib = os.path.normpath(os.path.join(PIPE_DIR, "..", "..", "hyderabad-jda-dashboard", "pipeline", "hyd_data.json"))
    if os.path.exists(sib):
        try:
            with open(sib, encoding="utf-8") as f:
                d = json.load(f)
            for r in d.get("reps", []):
                if r.get("id") and r.get("name"):
                    names[str(r["id"]).strip()] = r["name"]
            for m in d.get("mgrs", []):
                if len(m) >= 2 and m[0] and m[1]:
                    names[str(m[0]).strip()] = m[1]
            for e in (d.get("cat_deals") or {}).get("emps", []):
                if len(e) >= 2 and e[0] and e[1]:
                    names.setdefault(str(e[0]).strip(), e[1])
        except Exception:
            pass
    return names


def main():
    full = "--full-refresh" in sys.argv
    seed_dir = sys.argv[sys.argv.index("--seed-dir") + 1] if "--seed-dir" in sys.argv else None
    pin_area, areas, fb = load_geo()
    env_file = find_env()
    env = load_env(env_file) if env_file else None
    name_map = load_known_names()

    end_d = datetime.date.fromisoformat(WINDOW_END)
    fy_year = end_d.year if end_d.month >= 4 else end_d.year - 1
    ty_start, ty_end = datetime.date(fy_year, 4, 1), end_d
    ly_start, ly_end = datetime.date(fy_year - 1, 4, 1), year_back(end_d)

    cache = {"version": 1, "cats": [], "subcats": [], "channels": [], "emps": [], "docids": [], "days": {}} if seed_dir else load_cache()
    changed = fill_emp_names(cache, name_map) > 0

    if (not cache["days"] or seed_dir) and not full:
        sdir = seed_dir or os.path.join(PIPE_DIR, "raw_data")
        if os.path.isdir(sdir) and seed_from_csv(cache, pin_area, fb, sdir, name_map=name_map):
            prune_cache(cache, ly_start.isoformat())
            changed = True

    source = "cache"
    if env:
        try:
            if update_cache_sql(cache, env, pin_area, fb, ty_start, ty_end, ly_start, ly_end, full=full, name_map=name_map):
                changed = True
            source = "sql"
        except Exception as e:
            log(f"WARNING: JDS SQL refresh failed ({type(e).__name__}: {e}); using cached data.")

    if changed:
        save_cache(cache)

    payload = build_json_from_cache(cache, areas, ty_start, ty_end, ly_start, ly_end, source)
    if not payload:
        sys.exit("No JDS data loaded. Provide pipeline\\db_216.env or run with --seed-dir <csv folder>.")

    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    os.replace(tmp, OUT_PATH)
    log(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
