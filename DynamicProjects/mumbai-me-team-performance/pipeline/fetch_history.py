"""Past paid deals of the appointments' businesses (server 216, read-only), for the skewness card's 'own client' rule.

25 Nov 2026, the user: the skewness factor should leave out the ME's own clients ("isn't that fair"). An appointment is the ME's
own client when the business has a paid deal (dc_genio > 0) closed by the same ME at least 15 days before the appointment.
Deals from 1 Jan 2024 (the deals table starts there). Mumbai only (the card exists only on the sounak.biswas page).

Reads   cache\\raw.pkl (+ cache\\api_rows.pkl, the provisional days)
Writes  cache\\own_hist.pkl  {"pulled": datetime, "deals": {parentid: [(dealclosed_date, closer code without leading zeros), ...]}}
"""
import datetime
import os
import pickle
import sys
import time

import pymysql

import kitpaths
from fetch_deals import load_env, CACHE, TABLE, CITY_CODE


def main():
    if not kitpaths.SKEW_PAGE:
        print("not needed for this city (no skewness card)"); return 0
    raw = pickle.load(open(os.path.join(CACHE, "raw.pkl"), "rb"))
    ix = raw["cols"].index("parentid")
    pids = {str(r[ix]).strip() for r in raw["rows"] if r[ix]}
    ap = os.path.join(CACHE, "api_rows.pkl")
    if os.path.exists(ap):
        api = pickle.load(open(ap, "rb")); j = api["cols"].index("parentid")
        pids |= {str(r[j]).strip() for r in api["rows"] if r[j]}
    pids = sorted(pids)
    code = CITY_CODE.get(str(raw["city"]).lower(), "")
    env = load_env(); t0 = time.time()
    c = pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_PORT") or 3306), user=env["MYSQL_USER"],
                        password=env["MYSQL_PASSWORD"], connect_timeout=15, read_timeout=600)
    cur = c.cursor(); out = {}
    for i in range(0, len(pids), 1000):
        ch = pids[i:i + 1000]; ph = ",".join(["%s"] * len(ch)); docs = [code + p for p in ch] if code else ch
        cur.execute(f"""SELECT TRIM(parentid), TRIM(docid), dealclosed_date, TRIM(IFNULL(me, ''))
                        FROM {TABLE} WHERE (parentid IN ({ph}) OR TRIM(docid) IN ({ph})) AND dealclosed_date >= '2024-01-01' AND dc_genio > 0""",
                    ch + docs)
        for pid, doc, d, me in cur.fetchall():
            key = pid if pid in ch else (doc[len(code):] if code and doc and doc.startswith(code) else pid)
            out.setdefault(key, []).append((d, me.lstrip("0")))
    c.close()
    tmp = os.path.join(CACHE, "own_hist.pkl.tmp")
    pickle.dump({"pulled": datetime.datetime.now(), "deals": out}, open(tmp, "wb")); os.replace(tmp, os.path.join(CACHE, "own_hist.pkl"))
    print(f"own clients: {len(pids):,} businesses, {len(out):,} with paid deals since Jan 2024 ({sum(len(v) for v in out.values()):,} deals), "
          f"{time.time() - t0:.0f}s. Saved cache\\own_hist.pkl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
