"""
Safe demo refresh script for HTML Drop.
It writes a small JSON snapshot and a log entry. It does not connect to SQL,
external APIs, or modify files outside this project folder.
"""
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATA_FILE = DATA_DIR / "sample_data.json"
LOG_FILE = LOG_DIR / "refresh.log"

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().astimezone()
    previous_runs = 0
    if DATA_FILE.exists():
        try:
            old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            previous_runs = int(old.get("refresh_count", 0))
        except (ValueError, OSError, TypeError):
            previous_runs = 0

    snapshot = {
        "dashboard": "HTML Drop Refresh Test",
        "refreshed_at": now.isoformat(timespec="seconds"),
        "refresh_count": previous_runs + 1,
        "status": "success",
        "message": "Demo data refreshed successfully."
    }

    temp_file = DATA_FILE.with_suffix(".json.tmp")
    temp_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    temp_file.replace(DATA_FILE)

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(f"{now.isoformat(timespec='seconds')} | SUCCESS | refresh_count={snapshot['refresh_count']}\n")

    print(json.dumps(snapshot, indent=2))

if __name__ == "__main__":
    main()
