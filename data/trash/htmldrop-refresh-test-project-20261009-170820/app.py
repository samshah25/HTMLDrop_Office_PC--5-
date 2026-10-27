import json
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "sample_data.json"
app = Flask(__name__)

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/api/data")
def get_data():
    if not DATA_FILE.exists():
        return jsonify({"message": "No refreshed data yet. Run refresh_dashboards.py first."}), 404
    return jsonify(json.loads(DATA_FILE.read_text(encoding="utf-8")))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
