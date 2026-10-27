# HTML Drop

A self-service portal for hosting HTML reports on the office network. Colleagues log in, upload
their own files and get a permanent link. Uploading again under the same link name updates the page.

## Moving it to the office PC
1. Copy this whole folder to the office PC (without `data` and `config.json`, if they exist).
2. Install Python 3.9 or newer from python.org and tick **Add python.exe to PATH**.
3. Open PowerShell in this folder (as administrator if you can; it also works without) and run:
   `powershell -ExecutionPolicy Bypass -File .\setup_office_pc.ps1`
   Without administrator rights the firewall step is skipped. HTML Drop runs as `python.exe`, like the
   other dashboard servers, so colleagues can usually reach it anyway. If they can't, ask IT to allow TCP port 8150.
4. Share the link it prints, for example `http://yourpcname:8150/`.
5. Update the master dashboard: in the folder that serves `http://172.29.65.188:8075/`, back up the
   old `Master_dashboard.html`, then copy this folder's `Master_dashboard.html` over it (same name).
   Its address does not change.
6. The existing dashboards appear in their owners' **My pages** by themselves: HTML Drop adds them
   every time it starts. They **keep their original links** (ports 8080, 8085, ...) and stay on their
   own servers. The list (owners included) is `EXISTING_DASHBOARDS` in `server.py`: edit it and
   double-click `restart.bat`. Only pages uploaded through HTML Drop get a link on port 8150.
   **Replace** swaps in a new file on the same link (old version backed up in `data/history/`); for an
   existing dashboard, the first Replace finds its file on the PC by itself.

To run it by hand instead of at login, double-click `start.bat`.

## Users
Logging in is just a **User** (a name, like `Muskan`) and a **PIN** (4+ characters).
- **The admin user** is created on the first run: user `admin_username` (default `admin`), PIN
  `admin_password`, both in `config.json`. Log in with it, then click **Change PIN** in the top bar.
- **Everyone else** clicks **New user** on the upload page and picks a user name and PIN.
  To turn that off, set `"allow_signup": false` in `config.json` and restart the server.
- **Users** can publish, and update, retitle, move or delete **their own** pages (the **My pages** tab).
- **Admins** can do that for **every** page, and manage users at `/admin` > **Users**:
  reset a PIN, make someone an admin, or remove a user (their pages stay online).
- Forgot a PIN? An admin resets it and tells the person, who can change it after logging in.

Anyone on the network can still open a page's link without logging in.

## The ⋯ menu: Disable or Delete
Each page in **My pages** has a **⋯** menu: Rename, Disable temporarily / Enable, Change settings
(uploaded pages only) and Delete. **Rename** changes only the name shown in My pages; the link never
changes (works for existing dashboards too, and survives restarts).
- **Disable temporarily**: its link shows "Temporarily unavailable" and it disappears from the master
  dashboard. Nothing is deleted: an existing dashboard's real file is kept in `data/disabled/`
  meanwhile. **Enable** brings it back on the same link, exactly as it was. Or **Replace** it first:
  the new file waits, hidden, until you Enable.
- **Delete**: for good. The link stops working and it leaves the master dashboard and My pages. For
  an existing dashboard the file is removed from its own folder. A copy of every deleted page stays in
  `data/trash/`, so the admin can put one back by hand if needed. It isn't added back at the next start.

## Choosing what appears on the master dashboard
Uploaders answer **Show on master dashboard?** on the upload form: *No, just host it* /
*Yes, in General* / *Yes, in All dashboards only*. To change it later without a new file, click
**Change** on the page in **My pages**, pick a different option and click **Save changes**.

Admins can also override it at `/admin` > **Pages**, and set each page's **Category** (sidebar group)
and **Title on dashboard**. Uploads the admin hasn't checked yet are marked **NEW**. The category keys
come from `hub_categories` in `config.json` and must match `CATEGORIES` in `Master_Dashboard.html`.

The master dashboard stays on its own server at `http://172.29.65.188:8075/Master_dashboard.html`.
It picks changes up within 2 minutes, or right away on refresh, by asking HTML Drop on port 8150
(`DROP`, near the top of its script). Dashboards that run on their own ports are still listed by hand
in its `DASHBOARDS` array. To add one, copy a line there. The upload page's **Master dashboard** link
comes from `master_dashboard_url` in `config.json`.

## Files
| Path | What it is |
|---|---|
| `server.py` | The server (Python standard library only) |
| `portal.html` | The upload page (edit freely, no restart needed) |
| `admin.html` | The admin page at `/admin` |
| `Master_dashboard.html` | The updated master dashboard. Copy it over the one served on port 8075 |
| `restart.bat` | Restarts HTML Drop after you replace its files |
| `config.json` | Created on first run: port, admin user and starting PIN, new users on/off, upload limit |
| `data/users.json` | Users (PINs are stored hashed, never in plain text) |
| `data/sites/` | Live pages, one folder per link name |
| `data/history/` | Previous versions (last 10 per page). Copy one back into `data/sites/<name>/` to roll back |
| `data/trash/` | Deleted pages |
| `run_hidden.vbs` | Starts the server with no window (used at login) |
| `server.log` | Log when auto-started |

Back up the `data` folder regularly.

## Tips for uploaders
- A single self-contained `.html` file: just upload it.
- A report with separate images, CSS, JS or data files: zip the folder and upload the `.zip`.
  Links inside it must be relative (`assets/chart.js`), not `C:\...`.

## Stopping or removing it
- Stop: Task Manager > Details > end the `python.exe` whose command line has `server.py`
- Remove auto-start: `Unregister-ScheduledTask "HTML Drop"`, or delete "HTML Drop" from your
  Startup folder (Win+R, `shell:startup`), whichever the setup created
- Remove firewall rule: `Remove-NetFirewallRule -DisplayName "HTML Drop"`
