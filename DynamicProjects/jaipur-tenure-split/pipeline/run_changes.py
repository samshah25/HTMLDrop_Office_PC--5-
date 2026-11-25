"""What changed between two refreshes (user, 24 Nov 2026: track the morning run against the afternoon run, as for the Mumbai ME
dashboard, fix what is fixable, keep what is learnt). Compares the newest snapshot in data/run_snapshots with the one before
it (or two given names), only on the days both covered, and sorts every change:
  deals   added late for an earlier day / removed / moved day / jda_flag changed / team changed / TME or closer changed /
          deal count changed / RV changed / branch changed; plus the new days (expected)
  appts   appointments given changed / attended changed (per day, TME, ME, flag) on days both had
  hr      active days revised for a closed month / role or team changed / person added or dropped
  pres    presentations changed on days both had;  dialer: trunk minutes changed on days both had
  page    every page figure whose window has the same dates in both runs and moved by more than 0.1%
Writes checks/run_changes/<new>_vs_<old>.csv (every changed row) and adds one line per class to checks/run_changes/log.csv.
    python checks/run_changes.py                   # newest vs the one before
    python checks/run_changes.py snap_A snap_B     # B (newer) vs A"""
import os, sys, pickle, datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); TG = os.path.dirname(HERE)
KIT = os.path.exists(os.path.join(HERE, "kitpaths.py"))           # shared kit: snapshots and reports in the private folder
if KIT: sys.path.insert(0, HERE); import kitpaths  # noqa: E401,E702
SD = os.path.join(kitpaths.DATA if KIT else os.path.join(TG, "data"), "run_snapshots")
OUT = kitpaths.CHANGES if KIT else os.path.join(HERE, "run_changes"); os.makedirs(OUT, exist_ok=True)
names = sorted(f for f in os.listdir(SD) if f.startswith("snap_"))
if len(sys.argv) > 2: old_n, new_n = [n if n.endswith(".pkl") else n + ".pkl" for n in sys.argv[1:3]]
elif len(names) >= 2: old_n, new_n = names[-2], names[-1]
else: sys.exit("run_changes: fewer than two snapshots, nothing to compare yet")
O, N = (pickle.load(open(os.path.join(SD, n), "rb")) for n in (old_n, new_n))
D = lambda s: datetime.date.fromisoformat(s) if s else datetime.date.min
lo = max(min(O["deals"].day, default=datetime.date.min), min(N["deals"].day, default=datetime.date.min))
rows = []                                   # section, class, day, key, before, after


def add(sec, cls, day, key, b, a):
    rows.append((sec, cls, str(day), key, b, a))


# ---------------- deals: row by row (parentid + version, numbered when a key repeats)
def keyed(df):
    df = df[df.day >= lo].copy(); df["k"] = df.parentid.astype(str) + "|" + df.version.astype(str)
    df["k"] = df.k + "#" + df.groupby("k").cumcount().astype(str)
    return df.set_index("k")


od, nd = keyed(O["deals"]), keyed(N["deals"]); o_to = D(O["meta"]["deals_to"])
for k in nd.index.difference(od.index):
    r = nd.loc[k]
    add("deals", "added late for an earlier day" if r.day <= o_to else "new day", r.day, k, None, f"flag {r.jda_flag} dc {r.dc_genio} rv {r.RV_3yr:.0f}")
for k in od.index.difference(nd.index):
    r = od.loc[k]; add("deals", "removed", r.day, k, f"flag {r.jda_flag} dc {r.dc_genio} rv {r.RV_3yr:.0f}", None)
for k in od.index.intersection(nd.index):
    a, b = od.loc[k], nd.loc[k]
    for col, cls in (("day", "moved day"), ("jda_flag", "jda_flag changed"), ("team", "team changed"), ("city", "branch changed"),
                     ("tme", "TME changed"), ("me", "closer changed"), ("dc_genio", "deal count changed")):
        if str(a[col]) != str(b[col]): add("deals", cls, a.day, k, str(a[col]), str(b[col]))
    if abs(float(a.RV_3yr) - float(b.RV_3yr)) > 1: add("deals", "RV changed", a.day, k, round(float(a.RV_3yr)), round(float(b.RV_3yr)))

# ---------------- appointments: per day, TME, ME, flag, on days both runs had
a_to = min(D(O["meta"]["appts_to"]), D(N["meta"]["appts_to"]))
def ap(df):
    df = df[(df.day >= lo) & (df.day <= a_to)].assign(n=lambda t: t.n.astype(float), att_n=lambda t: t.n.astype(float) * t.att.astype(float))
    return df.groupby(["day", "tme", "me", "jda_flag"])[["n", "att_n"]].sum()
oa, na = ap(O["appts"]), ap(N["appts"]); j = oa.join(na, how="outer", lsuffix="_o", rsuffix="_n").fillna(0.0)
for (day, tme, me, jf), r in j.iterrows():
    if r.n_o != r.n_n: add("appts", "given changed", day, f"{tme}>{me} flag {jf}", r.n_o, r.n_n)
    elif r.att_n_o != r.att_n_n: add("appts", "attended changed", day, f"{tme}>{me} flag {jf}", r.att_n_o, r.att_n_n)

# ---------------- HR: per person-month-role
def hrk(df): return df.assign(active_days=df.active_days.astype(float)).groupby(["ym", "code"]).agg(days=("active_days", "sum"), role=("emptype", "first"), team=("team", "first"))
oh, nh = hrk(O["hr"]), hrk(N["hr"]); cur = max(nh.index.get_level_values(0), default=0)
for (ym, code), r in oh.join(nh, how="outer", lsuffix="_o", rsuffix="_n").iterrows():
    if pd.isna(r.days_o) or pd.isna(r.days_n):
        if ym < cur: add("hr", "person added" if pd.isna(r.days_o) else "person dropped", ym, code, r.days_o, r.days_n)
        continue
    if (r.role_o, r.team_o) != (r.role_n, r.team_n): add("hr", "role or team changed", ym, code, f"{r.role_o}/{r.team_o}", f"{r.role_n}/{r.team_n}")
    if ym < cur and r.days_o != r.days_n: add("hr", "active days revised (closed month)", ym, code, r.days_o, r.days_n)

# ---------------- presentations and dialer on days both had
for sec, key, col, to in (("pres", ["code", "day"], "pres", "pres_to"), ("dialer", ["agent", "day"], "trunk", "dialer_to")):
    t = min(D(O["meta"][to]), D(N["meta"][to]))
    f = lambda df: df[(df.day >= lo) & (df.day <= t)].groupby(key)[col].sum().astype(float)
    jj = pd.concat([f(O[sec]), f(N[sec])], axis=1, keys=["o", "n"]).fillna(0.0)
    for k, r in jj[jj.o != jj.n].iterrows():
        add(sec, f"{col} changed", k[1], str(k[0]), r.o, r.n)

# ---------------- page figures with the same window dates in both runs
for k, v in N["page"].items():
    if k in O["page"]:
        b = O["page"][k]
        if b and abs(v / b - 1) > 0.001: add("page", "figure moved", f"{k[0]} {k[1][0]}..{k[1][1]}", f"{k[2]} / {k[3]}", b, v)

df = pd.DataFrame(rows, columns=["section", "class", "day", "key", "before", "after"])
tag = f"{new_n[5:-4]}_vs_{old_n[5:-4]}"
df.to_csv(os.path.join(OUT, f"{tag}.csv"), index=False, encoding="utf-8-sig")
summ = df.groupby(["section", "class"]).size().rename("rows").reset_index()
# deals: what the changes do to deal totals on the days both runs had (home branch, deal city)
dd = lambda s: float(s[(s.city == "Jaipur") & (s.day <= o_to) & (s.day >= lo) & (s.dc_genio > 0)].dc_genio.sum())
log = summ.assign(old=old_n[5:-4], new=new_n[5:-4], old_pulled=O["meta"]["pulled"], new_pulled=N["meta"]["pulled"])
lf = os.path.join(OUT, "log.csv")
log.to_csv(lf, mode="a", header=not os.path.exists(lf), index=False, encoding="utf-8-sig")
print(f"run changes {new_n} vs {old_n}: pulled {O['meta']['pulled']} -> {N['meta']['pulled']}; data end {O['meta']['data_end']} -> {N['meta']['data_end']}")
print(f"  sources old {[O['meta'][k] for k in ('deals_to', 'appts_to', 'dialer_to', 'pres_to', 'hr_max_days_this_month')]}")
print(f"  sources new {[N['meta'][k] for k in ('deals_to', 'appts_to', 'dialer_to', 'pres_to', 'hr_max_days_this_month')]}")
print(f"  deals on the days both had (deal city): {dd(O['deals']):,.1f} -> {dd(N['deals']):,.1f}")
print(summ.to_string(index=False) if len(summ) else "  no changes")
