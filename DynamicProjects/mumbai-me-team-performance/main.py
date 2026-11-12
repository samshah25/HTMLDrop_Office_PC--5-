"""Data refresh for the ME team dashboards: one command runs every step, in order.

    python main.py               full refresh: appointments -> provisional days from the API -> deals + HR -> both pages
    python main.py --build-only  rebuild both pages from the cached data (no database)

Steps:
  1. fetch_data.py      appointments from server 240 (datagrowth.tbl_final_data_appt), into cache\\raw.pkl
  2. fetch_api.py       the days the appointment table does not have yet (it loads around 2 pm), up to yesterday, rebuilt
                        from the live ME allocation API and shown like any other day (cache\\api_rows.pkl); removed once the
                        table has those days. If the API cannot be reached, the refresh carries on without them.
  3. fetch_deals.py     deals (+ the 30-day rolling table for the newest days) and HR from server 216, into cache\\
     fetch_calls.py     the TMEs' dialer calls from server 120, for TME mode's funnel (cache\\calls.pkl; the refresh carries
                        on without them when there is no server 120 login or the server does not answer)
  4. build_review.py    the ME Head's dashboard,  Mumbai ME Team Performance.html (ME and TME mode; TME mode's reporting
                        lines from tme_lines.json, which tme_lines.py makes from the SSO dump: run on its own when a newer
                        "SSO dump*.xlsx" is put in exports\\)
(The older team page jd-me-team-performance.html is no longer rebuilt: the ME Head's final page is Mumbai ME Team
Performance.html, 14 Oct 2026. build_dashboard.py stays for reference.)

Run it twice a day (Task Scheduler, run_daily.bat): in the morning (yesterday comes from the API, provisional) and in the
afternoon after the appointment table loads (yesterday from the table). A third run later in the afternoon covers a late load.

A step that fails stops the run, so the pages keep their last good data. Every run is logged to refresh_log.txt.

Database logins are read from pipeline\\db_240.env and pipeline\\db_216.env; if those are not here, from the files named
by ME_DB_ENV / ME_DEALS_DB_ENV, then from DB_240 / DB_216 in pipeline\\environment.py, or else from the package's shared
pipeline folder (..\\..\\Kolkata\\pipeline\\). Logins are never copied into the pages.

Shared kit (6 Nov 2026): HTML Drop may show this kit's folder to everyone, so every run first moves the private files out of
it - environment.py, db_*.env, vault_keys.json, logins.json, pipeline\\cache, manager_pages, an unlocked page, the logs - into
C:\\ProgramData\\ME_dashboard_private (or the folder named by ME_PRIVATE_DIR; see pipeline\\kitpaths.py) and works there.
The kit's own "Mumbai ME Team Performance.html" is the sign-in page (every page inside it encrypted).
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
SHARED = os.path.normpath(os.path.join(PIPE, "..", "..", "Kolkata", "pipeline"))   # kolkata_lite_package\Kolkata\pipeline
sys.path.insert(0, PIPE)
import kitpaths   # where the private files live (shared kit: outside this folder)
LOG = os.path.join(kitpaths.LOGDIR, "refresh_log.txt")
SIGNIN_MARK = b"<title>Sign in \xc2\xb7 ME team, Mumbai</title>"
PLACEHOLDER = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>ME team, Mumbai</title></head><body style="
               "'font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:40px;color:#14213D'><h1 style='font-size:18px'>ME team, Mumbai</h1>"
               "<p>The dashboard is being updated. Please try again in a few minutes.</p></body></html>")


def move_private():
    """shared kit: move private files out of the kit folder into kitpaths.PRIVATE; returns what moved (6 Nov 2026)"""
    import shutil
    P = kitpaths.PRIVATE
    if not P:
        return []
    os.makedirs(P, exist_ok=True)
    moved = []

    def mv(src, dst):
        if not os.path.exists(src):
            return
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src):
                mv(os.path.join(src, f), os.path.join(dst, f))
            shutil.rmtree(src, ignore_errors=True)
            return
        if os.path.exists(dst):
            if os.path.getmtime(src) < os.path.getmtime(dst):   # the private copy is newer: keep it, park the old one
                old = os.path.join(P, "replaced")
                os.makedirs(old, exist_ok=True)
                shutil.move(src, os.path.join(old, f"{os.path.basename(src)}.{int(time.time())}"))
                moved.append(os.path.relpath(src, HERE))
                return
            os.remove(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved.append(os.path.relpath(src, HERE))
    for name in ("environment.py", "vault_keys.json", "logins.json", "serve_log.txt", "db_240.env", "db_216.env", "db_120.env"):
        mv(os.path.join(HERE, name), os.path.join(P, name))
    for name in ("environment.py", "db_240.env", "db_216.env", "db_120.env", "refresh_log.txt"):
        mv(os.path.join(PIPE, name), os.path.join(P, name))
    mv(os.path.join(PIPE, "cache"), kitpaths.CACHE)
    mv(os.path.join(HERE, "manager_pages"), kitpaths.MGR)
    top = os.path.join(HERE, kitpaths.PAGE_NAME)
    if os.path.exists(top):
        with open(top, "rb") as f:
            head = f.read(4096)
        if SIGNIN_MARK not in head and b"The dashboard is being updated" not in head:   # an unlocked page here: move it, leave a placeholder
            mv(top, kitpaths.FULL)
            with open(top, "w", encoding="utf-8") as f:
                f.write(PLACEHOLDER)
    return moved


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
    """the login file for a server: the private folder (shared kit), here, else the env var, else the shared pipeline folder"""
    for path in ((os.path.join(kitpaths.PRIVATE, name) if kitpaths.PRIVATE else ""), os.path.join(PIPE, name), os.environ.get(var, ""),
                 os.path.join(SHARED, name)):
        if path and os.path.exists(path):
            return path
    return ""


def in_settings(name):
    """True when pipeline\\environment.py has that login filled in"""
    try:
        sys.path[:0] = [x for x in (kitpaths.PRIVATE, PIPE, HERE) if x]
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
        stale = os.path.join(kitpaths.CACHE, "api_rows.pkl")
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


def sso_lines():
    """the TME mode's reporting lines (tme_lines.json, 29 Oct 2026): read again from the SSO dump when a newer
    "SSO dump*.xlsx" sits in exports\\ (or pipeline\\); without one (the shared kit) the json in pipeline\\ is used"""
    import glob
    found = [f for f in glob.glob(os.path.join(PIPE, "..", "exports", "SSO dump*.xlsx")) + glob.glob(os.path.join(PIPE, "SSO dump*.xlsx"))
             if not os.path.basename(f).startswith("~$")]
    js = os.path.join(PIPE, "tme_lines.json")
    if not found or (os.path.exists(js) and os.path.getmtime(js) >= max(os.path.getmtime(f) for f in found)):
        return
    t0 = time.time()
    log("-- tme_lines.py (a newer SSO dump)")
    p = step("tme_lines.py")
    for line in (p.stdout + p.stderr).strip().splitlines():
        log("   " + line)
    log(f"   ok ({time.time() - t0:.0f}s)" if p.returncode == 0 else f"   tme_lines.py failed (exit {p.returncode}); the TME lines stay as they were.")


def run_soft(step_name, *args):
    """a step the pages can do without (the TMEs' calls): a failure or a missing login is logged and the refresh carries on"""
    t0 = time.time()
    log(f"-- {step_name} {' '.join(args)}".rstrip())
    p = step(step_name, *args)
    for line in (p.stdout + p.stderr).strip().splitlines():
        log("   " + line)
    log(f"   ok ({time.time() - t0:.0f}s)" if p.returncode == 0 else f"   {step_name} did not finish (exit {p.returncode}); the pages keep the calls they had.")


# the steps find environment.py next to main.py as well as in pipeline
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=os.pathsep.join(x for x in (kitpaths.PRIVATE, HERE, PIPE, os.environ.get("PYTHONPATH", "")) if x))
if kitpaths.PRIVATE:
    ENV["ME_PRIVATE_DIR"] = kitpaths.PRIVATE

if __name__ == "__main__":
    build_only = "--build-only" in sys.argv
    t0 = time.time()
    moved = move_private()
    prev = unfinished_run()
    log("===== ME dashboards refresh" + (" (build only)" if build_only else "") + " =====")
    if kitpaths.PRIVATE:
        log(f"Private files (logins, data, unlocked pages, keys) in {kitpaths.PRIVATE}"
            + (f"; moved there from the kit folder: {', '.join(moved)}" if moved else ""))
    if prev:
        log(f"Note: the previous run (started {prev[0]}) never finished; it stopped during {prev[1]} without an error. "
            "Usually the PC slept or shut down, or Windows stopped the task at its time limit.")
    if not build_only:
        e240, e216 = env_file("ME_DB_ENV", "db_240.env"), env_file("ME_DEALS_DB_ENV", "db_216.env")
        missing = [n for n, p, k in (("server 240 (DB_240)", e240, "DB_240"), ("server 216 (DB_216)", e216, "DB_216")) if not p and not in_settings(k)]
        if missing:
            log("FAILED: no login for " + ", ".join(missing) + ". Fill DB_240 / DB_216 in " + os.path.join(kitpaths.PRIVATE or HERE, "environment.py") + ".")
            sys.exit(2)
        if e240: ENV["ME_DB_ENV"] = e240
        if e216: ENV["ME_DEALS_DB_ENV"] = e216
        run("fetch_data.py")
        run_optional("fetch_api.py")
        run("fetch_deals.py")
        e120 = env_file("ME_CALLS_DB_ENV", "db_120.env")   # the TMEs' dialer calls (server 120), for TME mode's funnel
        if e120: ENV["ME_CALLS_DB_ENV"] = e120
        run_soft("fetch_calls.py")
    sso_lines()
    run("build_review.py", "--full")
    if kitpaths.PRIVATE and not os.path.exists(kitpaths.KEYS):
        log(f"Note: no vault_keys.json in {kitpaths.PRIVATE}: the sign-in page was not made, the link shows 'being updated'.")
    log(f"===== done in {time.time() - t0:.0f}s =====")
