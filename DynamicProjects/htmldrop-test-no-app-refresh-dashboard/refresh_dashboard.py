#!/usr/bin/env python3
"""Safe test refresh script for HTML Drop. No app.py required."""
from datetime import datetime
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

now = datetime.now().astimezone().isoformat(timespec="seconds")
status = {
    "project": "HTML Drop Test — No app.py",
    "refreshed_at": now,
    "status": "success",
    "message": "refresh_dashboard.py executed successfully",
    "python": sys.version.split()[0],
}
(DATA_DIR / "refresh_status.json").write_text(
    json.dumps(status, indent=2), encoding="utf-8"
)
with (LOG_DIR / "refresh.log").open("a", encoding="utf-8") as f:
    f.write(f"[{now}] SUCCESS: refresh_dashboard.py executed\n")
print(json.dumps(status, indent=2))
