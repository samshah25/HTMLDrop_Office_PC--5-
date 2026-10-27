r"""
Refresh the Mumbai JDA dashboard: THE ONLY SCRIPT YOU NEED TO RUN.

It pulls data up to yesterday and puts it into JDA_JDS_Mumbai_Pincode_Dashboard.html, KEEPING THAT PAGE'S DESIGN. So when Sarvesh
sends a new version of the page, drop it into this folder (same name, replacing the old one) and the next refresh
fills it with fresh data. Only when a new page needs data this kit doesn't make yet does it need newer scripts too:
the refresh then says so, and the rest of the page still refreshes.

Run it from VS Code (open this file > Run Python File), or from a terminal:  python main.py
The daily scheduled task (set up by SETUP.bat) runs it too, through pipeline\run_daily.bat.

The other .py files in pipeline\ and tools\ are the steps it calls; you never run them yourself.
If a required step fails, it stops and the last good dashboard stays as it is. Details: pipeline\run_daily.log.

pipeline\pres_store\ holds the saved presentation days. NEVER DELETE IT: the presentation feed keeps only about
6 months, so older days exist only there.
"""
import datetime
import json
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(KIT, "pipeline")
LOG = os.path.join(PIPE, "run_daily.log")
FRESH = os.path.join(PIPE, "fresh_build.tmp")   # the kit's own full build; only its data is used
STEPS = [   # (what, script relative to pipeline\, extra args, required)
    ('Pull deals, presentations and listings', 'refresh_mumbai_dashboard.py', [], True),
    ('Add sub-verticals and sales groups', 'build_subvertical.py', [], True),
    ('Top-200 JDA categories', 'build_top200.py', [], False),
    ('Build the data', '..\\tools\\build_ui_lab.py', ['mumbai'], True),
]
# Where the page keeps its data: each marker is followed by one JSON value. Everything else in the page is design.
DATA_BLOCKS = {
    "pincode data": "\nconst DATA = ",
    "day-by-day data": "\nconst DAILY = ",
    "JDA deployment": "\nconst JDA_DEPLOYMENT = ",
    "employees": "\nconst EMP_META = ",
    "listings by sub-vertical": "\nconst MONETIZABLE_SUB_VERTICALS = ",
    "listings by sales group": '<script type="application/json" id="svsgData">',
    "top-500 / top-200 listings": "(function () { const T = ",
    "top-200 categories": "<script>const TOP200 = ",
    "map boundaries": "\nconst BOUNDARIES = ",
    "sales-group labels": "\nconst SALES_GROUP_LABEL_MAP = ",
}
TEXT_BLOCKS = {   # data shown as plain text in the page: (start, end) around it
    "'Data updated' time": ('<p id="lastRefreshed">', "</p>"),
}


def dashboard_file(kit_dir, default):
    """The dashboard page: the one .html in the kit folder, whatever it is called (it may have been renamed for
    hosting); the default name when there is none. With several, the default (and a warning)."""
    pages = sorted(f for f in os.listdir(kit_dir) if f.lower().endswith(".html"))
    if len(pages) == 1:
        return os.path.join(kit_dir, pages[0]), []
    return os.path.join(kit_dir, default), [p for p in pages if p != default]


def find_block(page, marker):
    """(start, end) of the JSON value after the marker, or None when the page doesn't have exactly one."""
    if page.count(marker) != 1:
        return None
    start = page.index(marker) + len(marker)
    try:
        _, end = json.JSONDecoder().raw_decode(page, start)
    except ValueError:
        return None
    return start, end


def find_text(page, start_tag, end_tag):
    """(start, end) of the text between the tags, or None when the page doesn't have exactly one."""
    if page.count(start_tag) != 1:
        return None
    start = page.index(start_tag) + len(start_tag)
    end = page.find(end_tag, start)
    return (start, end) if end >= 0 else None


def put_fresh_data(design, fresh):
    """The design page with every data block it has replaced by the fresh build's. Returns (page, notes)."""
    notes, swaps = [], []
    for name, marker in DATA_BLOCKS.items():
        here = find_block(design, marker)
        if here is None:
            continue   # this version of the page doesn't use it
        new = find_block(fresh, marker)
        if new is None:
            notes.append(f"'{name}' kept its last data: this page needs newer kit scripts for it (ask Sarvesh).")
            continue
        swaps.append((here, fresh[new[0]:new[1]]))
    for name, tags in TEXT_BLOCKS.items():
        here, new = find_text(design, *tags), find_text(fresh, *tags)
        if here and new:
            swaps.append((here, fresh[new[0]:new[1]]))
    for (start, end), value in sorted(swaps, reverse=True):   # back to front, so earlier positions stay valid
        design = design[:start] + value + design[end:]
    return design, notes


def main():
    dash, extra = dashboard_file(KIT, 'JDA_JDS_Mumbai_Pincode_Dashboard.html')
    os.environ["JDA_DASH_OUT"] = FRESH   # the build step writes here
    if extra:
        print("Note: several .html files here; updating " + os.path.basename(dash) + ". Delete the others so there is just one: " + ", ".join(extra))
    for env in ("db_216.env", "db_240.env"):
        if not os.path.exists(os.path.join(PIPE, env)):
            sys.exit(f"Missing pipeline\\{env}: copy {env}.template to {env} and fill in the database login (see SETUP.md).")
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"===== {datetime.datetime.now():%Y-%m-%d %H:%M} =====\n")
        for i, (what, script, args, required) in enumerate(STEPS, 1):
            print(f"[{i}/{len(STEPS)}] {what} ...", flush=True)
            log.write(f"--- {what}\n"); log.flush()
            r = subprocess.run([sys.executable, os.path.join(PIPE, script), *args], cwd=PIPE, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                msg = f"{what} FAILED (exit {r.returncode}); see pipeline\\run_daily.log."
                log.write(msg + "\n")
                if required:
                    sys.exit(msg + " The last good dashboard is unchanged.")
                print("   " + msg + " Carrying on (this step is optional).")

        print(f"[{len(STEPS) + 1}/{len(STEPS) + 1}] Put the data into the page ...", flush=True)
        with open(FRESH, encoding="utf-8", newline="") as f:
            fresh = f.read()
        design = None
        if os.path.exists(dash):
            with open(dash, encoding="utf-8", newline="") as f:
                design = f.read()
        if design is None or find_block(design, DATA_BLOCKS["pincode data"]) is None:
            page, notes = fresh, ["No usable dashboard page here, so the kit's own design was used."]
        else:
            page, notes = put_fresh_data(design, fresh)
        for n in notes:
            print("   Note: " + n)
            log.write("Note: " + n + "\n")
        tmp = dash + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(page)
        os.replace(tmp, dash)   # all at once, so viewers never see half a page
        os.remove(FRESH)
        log.write("Done.\n")
    print(f"Done: {dash} is up to date.")


if __name__ == "__main__":
    main()
