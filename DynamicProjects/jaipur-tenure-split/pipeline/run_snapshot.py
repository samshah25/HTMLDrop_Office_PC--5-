"""Save a snapshot of one refresh (user, 24 Nov 2026: "track the changes between morning run and the afternoon run", as for the
Mumbai ME dashboard). Run by main.py after t2_build. Writes data/run_snapshots/snap_<pull time>.pkl with:
  meta    pull time (deals.pkl's time), data end, how far each source goes (deals, appointments, dialer, presentations, HR days)
  page    the page's figures: every main window and its last-year / previous copy, every row, area All, tenure All
  deals   the home branch's deal rows (deal city, or closer on the home branch's HR list) from the first day of last month
  appts   the home branch's appointment rows (final_datacity) from the first day of last month
  hr      the home branch's HR rows for last month and this month (code, role, team, active days, Main / Remote)
  pres    presentations per person per day from the first day of last month (people on the home branch's HR list)
  dialer  the home branch's dialer per agent per day from the first day of last month
checks/run_changes.py compares two snapshots."""
import os, sys, json, pickle, datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(HERE, "kitpaths.py")):         # shared kit: data in the private folder
    sys.path.insert(0, HERE); import kitpaths; DATA = kitpaths.DATA  # noqa: E401,E702
else:
    DATA = os.path.join(HERE, "data")
OUTD = os.path.join(DATA, "run_snapshots"); os.makedirs(OUTD, exist_ok=True)
HOME = "Jaipur"
L = lambda n: pd.read_pickle(os.path.join(DATA, n + ".pkl"))
norm = lambda s: s.fillna("").astype(str).str.strip().str.lstrip("0")

pulled = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(DATA, "deals.pkl")))
G = json.load(open(os.path.join(DATA, "grid.json"), encoding="utf-8"))
end = datetime.date.fromisoformat(G["wins"]["MTD"][1])
start = (end.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)        # first day of last month

h = L("hr"); h["city"] = h.city.fillna("").str.strip().str.title(); h["code"] = norm(h.empcode)
h["ym"] = h.year_no.astype(int) * 100 + h.month_no.astype(int)
hh = h[(h.city == HOME) & (h.ym >= start.year * 100 + start.month)][["ym", "code", "emptype", "team", "active_days", "main_city_flag"]].reset_index(drop=True)
people = set(hh.code)

d = pd.concat([L("deals"), L("zero")], ignore_index=True)
d["day"] = pd.to_datetime(d.dealclosed_date).dt.date; d["city"] = d.city.fillna("").str.strip().str.title()
d["tme"] = norm(d.tme); d["me"] = norm(d.me)
d = d[(d.day >= start) & ((d.city == HOME) | d.me.isin(people))]
deals = d[["day", "parentid", "version", "city", "main_city_flag", "jda_flag", "team", "tme", "me", "dc_genio", "RV_3yr", "collection", "product"]].reset_index(drop=True)
for c in ("dc_genio", "RV_3yr", "collection"): deals[c] = pd.to_numeric(deals[c], errors="coerce").fillna(0).astype(float)

a = L("appts"); a["city"] = a.city.fillna("").str.strip().str.title(); a["day"] = pd.to_datetime(a.day).dt.date
a = a[(a.city == HOME) & (a.day >= start)].copy(); a["tme"] = norm(a.tme); a["me"] = norm(a.me)
appts = a[["day", "tme", "me", "tteam", "jda_flag", "main_city_flag", "att", "n"]].reset_index(drop=True)

p = L("pres"); p["day"] = pd.to_datetime(p.day).dt.date
pres = p[(p.day >= start) & p.code.astype(str).isin(people)].reset_index(drop=True)
dl = L("dialer"); dl["day"] = pd.to_datetime(dl.day).dt.date
dialer = dl[(dl.table_city == HOME.lower()) & (dl.day >= start)][["agent", "day", "calls", "trunk"]].reset_index(drop=True)

page = {}
MI = [m["id"] for m in G["metrics"]]
for wk, cube in G["cube"].items():
    for seg, areas in cube.items():
        for mi, v in enumerate(areas["All"][0]):
            if v is not None and v[0] is not None:
                page[(wk, tuple(G["wins"][wk][:2]), seg, MI[mi])] = v[0]
meta = {"pulled": pulled.isoformat(timespec="minutes"), "built": datetime.datetime.now().isoformat(timespec="minutes"), "data_end": end.isoformat(),
        "deals_to": str(max(d.day)) if len(d) else None, "appts_to": str(max(a.day)) if len(a) else None,
        "dialer_to": str(max(dialer.day)) if len(dialer) else None, "pres_to": str(max(pres.day)) if len(pres) else None,
        "hr_max_days_this_month": float(hh[hh.ym == hh.ym.max()].active_days.astype(float).max()) if len(hh) else None}
snap = {"meta": meta, "page": page, "deals": deals, "appts": appts, "hr": hh, "pres": pres, "dialer": dialer}
f = os.path.join(OUTD, f"snap_{pulled:%Y%m%d_%H%M}.pkl")
pickle.dump(snap, open(f, "wb"))
print("snapshot", os.path.basename(f), meta)
