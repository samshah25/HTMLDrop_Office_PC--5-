@echo off
rem Restarts HTML Drop, e.g. after you replace its files. It keeps running hidden, like at login.
cd /d "%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 /nobreak >nul
wscript "%~dp0run_hidden.vbs"
timeout /t 4 /nobreak >nul
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8150 -State Listen -ErrorAction SilentlyContinue) { 'HTML Drop is running: http://localhost:8150/' } else { 'HTML Drop did not start. Double-click start.bat to see the error.' }"
pause
