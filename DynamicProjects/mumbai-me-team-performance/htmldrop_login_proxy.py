"""Keeps the ME team dashboard on its HTML Drop link, behind the sign-in (5 Nov 2026).

HTML Drop hands every request under /s/mumbai-me-team-performance to the login server (serve_dashboard.py, running on this
same PC with --behind-htmldrop, port 8160) and sends its answer back. Nothing else in HTML Drop changes.

Add to HTML Drop (two small steps; Python standard library only):
  1. Put this file next to HTML Drop's own .py file, and near its other imports add:
         import htmldrop_login_proxy
  2. In HTML Drop's request handler class, make these the FIRST line of do_GET, do_POST and do_HEAD:
         if htmldrop_login_proxy.handle(self): return
     (If the class has no do_POST or do_HEAD, add them:
         def do_POST(self):
             if htmldrop_login_proxy.handle(self): return
             super().do_POST()          <- only if a parent class has do_POST; otherwise: self.send_error(405)
     )
Then restart HTML Drop. The old static upload at this link is no longer reachable; replace it with the small placeholder
page (no data in it) so its card on the master dashboard stays.
"""
import http.client

PREFIX = "/s/mumbai-me-team-performance"   # the link's path in HTML Drop
TARGET = ("127.0.0.1", 8160)               # serve_dashboard.py --behind-htmldrop
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding",
       "upgrade", "host", "server", "date", "content-length"}
DOWN = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>ME team dashboard</title></head>"
        "<body style='font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:40px;color:#14213D'><h1 style='font-size:18px'>ME team, Mumbai</h1>"
        "<p>The dashboard's sign-in is not running right now. Please try again in a few minutes.</p></body></html>").encode("utf-8")


def handle(h):
    """Call first in do_GET / do_POST / do_HEAD. True = the request was for the ME dashboard and has been answered."""
    path = h.path
    if not (path == PREFIX or path.startswith(PREFIX + "/") or path.startswith(PREFIX + "?")):
        return False
    rest = path[len(PREFIX):] or "/"
    if rest.startswith("?"):
        rest = "/" + rest
    n = int(h.headers.get("Content-Length") or 0)
    body = h.rfile.read(min(n, 65536)) if n > 0 else None
    headers = {k: v for k, v in h.headers.items() if k.lower() not in HOP and k.lower() not in ("x-forwarded-for", "x-forwarded-prefix")}
    headers["X-Forwarded-For"] = h.client_address[0]
    headers["X-Forwarded-Prefix"] = PREFIX
    try:
        c = http.client.HTTPConnection(*TARGET, timeout=60)
        c.request(h.command, rest, body=body, headers=headers)
        r = c.getresponse()
        data = r.read()
        c.close()
    except OSError:
        h.send_response(503)
        h.send_header("Content-Type", "text/html; charset=utf-8")
        h.send_header("Cache-Control", "no-store")
        h.send_header("Content-Length", str(len(DOWN)))
        h.end_headers()
        if h.command != "HEAD":
            h.wfile.write(DOWN)
        return True
    h.send_response(r.status)
    for k, v in r.getheaders():
        if k.lower() not in HOP:
            h.send_header(k, v)
    h.send_header("Content-Length", str(len(data)))
    h.end_headers()
    if h.command != "HEAD":
        h.wfile.write(data)
    return True
