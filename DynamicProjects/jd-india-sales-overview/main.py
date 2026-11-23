r"""
JD India sales overview: THE ONE SCRIPT TO RUN.

The dashboard refreshes twice a month: on the 15th and on the last day of the month.

    python main.py              refresh if a refresh day (15th / month end) has come since the last good refresh;
                                otherwise say when the next one is and do nothing
    python main.py --now        refresh right away, whatever the date
    python main.py --check      only say whether a refresh is due (changes nothing)
    python main.py --install    create the Windows scheduled task (runs main.py every day at 07:00; it refreshes only when due)
    python main.py --uninstall  remove that scheduled task

Why a daily task and not two monthly ones: if the PC is off on the 15th or the month end, the next morning's run
catches up. The date of the last good refresh is kept in pipeline\last_refresh.txt (only written when the refresh
succeeds; a failed refresh is tried again the next day). The data runs to the latest closed deal, so a 07:00 run
gives numbers up to the day before.

The refresh itself is refresh_dashboard.py (pull the deals, rebuild the page, self-check). Details: pipeline\refresh.log.
"""
import calendar
import datetime as dt
import os
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
STAMP = os.path.join(KIT, "pipeline", "last_refresh.txt")
TASK = "JD India sales overview refresh"
RUN_AT = "07:00"


def refresh_days(year, month):
    """the refresh days of a month: the 15th and the last day"""
    return [dt.date(year, month, 15), dt.date(year, month, calendar.monthrange(year, month)[1])]


def last_due(today):
    """the latest refresh day on or before today"""
    y, m = today.year, today.month
    for d in reversed(refresh_days(y, m)):
        if d <= today:
            return d
    py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    return refresh_days(py, pm)[-1]


def next_due(today):
    """the next refresh day after today"""
    y, m = today.year, today.month
    for d in refresh_days(y, m):
        if d > today:
            return d
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return refresh_days(ny, nm)[0]


def last_refresh():
    try:
        return dt.date.fromisoformat(open(STAMP, encoding="utf-8").read().strip()[:10])
    except (OSError, ValueError):
        return None


def is_due(today):
    done = last_refresh()
    return done is None or done < last_due(today), done


def refresh():
    """run refresh_dashboard.py; record the date only when it succeeds"""
    r = subprocess.run([sys.executable, os.path.join(KIT, "refresh_dashboard.py")], cwd=KIT)
    if r.returncode != 0:
        sys.exit("Refresh failed; it will be tried again on the next run. See pipeline\\refresh.log.")
    with open(STAMP, "w", encoding="utf-8") as f:
        f.write(dt.date.today().isoformat() + "\n")


def install():
    cmd = f'"{sys.executable}" "{os.path.join(KIT, "main.py")}"'
    r = subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK, "/SC", "DAILY", "/ST", RUN_AT, "/TR", cmd])
    if r.returncode == 0:
        print(f'Scheduled task "{TASK}" created: every day at {RUN_AT}; it refreshes on the 15th and the month end only.')
        print("The PC must be on and you must be logged in at that time; a missed day is caught up the next morning.")
    else:
        sys.exit("Could not create the task. Try again from a terminal opened as administrator.")


def uninstall():
    r = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK])
    print(f'Scheduled task "{TASK}" removed.' if r.returncode == 0 else "No such task, or it could not be removed.")


def main():
    args = set(sys.argv[1:])
    if "--install" in args:
        return install()
    if "--uninstall" in args:
        return uninstall()
    today = dt.date.today()
    due, done = is_due(today)
    if "--now" in args:
        return refresh()
    if "--check" in args:
        print(f"Last good refresh: {done or 'none yet'}. Last refresh day: {last_due(today)}. Next refresh day: {next_due(today)}. "
              f"Refresh due now: {'yes' if due else 'no'}.")
        return
    if due:
        print(f"Refresh day {last_due(today)} has come (last good refresh: {done or 'none yet'}). Refreshing ...")
        refresh()
    else:
        print(f"Not a refresh day. Last good refresh: {done}. Next refresh: {next_due(today)}.")


if __name__ == "__main__":
    main()
