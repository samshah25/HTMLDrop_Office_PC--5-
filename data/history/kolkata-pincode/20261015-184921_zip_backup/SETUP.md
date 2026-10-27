# Kolkata JDA dashboard: self-hosting kit

This folder has everything needed to refresh the Kolkata JDA vs JDS pincode dashboard every day and share it with
others on your network: the scripts, reference files and caches, and the database logins.

## Quick start (about 15 minutes, once)

1. Unzip this folder somewhere permanent, e.g. `D:\JDA\JDA_Kolkata_Dashboard_Kit`. Don't move it afterwards: the scheduled tasks point here.
2. Put the two database login files in `pipeline\`: **`db_216.env`** (deals and listings) and **`db_240.env`** (company master).
   Get them from Sarvesh, or copy each `*.env.template` to `*.env` and fill in `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER` and `MYSQL_PASSWORD`. Read-only access is enough.
   They are not in this zip on purpose.
3. Make sure the PC is on the **office network or VPN** (the databases and the presentation feed are internal).
4. Double-click **`SETUP.bat`**. It:
   1. checks Python (install Python 3.10+ from python.org first, ticking "Add python.exe to PATH");
   2. installs the two libraries it needs (`pymysql`, `openpyxl`);
   3. runs the first refresh (about 15 minutes);
   4. schedules the daily refresh at 12:30 and starts sharing.
5. Open **http://localhost:8090/** to check. Colleagues use **http://&lt;your-PC-name-or-IP&gt;:8090/**; the server window shows the address.
   If they can't reach it, allow Python through Windows Firewall when Windows asks (private networks).

If the scheduled tasks fail with "access denied", right-click `SETUP.bat` → **Run as administrator**.

## Host it with this kit's server only

Use `host_dashboard.bat` (or `python pipeline\serve_dashboard.py`), not VS Code Live Server, `python -m http.server` or IIS
pointed at this folder. Two reasons:

- **Safety:** a general web server shares *every* file in the folder, including the database logins in `pipeline\`.
  This server shares only the dashboard page.
- **Speed:** it sends the page compressed (about 6 MB instead of 53 MB). Repeat visits only re-check
  the file, so the page loads from the browser's copy until the next daily refresh.

To keep a port you already use, give it as a number, e.g. `host_dashboard.bat 8085`; the address is then
`http://<your-PC>:8085/`. `/JDA_Kolkata_Dashboard_UI_Lab.html` works too.

## Update of 15 Oct 2026

New on **Team productivity**: each JDA's HR work location (city from `db_paidcontracts`.`tbl_working_days_final_data`,
else `db_paidcontracts`.`hr_all_daily_copy_ganesh`) with an "outside branch" tag and a summary of JDAs from outside the
branch; JDA and manager emp codes (searchable); drag-to-resize columns; click a JDA's name for their details; the
"Deployed vs not deployed" rows open those JDAs. On **Sub-verticals & sales groups**: a "Sales groups: All | Top 500 |
Top 250" switch (ranks from `pipeline\top500_sales_groups.csv`).

The HR details need the server-216 login in `pipeline\db_216.env` to be able to read `db_paidcontracts`.`hr_all_daily_copy_ganesh`
and `db_paidcontracts`.`tbl_working_days_final_data`. Without that the refresh still works, the log says
"HR work location not read", and those columns show "—".

## Day to day

- The dashboard refreshes itself every day at 12:30, with data up to the previous day. Viewers just reload the page.
- The server must be running for others to see the page. It starts every time you log in to Windows; to start it by hand, double-click `host_dashboard.bat`.
- To refresh now, run **`main.py`** (in VS Code: open it, then Run Python File), or double-click `pipeline\run_daily.bat`. Its log is `pipeline\run_daily.log`, with detail in `pipeline\refresh_log.txt`.
- The page itself is **`JDA_Kolkata_Dashboard_UI_Lab.html`**. Keep that name, and keep it the only `.html` in this folder: Sarvesh sends new versions under the same name. You can also open it directly in a browser, or send it on as a single file.

## When Sarvesh sends a new version of the page

Design changes come as just the `.html` file. It has the same name, `JDA_Kolkata_Dashboard_UI_Lab.html`: put it in
this folder, replacing the old one. The next refresh fills it with fresh data and **keeps its new design**: the refresh only
changes the data inside the page, never the look.

Now and then a new page needs data this kit doesn't make yet. The refresh then prints a note such as
"'listings by sales group' kept its last data: this page needs newer kit scripts", the rest of the page still refreshes,
and Sarvesh sends the updated scripts.

## Saved presentation days: never delete `pipeline\pres_store`

The presentation feed keeps only about 6 months. Each refresh saves every day it reads into `pipeline\pres_store\`
(one small file per day) and fetches again only the last 14 days, so older days come from there. Days the feed has
already dropped exist **only** in that folder: don't delete it, and keep it when moving the kit.

## Working in VS Code

Open this folder in VS Code (File → Open Folder). **The only script you run is `main.py`** at the top of the folder; it calls the others in order. For reference, the pieces:

| Path | What it does |
|---|---|
| `main.py` | **Run this.** Runs the steps below in order, then puts the fresh data into the dashboard page (keeping its design); logs to `pipeline\run_daily.log` |
| `pipeline\run_daily.bat` | What the daily scheduled task starts; it just runs `main.py` |
| `pipeline\refresh_kolkata_dashboard.py` | Pulls deals, presentations and listings from the databases into the base dashboard; presentations from the saved days in `pipeline\pres_store` plus the feed for the last 14 days |
| `pipeline\build_subvertical.py` | Adds the sub-vertical / sales-group views |
| `pipeline\update_roster.py` | Reads the live JDA roster from the JDA heads' Google Sheet (keeps the last copy if it can't) |
| `Mumbai\tools\build_ui_lab.py` | Builds the data for the page (as a full page, `pipeline\fresh_build.tmp`; `main.py` takes only its data) |
| `pipeline\serve_dashboard.py` | The small web server (port 8090); serves only the dashboard file |
| `pipeline\db_216.env`, `db_240.env` | Database logins, which you add (templates included). **Keep them private: never commit or forward them.** |
| `pipeline\*.json`, `*.xlsx`, `geonames_IN.txt` | Reference files and caches; listing caches refresh themselves about monthly |


## Rules that keep the numbers right

- Sales are SUM(`dc_genio`) from `db_paidcontracts.daily_deals_closed_dump`. A JDA + JDS joint deal counts ½ to each side, and B2B deals are left out.
- A "working day" is any day on which anyone made a sale in the area shown, so branch holidays drop out of the per-day figures.
- Database access is read-only; the scripts only SELECT. Scratch tables, where used, sit in `ops_analytics`.

## Stopping or removing

- Stop sharing: close the server window.
- Remove the scheduled jobs: `schtasks /delete /tn "JDA Kolkata dashboard - daily refresh" /f` and `schtasks /delete /tn "JDA Kolkata dashboard - hosting" /f`.
