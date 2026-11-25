"""Jaipur tenure grid: build the cube (period x team row x area x tenure x metric) from t1_fetch's data and write the page.
16 Nov 2026 rebuild (user's list): MTD / WTD / Q3 to date / YTD / Q1 / Q2, each with last year (same dates) and the
previous period (MoM / WoW / QoQ); Main / Remote for every row; headcount and contribution by tenure; managers and
their TLs; B2B as its own team; product mix and product RV / deal; branch working days. eNACH dropped (no source).

Rows (user, 16 Nov 2026: "B2B as its own team, JDA without B2B"):
  Super Cat / Hot Data / Online / Rest of the JDS teams   JDS deals (jda_flag 0, joint flag 2 at half) by the TME team on
                          the deal, TME tenure; per manday: the TMEs of that HR team (B2B team never in these rows)
  B2B team                every flag-3 deal, deal city; tenure of the B2B-team person on it (TME slot first, then the
                          closer); people = HR team B2B (HR books them all as JDA; since Oct most are TMEs in SSO)
  JDA = All Team JDA      flag 1 + half of flag 2, deal city, JDA tenure; JDAs outside the B2B team
  BDE (= JDS-ME)          flag 0 deals with a closer whose city is the branch that month, any deal city, ME tenure
  All Team JDS            flag 0 + half of flag 2 = Super Cat + Hot Data + Online + Rest of the JDS teams
  Branch                  every deal of the branch (all flags) = All Team JDA + All Team JDS + B2B + no salesperson
Area = the deal's Main/Remote flag (follows the TME) for deals, the appointment's flag for appointments, the person's
HR Main/Remote for mandays / headcount; Main + Remote = All.
Periods end on the data end (yesterday; daily refresh since 23 Nov 2026). Mandays inside a part-month window = the person's HR active days for the month x the share of
the branch's working days that fall in the window (HR has monthly days only). Working days = days the branch closed
deals (Sundays and holidays have none; checked against HR's highest active days per month)."""
import os, sys, json, datetime, pickle, collections, re
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
KIT = os.path.exists(os.path.join(HERE, "kitpaths.py"))           # shared kit (as the ME kit): code in pipeline\, data private
sys.path.insert(0, HERE if KIT else os.path.join(ROOT, "Branch review", "analysis"))
if KIT: import kitpaths  # noqa: E402
DATA = kitpaths.DATA if KIT else os.path.join(HERE, "data")
from exclusions import drop_excluded  # noqa: E402  (user-excluded deals; none in Jaipur)

OUT = kitpaths.PAGE if KIT else os.path.join(ROOT, "Jaipur", "reports", "jaipur-tenure-split.html")   # = the HTML Drop link name (user, 24 Nov 2026)
TEMPLATE = os.path.join(HERE, "grid_template.html")                  # kit: in pipeline\, beside this file
SSO_PKL = os.path.join(DATA, "sso.pkl")          # copies of 2 Jul, 7 Sep, 12 Oct 2026 (from Jaipur\pipeline)
HOME, SKIP = "Jaipur", {"Jaipur", "Kolkata"}
BRANCHES = ["Ahmedabad", "Bangalore", "Chandigarh", "Chennai", "Coimbatore", "Delhi", "Hyderabad", "Jaipur", "Kolkata", "Mumbai", "Pune"]
D = datetime.date
END = pd.to_datetime(pd.read_pickle(os.path.join(DATA, "deals.pkl")).dealclosed_date).max().date()   # last day with a deal
# data end = the day the deals table is loaded up to: its daily load (~10:50) brings yesterday, so the day before the load date
# (24 Nov 2026, user: "data updated till" must move even after a Sunday / holiday that has no deals)
_lp = os.path.join(DATA, "loads.pkl")
if os.path.exists(_lp):
    _ld = pd.read_pickle(_lp); _ld = _ld[_ld.table_name.str.lower() == "daily_deals_closed_dump"]
    if len(_ld) and pd.notna(_ld.update_time.iloc[0]):
        END = max(END, min(pd.to_datetime(_ld.update_time.iloc[0]).date() - datetime.timedelta(days=1),
                           datetime.date.today() - datetime.timedelta(days=1)))
FY = END.year if END.month >= 4 else END.year - 1
FYS = D(FY, 4, 1)
PRES_FROM = D(2026, 4, 16)                      # per-person presentation copies start 16 Apr 2026
DIAL_FROM = {"Jaipur": (FYS - datetime.timedelta(days=80)).replace(day=1)}   # t1: home branch dialer from 3 months before the FY
DIAL_FROM_DEFAULT = FYS
BUCKETS = ["0-3M", "3-6M", "6-12M", "1-2Y", "2-4Y", "4Y+"]
BKS = ["All"] + BUCKETS + ["unknown"]
TEAMS = ["Super Cat", "Hot Data", "Online"]
REST = "Rest of the JDS teams"
SEGS = ["Super Cat", "Hot Data", "Online", REST, "B2B", "JDA", "BDE", "All Team JDA", "All Team JDS", "Branch"]
AREAS = ["All", "Main", "Remote"]

# ------------------------------------------------------------------ periods
def ly(w): return (w[0].replace(year=w[0].year - 1), w[1].replace(year=w[1].year - 1))
def mshift(d, k):                                  # first of the month k months away
    y, m = divmod(d.year * 12 + d.month - 1 + k, 12); return D(y, m + 1, 1)
def mend(d): return mshift(d, 1) - datetime.timedelta(days=1)
QN = (END.month - 4) % 12 // 3 + 1                  # FY quarter of the data end
QS = mshift(FYS, 3 * (QN - 1))
MAIN = {"MTD": (END.replace(day=1), END), "WTD": (END - datetime.timedelta(days=END.weekday()), END), "QTD": (QS, END), "YTD": (FYS, END)}
PM = mshift(END.replace(day=1), -1)
PREV = {"MTD": (PM, min(END.replace(day=1) - datetime.timedelta(days=1), PM + datetime.timedelta(days=END.day - 1))),
        "WTD": tuple(x - datetime.timedelta(days=7) for x in MAIN["WTD"]),
        "QTD": (mshift(QS, -3), min(QS - datetime.timedelta(days=1), mshift(QS, -3) + (END - QS)))}
PLABEL = {"MTD": "MTD", "WTD": "WTD", "QTD": f"Q{QN} to date", "YTD": "YTD"}
PVNAME = {"MTD": "MoM", "WTD": "WoW", "QTD": "QoQ"}
QUARTERS = []
for i in range(1, QN):                              # finished quarters of this FY
    a_ = mshift(FYS, 3 * (i - 1)); MAIN[f"Q{i}"] = (a_, mend(mshift(a_, 2))); PREV[f"Q{i}"] = (mshift(a_, -3), a_ - datetime.timedelta(days=1))
    PLABEL[f"Q{i}"] = f"Q{i}"; PVNAME[f"Q{i}"] = "QoQ"; QUARTERS.append(f"Q{i}")
WINS = {}
for k, w in MAIN.items():
    WINS[k] = w; WINS[k + "_ly"] = ly(w)
    if k in PREV: WINS[k + "_pv"] = PREV[k]


def fmt_d(a, b):
    f = lambda x: f"{x.day} {x:%b}"
    return f"{f(a)} – {f(b)} {b.year}" if a.year == b.year else f"{f(a)} {a.year} – {f(b)} {b.year}"


def norm(s):
    return s.astype(str).str.strip().str.lstrip("0")


def bucket(t):
    return np.select([t.isna(), t < 3, t < 6, t < 12, t < 24, t < 48], ["unknown"] + BUCKETS[:5], default="4Y+")


def side(flag):
    return np.where(pd.to_numeric(flag, errors="coerce") == 1, "Main", "Remote")


# ------------------------------------------------------------------ deals and working days
d = drop_excluded(pd.concat([pd.read_pickle(os.path.join(DATA, "deals.pkl")), pd.read_pickle(os.path.join(DATA, "zero.pkl"))], ignore_index=True))
d["city"] = d.city.fillna("").str.strip().str.title(); d["dt"] = pd.to_datetime(d.dealclosed_date); d["day"] = d.dt.dt.date
d["ym"] = d.dt.dt.year * 100 + d.dt.dt.month
for c in ("dc_genio", "RV_3yr", "collection"): d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(float)

# working days: a day counts when the branch closed at least max(3, 15% of its median day that month) deals
dd = d[d.city.isin(BRANCHES) & (d.dc_genio > 0)].groupby(["city", "ym", "day"]).dc_genio.sum().reset_index()
dd["med"] = dd.groupby(["city", "ym"]).dc_genio.transform("median")
dd = dd[dd.dc_genio >= np.maximum(3, 0.15 * dd.med)]
WD = {c: set(g.day) for c, g in dd.groupby("city")}
WD_M = {(c, ym): len(g) for (c, ym), g in dd.groupby(["city", "ym"])}


def wd_in(city, a, b):
    return sorted(x for x in WD.get(city, ()) if a <= x <= b)


# ------------------------------------------------------------------ HR roster and joining dates
h = pd.read_pickle(os.path.join(DATA, "hr.pkl"))
h["code"] = norm(h.empcode); h["ym"] = h.year_no.astype(int) * 100 + h.month_no.astype(int); h["city"] = h.city.str.strip().str.title()
h["active_days"] = pd.to_numeric(h.active_days, errors="coerce").fillna(0)
h["team"] = h.team.fillna("").str.strip(); h["emptype"] = h.emptype.fillna("").str.strip()
CHECK_WD = h[h.city.isin(BRANCHES)].groupby(["city", "ym"]).active_days.max().to_dict()
h = h[h.active_days > 0].copy()
j = pd.read_pickle(os.path.join(DATA, "join.pkl")); j["code"] = norm(j.empcode)
j["doj"] = pd.to_datetime(j.date_of_joining.astype(str).replace({"0000-00-00 00:00:00": None, "0000-00-00": None, "None": None}), errors="coerce")
DOJ = j.dropna(subset=["doj"]).groupby("code").doj.min()
HCITY = j.assign(city=j.city.fillna("").astype(str).str.strip().str.title()).drop_duplicates("code").set_index("code").city.to_dict()
h0 = h[h.emptype == "ME"].sort_values("active_days", ascending=False).drop_duplicates(["code", "ym"])
MECITY = dict(zip(zip(h0.code, h0.ym), h0.city))      # the dashboard's JDS-ME branch = the ME's city that month
# role type: B2B team first (HR books them as JDA), then TME / JDA / ME
h["role"] = np.select([h.team.str.upper() == "B2B", h.emptype == "TME", h.emptype == "JDA", h.emptype == "ME"], ["B2B", "TME", "JDA", "ME"], "")
h = h[h.role != ""].copy()
h["mid"] = pd.to_datetime((h.ym * 100 + 15).astype(str), format="%Y%m%d")
h["bk"] = bucket((h.mid - h.code.map(DOJ)).dt.days / 30.4375)
h = h.sort_values("active_days", ascending=False)
h["primary"] = ~h.duplicated(["code", "ym", "role"])        # numerators and headcount once per person-month and role
ROLE = {r: set(zip(h[h.role == r].code, h[h.role == r].ym)) for r in ("TME", "ME", "JDA", "B2B")}


def bk_at(person, ym, when, role):
    t = (when - person.map(DOJ)).dt.days / 30.4375
    known = pd.Series([(p, y) in ROLE[role] for p, y in zip(person, ym)], index=person.index)
    return np.where(known, bucket(t), "unknown")


# ------------------------------------------------------------------ deal rows per team row
d["tme_c"] = norm(d.tme.fillna("")); d["me_c"] = norm(d.me.fillna("")); d["team"] = d.team.fillna("").str.strip()
d["ecs"] = (pd.to_numeric(d.ecs_flag_original, errors="coerce") == 1).astype(float)
d["jf"] = pd.to_numeric(d.jda_flag, errors="coerce")
d["prod"] = d["product"].fillna("").str.strip().str.lower().map({"package": "pk", "pdg": "pd"}).fillna("ot")
me = d[(d.jf == 0) & (d.me_c != "")].copy()                       # BDE = JDS-ME without B2B: flag 0, closer's branch that month
me["city"] = [MECITY.get((c, y)) or HCITY.get(c, "") for c, y in zip(me.me_c, me.ym)]
me = me[me.city.isin(BRANCHES)].assign(w=1.0, cogn=1.0); me["bk"] = bk_at(me.me_c, me.ym, me.dt, "ME"); me["owner"] = me.me_c
d = d[d.city.isin(BRANCHES)].copy(); jf = d.jf
jds = pd.concat([d[jf == 0].assign(w=1.0), d[jf == 2].assign(w=0.5)]); jds["bk"] = bk_at(jds.tme_c, jds.ym, jds.dt, "TME"); jds["cogn"] = 1.0; jds["owner"] = jds.tme_c
jda = pd.concat([d[jf == 1].assign(w=1.0), d[jf == 2].assign(w=0.5)]); jda["bk"] = bk_at(jda.me_c, jda.ym, jda.dt, "JDA"); jda["cogn"] = 0.0; jda["owner"] = jda.me_c
b2b = d[jf == 3].assign(w=1.0, cogn=1.0)
tb = pd.Series([(c, y) in ROLE["B2B"] for c, y in zip(b2b.tme_c, b2b.ym)], index=b2b.index)
mb = pd.Series([(c, y) in ROLE["B2B"] for c, y in zip(b2b.me_c, b2b.ym)], index=b2b.index)
b2b["owner"] = np.where(tb, b2b.tme_c, np.where(mb, b2b.me_c, ""))
b2b["bk"] = bk_at(b2b.owner, b2b.ym, b2b.dt, "B2B")
nos = d[~jf.isin([0, 1, 2, 3])].assign(w=1.0, cogn=0.0, bk="unknown", owner="")   # flag 10: no salesperson
tm = jds.team.where(jds.team.isin(TEAMS), REST)
parts = [jds.assign(seg=tm), b2b.assign(seg="B2B"), jda.assign(seg="JDA"), jda.assign(seg="All Team JDA"), me.assign(seg="BDE"),
         jds.assign(seg="All Team JDS")] + [p_.assign(seg="Branch") for p_ in (jds, jda, b2b, nos)]
x = pd.concat(parts, ignore_index=True)
x["area"] = side(x.main_city_flag)
x["deals"] = x.dc_genio * x.w; x["rv"] = x.RV_3yr * x.w; x["coll"] = x.collection * x.w
x["ed"] = x.deals * x.ecs; x["er"] = x.rv * x.ecs; x["cogd"] = x.deals * x.cogn
for p_ in ("pk", "pd", "ot"):
    x[p_ + "_d"] = np.where(x["prod"] == p_, x.deals, 0.0); x[p_ + "_r"] = np.where(x["prod"] == p_, x.rv, 0.0)
XCOLS = ["deals", "rv", "coll", "ed", "er", "cogd", "pk_d", "pk_r", "pd_d", "pd_r", "ot_d", "ot_r"]
x = x[["city", "day", "seg", "area", "bk"] + XCOLS]; x["dn"] = [t.toordinal() for t in x.day]

# ------------------------------------------------------------------ appointments (COG denominators)
a = pd.read_pickle(os.path.join(DATA, "appts.pkl"))
a["city"] = a.city.str.strip().str.title(); a["day"] = pd.to_datetime(a.day).dt.date; a["n"] = a.n.astype(float); a["att"] = a.att.astype(float)
a["ym"] = [t.year * 100 + t.month for t in a.day]; a["jf"] = pd.to_numeric(a.jda_flag, errors="coerce")
a["tme_c"] = norm(a.tme.fillna("")); a["me_c"] = norm(a.me.fillna("")); a["tteam"] = a.tteam.fillna("").str.strip()
a["natt"] = a.n * a.att; a["mid"] = pd.to_datetime((a.ym * 100 + 15).astype(str), format="%Y%m%d"); a["area"] = side(a.main_city_flag)
at = a[a.city.isin(BRANCHES)].copy()
a0 = at[at.jf == 0].copy(); a0["bk"] = bk_at(a0.tme_c, a0.ym, a0.mid, "TME")
a3 = at[at.jf == 3].copy(); a3["bk"] = bk_at(a3.tme_c, a3.ym, a3.mid, "B2B")
am = a0[[(c, y) in ROLE["ME"] for c, y in zip(a0.me_c, a0.ym)]].copy(); am["bk"] = bk_at(am.me_c, am.ym, am.mid, "ME")
tt_ = a0.tteam.where(a0.tteam.isin(TEAMS), REST)
y = pd.concat([a0.assign(seg=tt_), a3.assign(seg="B2B"), am.assign(seg="BDE"), a0.assign(seg="All Team JDS"),
               a0.assign(seg="Branch"), a3.assign(seg="Branch")], ignore_index=True).rename(columns={"n": "appt"})
y = y[["city", "day", "seg", "area", "bk", "appt"]]; y["dn"] = [t.toordinal() for t in y.day]

# ------------------------------------------------------------------ daily person facts (per-manday numerators)
F = []
F.append(a[(a.jf == 0) & (a.tteam != "BDE")].groupby(["tme_c", "day"]).agg(made0=("n", "sum"), att0t=("natt", "sum")).rename_axis(["code", "day"]))
F.append(a[a.jf == 3].groupby(["tme_c", "day"]).agg(made3=("n", "sum"), att3t=("natt", "sum")).rename_axis(["code", "day"]))
F.append(a[a.jf == 0].groupby(["me_c", "day"]).agg(att_m0=("natt", "sum")).rename_axis(["code", "day"]))
F.append(a.groupby(["me_c", "day"]).agg(att_mall=("natt", "sum")).rename_axis(["code", "day"]))
HAS_DIALER = os.path.exists(os.path.join(DATA, "dialer.pkl"))
if HAS_DIALER:
    dl = pd.read_pickle(os.path.join(DATA, "dialer.pkl")); dl["code"] = norm(dl.agent.fillna("")); dl["day"] = pd.to_datetime(dl.day).dt.date
    dl["trunk"] = pd.to_numeric(dl.trunk, errors="coerce").fillna(0)
    F.append(dl.groupby(["code", "day"]).agg(trunk=("trunk", "sum")))
pr = pd.read_pickle(os.path.join(DATA, "pres.pkl")); pr["day"] = pd.to_datetime(pr.day).dt.date
pr["pres"] = pd.to_numeric(pr.pres, errors="coerce").fillna(0.0)   # 24 Nov 2026: a text column was dropped from every sum (pres = 0 on 23 Nov)
F.append(pr.groupby(["code", "day"]).agg(pres=("pres", "sum")))
for df_, nm in ((jds, "jds"), (jda, "jda"), (me, "me"), (b2b, "b2b")):
    g = df_[df_.owner != ""].assign(dl=lambda t: t.dc_genio * t.w, rvw=lambda t: t.RV_3yr * t.w).groupby(["owner", "day"]).agg(**{f"cd_{nm}": ("dl", "sum"), f"crv_{nm}": ("rvw", "sum")})
    F.append(g.rename_axis(["code", "day"]))
FACT = pd.concat(F, axis=1).fillna(0.0).reset_index()
if "trunk" not in FACT: FACT["trunk"] = 0.0           # first cut can run before the slow dialer pull ends
FACT["ym"] = [t.year * 100 + t.month for t in FACT.day]; FACT["dn"] = [t.toordinal() for t in FACT.day]
FCOLS = [c for c in FACT.columns if c not in ("code", "day", "ym", "dn")]

# person-month rows by role, with the team rows they feed
hh = h[h.city.isin(BRANCHES)].copy(); hh["area"] = side(hh.main_city_flag)
hh["tseg"] = np.where(hh.role == "TME", hh.team.where(hh.team.isin(TEAMS), REST), "")
ROLE_SEGS = {"TME": ["tseg", "All Team JDS", "Branch"], "B2B": ["B2B", "Branch"], "JDA": ["JDA", "All Team JDA", "Branch"], "ME": ["BDE", "All Team JDS", "Branch"]}
SUF = {"TME": "t", "B2B": "b", "JDA": "j", "ME": "m"}
# which daily fact feeds which measure, per role
MAPF = {"TME": {"made": "made0", "att": "att0t", "trunk": "trunk", "cd": "cd_jds", "crv": "crv_jds"},
        "B2B": {"made": "made3", "att": "att3t", "trunk": "trunk", "cd": "cd_b2b", "crv": "crv_b2b"},
        "JDA": {"pres": "pres", "cd": "cd_jda", "crv": "crv_jda"},
        "ME": {"att": "att_m0", "attall": "att_mall", "cd": "cd_me", "crv": "crv_me"}}


def fracs(cities, a_, b_, lo=None):
    """per (city, ym): share of the month's working days inside [a_, b_] (and after lo); and the month's weight in the window"""
    f, g = {}, {}
    for c in cities:
        days = [x_ for x_ in wd_in(c, a_, b_) if lo is None or x_ >= lo]
        tot = len(days)
        cnt = collections.Counter(x_.year * 100 + x_.month for x_ in days)
        for ym, n in cnt.items():
            f[(c, ym)] = n / WD_M[(c, ym)]; g[(c, ym)] = n / tot
    return f, g


def window_sums(a_, b_, cities):
    """sums per (city, seg, area, bk) for one window"""
    out = []
    lo_, hi_ = a_.toordinal(), b_.toordinal()
    xs = x[x.city.isin(cities) & (x.dn >= lo_) & (x.dn <= hi_)]
    out.append(xs.groupby(["city", "seg", "area", "bk"])[XCOLS].sum())
    ys = y[y.city.isin(cities) & (y.dn >= lo_) & (y.dn <= hi_)]
    out.append(ys.groupby(["city", "seg", "area", "bk"])[["appt"]].sum())
    f, g = fracs(cities, a_, b_)
    fp, _ = fracs(cities, a_, b_, PRES_FROM)
    ft = {}
    for c in cities:
        ft.update(fracs([c], a_, b_, DIAL_FROM.get(c, DIAL_FROM_DEFAULT))[0])
    if not HAS_DIALER: ft = {}
    fs = FACT[(FACT.dn >= lo_) & (FACT.dn <= hi_)].groupby(["code", "ym"])[FCOLS].sum()
    p = hh[hh.city.isin(cities)].copy()
    key = list(zip(p.city, p.ym))
    p["f"] = [f.get(k, 0.0) for k in key]; p["g"] = [g.get(k, 0.0) for k in key]
    p["fp"] = [fp.get(k, 0.0) for k in key]; p["ft"] = [ft.get(k, 0.0) for k in key]
    p = p[p.f > 0]
    p = p.merge(fs, left_on=["code", "ym"], right_index=True, how="left").fillna({c: 0.0 for c in FCOLS})
    for c in FCOLS: p[c] = np.where(p.primary, p[c], 0.0)
    rows = []
    for role, segs in ROLE_SEGS.items():
        q_ = p[p.role == role]
        if q_.empty: continue
        s = SUF[role]
        cols = {f"md_{s}": q_.active_days * q_.f, f"hc_{s}": np.where(q_.primary, q_.g, 0.0)}
        if role == "JDA": cols["md_jp"] = q_.active_days * q_.fp
        if role in ("TME", "B2B"): cols[f"md_{s}t"] = q_.active_days * q_.ft
        for k, src in MAPF[role].items():
            cols[f"{k}_{s}"] = q_[src]
        base = pd.DataFrame(cols, index=q_.index).assign(city=q_.city, area=q_.area, bk=q_.bk)
        for sg in segs:
            rows.append(base.assign(seg=q_.tseg if sg == "tseg" else sg))
    if rows:                         # a window with no working day (e.g. WTD on a Monday whose last-year date was a Sunday)
        z = pd.concat(rows, ignore_index=True)
        out.append(z.groupby(["city", "seg", "area", "bk"]).sum(numeric_only=True))
    C = pd.concat(out, axis=1).fillna(0.0).reset_index()
    # add area All and bucket All
    C = pd.concat([C, C.groupby(["city", "seg", "bk"]).sum(numeric_only=True).reset_index().assign(area="All")], ignore_index=True)
    C = pd.concat([C, C.groupby(["city", "seg", "area"]).sum(numeric_only=True).reset_index().assign(bk="All")], ignore_index=True)
    return C.set_index(["city", "seg", "area", "bk"]).sort_index()


TME_ROWS = set(TEAMS) | {REST, "All Team JDS"}
APPT_ROWS = TME_ROWS | {"B2B", "BDE", "Branch"}
MADE_ROWS = TME_ROWS | {"B2B", "Branch"}
ALL = set(SEGS)
# id, label, unit, applies to, floor for 'best branch' (on the base), higher is better, group
METRICS = [
    ("deals", "Deals", "n", ALL, None, True, "Volume and value"),
    ("contrib_deals", "Share of the row's deals (tenure contribution)", "pct", ALL, None, None, "Volume and value"),
    ("rv", "RV 3-yr", "lakh", ALL, None, True, "Volume and value"),
    ("contrib_rv", "Share of the row's RV (tenure contribution)", "pct", ALL, None, None, "Volume and value"),
    ("deals_pmd", "Deals per manday", "r3", ALL, 150, True, "Volume and value"),
    ("rv_pmd", "RV per manday", "rs", ALL, 150, True, "Volume and value"),
    ("rv_deal", "RV / deal", "rs", ALL, 30, True, "Volume and value"),
    ("coll_deal", "Collection per deal", "rs", ALL, 30, True, "Volume and value"),
    ("nonecs_rv", "Non-ECS RV / deal", "rs", ALL, 30, True, "Volume and value"),
    ("ecs_rv", "ECS RV / deal", "rs", ALL, 30, True, "Volume and value"),
    ("ecs_pct", "ECS %", "pct", ALL, 30, True, "Volume and value"),
    ("nonecs_pct", "Non-ECS %", "pct", ALL, 30, False, "Volume and value"),
    ("pk_pct", "Package: share of deals", "pct", ALL, 30, None, "Product"),
    ("pd_pct", "PDG: share of deals", "pct", ALL, 30, None, "Product"),
    ("ot_pct", "Other products: share of deals", "pct", ALL, 30, None, "Product"),
    ("pk_rv", "Package: RV / deal", "rs", ALL, 30, True, "Product"),
    ("pd_rv", "PDG: RV / deal", "rs", ALL, 30, True, "Product"),
    ("ot_rv", "Other products: RV / deal", "rs", ALL, 30, True, "Product"),
    ("att_pmd", "Appointments attended per manday", "r2", APPT_ROWS, 150, True, "Appointments and calls"),
    ("made_pmd", "Appointments given per TME manday", "r2", MADE_ROWS, 150, True, "Appointments and calls"),
    ("cog", "COG % (deals ÷ appointments given)", "pct", APPT_ROWS, 100, True, "Appointments and calls"),
    ("tt", "Avg trunk duration (min per TME manday)", "r0", MADE_ROWS, 150, True, "Appointments and calls"),
    ("pres", "Avg presentations per JDA manday", "r2", {"JDA", "All Team JDA", "Branch"}, 150, True, "Appointments and calls"),
    ("ecs_clear", "1st ECS clearance", "pct", set(), None, None, "Appointments and calls"),
    ("hc_t", "Headcount TME", "r1", TME_ROWS | {"Branch"}, None, None, "People"),
    ("hc_b", "Headcount B2B team", "r1", {"B2B", "Branch"}, None, None, "People"),
    ("hc_j", "Headcount JDA", "r1", {"JDA", "All Team JDA", "Branch"}, None, None, "People"),
    ("hc_m", "Headcount ME (BDE)", "r1", {"BDE", "All Team JDS", "Branch"}, None, None, "People"),
    ("md_t", "Man days TME", "n", TME_ROWS | {"Branch"}, None, None, "People"),
    ("md_b", "Man days B2B team", "n", {"B2B", "Branch"}, None, None, "People"),
    ("md_j", "Man days JDA", "n", {"JDA", "All Team JDA", "Branch"}, None, None, "People"),
    ("md_m", "Man days ME (BDE)", "n", {"BDE", "All Team JDS", "Branch"}, None, None, "People"),
]
MID = [m[0] for m in METRICS]
PER_MD = {"deals_pmd", "rv_pmd", "att_pmd", "made_pmd", "tt", "pres"}


def ratio(a_, b_):
    return float(a_ / b_) if b_ > 0 else None


def g0(r, c):
    return float(r.get(c, 0.0))


def metrics(r, rall, seg, bk):
    """value and base for every metric of one cell; rall = the same row's All-tenure sums"""
    G = lambda c: g0(r, c)
    if seg in TME_ROWS: pm = (G("cd_t"), G("crv_t"), G("md_t"))
    elif seg == "B2B": pm = (G("cd_b"), G("crv_b"), G("md_b"))
    elif seg in ("JDA", "All Team JDA"): pm = (G("cd_j"), G("crv_j"), G("md_j"))
    elif seg == "BDE": pm = (G("cd_m"), G("crv_m"), G("md_m"))
    else: pm = (G("cd_t") + G("cd_j") + G("cd_b"), G("crv_t") + G("crv_j") + G("crv_b"), G("md_t") + G("md_j") + G("md_b"))
    if bk == "All": pm = (G("deals"), G("rv"), pm[2])          # as the sales dashboard: the row's deals (RV) / the row's mandays
    if seg in TME_ROWS: att = (G("att_t"), G("md_t")) if seg != "All Team JDS" else (G("att_m"), G("md_m"))
    elif seg == "B2B": att = (G("att_b"), G("md_b"))
    elif seg == "BDE": att = (G("att_m"), G("md_m"))
    else: att = (G("attall_m"), G("md_m"))
    if seg == "B2B": made, tt = (G("made_b"), G("md_b")), (G("trunk_b"), G("md_bt"))
    elif seg == "Branch": made, tt = (G("made_t") + G("made_b"), G("md_t") + G("md_b")), (G("trunk_t") + G("trunk_b"), G("md_tt") + G("md_bt"))
    else: made, tt = (G("made_t"), G("md_t")), (G("trunk_t"), G("md_tt"))
    dl, rv, ed, er = G("deals"), G("rv"), G("ed"), G("er")
    v = {
        "deals": (dl, dl), "contrib_deals": (ratio(dl, g0(rall, "deals")), g0(rall, "deals")), "rv": (rv / 1e5, dl),
        "contrib_rv": (ratio(rv, g0(rall, "rv")), g0(rall, "deals")),
        "deals_pmd": (ratio(pm[0], pm[2]), pm[2]), "rv_pmd": (ratio(pm[1], pm[2]), pm[2]),
        "rv_deal": (ratio(rv, dl), dl), "coll_deal": (ratio(G("coll"), dl), dl),
        "nonecs_rv": (ratio(rv - er, dl - ed), dl - ed), "ecs_rv": (ratio(er, ed), ed),
        "ecs_pct": (ratio(ed, dl), dl), "nonecs_pct": (ratio(dl - ed, dl), dl),
        "pk_pct": (ratio(G("pk_d"), dl), dl), "pd_pct": (ratio(G("pd_d"), dl), dl), "ot_pct": (ratio(G("ot_d"), dl), dl),
        "pk_rv": (ratio(G("pk_r"), G("pk_d")), G("pk_d")), "pd_rv": (ratio(G("pd_r"), G("pd_d")), G("pd_d")), "ot_rv": (ratio(G("ot_r"), G("ot_d")), G("ot_d")),
        "att_pmd": (ratio(*att), att[1]), "made_pmd": (ratio(*made), made[1]), "cog": (ratio(G("cogd"), G("appt")), G("appt")),
        "tt": (ratio(tt[0] / 60.0, tt[1]) if HAS_DIALER else None, tt[1]), "pres": (ratio(G("pres_j"), G("md_jp")), G("md_jp")),
        "ecs_clear": (None, 0.0),
        "hc_t": (G("hc_t"), G("hc_t")), "hc_b": (G("hc_b"), G("hc_b")), "hc_j": (G("hc_j"), G("hc_j")), "hc_m": (G("hc_m"), G("hc_m")),
        "md_t": (G("md_t"), G("md_t")), "md_b": (G("md_b"), G("md_b")), "md_j": (G("md_j"), G("md_j")), "md_m": (G("md_m"), G("md_m")),
    }
    out = []
    for mid, _l, _u, segs, _f, _hb, _g in METRICS:
        if seg not in segs: out.append(None); continue
        if bk == "unknown" and mid in PER_MD | {"hc_t", "hc_b", "hc_j", "hc_m", "md_t", "md_b", "md_j", "md_m"}: out.append(None); continue
        val, base = v[mid]
        out.append([None if val is None else float(f"{val:.5g}"), round(float(base), 1)])
    return out


def cube_for(C, city):
    rows = C.loc[city].to_dict("index") if city in C.index.get_level_values(0) else {}     # keys (seg, area, bk)
    res = {}
    for seg in SEGS:
        for ar in AREAS:
            rall = rows.get((seg, ar, "All"), {})
            res.setdefault(seg, {})[ar] = [metrics(rows.get((seg, ar, bk), {}), rall, seg, bk) for bk in BKS]
    return res


print("building windows ...", flush=True)
cube, best, wdays, checks = {}, {}, {}, {}
OTHERS = [c for c in BRANCHES if c not in SKIP]
for wk, (a_, b_) in WINS.items():
    main = "_" not in wk
    cities = BRANCHES if main else [HOME]
    C = window_sums(a_, b_, cities)
    cube[wk] = cube_for(C, HOME)
    wdays[wk] = len(wd_in(HOME, a_, b_))
    # checks: rows add up (Jaipur, area All and Main + Remote, bucket All)
    J = lambda seg, ar="All", col="deals": g0(C.loc[(HOME, seg, ar, "All")], col) if (HOME, seg, ar, "All") in C.index else 0.0
    nos_w = nos[(nos.city == HOME) & (nos.day >= a_) & (nos.day <= b_)].dc_genio.sum()
    for col in ("deals", "rv"):
        assert abs(J("All Team JDS", col=col) - sum(J(t, col=col) for t in TEAMS + [REST])) < 0.01, (wk, col, "JDS teams")
        br_sum = J("All Team JDA", col=col) + J("All Team JDS", col=col) + J("B2B", col=col) + (nos_w if col == "deals" else nos[(nos.city == HOME) & (nos.day >= a_) & (nos.day <= b_)].RV_3yr.sum())
        assert abs(J("Branch", col=col) - br_sum) < 0.01, (wk, col, "Branch")
        for sg in SEGS:
            assert abs(J(sg, "All", col) - J(sg, "Main", col) - J(sg, "Remote", col)) < 0.01, (wk, sg, col, "area")
    checks[wk] = {s: round(J(s), 1) for s in SEGS}
    if main:
        wdj = max(1, wdays[wk]); scale = max(0.2, min(1.0, wdj / 25))
        oc = {c: cube_for(C, c) for c in OTHERS}
        for seg in SEGS:
            for ar in AREAS:
                for bi, bk in enumerate(BKS):
                    if bk == "unknown": continue
                    for mi, (mid, _l, _u, segs, floor, hb, _g) in enumerate(METRICS):
                        if seg not in segs or floor is None or hb is None: continue
                        fl = floor * scale
                        cand = [(m_[0], c, m_[1]) for c in OTHERS for m_ in [oc[c][seg][ar][bi][mi]] if m_ and m_[0] is not None and m_[1] >= fl]
                        if not cand: continue
                        bb = (max if hb else min)(cand, key=lambda t: t[0])
                        jv = cube[wk][seg][ar][bi][mi]
                        rank = None
                        if jv and jv[0] is not None:
                            rank = 1 + sum(1 for t in cand if (t[0] > jv[0] if hb else t[0] < jv[0]))
                        best.setdefault(wk, {}).setdefault(seg, {}).setdefault(ar, {}).setdefault(bk, {})[mid] = [bb[0], bb[1], round(bb[2], 1), len(cand) + 1, rank]
    print(f"  {wk:<7} {fmt_d(a_, b_):<26} wd {wdays[wk]:>3}  deals: " + ", ".join(f"{s} {checks[wk][s]:,.0f}" for s in ("JDA", "B2B", "All Team JDS", "BDE", "Branch")), flush=True)

# working days vs HR's highest active days per month (sanity)
wd_vs_hr = {f"{ym}": (WD_M.get((HOME, ym)), int(CHECK_WD.get((HOME, ym), 0))) for ym in sorted({k[1] for k in WD_M if k[0] == HOME})}
print("Jaipur working days by month (deal days, HR max active):", wd_vs_hr)

# ------------------------------------------------------------------ leaders: managers and their TLs (Jaipur, 2026 windows)
SSO = pickle.load(open(SSO_PKL, "rb"))
COPY_FOR = lambda ym: "2026-07-02" if ym <= 202607 else ("2026-09-07" if ym <= 202609 else "2026-10-12")
HEADS = {}
for S_ in SSO.values():
    for c_, v_ in S_.items():
        dsg, sec = v_.get("Designation", "").lower(), v_.get("Section", "").lower()
        if "vice president" in dsg or "branch / sales head" in sec: HEADS[c_] = "Branch head"
        elif sec.startswith("jda") and (dsg.startswith("avp") or ("general manager" in dsg and not dsg.startswith(("asst", "assistant")))): HEADS.setdefault(c_, "JDA head")
JNAME = dict(zip(j.code, j.empname.fillna("").astype(str))) if "empname" in j else {}   # HR master name, when SSO has none
LINES = {}
for cp, S in SSO.items():
    rep = collections.defaultdict(set)
    for c, v in S.items():
        if v.get("Reporting-1"): rep[v["Reporting-1"]].add(c)
    has_tls = {m_ for m_, rs in rep.items() if any(rep.get(r_) for r_ in rs)}
    # shared pages carry no JDA-head or city-head names (user rule): label those two by role, matched by code in any copy
    def head(c):
        return HEADS.get(c)
    name = lambda c: (head(c) or (S.get(c, {}).get("Emp Name") or JNAME.get(c) or c).strip().title()) if c else ""
    L = {}
    for c, v in S.items():
        r1 = v.get("Reporting-1", "")
        if rep.get(c):                                    # a TL (or manager) closing deals himself
            tl, mg = c, (r1 if r1 else c)
            if c in has_tls: tl, mg = c, c
        elif r1 in has_tls: tl, mg = r1, r1                 # reports straight to a manager
        else: tl, mg = r1, S.get(r1, {}).get("Reporting-1", "") or r1
        L[c] = (mg, name(mg), tl, name(tl) + (" · direct reportees" if tl == mg and tl != c else ""))
    LINES[cp] = L
LEAD_SEG = {"TME": "tseg", "B2B": "B2B", "JDA": "JDA", "ME": "BDE"}
LEAD_WINS = [k for k in WINS if not k.endswith("_ly")]
LEAD_SEG_LIST = TEAMS + [REST, "B2B", "JDA", "BDE"]          # no reporting lines for 2025


def hid(k, c):                     # codes stay out of the page: a hash pairs the same person across periods
    return str(abs(hash((k, c))) % 10**9)


def leaders_for(a_, b_):
    f, g = fracs([HOME], a_, b_)
    fs = FACT[(FACT.dn >= a_.toordinal()) & (FACT.dn <= b_.toordinal())].groupby(["code", "ym"])[FCOLS].sum()
    p = hh[hh.city == HOME].copy()
    key = list(zip(p.city, p.ym)); p["f"] = [f.get(k, 0.0) for k in key]; p["g"] = [g.get(k, 0.0) for k in key]
    p = p[p.f > 0].merge(fs, left_on=["code", "ym"], right_index=True, how="left").fillna({c: 0.0 for c in FCOLS})
    for c in FCOLS: p[c] = np.where(p.primary, p[c], 0.0)
    p["md"] = p.active_days * p.f; p["hc"] = np.where(p.primary, p.g, 0.0)
    p["cd"] = np.select([p.role == r for r in MAPF], [p[MAPF[r]["cd"]] for r in MAPF], 0.0)
    p["crv"] = np.select([p.role == r for r in MAPF], [p[MAPF[r]["crv"]] for r in MAPF], 0.0)
    p["seg"] = np.where(p.role == "TME", p.tseg, p.role.map(LEAD_SEG))
    ln = [LINES[COPY_FOR(ym)].get(c) for c, ym in zip(p.code, p.ym)]
    p["mg"] = [l_[0] if l_ else "" for l_ in ln]; p["mgn"] = [l_[1] if l_ else "Not in the reporting lines" for l_ in ln]
    p["tl"] = [l_[2] if l_ else "" for l_ in ln]; p["tln"] = [l_[3] if l_ else "Not in the reporting lines" for l_ in ln]
    p["pn"] = [HEADS.get(c) or (SSO[COPY_FOR(ym)].get(c, {}).get("Emp Name") or JNAME.get(c) or c).strip().title() for c, ym in zip(p.code, p.ym)]
    out = {}
    for seg, gs in p.groupby("seg"):
        for ar in AREAS:
            q_ = gs if ar == "All" else gs[gs.area == ar]
            if q_.empty: continue
            t = q_.groupby(["mg", "mgn", "tl", "tln"])[["hc", "md", "cd", "crv"]].sum().reset_index()
            pp = q_.groupby(["mg", "tl", "code", "pn"])[["hc", "md", "cd", "crv"]].sum().reset_index()
            ppl = {k: [[r.pn, round(r.hc, 2), round(r.md, 1), round(r.cd, 1), round(r.crv), hid("p", r.code)] for r in g.sort_values("cd", ascending=False).itertuples()]
                   for k, g in pp.groupby(["mg", "tl"])}
            mgs = []
            for (mg, mgn), tg in t.groupby(["mg", "mgn"]):
                tls = [[r.tln, round(r.hc, 1), round(r.md, 1), round(r.cd, 1), round(r.crv), ppl.get((mg, r.tl), []), hid("t", r.tl)] for r in tg.sort_values("cd", ascending=False).itertuples()]
                mgs.append([mgn, round(tg.hc.sum(), 1), round(tg.md.sum(), 1), round(tg.cd.sum(), 1), round(tg.crv.sum()), tls, mg])
            mgs.sort(key=lambda r: -r[3])
            out.setdefault(seg, {})[ar] = mgs
    return out


leaders = {wk: leaders_for(*WINS[wk]) for wk in LEAD_WINS}
# match a manager across windows by code (names can repeat); the code is used only inside the page to pair rows, never shown
for wk in leaders:
    for seg in leaders[wk]:
        for ar in leaders[wk][seg]:
            for r in leaders[wk][seg][ar]:
                r[6] = str(abs(hash(("m", r[6]))) % 10**9)

# ------------------------------------------------------------------ custom dates (user, 24 Nov 2026: a calendar in the period selector)
# The page works out any date range from the home branch's day-level building blocks, with the same rules as window_sums,
# metrics and leaders_for (ported to the page's script; tested: the MTD dates picked as a custom range give the MTD figures).
D0 = FYS.replace(year=FYS.year - 1)                                   # first day of the data (last FY start)
DI = lambda d_: (d_ - D0).days
SI = {s: i for i, s in enumerate(SEGS)}; BI = {b: i for i, b in enumerate(BKS)}; AI = {"Main": 0, "Remote": 1}
RS = [("TME", t) for t in TEAMS + [REST]] + [("B2B", ""), ("JDA", ""), ("ME", "")]   # role (and TME team) of a person-month
RSI = {r: i for i, r in enumerate(RS)}
RCOLS = {"TME": ["made", "att", "trunk", "cd", "crv"], "B2B": ["made", "att", "trunk", "cd", "crv"], "JDA": ["pres", "cd", "crv"],
         "ME": ["att", "attall", "cd", "crv"]}
r2 = lambda v: float(f"{v:.6g}")
# only the base rows go to the page; it adds up All Team JDA (= JDA), All Team JDS (= the TME teams) and Branch (= TME teams +
# B2B + JDA + no salesperson, the last kept as its own row "NOS", index len(SEGS))
BASE = TEAMS + [REST, "B2B", "JDA", "BDE"]
xh = x[x.city == HOME].groupby(["day", "seg", "area", "bk"])[XCOLS].sum()
yh = y[y.city == HOME].groupby(["day", "seg", "area", "bk"])[["appt"]].sum()
dxh = xh.join(yh, how="outer").fillna(0.0)
_b = dxh.xs("Branch", level="seg"); _p = dxh[dxh.index.get_level_values("seg").isin(TEAMS + [REST, "B2B", "JDA"])].groupby(level=["day", "area", "bk"]).sum()
_nos = _b.sub(_p, fill_value=0.0); _nos = _nos[(_nos.abs() > 1e-6).any(axis=1)]
_nos.index = pd.MultiIndex.from_tuples([(d_, "NOS", a_, k_) for d_, a_, k_ in _nos.index], names=["day", "seg", "area", "bk"])
dxh = pd.concat([dxh[dxh.index.get_level_values("seg").isin(BASE)], _nos]).reset_index()
MONEY = {"rv", "coll", "er", "pk_r", "pd_r", "ot_r"}
CCOLS = XCOLS + ["appt"]
cv = lambda c, v: int(round(v)) if c in MONEY else (int(v) if float(v).is_integer() else round(float(v), 2))
CX = {"cols": CCOLS, "rows": [[DI(r[0]), SI.get(r[1], len(SEGS)), AI[r[2]], BI[r[3]]] + [cv(c, v) for c, v in zip(CCOLS, r[4:])]
                              for r in dxh.itertuples(index=False)]}
hp = hh[hh.city == HOME].copy()
hp["rs"] = [RSI[(ro, ts if ro == "TME" else "")] for ro, ts in zip(hp.role, hp.tseg)]
fx = FACT.merge(hp[hp.primary][["code", "ym", "role", "rs", "area", "bk"]], on=["code", "ym"])
fxr = []
for role, cols in RCOLS.items():
    q_ = fx[fx.role == role]
    if q_.empty: continue
    g_ = q_.assign(**{c: q_[MAPF[role][c]] for c in cols}).groupby(["day", "rs", "area", "bk"])[cols].sum().reset_index()
    for r in g_.itertuples(index=False):
        vals = [r2(v) for v in r[4:]]
        if any(vals): fxr.append([DI(r[0]), int(r[1]), AI[r[2]], BI[r[3]]] + vals)
CF = {"rows": fxr}
hm = hp.assign(pr=hp.primary.astype(float)).groupby(["ym", "rs", "area", "bk"]).agg(act=("active_days", "sum"), pr=("pr", "sum")).reset_index()
CH = {"rows": [[int(r.ym), int(r.rs), AI[r.area], BI[r.bk], r2(r.act), r2(r.pr)] for r in hm.itertuples(index=False)]}
# managers: person-month rows (role row, reporting line, name) and each row's credited deals per day, from Jan of the FY's year
LFROM = D(FYS.year, 1, 1); LFYM = LFROM.year * 100 + LFROM.month
lp = hp[hp.ym >= LFYM].copy().reset_index(drop=True)
lp["seg"] = np.where(lp.role == "TME", lp.tseg, lp.role.map(LEAD_SEG))
ln = [LINES[COPY_FOR(ym)].get(c) for c, ym in zip(lp.code, lp.ym)]
NM = {}                                                              # names table (managers, team leaders, people)
nid = lambda s_: NM.setdefault(s_, len(NM))
lp["mg"] = [l_[0] if l_ else "" for l_ in ln]; lp["mgn"] = [nid(l_[1] if l_ else "Not in the reporting lines") for l_ in ln]
lp["tl"] = [l_[2] if l_ else "" for l_ in ln]; lp["tln"] = [nid(l_[3] if l_ else "Not in the reporting lines") for l_ in ln]
lp["pn"] = [nid(HEADS.get(c) or (SSO[COPY_FOR(ym)].get(c, {}).get("Emp Name") or JNAME.get(c) or c).strip().title()) for c, ym in zip(lp.code, lp.ym)]
LSI = {s: i for i, s in enumerate(LEAD_SEG_LIST)}
LPR = [[int(r.ym), LSI.get(r.seg, -1), AI[r.area], int(bool(r.primary)), r2(r.active_days), int(r.mgn), hid("m", r.mg), int(r.tln), hid("t", r.tl), int(r.pn), hid("p", r.code)]
       for r in lp.itertuples(index=False)]
lf = FACT[FACT.ym >= LFYM].merge(lp[lp.primary].reset_index()[["index", "code", "ym", "role"]], on=["code", "ym"])
lfr = []
for role in MAPF:
    q_ = lf[lf.role == role]
    for r in q_[["day", "index", MAPF[role]["cd"], MAPF[role]["crv"]]].itertuples(index=False):
        if r[2] or r[3]: lfr.append([DI(r[0]), int(r[1]), r2(r[2]), round(float(r[3]))])
WDH = sorted(DI(d_) for d_ in WD.get(HOME, ()))
CUSTOM = {"d0": D0.isoformat(), "end": END.isoformat(), "wd": WDH, "wdm": {str(k[1]): v for k, v in WD_M.items() if k[0] == HOME},
          "x": CX, "f": CF, "h": CH, "rs": [[ro, ts] for ro, ts in RS], "rcols": RCOLS, "pres_from": DI(PRES_FROM),
          "dial_from": DI(DIAL_FROM.get(HOME, DIAL_FROM_DEFAULT)), "has_dialer": bool(HAS_DIALER),
          "lead": {"rows": LPR, "facts": lfr, "names": [n for n, _ in sorted(NM.items(), key=lambda t: t[1])], "from": LFROM.isoformat()},
          "rolesegs": {"TME": ["tseg", "All Team JDS", "Branch"], "B2B": ["B2B", "Branch"], "JDA": ["JDA", "All Team JDA", "Branch"], "ME": ["BDE", "All Team JDS", "Branch"]},
          "suf": SUF}
print(f"custom dates data: {len(CX['rows']):,} deal-day rows, {len(fxr):,} person-fact rows, {len(CH['rows']):,} HR rows, "
      f"{len(LPR):,} manager rows, {len(lfr):,} manager deal rows")

# ------------------------------------------------------------------ page data
DEAL_UNKNOWN = {s: (lambda c: round(c[BKS.index("unknown")][0][0] / c[0][0][0], 3) if c[0][0] and c[0][0][0] else 0)(cube["QTD"][s]["All"]) for s in SEGS}
SEGL = {"Super Cat": ("Super Cat", "TME team", "jds"), "Hot Data": ("Hot Data", "TME team", "jds"), "Online": ("Online", "TME team", "jds"),
        REST: ("Rest of the JDS teams", "TME teams", "jds"), "B2B": ("B2B team", "own team", "b2b"),
        "JDA": ("JDA", "without B2B", "jda"), "BDE": ("BDE", "all MEs", "jds"), "All Team JDA": ("All Team JDA", "= JDA", "jda"),
        "All Team JDS": ("All Team JDS", "JDS channel", "jds"), "Branch": ("Branch", "all deals", "area")}
GROUPS = [("TME teams", ["Super Cat", "Hot Data", "Online", REST, "B2B"]), ("Field", ["JDA", "BDE"]), ("All teams", ["All Team JDA", "All Team JDS", "Branch"])]
PEOPLE = {**{t: "TMEs" for t in TEAMS + [REST]}, "B2B": "B2B people", "JDA": "JDAs", "BDE": "MEs"}
page = {
    "built": datetime.date.today().isoformat(), "home": HOME, "segs": SEGS, "areas": AREAS, "buckets": BKS,
    "metrics": [dict(id=m, label=l, unit=u, segs=sorted(s), floor=f, hb=hb, group=gr) for m, l, u, s, f, hb, gr in METRICS],
    "others": OTHERS, "main": list(MAIN), "plabel": PLABEL, "pvname": PVNAME,
    "wins": {k: [w[0].isoformat(), w[1].isoformat(), fmt_d(*w)] for k, w in WINS.items()}, "wdays": wdays,
    "cube": cube, "best": best, "leaders": leaders, "unknown_q3": DEAL_UNKNOWN,
    "nodata": {"pres_before": PRES_FROM.isoformat(), "dial_from": DIAL_FROM["Jaipur"].isoformat()},
    "segl": SEGL, "groups": GROUPS, "leadsegs": list(LEAD_SEG_LIST), "rest": REST, "quarters": QUARTERS, "people": PEOPLE,
    "custom": CUSTOM,
}
js = json.dumps(page, separators=(",", ":"), allow_nan=False)
json.dump(page, open(os.path.join(DATA, "grid.json"), "w"), separators=(",", ":"))
print(f"page data {len(js) / 1e6:.2f} MB")

# quick look: Jaipur MTD All, with last year
for seg in SEGS:
    c, l_ = cube["MTD"][seg]["All"][0], cube["MTD_ly"][seg]["All"][0]
    pick = lambda arr, m: None if arr[MID.index(m)] is None else arr[MID.index(m)][0]
    print(f"{seg:<22}", " | ".join(f"{m}: {pick(c, m)} (LY {pick(l_, m)})" for m in ("deals", "rv_deal", "deals_pmd", "cog", "hc_t", "hc_j", "hc_b")))

# ------------------------------------------------------------------ static copy for viewers that run no scripts (default: MTD)
BKL = {"All": "All", "0-3M": "0–3M", "3-6M": "3–6M", "6-12M": "6–12M", "1-2Y": "1–2Y", "2-4Y": "2–4Y", "4Y+": "4Y+", "unknown": "Tenure unknown"}


def ind(v):
    t = str(int(round(abs(v))))
    if len(t) > 3:
        head = t[:-3]; t = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1]) + "," + t[-3:]
    return ("-" if v < 0 else "") + t


def fmt(v, u):
    if v is None: return "–"
    if u == "rs": return "₹" + ind(v)
    if u == "lakh": return f"₹{v:,.1f} L"
    if u == "pct": return f"{v * 100:.1f}%"
    if u == "r1": return f"{v:,.1f}"
    if u == "r2": return f"{v:.2f}"
    if u == "r3": return f"{v:.3f}"
    return ind(v)


def chg(now, was, u, hb):
    if now is None or was is None: return ""
    if u == "pct": dd_ = (now - was) * 100; txt = f"{abs(dd_):.1f} pts"
    else:
        if not was: return ""
        dd_ = (now / was - 1) * 100; txt = f"{abs(dd_):.0f}%"
    if abs(dd_) < 0.5: return '<span class="eq">level</span>'
    cls = "eq" if hb is None else ("up" if (dd_ > 0) == hb else "dn")
    return f'<span class="{cls}">{"▲" if dd_ > 0 else "▼"}{txt}</span>'


def scell(seg, bi, mi):
    mid, _l, u, segs, floor, hb, _g = METRICS[mi]; bk = BKS[bi]; allc = "allc" if bk == "All" else ""
    if mid == "ecs_clear": return f'<td class="na {allc}">no data</td>'
    c = cube["MTD"][seg]["All"][bi][mi]
    if c is None: return f'<td class="na {allc}">·</td>'
    v, n = c
    h_ = f'<div class="{"v thin" if v is not None and floor and n < floor * SCALE_MTD else "v"}">{fmt(v, u)}</div>'
    for wk, lab in (("MTD_ly", "LY"), ("MTD_pv", "MoM")):
        w = cube[wk][seg]["All"][bi][mi]; wv = None if w is None else w[0]; ch = chg(v, wv, u, hb)
        h_ += f'<div class="cl">{lab} <b>{fmt(wv, u)}</b>{" " + ch if ch else ""}</div>'
    return f'<td class="{allc}">{h_}</td>'


SCALE_MTD = max(0.2, min(1.0, wdays["MTD"] / 25))
head = "<thead><tr><th class=\"rl\">Team row</th>" + "".join(f'<th class="{"all" if b == "All" else ""}">{BKL[b]}</th>' for b in BKS) + "</tr></thead>"
blocks = []
for mi, m in enumerate(METRICS):
    body = "".join(f'<tr class="grp"><td colspan="{len(BKS) + 1}">{gl}</td></tr>' + "".join(
        f'<tr class="k-{SEGL[sg][2]}"><td class="rl">{SEGL[sg][0]}<span class="tag">{SEGL[sg][1]}</span></td>' + "".join(scell(sg, bi, mi) for bi in range(len(BKS))) + "</tr>"
        for sg in segs) for gl, segs in GROUPS)
    blocks.append(f'<h3 class="sh">{m[1]}</h3><div class="tw"><table class="g">{head}<tbody>{body}</tbody></table></div>')
W = WINS
STATIC = ('<section class="card" id="static"><style>#static h3.sh { margin: 18px 0 6px; font-size: 14px; } #static h3.sh:first-of-type { margin-top: 6px; }</style>'
          f'<div class="chead"><h2>Every metric: Jaipur, MTD ({W["MTD"] and fmt_d(*W["MTD"])}), with last year and last month</h2></div>'
          f'<p class="lead">Bold = MTD. LY = the same dates last year ({fmt_d(*W["MTD_ly"])}); MoM = the same days last month ({fmt_d(*W["MTD_pv"])}). '
          'Open the file in Chrome or Edge to switch periods, areas and views.</p>'
          + "".join(blocks) + "</section>")
# user, 23 Nov 2026: the page is for sales people, so no notes on how figures are derived (they live in the README)
fills = {"{{SUB}}": f"Data up to {END.day} {END:%b %Y}", "<!--STATIC-->": STATIC}

if os.path.exists(TEMPLATE):
    html = open(TEMPLATE, encoding="utf-8").read()
    html = re.sub(r"<!--STATIC-->.*?<!--/STATIC-->", lambda _m: "<!--STATIC-->", html, count=1, flags=re.S)   # drop the template-only note
    for k, v in fills.items():
        assert k in html, k; html = html.replace(k, v)
    assert "{{" not in html and "tplnote" not in html
    html = html.replace("/*DATA*/null", js)
    html = html.replace("/*CUSTOM_JS*/", open(os.path.join(HERE, "custom_dates.js"), encoding="utf-8").read())   # the calendar (24 Nov 2026)
    open(OUT, "w", encoding="utf-8").write(html); print("wrote", OUT, f"{os.path.getsize(OUT) / 1e6:.2f} MB")
