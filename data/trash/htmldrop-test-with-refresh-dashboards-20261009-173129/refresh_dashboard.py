"""Safe test refresh script for HTML Drop.
Writes a timestamp/status file and appends a log entry. No external systems are accessed.
"""
from datetime import datetime
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
STATUS_FILE = DATA_DIR / "refresh_status.json"
LOG_FILE = LOG_DIR / "refresh.log"

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    runs = 0
    if STATUS_FILE.exists():
        try:
            runs = int(json.loads(STATUS_FILE.read_text(encoding="utf-8")).get("runs", 0))
        except (ValueError, OSError, TypeError):
            runs = 0
    payload = {
        "last_refresh": now,
        "runs": runs + 1,
        "message": "Refresh script executed successfully."
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{now} - refresh completed; run={runs + 1}\n")
    print(f"Refresh successful at {now}; run={runs + 1}")

if __name__ == "__main__":
    main()
