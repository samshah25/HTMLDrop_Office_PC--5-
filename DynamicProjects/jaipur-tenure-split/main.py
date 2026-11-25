"""Jaipur tenure grid: refresh (one command runs every step). Task Scheduler runs it at 07:30, 11:30 and 14:30 (setup_schedule.ps1).
    python main.py              pulls everything up to yesterday (read-only) and rebuilds "jaipur-tenure-split.html"
    python main.py --cached     rebuilds the page from the data already pulled
Every run first moves the private files out of this folder (HTML Drop shows every file here) into
C:\ProgramData\Jaipur_tenure_grid_private: environment.py (logins) and pipeline\seed\ (history); the data stays there.
After the page: a snapshot of this run and a list of what changed since the previous run (run_changes\ in the private folder).
A step that fails stops the run, so the page keeps its last good data. Each run is logged to refresh_log.txt (private folder)."""
import os, sys, shutil, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.join(HERE, "pipeline")
sys.path.insert(0, PIPE)
import kitpaths  # noqa: E402
os.makedirs(kitpaths.DATA, exist_ok=True)


def log(m):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {m}"
    print(line, flush=True)
    with open(kitpaths.LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# move the private files out of the shared folder (logins, history)
src = os.path.join(HERE, "environment.py")
if os.path.exists(src):
    shutil.move(src, os.path.join(kitpaths.PRIVATE, "environment.py")); log("environment.py moved to the private folder")
seed = os.path.join(PIPE, "seed")
if os.path.isdir(seed):
    for base, _, files in os.walk(seed):
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), seed)
            dst = os.path.join(kitpaths.DATA, rel)
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(os.path.join(base, f), dst)
    shutil.rmtree(seed, ignore_errors=True); log("seed data moved to the private folder")

log("refresh started")
steps = ([] if "--cached" in sys.argv else [["t1_fetch.py", "--refresh"]]) + [["t2_build.py"]]
for s in steps:
    r = subprocess.run([sys.executable, os.path.join(PIPE, s[0])] + s[1:], cwd=PIPE)
    if r.returncode:
        log(f"{s[0]} failed (code {r.returncode}): the page keeps its last good data"); sys.exit(r.returncode)
if "--cached" not in sys.argv:
    for s in ("run_snapshot.py", "run_changes.py"):
        r = subprocess.run([sys.executable, os.path.join(PIPE, s)], cwd=PIPE)
        if r.returncode: log(f"{s} failed (code {r.returncode}); the page is built anyway")
log("refresh done")
