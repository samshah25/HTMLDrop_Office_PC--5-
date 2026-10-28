
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

CATEGORIES_FILE = DATA / "categories.json"

DEFAULT_CATEGORIES = {
    "perf": {"label": "Sales Performance", "color": "#60a5fa"},
    "funnel": {"label": "Sales Funnel & Conversion", "color": "#fb7185"},
    "calls": {"label": "TME Calls & Sales Assistance", "color": "#f97316"},
    "renew": {"label": "Renewals & Retention", "color": "#34d399"},
    "ecs": {"label": "ECS & Collections", "color": "#fbbf24"},
    "explore": {"label": "Exploratory Insights", "color": "#e879f9"},
    "hr": {"label": "Workforce", "color": "#a78bfa"},
    "other": {"label": "More Dashboards", "color": "#94a3b8"},
}

def load_categories():
    cats = dict(DEFAULT_CATEGORIES)
    if CATEGORIES_FILE.is_file():
        try:
            custom = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
            cats.update(custom)
        except Exception:
            pass
    return cats

def add_category(key, label, color):
    custom = {}
    if CATEGORIES_FILE.is_file():
        try:
            custom = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    custom[key] = {"label": label, "color": color}
    CATEGORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    CATEGORIES_FILE.write_text(json.dumps(custom, indent=2), encoding="utf-8")
    return custom



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
DEFAULT_MASTER_URL = "/Master_dashboard.html"

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
    if not token:
        return None
    s = sessions.get(token)
    if not s or s.get("expires", 0) < time.time():
        disk_sessions = load_json(SESSIONS_FILE)
        s = disk_sessions.get(token)
        if s and s.get("expires", 0) > time.time():
            sessions[token] = s
        else:
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
        "jda_jds_mumbai_pincod" in title or "mumbai-pincode" in key or "mumbai_pincode" in key
        or "jda_jds_kolkata_pincod" in title or "kolkata-pincode" in key or "kolkata_pincode" in key
        or "pan_india_jda" in title or "pan_india_jda" in key or "pan india jda" in title or "pan-india-jda" in key
        or "employee headcount" in title
        or "employee_headcount" in key or "employee-headcount" in key or "headcount-tenure" in key
        or ("headcount" in title and "employee" in title)
    )


def public_record(slug, r, users):
    hub = hub_of(r)
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
        "placement": placement_of(hub),
        "category": hub.get("category", "other"),
    }


def can_manage(user, record):
    return bool(user) and (user["role"] == "admin" or user["username"] in owners_of(record))


def get_managed(meta, slug, user):
    record = meta.get(slug)
    if not record or record.get("deleted"):
        raise UserError("No such page.", 404)
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
    if ext == ".zip":
        raise UserError("ZIP files are only for dynamic projects. Please upload your project ZIP as a dynamic project.")
    if ext not in (".html", ".htm"):
        raise UserError("Only .html or .htm files are accepted for static dashboards.")
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


def get_existing_dashboard_file(slug, record=None, fallback_name=None):
    """Accurately resolve the local dashboard file Path on the host PC.
    Guarantees returning a file path (never a bare folder path)."""
    file_setting = (record.get("file") or "").strip() if record else ""

    # If file_setting points to an actual file on disk, return it directly
    if file_setting and Path(file_setting).is_file():
        return Path(file_setting).resolve()

    # Determine the target HTML filename
    expected_filename = ""
    if file_setting and not Path(file_setting).is_dir():
        expected_filename = Path(file_setting).name
    if not expected_filename and fallback_name:
        expected_filename = Path(fallback_name).name
    if not expected_filename and record and record.get("link"):
        try:
            expected_filename = unquote(urlparse(record["link"]).path).rsplit("/", 1)[-1]
        except Exception:
            pass
    if not expected_filename:
        for s, _p, fn, _o, _t in EXISTING_DASHBOARDS:
            if s.lower() == str(slug).lower():
                expected_filename = fn
                break
    if not expected_filename:
        expected_filename = f"{slug}.html"

    # Check Task Scheduler WorkingDirectory if task exists on Windows
    try:
        _tname, xml_root = query_task_scheduler_info(slug, record)
        if xml_root is not None:
            NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
            for exec_node in xml_root.findall(f".//{{{NS}}}Exec"):
                wdir_node = exec_node.find(f"{{{NS}}}WorkingDirectory")
                if wdir_node is not None and wdir_node.text:
                    wdir = Path(wdir_node.text.strip().strip('"'))
                    cand = wdir / expected_filename
                    if cand.is_file():
                        return cand.resolve()
    except Exception:
        pass

    # Check standard dashboard directory
    dash_folder = Path(r"C:\Users\10179794\Dashboardd\dash")
    cand = dash_folder / expected_filename
    if cand.is_file() or dash_folder.is_dir():
        return cand.resolve()

    # Try matching file via find_dashboard_file if link responds
    if record and record.get("link"):
        try:
            found = find_dashboard_file(record["link"])
            if found and Path(found).is_file():
                return Path(found).resolve()
        except Exception:
            pass

    # Default fallback to dash folder
    return cand.resolve()


def replace_page(slug, user, filename, data):
    """The Replace button: new file, same link. An existing dashboard's file is overwritten in
    its own folder under its own name (backed up first); an HTML Drop page gets a new version."""
    with lock:
        meta = load_meta()
        record = meta.get(slug)
        if not record or record.get("deleted"):
            raise UserError("No such page.", 404)
        if not record.get("link"):
            if Path(filename).suffix.lower() not in (".html", ".htm"):
                raise UserError("Static dashboards only accept .html or .htm files. Upload a .zip for dynamic projects.")
        else:
            if not can_manage(user, record):
                raise UserError("Only the page's owners or an admin can replace it.", 403)
            if Path(filename).suffix.lower() not in (".html", ".htm"):
                raise UserError("Choose the dashboard's .html file.")
            target = get_existing_dashboard_file(slug, record, fallback_name=filename)
            record["file"] = str(target)
            if record.get("disabled"):
                target = parked_path(slug, record)  # stays hidden until Enable
                target.parent.mkdir(parents=True, exist_ok=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now()
            backup = HISTORY / slug / f"{now:%Y%m%d-%H%M%S}_v{record['version']}"
            backup.mkdir(parents=True, exist_ok=True)
            if target.is_file():
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
        target_slug = slug
        if target_slug not in meta:
            for s in meta:
                if s.lower() == slug.lower() or meta[s].get("title", "").lower() == slug.lower():
                    target_slug = s
                    break
        if target_slug in meta and not meta[target_slug].get("deleted"):
            record = meta[target_slug]
            title = str(data.get("title", "")).strip()[:120]
            if title:
                record["title"] = title
            if "placement" in data:
                hub_up = placement_to_hub(data["placement"])
                if "category" in data and data["category"]:
                    hub_up["category"] = str(data["category"]).strip()[:40]
                record["hub"] = {**hub_of(record), **hub_up}
            if "category" in data and data["category"]:
                hub = hub_of(record)
                hub["category"] = str(data["category"]).strip()[:40]
                record["hub"] = hub
            if "link" in data and data["link"]:
                record["link"] = str(data["link"]).strip()
            save_meta(meta)
            return public_record(target_slug, record, load_json(USERS_FILE))
            
        # Also check dynamic meta
        dyn_meta = load_dynamic_meta()
        target_dyn = slug
        if target_dyn not in dyn_meta:
            for s in dyn_meta:
                if s.lower() == slug.lower() or dyn_meta[s].get("title", "").lower() == slug.lower():
                    target_dyn = s
                    break
        if target_dyn in dyn_meta and not dyn_meta[target_dyn].get("deleted"):
            drec = dyn_meta[target_dyn]
            title = str(data.get("title", "")).strip()[:120]
            if title:
                drec["title"] = title
            if "placement" in data:
                drec["show_on_master"] = (data["placement"] != "off")
                drec["master_scope"] = data["placement"] if data["placement"] in ("general", "all") else "all"
            if "category" in data and data["category"]:
                drec["category"] = str(data["category"]).strip()[:40]
            if "link" in data and data["link"]:
                drec["link"] = str(data["link"]).strip()
                drec["external_url"] = str(data["link"]).strip()
            save_dynamic_meta(dyn_meta)
            return dynamic_public(drec, include_path=True)
            
        raise UserError("No such page.", 404)


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
            default_dash_file = str(Path(r"C:\Users\10179794\Dashboardd\dash") / filename)
            current_file = (kept.get("file") or "").strip()
            if not current_file or Path(current_file).is_dir():
                current_file = default_dash_file
            meta[slug] = {
                "title": kept["title"] if kept.get("renamed") else (title or filename.rsplit(".", 1)[0]),
                "renamed": bool(kept.get("renamed")),
                "user": keys[0], "editors": keys[1:],
                "link": f"http://{EXISTING_HOST}:{port}/{filename}",
                "file": current_file,
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

def count_category_dashboards(key):
    cnt = 0
    key = str(key or '').strip().lower()
    try:
        with lock:
            if META_FILE.is_file():
                meta = load_meta()
                for r in meta.values():
                    hub = hub_of(r)
                    cat = str(hub.get('category') or r.get('category') or '').strip().lower()
                    if cat == key:
                        cnt += 1
            if DYNAMIC_META_FILE.is_file():
                dyn = load_dynamic_meta()
                for dr in dyn.values():
                    cat = str(dr.get('category') or '').strip().lower()
                    if cat == key:
                        cnt += 1
    except Exception:
        pass
    return cnt


def delete_category(key):
    key = str(key or '').strip().lower()
    if not key:
        raise UserError('Section key is required.', 400)
    if key in DEFAULT_CATEGORIES:
        raise UserError('Default system sections cannot be deleted.', 400)
    
    cnt = count_category_dashboards(key)
    if cnt > 0:
        raise UserError(f"Cannot delete section '{key}' because it contains {cnt} dashboard(s). Move them to another section first.", 400)
    
    custom = {}
    if CATEGORIES_FILE.is_file():
        try:
            custom = json.loads(CATEGORIES_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    if key in custom:
        del custom[key]
        CATEGORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        CATEGORIES_FILE.write_text(json.dumps(custom, indent=2), encoding='utf-8')
    return custom

    save_json(DYNAMIC_META_FILE, meta)


def get_dynamic_record(slug, meta=None):
    if meta is None:
        meta = load_dynamic_meta()
    if slug in meta:
        return slug, meta[slug]
    slug_lower = str(slug).lower().strip()
    for k, v in meta.items():
        if k.lower().strip() == slug_lower:
            return k, v
    slug_norm = slug_lower.replace("_", "-")
    for k, v in meta.items():
        if k.lower().strip().replace("_", "-") == slug_norm:
            return k, v
    return slug, None


def get_site_record(slug, meta=None):
    if meta is None:
        meta = load_meta()
    if slug in meta:
        return slug, meta[slug]
    slug_lower = str(slug).lower().strip()
    for k, v in meta.items():
        if k.lower().strip() == slug_lower:
            return k, v
    slug_norm = slug_lower.replace("_", "-")
    for k, v in meta.items():
        if k.lower().strip().replace("_", "-") == slug_norm:
            return k, v
    return slug, None


def dynamic_public(rec, include_path=False):
    out = {k: rec.get(k) for k in ("slug", "title", "owner", "created", "updated", "port", "status", "entry", "url", "show_on_master", "master_scope", "category", "message", "refresh")}
    out["disabled"] = bool(rec.get("disabled"))
    out["entry_html"] = Path(rec.get("entry") or "index.html").name
    slug = rec.get("slug", "")
    project_dir = DYNAMIC_ROOT / slug
    out["refresh_available"] = (project_dir / "main.py").is_file() or (project_dir / "refresh_dashboard.py").is_file()
    out["launch_type"] = rec.get("launch_type") or detect_dynamic_entry(project_dir)[1]
    main_port = int(CONFIG.get("port", 8150))
    if out["launch_type"] == "static" or (project_dir / "index.html").is_file() or int(rec.get("port", 0)) == main_port:
        out["port"] = main_port
        out["url"] = f"/s/{slug}/"
        out["running"] = not out["disabled"]
        out["status"] = "running"
    else:
        out["running"] = dynamic_running(rec)
        if out["running"]:
            out["status"] = "running"
        elif rec.get("status") == "running":
            out["status"] = "stopped"
    if include_path:
        out["project_path"] = str(DYNAMIC_ROOT / slug)
    return out


def dynamic_running(rec):
    slug = rec.get("slug", "")
    project_dir = DYNAMIC_ROOT / slug
    main_port = int(CONFIG.get("port", 8150))
    if rec.get("launch_type") == "static" or (project_dir / "index.html").is_file() or int(rec.get("port", 0)) == main_port:
        return not bool(rec.get("disabled"))
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
    """Detect launch method separately from refresh capability.
    HTML dashboards take precedence so they are served directly on port 8150."""
    ignored = {".venv", ".git", "node_modules"}
    indexes = [p for p in project.rglob("index.html") if p.is_file() and not ignored.intersection(p.parts)]
    if len(indexes) == 1:
        return str(indexes[0].relative_to(project)).replace("\\", "/"), "static", indexes[0].parent
    if len(indexes) > 1:
        root_indexes = [p for p in indexes if p.parent == project]
        if len(root_indexes) == 1:
            return "index.html", "static", project
        return str(indexes[0].relative_to(project)).replace("\\", "/"), "static", indexes[0].parent
    html_files = [p for p in project.rglob("*") if p.is_file() and p.suffix.lower() in (".html", ".htm") and not ignored.intersection(p.parts)]
    if html_files:
        root_html = [p for p in html_files if p.parent == project]
        chosen = root_html[0] if root_html else html_files[0]
        return str(chosen.relative_to(project)).replace("\\", "/"), "static", chosen.parent
    for name in ("app.py", "main.py", "run.py", "server.py"):
        candidate = project / name
        if candidate.is_file():
            return name, "python", None
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
    """Analyze project and prepare dashboard on port 8150 or launch Python app."""
    meta = load_dynamic_meta()
    rec = meta.get(slug)
    if not rec:
        return
    project = DYNAMIC_ROOT / slug
    log_dir = DYNAMIC_LOG_ROOT / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "runtime.log"
    rec["status"] = "preparing"
    rec["message"] = "Analyzing project and preparing dashboard."
    rec["updated"] = datetime.now().isoformat(timespec="seconds")
    save_dynamic_meta(meta)
    log_handle = None
    try:
        entry, launch_type, web_root = detect_dynamic_entry(project)
        if not entry:
            raise RuntimeError("No supported launch entry found. Add index.html or a supported Python entry point.")
        py = Path(sys.executable)
        env_dir = project / ".venv"
        requirements = project / "requirements.txt"
        has_script = (project / "main.py").is_file() or (project / "refresh_dashboard.py").is_file()
        if (launch_type == "python" or has_script) and requirements.is_file() and requirements.read_text(encoding="utf-8", errors="replace").strip():
            if not (env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")).exists():
                venv.EnvBuilder(with_pip=True, clear=False).create(str(env_dir))
            py = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Installing requirements.txt\n")
                log.flush()
                result = subprocess.run([str(py), "-m", "pip", "install", "-r", str(requirements)], cwd=str(project), stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
            if result.returncode != 0:
                raise RuntimeError("Dependency installation failed. Check project logs.")

        meta = load_dynamic_meta()
        rec = meta.get(slug)
        if not rec:
            return

        main_port = int(CONFIG.get("port", 8150))
        if launch_type == "static":
            # Run main.py once in background to generate fresh initial data (e.g. data.json/data.js)
            script_file = project / "main.py"
            if not script_file.is_file():
                script_file = project / "refresh_dashboard.py"
            if script_file.is_file():
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Running data generation ({script_file.name})...\n")
                    log.flush()
                    proc_run = subprocess.run([str(py), "-u", str(script_file)], cwd=str(project), stdout=log, stderr=subprocess.STDOUT, timeout=300, check=False)
                    if proc_run.returncode == 0:
                        log.write(f"[{datetime.now().isoformat(timespec='seconds')}] Data generation completed successfully.\n")
                    else:
                        log.write(f"[{datetime.now().isoformat(timespec='seconds')}] Data generation returned code {proc_run.returncode}.\n")

            rec["port"] = main_port
            rec["status"] = "running"
            rec["entry"] = entry
            rec["launch_type"] = "static"
            rec["pid"] = None
            rec["url"] = f"/s/{slug}/"
            rec["message"] = "Dashboard is live on port 8150."
            rec["updated"] = datetime.now().isoformat(timespec="seconds")
            save_dynamic_meta(meta)
            DYNAMIC_PROCESSES.pop(slug, None)
            return

        port = int(rec.get("port") or allocate_dynamic_port(meta))
        rec["port"] = port
        env = os.environ.copy()
        env.update({"PORT": str(port), "HOST": "0.0.0.0", "DASHBOARD_PORT": str(port), "DASHBOARD_HOST": "0.0.0.0", "PYTHONUNBUFFERED": "1"})
        log_handle = log_path.open("a", encoding="utf-8")
        launch_cwd = project
        command = [str(py), "-u", str(project / entry)]
        log_handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Starting Python entry {entry} on 0.0.0.0:{port}\n")
        log_handle.flush()
        proc = subprocess.Popen(command, cwd=str(launch_cwd), env=env, stdout=log_handle, stderr=subprocess.STDOUT, creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0))
        DYNAMIC_PROCESSES[slug] = proc
        rec["pid"] = proc.pid
        rec["status"] = "running"
        rec["entry"] = entry
        rec["launch_type"] = launch_type
        rec["url"] = f"http://localhost:{port}/"
        rec["message"] = f"Started {entry} on port {port}."
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

EXISTING_TASK_NAMES = {
    "kolkata-pincode": "Kolkata_Dashboard_Refresh",
    "headcount-tenure": "Employee_Headcount_Tenure_Referesh",
    "mumbai-pincode": "Mumbai_Pincode_Dashboard_Refresh",
    "Pan_india_JDA": "Pan_India_data_refresh",
    "pan_india_jda": "Pan_India_data_refresh",
    "pan-india-jda": "Pan_India_data_refresh",
}


def refresh_task_name(slug):
    norm = str(slug).strip().lower().replace("_", "-")
    for s_key, t_name in EXISTING_TASK_NAMES.items():
        if s_key.lower().replace("_", "-") == norm or s_key.lower() == str(slug).lower():
            return t_name
    return "HTMLDrop_Refresh_" + str(slug).replace(" ", "_")


def get_task_candidates(slug):
    norm = str(slug).strip().lower().replace("_", "-")
    candidates = []
    for s_key, t_name in EXISTING_TASK_NAMES.items():
        if s_key.lower().replace("_", "-") == norm or s_key.lower() == str(slug).lower():
            candidates.append(t_name)
            candidates.append("\\" + t_name)
    for s_key, t_name in EXISTING_TASK_NAMES.items():
        if t_name.lower() == str(slug).lower().lstrip("\\"):
            candidates.append(t_name)
            candidates.append("\\" + t_name)
    clean_slug = str(slug).replace(" ", "_")
    candidates.append("HTMLDrop_Refresh_" + clean_slug)
    candidates.append("\\HTMLDrop_Refresh_" + clean_slug)
    return candidates


def query_task_scheduler_info(slug, rec=None):
    """Query Task Scheduler for existing task info using schtasks /Query /XML.
    Returns (task_name, xml_root) or (None, None)."""
    if os.name != "nt":
        return None, None
    import xml.etree.ElementTree as ET
    candidates = []
    if rec and isinstance(rec.get("refresh"), dict) and rec["refresh"].get("task_name"):
        t = rec["refresh"]["task_name"]
        candidates.extend([t, "\\" + t.lstrip("\\"), t.lstrip("\\")])
    candidates.extend(get_task_candidates(slug))
    seen = set()
    uniq = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)

    for t_name in uniq:
        try:
            res = subprocess.run(["schtasks.exe", "/Query", "/TN", t_name, "/XML"],
                                 capture_output=True, text=True, timeout=8, check=False)
            if res.returncode == 0 and res.stdout.strip():
                xml_str = res.stdout.strip()
                idx = xml_str.find("<Task")
                if idx != -1:
                    xml_str = xml_str[idx:]
                    root = ET.fromstring(xml_str)
                    return t_name, root
        except Exception:
            pass
    return None, None


def extract_trigger_info_from_xml(xml_root):
    if xml_root is None:
        return {}
    NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    info = {}
    try:
        triggers = xml_root.find(f".//{{{NS}}}Triggers")
        if triggers is not None:
            cal = triggers.find(f"{{{NS}}}CalendarTrigger")
            if cal is not None:
                sb = cal.find(f"{{{NS}}}StartBoundary")
                if sb is not None and sb.text:
                    m = re.search(r"T(\d{2}:\d{2})", sb.text)
                    if m:
                        info["time"] = m.group(1)
                rep = cal.find(f"{{{NS}}}Repetition")
                if rep is not None:
                    iv = rep.find(f"{{{NS}}}Interval")
                    if iv is not None and iv.text:
                        info["frequency"] = "hourly"
                        hm = re.search(r"PT(\d+)H", iv.text)
                        if hm:
                            info["hours"] = int(hm.group(1))
                elif cal.find(f"{{{NS}}}ScheduleByWeek") is not None:
                    info["frequency"] = "weekly"
                elif cal.find(f"{{{NS}}}ScheduleByDay") is not None:
                    info["frequency"] = "daily"
    except Exception:
        pass
    return info


def apply_triggers_to_task_xml(root, settings):
    """In-place update of triggers in an existing Task Scheduler XML. Preserves all actions, principals, and settings."""
    import xml.etree.ElementTree as ET
    from datetime import datetime as _dt, timedelta as _td
    NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
    ET.register_namespace("", NS)

    start_time = str(settings.get("time", "06:00")).strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", start_time):
        raise UserError("Time must be valid 24-hour HH:MM, for example 06:01 or 19:19.")
    now = _dt.now()
    hh, mm = map(int, start_time.split(":"))
    start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if start <= now:
        start += _td(days=1)
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%S")

    triggers_node = root.find(f"{{{NS}}}Triggers")
    if triggers_node is not None:
        triggers_node.clear()
    else:
        insert_idx = len(root)
        for idx, child in enumerate(root):
            tag = child.tag.split("}")[-1]
            if tag in ("Principals", "Settings", "Data", "Actions"):
                insert_idx = idx
                break
        triggers_node = ET.Element(f"{{{NS}}}Triggers")
        root.insert(insert_idx, triggers_node)

    def el(parent, name, text=None, attrs=None):
        node = ET.SubElement(parent, "{" + NS + "}" + name, attrs or {})
        if text is not None:
            node.text = str(text)
        return node

    freq = settings.get("frequency", "daily")
    trigger = el(triggers_node, "CalendarTrigger")
    el(trigger, "StartBoundary", start_iso)
    el(trigger, "Enabled", "true")

    if freq == "hourly":
        hours = max(1, min(23, int(settings.get("hours", 1))))
        rep = el(trigger, "Repetition")
        el(rep, "Interval", f"PT{hours}H")
        el(rep, "StopAtDurationEnd", "false")
        daily = el(trigger, "ScheduleByDay")
        el(daily, "DaysInterval", "1")
    elif freq in ("weekly", "weekdays"):
        by = el(trigger, "ScheduleByWeek")
        el(by, "WeeksInterval", "1")
        days = el(by, "DaysOfWeek")
        daymap = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
                  "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}
        if freq == "weekdays":
            selected = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        else:
            selected = settings.get("days", ["Mon", "Tue", "Wed", "Thu", "Fri"])
        if not selected:
            raise UserError("Select at least one day for weekly refresh.")
        for d in selected:
            if d in daymap:
                el(days, daymap[d])
    else:
        by = el(trigger, "ScheduleByDay")
        days_interval = max(1, min(365, int(settings.get("days_interval", 1))))
        el(by, "DaysInterval", str(days_interval))

    return ET.tostring(root, encoding="utf-16", xml_declaration=True)


def resolve_dynamic_script(slug):
    """Find the project folder, python executable, and refresh script (main.py/refresh_dashboard.py).
    Works for both native dynamic projects and pre-existing/external dynamic dashboards."""
    # 1. Native dynamic project
    dyn_dir = (DYNAMIC_ROOT / slug).resolve()
    if dyn_dir.is_dir():
        script = dyn_dir / "main.py"
        if not script.is_file():
            script = dyn_dir / "refresh_dashboard.py"
        py = dyn_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not py.is_file():
            py = Path(sys.executable)
        return dyn_dir, script, py

    # 2. Pre-existing / external dashboard - Check Task Scheduler first!
    t_name, xml_root = query_task_scheduler_info(slug)
    if xml_root is not None:
        try:
            NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
            for exec_node in xml_root.findall(f".//{{{NS}}}Exec"):
                cmd = exec_node.find(f"{{{NS}}}Command")
                args = exec_node.find(f"{{{NS}}}Arguments")
                wdir = exec_node.find(f"{{{NS}}}WorkingDirectory")
                py_path = Path(cmd.text.strip().strip('"')) if cmd is not None and cmd.text else Path(sys.executable)
                work_dir = Path(wdir.text.strip().strip('"')) if wdir is not None and wdir.text else None
                script_path = None
                if args is not None and args.text:
                    script_path = Path(args.text.strip().strip('"'))
                if script_path and not script_path.is_absolute() and work_dir:
                    script_path = work_dir / script_path
                if script_path and script_path.is_file():
                    work_dir = work_dir or script_path.parent
                    return work_dir.resolve(), script_path.resolve(), py_path.resolve()
        except Exception:
            pass

    # 3. Pre-existing dashboard from file metadata
    meta = load_meta()
    linked = meta.get(slug)
    if linked and linked.get("link"):
        target_file = get_existing_dashboard_file(slug, linked)
        target_dir = target_file.parent.resolve()
        script = target_dir / "main.py"
        if not script.is_file():
            script = target_dir / "refresh_dashboard.py"
        py = target_dir / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not py.is_file():
            py = Path(sys.executable)
        return target_dir, script, py

    return dyn_dir, dyn_dir / "main.py", Path(sys.executable)


def build_refresh_task_xml(slug, rec, settings):
    """Build a Task Scheduler XML task. Schedule times use this PC's local clock."""
    import xml.etree.ElementTree as ET
    project, script, py = resolve_dynamic_script(slug)
    if not script.is_file():
        raise UserError("This dashboard has no main.py at its root. Add main.py first.")
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
    elif freq in ("weekly", "weekdays"):
        trigger=el(triggers,"CalendarTrigger"); el(trigger,"StartBoundary",start_iso); el(trigger,"Enabled","true")
        by=el(trigger,"ScheduleByWeek"); el(by,"WeeksInterval","1"); days=el(by,"DaysOfWeek")
        daymap={"Mon":"Monday","Tue":"Tuesday","Wed":"Wednesday","Thu":"Thursday","Fri":"Friday","Sat":"Saturday","Sun":"Sunday"}
        if freq == "weekdays":
            selected = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        else:
            selected = settings.get("days", ["Mon", "Tue", "Wed", "Thu", "Fri"])
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
    return ET.tostring(task, encoding="utf-16", xml_declaration=True)


def register_refresh_task(slug, rec, settings):
    if os.name != "nt":
        raise UserError("Windows Task Scheduler is only available on Windows. Schedule settings were not registered on this computer.", 501)
    
    t_name, xml_root = query_task_scheduler_info(slug, rec)
    if xml_root is not None and t_name:
        # Existing Windows task: update triggers directly in-place without touching actions or principals
        xml_data = apply_triggers_to_task_xml(xml_root, settings)
        target_name = t_name
    else:
        # New task: build XML from scratch
        xml_data = build_refresh_task_xml(slug, rec, settings)
        target_name = refresh_task_name(slug)

    task_file = TMP / ("refresh-" + re.sub(r'[^a-zA-Z0-9_-]', '_', str(slug)) + "-" + secrets.token_hex(4) + ".xml")
    task_file.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(xml_data, str):
        xml_data = xml_data.encode("utf-16")
    task_file.write_bytes(xml_data)

    try:
        result = subprocess.run(["schtasks.exe", "/Create", "/TN", target_name, "/XML", str(task_file), "/F"],
                                capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            err_msg = (result.stderr or result.stdout or "").strip()
            raise UserError(f"Windows Task Scheduler could not update task '{target_name}': {err_msg[:350]}", 500)
        # Ensure task is enabled
        subprocess.run(["schtasks.exe", "/Change", "/TN", target_name, "/ENABLE"],
                       capture_output=True, text=True, timeout=10, check=False)
    finally:
        task_file.unlink(missing_ok=True)

    rec["refresh"] = {
        **settings,
        "enabled": True,
        "task_name": target_name,
        "updated": datetime.now().isoformat(timespec="seconds"),
        "last_status": "scheduled"
    }
    return rec["refresh"]


def delete_refresh_task(slug, rec=None, is_external=False):
    if os.name == "nt":
        t_name, _ = query_task_scheduler_info(slug, rec)
        if t_name:
            if is_external:
                subprocess.run(["schtasks.exe", "/Change", "/TN", t_name, "/DISABLE"],
                               capture_output=True, text=True, timeout=15, check=False)
            else:
                subprocess.run(["schtasks.exe", "/Delete", "/TN", t_name, "/F"],
                               capture_output=True, text=True, timeout=15, check=False)
        else:
            for cand in get_task_candidates(slug):
                if is_external:
                    subprocess.run(["schtasks.exe", "/Change", "/TN", cand, "/DISABLE"],
                                   capture_output=True, text=True, timeout=15, check=False)
                else:
                    subprocess.run(["schtasks.exe", "/Delete", "/TN", cand, "/F"],
                                   capture_output=True, text=True, timeout=15, check=False)


# ---------------------------------------------------------------- dashboard snapshots
# The master dashboard shows a picture of each dashboard's front page instead of loading the
# whole dashboard in every card. HTML Drop takes the pictures with the PC's Edge or Chrome
# (one at a time, in the background), keeps them in data/thumbs/ and retakes them every 6 hours.

THUMBS = DATA / "thumbs"
THUMB_MAX_AGE = 6 * 3600
THUMB_JOBS = []                  # urls waiting for a picture, oldest first
THUMB_CV = threading.Condition()
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]


def thumb_file(url):
    return THUMBS / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:20] + ".png")


def thumb_url_allowed(url, request_host):
    """Only pictures of dashboards on this PC or the office dashboard PC, never other sites."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    allowed = {"127.0.0.1", "localhost", EXISTING_HOST, request_host.split(":")[0].lower()}
    try:
        allowed.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    return u.hostname.lower() in allowed


def queue_thumb(url):
    with THUMB_CV:
        if url not in THUMB_JOBS:
            THUMB_JOBS.append(url)
            THUMB_CV.notify()


THUMB_CHECKED = {}               # url -> when we last asked whether its dashboard changed


def page_changed_at(url):
    """When the dashboard behind url last changed (unix time), or None if unknown.
    HTML Drop's own pages: their last upload / Replace / refresh. Dashboards on their own
    server: the Last-Modified time that server reports (a HEAD request, nothing downloaded)."""
    m = re.match(r"^/s/([^/]+)/", urlparse(url).path)
    if m:
        record = load_meta().get(unquote(m.group(1)))
        if record and record.get("updated"):
            try:
                return datetime.fromisoformat(record["updated"]).timestamp()
            except ValueError:
                return None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=5) as resp:
            stamp = resp.headers.get("Last-Modified")
        if stamp:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(stamp).timestamp()
    except Exception:
        pass
    return None


STATUS_CACHE = {}                # url -> (checked at, {"up": bool, "changed": iso or ""})


def dashboard_status(url):
    """Is the dashboard answering, and when did it last change? HTML Drop's own pages are
    looked up directly; other dashboards get a HEAD request (nothing downloaded).
    Remembered for 2 minutes so the dashboard servers aren't asked on every page load."""
    hit = STATUS_CACHE.get(url)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    m = re.match(r"^/s/([^/]+)/", urlparse(url).path)
    slug = unquote(m.group(1)) if m else ""
    record = load_meta().get(slug) if m else None
    project = load_dynamic_meta().get(slug) if m and not record else None
    if record and not record.get("link"):
        result = {"up": not record.get("disabled") and not record.get("deleted"),
                  "changed": record.get("updated", "")}
    elif project:
        result = {"up": not project.get("disabled") and not project.get("deleted"),
                  "changed": project.get("updated", "")}
    else:
        result = {"up": False, "changed": ""}
        try:
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=4)
            except urllib.error.HTTPError as e:
                if e.code not in (405, 501):  # this server can't answer HEAD: ask for the first byte instead
                    raise
                resp = urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=0-0"}), timeout=4)
            with resp:
                result["up"] = resp.status < 400
                stamp = resp.headers.get("Last-Modified")
            if stamp:
                from email.utils import parsedate_to_datetime
                result["changed"] = parsedate_to_datetime(stamp).astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
        except Exception:
            pass
    STATUS_CACHE[url] = (time.time(), result)
    return result


def check_thumb(url, taken_at):
    """Retake the picture if its dashboard changed after the picture was taken."""
    changed = page_changed_at(url)
    if changed and changed > taken_at:
        queue_thumb(url)


def thumb_worker():
    browser = next((b for b in BROWSERS if os.path.isfile(b)), None)
    while True:
        with THUMB_CV:
            while not THUMB_JOBS:
                THUMB_CV.wait()
            url = THUMB_JOBS[0]
        out = thumb_file(url)
        try:
            if browser:
                THUMBS.mkdir(parents=True, exist_ok=True)
                tmp = out.with_name(out.stem + ".new.png")
                tmp.unlink(missing_ok=True)
                profile = THUMBS / ".browser" / secrets.token_hex(4)  # its own profile: runs can't collide
                # A 1280x800 page at half size: a sharp 640x400 picture of the dashboard's top.
                subprocess.Popen([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
                                  "--no-first-run", "--window-size=1280,800", "--force-device-scale-factor=0.5",
                                  "--virtual-time-budget=15000", f"--user-data-dir={profile}",
                                  f"--screenshot={tmp}", url],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                # msedge.exe hands the work to a background browser and returns at once, so wait
                # for the picture itself: it exists and has stopped growing.
                deadline, last = time.time() + 90, -1
                while time.time() < deadline:
                    time.sleep(1)
                    size = tmp.stat().st_size if tmp.is_file() else -1
                    if size > 2000 and size == last:
                        break
                    last = size
                time.sleep(2)  # let the browser close before its profile is removed
                if tmp.is_file() and tmp.stat().st_size > 2000:
                    os.replace(tmp, out)
                else:
                    tmp.unlink(missing_ok=True)
                shutil.rmtree(profile, ignore_errors=True)
        except Exception:
            traceback.print_exc()
        finally:
            with THUMB_CV:
                if url in THUMB_JOBS:
                    THUMB_JOBS.remove(url)


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
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
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
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            if path in ("/", "/index.html"):
                return self.send_body(PORTAL_FILE.read_bytes(), "text/html; charset=utf-8")
            if path in ("/Master_dashboard.html", "/master", "/master.html", "/Master_Dashboard.html"):
                master_file = ROOT / "Master_dashboard.html"
                if master_file.is_file():
                    return self.send_body(master_file.read_bytes(), "text/html; charset=utf-8", cors=True)
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
                replace_fn = """async function replaceProjectZip(slug,input){const file=input.files&&input.files[0];if(!file)return;if(!confirm('Replace the ZIP for '+slug+'? The dashboard will restart with the replacement files.')){input.value='';return}try{let d;try{d=await api('/api/dynamic/replace?slug='+encodeURIComponent(slug),{method:'POST',headers:{'Content-Type':'application/zip'},body:file});}catch(err){if(err.message&&err.message.includes('HTML filename mismatch')&&confirm('⚠️ HTML Filename Warning:\\n\\n'+err.message+'\\n\\nDo you want to proceed and replace anyway?')){d=await api('/api/dynamic/replace?force=1&slug='+encodeURIComponent(slug),{method:'POST',headers:{'Content-Type':'application/zip'},body:file});}else{throw err;}}alert(d.message||'ZIP replaced. Restart started automatically.');await loadProjects();setTimeout(loadProjects,1800);setTimeout(loadProjects,6000)}catch(e){alert('Could not replace ZIP: '+e.message)}finally{input.value=''}}
"""
                if marker in page and 'async function replaceProjectZip' not in page:
                    page = page.replace(marker, replace_fn + marker)
                return self.send_body(page.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/me":
                m_url = CONFIG.get("master_dashboard_url", DEFAULT_MASTER_URL)
                if not m_url or "172.29.65.188" in str(m_url):
                    m_url = "/Master_dashboard.html"
                return self.send_json({"user": self.current_user(),
                                       "allow_signup": bool(CONFIG.get("allow_signup", True)),
                                       "master_url": m_url,
                                       "members": member_list()})
            if path == "/api/sites":
                users = load_json(USERS_FILE)
                user = self.current_user()
                items = []
                for s, r in load_meta().items():
                    if r.get("deleted"):
                        continue
                    # These existing external dashboards are presented in Dynamic projects
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
                    port_match = re.search(r":(\d+)(?:/|$)", urlparse(url).netloc or url)
                    _p_dir, _p_script, _ = resolve_dynamic_script(slug)
                    has_script = _p_script.is_file()
                    ext_refresh = rec.get("refresh", {})
                    _found_task_name, _found_task_xml = query_task_scheduler_info(slug, rec)
                    if _found_task_name:
                        extracted = extract_trigger_info_from_xml(_found_task_xml)
                        if not ext_refresh or not ext_refresh.get("enabled"):
                            ext_refresh = {
                                "enabled": True,
                                "task_name": _found_task_name,
                                "frequency": extracted.get("frequency", "daily"),
                                "time": extracted.get("time", "active"),
                                **extracted
                            }
                    ext_entry_html = Path(rec.get("file") or "").name if rec.get("file") else unquote(urlparse(url).path).rsplit("/", 1)[-1]
                    items.append({
                        "slug": slug, "title": rec.get("title") or slug, "owner": ", ".join(
                            display_name(users, x) for x in owners_of(rec)
                        ) or rec.get("owner", ""),
                        "created": rec.get("created", ""), "updated": rec.get("updated", ""),
                        "port": port_match.group(1) if port_match else "",
                        "status": "On its own server", "url": url, "external": True,
                        "disabled": bool(rec.get("disabled")),
                        "entry_html": ext_entry_html,
                        "refresh": ext_refresh, "refresh_available": has_script or bool(_found_task_name),
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
            if path == "/api/status":
                # For the master dashboard's sidebar: which dashboards answer, and when each changed.
                try:
                    urls = json.loads(parse_qs(urlparse(self.path).query).get("urls", ["[]"])[0])[:200]
                except ValueError:
                    raise UserError("Bad list of links.")
                host = self.headers.get("Host") or ""
                urls = [u for u in urls if isinstance(u, str) and thumb_url_allowed(u, host)]
                results = {}
                workers = [threading.Thread(target=lambda u=u: results.__setitem__(u, dashboard_status(u)))
                           for u in dict.fromkeys(urls)]
                for t in workers:
                    t.start()
                for t in workers:
                    t.join(6)
                return self.send_json(results, cors=True)
            if path == "/api/thumb":
                # A saved picture of a dashboard's front page; 404 (and a picture is queued) if
                # there is none yet, so the card shows its icon until the picture is ready.
                url = parse_qs(urlparse(self.path).query).get("url", [""])[0]
                if not thumb_url_allowed(url, self.headers.get("Host") or ""):
                    raise UserError("Not a dashboard on this network.", 400)
                f = thumb_file(url)
                if f.is_file():
                    taken = f.stat().st_mtime
                    if time.time() - taken > THUMB_MAX_AGE:
                        queue_thumb(url)
                    elif time.time() - THUMB_CHECKED.get(url, 0) > 60:
                        # Changed since the picture? Checked in the background, at most once a minute.
                        THUMB_CHECKED[url] = time.time()
                        threading.Thread(target=check_thumb, args=(url, taken), daemon=True).start()
                    return self.send_body(f.read_bytes(), "image/png", cors=True)
                queue_thumb(url)
                return self.send_json({"error": "No picture yet."}, 404, cors=True)
            if path == "/api/titles":
                return self.send_titles()
            if path == "/api/categories":
                return self.send_json(load_categories(), cors=True)
            if path in ("/api/categories/delete", "/api/categories/del"):
                key = str(q.get("key", [""])[0] or q.get("category", [""])[0]).strip().lower()
                delete_category(key)
                return self.send_json({"ok": True, "categories": load_categories()}, cors=True)
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
            self.send_json({"error": str(e)}, e.status, cors=True)

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
        main_port = int(CONFIG.get("port", 8150))
        for rec in load_dynamic_meta().values():
            if rec.get("show_on_master") and dynamic_running(rec):
                u_str = rec.get("url") or f"/s/{rec['slug']}/"
                if u_str.startswith("/"):
                    u_str = f"http://{host}:{main_port}{u_str}"
                items.append({
                    "id": f"dynamic-{rec['slug']}", "url": u_str,
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
        target_slug, record = get_site_record(slug)
        is_dynamic = False
        if not record or record.get("deleted"):
            dyn_slug, dyn_rec = get_dynamic_record(slug)
            if dyn_rec and not dyn_rec.get("deleted"):
                record = dyn_rec
                slug = dyn_slug
                is_dynamic = True
            else:
                return self.send_error(404, "No page with that name")
        else:
            slug = target_slug

        if record.get("disabled") and not record.get("link"):
            return self.send_body(UNAVAILABLE_PAGE.encode("utf-8"), "text/html; charset=utf-8", 503)
        if record.get("link"):
            return self.redirect(record["link"])
        if rest is None:
            return self.redirect(f"/s/{quote(slug)}/")
        entry_file = record.get("entry") or "index.html"
        if rest == "/" and entry_file != "index.html":
            return self.redirect(f"/s/{quote(slug)}/{quote(entry_file)}")
        base = (DYNAMIC_ROOT / slug).resolve() if is_dynamic else (SITES / slug).resolve()
        target = (base / rest.lstrip("/")).resolve()
        if not target.is_relative_to(base):
            return self.send_error(403)
        if target.is_dir():
            target = target / entry_file
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
            if self.headers.get("X-HD") != "1" and u.path not in ("/api/dashboard/section", "/api/categories/add", "/api/categories/delete", "/api/categories/del"):
                raise UserError("Missing request header.", 403)

            if u.path in ("/api/categories/delete", "/api/categories/del"):
                data = self.read_json()
                key = str(data.get("key") or data.get("category") or "").strip().lower()
                if not key:
                    raise UserError("Section key is required.", 400)
                if key in DEFAULT_CATEGORIES:
                    raise UserError("Default system sections cannot be deleted.", 400)
                delete_category(key)
                return self.send_json({"ok": True, "categories": load_categories()}, cors=True)

            if u.path == "/api/categories/add":
                data = self.read_json()
                label = str(data.get("label") or data.get("name") or "").strip()[:60]
                if not label:
                    raise UserError("Section name is required.", 400)
                key = str(data.get("key") or "").strip().lower()
                if not key:
                    key = re.sub(r"[^a-z0-9_-]", "", label.lower().replace(" ", "-"))[:30]
                if not key:
                    key = f"cat-{int(time.time())}"
                color = str(data.get("color") or "").strip()[:20] or "#818cf8"
                add_category(key, label, color)
                return self.send_json({"ok": True, "key": key, "label": label, "color": color}, cors=True)

            if u.path == "/api/dashboard/section":
                data = self.read_json()
                raw_slug = str(data.get("slug") or data.get("id") or "").strip()
                slug = raw_slug
                if slug.startswith("drop-"):
                    slug = slug[5:]
                if slug.startswith("dynamic-"):
                    slug = slug[8:]
                cat = str(data.get("category") or data.get("section") or "").strip()[:40]
                if not slug or not cat:
                    raise UserError("Missing slug or category.", 400)
                
                updated = False
                with lock:
                    meta = load_meta()
                    rec_key = None
                    if slug in meta:
                        rec_key = slug
                    elif raw_slug in meta:
                        rec_key = raw_slug
                    else:
                        for k, r in meta.items():
                            if r.get("hub", {}).get("legacy_id") in (raw_slug, slug) or k.lower() == slug.lower():
                                rec_key = k
                                break
                    if rec_key:
                        meta[rec_key]["hub"] = {**hub_of(meta[rec_key]), "category": cat, "show": True}
                        save_meta(meta)
                        updated = True
                        
                    dyn_meta = load_dynamic_meta()
                    dyn_key = None
                    if slug in dyn_meta:
                        dyn_key = slug
                    elif raw_slug in dyn_meta:
                        dyn_key = raw_slug
                    if dyn_key:
                        dyn_meta[dyn_key]["category"] = cat
                        dyn_meta[dyn_key]["show_on_master"] = True
                        save_dynamic_meta(dyn_meta)
                        updated = True
                        
                return self.send_json({"ok": True, "slug": slug, "category": cat, "updated": updated}, cors=True)

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
                if hub_choice and "category" in q and q["category"]:
                    hub_choice["category"] = q["category"].strip()[:40]
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
                main_port = int(CONFIG.get("port", 8150))
                port = main_port if launch_type == "static" else allocate_dynamic_port(meta)
                host = (self.headers.get("Host") or "localhost").split(":")[0]
                url = f"/s/{slug}/" if launch_type == "static" else f"http://{host}:{port}/"
                rec = {"slug": slug, "title": title, "owner": user["username"],
                       "created": datetime.now().isoformat(timespec="seconds"),
                       "updated": datetime.now().isoformat(timespec="seconds"),
                       "port": port, "status": "preparing", "entry": detected_entry, "launch_type": launch_type, "pid": None,
                       "url": url,
                       "show_on_master": q.get("placement", "off") in ("general", "all") if "placement" in q else q.get("show") == "1",
                       "master_scope": q.get("placement", "all") if q.get("placement") in ("general", "all") else "all",
                       "category": q.get("category", "other")[:40],
                       "message": ("Validated dashboard files. Running on port 8150." if launch_type == "static" else "Validated Python project. Preparing environment and starting automatically.")}
                meta[slug] = rec
                save_dynamic_meta(meta)
                threading.Thread(target=start_dynamic_worker, args=(slug,), daemon=True).start()
                self.log_message("%s uploaded dynamic project %s; auto-start queued", user["username"], slug)
                return self.send_json(dynamic_public(rec, include_path=user.get("role") == "admin"), 201)
            if u.path == "/api/dynamic/replace-zip":
                user = self.require_user()
                slug = q.get("slug", "").strip().lower()
                if not SLUG_RE.match(slug):
                    raise UserError("Invalid project link name.")
                body = self.read_body()
                all_meta = load_meta()
                linked = all_meta.get(slug)
                if not linked or not linked.get("link") or linked.get("deleted"):
                    raise UserError("This is not a registered existing dashboard.", 404)
                if not can_manage(user, linked):
                    raise UserError("Only the dashboard owner or an admin can change its ZIP.", 403)
                target_file = get_existing_dashboard_file(slug, linked)
                target_dir = target_file.parent.resolve()
                linked["file"] = str(target_file)
                expected_html = target_file.name.lower()
                force_upload = q.get("force") == "1"
                try:
                    zf = zipfile.ZipFile(io.BytesIO(body))
                    infos = [x for x in zf.infolist() if not x.is_dir()]
                    if not infos:
                        raise UserError("The ZIP contains no files.")
                    names = [Path(x.filename.replace("\\", "/")) for x in infos]
                    if any(n.is_absolute() or ".." in n.parts for n in names):
                        raise UserError("ZIP contains unsafe file paths.")

                    # Validate HTML file name matches the older dashboard file
                    zip_html_files = [n.name for n in names if n.suffix.lower() in (".html", ".htm")]
                    if expected_html and expected_html.endswith((".html", ".htm")):
                        if not any(h.lower() == expected_html for h in zip_html_files) and not force_upload:
                            found_str = ", ".join(zip_html_files) if zip_html_files else "none found"
                            raise UserError(f"HTML filename mismatch: The uploaded ZIP does not contain '{target_file.name}' (HTML files in ZIP: {found_str}).", 409)

                    # If all files sit inside one wrapper folder, remove that common folder.
                    first_parts = [n.parts for n in names]
                    strip_root = (len(first_parts[0]) > 1 and
                                  all(len(parts) > 1 and parts[0] == first_parts[0][0]
                                      for parts in first_parts))
                    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    backup_root = HISTORY / slug / f"{stamp}_zip_backup"
                    written = 0
                    for info, name in zip(infos, names):
                        parts = name.parts[1:] if strip_root else name.parts
                        if not parts:
                            continue
                        dest = (target_dir.joinpath(*parts)).resolve()
                        if dest != target_dir and target_dir not in dest.parents:
                            raise UserError("ZIP contains a path outside the dashboard folder.")
                        if dest.exists() and dest.is_file():
                            rel = dest.relative_to(target_dir)
                            backup = backup_root / rel
                            backup.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(dest, backup)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        tmp = dest.with_name(dest.name + ".htmldrop-new")
                        tmp.write_bytes(zf.read(info))
                        os.replace(tmp, dest)
                        written += 1
                    zf.close()
                except zipfile.BadZipFile:
                    raise UserError("The uploaded file is not a valid ZIP.")
                except OSError as exc:
                    raise UserError(f"Could not update the existing dashboard folder: {exc}")
                linked["updated"] = datetime.now().isoformat(timespec="seconds")
                all_meta[slug] = linked
                save_meta(all_meta)
                self.log_message("%s updated existing dashboard %s from ZIP (%s files) into %s",
                                 user["username"], slug, written, target_dir)
                return self.send_json({"ok": True, "message":
                    f"Updated {written} files in '{target_dir}'. Existing files not in the ZIP, cron scripts, URL and port were left unchanged. Backups: {backup_root}"})
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
                    force_upload = q.get("force") == "1"
                    older_entry = (rec.get("entry") or "index.html").strip()
                    expected_html = Path(older_entry).name.lower()
                    if expected_html and expected_html.endswith((".html", ".htm")) and not force_upload:
                        staged_html = [p.name for p in staged_path.rglob("*") if p.is_file() and p.suffix.lower() in (".html", ".htm") and ".venv" not in p.parts]
                        if not any(h.lower() == expected_html for h in staged_html):
                            shutil.rmtree(staged_path, ignore_errors=True)
                            found_str = ", ".join(staged_html[:10]) if staged_html else "none found"
                            raise UserError(f"HTML filename mismatch: The uploaded ZIP does not contain '{expected_html}' (HTML files in ZIP: {found_str}).", 409)

                    if rec.get("refresh", {}).get("enabled") and not ((staged_path / "main.py").is_file() or (staged_path / "refresh_dashboard.py").is_file()):
                        shutil.rmtree(staged_path, ignore_errors=True)
                        raise UserError("Replacement ZIP is missing main.py, but this project has an active refresh schedule. The existing project and schedule were left unchanged.", 409)
                    live_path = DYNAMIC_ROOT / slug
                    stop_dynamic_process(slug, rec)
                    live_path.mkdir(parents=True, exist_ok=True)
                    # Clean out old dashboard files except .venv and logs
                    for item in list(live_path.iterdir()):
                        if item.name in (".venv", "logs", "__pycache__"):
                            continue
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            try:
                                item.unlink(missing_ok=True)
                            except Exception:
                                pass
                    # Copy new files from staged_path into live_path
                    for item in list(staged_path.iterdir()):
                        dest_item = live_path / item.name
                        if item.is_dir():
                            shutil.copytree(item, dest_item, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, dest_item)
                    shutil.rmtree(staged_path, ignore_errors=True)
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
                slug = q.get("slug", "").strip()
                meta = load_dynamic_meta()
                target_slug, rec = get_dynamic_record(slug, meta)
                is_ext = False
                static_meta = None
                if not rec:
                    static_meta = load_meta()
                    target_slug, rec = get_site_record(slug, static_meta)
                    if rec and rec.get("link") and is_migration_target(target_slug, rec) and can_manage(user, rec):
                        is_ext = True
                if not rec or (not is_ext and not dynamic_owner_allowed(user, rec)):
                    raise UserError("Project not found or access denied.", 404)
                data = self.read_json()
                if not data.get("enabled"):
                    delete_refresh_task(target_slug, rec, is_external=is_ext)
                    t_name = (rec.get("refresh") or {}).get("task_name") or refresh_task_name(target_slug)
                    rec["refresh"] = {"enabled": False, "task_name": t_name, "updated": datetime.now().isoformat(timespec="seconds")}
                    if is_ext:
                        save_meta(static_meta)
                    else:
                        save_dynamic_meta(meta)
                    return self.send_json({"ok": True, "refresh": rec["refresh"], "message": "Automatic refresh schedule disabled."})
                settings={"frequency":str(data.get("frequency","daily")),"time":str(data.get("time","06:00")),
                          "hours":int(data.get("hours",1)),"days_interval":int(data.get("days_interval",1)),
                          "days":data.get("days",["Mon","Tue","Wed","Thu","Fri"]),"catch_up":True,"wake_to_run":True}
                if settings["frequency"] not in ("daily", "weekdays", "hourly", "weekly", "custom"):
                    raise UserError("Invalid refresh frequency.")
                reg_info = register_refresh_task(target_slug, rec, settings)
                rec["updated"] = datetime.now().isoformat(timespec="seconds")
                if is_ext:
                    save_meta(static_meta)
                else:
                    save_dynamic_meta(meta)
                self.log_message("%s configured refresh task for %s", user["username"], target_slug)
                return self.send_json({"ok": True, "refresh": rec["refresh"], "message": f"Schedule updated in Windows Task Scheduler for '{reg_info.get('task_name')}'."}, 201)
            if u.path == "/api/dynamic/refresh-now":
                user = self.require_user()
                slug = q.get("slug", "").strip()
                meta = load_dynamic_meta()
                target_slug, rec = get_dynamic_record(slug, meta)
                is_ext = False
                if not rec:
                    static_meta = load_meta()
                    target_slug, rec = get_site_record(slug, static_meta)
                    if rec and rec.get("link") and is_migration_target(target_slug, rec) and can_manage(user, rec):
                        is_ext = True
                if not rec or (not is_ext and not dynamic_owner_allowed(user, rec)):
                    raise UserError("Project not found or access denied.", 404)
                if os.name != "nt":
                    raise UserError("Run-now is supported on the Windows host only.", 501)
                # 1. Run through Windows Task Scheduler directly
                t_name, _ = query_task_scheduler_info(target_slug, rec)
                if t_name:
                    res = subprocess.run(["schtasks.exe", "/Run", "/TN", t_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        self.log_message("%s triggered Windows Task Scheduler task %s", user["username"], t_name)
                        return self.send_json({"ok": True, "message": f"Started refresh task '{t_name}' in Windows Task Scheduler."}, 202)
                    else:
                        err_msg = (res.stderr or res.stdout or "").strip()
                        self.log_message("Warning: schtasks /Run failed for %s: %s", t_name, err_msg)

                # 2. If no task was registered yet or schtasks failed, resolve script and run
                proj_dir, script, py = resolve_dynamic_script(target_slug)
                if not script.is_file():
                    raise UserError(f"Task Scheduler task was not found and project has no main.py.")

                logdir = DYNAMIC_LOG_ROOT / target_slug
                logdir.mkdir(parents=True, exist_ok=True)
                log = (logdir / "refresh.log").open("a", encoding="utf-8")
                log.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] Manual refresh started\n")
                log.flush()
                subprocess.Popen([str(py), str(script)], cwd=str(proj_dir), stdout=log, stderr=subprocess.STDOUT,
                                 creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0))
                return self.send_json({"ok": True, "message": "Refresh started. See project logs for results."}, 202)

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
            if u.path in ("/api/page", "/api/page/update"):
                data = self.read_json()
                slug = q.get("slug") or data.get("slug", "")
                try:
                    user, cookie = self.acting_user()
                except Exception:
                    user, cookie = (self.current_user() or {"username": "office", "role": "admin"}), None
                rec = update_page(slug, user, data)
                self.log_message("%s edited %s", user.get("username", "user"), slug)
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
            self.send_json({"error": str(e)}, e.status, cors=True)
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
    threading.Thread(target=thumb_worker, daemon=True).start()
    load_sessions()
    port = int(CONFIG.get("port", 8150))
    try:
        httpd = ExclusiveServer(("0.0.0.0", port), Handler)
    except OSError:
        sys.exit(f"Port {port} is already in use by another program. "
                 f"Change \"port\" in config.json and try again.")
    host = socket.gethostname()
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        ip = "127.0.0.1"
    print(f"HTML Drop is running on your network:\n"
          f"  http://{ip}:{port}/\n"
          f"  http://{host}:{port}/\n"
          f"  http://localhost:{port}/\n"
          f"Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
