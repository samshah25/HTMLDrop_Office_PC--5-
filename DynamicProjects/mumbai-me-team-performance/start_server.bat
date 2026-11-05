@echo off
rem The login server for the ME team dashboard (each manager sees only their own team). Keep this window open.
rem It sits behind HTML Drop: everyone opens the usual link http://<this PC>:8150/s/mumbai-me-team-performance/
rem (HTML Drop needs htmldrop_login_proxy.py added once; see README.txt, "Logins").
rem Put a shortcut to this file in the Startup folder (Win+R, shell:startup) to start it when the PC starts.
cd /d "%~dp0"
python serve_dashboard.py --behind-htmldrop
pause
