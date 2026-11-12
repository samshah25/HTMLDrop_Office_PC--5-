@echo off
rem The login server for the ME team dashboard (each manager sees only their own team). Keep this window open.
rem Put a shortcut to this file in the Startup folder (Win+R, shell:startup) to start it when the PC starts.
cd /d "%~dp0"
python serve_dashboard.py
pause
