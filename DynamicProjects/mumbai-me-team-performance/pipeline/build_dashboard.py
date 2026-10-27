"""Step 2 of the refresh: turn cache\\raw.pkl into the ME team dashboard (one self-contained .html).

Every appointment given to an ME ships to the page as a compact record (day, ME, manager, TME, TME team, outcome), so
the page can add up any period, team, ME or lead source itself. Nothing is estimated.

The records and the deal rule are in records.py (shared with build_review.py).

    python build_dashboard.py          data only: swaps the data inside the existing page, keeps its design
    python build_dashboard.py --full   rebuilds the page from the design files in pipeline\\app
"""
import base64
from array import array
import datetime
import json
import os
import re
import sys

from records import OUTCOMES, prepare, tidy

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
APP = os.path.join(PIPE, "app")
DEFAULT_PAGE = "jd-me-team-performance.html"
DATA_FORMAT = 1


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def dashboard_file():
    if os.environ.get("ME_DASH_OUT"):
        return os.environ["ME_DASH_OUT"]
    pages = sorted(f for f in os.listdir(KIT) if f.lower().endswith(".html"))
    return os.path.join(KIT, pages[0] if len(pages) == 1 else DEFAULT_PAGE)


def main():
    P = prepare(PIPE, log)
    R, fy, end, raw = P["rows"], P["fy"], P["end"], P["raw"]
    MES, MGRS, TMES, TEAMS = P["MES"], P["MGRS"], P["TMES"], P["TEAMS"]
    recs, bad, deal_src, later, mg_up = P["recs"], P["bad"], P["deal_src"], P["later"], P["mg_up"]

    # ---- self-check: what the page will count vs the table ----
    n_given = len(R) - bad
    n_att = sum(1 for x in recs if x[5] <= 2)
    n_deal = sum(1 for x in recs if x[5] == 0)
    want_att = sum(1 for r in R if r["final_disposition_name"] in ("Dealclosed", "Follow Up", "Not Interested"))   # the MIS's attended
    want_deal = deal_src.get("dump", deal_src["table"])
    log(f"Appointments {len(recs):,} (left out, outcome not one of the six or flags disagree: {bad}); attended {n_att:,} "
        f"(table {want_att:,}); deals {n_deal:,} (table {want_deal:,})")
    if bad > len(R) * 0.01:
        sys.exit("More than 1% of appointments have an unknown outcome; the page was not changed.")

    assert sys.byteorder == "little"
    def pack(code, values):
        return base64.b64encode(array(code, values).tobytes()).decode()
    D = (end - fy).days + 1
    data = {
        "meta": {"city": tidy(raw["city"]), "fy": fy.isoformat(), "end": end.isoformat(), "days": D,
                 "refreshed": raw["pulled"].strftime("%Y-%m-%dT%H:%M"), "outcomes": OUTCOMES,
                 "check": {"given": len(recs), "attended": n_att, "deals": n_deal, "left_out": bad}, "dealSrc": deal_src},
        "mes": MES, "mgrs": MGRS, "mgUp": mg_up, "tmes": TMES, "teams": TEAMS,
        "a": {"n": len(recs), "d": pack("H", [x[0] for x in recs]), "me": pack("H", [x[1] for x in recs]),
              "mg": pack("H", [x[2] for x in recs]), "tme": pack("H", [x[3] for x in recs]),
              "tt": pack("B", [x[4] for x in recs]), "o": pack("B", [x[5] for x in recs]), "rl": pack("B", later)},
        "co": [x[6] for x in recs], "pid": [x[7] for x in recs],
    }
    assert len(MES) < 65536 and len(MGRS) < 65536 and len(TMES) < 65536 and len(TEAMS) < 256
    blob = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    log(f"Data: {len(blob) / 1e6:.1f} MB; {len(MES):,} MEs, {len(MGRS):,} managers, {len(TMES):,} TMEs, {len(TEAMS)} TME teams")

    out = dashboard_file()
    MARK = '<script type="application/json" id="data">'
    if "--full" not in sys.argv and os.path.exists(out):
        page = open(out, encoding="utf-8").read()
        fmt = re.search(r'<meta name="jd-data-format" content="(\d+)">', page)
        if not fmt or int(fmt.group(1)) != DATA_FORMAT or MARK not in page:
            sys.exit(f"{os.path.basename(out)} needs a different data format; ask Sarvesh for the matching pipeline files. The page has not been changed.")
        start = page.index(MARK) + len(MARK)
        stop = page.index("</script>", start)
        page = page[:start] + blob + page[stop:]
        how = "data updated; design kept"
    else:
        shell = open(os.path.join(APP, "shell.tpl"), encoding="utf-8").read()
        css = open(os.path.join(APP, "app.css"), encoding="utf-8").read()
        js = open(os.path.join(APP, "app.js"), encoding="utf-8").read()
        fonts = ""
        fdir = os.path.join(APP, "fonts")
        for f in sorted(os.listdir(fdir)):
            mm = re.match(r"(.+)-(\d{3}|var)\.woff2$", f)
            if mm:
                weight = "100 900" if mm.group(2) == "var" else mm.group(2)
                fonts += (f"@font-face{{font-family:'{mm.group(1)}';font-style:normal;font-weight:{weight};font-display:swap;"
                          f"src:url(data:font/woff2;base64,{base64.b64encode(open(os.path.join(fdir, f), 'rb').read()).decode()}) format('woff2');}}")
        logo = "data:image/png;base64," + base64.b64encode(open(os.path.join(APP, "jd_logo.png"), "rb").read()).decode()
        page = shell.replace("/*FONTS*/", fonts).replace("/*CSS*/", css).replace("/*LOGO*/", logo).replace("/*DATA*/", blob).replace("/*JS*/", js)
        page = page.replace("<head>", f'<head>\n<meta name="jd-data-format" content="{DATA_FORMAT}">', 1)
        how = "built from the design files"
    tmp = out + ".tmp"
    open(tmp, "w", encoding="utf-8").write(page)
    os.replace(tmp, out)
    log(f"Wrote {out} ({len(page) / 1e6:.1f} MB, {how})")


if __name__ == "__main__":
    sys.exit(main())
