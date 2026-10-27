============================================================
HTML DROP DYNAMIC TEST PROJECT WITH AUTOMATIC REFRESH
============================================================

Files in this project:
- index.html        : Interactive dashboard UI with KPI cards and table
- main.py           : Refresh script executed by Task Scheduler or manually
- data.json         : Live JSON data file updated by main.py
- refresh.log       : Log file recording each refresh execution
- requirements.txt  : Dependencies list (standard library only)

HOW TO RUN MANUALLY:
1. Open PowerShell or Command Prompt in this folder.
2. Run:
     python main.py
3. Open or refresh index.html in your browser. You will see new random revenue,
   updated percentages, and the new timestamp!

HOW TO TEST IN HTML DROP:
1. Upload HTMLDrop_Test_Project.zip on HTML Drop (http://localhost:8150/).
2. In the "Dynamic projects" section:
   - Click "Refresh now" to trigger execution via Windows Task Scheduler.
   - Click "Refresh settings" to schedule daily or hourly runs.
============================================================
