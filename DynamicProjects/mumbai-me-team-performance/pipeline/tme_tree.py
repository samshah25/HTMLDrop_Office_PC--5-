"""The TME tree for the dashboard's TME mode (29 Oct 2026): TME head > managers > team leaders > TMEs.

Team leader = the appointment's tme_manager: a name, as it was on the day of the appointment (TMEs move between team
leaders; 352 of 1,001 did in the FY). Its employee code comes from the SSO lines (tme_lines.json, from the SSO dump):
the person of that name who is the direct manager (Reporting-1) of the appointment's TMEs, else the one person of that
name in the lines. An appointment with no tme_manager takes the TME's own direct manager in the lines. Above a team
leader: each person's direct manager in the lines. The TME head is the lowest person whose line covers 90% or more of
the last 60 days' appointments (Deepak Thukral, VP - Tele Marketing, on 29 Oct 2026); everyone above the head is left
out, so a line that does not pass through the head ends below it (the page groups those TMEs apart, as it does the MEs
outside the ME head's line). A team leader whose name cannot be matched is a team of their own with no line above.

A deal closed carries the deal record's TME; its team leader is that TME's usual team leader on their appointments in
the deal's month, else in the year, else the TME's direct manager in the lines.
"""
import datetime
import json
import os
import re
from collections import Counter, defaultdict

COVER = 0.9      # the head's line covers this share of the last 60 days' appointments
NONE = 65535


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def code(v):
    return str(v or "").strip().lstrip("0")


def tidy_name(s):
    return " ".join(str(s or "").split())


def build(P, pipe, log):
    path = os.path.join(pipe, "tme_lines.json")
    if not os.path.exists(path):
        log("tme_lines.json is missing (run tme_lines.py with an SSO dump): the page has no TME mode.")
        return None
    L = json.load(open(path, encoding="utf-8"))
    people = L["people"]   # code -> [name, designation, status, reporting-1 code, joined]
    recs, TMES, DL, end = P["recs"], P["TMES"], P["deals"], P["end"]
    fy = P["fy"]
    D_end = (end - fy).days

    # a team leader's name -> code: the direct manager of the appointment's TMEs with that name, else the one person
    by_r1 = defaultdict(Counter)
    for x in recs:
        nm = norm(x[8].get("tme_manager"))
        p = people.get(code(TMES[x[3]][0]))
        if nm and p and p[3] in people and norm(people[p[3]][0]) == nm:
            by_r1[nm][p[3]] += 1
    by_name = defaultdict(list)
    for c, p in people.items():
        by_name[norm(p[0])].append(c)
    name_code, unmatched = {}, Counter()
    for x in recs:
        nm = norm(x[8].get("tme_manager"))
        if not nm or nm in name_code:
            continue
        if by_r1.get(nm):
            name_code[nm] = by_r1[nm].most_common(1)[0][0]
        elif len(by_name.get(nm, [])) == 1:
            name_code[nm] = by_name[nm][0]
        else:
            name_code[nm] = None

    # each appointment's team leader: a code, or ('name', ...) when it cannot be matched
    def tl_key(x):
        nm = norm(x[8].get("tme_manager"))
        if nm:
            c = name_code.get(nm)
            return c if c else ("name", nm, tidy_name(x[8].get("tme_manager")))
        p = people.get(code(TMES[x[3]][0]))
        return p[3] if p and p[3] else None
    keys = [tl_key(x) for x in recs]
    for x, k in zip(recs, keys):
        if isinstance(k, tuple):
            unmatched[k[2]] += 1

    # chains above each team leader, and the head: the lowest person covering COVER of the last 60 days
    def chain(c):
        out, seen = [], set()
        while c and c in people and c not in seen:
            seen.add(c); out.append(c); c = people[c][3]
        return out
    cover, recent = Counter(), 0
    for x, k in zip(recs, keys):
        if x[0] < D_end - 60 or not k or isinstance(k, tuple):
            continue
        recent += 1
        for c in chain(k):
            cover[c] += 1
    cands = [c for c, n in cover.items() if n >= COVER * recent]
    head = min(cands, key=lambda c: (cover[c], c)) if cands else None
    above = set(chain(people[head][3])) if head and people[head][3] else set()

    nodes, ix = [], {}
    def node(k):
        if k in ix:
            return ix[k]
        if isinstance(k, tuple):
            ix[k] = len(nodes); nodes.append(["", k[2]]); return ix[k]
        ix[k] = len(nodes); nodes.append([k, tidy_name(people[k][0]) if k in people else k])
        return ix[k]
    atl = []
    for k in keys:
        if not k or k in above:
            atl.append(NONE); continue
        i = node(k)
        if not isinstance(k, tuple):   # everyone above, down from the head
            for c in chain(k)[1:]:
                if c in above:
                    break
                node(c)
        atl.append(i)
    up = []
    for c, _nm in nodes:
        u = people[c][3] if c and c in people else ""
        up.append(ix[u] if u and u in ix and u not in above and c != head else -1)
    root = ix.get(head, -1)

    # each TME's team leader by month and over the year (for the deals closed)
    by_month, by_year = defaultdict(Counter), defaultdict(Counter)
    for x, t in zip(recs, atl):
        if t == NONE:
            continue
        d = fy + datetime.timedelta(days=x[0])
        by_month[(x[3], d.year, d.month)][t] += 1
        by_year[x[3]][t] += 1
    dtl = []
    for x in DL:
        tm = x[6]
        if tm < 0:
            dtl.append(NONE); continue
        d = fy + datetime.timedelta(days=x[0])
        c = by_month.get((tm, d.year, d.month)) or by_year.get(tm)
        if c:
            dtl.append(c.most_common(1)[0][0]); continue
        p = people.get(code(TMES[tm][0]))
        dtl.append(ix[p[3]] if p and p[3] in ix else NONE)

    depth = []
    for i in range(len(nodes)):
        d, c, seen = 0, i, set()
        while c != root and c >= 0 and c not in seen:
            seen.add(c); c = up[c]; d += 1
        depth.append(d if c == root else -1)
    dn = Counter(depth)
    log(f"TME tree: head {nodes[root][1] if root >= 0 else '(none)'}"
        f" ({people[head][1] if head in people else ''}; covers {cover.get(head, 0) / max(1, recent):.0%} of the last 60 days); "
        f"{dn.get(1, 0)} below the head, {dn.get(2, 0)} below those, {sum(v for k, v in dn.items() if k > 2)} further down, "
        f"{dn.get(-1, 0)} outside the head's line; "
        f"{sum(1 for t in atl if t == NONE)} appointments with no team leader"
        + (f"; names not matched to the SSO lines: {', '.join(f'{k} ({v})' for k, v in unmatched.most_common(5))}" if unmatched else ""))
    # the TMEs' designation and joining date in the lines (the HR record wins when there is one)
    des, joined = [], []
    for c, _nm in TMES:
        p = people.get(code(c))
        des.append(p[1] if p else ""); joined.append(p[4] if p else "")
    return {"nodes": nodes, "up": up, "root": root, "atl": atl, "dtl": dtl, "des": des, "j": joined,
            "src": L.get("source", ""), "srcDate": L.get("sourceDate", ""), "read": L.get("read", "")}
