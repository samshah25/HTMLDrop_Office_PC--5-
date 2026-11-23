"""
Refresh the JD India sales overview right now (main.py calls this on the 15th and the month end; run main.py).

It pulls the latest numbers and rebuilds the dashboard page (the one .html file in this folder) with data up to the
latest deal date. Run it from VS Code (open this file > Run Python File), or from a terminal:
    python refresh_dashboard.py

Schedule it however you like (see SETUP.md). A run takes about a minute.

If a step fails, it stops and the last good dashboard stays as it is. Details: pipeline\refresh.log.
"""
import datetime
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(KIT, "pipeline")
LOG = os.path.join(PIPE, "refresh.log")
DEFAULT_PAGE = "jd-india-sales-overview.html"
STEPS = [   # (what, script in pipeline\)
    ("Pull deals and RV 3yr by day", "fetch_data.py"),
    ("Build the dashboard page", "build_dashboard.py"),
]


def dashboard_file():
    """The page to update: the one .html in this folder, whatever it is called (it may have been renamed for
    hosting); the default name when there is none. With several, the default, and a note to delete the others."""
    pages = sorted(f for f in os.listdir(KIT) if f.lower().endswith(".html"))
    if len(pages) == 1:
        return os.path.join(KIT, pages[0]), []
    return os.path.join(KIT, DEFAULT_PAGE), [p for p in pages if p != DEFAULT_PAGE]


def main():
    if not os.path.exists(os.path.join(PIPE, "db_216.env")) and not os.environ.get("JDA_DB_ENV"):
        sys.exit("Missing pipeline\\db_216.env: copy db_216.env.template to db_216.env and fill in the database login (see SETUP.md).")
    page, extra = dashboard_file()
    if extra:
        print("Note: several .html files here; updating " + os.path.basename(page) + ". Delete the others so there is just one: " + ", ".join(extra))
    env = dict(os.environ, JDA_DASH_OUT=page, PYTHONIOENCODING="utf-8")
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"===== {datetime.datetime.now():%Y-%m-%d %H:%M} =====\n")
        for k, (what, script) in enumerate(STEPS, 1):
            print(f"[{k}/{len(STEPS)}] {what} ...", flush=True)
            log.write(f"--- {what}\n")
            log.flush()
            r = subprocess.run([sys.executable, os.path.join(PIPE, script)], cwd=PIPE, env=env, stdout=log, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                msg = f"{what} FAILED (exit {r.returncode}); see pipeline\\refresh.log. The last good dashboard is unchanged."
                log.write(msg + "\n")
                sys.exit(msg)
        log.write("Done.\n")
    print(f"Done: {page} is up to date.")


if __name__ == "__main__":
    main()
