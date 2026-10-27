HTMLDrop - Changed Files Update Package
==========================================

This package contains ONLY the modified frontend and backend files:
1. Master_dashboard.html
   - Dark theme folder pockets with live embedded dashboards
   - 2-in-1 line layout (symmetrical 2-column view)
   - Dynamic pocket sizing with horizontal scrolling for new dashboards
   - Clicking on a dashboard card opens the dashboard directly in browser
   - Clicking folder body or tab expands it into full 2-column grid
   - Clean UI without pink dog-ear triangles, view mode toggle, or General/All filters
2. portal.html
   - Step 3 now asks "Show on master dashboard?" (No, just host it / Yes, on master dashboard)
   - Interactive Section Selection popup modal asking which section to place the dashboard in:
     (Sales Funnel, Location, Renewals, Sales Operations & Overview, Collections, Workforce)
   - Clean category assignment and badge preview
3. server.py
   - Backend support for saving selected category metadata on upload and settings edit
   - Live synchronization with Master Dashboard

HOW TO APPLY ON OFFICE PC:
--------------------------
1. Stop the running HTML Drop server on the Office PC (close the window or Ctrl+C).
2. Copy the 3 files (Master_dashboard.html, portal.html, server.py) into your HTMLDrop folder on the Office PC.
   (Overwrite the existing 3 files).
   NOTE: Do NOT delete or touch your data/ directory or config.json. All newly added dashboards, history, logins, and configurations on the Office PC will remain completely intact!
3. Start HTML Drop again (run start.bat or restart.bat).
