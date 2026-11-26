"""TME reporting lines for the dashboard's TME mode (29 Oct 2026), from the SSO dump (the official employee list with
Reporting-1..8; Reporting-1 = the direct manager).

    python tme_lines.py                 reads the newest "SSO dump*.xlsx" in ..\\exports or in this folder
    python tme_lines.py "<file>.xlsx"   reads that file

Writes tme_lines.json next to this script: every employee of the city's branch (cache\\raw.pkl's city; Mumbai) and
everyone above them in their reporting chains, with the work fields only: name, designation, status, direct manager's
code, joining date. Birth date, phone and e-mail are never copied. The SSO dump is a snapshot: run this again when a
newer one arrives (main.py does it on its own when a newer SSO dump sits in exports\\). build_review.py reads the json;
the dump itself is not needed for a refresh.
"""
import datetime
import glob
import json
import os
import pickle
import sys

import openpyxl

PIPE = os.path.dirname(os.path.abspath(__file__))
import kitpaths
OUT = os.path.join(PIPE, "tme_lines.json")
FIELDS = ["Emp Code", "Emp Name", "Branch", "Status", "Designation", "DOJ"] + [f"Reporting-{k}" for k in range(1, 9)]


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def newest_dump():
    """the newest SSO dump in ..\\exports or this folder, or None"""
    found = glob.glob(os.path.join(PIPE, "..", "exports", "SSO dump*.xlsx")) + glob.glob(os.path.join(PIPE, "SSO dump*.xlsx"))
    found = [f for f in found if not os.path.basename(f).startswith("~$")]
    return max(found, key=os.path.getmtime) if found else None


def code(v):
    return str(v or "").strip().lstrip("0")


def day(v):
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    return ""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else newest_dump()
    if not src or not os.path.exists(src):
        sys.exit("No SSO dump found (put \"SSO dump ... .xlsx\" in exports\\ or name the file). tme_lines.json was not changed.")
    city = "Mumbai"
    rp = os.path.join(kitpaths.CACHE, "raw.pkl")
    if os.path.exists(rp):
        city = str(pickle.load(open(rp, "rb"))["city"]).strip() or city
    t0 = datetime.datetime.now()
    wb = openpyxl.load_workbook(src, read_only=True)
    rows = wb.active.iter_rows(values_only=True)
    hdr = [str(h).strip() if h is not None else "" for h in next(rows)]
    missing = [f for f in FIELDS if f not in hdr]
    if missing:
        sys.exit(f"{os.path.basename(src)} has no column {', '.join(missing)}. tme_lines.json was not changed.")
    ix = {f: hdr.index(f) for f in FIELDS}
    everyone, branch = {}, set()
    for r in rows:
        c = code(r[ix["Emp Code"]])
        if not c:
            continue
        everyone[c] = [" ".join(str(r[ix["Emp Name"]] or "").split()), " ".join(str(r[ix["Designation"]] or "").split()),
                       str(r[ix["Status"]] or "").strip(), code(r[ix["Reporting-1"]]), day(r[ix["DOJ"]]),
                       [code(r[ix[f"Reporting-{k}"]]) for k in range(1, 9)]]
        if str(r[ix["Branch"]] or "").strip().lower() == city.lower():
            branch.add(c)
    keep = set(branch)
    for c in branch:
        keep.update(x for x in everyone[c][5] if x)
    people = {c: everyone[c][:5] for c in sorted(keep) if c in everyone}
    out = {"source": os.path.basename(src), "sourceDate": datetime.date.fromtimestamp(os.path.getmtime(src)).isoformat(),
           "read": datetime.date.today().isoformat(), "city": city,
           "fields": ["name", "designation", "status", "reporting1", "joined"], "people": people}
    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    log(f"{os.path.basename(src)}: {len(branch):,} {city} employees and {len(people) - len(branch):,} people above them "
        f"-> tme_lines.json ({os.path.getsize(OUT) / 1e6:.1f} MB, {(datetime.datetime.now() - t0).seconds}s)")


if __name__ == "__main__":
    sys.exit(main())
