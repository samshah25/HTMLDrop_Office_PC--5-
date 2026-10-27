@echo off
REM One-time setup for the Kolkata JDA dashboard on this PC. Double-click it (or right-click > Run as administrator
REM if the scheduled tasks fail with "access denied").
setlocal
cd /d %~dp0
echo.
echo === 1/4  Checking Python ===
python --version || (echo Python 3 is not installed or not on PATH. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again. & pause & exit /b 1)
if not exist "pipeline\db_216.env" (echo Missing pipeline\db_216.env: copy db_216.env.template to db_216.env and fill in the database login ^(see SETUP.md^). & pause & exit /b 1)
if not exist "pipeline\db_240.env" (echo Missing pipeline\db_240.env: copy db_240.env.template to db_240.env and fill in the database login ^(see SETUP.md^). & pause & exit /b 1)
echo.
echo === 2/4  Installing the two Python libraries ===
python -m pip install --user -r requirements.txt || (echo pip install failed. & pause & exit /b 1)
echo.
echo === 3/4  First refresh (needs the office network or VPN; takes about 15 minutes) ===
call "pipeline\run_daily.bat"
if errorlevel 1 (echo The first refresh failed: see pipeline\run_daily.log. The last dashboard in this folder still works. & pause & exit /b 1)
echo Refresh finished.
echo.
echo === 4/4  Daily refresh at 12:30 and hosting at log-on ===
schtasks /create /tn "JDA Kolkata dashboard - daily refresh" /tr "\"%~dp0pipeline\run_daily.bat\"" /sc daily /st 12:30 /f
schtasks /create /tn "JDA Kolkata dashboard - hosting" /tr "\"%~dp0host_dashboard.bat\"" /sc onlogon /f
echo.
echo Setup done. Starting the dashboard server now (this window must stay open to keep sharing):
call "%~dp0host_dashboard.bat"
