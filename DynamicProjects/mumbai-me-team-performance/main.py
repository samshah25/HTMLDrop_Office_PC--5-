"""Data refresh for the ME team dashboards: one command runs every step, in order.

    python main.py               full refresh: appointments -> provisional days from the API -> deals + HR -> both pages
    python main.py --build-only  rebuild both pages from the cached data (no database)

Steps:
  1. fetch_data.py      appointments from server 240 (datagrowth.tbl_final_data_appt), into cache\\raw.pkl
  2. fetch_api.py       the days the appointment table does not have yet (it loads around 2 pm), up to yesterday, rebuilt
                        from the live ME allocation API and marked provisional (cache\\api_rows.pkl); removed once the
                        table has those days. If the API cannot be reached, the refresh carries on without them.
  3. fetch_deals.py     deals (+ the 30-day rolling table for the newest days) and HR from server 216, into cache\\
  4. build_dashboard.py the team page,            jd-me-team-performance.html (only if that page is in the folder)
  5. build_review.py    the ME Head's dashboard,  Mumbai ME Team Performance.html

Run it twice a day (Task Scheduler, run_daily.bat): in the morning (yesterday comes from the API, provisional) and in the
afternoon after the appointment table loads (yesterday from the table). A third run later in the afternoon covers a late load.

A step that fails stops the run, so the pages keep their last good data. Every run is logged to refresh_log.txt.

Database logins are read from pipeline\\db_240.env and pipeline\\db_216.env; if those are not here, from the files named
by ME_DB_ENV / ME_DEALS_DB_ENV, then from DB_240 / DB_216 in pipeline\\environment.py, or else from the package's shared
pipeline folder (..\\..\\pipeline\\). Logins are never copied into the pages.
"""
import datetime
import os
import subprocess
import sys
import time

# main.py works from the pipeline folder or from the folder above it (the shared kit keeps main.py and environment.py
# at its top level, with the scripts in pipeline\)
HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.join(HERE, "pipeline") if os.path.isfile(os.path.join(HERE, "pipeline", "fetch_data.py")) else HERE
SHARED = os.path.normpath(os.path.join(PIPE, "..", "..", "pipeline"))   # kolkata_lite_package\pipeline
LOG = os.path.join(PIPE, "refresh_log.txt")


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def unfinished_run():
    """the start time and last step of the previous run when it never logged its end, else None"""
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-400:]
    except OSError:
        return None
    start = max((i for i, l in enumerate(lines) if "===== ME dashboards refresh" in l), default=None)
    if start is None or any(("===== done" in l or "FAILED" in l) for l in lines[start + 1:]):
        return None
    steps = [l.split("-- ", 1)[1].strip() for l in lines[start + 1:] if "] -- " in l]
    return lines[start][1:20], (steps[-1] if steps else "the start")


def env_file(var, name):
    """the login file for a server: here, else the env var, else the shared pipeline folder"""
    for path in (os.path.join(PIPE, name), os.environ.get(var, ""), os.path.join(SHARED, name)):
        if path and os.path.exists(path):
            return path
    return ""


def in_settings(name):
    """True when pipeline\\environment.py has that login filled in"""
    try:
        sys.path[:0] = [PIPE, HERE]
        import environment
    except ImportError:
        return False
    d = getattr(environment, name, None) or {}
    return bool(str(d.get("MYSQL_HOST", "")).strip() and str(d.get("MYSQL_USER", "")).strip())


STEP_LIMIT = 40 * 60   # seconds; a normal run takes about 2 minutes. Windows' own task limit (2 hours) stops a run silently


def step(name, *args):
    """runs one step; a step that goes over STEP_LIMIT is stopped and logged (exit code 124)"""
    try:
        return subprocess.run([sys.executable, os.path.join(PIPE, name), *args], cwd=PIPE, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=ENV, timeout=STEP_LIMIT)
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return subprocess.CompletedProcess(e.cmd, 124, out, f"TIMED OUT: stopped after {STEP_LIMIT // 60} minutes "
                                           "(a database or the API did not answer, or the PC slept during the step)")


def run_optional(step_name, *args):
    """a step whose failure should not stop the refresh: the pages are built without its output"""
    t0 = time.time()
    step_ = step_name
    log(f"-- {step_} {' '.join(args)}".rstrip())
    p = step(step_, *args)
    for line in (p.stdout + p.stderr).strip().splitlines():
        log("   " + line)
    if p.returncode != 0:
        stale = os.path.join(PIPE, "cache", "api_rows.pkl")
        if os.path.exists(stale):
            os.remove(stale)
        log(f"   {step_} failed (exit {p.returncode}); carrying on without provisional days.")
    else:
        log(f"   ok ({time.time() - t0:.0f}s)")


def run(step_name, *args):
    t0 = time.time()
    log(f"-- {step_name} {' '.join(args)}".rstrip())
    p = step(step_name, *args)
    for line in (p.stdout + p.stderr).strip().splitlines():
        log("   " + line)
    if p.returncode != 0:
        log(f"FAILED: {step_name} (exit {p.returncode}). Stopped here; the pages keep their last good data.")
        sys.exit(p.returncode)
    log(f"   ok ({time.time() - t0:.0f}s)")


# the steps find environment.py next to main.py as well as in pipeline
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=os.pathsep.join(x for x in (HERE, PIPE, os.environ.get("PYTHONPATH", "")) if x))

if __name__ == "__main__":
    build_only = "--build-only" in sys.argv
    t0 = time.time()
    prev = unfinished_run()
    log("===== ME dashboards refresh" + (" (build only)" if build_only else "") + " =====")
    if prev:
        log(f"Note: the previous run (started {prev[0]}) never finished; it stopped during {prev[1]} without an error. "
            "Usually the PC slept or shut down, or Windows stopped the task at its time limit.")
    if not build_only:
        e240, e216 = env_file("ME_DB_ENV", "db_240.env"), env_file("ME_DEALS_DB_ENV", "db_216.env")
        missing = [n for n, p, k in (("server 240 (DB_240)", e240, "DB_240"), ("server 216 (DB_216)", e216, "DB_216")) if not p and not in_settings(k)]
        if missing:
            log("FAILED: no login for " + ", ".join(missing) + ". Fill DB_240 / DB_216 in " + os.path.join(HERE, "environment.py") + ".")
            sys.exit(2)
        if e240: ENV["ME_DB_ENV"] = e240
        if e216: ENV["ME_DEALS_DB_ENV"] = e216
        run("fetch_data.py")
        run_optional("fetch_api.py")
        run("fetch_deals.py")
    # the older team page is rebuilt only where it is kept (not in the shared kit, which hosts just the ME Head's page)
    if os.path.exists(os.path.join(os.path.dirname(PIPE), "jd-me-team-performance.html")):
        run("build_dashboard.py", "--full")
    run("build_review.py", "--full")
    log(f"===== done in {time.time() - t0:.0f}s =====")
