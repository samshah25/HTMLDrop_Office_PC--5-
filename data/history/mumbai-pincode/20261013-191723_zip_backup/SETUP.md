# Mumbai JDA dashboard: self-hosting kit

This folder has everything needed to refresh the Mumbai JDA vs JDS pincode dashboard every day and share it with
others on your network: the scripts, reference files and caches, and the database logins.

## Quick start (about 12 minutes, once)

1. Unzip this folder somewhere permanent, e.g. `D:\JDA\JDA_Mumbai_Dashboard_Kit`. Don't move it afterwards: the scheduled tasks point here.
2. Put the two database login files in `pipeline\`: **`db_216.env`** (deals and listings) and **`db_240.env`** (company master).
   Get them from Sarvesh, or copy each `*.env.template` to `*.env` and fill in `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER` and `MYSQL_PASSWORD`. Read-only access is enough.
   They are not in this zip on purpose.
3. Make sure the PC is on the **office network or VPN** (the databases and the presentation feed are internal).
4. Double-click **`SETUP.bat`**. It:
   1. checks Python (install Python 3.10+ from python.org first, ticking "Add python.exe to PATH");
   2. installs the two libraries it needs (`pymysql`, `openpyxl`);
   3. runs the first refresh (about 12 minutes);
   4. schedules the daily refresh at 12:45 and starts sharing.
5. Open **http://localhost:8091/** to check. Colleagues use **http://&lt;your-PC-name-or-IP&gt;:8091/**; the server window shows the address.
   If they can't reach it, allow Python through Windows Firewall when Windows asks (private networks).

If the scheduled tasks fail with "access denied", right-click `SETUP.bat` → **Run as administrator**.

## Host it with this kit's server only

Use `host_dashboard.bat` (or `python pipeline\serve_dashboard.py`), not VS Code Live Server, `python -m http.server` or IIS
pointed at this folder. Two reasons:

- **Safety:** a general web server shares *every* file in the folder, including the database logins in `pipeline\`.
  This server shares only the dashboard page.
- **Speed:** it sends the page compressed (about 6 MB instead of 17 MB). Repeat visits only re-check
  the file, so the page loads from the browser's copy until the next daily refresh.

To keep a port you already use, give it as a number, e.g. `host_dashboard.bat 8085`; the address is then
`http://<your-PC>:8085/`. `/Mumbai_JDA_Dashboard.html` works too.

## Day to day

- The dashboard refreshes itself every day at 12:45, with data up to the previous day. Viewers just reload the page.
- The server must be running for others to see the page. It starts every time you log in to Windows; to start it by hand, double-click `host_dashboard.bat`.
- To refresh now, run **`refresh_dashboard.py`** (in VS Code: open it, then Run Python File), or double-click `pipeline\run_daily.bat`. Its log is `pipeline\run_daily.log`, with detail in `pipeline\refresh_log.txt`.
- The page itself is **`Mumbai_JDA_Dashboard.html`**. You can also open it directly in a browser, or send it on as a single file.

## Working in VS Code

Open this folder in VS Code (File → Open Folder). **The only script you run is `refresh_dashboard.py`** at the top of the folder; it calls the others in order. For reference, the pieces:

| Path | What it does |
|---|---|
| `refresh_dashboard.py` | **Run this.** Runs the steps below in order and logs to `pipeline\run_daily.log` |
| `pipeline\run_daily.bat` | What the daily scheduled task starts; it just runs `refresh_dashboard.py` |
| `pipeline\refresh_mumbai_dashboard.py` | Pulls deals, presentations and listings from the databases into `pipeline\base` |
| `pipeline\build_subvertical.py` | Adds the sub-vertical / sales-group views |
| `pipeline\build_top200.py` | Top-200 JDA categories (deals daily, listings about monthly) |
| `tools\build_ui_lab.py` | Builds the final dashboard page (`Mumbai_JDA_Dashboard.html`) from the refreshed data |
| `pipeline\serve_dashboard.py` | The small web server (port 8091); serves only the dashboard file |
| `pipeline\db_216.env`, `db_240.env` | Database logins, which you add (templates included). **Keep them private: never commit or forward them.** |
| `pipeline\*.json`, `*.xlsx`, `geonames_IN.txt` | Reference files and caches; listing caches refresh themselves about monthly |


## Rules that keep the numbers right

- Sales are SUM(`dc_genio`) from `db_paidcontracts.daily_deals_closed_dump`. A JDA + JDS joint deal counts ½ to each side, and B2B deals are left out.
- A "working day" is any day on which anyone made a sale in the area shown, so branch holidays drop out of the per-day figures.
- Database access is read-only; the scripts only SELECT. Scratch tables, where used, sit in `ops_analytics`.

## Stopping or removing

- Stop sharing: close the server window.
- Remove the scheduled jobs: `schtasks /delete /tn "JDA Mumbai dashboard - daily refresh" /f` and `schtasks /delete /tn "JDA Mumbai dashboard - hosting" /f`.
