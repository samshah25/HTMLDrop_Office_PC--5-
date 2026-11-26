# Hyderabad JDS Dashboard

Standalone, offline-capable YoY analytics dashboard for **Hyderabad JDS (Inside Sales TME & Field ME)** — covering **Total DocIDs (`COUNT(DISTINCT docid)`)**, **3-Yr RV**, **Collection**, **ECS / B2B / Fresh mix**, **Channels**, **Categories & Sales Groups**, **Telangana & Andhra Areas**, and **TME / ME Scorecards**.

## Quick Start
```powershell
python main.py
```
- Pulls incremental daily JDS deals from MySQL (`ops_analytics.tbl_modified_deal_level_data`, `vertical_owner.tbl_company_vertical_mapping_SB`, `db_paidcontracts.hr_all_daily_copy_ganesh`) using `pipeline\db_216.env` (or reuses the compact gzipped cache `pipeline\jds_cache.json.gz` when offline).
- Builds a single self-contained `Hyderabad_JDS_Dashboard.html` that opens directly in any browser with zero server required.

## Optional Flags
- `python main.py --page-only` — rebuild HTML from existing `pipeline\jds_data.json` after template edits.
- `python main.py --full-refresh` — re-fetch the entire FY + LY from MySQL instead of incremental 14-day updates.
- `python main.py --seed-dir "C:\path\to\csvs"` — seed the cache from exported `hyd_2025_deals_all.csv`, `hyd_2026_deals_all.csv`, `hyd_cat_group_deals_all.csv`, and `hyd_sales_group_deals_all.csv`.

## Setup on Office PC
1. Copy `db_216.env` into `pipeline\db_216.env` (this file is gitignored and never committed).
2. Run `python main.py`.
3. Open `Hyderabad_JDS_Dashboard.html`.
