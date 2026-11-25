Jaipur tenure grid - dashboard kit (24 Nov 2026)
=================================================

Top level (the same layout as the Mumbai ME kit)
---------
  jaipur-tenure-split.html     the page (Jaipur teams by tenure: by metric, by team, managers > team leaders > people)
  main.py                     refreshes the data and rebuilds the page:  python main.py
  run_daily.bat               same as "python main.py", for Windows Task Scheduler
  setup_schedule.ps1          registers the daily runs in Task Scheduler (07:30, 11:30, 14:30)
  environment.py              the database logins (DB_216, DB_240, DB_120, filled in) - the first run moves it out (below)
  pipeline\                   the refresh steps, the page template and the starting history (no need to touch)

Private files - kept OUT of this folder
-------------
HTML Drop shows every file in this folder to anyone on the network. So every run of main.py first moves the private files
out of it, into  C:\ProgramData\Jaipur_tenure_grid_private  (set JAIPUR_TENURE_PRIVATE_DIR to use another folder):
  environment.py              the database logins
  data\                       the pulled data, the history (reporting lines, presentations, call data) and each run's snapshot
  run_changes\                what changed from one run to the next (log.csv and one file per pair of runs)
  refresh_log.txt             one line per step of every run

First time / updating
---------------------
1. Unzip into the HTML Drop project folder (or over the old folder).
2. Run  python main.py  straight away. It moves environment.py and the history out of the folder, pulls the data up to
   yesterday and rebuilds "jaipur-tenure-split.html" (about 10 minutes the first time).
3. Register the daily runs once:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
pip install -r pipeline\requirements.txt only if Python packages are missing (pymysql, pandas, numpy).

Every day
---------
  07:30   deals and HR still end the day before yesterday (the tables load yesterday at about 10:50 and 11:05)
  11:30   yesterday's deals, HR and calls; yesterday's ME appointments are not in yet
  14:30   yesterday complete (the appointment table loads at about 14:05)
The page's top line says how far the data goes. If a run fails, the page keeps its last good data; the next run catches up.
