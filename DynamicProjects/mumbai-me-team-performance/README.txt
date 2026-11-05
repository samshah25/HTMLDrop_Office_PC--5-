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
  manager_pages\                    one page per manager under Kushal Sharma, each with only that manager's team
                                    (rebuilt by every refresh)
  serve_dashboard.py                the login server: each login sees only its own page (see "Logins" below)
  logins.json                       the logins, their pages and hashed passwords (no password is stored in clear)
  start_server.bat                  starts the login server

Data in this copy: appointments 1 Apr 2026 - 1 Nov 2026 (Sunday appointments counted on the Saturday before,
as the Sales MIS does), TMEs' calls to 31 Oct 2026, read 2 Nov 2026, 14:33.

Updating from the 27 Oct kit
----------------------------
Unzip over the old folder (the new environment.py already holds the logins for servers 240, 216 and 120). Then:
  pip install -r pipeline\requirements.txt
  python main.py
then set up the sign-in on the usual link (see "Logins" below).
The first run pulls the TMEs' calls since 1 April
(a few minutes longer than usual); later runs pull only the current month.
pipeline\build_dashboard.py and pipeline\app\app.js, app.css, shell.tpl are no longer used and can be deleted
(keep pipeline\app\fonts and pipeline\app\jd_logo.png).

ME and TME mode
---------------
The ME | TME switch in the top bar shows the same page for MEs or for TMEs (amber). The dates are one filter for both.
ME mode follows the ME team's hierarchy (ME head > managers > team leaders > MEs). TME mode follows the TMEs'
reporting lines from the SSO dump (pipeline\tme_lines.json) and HR's TME team (Super Cat, Hot Data, ...).
The page opens on Kushal Sharma's line only; "All MEs" can be picked in Settings for the open browser tab.

Logins (2 Nov 2026; on the usual link since 5 Nov): each manager sees only their own team
------------------------------------------------------------------------------------------
Everyone opens the usual link, which now asks for a sign-in:
  http://172.29.65.188:8150/s/mumbai-me-team-performance/
  - Kushal Sharma's login opens the whole dashboard (Mumbai ME Team Performance.html);
  - each of the 8 managers' logins opens manager_pages\<manager code>.html: that manager's team only (their team
    leaders, MEs, appointments, deals closed and businesses). Its "Mumbai" comparison figures are Kushal Sharma's whole
    line added up; no other team's MEs, team leaders or businesses are in the file. No TME mode on these pages.
How it works: serve_dashboard.py (the login server) runs on this PC on port 8160, reachable from this PC only. HTML Drop
hands every request for the link above to it (htmldrop_login_proxy.py) and sends the answer back. Other HTML Drop pages
are not touched.
One-time setup
  1. HTML Drop: copy htmldrop_login_proxy.py next to HTML Drop's own .py file; add  import htmldrop_login_proxy  with its
     other imports; make  if htmldrop_login_proxy.handle(self): return  the first line of do_GET, do_POST and do_HEAD in
     its request handler class (details at the top of htmldrop_login_proxy.py). Restart HTML Drop.
  2. Start the login server: double-click start_server.bat and keep the window open. To start it with the PC:
     Win+R, shell:startup, and put a shortcut to start_server.bat in that folder.
  3. In HTML Drop, replace the uploaded "Mumbai ME Team Performance.html" at this link with
     htmldrop_placeholder\Mumbai ME Team Performance.html (same name, no data inside), so the old open copy is gone.
     Its card on the master dashboard stays.
  4. Check: open the link, sign in.
Every day: nothing changes. main.py rewrites the pages and the login server picks them up by itself; nothing to upload.
  - If the login server is not running, the link says the dashboard's sign-in is not running right now.
  - A sign-in lasts 12 hours. Five wrong passwords lock a login for 15 minutes. serve_log.txt lists every sign-in,
    failed try and page view, with the viewer's PC address.
  - Change a password:  python serve_dashboard.py --set-password <login id> <new password>
    List the logins:     python serve_dashboard.py --list
    The login IDs and passwords were given to Kushal Sharma separately; they are not in this kit.
IMPORTANT
  - Do not serve this folder with any other web server, and do not upload it to HTML Drop as a project: it holds every
    manager's page, logins.json and environment.py (database passwords). Only serve_dashboard.py should serve it.
  - The connection is plain http inside the office network (no https), as the other dashboards.

Hosting without logins (old way)
--------------------------------
"Mumbai ME Team Performance.html" is one self-contained page (no server code, database or internet needed), but
hosting it openly lets anyone who has the link see every team.

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
