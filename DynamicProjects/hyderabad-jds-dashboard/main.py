r"""
Refresh the Hyderabad JDS Dashboard: THE ONLY SCRIPT YOU NEED TO RUN.

1. pipeline\jds_refresh.py pulls JDS (TME & ME) deals from ops_analytics.tbl_modified_deal_level_data
   + vertical_owner.tbl_company_vertical_mapping_SB + db_paidcontracts.hr_all_daily_copy_ganesh
   (or uses pipeline\jds_cache.json.gz / CSV exports when offline) into pipeline\jds_data.json.
2. Injects pipeline\jds_data.json into template\jds_template.html -> Hyderabad_JDS_Dashboard.html.

Usage:
  python main.py                          # incremental daily refresh + build HTML
  python main.py --page-only              # rebuild HTML from existing pipeline\jds_data.json
  python main.py --full-refresh           # ignore cache and re-fetch full FY + LY from SQL
  python main.py --seed-dir <folder>      # seed cache from exported *_all.csv files
"""
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(ROOT, "pipeline")
TEMPLATE = os.path.join(ROOT, "template", "jds_template.html")
DATA = os.path.join(PIPE, "jds_data.json")
PAGE = os.path.join(ROOT, "Hyderabad_JDS_Dashboard.html")
LOG = os.path.join(PIPE, "run_daily.log")
DATA_TAG = '<script type="application/json" id="jdsData">'


def build_page():
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    with open(DATA, encoding="utf-8") as f:
        data = f.read().replace("</", "<\\/")
    if page.count(DATA_TAG) != 1:
        sys.exit("Template missing data slot: " + DATA_TAG)
    start = page.index(DATA_TAG) + len(DATA_TAG)
    end = page.index("</script>", start)
    page = page[:start] + data + page[end:]
    tmp = PAGE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(page)
    os.replace(tmp, PAGE)


def main():
    skip_pull = "--page-only" in sys.argv
    full_refresh = "--full-refresh" in sys.argv
    os.makedirs(PIPE, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"===== {datetime.datetime.now():%Y-%m-%d %H:%M} =====\n")
        if not skip_pull:
            cmd = [sys.executable, os.path.join(PIPE, "jds_refresh.py")]
            if full_refresh:
                cmd.append("--full-refresh")
            if "--seed-dir" in sys.argv:
                ix = sys.argv.index("--seed-dir")
                if ix + 1 < len(sys.argv):
                    cmd.extend(["--seed-dir", sys.argv[ix + 1]])
            print("[1/2] Refresh Hyderabad JDS data (incremental) ...", flush=True)
            log.flush()
            r = subprocess.run(cmd, cwd=PIPE, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                log.write(f"Data step FAILED (exit {r.returncode}).\n")
                sys.exit("Data step failed; see pipeline\\run_daily.log. Existing dashboard left unchanged.")
        print("[2/2] Build Hyderabad_JDS_Dashboard.html ...", flush=True)
        build_page()
        log.write("Done.\n")
    print(f"Done: {PAGE} is up to date.")


if __name__ == "__main__":
    main()
