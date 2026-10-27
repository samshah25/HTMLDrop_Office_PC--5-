"""
Share the Mumbai JDA dashboard with people on the same network, and nothing else.

Only the one dashboard file is served (at http://<this-pc>:8091/). The pipeline folder, with its database logins, is
never reachable, and every other path returns 404. Each request reads the file fresh, so viewers get the latest data
after the daily refresh just by reloading the page.

Run:  python serve_dashboard.py            (port 8091)
      python serve_dashboard.py 8095       (another port)
Stop: close the window or press Ctrl+C.
"""
import http.server
import os
import socket
import sys

PIPE_DIR = os.path.dirname(os.path.abspath(__file__))
def dashboard_file(kit_dir, default):
    """The dashboard page: the one .html in the kit folder, whatever it is called (it may have been renamed for
    hosting); the default name when there is none. With several, the default (and a warning)."""
    pages = sorted(f for f in os.listdir(kit_dir) if f.lower().endswith(".html"))
    if len(pages) == 1:
        return os.path.join(kit_dir, pages[0]), []
    return os.path.join(kit_dir, default), [p for p in pages if p != default]


DASHBOARD = dashboard_file(os.path.dirname(PIPE_DIR), "JDA_JDS_Mumbai_Pincode_Dashboard.html")[0]
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8091


import gzip
import threading

_cache = {"key": None, "etag": "", "raw": b"", "gz": b""}
_lock = threading.Lock()


def page():
    """The dashboard, read and gzip-compressed once per file version (the daily refresh changes it)."""
    st = os.stat(DASHBOARD)
    key = (st.st_mtime_ns, st.st_size)
    with _lock:
        if _cache["key"] != key:
            with open(DASHBOARD, "rb") as f:
                raw = f.read()
            _cache.update(key=key, etag=f'"{key[0]:x}-{key[1]:x}"', raw=raw, gz=gzip.compress(raw, 6))
        return _cache


class OneFile(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/", "/index.html", "/" + os.path.basename(DASHBOARD)):
            self.send_error(404)
            return
        c = page()
        if self.headers.get("If-None-Match") == c["etag"]:   # the browser already has this version: nothing to send
            self.send_response(304)
            self.send_header("ETag", c["etag"])
            self.end_headers()
            return
        gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        body = c["gz"] if gz else c["raw"]                    # compressed: about a tenth of the size
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", c["etag"])
        self.send_header("Cache-Control", "no-cache")       # always ask, but a 304 costs almost nothing
        self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = "this-pc"
    print(f"Sharing the Mumbai JDA dashboard at  http://{ip}:{PORT}/   (on this PC: http://localhost:{PORT}/)")
    print("Keep this window open. Press Ctrl+C to stop.")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), OneFile).serve_forever()
