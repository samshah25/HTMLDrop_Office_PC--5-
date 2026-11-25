"""Read-only database helper for the kit. Logins: DB_216 / DB_240 / DB_120 in environment.py (the private folder; the ME kit's
format), else pipeline\db_<server>.env. Logins are never copied into the page or the logs."""
import os
import sys
import pymysql
import kitpaths  # noqa: F401  (puts the private folder on the path)


def login(server):
    try:
        import environment
        d = getattr(environment, f"DB_{server}", None) or {}
        if str(d.get("MYSQL_HOST", "")).strip() and str(d.get("MYSQL_USER", "")).strip():
            return {k: str(v).strip() for k, v in d.items()}
    except ImportError:
        pass
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"db_{server}.env")
    if os.path.exists(f):
        e = {}
        for l in open(f, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1); e[k.strip()] = v.strip().strip('"').strip("'")
        return e
    sys.exit(f"Missing the server {server} login: DB_{server} in environment.py (see README.txt)")


def q(server, sql, args=None):
    e = login(server)
    c = pymysql.connect(host=e["MYSQL_HOST"], port=int(e.get("MYSQL_PORT") or 3306), user=e["MYSQL_USER"], password=e["MYSQL_PASSWORD"],
                        ssl_disabled=True, connect_timeout=30, read_timeout=1800)
    try:
        with c.cursor() as cur:
            cur.execute(sql, args); cols = [d[0] for d in cur.description]; return cols, cur.fetchall()
    finally:
        c.close()
