"""
HTML Drop Test Dynamic Dashboard - Data Refresh Script
This script can be executed manually:
    python main.py
or scheduled automatically via Windows Task Scheduler.
"""

import os
import json
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
LOG_FILE = BASE_DIR / "refresh.log"

REGIONS = ["Kolkata", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune"]

def generate_fresh_metrics():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = []
    total_sales = 0
    total_units = 0

    for reg in REGIONS:
        sales = random.randint(150000, 950000)
        units = random.randint(350, 1800)
        target = random.randint(500000, 900000)
        achievement = round((sales / target) * 100, 1)
        total_sales += sales
        total_units += units
        records.append({
            "region": reg,
            "sales": sales,
            "units": units,
            "target": target,
            "achievement": achievement
        })

    data = {
        "title": "Pan-India Operations & Sales Tracker",
        "last_refresh": timestamp,
        "total_revenue": total_sales,
        "total_units": total_units,
        "avg_achievement": round(sum(r["achievement"] for r in records) / len(records), 1),
        "records": records
    }
    return data

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting data refresh via main.py...")
    fresh_data = generate_fresh_metrics()

    # Save to data.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(fresh_data, f, indent=2)

    # Append to refresh.log
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{fresh_data['last_refresh']}] Refresh SUCCESS: Total Revenue Rs {fresh_data['total_revenue']:,}, Units: {fresh_data['total_units']:,}\n")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Refresh complete! Last refresh updated to: {fresh_data['last_refresh']}")
    print(f"Total Revenue: Rs {fresh_data['total_revenue']:,} across {len(fresh_data['records'])} regions.")

if __name__ == "__main__":
    main()
