Ahmedabad ME Team Performance - dashboard kit (26 Nov 2026)
===========================================================

The Ahmedabad copy of the ME team dashboard (the same page as Mumbai's: ME and TME modes, Overview / Table, Checks),
with the Super Cat skewness card on the Overview. There is NO sign-in: anyone on the network who has the link sees the
whole page.

Top level
---------
  Ahmedabad ME Team Performance.html   the dashboard (open page; rewritten in place by every refresh)
  main.py                              refreshes the data and rebuilds the page:  python main.py
  run_daily.bat                        same as "python main.py", for Windows Task Scheduler
  setup_schedule.ps1                   registers the daily runs in Task Scheduler (08:20, 14:50)
  environment.py                       the database logins (the same file as the Mumbai ME kit); the first run moves it out
  pipeline\                            the refresh steps and the page design files (no need to touch).
                                       pipeline\city.txt = ahmedabad sets the branch.

Private files - kept OUT of this folder
---------------------------------------
HTML Drop shows every file in this folder to anyone on the network. So every run of main.py first moves the private
files out of it, into  C:\ProgramData\ME_dashboard_private_ahmedabad  (set ME_PRIVATE_DIR to use another folder), and
works there: environment.py, the pulled data (cache\), the managers' pages and refresh_log.txt.
This kit is separate from the Mumbai ME kit: its own folder, its own private folder, its own scheduled task.

First setup (once)
------------------
1. Upload this zip to HTML Drop as a NEW project, named "Ahmedabad ME Team Performance"
   (link: http://172.29.65.188:8150/s/ahmedabad-me-team-performance/). Do not unzip it over the Mumbai ME kit.
2. In that project's folder, run  python main.py  straight away: it moves environment.py out of the folder, then pulls
   everything since 1 April (about 10 minutes the first time; later runs about 5) and rewrites the page.
   pip install -r pipeline\requirements.txt only if Python packages are missing.
3. Register the schedule once:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
   It adds the task "Ahmedabad ME Team Performance refresh": every day at 08:20 (yesterday from the live allocation API,
   provisional) and 14:50 (yesterday from the appointment table, which loads at about 14:05). It runs 20 minutes after
   the Mumbai ME kit's runs so the two never overlap. Remove it with:
     Unregister-ScheduledTask -TaskName "Ahmedabad ME Team Performance refresh" -Confirm:$false

Updating later
--------------
Upload Ahmedabad_ME_Team_Performance_update.zip over the same project (it has no environment.py: the login already
sits in the private folder), then run  python main.py  once.

Refresh
-------
  python main.py               full refresh (appointments, yesterday from the API until the table has it, deals and HR,
                               the TMEs' calls, past deals and appointment pincodes for the skewness card), then the page
  python main.py --build-only  rebuild the page from the last pulled data
If a step fails, it stops and the page keeps its last good data (the API, the calls and the skewness card's extra data
are optional: the refresh carries on without them). Log: refresh_log.txt in the private folder.
New TME reporting lines: put the newer "SSO dump*.xlsx" in pipeline\; the next run re-reads it.

The page shows internal employee data. environment.py holds passwords: keep this kit and the private folder off any
shared or public place other than this HTML Drop project.
