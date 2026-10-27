r"""
Refresh the Mumbai JDA dashboard: THE ONLY SCRIPT YOU NEED TO RUN.

It runs every step of the pipeline in order and rebuilds Mumbai_JDA_Dashboard.html with data up to yesterday.
Run it from VS Code (open this file > Run Python File), or from a terminal:  python refresh_dashboard.py
The daily scheduled task (set up by SETUP.bat) runs it too, through pipeline\run_daily.bat.

The other .py files in pipeline\ and tools\ are the steps it calls; you never run them yourself.
If a required step fails, it stops and the last good dashboard stays as it is. Details: pipeline\run_daily.log.
"""
import datetime
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(KIT, "pipeline")
LOG = os.path.join(PIPE, "run_daily.log")
STEPS = [   # (what, script relative to pipeline\, extra args, required)
    ('Pull deals, presentations and listings', 'refresh_mumbai_dashboard.py', [], True),
    ('Add sub-verticals and sales groups', 'build_subvertical.py', [], True),
    ('Top-200 JDA categories', 'build_top200.py', [], False),
    ('Build the dashboard page', '..\\tools\\build_ui_lab.py', ['mumbai'], True),
]


def main():
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
        log.write("Done.\n")
    print(f"Done: {os.path.join(KIT, 'JDA_JDS_Mumbai_Pincode_Dashboard')} is up to date.")


if __name__ == "__main__":
    main()
