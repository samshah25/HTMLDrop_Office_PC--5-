#!/usr/bin/env python3
"""HTML Drop - a self-service LAN hosting portal for HTML reports.

People open http://<this-pc>:<port>/, log in (or create an account), upload an
.html file (or a .zip with assets), and get a permanent link. Re-uploading
under the same name replaces the live page and keeps the previous version in
data/history/. Each page belongs to the account that created it; admins can
manage every page and every account.

Standard library only - no pip install needed.
"""
import hashlib
import io
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import string
import sys
import urllib.request
import threading
import time
import traceback
import zipfile
import subprocess
import venv
import signal
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITES = DATA / "sites"
HISTORY = DATA / "history"
TRASH = DATA / "trash"
PARKED = DATA / "disabled"  # real files of disabled existing dashboards, kept until Enable
TMP = DATA / "tmp"
DYNAMIC_ROOT = ROOT / "DynamicProjects"
DYNAMIC_META_FILE = DATA / "dynamic_projects.json"
DYNAMIC_LOG_ROOT = ROOT / "logs" / "dynamic"
DYNAMIC_PORT_START = 8160
DYNAMIC_PORT_END = 8999
DYNAMIC_PROCESSES = {}
DYNAMIC_LOCK = threading.RLock()
META_FILE = DATA / "sites.json"
USERS_FILE = DATA / "users.json"
SESSIONS_FILE = DATA / "sessions.json"
CONFIG_FILE = ROOT / "config.json"
PORTAL_FILE = ROOT / "portal.html"
ADMIN_FILE = ROOT / "admin.html"
DYNAMIC_FILE = ROOT / "dynamic.html"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
# A user is just a name ("Muskan", "priya.s"); the lowercase form is the account key.
USER_RE = re.compile(r"^[a-z0-9][a-z0-9 ._-]{1,31}$")
ALLOWED_EXT = {".html", ".htm", ".zip"}
COOKIE = "hd_session"
SESSION_DAYS = 30
MIN_PASSWORD = 4  # the PIN

# Windows' registry often maps these wrongly, which breaks JS/CSS in browsers.
for ctype, ext in [
    ("text/javascript", ".js"), ("text/javascript", ".mjs"), ("text/css", ".css"),
    ("image/svg+xml", ".svg"), ("application/json", ".json"), ("font/woff2", ".woff2"),
    ("font/woff", ".woff"), ("application/wasm", ".wasm"), ("text/html", ".html"),
    ("text/html", ".htm"), ("text/csv", ".csv"),
]:
    mimetypes.add_type(ctype, ext)

lock = threading.Lock()


class UserError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


# ---------------------------------------------------------------- storage

# Must match the CATEGORIES keys in Master_Dashboard.html.
# Names offered in the login screen's User list. Anyone else can use "Add".
DEFAULT_MEMBERS = ["Ayush", "Ganesh", "Mohit", "Muskan", "Priyal", "Sarvesh", "Sounak"]

# Where the master dashboard is hosted (its own server); the upload page links to it.
DEFAULT_MASTER_URL = "http://172.29.65.188:8075/Master_dashboard.html"

DEFAULT_HUB_CATEGORIES = {
    "geo": "Geography", "hr": "Workforce", "funnel": "Sales Funnel",
    "renew": "Renewals", "ecs": "Collections",
}


def load_config():
    if not CONFIG_FILE.exists():
        cfg = {
            "port": 8150,
            "admin_username": "admin",
            "admin_password": secrets.token_urlsafe(9),
            "allow_signup": True,
            "max_upload_mb": 200,
            "keep_versions": 10,
            "hub_categories": DEFAULT_HUB_CATEGORIES,
            "master_dashboard_url": DEFAULT_MASTER_URL,
            "members": DEFAULT_MEMBERS,
        }
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print(f"Created config.json - log in as '{cfg['admin_username']}' "
              f"with PIN: {cfg['admin_password']}")
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


CONFIG = load_config()


def load_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_meta():
    return load_json(META_FILE)


def save_meta(meta):
    save_json(META_FILE, meta)


# ---------------------------------------------------------------- accounts

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def make_account(name, password, role):
    salt = secrets.token_hex(16)
    return {"name": name, "role": role, "salt": salt, "pw_hash": hash_password(password, salt),
            "created": datetime.now().isoformat(timespec="seconds")}


def check_password_rules(password):
    if len(password) < MIN_PASSWORD:
        raise UserError(f"PIN must be at least {MIN_PASSWORD} characters.")


def ensure_admin():
    """First run: create the admin account named in config.json."""
    with lock:
        users = load_json(USERS_FILE)
        if any(u["role"] == "admin" for u in users.values()):
            return
        username = str(CONFIG.get("admin_username", "admin")).lower()
        password = str(CONFIG.get("admin_password") or CONFIG.get("admin_pin") or "")
        if len(password) < MIN_PASSWORD:
            password = secrets.token_urlsafe(9)
            CONFIG["admin_password"] = password
            CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")
        users[username] = make_account("Admin", password, "admin")
        save_json(USERS_FILE, users)
        print(f"Admin user '{username}' created. Its PIN is admin_password in config.json.")


def public_user(username, u):
    return {"username": username, "name": u["name"], "role": u["role"]}


def display_name(users, username):
    u = users.get(username)
    if u:
        return u["name"]
    # Assigned to a member who hasn't set a PIN yet: use the name as written in config.
    for n in CONFIG.get("members", DEFAULT_MEMBERS):
        if user_key(str(n)) == username:
            return " ".join(str(n).split())
    return username or ""


def owners_of(r):
    """The page's owner first, then anyone it is shared with ("editors")."""
    return [u for u in [r.get("user", "")] + r.get("editors", []) if u]


def user_key(user):
    return " ".join(user.split()).lower()


def signup(user, password):
    if not CONFIG.get("allow_signup", True):
        raise UserError("New users are turned off. Ask the admin to add you.", 403)
    name = " ".join(user.split())[:32]
    username = name.lower()
    if not USER_RE.match(username):
        raise UserError("User: 2-32 letters or numbers (spaces, dots and dashes are fine).")
    check_password_rules(password)
    with lock:
        users = load_json(USERS_FILE)
        if username in users:
            raise UserError(f"'{name}' already exists. Log in instead, or pick another user.", 409)
        users[username] = make_account(name, password, "user")
        save_json(USERS_FILE, users)
    return username


def login(username, password):
    username = user_key(username)
    u = load_json(USERS_FILE).get(username)
    if not u or not secrets.compare_digest(hash_password(password, u["salt"]), u["pw_hash"]):
        time.sleep(0.5)  # slows password guessing
        raise UserError("Wrong user or PIN.", 401)
    return username


def member_list():
    """Everyone the login screen offers: the configured names plus every existing user.
    has_pin tells the page whether to ask "Choose your PIN" (first time) or just "PIN"."""
    users = load_json(USERS_FILE)
    names = {user_key(n): " ".join(str(n).split()) for n in CONFIG.get("members", DEFAULT_MEMBERS) if str(n).strip()}
    for key, u in users.items():
        names[key] = u["name"]
    return [{"name": n, "has_pin": k in users} for k, n in names.items()]


def auth_or_create(user, pin):
    """User + PIN typed on the upload form: log in, or create the user the first time."""
    if not user_key(user):
        raise UserError("Enter your user and PIN.", 401)
    users = load_json(USERS_FILE)
    if user_key(user) not in users:
        return signup(user, pin)
    try:
        return login(user, pin)
    except UserError:
        raise UserError(f"Wrong PIN for {users[user_key(user)]['name']}. "
                        "If that's not you, use a different user name.", 401)


def change_password(username, old, new):
    check_password_rules(new)
    with lock:
        users = load_json(USERS_FILE)
        u = users.get(username)
        if not u or not secrets.compare_digest(hash_password(old, u["salt"]), u["pw_hash"]):
            raise UserError("Your current PIN is wrong.", 403)
        users[username] = {**make_account(u["name"], new, u["role"]), "created": u["created"]}
        save_json(USERS_FILE, users)


def admin_user_action(me, action, username, value):
    with lock:
        users = load_json(USERS_FILE)
        u = users.get(username)
        if not u:
            raise UserError("No such user.", 404)
        if action == "reset":
            check_password_rules(value)
            users[username] = {**make_account(u["name"], value, u["role"]), "created": u["created"]}
            drop_sessions(username)
        elif action == "role":
            if value not in ("admin", "user"):
                raise UserError("Unknown role.")
            if value == "user" and u["role"] == "admin" and \
                    sum(x["role"] == "admin" for x in users.values()) == 1:
                raise UserError("You can't remove the last admin.")
            u["role"] = value
        elif action == "delete":
            if username == me:
                raise UserError("You can't delete your own account.")
            if u["role"] == "admin" and sum(x["role"] == "admin" for x in users.values()) == 1:
                raise UserError("You can't delete the last admin.")
            del users[username]
            drop_sessions(username)
        else:
            raise UserError("Unknown action.")
        save_json(USERS_FILE, users)


# ---------------------------------------------------------------- sessions

sessions = {}
sessions_lock = threading.Lock()


def load_sessions():
    now = time.time()
    sessions.update({t: s for t, s in load_json(SESSIONS_FILE).items() if s["expires"] > now})


def new_session(username):
    token = secrets.token_urlsafe(32)
    with sessions_lock:
        sessions[token] = {"user": username, "expires": time.time() + SESSION_DAYS * 86400}
        save_json(SESSIONS_FILE, sessions)
    return token


def end_session(token):
    with sessions_lock:
        if sessions.pop(token, None):
            save_json(SESSIONS_FILE, sessions)


def drop_sessions(username):
    with sessions_lock:
        for t in [t for t, s in sessions.items() if s["user"] == username]:
            del sessions[t]
        save_json(SESSIONS_FILE, sessions)


def session_user(token):
    s = sessions.get(token or "")
    if not s or s["expires"] < time.time():
        return None
    u = load_json(USERS_FILE).get(s["user"])
    return public_user(s["user"], u) if u else None


# ---------------------------------------------------------------- pages

# How a page appears on the master dashboard. scope is the tab: "general" shows it on the
# General tab, "all" only on All dashboards. reviewed marks pages the admin has looked at.
DEFAULT_HUB = {"show": False, "scope": "general", "reviewed": False, "category": "",
               "branch": "", "tags": [], "title": "", "legacy_id": ""}
PLACEMENTS = ("off", "general", "all")


def hub_of(r):
    return {**DEFAULT_HUB, **r.get("hub", {})}


def placement_of(hub):
    return hub["scope"] if hub["show"] else "off"


def placement_to_hub(value):
    if value not in PLACEMENTS:
        raise UserError("Unknown master dashboard option.")
    return {"show": value != "off", "scope": "general" if value == "off" else value}


def is_migration_target(slug, record):
    """Existing external dashboards to display under Dynamic projects without redeploying them."""
    title = str(record.get("title", "")).strip().lower()
    key = str(slug).strip().lower()
    return (
        "jda_jds_mumbai_pincod" in title or "jda_jds_mumbai_pincod" in key
        or "jda_jds_kolkata_pincod" in title or "jda_jds_kolkata_pincod" in key
        or "pan india jda dashboard" in title or "pan_india_jda_dashboard" in key
        or "panindia jda dashboard" in title or "panindia_jda_dashboard" in key
        or "employee headcount" in title
        or "employee_headcount" in key or "employee-headcount" in key
        or ("headcount" in title and "employee" in title)
    )


def public_record(slug, r, users):
    return {
        "slug": slug,
        "linked": bool(r.get("link")),
        "disabled": bool(r.get("disabled")),
        "title": r["title"],
        "user": r.get("user", ""),
        "owners": owners_of(r),
        "owner": ", ".join(display_name(users, u) for u in owners_of(r)) or r.get("owner", ""),
        "version": r["version"],
        "created": r["created"],
        "updated": r["updated"],
        "url": r.get("link") or f"/s/{slug}/",
        "placement": placement_of(hub_of(r)),
    }


def can_manage(user, record):
    return bool(user) and (user["role"] == "admin" or user["username"] in owners_of(record))


def get_managed(meta, slug, user):
    record = meta.get(slug)
    if not record or record.get("deleted"):
        raise UserError("No such page.", 404)
    if record.get("link") and user["role"] != "admin":
        raise UserError("This dashboard runs on its own server; HTML Drop only links to it.", 403)
    if not can_manage(user, record):
        raise UserError("Only the page's owner or an admin can change it.", 403)
    return record


def set_hub(slug, data):
    with lock:
        meta = load_meta()
        record = meta.get(slug)
        if not record:
            raise UserError("No such page.", 404)
        hub = hub_of(record)
        if "placement" in data:
            hub.update(placement_to_hub(data["placement"]))
        hub.update(
            reviewed=True,
            category=str(data.get("category", hub["category"]))[:40],
            branch=str(data.get("branch", hub["branch"])).strip()[:40],
            title=str(data.get("title", hub["title"])).strip()[:120],
            tags=[t.strip().lower()[:30] for t in data.get("tags", hub["tags"]) if str(t).strip()][:20],
        )
        record["hub"] = hub
        save_meta(meta)
        return hub


def move_with_retry(src, dst):
    # Windows refuses to rename a folder while a file inside is being read.
    for attempt in range(20):
        try:
            shutil.move(str(src), str(dst))
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.25)


def extract_zip(data, dest):
    """Extract into dest, strip a single wrapping folder, return entry html."""
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist()
                 if not n.endswith("/") and not n.startswith("__MACOSX/")]
        if not names:
            raise UserError("The zip file is empty.")
        parts = [n.split("/") for n in names]
        prefix = ""
        if all(len(p) > 1 for p in parts) and len({p[0] for p in parts}) == 1:
            prefix = parts[0][0] + "/"
        for n in names:
            target = (dest / n[len(prefix):]).resolve()
            if not target.is_relative_to(dest_resolved):
                raise UserError("The zip contains unsafe paths.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    if (dest / "index.html").is_file():
        return "index.html"
    htmls = sorted(p.name for p in dest.iterdir()
                   if p.is_file() and p.suffix.lower() in (".html", ".htm"))
    if not htmls:
        raise UserError("No .html file found at the top level of the zip.")
    return htmls[0]


def prune_history(slug):
    folder = HISTORY / slug
    if not folder.exists():
        return
    versions = sorted(p for p in folder.iterdir() if p.is_dir())
    for old in versions[: -int(CONFIG.get("keep_versions", 10)) or None]:
        shutil.rmtree(old, ignore_errors=True)


def publish(slug, title, user, filename, data, hub_choice=None):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise UserError("Only .html, .htm or .zip files are accepted.")
    with lock:
        meta = load_meta()
        users = load_json(USERS_FILE)
        existing = meta.get(slug)
        if existing and existing.get("link"):
            raise UserError(f"'{slug}' is an existing dashboard on its own server. "
                            "Choose a different link name.", 403)
        if existing and not can_manage(user, existing):
            owner = display_name(users, existing.get("user")) or "someone else"
            raise UserError(f"The link name '{slug}' is already used by {owner}. "
                            "Choose a different name.", 403)

        TMP.mkdir(parents=True, exist_ok=True)
        staging = TMP / f"{slug}-{secrets.token_hex(4)}"
        staging.mkdir()
        try:
            if ext == ".zip":
                entry = extract_zip(data, staging)
            else:
                (staging / "index.html").write_bytes(data)
                entry = "index.html"

            now = datetime.now()
            live = SITES / slug
            if live.exists():
                hist = HISTORY / slug / f"{now:%Y%m%d-%H%M%S}_v{existing['version']}"
                hist.parent.mkdir(parents=True, exist_ok=True)
                move_with_retry(live, hist)
            SITES.mkdir(parents=True, exist_ok=True)
            move_with_retry(staging, live)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        prune_history(slug)

        stamp = now.isoformat(timespec="seconds")
        if existing:
            record = existing
            record.update(version=existing["version"] + 1, updated=stamp, entry=entry,
                          title=title or existing["title"])
        else:
            record = {"title": title or slug, "user": user["username"], "version": 1,
                      "created": stamp, "updated": stamp, "entry": entry}
        if hub_choice is not None:
            # Chosen on the upload form; the admin page can still override it.
            # "reviewed" is left alone so the admin still sees new uploads flagged.
            record["hub"] = {**hub_of(record), **hub_choice}
        meta[slug] = record
        save_meta(meta)
        return public_record(slug, record, users)


# Folders never searched when looking for an existing dashboard's file.
SKIP_DIRS = {"windows", "program files", "program files (x86)", "programdata", "$recycle.bin",
             "system volume information", "appdata", "node_modules", ".git", "__pycache__"}


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_dashboard_file(link):
    """The file on this PC that an existing dashboard's link serves: same name, and exactly
    the content the link returns right now (so a stale copy elsewhere can't be picked)."""
    name = unquote(urlparse(link).path).rsplit("/", 1)[-1].lower()
    try:
        with urllib.request.urlopen(link, timeout=60) as resp:
            served = hashlib.sha256(resp.read()).hexdigest()
    except Exception:
        raise UserError("Its server isn't answering, so it can't be replaced right now. "
                        "Start that dashboard's server and try again.", 409)
    own = str(DATA.resolve()).lower()
    roots = [os.path.expanduser("~")] + [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    seen, matches = set(), set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            low = dirpath.lower()
            if low in seen or low.startswith(own):
                dirnames[:] = []
                continue
            seen.add(low)
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            for f in filenames:
                if f.lower() == name:
                    p = os.path.join(dirpath, f)
                    try:
                        if file_sha(p) == served:
                            matches.add(os.path.realpath(p))
                    except OSError:
                        pass
        if len(matches) == 1:
            break  # found in the user's folders; no need to search whole drives
    if len(matches) != 1:
        raise UserError("Couldn't find this dashboard's file on the PC" if not matches else
                        "Found several identical copies of this dashboard's file", 409)
    return matches.pop()


def replace_page(slug, user, filename, data):
    """The Replace button: new file, same link. An existing dashboard's file is overwritten in
    its own folder under its own name (backed up first); an HTML Drop page gets a new version."""
    with lock:
        meta = load_meta()
        record = meta.get(slug)
        if not record or record.get("deleted"):
            raise UserError("No such page.", 404)
        if not record.get("link"):
            pass  # handled by publish() below, outside this block
        else:
            if not can_manage(user, record):
                raise UserError("Only the page's owners or an admin can replace it.", 403)
            if Path(filename).suffix.lower() not in (".html", ".htm"):
                raise UserError("Choose the dashboard's .html file.")
            target = Path(record.get("file") or "")
            if record.get("disabled"):
                target = parked_path(slug, record)  # stays hidden until Enable
            elif not record.get("file") or not target.is_file():
                target = Path(find_dashboard_file(record["link"]))
                record["file"] = str(target)
            now = datetime.now()
            backup = HISTORY / slug / f"{now:%Y%m%d-%H%M%S}_v{record['version']}"
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup / target.name)
            tmp = target.with_name(target.name + ".htmldrop-new")
            tmp.write_bytes(data)
            for attempt in range(20):
                try:
                    os.replace(tmp, target)  # same folder, same name: the old server serves it at once
                    break
                except PermissionError:
                    if attempt == 19:
                        tmp.unlink(missing_ok=True)
                        raise UserError("The dashboard file is in use right now. Try again in a moment.", 409)
                    time.sleep(0.25)
            prune_history(slug)
            record.update(version=record["version"] + 1, updated=now.isoformat(timespec="seconds"))
            save_meta(meta)
            return public_record(slug, record, load_json(USERS_FILE))
    return publish(slug, "", user, filename, data)  # keeps its title and dashboard settings


UNAVAILABLE_PAGE = """<!doctype html>
<!-- HTML Drop: this dashboard is temporarily disabled. The real file is kept safe; "Enable" puts it back. -->
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Temporarily unavailable</title></head>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#f4efe6;color:#1f1c17;font-family:Georgia,serif">
<div style="text-align:center;padding:32px"><h1 style="font-weight:500;font-size:34px;margin:0 0 10px">Temporarily unavailable</h1>
<p style="font-family:Segoe UI,sans-serif;color:#5a5347;margin:0">This dashboard is switched off for now. Please check back later.</p></div>
</body></html>
"""


def parked_path(slug, record):
    return PARKED / slug / Path(record["file"]).name


def write_in_place(target, data):
    """Swap a file's content in its own folder, under its own name (what its server serves)."""
    tmp = target.with_name(target.name + ".htmldrop-new")
    tmp.write_bytes(data)
    for attempt in range(20):
        try:
            os.replace(tmp, target)
            return
        except PermissionError:
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise UserError("The dashboard file is in use right now. Try again in a moment.", 409)
            time.sleep(0.25)


def set_disabled(slug, user, disabled):
    """Disable: the link shows "temporarily unavailable" and the page leaves the master dashboard;
    nothing is deleted. Enable: back exactly as it was (or with the file Replaced meanwhile)."""
    record = load_meta().get(slug)
    if not record or record.get("deleted"):
        raise UserError("No such page.", 404)
    if not can_manage(user, record):
        raise UserError("Only the page's owners or an admin can do that.", 403)
    # Finding an existing dashboard's file can take a while; do it before taking the lock.
    found = None
    if disabled and record.get("link") and not record.get("disabled"):
        f = Path(record.get("file") or "")
        found = f if record.get("file") and f.is_file() else Path(find_dashboard_file(record["link"]))
    with lock:
        meta = load_meta()
        record = meta.get(slug)
        if not record:
            raise UserError("No such page.", 404)
        if bool(record.get("disabled")) == disabled:
            return public_record(slug, record, load_json(USERS_FILE))
        if record.get("link"):
            if disabled:
                record["file"] = str(found)
                park = parked_path(slug, record)
                park.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(found, park)                       # the real file, kept safe
                write_in_place(found, UNAVAILABLE_PAGE.encode("utf-8"))
            else:
                park = parked_path(slug, record)
                if not park.is_file():
                    raise UserError("The dashboard's saved file is missing, so it can't be enabled. "
                                    "Use Replace to put a file back.", 409)
                write_in_place(Path(record["file"]), park.read_bytes())
                park.unlink()
        record["disabled"] = disabled
        record["updated"] = datetime.now().isoformat(timespec="seconds")
        save_meta(meta)
        return public_record(slug, record, load_json(USERS_FILE))


def update_page(slug, user, data):
    """Change a page's title or master dashboard placement without a new file."""
    with lock:
        meta = load_meta()
        record = get_managed(meta, slug, user)
        title = str(data.get("title", "")).strip()[:120]
        if title:
            record["title"] = title
        if "placement" in data:
            record["hub"] = {**hub_of(record), **placement_to_hub(data["placement"])}
        save_meta(meta)
        return public_record(slug, record, load_json(USERS_FILE))


def rename_page(slug, user, title):
    """Change only the display name shown in My pages. The link (link name / address) never
    changes. Works for every page, including dashboards that run on their own server."""
    title = " ".join(str(title).split())[:120]
    if not title:
        raise UserError("Type a name first.")
    with lock:
        meta = load_meta()
        record = meta.get(slug)
        if not record or record.get("deleted"):
            raise UserError("No such page.", 404)
        if not can_manage(user, record):
            raise UserError("Only the page's owners or an admin can rename it.", 403)
        record["title"] = title
        if record.get("link"):
            record["renamed"] = True  # so the start-up sync doesn't set the file name back
        elif hub_of(record)["title"]:
            record["hub"] = {**hub_of(record), "title": title}  # master dashboard shows the new name too
        save_meta(meta)
        return public_record(slug, record, load_json(USERS_FILE))


def delete_linked(slug, user):
    """Delete an existing dashboard: its file comes off its own server (so the link stops working),
    a copy goes to data/trash, and a "deleted" marker stays so the master dashboard hides it and
    it is not added back at the next start."""
    record = load_meta().get(slug)
    if not can_manage(user, record):
        raise UserError("Only the page's owners or an admin can delete it.", 403)
    found = None
    if not record.get("disabled"):  # finding the file can take a while; do it before the lock
        f = Path(record.get("file") or "")
        found = f if record.get("file") and f.is_file() else Path(find_dashboard_file(record["link"]))
    with lock:
        meta = load_meta()
        record = meta[slug]
        target = found or Path(record["file"])
        real = parked_path(slug, record) if record.get("disabled") else target
        now = datetime.now()
        bin_dir = TRASH / f"{slug}-{now:%Y%m%d-%H%M%S}"
        bin_dir.mkdir(parents=True, exist_ok=True)
        if real.is_file():
            shutil.copy2(real, bin_dir / target.name)  # kept, in case it's needed back
        for attempt in range(20):
            try:
                if target.exists():
                    target.unlink()  # off its server: the link now says "not found"
                break
            except PermissionError:
                if attempt == 19:
                    raise UserError("The dashboard file is in use right now. Try again in a moment.", 409)
                time.sleep(0.25)
        if record.get("disabled") and real.is_file():
            real.unlink()
        meta[slug] = {"deleted": True, "link": record["link"], "title": record["title"],
                      "user": record.get("user", ""), "editors": record.get("editors", []),
                      "file": str(target), "trash": str(bin_dir),
                      "deleted_at": now.isoformat(timespec="seconds"), "deleted_by": user["username"]}
        save_meta(meta)


def delete(slug, user):
    record = load_meta().get(slug)
    if record and record.get("link") and not record.get("deleted"):
        return delete_linked(slug, user)
    with lock:
        meta = load_meta()
        if meta.get(slug, {}).get("deleted"):
            raise UserError("No such page.", 404)
        record = get_managed(meta, slug, user)
        live = SITES / slug
        if record.get("link"):
            live = TMP / "nothing-to-move"  # a link has no files
        if live.exists():
            TRASH.mkdir(parents=True, exist_ok=True)
            move_with_retry(live, TRASH / f"{slug}-{datetime.now():%Y%m%d-%H%M%S}")
        del meta[slug]
        save_meta(meta)


# ---------------------------------------------------------------- existing dashboards
# Dashboards that already run on their own servers. They KEEP THEIR ORIGINAL LINKS; HTML Drop
# only lists each one in its owners' My pages (where Replace / Disable / Delete work on its file).
# To add one or change an owner, edit this list and restart HTML Drop (double-click restart.bat).
#   (name, port, file, owners (first is the main one), title (None = the file name))
EXISTING_HOST = "172.29.65.188"
EXISTING_DASHBOARDS = [
    ("mumbai-pincode",          8080, "JDA_JDS_Mumbai_Pincode_Dashboard.html",     ["Sarvesh"],          None),
    ("kolkata-pincode",         8085, "JDA_JDS_Kolkata_Pincode_Dashboard.html",    ["Sarvesh"],          None),
    ("headcount-tenure",        8090, "Employee_Headcount_Tenure_Dashboard.html",  ["Muskan"],           None),
    ("supercat-funnel",         8000, "Supercat-funnel-Aug26.html",                ["Muskan"],           None),
    ("renewal-funnel-fy27",     8095, "Renewal_funnel_Apr_Aug_fy27.html",          ["Muskan"],           None),
    ("rv-vintage-tracker",      8070, "RV_Vintage_Tracker.html",                   ["Sounak"],           None),
    ("chennai-rv-drop",         8050, "Chennai_RV_drop_analysis_Aug26.html",       ["Sounak"],           None),
    ("ecs-billed-cleared",      8045, "ECS_billed_vs_cleared_Mar22_to_Aug26.html", ["Sounak"],           None),
    ("deal-retouch-timing",     8055, "Deal_Retouch_Timing.html",                  ["Sounak"],           None),
    ("cos-vs-revenue",          8060, "Cost_vs_Sale.html",                         ["Sounak", "Ganesh"], None),
    ("appointment-funnel",      8010, "appointment_funnel_dashboard.html",         ["Ayush"],            "Appointment_funnel"),
    ("Pan_india_JDA",          8020, "Pan_India_JDA_Dashboard.html",              ["Sarvesh"],           None),
    ("callable-representation", 8025, "Justdial_callable_representation.html",     ["Priyal"],           None),
]


def sync_existing_dashboards():
    """Runs at every start: makes sure each dashboard above is in its owners' My pages, with
    its original link. Keeps what owners did meanwhile (versions, Disable); skips ones they
    deleted. Copies made by an old import tool are moved to data/trash."""
    stamp = datetime.now().isoformat(timespec="seconds")
    listed = 0
    with lock:
        meta = load_meta()
        for slug, port, filename, owners, title in EXISTING_DASHBOARDS:
            old = meta.get(slug)
            if old and old.get("deleted"):
                continue
            if old and not old.get("link"):
                copy = SITES / slug
                if copy.exists():
                    TRASH.mkdir(parents=True, exist_ok=True)
                    move_with_retry(copy, TRASH / f"{slug}-copy-{datetime.now():%Y%m%d-%H%M%S}")
            kept = old if old and old.get("link") else {}
            keys = [user_key(o) for o in owners]
            meta[slug] = {
                "title": kept["title"] if kept.get("renamed") else (title or filename.rsplit(".", 1)[0]),
                "renamed": bool(kept.get("renamed")),
                "user": keys[0], "editors": keys[1:],
                "link": f"http://{EXISTING_HOST}:{port}/{filename}",
                "file": kept.get("file", ""),
                "version": kept.get("version", 1),
                "created": kept.get("created", stamp),
                "updated": kept.get("updated", stamp),
                "entry": "",
                "disabled": kept.get("disabled", False),
                "hub": {**DEFAULT_HUB, "reviewed": True},
            }
            listed += 1
        save_meta(meta)
    print(f"Existing dashboards: {listed} listed in their owners' My pages, on their original links.")


# ---------------------------------------------------------------- http

# ---------------------------------------------------------------- dynamic projects

def load_dynamic_meta():
    return load_json(DYNAMIC_META_FILE)


def save_dynamic_meta(meta):
    save_json(DYNAMIC_META_FILE, meta)


def dynamic_public(rec, include_path=False):
    out = {k: rec.get(k) for k in ("slug", "title", "owner", "created", "updated", "port", "status", "entry", "url", "show_on_master", "master_scope", "category", "message", "refresh")}
    out["disabled"] = bool(rec.get("disabled"))
    out["running"] = dynamic_running(rec)
    project_dir = DYNAMIC_ROOT / rec.get("slug", "")
    out["refresh_available"] = (project_dir / "refresh_dashboard.py").is_file()
    out["launch_type"] = rec.get("launch_type") or detect_dynamic_entry(project_dir)[1]
    if out["running"]:
        out["status"] = "running"
    elif rec.get("status") == "running":
        out["status"] = "stopped"
    if include_path:
        out["project_path"] = str(DYNAMIC_ROOT / rec.get("slug", ""))
    return out


def dynamic_running(rec):
    slug = rec.get("slug", "")
    proc = DYNAMIC_PROCESSES.get(slug)
    if proc is not None:
        return proc.poll() is None
    pid = rec.get("pid")
    if pid:
        # Recover visibility after the portal restarts. Do not claim a process is
        # healthy just because a PID exists; Windows may have reused it.
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if h:
                ctypes.windll.kernel32.CloseHandle(h)
                return rec.get("status") == "running"
        except Exception:
            pass
    return False


def dynamic_owner_allowed(user, rec):
    return bool(user and (user.get("role") == "admin" or user.get("username") == rec.get("owner")))


def detect_dynamic_entry(project: Path):
    """Detect launch method separately from refresh capability."""
    for name in ("app.py", "main.py", "run.py", "server.py"):
        candidate = project / name
        if candidate.is_file():
            return name, "python", None
    ignored = {".venv", ".git", "node_modules"}
    indexes = [p for p in project.rglob("index.html") if p.is_file() and not ignored.intersection(p.parts)]
    if len(indexes) == 1:
        return str(indexes[0].relative_to(project)), "static", indexes[0].parent
    if len(indexes) > 1:
        root_indexes = [p for p in indexes if p.parent == project]
        if len(root_indexes) == 1:
            return "index.html", "static", project
        return None, None, None
    html_files = [p for p in project.rglob("*") if p.is_file() and p.suffix.lower() in (".html", ".htm") and not ignored.intersection(p.parts)]
    if len(html_files) == 1:
        return str(html_files[0].relative_to(project)), "static", html_files[0].parent
    return None, None, None


def safe_extract_dynamic(zip_bytes, slug):
    """Extract a project ZIP without allowing traversal, links, or archive bombs."""
    DYNAMIC_ROOT.mkdir(parents=True, exist_ok=True)
    target = DYNAMIC_ROOT / slug
    staging = DYNAMIC_ROOT / ("." + slug + ".uploading-" + secrets.token_hex(4))
    total_size = 0
    max_files = 5000
    max_uncompressed = 1024 * 1024 * 1024
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if not infos:
                raise UserError("The ZIP contains no files.")
            if len(infos) > max_files:
                raise UserError(f"The project has too many files (limit {max_files}).")
            clean = []
            for info in infos:
                name = info.filename.replace("\\", "/")
                parts = [p for p in name.split("/") if p not in ("", ".")]
                if not parts or any(p == ".." for p in parts) or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                    raise UserError("The ZIP contains an unsafe file path.")
                # Unix symlinks inside ZIPs are not accepted.
                if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    raise UserError("Symbolic links are not allowed in project ZIPs.")
                total_size += info.file_size
                if total_size > max_uncompressed:
                    raise UserError("The extracted project exceeds the 1 GB limit.", 413)
                clean.append((info, parts))
            # Remove a common enclosing folder when the ZIP contains one.
            first_parts = [p for _, p in clean]
            roots = {p[0] for p in first_parts}
            strip_root = len(roots) == 1 and all(len(p) > 1 for p in first_parts)
            staging.mkdir(parents=True, exist_ok=False)
            for info, parts in clean:
                rel_parts = parts[1:] if strip_root else parts
                if not rel_parts:
                    continue
                dest = staging.joinpath(*rel_parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Copy through ZipExtFile, not ZipFile.extract, after path validation.
                with zf.open(info, "r") as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        entry, launch_type, _web_root = detect_dynamic_entry(staging)
        if not entry:
            raise UserError("Could not identify a launch entry. Include index.html (or one unambiguous HTML page), or a supported Python entry point: app.py, main.py, run.py, or server.py.")
        if target.exists():
            raise UserError("A project with that link name already exists. Choose another name.", 409)
        staging.rename(target)
        return target
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def dynamic_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def allocate_dynamic_port(meta):
    used = {int(r.get("port", 0)) for r in meta.values()}
    for port in range(DYNAMIC_PORT_START, DYNAMIC_PORT_END + 1):
        if port not in used and not dynamic_port_in_use(port):
            return port
    raise UserError("No free dynamic dashboard ports are available (8160–8999).", 503)


def stop_dynamic_process(slug, rec):
    proc = DYNAMIC_PROCESSES.get(slug)
    pid = proc.pid if proc is not None else rec.get("pid")
    if pid and os.name == "nt":
        # Stop the recorded process tree so child workers are not left behind.
        try:
            subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8, check=False)
        except Exception:
            pass
    elif proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    DYNAMIC_PROCESSES.pop(slug, None)
    rec["pid"] = None
    rec["status"] = "stopped"
    rec["message"] = "Stopped by administrator."
    rec["updated"] = datetime.now().isoformat(timespec="seconds")


def start_dynamic_worker(slug):
    """Analyze project and launch a supported Python app or serve static HTML."""
    meta = load_dynamic_meta()
    rec = meta.get(slug)
    if not rec:
        return
    project = DYNAMIC_ROOT / slug
    log_dir = DYNAMIC_LOG_ROOT / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "runtime.log"
    rec["status"] = "preparing"
    rec["message"] = "Analyzing project and preparing launch."
    rec["updated"] = datetime.now().isoformat(timespec="seconds")
    save_dynamic_meta(meta)
    log_handle = None
    try:
        entry, launch_type, web_root = detect_dynamic_entry(project)
        if not entry:
            raise RuntimeError("No supported launch entry found. Add index.html or a supported Python entry point.")
        py = Path(sys.executable)
        if launch_type == "python":
            env_dir = project / ".venv"
            if not (env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")).exists():
                venv.EnvBuilder(with_pip=True, clear=False).create(str(env_dir))
            py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            requirements = project / "requirements.txt"
            if requirements.is_file() and requirements.read_text(encoding="utf-8", errors="replace").strip():
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"\\n[{datetime.now().isoformat(timespec='seconds')}] Installing requirements.txt\\n")
                    log.flush()
                    result = subprocess.run([str(py), "-m", "pip", "install", "-r", str(requirements)], cwd=str(project), stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
                if result.returncode != 0:
                    raise RuntimeError("Dependency installation failed. Check project logs.")
        meta = load_dynamic_meta()
        rec = meta.get(slug)
        if not rec:
            return
        port = int(rec["port"])
        env = os.environ.copy()
        env.update({"PORT": str(port), "HOST": "0.0.0.0", "DASHBOARD_PORT": str(port), "DASHBOARD_HOST": "0.0.0.0", "PYTHONUNBUFFERED": "1"})
        log_handle = log_path.open("a", encoding="utf-8")
        if launch_type == "static":
            launch_cwd = Path(web_root or project)
            command = [str(py), "-u", "-m", "http.server", str(port), "--bind", "0.0.0.0", "--directory", str(launch_cwd)]
            log_handle.write(f"\\n[{datetime.now().isoformat(timespec='seconds')}] Serving static HTML from {launch_cwd} on 0.0.0.0:{port}\\n")
        else:
            launch_cwd = project
            command = [str(py), "-u", str(project / entry)]
            log_handle.write(f"\\n[{datetime.now().isoformat(timespec='seconds')}] Starting Python entry {entry} on 0.0.0.0:{port}\\n")
        log_handle.flush()
        proc = subprocess.Popen(command, cwd=str(launch_cwd), env=env, stdout=log_handle, stderr=subprocess.STDOUT, creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0))
        DYNAMIC_PROCESSES[slug] = proc
        meta = load_dynamic_meta()
        rec = meta.get(slug)
        if rec:
            rec["pid"] = proc.pid
            rec["status"] = "running"
            rec["entry"] = entry
            rec["launch_type"] = launch_type
            rec["message"] = "Static HTML is being served." if launch_type == "static" else f"Started {entry}. Confirm it uses PORT and binds to 0.0.0.0 if the page does not open."
            rec["updated"] = datetime.now().isoformat(timespec="seconds")
            save_dynamic_meta(meta)
        log_handle.close()
    except Exception as exc:
        if log_handle and not log_handle.closed:
            log_handle.close()
        meta = load_dynamic_meta()
        rec = meta.get(slug)
        if rec:
            rec["status"] = "error"
            rec["message"] = str(exc)[:500]
            rec["updated"] = datetime.now().isoformat(timespec="seconds")
            save_dynamic_meta(meta)


# ---------------------------------------------------------------- scheduled data refresh

def refresh_task_name(slug):
    return "HTMLDrop_Refresh_" + slug


def build_refresh_task_xml(slug, rec, settings):
    """Build a Task Scheduler XML task. Schedule times use this PC's local clock."""
    import xml.etree.ElementTree as ET
    project = (DYNAMIC_ROOT / slug).resolve()
    script = project / "refresh_dashboard.py"
    if not script.is_file():
        raise UserError("This project has no refresh_dashboard.py at its root. Add it with Change ZIP first.")
    py = project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.is_file():
        py = Path(sys.executable)
    start_time = str(settings.get("time", "06:00"))
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", start_time):
        raise UserError("Time must be valid 24-hour HH:MM, for example 06:01 or 19:19.")
    import datetime as _dt
    now = _dt.datetime.now()
    hh, mm = map(int, start_time.split(":"))
    start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if start <= now:
        start += _dt.timedelta(days=1)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%S")
    NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", NS)
    def el(parent, name, text=None, attrs=None):
        node=ET.SubElement(parent, "{"+NS+"}"+name, attrs or {})
        if text is not None: node.text=str(text)
        return node
    task=ET.Element("{"+NS+"}Task", {"version":"1.4"})
    reg=el(task,"RegistrationInfo"); el(reg,"Description",f"HTML Drop automatic data refresh for {slug}")
    triggers=el(task,"Triggers")
    freq=settings.get("frequency","daily")
    if freq=="hourly":
        trigger=el(triggers,"CalendarTrigger"); el(trigger,"StartBoundary",start_iso); el(trigger,"Enabled","true")
        rep=el(trigger,"Repetition"); el(rep,"Interval",f"PT{int(settings.get('hours',1))}H"); el(rep,"StopAtDurationEnd","false")
        daily=el(trigger,"ScheduleByDay"); el(daily,"DaysInterval","1")
    elif freq=="weekly":
        trigger=el(triggers,"CalendarTrigger"); el(trigger,"StartBoundary",start_iso); el(trigger,"Enabled","true")
        by=el(trigger,"ScheduleByWeek"); el(by,"WeeksInterval","1"); days=el(by,"DaysOfWeek")
        daymap={"Mon":"Monday","Tue":"Tuesday","Wed":"Wednesday","Thu":"Thursday","Fri":"Friday","Sat":"Saturday","Sun":"Sunday"}
        selected=settings.get("days",["Mon","Tue","Wed","Thu","Fri"])
        if not selected: raise UserError("Select at least one day for weekly refresh.")
        for d in selected:
            if d in daymap: el(days,daymap[d])
    else:
        trigger=el(triggers,"CalendarTrigger"); el(trigger,"StartBoundary",start_iso); el(trigger,"Enabled","true")
        by=el(trigger,"ScheduleByDay"); el(by,"DaysInterval",str(max(1,min(365,int(settings.get("days_interval",1))))))
    principals=el(task,"Principals"); principal=el(principals,"Principal",attrs={"id":"Author"})
    el(principal,"LogonType","InteractiveToken"); el(principal,"RunLevel","LeastPrivilege")
    settings_node=el(task,"Settings")
    el(settings_node,"MultipleInstancesPolicy","IgnoreNew")
    el(settings_node,"StartWhenAvailable","true")
    el(settings_node,"WakeToRun","true")
    el(settings_node,"Enabled","true")
    el(settings_node,"ExecutionTimeLimit","PT2H")
    el(settings_node,"DisallowStartIfOnBatteries","false")
    el(settings_node,"StopIfGoingOnBatteries","false")
    actions=el(task,"Actions",attrs={"Context":"Author"}); action=el(actions,"Exec")
    el(action,"Command",str(py)); el(action,"Arguments",f'"{script}"'); el(action,"WorkingDirectory",str(project))
    return ET.tostring(task, encoding="unicode", xml_declaration=True)


def register_refresh_task(slug, rec, settings):
    if os.name != "nt":
        raise UserError("Windows Task Scheduler is only available on Windows. Schedule settings were not registered on this computer.", 501)
    xml_text=build_refresh_task_xml(slug,rec,settings)
    task_file=TMP / ("refresh-"+slug+"-"+secrets.token_hex(4)+".xml")
    task_file.parent.mkdir(parents=True,exist_ok=True)
    task_file.write_text(xml_text,encoding="utf-16")
    try:
        result=subprocess.run(["schtasks.exe","/Create","/TN",refresh_task_name(slug),"/XML",str(task_file),"/F"],
                              capture_output=True,text=True,timeout=30,check=False)
        if result.returncode:
            raise UserError("Windows could not register the refresh task. Check Task Scheduler permissions. "+(result.stderr or result.stdout or "" )[:350], 500)
    finally:
        task_file.unlink(missing_ok=True)
    rec["refresh"]={**settings,"enabled":True,"task_name":refresh_task_name(slug),"updated":datetime.now().isoformat(timespec="seconds"),"last_status":"scheduled"}
    return rec["refresh"]


def delete_refresh_task(slug):
    if os.name=="nt":
        subprocess.run(["schtasks.exe","/Delete","/TN",refresh_task_name(slug),"/F"],capture_output=True,text=True,timeout=15,check=False)


class Handler(BaseHTTPRequestHandler):
    server_version = "HTMLDrop/2.0"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] "
                         f"{self.client_address[0]} {fmt % args}\n")

    def send_body(self, body, ctype, status=200, cors=False, headers=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, status=200, cors=False, headers=()):
        self.send_body(json.dumps(obj).encode(), "application/json", status, cors, headers)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # --- auth helpers
    def token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return ""
        return cookie[COOKIE].value if COOKIE in cookie else ""

    def current_user(self):
        return session_user(self.token())

    def require_user(self):
        user = self.current_user()
        if not user:
            raise UserError("Please log in first.", 401)
        return user

    def require_admin(self):
        user = self.require_user()
        if user["role"] != "admin":
            raise UserError("Only admins can do that.", 403)
        return user

    def acting_user(self):
        """Who is publishing: the form's User + PIN headers, else the session.
        Returns (user, Set-Cookie header or None when no new session was made)."""
        form_user = unquote(self.headers.get("X-User", "")).strip()
        if not form_user:
            if not self.current_user():
                raise UserError("Enter your user and PIN.", 401)
            return self.current_user(), None
        me = self.current_user()
        if me and me["username"] == user_key(form_user):
            return me, None
        username = auth_or_create(form_user, unquote(self.headers.get("X-Pin", "")))
        return self.user_of(username), self.session_cookie(new_session(username), SESSION_DAYS * 86400)

    def check_not_taken(self, slug):
        # Refuse someone else's link name before a new user gets created for nothing.
        existing = load_meta().get(slug)
        if existing and existing.get("link"):
            raise UserError(f"'{slug}' is an existing dashboard on its own server. "
                            "Choose a different link name.", 403)
        form_user = user_key(unquote(self.headers.get("X-User", "")))
        if not existing or not form_user or form_user == existing.get("user"):
            return
        users = load_json(USERS_FILE)
        if users.get(form_user, {}).get("role") == "admin":
            return
        owner = display_name(users, existing.get("user")) or "someone else"
        raise UserError(f"The link name '{slug}' is already used by {owner}. "
                        "Choose a different name.", 403)

    def session_cookie(self, token, max_age):
        return ("Set-Cookie", f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}")

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 65536:
            raise UserError("Request too large.", 413)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            raise UserError("Bad request.")

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        limit = int(CONFIG.get("max_upload_mb", 200)) * 1024 * 1024
        if length <= 0:
            raise UserError("The file is empty.")
        if length > limit:
            raise UserError(f"File is larger than {CONFIG.get('max_upload_mb')} MB.", 413)
        return self.rfile.read(length)

    # --- routes
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            if path in ("/", "/index.html"):
                page = PORTAL_FILE.read_text(encoding="utf-8")
                page = page.replace('<button class="btn" onclick="replace(\'${esc(s.slug)}\')">Replace</button>', '${s.dynamic ? `<input type="file" accept=".html,.htm,text/html" hidden id="replace-html-${esc(s.slug)}" onchange="replaceDynamicHtml(\'${esc(s.slug)}\',this)"><button class="btn" onclick="document.getElementById(\'replace-html-${esc(s.slug)}\').click()">Replace HTML</button>` : `<button class="btn" onclick="replace(\'${esc(s.slug)}\')">Replace</button>`}')
                marker = "async function del(slug) {"
                if marker in page and "async function replaceDynamicHtml(slug,input)" not in page:
                    page = page.replace(marker, 'async function replaceDynamicHtml(slug,input){const file=input.files&&input.files[0];if(!file)return;if(!confirm("Replace only the HTML file for "+slug+"? Other project files and the dashboard link will be kept. A backup will be saved and the dashboard restarted.")){input.value="";return}listMsg("Replacing HTML for "+slug+"…");try{const r=await fetch("/api/dynamic/replace-html?"+new URLSearchParams({slug,filename:file.name}),{method:"POST",headers:{"X-HD":"1"},body:file});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||"HTML replacement failed ("+r.status+").");listMsg(d.message||"HTML replaced and restart started.");setTimeout(load,1500);setTimeout(load,5000)}catch(e){listMsg(e.message,true)}finally{input.value=""}}\n\n' + marker, 1)
                return self.send_body(page.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/admin":
                return self.send_body(ADMIN_FILE.read_bytes(), "text/html; charset=utf-8")
            if path == "/dynamic":
                if not DYNAMIC_FILE.is_file():
                    raise UserError("Dynamic Dashboards page file is missing. Restore dynamic.html next to server.py.", 500)
                page = DYNAMIC_FILE.read_text(encoding="utf-8")
                page = page.replace("Uploads are stored for review; only an HTML Drop administrator can start code.", "Uploads are deployed automatically after validation. Only upload Python projects you trust.")
                page = page.replace("Uploaded ${d.title}. An administrator must review and deploy it before it runs.", "Uploaded ${d.title}. Deployment has started automatically.")
                old_actions = """<button class="btn" onclick="showLogs('${esc(p.slug)}','${esc(p.title)}')">View logs</button>${isAdmin?`${p.running?`<button class="btn" onclick="stopProject('${esc(p.slug)}')">Stop</button>`:`<button class="btn primary" onclick="startProject('${esc(p.slug)}')">Deploy / Start</button>`}<button class="btn danger" onclick="deleteProject('${esc(p.slug)}')">Delete</button>`:''}"""
                new_actions = """<button class="btn" onclick="showLogs('${esc(p.slug)}','${esc(p.title)}')">View logs</button><input type="file" accept=".zip,application/zip" hidden id="replace-${esc(p.slug)}" onchange="replaceProjectZip('${esc(p.slug)}',this)"><button class="btn" onclick="document.getElementById('replace-${esc(p.slug)}').click()">Change ZIP</button>${isAdmin?`${p.running?`<button class="btn" onclick="stopProject('${esc(p.slug)}')">Stop</button>`:`<button class="btn primary" onclick="startProject('${esc(p.slug)}')">Deploy / Start</button>`}<button class="btn danger" onclick="deleteProject('${esc(p.slug)}')">Delete</button>`:''}"""
                if old_actions in page:
                    page = page.replace(old_actions, new_actions)
                marker = "async function startProject(slug){"
                replace_fn = """async function replaceProjectZip(slug,input){const file=input.files&&input.files[0];if(!file)return;if(!confirm('Replace the ZIP for '+slug+'? The dashboard will restart with the replacement files.')){input.value='';return}try{const d=await api('/api/dynamic/replace?slug='+encodeURIComponent(slug),{method:'POST',headers:{'Content-Type':'application/zip'},body:file});alert(d.message||'ZIP replaced. Restart started automatically.');await loadProjects();setTimeout(loadProjects,1800);setTimeout(loadProjects,6000)}catch(e){alert('Could not replace ZIP: '+e.message)}finally{input.value=''}}
"""
                if marker in page and 'async function replaceProjectZip' not in page:
                    page = page.replace(marker, replace_fn + marker)
                return self.send_body(page.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/me":
                return self.send_json({"user": self.current_user(),
                                       "allow_signup": bool(CONFIG.get("allow_signup", True)),
                                       "master_url": CONFIG.get("master_dashboard_url", DEFAULT_MASTER_URL),
                                       "members": member_list()})
            if path == "/api/sites":
                users = load_json(USERS_FILE)
                user = self.current_user()
                items = []
                for s, r in load_meta().items():
                    if r.get("deleted"):
                        continue
                    # These three existing external dashboards are presented in Dynamic projects
                    # for Sarvesh/their owners; their actual servers and refresh jobs are untouched.
                    if is_migration_target(s, r) and (
                        user and (user.get("role") == "admin" or user.get("username", "").lower() in
                                  {str(x).lower() for x in owners_of(r)} | {str(r.get("user", "")).lower(), str(r.get("owner", "")).lower()})
                    ):
                        continue
                    items.append(public_record(s, r, users))
                if user:
                    existing_slugs = {str(item.get("slug", "")).lower() for item in items}
                    for slug, rec in load_dynamic_meta().items():
                        if rec.get("deleted") or not dynamic_owner_allowed(user, rec) or slug.lower() in existing_slugs:
                            continue
                        running = dynamic_running(rec)
                        items.append({"slug": slug, "linked": True, "dynamic": True, "disabled": False,
                                      "title": rec.get("title") or slug.replace("-", " ").title(),
                                      "user": rec.get("owner", ""), "owner": rec.get("owner", ""),
                                      "owners": [rec.get("owner", "")], "version": 1,
                                      "created": rec.get("created", ""), "updated": rec.get("updated", ""),
                                      "url": rec.get("url", ""), "placement": "dynamic",
                                      "status": "running" if running else rec.get("status", "stopped")})
                items.sort(key=lambda r: r.get("updated", ""), reverse=True)
                return self.send_json(items)
            if path == "/api/dynamic/projects":
                user = self.require_user()
                meta = load_dynamic_meta()
                items = [dynamic_public(r, include_path=(user.get("role") == "admin"))
                         for r in meta.values() if dynamic_owner_allowed(user, r)]
                # Virtual entries for already-running external dashboards. Do not copy files,
                # relaunch processes, change ports, or touch their existing cron tasks.
                users = load_json(USERS_FILE)
                for slug, rec in load_meta().items():
                    if rec.get("deleted") or not rec.get("link") or not is_migration_target(slug, rec):
                        continue
                    owners = {str(x).lower() for x in owners_of(rec)}
                    owners.update({str(rec.get("user", "")).lower(), str(rec.get("owner", "")).lower()})
                    if user.get("role") != "admin" and user.get("username", "").lower() not in owners:
                        continue
                    url = rec.get("link") or ""
                    port_match = re.search(r":(\\d+)(?:/|$)", urlparse(url).netloc or url)
                    items.append({
                        "slug": slug, "title": rec.get("title") or slug, "owner": ", ".join(
                            display_name(users, x) for x in owners_of(rec)
                        ) or rec.get("owner", ""),
                        "created": rec.get("created", ""), "updated": rec.get("updated", ""),
                        "port": port_match.group(1) if port_match else "",
                        "status": "On its own server", "url": url, "external": True,
                        "refresh": {"enabled": False}, "refresh_available": False,
                        "show_on_master": False, "master_scope": "off"
                    })
                items.sort(key=lambda r: r.get("updated", ""), reverse=True)
                return self.send_json({"projects": items, "is_admin": user.get("role") == "admin"})
            if path == "/api/dynamic/log":
                user = self.require_user()
                slug = parse_qs(urlparse(self.path).query).get("slug", [""])[0]
                rec = load_dynamic_meta().get(slug)
                if not rec or not dynamic_owner_allowed(user, rec):
                    raise UserError("Project not found or access denied.", 404)
                log_path = DYNAMIC_LOG_ROOT / slug / "runtime.log"
                content = log_path.read_text(encoding="utf-8", errors="replace")[-20000:] if log_path.exists() else "No logs yet."
                return self.send_json({"slug": slug, "log": content})
            if path == "/api/titles":
                return self.send_titles()
            if path == "/api/categories":
                return self.send_json(CONFIG.get("hub_categories", DEFAULT_HUB_CATEGORIES))
            if path == "/api/hub":
                return self.send_hub()
            if path == "/api/admin/sites":
                self.require_admin()
                users = load_json(USERS_FILE)
                items = [{**public_record(s, r, users), "hub": hub_of(r), "file": r.get("file", "")}
                         for s, r in load_meta().items() if not r.get("deleted")]
                items.sort(key=lambda r: r["updated"], reverse=True)
                return self.send_json({"sites": items,
                                       "categories": CONFIG.get("hub_categories", DEFAULT_HUB_CATEGORIES)})
            if path == "/api/admin/users":
                self.require_admin()
                meta = load_meta()
                counts = {}
                for r in meta.values():
                    if not r.get("deleted"):
                        counts[r.get("user", "")] = counts.get(r.get("user", ""), 0) + 1
                users = [{**public_user(n, u), "created": u["created"], "pages": counts.get(n, 0)}
                         for n, u in load_json(USERS_FILE).items()]
                users.sort(key=lambda u: (u["role"] != "admin", u["username"]))
                return self.send_json(users)
            m = re.match(r"^/s/([^/]+)(/.*)?$", path)
            if m:
                return self.serve_site(m.group(1), m.group(2))
            self.send_error(404)
        except UserError as e:
            self.send_json({"error": str(e)}, e.status)

    def send_hub(self):
        # Read by Master_Dashboard.html, which may be served from another port.
        base = f"http://{self.headers.get('Host') or 'localhost'}"
        users = load_json(USERS_FILE)
        items = []
        for slug, r in load_meta().items():
            hub = hub_of(r)
            if r.get("disabled") or r.get("deleted"):
                if r.get("link"):
                    items.append({"id": slug, "hidden": True})  # an old dashboard to hide there
                continue
            if hub["show"] and not r.get("link"):  # linked ones are already on the master dashboard
                owner = " ".join(display_name(users, u) for u in owners_of(r)) or r.get("owner", "")
                items.append({
                    # A page imported from the master dashboard's fixed list keeps that entry's id,
                    # so the master dashboard swaps its old link for this one (and pins still work).
                    "id": hub["legacy_id"] or f"drop-{slug}", "url": f"{base}/s/{slug}/",
                    "title": hub["title"] or r["title"], "category": hub["category"] or "other",
                    "branch": hub["branch"], "scope": hub["scope"],
                    "tags": hub["tags"] + [slug, owner.lower()],
                    "updated": r["updated"],
                })
        # Dynamic projects are published only when running and explicitly selected for the master dashboard.
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        for rec in load_dynamic_meta().values():
            if rec.get("show_on_master") and dynamic_running(rec):
                items.append({
                    "id": f"dynamic-{rec['slug']}", "url": rec.get("url") or f"http://{host}:{rec.get('port')}/",
                    "title": rec.get("title") or rec["slug"], "category": rec.get("category") or "other",
                    "branch": "", "scope": rec.get("master_scope") if rec.get("master_scope") in ("general", "all") else "all", "tags": [rec["slug"], "dynamic", rec.get("owner", "").lower()],
                    "updated": rec.get("updated", ""),
                })
        items.sort(key=lambda d: d.get("title", "").lower())
        return self.send_json(items, cors=True)

    def send_titles(self):
        # Read by Master_Dashboard.html: the new names of renamed dashboards that run on their
        # own ports. The master matches on its own id (the slug) or on the dashboard's link.
        by_slug, by_link = {}, {}
        for slug, r in load_meta().items():
            if r.get("link") and r.get("renamed") and not r.get("deleted"):
                by_slug[slug] = r["title"]
                by_link[r["link"]] = r["title"]
        return self.send_json({"by_slug": by_slug, "by_link": by_link}, cors=True)

    def serve_site(self, slug, rest):
        record = load_meta().get(slug)
        if not record or record.get("deleted"):
            return self.send_error(404, "No page with that name")
        if record.get("disabled") and not record.get("link"):
            return self.send_body(UNAVAILABLE_PAGE.encode("utf-8"), "text/html; charset=utf-8", 503)
        if record.get("link"):
            return self.redirect(record["link"])
        if rest is None:
            return self.redirect(f"/s/{quote(slug)}/")
        if rest == "/" and record["entry"] != "index.html":
            return self.redirect(f"/s/{quote(slug)}/{quote(record['entry'])}")
        base = (SITES / slug).resolve()
        target = (base / rest.lstrip("/")).resolve()
        if not target.is_relative_to(base):
            return self.send_error(403)
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return self.send_error(404)
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        try:
            with open(target, "rb") as f:
                size = os.fstat(f.fileno()).st_size
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(size))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                shutil.copyfileobj(f, self.wfile)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            # Browsers can't add this header to a cross-site request without our
            # permission, so another site can't make a logged-in user's browser act here.
            if self.headers.get("X-HD") != "1":
                raise UserError("Missing request header.", 403)

            if u.path == "/api/signup":
                data = self.read_json()
                username = signup(str(data.get("username", "")), str(data.get("password", "")))
                token = new_session(username)
                self.log_message("signup %s", username)
                return self.send_json({"user": self.user_of(username)},
                                      headers=[self.session_cookie(token, SESSION_DAYS * 86400)])
            if u.path == "/api/enter":
                # The login screen: logs in, or creates the user the first time.
                data = self.read_json()
                username = auth_or_create(str(data.get("username", "")), str(data.get("password", "")))
                token = new_session(username)
                return self.send_json({"user": self.user_of(username)},
                                      headers=[self.session_cookie(token, SESSION_DAYS * 86400)])
            if u.path == "/api/login":
                data = self.read_json()
                username = login(str(data.get("username", "")), str(data.get("password", "")))
                token = new_session(username)
                return self.send_json({"user": self.user_of(username)},
                                      headers=[self.session_cookie(token, SESSION_DAYS * 86400)])
            if u.path == "/api/logout":
                end_session(self.token())
                return self.send_json({"ok": True}, headers=[self.session_cookie("", 0)])
            if u.path == "/api/password":
                user = self.require_user()
                data = self.read_json()
                change_password(user["username"], str(data.get("old", "")), str(data.get("new", "")))
                return self.send_json({"ok": True})

            if u.path == "/api/upload":
                slug = q.get("slug", "").strip().lower()
                if not SLUG_RE.match(slug):
                    raise UserError("Link name must be lowercase letters, numbers and dashes "
                                    "(e.g. sales-dashboard).")
                data = self.read_body()
                self.check_not_taken(slug)
                user, cookie = self.acting_user()
                hub_choice = placement_to_hub(q["hub"]) if "hub" in q else None
                rec = publish(slug, q.get("title", "").strip()[:120], user,
                              q.get("filename", ""), data, hub_choice)
                self.log_message("%s published %s v%s", user["username"], slug, rec["version"])
                return self.send_json({**rec, "me": user}, headers=[cookie] if cookie else [])
            if u.path == "/api/dynamic/upload":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                if not SLUG_RE.match(slug):
                    raise UserError("Project name must be lowercase letters, numbers and dashes (e.g. revenue-dashboard).")
                title = q.get("title", "").strip()[:120] or slug.replace("-", " ").title()
                body = self.read_body()
                meta = load_dynamic_meta()
                if slug in meta or (DYNAMIC_ROOT / slug).exists():
                    raise UserError("A dynamic project with that name already exists. Choose a different link name.", 409)
                project_path = safe_extract_dynamic(body, slug)
                detected_entry, launch_type, _web_root = detect_dynamic_entry(project_path)
                port = allocate_dynamic_port(meta)
                host = (self.headers.get("Host") or "localhost").split(":")[0]
                rec = {"slug": slug, "title": title, "owner": user["username"],
                       "created": datetime.now().isoformat(timespec="seconds"),
                       "updated": datetime.now().isoformat(timespec="seconds"),
                       "port": port, "status": "preparing", "entry": detected_entry, "launch_type": launch_type, "pid": None,
                       "url": f"http://{host}:{port}/",
                       "show_on_master": q.get("placement", "off") in ("general", "all") if "placement" in q else q.get("show") == "1",
                       "master_scope": q.get("placement", "all") if q.get("placement") in ("general", "all") else "all",
                       "category": q.get("category", "other")[:40],
                       "message": ("Validated static HTML. Starting automatically." if launch_type == "static" else "Validated Python project. Preparing environment and starting automatically.")}
                meta[slug] = rec
                save_dynamic_meta(meta)
                threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("%s uploaded dynamic project %s; auto-start queued", user["username"], slug)
                return self.send_json(dynamic_public(rec, include_path=user.get("role") == "admin"), 201)
            if u.path == "/api/dynamic/replace-html":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                filename = Path(q.get("filename", "dashboard.html")).name
                if not SLUG_RE.match(slug):
                    raise UserError("Invalid project link name.")
                if Path(filename).suffix.lower() not in (".html", ".htm"):
                    raise UserError("Choose an .html or .htm file.")
                body = self.read_body()
                # Linked dashboards are stored in the normal page registry. Use its safe
                # replacement flow so the original HTML file is backed up before overwrite.
                linked_rec = load_meta().get(slug)
                if linked_rec and linked_rec.get("link") and not linked_rec.get("deleted"):
                    rec = replace_page(slug, user, filename, body)
                    self.log_message("%s replaced external dashboard HTML %s (v%s)",
                                     user["username"], slug, rec["version"])
                    return self.send_json(rec)
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec or not dynamic_owner_allowed(user, rec):
                        raise UserError("Project not found or access denied.", 404)
                    project = (DYNAMIC_ROOT / slug).resolve()
                    candidates = [p for p in project.rglob("*")
                                  if p.is_file() and p.suffix.lower() in (".html", ".htm")
                                  and ".venv" not in p.parts and ".git" not in p.parts
                                  and "node_modules" not in p.parts]
                    same_name = [p for p in candidates if p.name.lower() == filename.lower()]
                    if len(same_name) == 1:
                        target = same_name[0]
                    elif len(same_name) > 1:
                        indexes = [p for p in same_name if p.name.lower() == "index.html"]
                        if len(indexes) == 1:
                            target = indexes[0]
                        else:
                            raise UserError("More than one HTML file has that name. Upload using a unique existing HTML filename.", 409)
                    else:
                        indexes = [p for p in candidates if p.name.lower() in ("index.html", "index.htm")]
                        if len(indexes) == 1:
                            target = indexes[0]
                        elif len(candidates) == 1:
                            target = candidates[0]
                        elif not candidates:
                            raise UserError("This project ZIP has no HTML file to replace. Use Change ZIP instead.", 409)
                        else:
                            names = ", ".join(sorted(p.name for p in candidates[:12]))
                            raise UserError("Couldn't match that filename to a single HTML file in the project. Upload a file named like the existing HTML file. Found: " + names, 409)
                    backup_root = DYNAMIC_ROOT / ".html-backups" / slug / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                    backup_target = backup_root / target.relative_to(project)
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup_target)
                    tmp = target.with_name(target.name + ".htmldrop-new")
                    try:
                        tmp.write_bytes(body)
                        os.replace(tmp, target)
                    except Exception:
                        tmp.unlink(missing_ok=True)
                        raise
                    # Restart the project so the new HTML is picked up by its app/template engine.
                    stop_dynamic_process(slug, rec)
                    rec["status"] = "preparing"
                    rec["message"] = "HTML file replaced (backup saved). Restarting dashboard automatically."
                    rec["pid"] = None
                    rec["updated"] = datetime.now().isoformat(timespec="seconds")
                    save_dynamic_meta(meta)
                    threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("%s replaced HTML for dynamic project %s", user["username"], slug)
                return self.send_json({"ok": True, "slug": slug,
                                       "message": "HTML file replaced. Backup saved and dashboard restart started."}, 202)

            if u.path == "/api/dynamic/replace":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                if not SLUG_RE.match(slug):
                    raise UserError("Invalid project link name.")
                body = self.read_body()
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec or not dynamic_owner_allowed(user, rec):
                        raise UserError("Project not found or access denied.", 404)
                    staging_slug = slug + "-replacement-" + secrets.token_hex(4)
                    staged_path = safe_extract_dynamic(body, staging_slug)
                    if rec.get("refresh", {}).get("enabled") and not (staged_path / "refresh_dashboard.py").is_file():
                        shutil.rmtree(staged_path, ignore_errors=True)
                        raise UserError("Replacement ZIP is missing refresh_dashboard.py, but this project has an active refresh schedule. The existing project and schedule were left unchanged.", 409)
                    live_path = DYNAMIC_ROOT / slug
                    backup_path = DYNAMIC_ROOT / ("." + slug + ".backup-" + secrets.token_hex(4))
                    stop_dynamic_process(slug, rec)
                    moved_old = False
                    try:
                        if live_path.exists():
                            live_path.rename(backup_path)
                            moved_old = True
                        staged_path.rename(live_path)
                    except Exception:
                        if live_path.exists() and moved_old:
                            shutil.rmtree(live_path, ignore_errors=True)
                        if moved_old and backup_path.exists():
                            backup_path.rename(live_path)
                        shutil.rmtree(staged_path, ignore_errors=True)
                        raise
                    shutil.rmtree(backup_path, ignore_errors=True)
                    rec["status"] = "preparing"
                    rec["message"] = "ZIP replaced. Preparing environment and restarting automatically."
                    rec["pid"] = None
                    rec["updated"] = datetime.now().isoformat(timespec="seconds")
                    meta[slug] = rec
                    save_dynamic_meta(meta)
                    threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("%s replaced dynamic project %s and queued restart", user["username"], slug)
                return self.send_json({**dynamic_public(rec, include_path=user.get("role") == "admin"),
                                       "message": "ZIP replaced. Restart started automatically."}, 202)

            if u.path == "/api/dynamic/start":
                user = self.require_admin()
                slug = q.get("slug", "")
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec:
                        raise UserError("Project not found.", 404)
                    if dynamic_running(rec):
                        return self.send_json(dynamic_public(rec, include_path=True))
                    if rec.get("status") == "preparing":
                        return self.send_json(dynamic_public(rec, include_path=True))
                    entry, launch_type, _web_root = detect_dynamic_entry(DYNAMIC_ROOT / slug)
                    if not entry:
                        raise UserError("No supported launch entry found. Add index.html or a supported Python entry point.")
                    rec["entry"] = entry
                    rec["launch_type"] = launch_type
                    if dynamic_port_in_use(rec["port"]):
                        rec["port"] = allocate_dynamic_port(meta)
                        host = (self.headers.get("Host") or "localhost").split(":")[0]
                        rec["url"] = f"http://{host}:{rec['port']}/"
                    rec["status"] = "preparing"
                    rec["message"] = "Queued for environment setup and startup."
                    rec["updated"] = datetime.now().isoformat(timespec="seconds")
                    save_dynamic_meta(meta)
                    threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("admin %s started dynamic project %s", user["username"], slug)
                return self.send_json(dynamic_public(rec, include_path=True), 202)
            if u.path == "/api/dynamic/rename":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                data = self.read_json()
                title = str(data.get("title", "")).strip()
                if not title:
                    raise UserError("Type a project name first.")
                if len(title) > 120:
                    raise UserError("Project name must be 120 characters or fewer.")
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec or not dynamic_owner_allowed(user, rec):
                        raise UserError("Project not found or access denied.", 404)
                    rec["title"] = title
                    rec["updated"] = datetime.now().isoformat(timespec="seconds")
                    save_dynamic_meta(meta)
                self.log_message("%s renamed dynamic project %s to %s", user["username"], slug, title)
                return self.send_json(dynamic_public(rec, include_path=True))
            if u.path == "/api/dynamic/toggle-disabled":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                disabled = (q.get("disabled", "1").strip().lower() not in ("0", "false", "no"))
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec or not dynamic_owner_allowed(user, rec):
                        raise UserError("Project not found or access denied.", 404)
                    if disabled:
                        stop_dynamic_process(slug, rec)
                        rec["disabled"] = True
                        rec["status"] = "disabled"
                        rec["message"] = "Temporarily disabled from HTML Drop."
                    else:
                        rec["disabled"] = False
                        entry, launch_type, _web_root = detect_dynamic_entry(DYNAMIC_ROOT / slug)
                        if not entry:
                            raise UserError("No supported launch entry found. Add index.html or a supported Python entry point.")
                        rec["entry"] = entry
                        rec["launch_type"] = launch_type
                        rec["status"] = "preparing"
                        rec["message"] = "Re-enabled; starting project."
                    rec["updated"] = datetime.now().isoformat(timespec="seconds")
                    save_dynamic_meta(meta)
                    if not disabled:
                        threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("%s %s dynamic project %s", user["username"],
                                 "disabled" if disabled else "enabled", slug)
                return self.send_json(dynamic_public(rec, include_path=True))
            if u.path == "/api/dynamic/stop":
                user = self.require_admin()
                slug = q.get("slug", "")
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec:
                        raise UserError("Project not found.", 404)
                    stop_dynamic_process(slug, rec)
                    save_dynamic_meta(meta)
                self.log_message("admin %s stopped dynamic project %s", user["username"], slug)
                return self.send_json(dynamic_public(rec, include_path=True))
            if u.path == "/api/dynamic/delete":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                with DYNAMIC_LOCK:
                    meta = load_dynamic_meta()
                    rec = meta.get(slug)
                    if not rec:
                        raise UserError("Project not found.", 404)
                    if not dynamic_owner_allowed(user, rec):
                        raise UserError("Only the project owner or an admin can delete it.", 403)
                    stop_dynamic_process(slug, rec)
                    delete_refresh_task(slug)
                    save_dynamic_meta(meta)
                    shutil.rmtree(DYNAMIC_ROOT / slug, ignore_errors=True)
                    shutil.rmtree(DYNAMIC_LOG_ROOT / slug, ignore_errors=True)
                    meta.pop(slug, None)
                    save_dynamic_meta(meta)
                self.log_message("%s %s deleted dynamic project %s", user.get("role", "user"), user["username"], slug)
                return self.send_json({"ok": True})
            if u.path == "/api/dynamic/refresh-settings":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                data = self.read_json()
                meta = load_dynamic_meta()
                rec = meta.get(slug)
                if not rec or not dynamic_owner_allowed(user, rec):
                    raise UserError("Project not found or access denied.", 404)
                if not data.get("enabled"):
                    delete_refresh_task(slug)
                    rec["refresh"] = {"enabled": False, "task_name": refresh_task_name(slug), "updated": datetime.now().isoformat(timespec="seconds")}
                    save_dynamic_meta(meta)
                    return self.send_json({"ok": True, "refresh": rec["refresh"]})
                settings={"frequency":str(data.get("frequency","daily")),"time":str(data.get("time","06:00")),
                          "hours":int(data.get("hours",1)),"days_interval":int(data.get("days_interval",1)),
                          "days":data.get("days",["Mon","Tue","Wed","Thu","Fri"]),"catch_up":True,"wake_to_run":True}
                if settings["frequency"] not in ("daily","hourly","weekly","custom"):
                    raise UserError("Invalid refresh frequency.")
                register_refresh_task(slug,rec,settings)
                rec["updated"] = datetime.now().isoformat(timespec="seconds")
                save_dynamic_meta(meta)
                self.log_message("%s configured refresh task for %s",user["username"],slug)
                return self.send_json({"ok":True,"refresh":rec["refresh"]},201)
            if u.path == "/api/dynamic/refresh-now":
                user=self.require_user(); slug=q.get("slug","").strip().lower()
                meta=load_dynamic_meta(); rec=meta.get(slug)
                if not rec or not dynamic_owner_allowed(user,rec): raise UserError("Project not found or access denied.",404)
                script=(DYNAMIC_ROOT/slug/"refresh_dashboard.py").resolve()
                if not script.is_file(): raise UserError("Project has no refresh_dashboard.py.")
                if os.name!="nt": raise UserError("Run-now is supported on the Windows host only.",501)
                py=DYNAMIC_ROOT/slug/".venv"/"Scripts"/"python.exe"
                if not py.is_file(): py=Path(sys.executable)
                logdir=DYNAMIC_LOG_ROOT/slug; logdir.mkdir(parents=True,exist_ok=True)
                log=(logdir/"refresh.log").open("a",encoding="utf-8")
                log.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Manual refresh started\n"); log.flush()
                subprocess.Popen([str(py),str(script)],cwd=str(DYNAMIC_ROOT/slug),stdout=log,stderr=subprocess.STDOUT,
                                 creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0))
                return self.send_json({"ok":True,"message":"Refresh started. See project logs for results."},202)

            if u.path == "/api/dynamic/settings":
                user = self.require_admin()
                slug = q.get("slug", "")
                data = self.read_json()
                meta = load_dynamic_meta()
                rec = meta.get(slug)
                if not rec:
                    raise UserError("Project not found.", 404)
                rec["show_on_master"] = bool(data.get("show_on_master"))
                if data.get("placement") in ("off", "general", "all"):
                    rec["show_on_master"] = data["placement"] != "off"
                    if data["placement"] in ("general", "all"):
                        rec["master_scope"] = data["placement"]
                category = str(data.get("category", "other"))
                allowed_categories = set(CONFIG.get("hub_categories", DEFAULT_HUB_CATEGORIES)) | {"other"}
                if category not in allowed_categories:
                    category = "other"
                rec["category"] = category
                rec["updated"] = datetime.now().isoformat(timespec="seconds")
                save_dynamic_meta(meta)
                return self.send_json(dynamic_public(rec, include_path=True))

            if u.path == "/api/disable":
                user = self.require_user()
                on = q.get("on") == "1"
                rec = set_disabled(q.get("slug", ""), user, on)
                self.log_message("%s %s %s", user["username"], "disabled" if on else "enabled", q.get("slug"))
                return self.send_json(rec)
            if u.path == "/api/replace":
                user = self.require_user()
                data = self.read_body()
                rec = replace_page(q.get("slug", ""), user, q.get("filename", ""), data)
                self.log_message("%s replaced %s (v%s)", user["username"], q.get("slug"), rec["version"])
                return self.send_json(rec)
            if u.path == "/api/page":
                user, cookie = self.acting_user()
                rec = update_page(q.get("slug", ""), user, self.read_json())
                self.log_message("%s edited %s", user["username"], q.get("slug"))
                return self.send_json({**rec, "me": user}, headers=[cookie] if cookie else [])
            if u.path == "/api/rename":
                user = self.require_user()
                rec = rename_page(q.get("slug", ""), user, self.read_json().get("title", ""))
                self.log_message("%s renamed %s -> %s", user["username"], q.get("slug"), rec["title"])
                return self.send_json(rec)
            if u.path == "/api/delete":
                user = self.require_user()
                delete(q.get("slug", ""), user)
                self.log_message("%s deleted %s", user["username"], q.get("slug"))
                return self.send_json({"ok": True})

            if u.path == "/api/admin/hub":
                self.require_admin()
                hub = set_hub(q.get("slug", ""), self.read_json())
                self.log_message("hub %s -> %s", q.get("slug"), placement_of(hub))
                return self.send_json(hub)
            if u.path == "/api/admin/user":
                me = self.require_admin()
                data = self.read_json()
                admin_user_action(me["username"], str(data.get("action", "")),
                                  str(data.get("username", "")), str(data.get("value", "")))
                self.log_message("admin %s: %s %s", me["username"], data.get("action"), data.get("username"))
                return self.send_json({"ok": True})
            self.send_error(404)
        except UserError as e:
            self.send_json({"error": str(e)}, e.status)
        except zipfile.BadZipFile:
            self.send_json({"error": "That zip file is damaged or not a zip."}, 400)
        except Exception as e:
            traceback.print_exc()
            self.send_json({"error": f"Server error: {e}"}, 500)

    def user_of(self, username):
        return public_user(username, load_json(USERS_FILE)[username])


class ExclusiveServer(ThreadingHTTPServer):
    # http.server enables SO_REUSEADDR, which on Windows lets a second program bind
    # the same port silently and steal requests. Claim the port exclusively instead.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    if sys.stdout is None or sys.stderr is None:
        # Started with pythonw (no console, e.g. from auto-start): log to a file.
        log = open(ROOT / "server.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = log
    for d in (SITES, HISTORY, TMP):
        d.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir()
    ensure_admin()
    sync_existing_dashboards()
    load_sessions()
    port = int(CONFIG.get("personal_test_port", 8151))
    try:
        httpd = ExclusiveServer(("127.0.0.1", port), Handler)
    except OSError:
        sys.exit(f"Port {port} is already in use by another program. "
                 f"Change \"port\" in config.json and try again.")
    host = socket.gethostname()
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        ip = "127.0.0.1"
    print(f"HTML Drop PERSONAL TEST instance running locally only:\n  http://127.0.0.1:{port}/\nThis instance is not exposed to your LAN. Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
