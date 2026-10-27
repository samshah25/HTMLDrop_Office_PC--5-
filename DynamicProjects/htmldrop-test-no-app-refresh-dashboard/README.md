# HTML Drop Test Project — No app.py

This test project intentionally has **no `app.py`**.

## Contents
- `index.html` — static dashboard entry page
- `refresh_dashboard.py` — safe test refresh script; writes `data/refresh_status.json` and appends `logs/refresh.log`
- `data/` — refresh output
- `logs/` — refresh log output

## Expected HTML Drop behavior
1. Upload this ZIP through the existing HTML Drop upload page.
2. HTML Drop should recognize and serve the static `index.html` without requiring `app.py`.
3. `Refresh now` should execute `refresh_dashboard.py`.
4. If automatic refresh is configured, Windows Task Scheduler should run `refresh_dashboard.py` on the machine hosting HTML Drop.
5. If the project cannot launch, check the HTML Drop project logs and ensure static HTML projects are supported.

The script only writes a small JSON status file and a local log; it does not access the network or modify data outside this project folder.
