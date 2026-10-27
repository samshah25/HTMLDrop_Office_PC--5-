HTML Drop - Refresh Scheduling Test ZIP

Contents:
- index.html: simple dashboard entry point
- refresh_dashboard.py: test refresh script (exact expected filename at ZIP root)
- data/ and logs/: created automatically by the refresh script when it runs

Expected test:
1. Upload this ZIP through HTML Drop.
2. The project should publish as a Dynamic Project.
3. Because refresh_dashboard.py exists at the ZIP root, the UI should offer to configure automatic refresh.
4. If you accept, select a schedule and time.
5. Open the dashboard and click "Check again" after the refresh runs to see its timestamp and run count.

The script only writes local test status/log files. It does not connect to SQL, email, or any external service.
