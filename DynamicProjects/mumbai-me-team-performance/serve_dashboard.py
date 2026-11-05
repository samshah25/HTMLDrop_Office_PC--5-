"""Login server for the Mumbai ME Team Performance dashboard (2 Nov 2026).

Each login sees one page only:
  page "full"       -> Mumbai ME Team Performance.html (the ME head's whole dashboard)
  page "<code>"     -> manager_pages\\<code>.html (one manager's line only; built by main.py / build_review.py)
The logins, their names and pages, and salted password hashes are in logins.json next to this file. Passwords are never
stored in clear; set or change one with:
    python serve_dashboard.py --set-password <login id> <new password>
List the logins and check their pages exist:
    python serve_dashboard.py --list
Run the server (Ctrl+C stops it):
    python serve_dashboard.py              (port from logins.json, default 8160)
    python serve_dashboard.py --port 8170
    python serve_dashboard.py --local      (a test on this PC only: http://localhost:8160/, not reachable from other PCs)

Only four addresses answer: / (sign-in), /login, /dashboard (the signed-in person's page) and /logout. No file in this
folder can be fetched by its name, so logins.json, the pages and environment.py are never served directly.

Behind HTML Drop (5 Nov 2026: the dashboard keeps its old link http://<PC>:8150/s/mumbai-me-team-performance/):
    python serve_dashboard.py --behind-htmldrop     (listens on this PC only; start_server.bat does this)
HTML Drop hands every request under /s/mumbai-me-team-performance to this server (htmldrop_login_proxy.py, added to
HTML Drop), with the headers X-Forwarded-Prefix (the link's path) and X-Forwarded-For (the viewer's address). Those two
headers are believed only from this PC itself.
Five wrong passwords for a login (or twenty from one PC) lock it for 15 minutes. A sign-in lasts 12 hours (logins.json:
session_hours) or until the server restarts. Every sign-in, failure and page view is written to serve_log.txt.
Needs Python 3.8+ and nothing else.
"""
import datetime
import gzip
import hashlib
import hmac
import html
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "logins.json")
FULL = os.path.join(HERE, "Mumbai ME Team Performance.html")
MGR_DIR = os.path.join(HERE, "manager_pages")
LOG = os.path.join(HERE, "serve_log.txt")
ITER = 200_000
MAX_FAIL, MAX_FAIL_PC, LOCK_MIN = 5, 20, 15   # wrong passwords before a lock: per login, per PC (several people may share one)
COOKIE = "jdme_session"

SESS = {}    # token -> (login, expires at)
FAILS = {}   # "u:<login>" or "ip:<address>" -> [failure times]
CACHE = {}   # (path, mtime, name, gzip) -> bytes
LOCK = threading.Lock()


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_conf():
    with open(CONF, encoding="utf-8") as f:
        return json.load(f)


def save_conf(c):
    tmp = CONF + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CONF)


def phash(pw, salt, it=ITER):
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), it).hex()


def page_path(page):
    if page == "full":
        return FULL
    if not page or not page.isalnum():
        return None
    return os.path.join(MGR_DIR, page + ".html")


def locked(keys):
    now = time.time()
    with LOCK:
        for k in keys:
            ts = [t for t in FAILS.get(k, []) if now - t < LOCK_MIN * 60]
            FAILS[k] = ts
            if len(ts) >= (MAX_FAIL_PC if k.startswith("ip:") else MAX_FAIL):
                return int((LOCK_MIN * 60 - (now - ts[0])) // 60) + 1
    return 0


def failed(keys):
    with LOCK:
        for k in keys:
            FAILS.setdefault(k, []).append(time.time())


SIGNIN = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · ME team, Mumbai</title><style>
:root{--navy:#0B1B3F;--ink:#14213D;--mu:#5B6475;--line:#D9DEE7;--bg:#F4F6FA;--red:#B8322A}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.card{width:min(360px,calc(100vw - 32px));background:#fff;border:1px solid var(--line);border-top:4px solid var(--navy);border-radius:10px;padding:26px 26px 22px}
h1{font-size:19px;margin:0 0 4px}p.s{margin:0 0 18px;color:var(--mu);font-size:13px}label{display:block;font-size:13px;font-weight:600;margin:12px 0 5px}
input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:6px;font:inherit}input:focus{outline:2px solid #2a78d6;outline-offset:1px;border-color:#2a78d6}
button{margin-top:18px;width:100%;padding:10px;border:0;border-radius:6px;background:var(--navy);color:#fff;font:inherit;font-weight:600;cursor:pointer}
.err{margin:12px 0 0;color:var(--red);font-size:13px}.ft{margin:16px 0 0;color:var(--mu);font-size:12px}
</style></head><body><form class="card" method="post" action="%BASE%/login" autocomplete="on"><h1>ME team, Mumbai</h1><p class="s">Sign in with the login ID and password you were given.</p>
<label for="u">Login ID</label><input id="u" name="u" autocomplete="username" autofocus required>
<label for="p">Password</label><input id="p" name="p" type="password" autocomplete="current-password" required>
%ERR%<button type="submit">Sign in</button><p class="ft">For a forgotten password, ask Kushal Sharma.</p></form></body></html>"""

BAR = ('<div style="position:fixed;right:12px;bottom:12px;z-index:2147483000;background:#fff;color:#14213D;border:1px solid #D9DEE7;'
       'border-radius:999px;padding:5px 12px;font:12px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 1px 4px rgba(20,33,61,.12)" '
       'class="jd-signbar">Signed in: <b>%NAME%</b> · <a href="%BASE%/logout" style="color:#1F5FAD">Sign out</a></div>'
       '<style>@media print{.jd-signbar{display:none}}</style>')


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "JD"
    sys_version = ""

    def log_message(self, fmt, *args):   # the standard request lines are left out; sign-ins and page views are logged below
        return

    def from_this_pc(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def ip(self):
        """the viewer's address; behind HTML Drop (a request from this PC carrying X-Forwarded-For) the address HTML Drop saw"""
        fwd = self.headers.get("X-Forwarded-For", "") if self.from_this_pc() else ""
        return fwd.split(",")[0].strip()[:64] or self.client_address[0]

    def base(self):
        """the link's path in front of /, /login, /dashboard, /logout: '' when opened directly, '/s/<link name>' behind HTML Drop"""
        p = self.headers.get("X-Forwarded-Prefix", "").rstrip("/") if self.from_this_pc() else ""
        return p if p and len(p) <= 100 and all(c.isalnum() or c in "/-_" for c in p) and p.startswith("/") else ""

    def cookie(self, value, age):
        return f"{COOKIE}={value}; Path={self.base() or '/'}; Max-Age={age}; HttpOnly; SameSite=Strict"

    def headers_common(self, ctype="text/html; charset=utf-8"):
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")

    def send_html(self, code, body, cookie=None):
        b = body.encode("utf-8")
        self.send_response(code)
        self.headers_common()
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, to, cookie=None):
        self.send_response(303)
        self.send_header("Location", to)
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def session(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE and v:
                with LOCK:
                    s = SESS.get(v)
                    if s and s[1] > time.time():
                        return v, s[0]
                    SESS.pop(v, None)
        return None, None

    def signin(self, err=""):
        e = f'<p class="err" role="alert">{html.escape(err)}</p>' if err else ""
        self.send_html(200 if not err else 401, SIGNIN.replace("%ERR%", e).replace("%BASE%", self.base()))

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        b = self.base()
        if path in ("/", "/login", "/Mumbai ME Team Performance.html"):   # the last one: old bookmarks of the open page
            _, user = self.session()
            return self.redirect(b + "/dashboard") if user else self.signin()
        if path == "/logout":
            tok, user = self.session()
            if tok:
                with LOCK:
                    SESS.pop(tok, None)
                log(f"sign out  {user} from {self.ip()}")
            return self.redirect(b + "/", self.cookie("", 0))
        if path == "/dashboard":
            _, user = self.session()
            if not user:
                return self.redirect(b + "/")
            return self.dashboard(user)
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_html(404, "<!doctype html><title>Not found</title><p>Not found.</p>")

    def dashboard(self, user):
        try:
            entry = load_conf()["logins"].get(user)
        except (OSError, ValueError):
            entry = None
        p = page_path(entry.get("page")) if entry else None
        if not p or not os.path.exists(p):
            log(f"no page   {user} ({entry.get('page') if entry else 'login removed'})")
            return self.send_html(503, "<!doctype html><meta charset='utf-8'><title>Not ready</title><p style='font:15px system-ui;margin:40px'>"
                                       f"Your page is not ready yet. Please try again later, or tell Kushal Sharma. <a href='{self.base()}/logout'>Sign out</a></p>")
        gz = "gzip" in self.headers.get("Accept-Encoding", "")
        mt = os.path.getmtime(p)
        key = (p, mt, entry.get("name", user), gz, self.base())
        body = CACHE.get(key)
        if body is None:
            with open(p, "rb") as f:
                raw = f.read()
            bar = BAR.replace("%NAME%", html.escape(entry.get("name", user))).replace("%BASE%", self.base()).encode("utf-8")
            i = raw.rfind(b"</body>")
            raw = raw[:i] + bar + raw[i:] if i >= 0 else raw + bar
            body = gzip.compress(raw, 6) if gz else raw
            with LOCK:
                for k in [k for k in CACHE if k[0] == p and k[1] != mt]:
                    CACHE.pop(k, None)
                CACHE[key] = body
        self.send_response(200)
        self.headers_common()
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        log(f"page      {user} -> {os.path.basename(p)} from {self.ip()}")

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/login":
            return self.send_html(404, "<!doctype html><title>Not found</title><p>Not found.</p>")
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 4096:
            return self.signin("Please enter your login ID and password.")
        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
        user = (form.get("u", [""])[0]).strip().lower()
        pw = form.get("p", [""])[0]
        keys = [f"u:{user}", f"ip:{self.ip()}"]
        wait = locked(keys)
        if wait:
            log(f"locked    {user!r} from {self.ip()}")
            return self.signin(f"Too many wrong tries. Please try again in {wait} minute{'s' if wait > 1 else ''}.")
        try:
            conf = load_conf()
        except (OSError, ValueError) as e:
            log(f"logins.json cannot be read: {e}")
            return self.signin("Sign-in is not available right now.")
        entry = conf["logins"].get(user)
        if entry and entry.get("hash"):
            ok = hmac.compare_digest(phash(pw, entry["salt"], entry.get("iter", ITER)), entry["hash"])
        else:
            phash(pw, "00" * 16)   # the same work for an unknown login, so the answer time does not tell which logins exist
            ok = False
        if not ok:
            failed(keys)
            log(f"failed    {user!r} from {self.ip()}")
            return self.signin("The login ID or password is not right.")
        tok = secrets.token_urlsafe(32)
        hours = float(conf.get("session_hours", 12))
        now = time.time()
        with LOCK:
            for k in [k for k, v in SESS.items() if v[1] <= now]:
                SESS.pop(k, None)
            SESS[tok] = (user, now + hours * 3600)
            FAILS.pop(f"u:{user}", None)
        log(f"signed in {user} from {self.ip()}")
        self.redirect(self.base() + "/dashboard", self.cookie(tok, int(hours * 3600)))


def main():
    args = sys.argv[1:]
    if args[:1] == ["--set-password"]:
        if len(args) != 3:
            sys.exit("Use: python serve_dashboard.py --set-password <login id> <new password>")
        user, pw = args[1].strip().lower(), args[2]
        if len(pw) < 6:   # the agreed format (5 Nov 2026): first name in small letters + 3 digits, e.g. yash472
            sys.exit("Use a password of at least 6 characters.")
        c = load_conf()
        if user not in c["logins"]:
            sys.exit(f"No login {user!r} in logins.json. Logins: {', '.join(c['logins'])}")
        salt = secrets.token_hex(16)
        c["logins"][user].update({"salt": salt, "hash": phash(pw, salt), "iter": ITER})
        save_conf(c)
        print(f"Password set for {user}. A running server uses it from the next sign-in.")
        return
    if args[:1] == ["--list"]:
        c = load_conf()
        for u, e in c["logins"].items():
            p = page_path(e.get("page"))
            print(f"{u:24} {e.get('name', ''):28} page {e.get('page')!s:10} {'ok' if p and os.path.exists(p) else 'MISSING'}"
                  f"{'' if e.get('hash') else '  (no password set)'}")
        return
    conf = load_conf()
    port = int(args[args.index("--port") + 1]) if "--port" in args else int(conf.get("port", 8160))
    for u, e in conf["logins"].items():
        p = page_path(e.get("page"))
        if not p or not os.path.exists(p):
            log(f"warning: the page of {u} ({e.get('page')}) is not there yet")
    behind = "--behind-htmldrop" in args
    # --local: this PC only (a test), http://localhost:<port>/ ; --behind-htmldrop: this PC only, HTML Drop passes the requests on
    host = "127.0.0.1" if "--local" in args or behind else "0.0.0.0"
    srv = http.server.ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    where = " behind HTML Drop (open the dashboard by its HTML Drop link)" if behind else ", this PC only" if host == "127.0.0.1" else ""
    log(f"Serving on port {port} ({len(conf['logins'])} logins{where}). Ctrl+C stops it.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
