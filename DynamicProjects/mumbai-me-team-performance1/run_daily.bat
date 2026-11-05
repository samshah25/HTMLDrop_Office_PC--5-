@echo off
REM Refresh the Mumbai ME Team Performance dashboard (Task Scheduler runs this; see setup_schedule.ps1).
REM Morning run: yesterday comes from the live allocation API, marked provisional.
REM Afternoon run: once the appointment table has loaded, yesterday comes from the table.
cd /d "%~dp0"
python main.py
