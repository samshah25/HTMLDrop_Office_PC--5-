"""Appointment pincodes from the allocation API (read-only 'fetch' pipelines), for the 'where the leads go' section of the
skewness card (26 Nov 2026, the user: show how Super Cat reaches the Super Cat-heavy MEs, on the sounak.biswas page only).

Each TME appointment (allocationType 25) carries the appointment's pincode. Only contractCode, allocationTime, actionTime and
pincode are read (no names, contacts or addresses). Only the cities with the card (kitpaths.SKEW_PAGE: Mumbai, Ahmedabad since
26 Nov 2026).

Where: the city's own partition of the API (all its records by week), then the other partitions for the businesses still
missing (by contractCode). 26 Nov 2026: Ahmedabad's branch covers all of Gujarat and the API keeps Surat, Vadodara, Rajkot
and the other cities in the 'remote' partition: the own partition alone found 37% of Ahmedabad's appointments (Ahmedabad
city 97%, every other city 0-1%); 97% of the missing ones are in 'remote'. (Until 26 Nov the partition was hard-coded
"mumbai" and only the own partition was read; Mumbai's own partition found 89%.)

Reads   cache\\raw.pkl (+ cache\\api_rows.pkl, the provisional days): the FY's first day, the data end, the appointments' businesses
Writes  cache\\pins\\<yyyymm>.v2.pkl (by allocation month; closed months are kept, the current and the previous month are pulled
        again each run; the older <yyyymm>.pkl files, own partition only, are no longer read)
        cache\\pins.pkl  {"pulled": datetime, "fix": {parentid: [(allocation date, appointment date, pincode), ...]}}
"""
import datetime
import os
import pickle
import sys
import time

import kitpaths
from fetch_api import api, PARTITIONS

CACHE = kitpaths.CACHE
PROJ = {"$project": {"_id": 0, "contractCode": 1, "allocationTime": 1, "actionTime": 1, "pincode": 1}}
CHUNK = 500


def rows_of(recs):
    return [(str(r.get("contractCode") or "").strip(), str(r.get("allocationTime") or "")[:10], str(r.get("actionTime") or "")[:10],
             str(r.get("pincode") or "").strip()) for r in recs if r.get("contractCode") and r.get("pincode")]


def own_pull(m0, m1):
    """the city's own partition: every TME appointment record allocated in [m0, m1), a week at a time"""
    out, d = [], m0
    while d < m1:
        n = min(d + datetime.timedelta(days=7), m1)
        out += api([{"$match": {"allocationType": 25, "allocationTime": {"$gte": f"{d} 00:00:00", "$lt": f"{n} 00:00:00"}}}, PROJ], kitpaths.CITY)
        d = n
    return rows_of(out)


def other_pull(m0, m1, pids):
    """the other partitions: only these businesses' TME appointment records allocated in [m0, m1)"""
    out, by = [], {}
    for part in [p for p in PARTITIONS if p != kitpaths.CITY]:
        got = []
        for i in range(0, len(pids), CHUNK):
            got += api([{"$match": {"allocationType": 25, "contractCode": {"$in": pids[i:i + CHUNK]},
                                    "allocationTime": {"$gte": f"{m0} 00:00:00", "$lt": f"{m1} 00:00:00"}}}, PROJ], part)
        got = rows_of(got); out += got
        if got:
            by[part] = len(got)
    return out, by


def appointment_days():
    """{parentid: [appointment dates]} of the page's data (the appointment table + the provisional days)"""
    pd_ = {}
    for name in ("raw.pkl", "api_rows.pkl"):
        p = os.path.join(CACHE, name)
        if not os.path.exists(p):
            continue
        x = pickle.load(open(p, "rb")); C = x["cols"]; i, j = C.index("parentid"), C.index("to_date")
        for r in x["rows"]:
            pid, d = str(r[i] or "").strip(), r[j]
            if pid and d:
                d = d.date() if isinstance(d, datetime.datetime) else d if isinstance(d, datetime.date) else datetime.date.fromisoformat(str(d)[:10])
                pd_.setdefault(pid, []).append(d)
    return pd_


def main():
    if not kitpaths.SKEW_PAGE:
        print("not needed for this city (no skewness card)"); return 0
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    fy, end = raw["fy"], raw["end"]
    folder = os.path.join(CACHE, "pins"); os.makedirs(folder, exist_ok=True)
    t0 = time.time(); today = datetime.date.today()
    keep_from = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)   # the previous month and later: pulled again
    m = (fy - datetime.timedelta(days=31)).replace(day=1)                            # a month before the FY: fixes ahead of early appointments
    appts = None
    rows, pulled, n_own, n_other, parts = [], 0, 0, 0, {}
    while m <= end:
        nxt = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        p = os.path.join(folder, f"{m:%Y%m}.v2.pkl")
        if os.path.exists(p) and m < keep_from:
            c = pickle.load(open(p, "rb"))
        else:
            m1 = min(nxt, end + datetime.timedelta(days=2))
            own = own_pull(m, m1)
            # businesses with an appointment this allocation month could serve (the page matches a fix up to 30 days before)
            if appts is None:
                appts = appointment_days()
            hi = nxt + datetime.timedelta(days=31); have = {r[0] for r in own}
            miss = sorted(pid for pid, ds in appts.items() if pid not in have and any(m <= d < hi for d in ds))
            other, by = other_pull(m, m1, miss) if miss else ([], {})
            c = {"own": len(own), "other": len(other), "parts": by, "rows": own + other}
            pulled += 1
            tmp = p + ".tmp"; pickle.dump(c, open(tmp, "wb")); os.replace(tmp, p)
        rows += c["rows"]; n_own += c["own"]; n_other += c["other"]
        for k, v in c["parts"].items():
            parts[k] = parts.get(k, 0) + v
        m = nxt
    fix = {}
    for pid, a, d, pin in rows:
        fix.setdefault(pid, []).append((a, d, pin))
    tmp = os.path.join(CACHE, "pins.pkl.tmp")
    pickle.dump({"pulled": datetime.datetime.now(), "fix": fix}, open(tmp, "wb")); os.replace(tmp, os.path.join(CACHE, "pins.pkl"))
    print(f"pincodes: {len(rows):,} TME appointment records for {len(fix):,} businesses ({n_own:,} from the {kitpaths.CITY} partition, "
          f"{n_other:,} from the others: {', '.join(f'{k} {v:,}' for k, v in sorted(parts.items(), key=lambda kv: -kv[1])) or 'none'}; "
          f"{pulled} month(s) pulled, {time.time() - t0:.0f}s). Saved cache\\pins.pkl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
