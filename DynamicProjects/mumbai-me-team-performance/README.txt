Mumbai ME Team Performance - dashboard kit
==========================================

Top level
---------
  Mumbai ME Team Performance.html   the dashboard (one self-contained page: data, fonts and logo inside)
  main.py                           refreshes the data and rebuilds the page:  python main.py
  environment.py                    database logins (DB_240, DB_216) and CITY - fill in before the first refresh
  run_daily.bat                     same as "python main.py", for Windows Task Scheduler
  setup_schedule.ps1                registers the daily runs in Task Scheduler (08:00, 14:30)
  pipeline\                         the refresh steps and the page design files (no need to touch)

Data in this copy: appointments 1 Apr 2026 - 14 Oct 2026 (Sunday appointments counted on the Saturday before,
as the Sales MIS does), deals closed to 14 Oct 2026, read 15 Oct 2026, 16:24.

Teams
-----
The page follows the ME team's hierarchy: ME head > managers > team leaders > MEs. The team button in the top bar
shows one manager's or team leader's team on the whole page; "Show" (on the Table and on the Overview's
"Your team" card, one choice for both) switches between Managers, Team leaders and MEs (each team line adds up
its MEs; > opens it). For now the hierarchy comes from HR's reporting
lines (each person's usual manager on their appointments); it will follow the official list once it is in.

Hosting
-------
Serve "Mumbai ME Team Performance.html" from this folder (any static web server) or copy it to the host.
It needs no server code, no database and no internet connection.

Refresh
-------
1. Python 3.9+ and:  pip install -r pipeline\requirements.txt   (one package: pymysql)
2. environment.py must hold read-only logins for server 240 (datagrowth.tbl_final_data_appt) and server 216
   (db_paidcontracts: deals and HR).
3. Run:  python main.py   (about 2-3 minutes). It pulls appointments, then yesterday from the allocation API if the
   appointment table does not have it yet, then deals and HR, then rewrites "Mumbai ME Team Performance.html" in this
   folder. If a step fails, it stops and the page keeps its last good data (if only the API cannot be reached, the
   refresh carries on without yesterday). Log: pipeline\refresh_log.txt.
   Rebuild from the last pulled data only:  python main.py --build-only

Yesterday, before the appointment table loads
---------------------------------------------
The appointment table loads at about 2 pm, so in the morning it ends the day before yesterday. The refresh then
rebuilds yesterday from the live ME allocation API (http://192.168.8.121:8082, read-only) with the Sales MIS counting
rules and shows it like any other day. Until the deals tables have yesterday (about 10:15 am),
its deals are the system's Dealclosed records in the API (allocationType 103). Appointments given are usually within
1-4% of the final figure; deals closed are an early estimate, because the system's Dealclosed records and the deals
tables do not always agree on the business or the day (15 Oct: 62 at 08:00, 79 in the deals tables). The afternoon run replaces it with the table's own numbers. The PC needs the office network for the API.

Schedule (Windows)
------------------
Run once:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
(Run it again after updating from a kit dated 16 Oct 2026 or earlier: a run may now take up to 2 hours instead of 30 minutes,
so a PC that wakes late is not stopped silently. A run that still never finishes is noted at the top of the next run's log.)
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

The page shows internal employee data. environment.py, once filled in, holds passwords: keep both private.
