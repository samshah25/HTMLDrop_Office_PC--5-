Mumbai ME Team Performance - dashboard kit (2 Nov 2026)
=======================================================

Top level
---------
  Mumbai ME Team Performance.html   the dashboard (one self-contained page: data, fonts and logo inside)
  main.py                           refreshes the data and rebuilds the page:  python main.py
  environment.py                    database logins (DB_240, DB_216, DB_120, filled in) and CITY
  run_daily.bat                     same as "python main.py", for Windows Task Scheduler
  setup_schedule.ps1                registers the daily runs in Task Scheduler (08:00, 14:30)
  pipeline\                         the refresh steps and the page design files (no need to touch)

Data in this copy: appointments 1 Apr 2026 - 1 Nov 2026 (Sunday appointments counted on the Saturday before,
as the Sales MIS does), TMEs' calls to 31 Oct 2026, read 2 Nov 2026, 14:33.

Updating from the 27 Oct kit
----------------------------
Unzip over the old folder (the new environment.py already holds the logins for servers 240, 216 and 120). Then:
  pip install -r pipeline\requirements.txt
  python main.py
and copy the new "Mumbai ME Team Performance.html" to the host. The first run pulls the TMEs' calls since 1 April
(a few minutes longer than usual); later runs pull only the current month.
pipeline\build_dashboard.py and pipeline\app\app.js, app.css, shell.tpl are no longer used and can be deleted
(keep pipeline\app\fonts and pipeline\app\jd_logo.png).

ME and TME mode
---------------
The ME | TME switch in the top bar shows the same page for MEs or for TMEs (amber). The dates are one filter for both.
ME mode follows the ME team's hierarchy (ME head > managers > team leaders > MEs). TME mode follows the TMEs'
reporting lines from the SSO dump (pipeline\tme_lines.json) and HR's TME team (Super Cat, Hot Data, ...).
The page opens on Kushal Sharma's line only; "All MEs" can be picked in Settings for the open browser tab.

Hosting
-------
Serve "Mumbai ME Team Performance.html" from this folder (any static web server) or copy it to the host.
It needs no server code, no database and no internet connection.

Refresh
-------
1. Python 3.9+ and:  pip install -r pipeline\requirements.txt   (pymysql, cryptography; openpyxl only for a new SSO dump)
2. environment.py must hold read-only logins for server 240 (datagrowth.tbl_final_data_appt) and server 216
   (db_paidcontracts: deals and HR). For TME mode's calls also server 120 (sounak_db.tbl_dialer_data_mumbai_<yyyymm>);
   without it the refresh carries on and TME mode shows no calls.
3. Run:  python main.py   (about 3 minutes). It pulls appointments, then yesterday from the allocation API if the
   appointment table does not have it yet, then deals and HR, then the TMEs' calls, then rewrites
   "Mumbai ME Team Performance.html" in this folder. If a step fails, it stops and the page keeps its last good data
   (if only the API or server 120 cannot be reached, the refresh carries on without them). Log: pipeline\refresh_log.txt.
   Rebuild from the last pulled data only:  python main.py --build-only
4. New TME reporting lines: put the newer "SSO dump*.xlsx" in pipeline\ (or in an exports\ folder next to pipeline\);
   the next run re-reads it into pipeline\tme_lines.json.

Yesterday, before the appointment table loads
---------------------------------------------
The appointment table loads at about 2 pm, so in the morning it ends the day before yesterday. The refresh then
rebuilds yesterday from the live ME allocation API (http://192.168.8.121:8082, read-only) with the Sales MIS counting
rules and shows it like any other day. Until the deals tables have yesterday (about 10:15 am),
its deals are the system's Dealclosed records in the API (allocationType 103). Appointments given are usually within
1-4% of the final figure; deals closed are an early estimate, because the system's Dealclosed records and the deals
tables do not always agree on the business or the day. The afternoon run replaces it with the table's own numbers.
The PC needs the office network for the API.

Schedule (Windows)
------------------
Run once:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
It adds the task "Mumbai ME Team Performance refresh": every day at 08:00 (yesterday from the API; its deals are
the system's Dealclosed records) and 14:30 (yesterday from the appointment table, which loads at about 14:05, and
deals closed from the deals tables, as the Sales MIS counts them). If the table is late, run  python main.py  again.
It may wake the PC from sleep; to run while logged off: Task Scheduler > the task > Properties > "Run whether user is logged on
or not". Remove it with:  Unregister-ScheduledTask -TaskName "Mumbai ME Team Performance refresh" -Confirm:$false

Counting (as the Sales MIS "ME Appointment Given / ME Appnt Attended", Mumbai, JDS-ME)
-------------------------------------------------------------------------------------
Given = final_datacity Mumbai, jda_flag 0 or 3, any disposition except "Not Counted/Cancelled" (BDE-set included);
Attended = Dealclosed, Follow Up, Not Interested; MEs in team Corporate or section Sales (Training) left out;
a Sunday appointment counts on the Saturday before.
Deals closed = the Sales MIS "Deals Closed" (JDS-ME): every deal row in db_paidcontracts.daily_deals_closed_dump
(SUM of dc_genio, one row per payment version) with jda_flag 0 or 3, of an ME who was a Mumbai ME that month, with
or without an appointment behind it (no TME = TME team "Cold call (no TME)"). Conversion = deals closed / attended.
TME calls dialed = dialer calls whose agent is a TME (emptype 'TME') in db_paidcontracts.tbl_working_days_final_data
that month; connected = call_trunk_duration > 0 and one of the agreed call end types (list in pipeline\fetch_calls.py).

The page shows internal employee data. environment.py holds passwords: keep both private, and do not put this kit
or environment.py in a shared or public folder.
