@echo off
rem Runs HTML Drop in this window. Close the window (or Ctrl+C) to stop.
cd /d "%~dp0"
python server.py
pause
