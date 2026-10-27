@echo off
REM Share the Kolkata JDA dashboard on the network (serves only the dashboard file, never the pipeline folder).
cd /d %~dp0pipeline
python serve_dashboard.py %1
pause
