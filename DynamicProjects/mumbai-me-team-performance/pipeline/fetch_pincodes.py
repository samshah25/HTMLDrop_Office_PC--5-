"""Appointment pincodes from the allocation API (read-only 'fetch' pipelines), for the 'where the leads go' section of the
skewness card (26 Nov 2026, the user: show how Super Cat reaches the Super Cat-heavy MEs, on the sounak.biswas page only).

Each TME appointment (allocationType 25) carries the appointment's pincode. Only contractCode, allocationTime, actionTime and
pincode are read (no names, contacts or addresses). Mumbai only (the card exists only on the sounak.biswas page).

Reads   cache\\raw.pkl (the financial year's first day and the data end)
Writes  cache\\pins\\<yyyymm>.pkl (closed months are kept; the current and the previous month are pulled again each run)
        cache\\pins.pkl  {"pulled": datetime, "fix": {parentid: [(allocation date, appointment date, pincode), ...]}}
"""
import datetime
import os
import pickle
import sys
import time

import kitpaths
from fetch_api import api

CACHE = kitpaths.CACHE


def month_pull(m0, m1):
    out = []
    d = m0
    while d < m1:
        n = min(d + datetime.timedelta(days=7), m1)
        out += api([{"$match": {"allocationType": 25, "allocationTime": {"$gte": f"{d} 00:00:00", "$lt": f"{n} 00:00:00"}}},
                    {"$project": {"_id": 0, "contractCode": 1, "allocationTime": 1, "actionTime": 1, "pincode": 1}}], "mumbai")
        d = n
    return [(str(r.get("contractCode") or "").strip(), str(r.get("allocationTime") or "")[:10], str(r.get("actionTime") or "")[:10],
             str(r.get("pincode") or "").strip()) for r in out if r.get("contractCode") and r.get("pincode")]


def main():
    if not kitpaths.SKEW_PAGE:
        print("not needed for this city (no skewness card)"); return 0
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    fy, end = raw["fy"], raw["end"]
    folder = os.path.join(CACHE, "pins"); os.makedirs(folder, exist_ok=True)
    t0 = time.time(); today = datetime.date.today()
    keep_from = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)   # the previous month and later: pulled again
    m = (fy - datetime.timedelta(days=31)).replace(day=1)                            # a month before the FY: fixes ahead of early appointments
    rows, pulled = [], 0
    while m <= end:
        nxt = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        p = os.path.join(folder, f"{m:%Y%m}.pkl")
        if os.path.exists(p) and m < keep_from:
            rows += pickle.load(open(p, "rb"))
        else:
            r = month_pull(m, min(nxt, end + datetime.timedelta(days=2))); rows += r; pulled += 1
            tmp = p + ".tmp"; pickle.dump(r, open(tmp, "wb")); os.replace(tmp, p)
        m = nxt
    fix = {}
    for pid, a, d, pin in rows:
        fix.setdefault(pid, []).append((a, d, pin))
    tmp = os.path.join(CACHE, "pins.pkl.tmp")
    pickle.dump({"pulled": datetime.datetime.now(), "fix": fix}, open(tmp, "wb")); os.replace(tmp, os.path.join(CACHE, "pins.pkl"))
    print(f"pincodes: {len(rows):,} TME appointment records for {len(fix):,} businesses ({pulled} month(s) pulled, {time.time() - t0:.0f}s). Saved cache\\pins.pkl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
