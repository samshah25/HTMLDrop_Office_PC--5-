"""Manager pages (2 Nov 2026, Kushal via the user): one page per manager under the ME head, holding only that manager's
line, behind a login (serve_dashboard.py). build_review.py calls build() after it has made the full page's data.

What a manager's page holds:
  - the manager's own records in full: appointments, deals closed and not-counted appointments of the MEs in the
    manager's line (the same rules as the page's own team tree in app.js: makeTree / nodeA0 / ME_NODE0 / nodeD0 /
    inLineNC, copied below), with company, parentid and HR details, as on the full page;
  - for the Mumbai comparison lines, the rest of the ME head's line as anonymous records: no ME, no team, no company
    or parentid; only the day, TME team, outcome, check flags and times of each appointment, deals closed added up per
    day, TME team and TME, and the not-counted ones by day and kind. They all sit under one placeholder ME at the head
    of the tree, which the page never lists (the page is locked to the manager's team). The TME stays on them only for
    TMEs who also worked with the manager's MEs (for the 'same TMEs with other MEs' comparisons); every other TME
    becomes one unnamed TME;
  - no TME mode (no TME tree, calls or TME HR), no MEs outside the ME head's line, no other team's names.
"""
import base64
import json
import os
import re
from array import array

REST_NAME = "Rest of the ME head's line"   # the placeholder ME; the page never shows it
ANON_TME = "TME"                           # the one unnamed TME on the anonymous records


def _un(code, s):
    a = array(code)
    a.frombytes(base64.b64decode(s))
    return a.tolist()


def _pk(code, values):
    return base64.b64encode(array(code, values).tobytes()).decode()


def ncode(s):
    return str(s).strip().lstrip("0")


def tree(data):
    """the page's ME tree, as app.js builds it from the full data (makeTree with root -1, then the line filter's nodes)"""
    G, UP = data["mgrs"], data["mgUp"]
    NG0, OUT = len(G), len(G)
    A, DL, NC = data["a"], data["dl"], data["nc"]
    AD, AME, AG = _un("H", A["d"]), _un("H", A["me"]), _un("H", A["mg"])
    DLME, DLMG = _un("H", DL["me"]), _un("H", DL["mg"])
    NCME = _un("H", NC["me"])
    LAST = data["meta"]["days"] - 1
    HEAD = []
    for m in range(NG0):
        c, seen = m, {m}
        while UP[c] >= 0 and UP[c] not in seen:
            c = UP[c]
            seen.add(c)
        HEAD.append(c)
    cnt = [0] * NG0
    for i in range(len(AD)):
        if AG[i] < NG0 and AD[i] >= LAST - 60:
            cnt[HEAD[AG[i]]] += 1
    R0 = 0
    for m in range(1, NG0):
        if cnt[m] > cnt[R0]:
            R0 = m

    def depth(m):
        d, c, seen = 0, m, set()
        while c != R0:
            if c < 0 or c in seen:
                return -1
            seen.add(c)
            c = UP[c]
            d += 1
        return d
    DEPTH = [depth(m) for m in range(NG0)]

    def teamof(m):
        if DEPTH[m] < 0:
            return OUT
        c = m
        while DEPTH[c] > 2:
            c = UP[c]
        return c
    TEAMOF = [teamof(m) for m in range(NG0)]
    LEAD_OF = {}
    for m, x in enumerate(G):
        if DEPTH[m] >= 0 and x[0]:
            LEAD_OF[ncode(x[0])] = m
    OWN = []
    for x in data["mes"]:
        m = LEAD_OF.get(ncode(x[0])) if x[0] else None
        OWN.append(-1 if m is None else TEAMOF[m])

    def node_a(i):
        o = OWN[AME[i]]
        return o if o >= 0 else TEAMOF[AG[i]] if AG[i] < NG0 else OUT
    ANODE = [node_a(i) for i in range(len(AD))]
    cnt2 = {}
    for i in range(len(AD)):
        k = AME[i] * 65536 + ANODE[i]
        cnt2[k] = cnt2.get(k, 0) + 1
    ME_NODE = [-1] * len(data["mes"])
    bn = [0] * len(data["mes"])
    for k, v in cnt2.items():   # insertion order, strictly more wins: as the page's Map
        me = k // 65536
        if v > bn[me]:
            bn[me], ME_NODE[me] = v, k % 65536

    def node_d(j):
        me = DLME[j]
        o = OWN[me]
        return o if o >= 0 else TEAMOF[DLMG[j]] if DLMG[j] < NG0 else ME_NODE[me] if ME_NODE[me] >= 0 else OUT
    DNODE = [node_d(j) for j in range(len(DLME))]
    NCNODE = [ME_NODE[me] if ME_NODE[me] >= 0 and ME_NODE[me] != OUT else OUT for me in NCME]

    def mgr_of(node):
        """the manager (a node one below the head) a team sits under; -1 the head's own; None outside the line"""
        if node == OUT or node < 0:
            return None
        c, g = node, 0
        while DEPTH[c] > 1 and g < 8:
            c, g = UP[c], g + 1
        return c if DEPTH[c] == 1 else -1 if c == R0 else None
    return {"R0": R0, "DEPTH": DEPTH, "UP": UP, "OUT": OUT, "ANODE": ANODE, "DNODE": DNODE, "NCNODE": NCNODE, "mgr_of": mgr_of}


def managers(data, T=None):
    """the nodes one below the ME head that lead a team (the page's 'Managers under ...'), with their record counts"""
    T = T or tree(data)
    out = []
    for m, x in enumerate(data["mgrs"]):
        if T["DEPTH"][m] != 1:
            continue
        n = sum(1 for nd in T["ANODE"] if T["mgr_of"](nd) == m)
        out.append({"node": m, "code": str(x[0]).strip(), "name": str(x[1]).strip(), "appts": n})
    return out


def filtered(data, m, T):
    """the data of manager node m's page"""
    mgr_of, R0 = T["mgr_of"], T["R0"]
    A, DL, NC, HR = data["a"], data["dl"], data["nc"], data["hr"]
    a = {k: _un(c, A[k]) for k, c in (("d", "H"), ("me", "H"), ("mg", "H"), ("tme", "H"), ("tt", "B"), ("o", "B"), ("rl", "B"),
                                       ("f", "B"), ("sl", "i"), ("bk", "i"), ("en", "i"), ("dc", "i"))}
    dl = {k: _un(c, DL[k]) for k, c in (("d", "H"), ("me", "H"), ("mg", "H"), ("tt", "B"), ("w", "f"), ("tm", "H"), ("rv", "f"))}
    nc = {k: _un(c, NC[k]) for k, c in (("d", "H"), ("me", "H"), ("tme", "H"), ("k", "B"), ("bk", "i"), ("sl", "i"), ("tt", "B"))}
    # which records are the manager's (mine), the rest of the head's line (rest), or outside the line (dropped)
    side = lambda node: None if mgr_of(node) is None else "mine" if mgr_of(node) == m else "rest"
    sa = [side(nd) for nd in T["ANODE"]]
    sd = [side(nd) for nd in T["DNODE"]]
    sn = [side(nd) for nd in T["NCNODE"]]

    # the nodes kept: the head and the manager's subtree; the head has nobody above it here
    keep_n = [x for x in range(len(data["mgrs"])) if x == R0 or (T["DEPTH"][x] >= 1 and mgr_of(x) == m)]
    NIX = {x: k for k, x in enumerate(keep_n)}
    mgrs = [data["mgrs"][x] for x in keep_n]
    mg_up = [-1 if x == R0 else NIX.get(T["UP"][x], -1) for x in keep_n]
    mapn = lambda x: NIX.get(x, 65535)
    root = NIX[R0]

    # the people kept: the manager's line's MEs, then the placeholder ME for the rest
    used = sorted({a["me"][i] for i in range(len(sa)) if sa[i] == "mine"} | {dl["me"][j] for j in range(len(sd)) if sd[j] == "mine"}
                  | {nc["me"][k] for k in range(len(sn)) if sn[k] == "mine"})
    MIX = {x: k for k, x in enumerate(used)}
    REST = len(used)
    mes = [data["mes"][x] for x in used] + [["", REST_NAME]]
    # the TMEs kept: those on the manager's records; the rest's TMEs keep their name only when they are one of those
    tm_used = sorted({a["tme"][i] for i in range(len(sa)) if sa[i] == "mine"} | {dl["tm"][j] for j in range(len(sd)) if sd[j] == "mine" and dl["tm"][j] != 65535}
                     | {nc["tme"][k] for k in range(len(sn)) if sn[k] == "mine"})
    tm_used = [x for x in tm_used if x < len(data["tmes"])]
    TIX = {x: k for k, x in enumerate(tm_used)}
    ANON = len(tm_used)
    tmes = [data["tmes"][x] for x in tm_used] + [["", ANON_TME]]
    tmap = lambda x: TIX.get(x, ANON) if x < len(data["tmes"]) else x

    # appointments, in their original order: the manager's in full, the rest without ME, team, company or parentid
    A2 = {k: [] for k in a}
    co, pid = [], []
    for i in range(len(sa)):
        if sa[i] is None:
            continue
        mine = sa[i] == "mine"
        A2["d"].append(a["d"][i]); A2["tt"].append(a["tt"][i]); A2["o"].append(a["o"][i]); A2["rl"].append(a["rl"][i]); A2["f"].append(a["f"][i])
        A2["sl"].append(a["sl"][i]); A2["bk"].append(a["bk"][i]); A2["en"].append(a["en"][i]); A2["dc"].append(a["dc"][i])
        A2["tme"].append(TIX[a["tme"][i]] if mine and a["tme"][i] in TIX else tmap(a["tme"][i]))
        A2["me"].append(MIX[a["me"][i]] if mine else REST)
        A2["mg"].append(mapn(a["mg"][i]) if mine else root)
        co.append(data["co"][i] if mine else "")
        pid.append(data["pid"][i] if mine else "")
    # deals closed: the manager's one by one; the rest added up per day, TME team and TME
    D2 = {k: [] for k in dl}
    dpid = []
    rest = {}
    for j in range(len(sd)):
        if sd[j] == "mine":
            D2["d"].append(dl["d"][j]); D2["me"].append(MIX[dl["me"][j]]); D2["mg"].append(mapn(dl["mg"][j])); D2["tt"].append(dl["tt"][j])
            D2["w"].append(dl["w"][j]); D2["tm"].append(TIX.get(dl["tm"][j], ANON) if dl["tm"][j] != 65535 else 65535); D2["rv"].append(dl["rv"][j])
            dpid.append(data["dl"]["pid"][j] if data["dl"].get("pid") else "")
        elif sd[j] == "rest":
            tm = 65535 if dl["tm"][j] == 65535 else TIX.get(dl["tm"][j], ANON)
            k = (dl["d"][j], dl["tt"][j], tm)
            s = rest.setdefault(k, [0.0, 0.0])
            s[0] += dl["w"][j]; s[1] += dl["rv"][j]
    for (d, tt, tm), (w, rv) in rest.items():
        D2["d"].append(d); D2["me"].append(REST); D2["mg"].append(root); D2["tt"].append(tt); D2["w"].append(w); D2["tm"].append(tm); D2["rv"].append(rv)
        dpid.append("")
    order = sorted(range(len(D2["d"])), key=lambda j: D2["d"][j])
    D2 = {k: [v[j] for j in order] for k, v in D2.items()}
    dpid = [dpid[j] for j in order]
    # not counted as given: the manager's in full; the rest without ME, company or parentid
    N2 = {k: [] for k in nc}
    nco, npid = [], []
    for k in range(len(sn)):
        if sn[k] is None:
            continue
        mine = sn[k] == "mine"
        N2["d"].append(nc["d"][k]); N2["k"].append(nc["k"][k]); N2["bk"].append(nc["bk"][k]); N2["sl"].append(nc["sl"][k]); N2["tt"].append(nc["tt"][k])
        N2["me"].append(MIX[nc["me"][k]] if mine else REST)
        N2["tme"].append(TIX[nc["tme"][k]] if mine and nc["tme"][k] in TIX else tmap(nc["tme"][k]))
        nco.append(NC["co"][k] if mine else "")
        npid.append(NC["pid"][k] if mine else "")

    # HR, per ME kept (and an empty record for the placeholder)
    NM = len(data["meta"]["months"])
    days, mis = _un("H", HR["days"]), _un("B", HR["mis"]) if HR.get("mis") else []
    hd, hm = [], []
    for x in used:
        hd += days[x * NM:(x + 1) * NM]
        hm += mis[x * NM:(x + 1) * NM] if mis else []
    hd += [65535] * NM
    hm += [2] * NM if mis else []
    pick = lambda arr: [arr[x] for x in used] + [""] if arr else []

    meta = dict(data["meta"])
    meta["mgr"] = {"node": NIX[m], "code": str(data["mgrs"][m][0]).strip(), "name": str(data["mgrs"][m][1]).strip(), "rest": REST}
    meta["check"] = dict(meta.get("check") or {})
    out = {
        "meta": meta, "mes": mes, "mgrs": mgrs, "mgUp": mg_up, "tmes": tmes, "teams": data["teams"],
        "a": {"n": len(A2["d"]), **{k: _pk(c, A2[k]) for k, c in (("d", "H"), ("me", "H"), ("mg", "H"), ("tme", "H"), ("tt", "B"), ("o", "B"),
                                                                  ("rl", "B"), ("f", "B"), ("sl", "i"), ("bk", "i"), ("en", "i"), ("dc", "i"))}},
        "co": co, "pid": pid,
        "dl": {"n": len(D2["d"]), **{k: _pk(c, D2[k]) for k, c in (("d", "H"), ("me", "H"), ("mg", "H"), ("tt", "B"), ("w", "f"), ("tm", "H"), ("rv", "f"))},
               "pid": dpid},
        "nc": {"n": len(N2["d"]), **{k: _pk(c, N2[k]) for k, c in (("d", "H"), ("me", "H"), ("tme", "H"), ("k", "B"), ("bk", "i"), ("sl", "i"), ("tt", "B"))},
               "kinds": NC["kinds"], "co": nco, "pid": npid},
        "hr": {"days": _pk("H", hd), "j": pick(HR.get("j")), "des": pick(HR.get("des")), "city": pick(HR.get("city")),
               "grade": pick(HR.get("grade")), "mis": _pk("B", hm)},
    }
    stats = {"mine": sa.count("mine"), "rest": sa.count("rest"), "out": sa.count(None), "mes": len(used), "tmes": len(tm_used),
             "nodes": len(keep_n), "deals_mine": round(sum(dl["w"][j] for j in range(len(sd)) if sd[j] == "mine"), 2),
             "deals_rest": round(sum(dl["w"][j] for j in range(len(sd)) if sd[j] == "rest"), 2)}
    return out, stats


def build(data, assemble, out_dir, log):
    """writes out_dir\\<manager code>.html for every manager under the ME head, and out_dir\\managers.json (code, name,
    file, counts) for the login server; assemble(blob) turns a data blob into a page"""
    T = tree(data)
    ms = managers(data, T)
    os.makedirs(out_dir, exist_ok=True)
    listing = []
    for x in ms:
        d, st = filtered(data, x["node"], T)
        blob = json.dumps(d, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        page = assemble(blob)
        safe = re.sub(r"[^0-9A-Za-z]", "", x["code"]) or f"node{x['node']}"
        path = os.path.join(out_dir, safe + ".html")
        tmp = path + ".tmp"
        open(tmp, "w", encoding="utf-8").write(page)
        os.replace(tmp, path)
        listing.append({"code": x["code"], "name": x["name"], "file": safe + ".html", **st})
        log(f"Manager page {x['name']}: {st['mine']:,} appointments, {st['deals_mine']:,} deals closed, {st['mes']} MEs "
            f"(+ {st['rest']:,} anonymous appointments of the rest of the line; {len(page) / 1e6:.1f} MB)")
    json.dump({"head": str(data["mgrs"][T["R0"]][1]), "managers": listing}, open(os.path.join(out_dir, "managers.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return listing
