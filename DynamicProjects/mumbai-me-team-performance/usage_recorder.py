"""Usage recorder for the ME dashboard (23 Nov 2026): who opens it, when, for how long, and which views they use.

The dashboard's page (the sign-in page made by pipeline\\lock_page.py) sends a small note to this recorder after a person
signs in: page opened, each button / tab clicked and list changed (labels only, never typed text), and one 'active' note a
minute while the tab is in front and in use. The recorder runs on the PC that hosts the dashboard, on port 8170, and keeps
the notes in the private folder (C:\\ProgramData\\ME_dashboard_private\\usage\\, one file a month), never in the kit folder.

    python usage_recorder.py --install     start it now and at every Windows sign-in (a shortcut in the Startup folder);
                                           a running copy is replaced, so run this again after unzipping a new kit
    python usage_recorder.py --restart     replace a running copy with this file's version (no Startup change)
    python usage_recorder.py --ensure      what main.py runs at every refresh: replaces an older running copy, restarts a
                                           stopped one (only once installed), else does nothing
    python usage_recorder.py --uninstall   remove that shortcut (stop a running one in Task Manager: pythonw.exe)
    python usage_recorder.py --status      is it running?
    python usage_recorder.py               run it in this window (Ctrl+C stops it)
    python usage_recorder.py --local       a test on this PC only (http://localhost:8170/usage)
    python usage_recorder.py --set-key <new key>   change the usage page's key

Usage page (needs the key, given to the dashboard owner separately): http://<this PC>:8170/usage
  people who opened it, sessions, active minutes, last opened, the logins that did not open it, day by day, the controls
  used most; any dates, against the period before; downloads (CSV for Excel). Every Monday a copy of the week before
  (Monday-Sunday) is saved in usage\\weekly\\ and listed on the page.

Windows firewall: other PCs must be allowed to reach port 8170. Windows usually asks the first time (click Allow); or, as
administrator:  netsh advfirewall firewall add rule name="JD dashboard usage recorder" dir=in action=allow protocol=TCP localport=8170
Needs Python 3.8+ and nothing else.
"""
import collections
import csv
import datetime as dt
import hashlib
import hmac
import html
import http.server
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pipeline"))
import kitpaths   # the private folder (shared kit: C:\ProgramData\ME_dashboard_private)

USAGE = os.path.join(kitpaths.LOGDIR, "usage")
WEEKLY = os.path.join(USAGE, "weekly")
KEYFILE = os.path.join(USAGE, "usage_key.txt")             # set by --set-key; else the key below
KEY_SHA256 = "e29a9293d2679ffc1bfe38019d8fbe11d247c2e51a88d3c2c797876c44f0ddd2"   # only the key's fingerprint, not the key
PORT = int(os.environ.get("ME_USAGE_PORT") or 8170)
VERSION = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:12]   # /health tells it; main.py --ensure compares
COOKIE = "jdme_usage"
FIELDS = ["time", "ip", "dashboard", "login", "name", "page", "event", "detail", "visit"]
EVENTS = {"sign-in", "reopen", "open", "click", "change", "active"}
GAP_MIN = 30          # a new session after 30 minutes without any note
LOCK = threading.Lock()
HITS = collections.defaultdict(collections.deque)   # ip -> recent note times (a cap per PC)
STARTUP = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup", "JD dashboard usage recorder.cmd")


def log(msg):
    os.makedirs(USAGE, exist_ok=True)
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(os.path.join(USAGE, "recorder_log.txt"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def key_hash():
    try:
        h = open(KEYFILE, encoding="utf-8").read().strip()
        if re.fullmatch(r"[0-9a-f]{64}", h):
            return h
    except OSError:
        pass
    return KEY_SHA256


def key_ok(k):
    return bool(k) and hmac.compare_digest(hashlib.sha256(k.encode("utf-8")).hexdigest(), key_hash())


def clean(s, n):
    s = re.sub(r"[\x00-\x1f\x7f]", " ", str(s or "")).strip()[:n]
    return "'" + s if s and s[0] in "=+-@" else s     # no formulas when the CSV is opened in Excel


# ---------------------------------------------------------------- notes in, rows out
REJECTED = set()   # (day, reason, login): each kind of refused note is logged once a day, so a refusal never goes unnoticed


def refused(reason, login, ip):
    k = (dt.date.today(), reason, login)
    if k not in REJECTED:
        REJECTED.add(k)
        log(f"note refused ({reason}) login {login!r} from {ip}")
    return False


def record(ip, d):
    e = d.get("e")
    dash, login, page, vid = str(d.get("d", "")), str(d.get("u", "")).lower(), str(d.get("p", "")), str(d.get("vid", ""))
    if e not in EVENTS:
        return refused(f"event {str(e)[:20]!r}", login[:40], ip)
    # page: "full", "full_sk" (the full page with the skewness card, 25 Nov 2026) or a manager code
    for ok, what in ((re.fullmatch(r"[a-z]{2,20}", dash), "dashboard"), (re.fullmatch(r"[a-z0-9._-]{1,40}", login), "login"),
                     (re.fullmatch(r"[A-Za-z0-9_-]{1,30}", page), f"page {page[:30]!r}"), (re.fullmatch(r"[a-z0-9]{4,16}", vid), "visit id")):
        if not ok:
            return refused(what, login[:40], ip)
    now = time.time()
    with LOCK:
        q = HITS[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= 300:            # at most 300 notes a minute from one PC
            return refused("over 300 a minute", login, ip)
        q.append(now)
        os.makedirs(USAGE, exist_ok=True)
        path = os.path.join(USAGE, f"usage_{dt.date.today():%Y-%m}.csv")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(FIELDS)
            w.writerow([f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}", clean(ip, 64), dash, login, clean(d.get("n"), 60), page, e,
                        clean(d.get("v"), 80), vid])
    return True


def read_rows(d0, d1):
    """notes from d0 to d1 (dates, both included)"""
    out = []
    m = dt.date(d0.year, d0.month, 1)
    while m <= d1:
        p = os.path.join(USAGE, f"usage_{m:%Y-%m}.csv")
        if os.path.exists(p):
            with LOCK, open(p, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    try:
                        t = dt.datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                    except (KeyError, ValueError):
                        continue
                    if d0 <= t.date() <= d1:
                        r["t"] = t
                        out.append(r)
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return sorted(out, key=lambda r: r["t"])


def logins():
    """the dashboard's logins (name, page) from vault_keys.json, to list who did not open it"""
    try:
        with open(kitpaths.KEYS, encoding="utf-8") as f:
            return {u: (e.get("name", u), e.get("page", "")) for u, e in json.load(f)["logins"].items()}
    except (OSError, ValueError, KeyError):
        return {}


def summary(rows):
    P = {}
    days = collections.defaultdict(lambda: {"people": set(), "sessions": 0, "active": 0})
    ctl = collections.defaultdict(lambda: {"n": 0, "people": set()})
    for r in rows:
        u = r["login"]
        p = P.setdefault(u, {"name": r["name"] or u, "page": r["page"], "sessions": 0, "days": set(), "active": 0, "first": r["t"],
                             "last": None, "ctl": collections.Counter()})
        if p["last"] is None or (r["t"] - p["last"]).total_seconds() > GAP_MIN * 60:
            p["sessions"] += 1
            days[r["t"].date()]["sessions"] += 1
        p["last"] = r["t"]
        p["days"].add(r["t"].date())
        days[r["t"].date()]["people"].add(u)
        if r["event"] == "active":
            p["active"] += 1
            days[r["t"].date()]["active"] += 1
        elif r["event"] in ("click", "change") and r["detail"]:
            p["ctl"][r["detail"]] += 1
            ctl[r["detail"]]["n"] += 1
            ctl[r["detail"]]["people"].add(u)
    tot = {"people": len(P), "sessions": sum(p["sessions"] for p in P.values()), "active": sum(p["active"] for p in P.values())}
    return P, days, ctl, tot


def page_kind(page):
    return "Whole dashboard" if page.startswith("full") else "Manager page" if page else ""


# ---------------------------------------------------------------- the usage page
CSS = """:root{--navy:#0B1B3F;--ink:#14213D;--mu:#5B6475;--line:#D9DEE7;--bg:#F4F6FA;--up:#1F7A4D;--down:#B8322A;--blue:#1F5FAD}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--navy);color:#fff;padding:14px 24px}header h1{margin:0;font-size:19px}header p{margin:2px 0 0;color:#C9D3E8;font-size:13px}
main{max-width:1240px;margin:0 auto;padding:16px 24px 40px}form.f{display:flex;flex-wrap:wrap;gap:8px;align-items:end;margin-bottom:14px}
form.f label{font-size:12px;color:var(--mu);display:flex;flex-direction:column;gap:3px}input{padding:6px 8px;border:1px solid var(--line);border-radius:6px;font:inherit}
button,.q{padding:7px 12px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);font:inherit;cursor:pointer;text-decoration:none;font-size:13px}
button.go{background:var(--navy);color:#fff;border-color:var(--navy)}.q.on{border-color:var(--navy);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}.k{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.k b{display:block;font-size:26px;line-height:1.2}.k span{color:var(--mu);font-size:12px}.d{font-size:12px;margin-top:2px}.d.up{color:var(--up)}.d.down{color:var(--down)}.d.eq{color:var(--mu)}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px}.card h2{margin:0 0 8px;font-size:15px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mu);font-weight:600;font-size:12px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}.mu{color:var(--mu)}.dl a{color:var(--blue);margin-right:12px;font-size:13px}
.empty{color:var(--mu);padding:8px 0}@media (max-width:1000px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}}"""

KEYFORM = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dashboard usage</title>
<style>{css}form.c{{max-width:360px;margin:12vh auto;background:#fff;border:1px solid var(--line);border-top:4px solid var(--navy);border-radius:10px;padding:24px}}
form.c input{{width:100%;margin:6px 0 14px}}form.c button{{width:100%}}</style></head><body><form class="c" method="post" action="/usage">
<h1 style="font-size:18px;margin:0 0 6px">Dashboard usage</h1><label for="k" class="mu">Key</label><input id="k" name="key" type="password" autofocus required>
{err}<button class="go" type="submit">Open</button></form></body></html>"""


def fmt_delta(a, b):
    if b == 0:
        return '<div class="d eq">no earlier data</div>' if a == 0 else '<div class="d eq">new in this period</div>'
    ch = (a - b) / b * 100
    cls = "up" if ch > 0.5 else "down" if ch < -0.5 else "eq"
    return f'<div class="d {cls}">{"+" if ch > 0 else ""}{ch:.0f}% vs {b:,} before</div>'


def period(q):
    today = dt.date.today()
    try:
        d1 = dt.date.fromisoformat(q.get("to", [""])[0])
    except ValueError:
        d1 = today
    try:
        d0 = dt.date.fromisoformat(q.get("from", [""])[0])
    except ValueError:
        d0 = d1 - dt.timedelta(days=6)
    if d0 > d1:
        d0, d1 = d1, d0
    return d0, d1


def usage_page(q):
    e = html.escape
    d0, d1 = period(q)
    n = (d1 - d0).days + 1
    p0, p1 = d0 - dt.timedelta(days=n), d0 - dt.timedelta(days=1)
    P, days, ctl, tot = summary(read_rows(d0, d1))
    _, _, _, prev = summary(read_rows(p0, p1))
    today = dt.date.today()
    mon = today - dt.timedelta(days=today.weekday())
    quick = [("Last 7 days", today - dt.timedelta(days=6), today), ("This week", mon, today),
             ("Last week", mon - dt.timedelta(days=7), mon - dt.timedelta(days=1)), ("This month", today.replace(day=1), today),
             ("Last month", (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1), today.replace(day=1) - dt.timedelta(days=1))]
    qs = "".join(f'<a class="q{" on" if (a, b) == (d0, d1) else ""}" href="/usage?from={a}&to={b}">{t}</a>' for t, a, b in quick)
    avg = tot["active"] / tot["sessions"] if tot["sessions"] else 0
    avgp = prev["active"] / prev["sessions"] if prev["sessions"] else 0
    kp = [("People who opened it", tot["people"], prev["people"]), ("Sessions", tot["sessions"], prev["sessions"]),
          ("Active minutes", tot["active"], prev["active"])]
    k = "".join(f'<div class="k"><span>{t}</span><b>{a:,}</b>{fmt_delta(a, b)}</div>' for t, a, b in kp)
    k += (f'<div class="k"><span>Active minutes per session</span><b>{avg:.1f}</b>'
          f'<div class="d eq">{avgp:.1f} before</div></div>')
    rows = "".join(
        f'<tr><td>{e(p["name"])}<div class="mu">{e(u)}</div></td><td>{page_kind(p["page"])}</td><td class="n">{p["sessions"]}</td>'
        f'<td class="n">{len(p["days"])}</td><td class="n">{p["active"]}</td><td>{p["last"]:%d %b %H:%M}</td>'
        f'<td>{e(", ".join(f"{c} ({v})" for c, v in p["ctl"].most_common(3))) or "<span class=mu>-</span>"}</td></tr>'
        for u, p in sorted(P.items(), key=lambda x: (-x[1]["active"], -x[1]["sessions"])))
    people = (f'<table><thead><tr><th>Person</th><th>Page</th><th class="n">Sessions</th><th class="n">Days opened</th><th class="n">Active min</th>'
              f'<th>Last opened</th><th>Most used</th></tr></thead><tbody>{rows}</tbody></table>') if rows else '<p class="empty">Nobody opened it in these dates.</p>'
    L = logins()
    miss = [(u, nm, pg) for u, (nm, pg) in L.items() if u not in P]
    nots = ("".join(f'<tr><td>{e(nm)}<div class="mu">{e(u)}</div></td><td>{page_kind(pg)}</td></tr>' for u, nm, pg in sorted(miss, key=lambda x: x[1]))
            if miss else "")
    notopen = (f'<table><thead><tr><th>Login</th><th>Page</th></tr></thead><tbody>{nots}</tbody></table>' if nots else
               '<p class="empty">' + ("Every login opened it." if L else "The list of logins is not available on this PC.") + "</p>")
    drows = "".join(f'<tr><td>{d:%a %d %b}</td><td class="n">{len(v["people"])}</td><td class="n">{v["sessions"]}</td><td class="n">{v["active"]}</td></tr>'
                    for d, v in sorted(days.items(), reverse=True))
    daily = (f'<table><thead><tr><th>Day</th><th class="n">People</th><th class="n">Sessions</th><th class="n">Active min</th></tr></thead><tbody>{drows}</tbody></table>'
             if drows else '<p class="empty">No days with use.</p>')
    crows = "".join(f'<tr><td>{e(c)}</td><td class="n">{v["n"]}</td><td class="n">{len(v["people"])}</td></tr>'
                    for c, v in sorted(ctl.items(), key=lambda x: -x[1]["n"])[:20])
    ctls = (f'<table><thead><tr><th>Button, tab or list</th><th class="n">Uses</th><th class="n">People</th></tr></thead><tbody>{crows}</tbody></table>'
            if crows else '<p class="empty">No clicks recorded.</p>')
    wk = sorted(os.listdir(WEEKLY), reverse=True)[:12] if os.path.isdir(WEEKLY) else []
    weekly = " ".join(f'<a href="/weekly/{urllib.parse.quote(w)}">{e(w[:-4])}</a>' for w in wk) or '<span class="mu">The first weekly copy is saved on the Monday after the first full week.</span>'
    rng = f"from={d0}&to={d1}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard usage</title><style>{CSS}</style></head><body>
<header><h1>ME team dashboard, {e(kitpaths.CITY_NAME)}: usage</h1><p>{d0:%d %b %Y} to {d1:%d %b %Y} ({n} days), against {p0:%d %b} to {p1:%d %b}. Recorded since this recorder started; times are this PC's.</p></header>
<main><form class="f" method="get" action="/usage"><label>From<input type="date" name="from" value="{d0}"></label><label>To<input type="date" name="to" value="{d1}"></label>
<button class="go" type="submit">Show</button>{qs}</form>
<div class="kpis">{k}</div>
<div class="card"><h2>Who used it</h2>{people}</div>
<div class="grid2"><div class="card"><h2>Logins that did not open it</h2>{notopen}</div><div class="card"><h2>Day by day</h2>{daily}</div></div>
<div class="card"><h2>Most used buttons, tabs and lists</h2>{ctls}</div>
<div class="card dl"><h2>Downloads (CSV for Excel)</h2><a href="/usage.csv?what=people&{rng}">People</a><a href="/usage.csv?what=daily&{rng}">Day by day</a>
<a href="/usage.csv?what=controls&{rng}">Buttons and tabs</a><a href="/usage.csv?what=raw&{rng}">Every note</a>
<p style="margin:10px 0 0"><b>Weekly copies (Monday to Sunday):</b> {weekly}</p></div>
<p class="mu" style="font-size:12px">A session ends after {GAP_MIN} minutes without use. Active minutes = minutes with the dashboard tab in front and used in the last 5 minutes.
Sign-ins come from the page, so a person who opens it while this recorder is off is not counted.</p></main></body></html>"""


def table_csv(what, d0, d1):
    rows = read_rows(d0, d1)
    P, days, ctl, _ = summary(rows)
    b = io.StringIO()
    w = csv.writer(b)
    if what == "raw":
        w.writerow(FIELDS)
        for r in rows:
            w.writerow([r[f] for f in FIELDS])
    elif what == "daily":
        w.writerow(["day", "people", "sessions", "active minutes"])
        for d, v in sorted(days.items()):
            w.writerow([d, len(v["people"]), v["sessions"], v["active"]])
    elif what == "controls":
        w.writerow(["button, tab or list", "uses", "people"])
        for c, v in sorted(ctl.items(), key=lambda x: -x[1]["n"]):
            w.writerow([c, v["n"], len(v["people"])])
    else:
        w.writerow(["login", "name", "page", "sessions", "days opened", "active minutes", "first opened", "last opened", "most used"])
        for u, p in sorted(P.items(), key=lambda x: -x[1]["active"]):
            w.writerow([u, p["name"], page_kind(p["page"]), p["sessions"], len(p["days"]), p["active"], f'{p["first"]:%Y-%m-%d %H:%M}',
                        f'{p["last"]:%Y-%m-%d %H:%M}', "; ".join(f"{c} ({v})" for c, v in p["ctl"].most_common(5))])
        for u, (nm, pg) in sorted(logins().items()):
            if u not in P:
                w.writerow([u, nm, page_kind(pg), 0, 0, 0, "", "", ""])
    return "\ufeff" + b.getvalue()


def weekly_copies():
    """every Monday: the week before (Monday-Sunday), people table, into usage\\weekly\\"""
    while True:
        try:
            today = dt.date.today()
            mon = today - dt.timedelta(days=today.weekday())
            a, b = mon - dt.timedelta(days=7), mon - dt.timedelta(days=1)
            path = os.path.join(WEEKLY, f"ME_dashboard_usage_{a}_to_{b}.csv")
            if not os.path.exists(path) and read_rows(a, b):
                os.makedirs(WEEKLY, exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(table_csv("people", a, b))
                log(f"weekly copy saved: {os.path.basename(path)}")
        except Exception as ex:   # never stop the recorder for this
            log(f"weekly copy failed: {ex}")
        time.sleep(3600)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "JD"
    sys_version = ""

    def log_message(self, fmt, *args):
        return

    def send(self, code, body, ctype="text/html; charset=utf-8", extra=()):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in extra:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def signed_in(self, q):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE and key_ok(urllib.parse.unquote(v)):
                return True
        return key_ok(q.get("key", [""])[0])

    def remember(self, key):
        return ("Set-Cookie", f"{COOKIE}={urllib.parse.quote(key)}; Path=/; Max-Age={60 * 86400}; HttpOnly; SameSite=Strict")

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/health":
            return self.send(200, f"ok {VERSION}", "text/plain; charset=utf-8")
        if u.path in ("/", "/usage", "/usage.csv") or u.path.startswith("/weekly/"):
            if not self.signed_in(q):
                return self.send(200 if u.path in ("/", "/usage") else 403, KEYFORM.format(css=CSS, err=""))
            extra = [self.remember(q["key"][0])] if q.get("key") else []
            if u.path == "/usage.csv":
                d0, d1 = period(q)
                what = q.get("what", ["people"])[0]
                what = what if what in ("people", "daily", "controls", "raw") else "people"
                return self.send(200, table_csv(what, d0, d1), "text/csv; charset=utf-8",
                                 extra + [("Content-Disposition", f'attachment; filename="ME_dashboard_usage_{what}_{d0}_to_{d1}.csv"')])
            if u.path.startswith("/weekly/"):
                name = os.path.basename(urllib.parse.unquote(u.path[8:]))
                p = os.path.join(WEEKLY, name)
                if not re.fullmatch(r"ME_dashboard_usage_[0-9-]+_to_[0-9-]+\.csv", name) or not os.path.isfile(p):
                    return self.send(404, "Not found", "text/plain; charset=utf-8")
                return self.send(200, open(p, "rb").read(), "text/csv; charset=utf-8", [("Content-Disposition", f'attachment; filename="{name}"')])
            try:
                return self.send(200, usage_page(q), extra=extra)
            except Exception as ex:
                log(f"usage page failed: {ex!r}")
                return self.send(500, "The usage page could not be made; see usage\\recorder_log.txt.", "text/plain; charset=utf-8")
        self.send(404, "Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 2048:
            return self.send(400, "", "text/plain")
        body = self.rfile.read(n).decode("utf-8", "replace")
        if path == "/hit":
            try:
                ok = record(self.client_address[0], json.loads(body))
            except (ValueError, AttributeError):
                ok = False
            return self.send(204 if ok else 400, "", "text/plain", [("Access-Control-Allow-Origin", "*")])
        if path == "/usage":
            k = urllib.parse.parse_qs(body).get("key", [""])[0]
            if not key_ok(k):
                time.sleep(1)
                return self.send(401, KEYFORM.format(css=CSS, err='<p style="color:var(--down);margin:-6px 0 12px">That key is not right.</p>'))
            self.send_response(303)
            self.send_header("Location", "/usage")
            self.send_header("Set-Cookie", self.remember(k)[1])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send(404, "", "text/plain")


def running_version():
    """None = not running; '' = a recorder from before 26 Nov (no version); else its version"""
    try:
        t = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3).read().decode("ascii", "replace").split()
        return (t[1] if len(t) > 1 else "") if t and t[0] == "ok" else None
    except Exception:
        return None


def running():
    return running_version() is not None


def ensure():
    """main.py runs this at every refresh (26 Nov 2026): after a new kit is unzipped the running copy is replaced by the
    new version, and a stopped recorder is started again - but only on a PC where it was installed (Startup shortcut)"""
    v = running_version()
    if v == VERSION:
        return print("Usage recorder: running, current version.")
    if v is None and not os.path.exists(STARTUP):
        return print("Usage recorder: not installed on this PC (python usage_recorder.py --install); left as it is.")
    print("Usage recorder: " + ("not running" if v is None else "an older version is running") + "; starting the current version.")
    install(startup=False)


def exe_and_me():
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return (pyw if os.path.exists(pyw) else sys.executable), os.path.abspath(__file__)


def stop_running():
    """end every running copy of this recorder (python / pythonw whose command line names usage_recorder.py), not this one"""
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\\.exe$|^py\\.exe$' -and "
          "$_.CommandLine -like '*usage_recorder.py*' -and $_.ProcessId -ne %d -and $_.ProcessId -ne %d } | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }" % (os.getpid(), os.getppid()))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    ids = r.stdout.split()
    if ids:
        print(f"Stopped the running recorder ({len(ids)} process{'es' if len(ids) > 1 else ''}).")
        time.sleep(2)
    return ids


def install(startup=True):
    """--install: Startup shortcut + (re)start; --restart: (re)start only. Both replace a running copy, so a new kit's
    usage_recorder.py takes over at once."""
    exe, me = exe_and_me()
    if startup:
        os.makedirs(os.path.dirname(STARTUP), exist_ok=True)
        with open(STARTUP, "w", encoding="utf-8") as f:
            f.write(f'@echo off\r\ncd /d "{HERE}"\r\nstart "" "{exe}" "{me}"\r\n')
        print(f"Added to the Startup folder: it starts at every Windows sign-in ({STARTUP}).")
    stop_running()
    if running():
        sys.exit(f"Port {PORT} is still in use by another program; the recorder was not started.")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    for extra in (0x01000000, 0):   # CREATE_BREAKAWAY_FROM_JOB first, so a scheduled refresh ending does not end the recorder
        try:
            subprocess.Popen([exe, me], cwd=HERE, creationflags=flags | extra, close_fds=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
        except OSError:
            if not extra:
                raise
    for _ in range(10):
        time.sleep(1)
        if running():
            print(f"Started: it is running on port {PORT}. Usage page: http://<this PC>:{PORT}/usage")
            print(f"If other PCs cannot reach it, allow port {PORT} in Windows Firewall (see the top of this file).")
            return
    print(f"It did not answer on port {PORT}; see {os.path.join(USAGE, 'recorder_log.txt')}, or run  python usage_recorder.py  to see the error.")


def main():
    a = sys.argv[1:]
    if "--install" in a:
        return install()
    if "--restart" in a:
        return install(startup=False)
    if "--ensure" in a:
        return ensure()
    if "--uninstall" in a:
        if os.path.exists(STARTUP):
            os.remove(STARTUP)
        return print("Removed from the Startup folder. A running recorder stops at sign-out (or end pythonw.exe in Task Manager).")
    if "--status" in a:
        return print(f"Running on port {PORT}." if running() else f"Not running on port {PORT}.")
    if a[:1] == ["--set-key"]:
        if len(a) != 2 or len(a[1]) < 10:
            sys.exit("Use: python usage_recorder.py --set-key <new key of 10+ characters>")
        os.makedirs(USAGE, exist_ok=True)
        open(KEYFILE, "w", encoding="utf-8").write(hashlib.sha256(a[1].encode("utf-8")).hexdigest())
        return print("Usage page key changed (a running recorder uses it from now on).")
    port = int(a[a.index("--port") + 1]) if "--port" in a else PORT
    host = "127.0.0.1" if "--local" in a else "0.0.0.0"
    if running() and port == PORT:
        sys.exit(f"The recorder is already running on port {port}.")
    srv = http.server.ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=weekly_copies, daemon=True).start()
    log(f"Usage recorder on port {port}{' (this PC only)' if host == '127.0.0.1' else ''}; notes in {USAGE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
