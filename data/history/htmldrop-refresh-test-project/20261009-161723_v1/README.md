# HTML Drop Refresh Test Project

A safe demo project for testing HTML Drop's data-refresh scheduling.

## Files
- `app.py`: Flask web app; reads the latest snapshot from `data/sample_data.json`.
- `refresh_dashboards.py`: writes a timestamped demo snapshot and appends `logs/refresh.log`.
- `requirements.txt`: Flask dependency.
- `index.html`: small page that displays the latest snapshot.
- `data/` and `logs/`: generated files are stored here.

## Test locally
1. Create a virtual environment if desired.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Run one refresh: `python refresh_dashboards.py`
4. Start the dashboard: `python app.py`
5. Open `http://127.0.0.1:5000/`

The refresh script only modifies files inside this project folder and does not connect to SQL or external services.
