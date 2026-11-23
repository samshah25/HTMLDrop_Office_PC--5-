# JD India sales overview: setup

The dashboard is **one file**, `jd-india-sales-overview.html`. It holds its own data, so it opens in any browser
and needs no internet connection. **The only script you run is `main.py`**; it rebuilds that file with the latest data
twice a month, on the **15th** and on the **last day of the month**.

This is a separate dashboard from the Pan India JDA dashboard. It has its own folder, refresh and server port, and the
two can run side by side.

## One-time setup

1. **Python 3.9 or newer.** In this folder, run `pip install -r requirements.txt`.
2. **Database login.** In `pipeline\`, copy `db_216.env.template` to `db_216.env` and fill in the login for the deals
   database (172.29.0.216). Read-only access is enough. Never share or commit this file.
3. **Network.** The PC needs to reach the database (172.29.0.216, port 3306).
4. **First refresh.** Run `python main.py --now`. It takes about a minute.
5. **Schedule it.** Run `python main.py --install` once. This creates the Windows task "JD India sales overview refresh"
   (every day at 07:00). It refreshes only on the 15th and the month end; on other days it does nothing.

## Refreshing

- **Twice a month, by itself:** the scheduled task runs `main.py` every morning at 07:00. It refreshes when the 15th
  or the last day of the month has come since the last good refresh, and otherwise does nothing.
  - The PC must be on and you must be logged in at 07:00. If it was off on a refresh day, the next morning's run
    catches up.
  - The data runs to the latest closed deal, so the 15th's run shows data to the 14th, and the month-end run data to
    the day before the month end.
  - The date of the last good refresh is kept in `pipeline\last_refresh.txt`. A failed refresh is tried again the
    next morning.
- **Other commands:**
  - `python main.py --now`: refresh right away, whatever the date.
  - `python main.py --check`: show the last refresh and the next refresh day (changes nothing).
  - `python main.py --uninstall`: remove the scheduled task.
- **Self-check:** every refresh compares the page's totals with the deals table. If they don't match, the refresh
  stops, says so, and leaves the last good dashboard as it is. Details are in `pipelineefresh.log`.

## Hosting

- **With your own web server** (IIS, nginx, a shared folder): copy the `.html` file there after each refresh. The page
  is about 18 MB (5 MB compressed) because it carries day-by-day data (deals, unique customers, and every deal of ₹50,000 RV 3yr or more one by one), so viewers can pick any dates and leave out big deals. Turn on gzip compression for `.html`
  in your web server.
- **Or with the included server:** `python serve_dashboard.py` shares the page at `http://<this-pc>:8093/`. Add a port
  number to change it, for example `python serve_dashboard.py 8096`. Only the dashboard file is served, never the
  pipeline folder with its login. The page is compressed, and browsers re-use their copy until the next refresh.
- You can rename the `.html` file. Keep it the only `.html` in this folder: the refresh then updates the renamed file,
  and the server serves it.

## What's in the folder

| File | What it does |
|---|---|
| `main.py` | **Run this.** Refreshes on the 15th and the month end; `--now`, `--check`, `--install`, `--uninstall`. |
| `refresh_dashboard.py` | The refresh itself, called by `main.py`: runs the two steps below in order. |
| `serve_dashboard.py` | Optional: shares the page on your network (port 8093). |
| `pipeline\fetch_data.py` | Step 1: pulls deals and RV 3yr by pincode and day (this year and the same dates last year) into `pipeline\cache\` |
| `pipeline\build_dashboard.py` | Step 2: checks the totals and puts the new data into the page. With `--full` it also rebuilds the page from its design files in `pipeline\app\` |
| `pipeline\reference\` | Pincode → branch and city list; GeoNames places (state, district, location) |

## If something goes wrong

- **"Missing pipeline\db_216.env"**: see step 2 of the setup.
- **"Can't connect to MySQL server"**: the PC cannot reach 172.29.0.216. Check VPN or network access.
- **"Totals do not match the deals table"**: the page was not changed. Run the refresh again later. If it keeps
  happening, send `pipeline\refresh.log` to Sarvesh.
- **"needs data format …"**: the page is newer than the pipeline files. Ask Sarvesh for the matching pipeline files.
- **The page looks old in the browser**: reload it. The dates at the top right show the data's last day.
