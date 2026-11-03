"""Daily refresh for HTML Drop.

HTML Drop runs this file on its Task Scheduler schedule. It pulls fresh numbers from the
database into portal_data.js (via daily_refresh_b2b.py), then bumps the ?v= stamp in
index.html so browsers load the new data instead of a cached copy.
"""
import logging
import os
import re
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import pymysql  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "pymysql"])

import daily_refresh_b2b  # noqa: E402

log_file = logging.FileHandler(os.path.join(HERE, "refresh.log"), encoding="utf-8")
log_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(log_file)

if not daily_refresh_b2b.run():
    sys.exit(1)

index = os.path.join(HERE, "index.html")
with open(index, encoding="utf-8") as f:
    html = f.read()
stamp = datetime.now().strftime("%Y%m%d%H%M")
with open(index, "w", encoding="utf-8") as f:
    f.write(re.sub(r"\?v=\d+", "?v=" + stamp, html))
logging.info(f"index.html stamped v={stamp}")
