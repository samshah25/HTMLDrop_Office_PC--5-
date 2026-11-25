r"""
Refresh the Hyderabad JDA dashboard: THE ONLY SCRIPT YOU NEED TO RUN.

1. pipeline\hyd_refresh.py pulls presentations (and, with pipeline\db_216.env, sales, HR details, and
   category/subcategory YoY deals from ops_analytics.tbl_modified_deal_level_data +
   vertical_owner.tbl_company_vertical_mapping_SB) up to yesterday into pipeline\hyd_data.json;
2. the data goes into template\dashboard_template.html, written out as Hyderabad_JDA_Dashboard.html in this folder.

The page's look lives only in the template: to change the design, edit or replace the template and run this again.
Run it from VS Code (open this file > Run Python File) or a terminal:  python main.py
Optional flags:  --page-only (rebuild HTML from existing hyd_data.json),  --cat-only (refresh category YoY data only).
If the data step fails, the last good dashboard stays as it is. Log: pipeline\run_daily.log.

pipeline\pres_store\ holds the saved presentation days. NEVER DELETE IT: the feed keeps only about 6 months.
"""
import datetime
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(KIT, "pipeline")
TEMPLATE = os.path.join(KIT, "template", "dashboard_template.html")
DATA = os.path.join(PIPE, "hyd_data.json")
PAGE = os.path.join(KIT, "Hyderabad_JDA_Dashboard.html")
LOG = os.path.join(PIPE, "run_daily.log")
DATA_TAG = '<script type="application/json" id="hydData">'


def build_page():
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    with open(DATA, encoding="utf-8") as f:
        data = f.read().replace("</", "<\\/")   # keeps the JSON from closing the script tag
    if page.count(DATA_TAG) != 1:
        sys.exit("The template has no data slot (" + DATA_TAG + "): was it replaced with the wrong file?")
    start = page.index(DATA_TAG) + len(DATA_TAG)
    end = page.index("</script>", start)
    page = page[:start] + data + page[end:]
    tmp = PAGE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(page)
    os.replace(tmp, PAGE)   # all at once, so viewers never see half a page


def main():
    skip_pull = "--page-only" in sys.argv   # rebuild the page from the last data, e.g. after a design change
    cat_only = "--cat-only" in sys.argv     # refresh only category YoY data (incremental SQL if db_216.env exists, else cache)
    full_cat = "--full-cat-refresh" in sys.argv   # ignore category cache and re-fetch full FY + LY from SQL
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"===== {datetime.datetime.now():%Y-%m-%d %H:%M} =====\n")
        if not skip_pull:
            cmd = [sys.executable, os.path.join(PIPE, "hyd_refresh.py")]
            if cat_only:
                cmd.append("--cat-only")
            if full_cat:
                cmd.append("--full-cat-refresh")
            if "--seed-dir" in sys.argv:
                ix = sys.argv.index("--seed-dir")
                if ix + 1 < len(sys.argv):
                    cmd.extend(["--seed-dir", sys.argv[ix + 1]])
            if cat_only:
                print("[1/2] Refresh category & subcategory YoY deals (incremental) ...", flush=True)
            else:
                print("[1/2] Pull presentations, sales, HR and category YoY deals ...", flush=True)
            log.flush()
            r = subprocess.run(cmd, cwd=PIPE, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                log.write(f"Data step FAILED (exit {r.returncode}).\n")
                sys.exit("The data step failed; see pipeline\\run_daily.log. The last good dashboard is unchanged.")
        print("[2/2] Put the data into the page ...", flush=True)
        build_page()
        log.write("Done.\n")
    print(f"Done: {PAGE} is up to date.")


if __name__ == "__main__":
    main()
