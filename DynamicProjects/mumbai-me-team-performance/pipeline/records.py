"""The appointment records both pages are built from: cache\\raw.pkl (+ cache\\deals.pkl) -> one compact record per
appointment given to an ME, with the deal rule applied. Used by build_dashboard.py and build_review.py, so both pages
count appointments, attended and deals the same way.

Outcome of an appointment (final_disposition_name), as recorded in tbl_final_data_appt:
  attended:      Dealclosed (a deal) | Follow Up | Not Interested
  not attended:  Not Available (customer) | Pending (not updated) | Not Visited (ME did not go)

Deals closed (15 Oct 2026) are separate deal records counted as the Sales MIS counts them (fetch_deals.py MIS_SQL), not
the Dealclosed appointments: prepare() returns them as 'deals'.
"""
from collections import Counter, defaultdict
import datetime
import os
import pickle

OUTCOMES = ["Dealclosed", "Follow Up", "Not Interested", "Not Available", "Pending", "Not Visited"]   # 0-2 attended


def tidy(name):
    name = " ".join(str(name or "").split())
    return name.title() if name.isupper() or name.islower() else name


def prepare(pipe, log=print):
    """Returns a dict: fy, end, raw, rows (given, as dicts), not_counted (given_count 0, as dicts), MES / MGRS / TMES /
    TEAMS lookups, recs [(day, me, mgr, tme, team, outcome, company, parentid, row)], bad, deal_src, later, mg_up,
    me_ix (code -> index; adds an ME), tme_ix."""
    raw = pickle.load(open(os.path.join(pipe, "cache", "raw.pkl"), "rb"))
    cols = raw["cols"]
    ALL = [dict(zip(cols, r)) for r in raw["rows"]]
    # Days the appointment table does not have yet (it loads around 2 pm), rebuilt from the live allocation API by
    # fetch_api.py: added only after the table's last day, and marked provisional on the pages.
    provisional = []
    ap = os.path.join(pipe, "cache", "api_rows.pkl")
    if os.path.exists(ap):
        api = pickle.load(open(ap, "rb"))
        if api["cols"] == cols:
            new = [dict(zip(cols, r)) for r in api["rows"] if r[cols.index("to_date")] > raw["end"]]
            if new:
                # a deal closed on that day for an ME's appointment of an earlier day this month: the table moves that
                # business's row to the deal day, so the ME's earlier (not deal) row of it goes
                rep = {}
                for pid, me, d in api.get("replaces", []):
                    d = datetime.date.fromisoformat(d) if isinstance(d, str) else d
                    if d > raw["end"]:
                        k = (pid, str(me).strip().lstrip("0"))
                        rep[k] = min(rep.get(k, d), d)
                if rep:
                    n0 = len(ALL)
                    def moved(r):
                        d = rep.get((r["parentid"], str(r["me"]).strip().lstrip("0")))
                        return (d is not None and r["to_date"] < d and (r["to_date"].year, r["to_date"].month) == (d.year, d.month)
                                and r.get("final_disposition_name") != "Dealclosed")
                    ALL = [r for r in ALL if not moved(r)]
                    log(f"{n0 - len(ALL)} earlier appointment rows moved to their deal day (deals closed later, as the table does)")
                # one row per business per month, as the table: a business seen again on a provisional day (any ME) loses
                # its earlier row of the month, unless that row is a deal - then the deal row stays and the new visit goes.
                # Checked on 15 Oct 2026: the morning's 1-14 Oct went from 3,308 to 3,297 given, the table's own figure.
                NCC = "Not Counted/Cancelled"
                pm = defaultdict(list)
                for r in new:
                    if r["final_disposition_name"] != NCC:
                        pm[(r["parentid"], r["to_date"].year, r["to_date"].month)].append(r)
                old = defaultdict(list)
                for r in ALL:
                    k = (r["parentid"], r["to_date"].year, r["to_date"].month)
                    if k in pm and r["final_disposition_name"] != NCC:
                        old[k].append(r)
                gone, skip = set(), set()
                for k, rs in old.items():
                    if any(r["final_disposition_name"] == "Dealclosed" for r in rs) and not any(r["final_disposition_name"] == "Dealclosed" for r in pm[k]):
                        skip |= {id(r) for r in pm[k]}
                    else:
                        gone |= {id(r) for r in rs if r["final_disposition_name"] != "Dealclosed"}
                if gone or skip:
                    ALL = [r for r in ALL if id(r) not in gone]
                    new = [r for r in new if id(r) not in skip]
                    log(f"{len(gone)} earlier rows of this month replaced by a newer appointment of the same business; "
                        f"{len(skip)} new visits left out (the business already has a deal this month)")
                ALL += new
                provisional = sorted({r["to_date"] for r in new})
                raw = dict(raw, end=max(raw["end"], provisional[-1]))
                log(f"Provisional days from the allocation API: {', '.join(str(d) for d in provisional)} ({len(new):,} rows, pulled {api['pulled']:%d %b %H:%M})")
    # Two Sales MIS rules (reverse-engineered 2026-10-12 from the MIS's own per-executive numbers, 1 Apr - 9 Oct: 44,803 /
    # 35,107 here vs 44,804 / 35,106 there, the 1 being overnight changes):
    # (1) an appointment whose ME sits in team 'Corporate' or section 'Sales (Training)' is not a JDS-ME appointment;
    # (2) a Sunday appointment is reported on the Saturday before (the MIS has no Sundays). The real date stays in
    #     appt_date for the record checks that compare times.
    def mis_me(r):
        return (str(r.get("me_team_type_name") or "").strip().lower() != "corporate"
                and not str(r.get("me_section") or "").strip().lower().startswith("sales (training)"))
    dropped = sum(1 for r in ALL if not mis_me(r))
    ALL = [r for r in ALL if mis_me(r)]
    sundays = 0
    for r in ALL:
        d = r["to_date"]
        r["appt_date"] = d
        if d.weekday() == 6:
            r["to_date"] = d - datetime.timedelta(days=1)
            sundays += 1
    log(f"Sales MIS rules: {dropped:,} rows of Corporate / Sales (Training) MEs left out; {sundays:,} Sunday appointments reported on the Saturday before")
    # An appointment counts as given when it has a real disposition, as in the Sales MIS (reconciled 2026-10-12): the
    # table's given_count is 1 only for TME-set appointments, so BDE-set ones (given_count 0 even when visited) would be
    # missed. 'Not Counted/Cancelled' rows (cancelled, refixed, fake...) are kept apart and shown per ME.
    NCD = "Not Counted/Cancelled"
    R = [r for r in ALL if r.get("final_disposition_name") != NCD]
    NC = [r for r in ALL if r.get("final_disposition_name") == NCD]
    fy, end = raw["fy"], raw["end"]

    def table():
        names, ix = [], {}
        def get(k, v=None):
            if k not in ix:
                ix[k] = len(names); names.append(v if v is not None else k)
            return ix[k]
        return names, get, ix
    MES, me_get, _ = table()           # [code, name]
    MGRS, mg_ix, mg_map = table()     # [code, name]
    TMES, tme_get, _ = table()
    TEAMS, team_ix, _ = table()
    me_name, mg_name, tme_name = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    for r in R:
        me_name[r["me"]][tidy(r["mename"])] += 1
        mg_name[r["me_manager_code"]][tidy(r["me_manager"])] += 1
        tme_name[r["tme"]][tidy(r["tmename"])] += 1
    for r in NC:                      # names for people who only appear on not-counted appointments
        me_name[r["me"]][tidy(r["mename"])] += 0
        tme_name[r["tme"]][tidy(r["tmename"])] += 0
    usual_mgr = {}
    by_me = defaultdict(Counter)
    for r in R:
        by_me[r["me"]][r["me_manager_code"]] += 1
    for me, c in by_me.items():
        usual_mgr[me] = c.most_common(1)[0][0]

    def me_ix(code):
        return me_get(code, [code, me_name[code].most_common(1)[0][0] if me_name[code] else str(code)])

    def tme_ix(code):
        return tme_get(code, [code, tme_name[code].most_common(1)[0][0] if tme_name[code] else str(code)])

    recs = []
    bad = 0
    for r in sorted(R, key=lambda r: (r["to_date"], r["me"])):
        o = OUTCOMES.index(r["final_disposition_name"]) if r["final_disposition_name"] in OUTCOMES else -1
        # the table's counts must agree with the disposition on TME-set rows; BDE-set rows carry 0 counts by design
        if o < 0 or (r.get("given_count", 1) == 1 and ((o <= 2) != (r["attended_count"] == 1) or (o == 0) != (r["dealclosed_count"] == 1))):
            bad += 1
            continue
        mi = me_ix(r["me"])
        gi = mg_ix(r["me_manager_code"], [r["me_manager_code"], mg_name[r["me_manager_code"]].most_common(1)[0][0]])
        ti = tme_ix(r["tme"])
        tt = team_ix(r["tme_team_type_name"] or "Not recorded")
        recs.append(((r["to_date"] - fy).days, mi, gi, ti, tt, o, str(r["companyname"] or "").strip()[:60], str(r["parentid"] or ""), r))
    # deals come from the deals table (db_paidcontracts.daily_deals_closed_dump, cache\deals.pkl): an appointment is a
    # deal when its business (parentid / docid) has a deal that day. The deals table books Sunday deals on the Saturday
    # before, so a Saturday deal also counts for an appointment on the next one or two days. Each business-day deal
    # converts one appointment: the closest day, then the ME who closed it. Only an appointment the table marks attended
    # (Dealclosed / Follow Up / Not Interested) can take a deal, so attended stays the Sales MIS's count exactly; a deal
    # whose business had only not-attended appointments that day is left out (counted in deal_src.notAttended).
    deal_src = {"table": sum(1 for x in recs if x[5] == 0)}
    dpath = os.path.join(pipe, "cache", "deals.pkl")
    if os.path.exists(dpath):
        dl = pickle.load(open(dpath, "rb"))
        deals_on = defaultdict(lambda: defaultdict(set))
        for d, pid, n, me, jf in dl["deals"]:
            deals_on[pid][d].add(me)
        appts = defaultdict(list)
        for i, x in enumerate(recs):
            appts[x[7]].append(i)
        conv = [0] * len(recs)
        not_att = 0
        for pid, days in deals_on.items():
            for d, mes in days.items():
                best = None
                for i in appts.get(pid, ()):
                    if recs[i][5] > 2:
                        continue
                    gap = (fy + datetime.timedelta(days=recs[i][0]) - d).days
                    if gap == 0 or (gap in (1, 2) and d.weekday() == 5):
                        score = (gap, MES[recs[i][1]][0] not in mes, recs[i][5] > 2, conv[i])
                        if best is None or score < best[0]:
                            best = (score, i)
                if best and not conv[best[1]]:
                    conv[best[1]] = 1
                elif not best and any(((fy + datetime.timedelta(days=recs[i][0]) - d).days == 0 or (((fy + datetime.timedelta(days=recs[i][0]) - d).days in (1, 2)) and d.weekday() == 5)) for i in appts.get(pid, ())):
                    not_att += 1
        moved_in = moved_out = 0
        # days the deals tables do not cover yet (provisional days before about 10:15 am): keep the deals as recorded
        cover = max([d for d in (dl.get("dump_to"), dl.get("recent_to")) if d] or [None]) if dl.get("dump_to") else None
        for i, x in enumerate(recs):
            o = x[5]
            if cover and fy + datetime.timedelta(days=x[0]) > cover and x[8].get("to_date") and x[8]["to_date"] > cover:
                continue
            if conv[i] and o != 0:
                o, moved_in = 0, moved_in + 1             # a deal proves the visit
            elif not conv[i] and o == 0:
                o, moved_out = 1, moved_out + 1           # attended; the business's deal went to another appointment
            if o != x[5]:
                recs[i] = x[:5] + (o,) + x[6:]
        deal_src.update({"dump": sum(conv), "toDeal": moved_in, "fromDeal": moved_out, "notAttended": not_att, "pulled": dl["pulled"].strftime("%Y-%m-%dT%H:%M"),
                         "dumpTo": str(dl.get("dump_to") or ""), "recentTo": str(dl.get("recent_to") or "")})
        log(f"Deals from the deals table: {sum(conv):,} appointments converted (the appointment table marks {deal_src['table']:,}); "
            f"{moved_in} marked not deal there, {moved_out} marked deal there but their business's deal went to another appointment")
    else:
        log("deals.pkl is missing from the cache folder (run fetch_deals.py): deals are the appointment table's own Dealclosed.")

    # Deals closed, as the Sales MIS counts them (user, 15 Oct 2026: the page's 'Deals closed' = the MIS's): every deal row
    # in the deals dump (one per payment version, dc_genio) of an ME of this city that month, whether or not an
    # appointment sits behind it (fetch_deals.py MIS_SQL). These, not the Dealclosed appointments above, are the page's
    # deals closed and its conversion. Each deal sits with its ME, the ME's team leader that month, and the deal's TME
    # team (final_team_type_name; none = 'Cold call (no TME)'). Days the deals tables do not have yet (the morning's
    # provisional day) use the Dealclosed appointments of that day instead.
    deals = []   # (day, me, mgr or -1, team, dc_genio, parentid)
    mgr_month = defaultdict(Counter)
    for r in R:
        mgr_month[(str(r["me"]).strip().lstrip("0"), r["to_date"].year, r["to_date"].month)][r["me_manager_code"]] += 1
    code_of = {}
    for r in R:
        code_of.setdefault(str(r["me"]).strip().lstrip("0"), r["me"])
    mis = dl.get("mis") if os.path.exists(dpath) else None
    cover = None
    if mis is not None:
        cover = max([x for x in (dl.get("mis_to"), dl.get("dump_to"), dl.get("recent_to")) if x] or [None])
        for code, nm in (dl.get("names") or {}).items():
            if code not in code_of and nm:
                me_name[code][tidy(nm)] += 0
        for d, pid, dc, me, tme, team, jf in mis:
            if d < fy or d > end or not dc:   # dc_genio 0: a payment version that is not a deal
                continue
            code = code_of.get(me, me)
            mc = mgr_month.get((me, d.year, d.month)) or (Counter({usual_mgr[code]: 1}) if code in usual_mgr else None)
            gi = -1
            if mc:
                mg = mc.most_common(1)[0][0]
                gi = mg_ix(mg, [mg, mg_name[mg].most_common(1)[0][0] if mg_name[mg] else str(mg)])
            tt = team_ix(team if team and team.upper() != "BLANK" else "Cold call (no TME)")
            deals.append(((d - fy).days, me_ix(code), gi, tt, dc, pid))
    # days after the deals tables (or every day, when they could not be read): the Dealclosed appointments stand in, with
    # the MIS's city rule - an ME of another city that month (HR month row, else the HR master) closes deals elsewhere
    hp = os.path.join(pipe, "cache", "hr.pkl")
    hr = pickle.load(open(hp, "rb")) if os.path.exists(hp) else None
    city_l = str(raw["city"]).strip().lower()
    def here(code, d):
        if not hr:
            return True
        v = hr["days"].get((str(code).strip(), d.year, d.month))
        if v is not None:
            return v[3].strip().lower() == city_l and v[2].strip().upper() == "ME"
        m = hr["master"].get(str(code).strip())
        return not m or not m[4] or m[4].strip().lower() == city_l
    for x in recs:
        day = fy + datetime.timedelta(days=x[0])
        if x[5] == 0 and (cover is None or day > cover) and here(MES[x[1]][0], day):
            deals.append((x[0], x[1], x[2], x[4], 1.0, x[7]))
    deals.sort()
    deal_src.update({"mis": round(sum(x[4] for x in deals), 2), "misTo": str(cover or "")})
    log(f"Deals closed (Sales MIS rule): {sum(x[4] for x in deals):,.2f} from {len(deals):,} deal rows"
        + (f"; after {cover} from the Dealclosed appointments" if cover and cover < end else ""))

    # 'customer reached later': for a 'Not Available' appointment, did the same business (parentid) have an attended
    # appointment (by any ME) within the next 30 days? 0 = not 'Not Available'; 1 = yes; 2 = no; 3 = the 30 days are
    # not over yet (left out of the check).
    D_end = (end - fy).days
    attended_days = defaultdict(list)
    for x in recs:
        if x[5] <= 2 and x[7]:
            attended_days[x[7]].append(x[0])
    later = []
    for x in recs:
        if x[5] != 3:
            later.append(0)
        elif x[0] + 30 > D_end:
            later.append(3)
        else:
            later.append(1 if any(x[0] < d <= x[0] + 30 for d in attended_days.get(x[7], ())) else 2)
    log(f"'Not available' appointments with the 30 days over: {sum(1 for v in later if v in (1, 2)):,}; "
        f"customer attended within 30 days: {sum(1 for v in later if v == 1):,}")

    # each manager's own manager (when the manager is also an ME here), so a team includes everyone below
    mg_up = []
    for code, _name in MGRS:
        up = usual_mgr.get(code)
        mg_up.append(mg_map[up] if up in mg_map and up != code else -1)

    return {"provisional": provisional, "fy": fy, "end": end, "raw": raw, "rows": R, "not_counted": NC, "MES": MES, "MGRS": MGRS, "TMES": TMES,
            "TEAMS": TEAMS, "recs": recs, "bad": bad, "deal_src": deal_src, "later": later, "mg_up": mg_up,
            "me_ix": me_ix, "tme_ix": tme_ix, "deals": deals}
