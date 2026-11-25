@echo off
REM Refresh the Jaipur tenure grid (Task Scheduler runs this at 07:30, 11:30 and 14:30; see setup_schedule.ps1).
cd /d "%~dp0"
python main.py
