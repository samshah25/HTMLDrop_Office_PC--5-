@echo off
REM Daily refresh of the Mumbai JDA dashboard: runs refresh_dashboard.py (the one script that runs every step).
cd /d %~dp0..
python refresh_dashboard.py
