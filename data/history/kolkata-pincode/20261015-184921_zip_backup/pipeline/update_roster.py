"""
Kolkata JDA deployment roster: pull the JDA heads' live Google Sheet and write it into the dashboards' JDA_DEPLOYMENT.

The sheet (Employee Id, Employee Name, Reporting Head Code, Reporting Head Name, Pincode; one row per JDA x pincode)
is kept up to date by the JDA heads, so this runs after every refresh and can also be run on its own at any time
(~5 s, no database needed):   python update_roster.py

- EXCLUDED_EMPLOYEES are skipped (Sarvesh, 2026-09-28: the bottom 16 JDAs under Partha Pratim Singha Roy, whose pincodes
  are being corrected -- their cells are mangled, e.g. '700,087,700,157,...'). Remove IDs here once fixed.
- Any other row whose pincode isn't 6 digits is skipped and counted in meta, never guessed.
- Pincodes outside the Kolkata-branch list are kept out of the table (counted in meta).
- If the sheet can't be read, the dashboards keep their current roster (exit code 0, logged), so a Google hiccup never
  breaks the daily run.
Writes both the pipeline page (JDA_JDS_Kolkata_Pincode_Dashboard_Lite.page, which build_subvertical copies from) and the
SubVertical page, atomically.
"""
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.request

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(PIPE_DIR)
SHEET_ID = "1j5ORn5_3_U9CFslqJR0Y2QI6p95OebjrPHVMIHzy_bA"
SHEET_GID = "0"
SHEET_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
# the pipeline's working file (pipeline\base\ in a package, else the sales-group page) first, then the dashboard
PAGES = [p for p in (os.path.join(PIPE_DIR, "base", "JDA_JDS_Kolkata_Pincode_Dashboard_Lite.page"),
                     os.path.join(PKG_DIR, "JDA_JDS_Kolkata_Pincode_Dashboard_Lite.page"),
                     os.path.join(PKG_DIR, "JDA_JDS_Kolkata_Pincode_Dashboard_Lite_SubVertical.page")) if os.path.exists(p)]
EXCLUDED_EMPLOYEES = {  # pincodes being corrected by their head (2026-09-28)
    "10149522", "10157214", "10168521", "10174226", "10180229", "10181037", "10189100", "10189755",
    "10193346", "10193347", "10194986", "10196172", "10196153", "10196685", "10196688", "10197284",
}
CACHE = os.path.join(PIPE_DIR, "roster_sheet_last.csv")  # last good download, for reference / debugging
LOG = os.path.join(PIPE_DIR, "refresh_log.txt")


def log(msg):
    line = f"[{dt.datetime.now().isoformat(timespec='seconds')}] update_roster: {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def const_span(s, name):
    m = re.search(r"([\n;])const " + name + r" = ", s)
    if not m:
        return None
    start = m.end()
    obj, n = json.JSONDecoder().raw_decode(s[start:])
    return start, start + n, obj


def main():
    try:
        with urllib.request.urlopen(SHEET_CSV, timeout=30) as r:
            text = r.read().decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        need = {"Employee Id", "Employee Name", "Reporting Head Name", "Pincode"}
        if not rows or not need <= set(rows[0].keys()):
            raise ValueError(f"unexpected sheet columns: {list(rows[0].keys()) if rows else 'no rows'}")
    except Exception as e:
        log(f"WARNING: could not read the roster sheet ({type(e).__name__}: {e}) -- dashboards keep their current roster.")
        return 0
    with open(CACHE, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    base = open(PAGES[0], encoding="utf-8").read()
    union = {str(p) for p in const_span(base, "DATA")[2]["union_pincodes"]}
    deployed, emps, heads = {}, set(), set()
    excl_emp_rows, bad_pin_rows, outside_rows, dup_rows = 0, 0, 0, 0
    excluded_seen, outside_pins = set(), set()
    for r in rows:
        eid = (r.get("Employee Id") or "").strip()
        name = (r.get("Employee Name") or "").strip()
        pin = (r.get("Pincode") or "").strip()
        if not eid:
            continue
        if eid in EXCLUDED_EMPLOYEES:
            excl_emp_rows += 1
            excluded_seen.add(eid)
            continue
        if not re.fullmatch(r"\d{6}", pin):
            bad_pin_rows += 1
            continue
        if pin not in union:
            outside_rows += 1
            outside_pins.add(pin)
            continue
        lst = deployed.setdefault(pin, [])
        if any(x["id"] == eid for x in lst):
            dup_rows += 1
            continue
        head = (r.get("Reporting Head Name") or "").strip()
        lst.append({"id": eid, "name": name, "head": head})
        emps.add(eid)
        heads.add(head)
    fetched = dt.datetime.now().strftime("%d %b %Y, %I:%M %p")
    payload = {"deployed": deployed, "meta": {
        "source_file": "Live roster sheet (JDA heads)", "live": True, "fetched_at": fetched,
        "scope": "Live roster kept by the JDA heads; applies to whatever period is selected",
        "employees": len(emps), "heads": sorted(heads), "pincodes": len(deployed),
        "excluded_employees": len(excluded_seen), "excluded_employee_rows": excl_emp_rows,
        "bad_pincode_rows": bad_pin_rows, "outside_branch_rows": outside_rows,
        "outside_branch_pincodes": sorted(outside_pins), "duplicate_rows": dup_rows,
    }}
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    for page in PAGES:
        s = open(page, encoding="utf-8").read()
        span = const_span(s, "JDA_DEPLOYMENT")
        if not span:
            log(f"WARNING: no JDA_DEPLOYMENT in {os.path.basename(page)} -- skipped.")
            continue
        s = s[:span[0]] + js + s[span[1]:]
        tmp = page + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        os.replace(tmp, page)
    log(f"roster: {len(emps)} JDAs on {len(deployed)} pincodes (heads: {', '.join(sorted(heads))}); skipped "
        f"{len(excluded_seen)} excluded JDAs ({excl_emp_rows} rows), {bad_pin_rows} bad-pincode rows, "
        f"{outside_rows} rows outside the Kolkata list {sorted(outside_pins)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
