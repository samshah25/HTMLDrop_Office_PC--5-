"""
Share the JD India sales overview with people on the same network, and nothing else.

Only the one dashboard file is served (at http://<this-pc>:8093/). The pipeline folder, with its database login, is
never reachable, and every other path returns 404. The page is compressed once per refresh and browsers re-use their
copy until the next refresh, so it opens quickly. Viewers get new data by reloading after a refresh.

Run:  python serve_dashboard.py            (port 8093)
      python serve_dashboard.py 8096       (another port)
Stop: close the window or press Ctrl+C.

Already have a web server? Then you don't need this: copy the .html file into it after each refresh.
"""
import gzip
import http.server
import os
import socket
import sys
import threading

KIT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PAGE = "jd-india-sales-overview.html"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8093


def dashboard_file():
    """The one .html in this folder, whatever it is called; the default name when there is none or several."""
    pages = sorted(f for f in os.listdir(KIT) if f.lower().endswith(".html"))
    return os.path.join(KIT, pages[0] if len(pages) == 1 else DEFAULT_PAGE)


DASHBOARD = dashboard_file()
_cache = {"key": None, "etag": "", "raw": b"", "gz": b""}
_lock = threading.Lock()


def page():
    """The dashboard, read and gzip-compressed once per file version (each refresh changes it)."""
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
        if self.headers.get("If-None-Match") == c["etag"]:   # the browser already has this version
            self.send_response(304)
            self.send_header("ETag", c["etag"])
            self.end_headers()
            return
        gz = "gzip" in (self.headers.get("Accept-Encoding") or "")
        body = c["gz"] if gz else c["raw"]
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
    if not os.path.exists(DASHBOARD):
        sys.exit(f"No dashboard yet: run refresh_dashboard.py first (it creates {os.path.basename(DASHBOARD)}).")
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        ip = "this-pc"
    print(f"Sharing the JD India sales overview at  http://{ip}:{PORT}/   (on this PC: http://localhost:{PORT}/)")
    print("Keep this window open. Press Ctrl+C to stop.")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), OneFile).serve_forever()
