"""
========================================================================================
PAN INDIA B2B DATA REFRESH ETL SCRIPT (PRODUCTION FINAL)
========================================================================================
Source Tables:
  1: db_paidcontracts.tbl_b2b_panindia_data
  2: ops_analytics.tbl_modified_deal_level_data
  3: ops_analytics.daily_deals_closed_dump_2018_2025_camp_modified_1

Architecture:
  - Uses stored city_master_mapping.json (928 cities mapped once & stored)
  - Auto-updates mapping file if any new city appears in Table 1
  - Table 1 Universe: freeze=0, mask=0, clos_downflag NOT IN (1, 9, 10)
    (vfl_tag=1 rows are kept apart: base totals exclude them, the 'g' split carries them as '|V' keys)
  - Native Paid Breakdown: 0 = Never-Paid, 1 = Active Paid, 2 = Expired / Churned
  - Deals attribution: dc_genio > 0 mapped to active paid listings (paid=1)
  - Financials: Sum dc_genio, Collections (₹ Cr), 3-Year RV (₹ Cr), ECS % (ecs_flag_original=1)
  - Campaign Combinations: Package, PDG, Others, PDG|Package, Package|Others, PDG|Others, PDG|Package|Others
  - Macro Rollups: Package, PDG, Others totals and shares
  - Overwrites: dashboard/portal_data.js (the only data file the dashboard reads)
========================================================================================
"""

import os
import sys
import json
import csv
import subprocess
import logging
from datetime import datetime

# Setup formatted logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 1. Database Configuration (Update with your credentials or environment variables)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "172.29.0.216"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "muskan_10179794"),
    "password": os.getenv("DB_PASSWORD", "Mu$|<@^_94"),
    "database": "db_paidcontracts"
}

# 2. Query 1: Master Listing Universe by Branch & City from Table 1
SQL_UNIVERSE = """
SELECT 
    COALESCE(NULLIF(TRIM(final_data_city), ''), 'Other') AS branch,
    COALESCE(NULLIF(TRIM(data_city), ''), 'Other') AS local_city,
    CASE WHEN UPPER(TRIM(business_flag)) IN ('B2B', 'B2C', 'BOTH') THEN UPPER(TRIM(business_flag)) ELSE 'NA' END AS biz,
    CASE WHEN UPPER(TRIM(prod_service_flag)) IN ('PROD', 'SERV', 'MIX') THEN UPPER(TRIM(prod_service_flag)) ELSE 'NA' END AS ps,
    CASE WHEN vfl_tag = 1 THEN 1 ELSE 0 END AS vfl,

    COUNT(*) AS total_listings,
    SUM(CASE WHEN (callable_flag = 1 OR paid <> 0) THEN 1 ELSE 0 END) AS monetizable_count,
    SUM(CASE WHEN callable_flag = 1 THEN 1 ELSE 0 END) AS callable_count,
    SUM(CASE WHEN callable_flag = 0 THEN 1 ELSE 0 END) AS non_callable_count,

    SUM(CASE WHEN paid = 1 THEN 1 ELSE 0 END) AS active_paid_count,
    SUM(CASE WHEN paid = 2 THEN 1 ELSE 0 END) AS expired_paid_count,
    SUM(CASE WHEN paid = 0 THEN 1 ELSE 0 END) AS never_paid_count,

    SUM(CASE WHEN callable_flag = 1 AND paid = 1 THEN 1 ELSE 0 END) AS call_1_paid_1,
    SUM(CASE WHEN callable_flag = 0 AND paid = 1 THEN 1 ELSE 0 END) AS call_0_paid_1,
    SUM(CASE WHEN callable_flag = 1 AND paid = 2 THEN 1 ELSE 0 END) AS call_1_paid_2,
    SUM(CASE WHEN callable_flag = 0 AND paid = 2 THEN 1 ELSE 0 END) AS call_0_paid_2,
    SUM(CASE WHEN callable_flag = 1 AND paid = 0 THEN 1 ELSE 0 END) AS call_1_paid_0,
    SUM(CASE WHEN callable_flag = 0 AND paid = 0 THEN 1 ELSE 0 END) AS call_0_paid_0

FROM db_paidcontracts.tbl_b2b_panindia_data
WHERE freeze = 0
  AND mask = 0
  -- vfl_tag is not filtered here: VFL rows are kept as their own bucket (vfl = 1)
  AND (close_downflag NOT IN (1, 9, 10) OR close_downflag IS NULL)
GROUP BY
    COALESCE(NULLIF(TRIM(final_data_city), ''), 'Other'),
    COALESCE(NULLIF(TRIM(data_city), ''), 'Other'),
    biz,
    ps,
    vfl;
"""

# 3. Query 2: Active Paid Deals & Campaign Classifications with Financials
# Active (docid, version) from db_paidcontracts.tbl_daily_paid_contracts_dump; deals with dc_genio > 0 only
SQL_DEALS = """
WITH RECURSIVE split_versions AS (
    -- active (docid, version) pairs straight from today's contracts dump; version is comma-separated
    SELECT
        docid,
        TRIM(SUBSTRING_INDEX(version, ',', 1)) AS version,
        CASE WHEN version LIKE '%,%' THEN SUBSTRING(version, LOCATE(',', version) + 1) ELSE '' END AS remaining_versions
    FROM db_paidcontracts.tbl_daily_paid_contracts_dump
    WHERE docid <> '' AND version IS NOT NULL AND TRIM(version) <> ''

    UNION ALL

    SELECT
        docid,
        TRIM(SUBSTRING_INDEX(remaining_versions, ',', 1)),
        CASE WHEN remaining_versions LIKE '%,%' THEN SUBSTRING(remaining_versions, LOCATE(',', remaining_versions) + 1) ELSE '' END
    FROM split_versions
    WHERE remaining_versions <> ''
),
active_versions AS (
    SELECT DISTINCT docid, CAST(version AS UNSIGNED) AS version
    FROM split_versions
    WHERE version REGEXP '^[0-9]+$'
),
active_docids AS (
    SELECT DISTINCT 
        docid,
        COALESCE(NULLIF(TRIM(final_data_city), ''), 'Other') AS branch,
        COALESCE(NULLIF(TRIM(data_city), ''), 'Other') AS local_city,
        CASE WHEN UPPER(TRIM(business_flag)) IN ('B2B', 'B2C', 'BOTH') THEN UPPER(TRIM(business_flag)) ELSE 'NA' END AS biz,
        CASE WHEN UPPER(TRIM(prod_service_flag)) IN ('PROD', 'SERV', 'MIX') THEN UPPER(TRIM(prod_service_flag)) ELSE 'NA' END AS ps,
        CASE WHEN vfl_tag = 1 THEN 1 ELSE 0 END AS vfl
    FROM db_paidcontracts.tbl_b2b_panindia_data
    WHERE freeze = 0
      AND mask = 0
      -- vfl_tag not filtered: VFL deals are tagged via a.vfl
      AND (close_downflag NOT IN (1, 9, 10) OR close_downflag IS NULL)
      AND paid = 1
),
deals_union AS (
    SELECT 
        docid,
        version,
        modified_camp_name,
        dc_genio,
        collection,
        rv_3yr,
        ecs_flag_original,
        original_budget
    FROM ops_analytics.tbl_modified_deal_level_data
    WHERE dc_genio > 0

    UNION ALL

    SELECT 
        docid,
        version,
        modified_camp_name,
        dc_genio,
        collection,
        RV_3yr AS rv_3yr,
        ecs_flag_original,
        original_budget
    FROM ops_analytics.daily_deals_closed_dump_2018_2025_camp_modified_1
    WHERE dc_genio > 0
),
-- one row per active contract (docid, version): a contract split over several deal rows repeats
-- its full original_budget on each row, so the budget is taken once (MAX) and the rest summed
active_version_deals AS (
    SELECT 
        d.docid,
        d.version,
        MAX(d.modified_camp_name) AS modified_camp_name,
        SUM(d.dc_genio) AS dc_genio,
        SUM(d.collection) AS collection,
        SUM(d.rv_3yr) AS rv_3yr,
        MAX(d.ecs_flag_original) AS ecs_flag_original,
        MAX(d.original_budget) AS original_budget
    FROM deals_union d
    JOIN active_versions v ON v.docid = d.docid AND v.version = d.version
    GROUP BY d.docid, d.version
)
SELECT 
    a.branch,
    a.local_city,
    a.biz,
    a.ps,
    a.vfl,
    COALESCE(NULLIF(TRIM(d.modified_camp_name), ''), 'Others') AS modified_camp_name,
    ROUND(SUM(d.dc_genio), 4) AS deals_sum,
    COUNT(*) AS txns_count,
    SUM(COALESCE(d.collection, 0)) / 10000000 AS collection_cr,
    SUM(COALESCE(d.rv_3yr, 0)) / 10000000 AS rv_3yr_cr,
    ROUND(SUM(CASE WHEN d.ecs_flag_original = 1 THEN d.dc_genio ELSE 0 END), 4) AS ecs_deals_sum,
    SUM(CASE WHEN d.ecs_flag_original = 1 THEN COALESCE(d.collection, 0) ELSE 0 END) / 10000000 AS ecs_collection_cr,
    SUM(CASE WHEN d.ecs_flag_original = 1 THEN COALESCE(d.rv_3yr, 0) ELSE 0 END) / 10000000 AS ecs_rv_3yr_cr,
    ROUND(SUM(COALESCE(d.original_budget, 0)) / 10000000, 4) AS original_budget_cr,
    COUNT(*) AS contracts_count
FROM active_docids a
JOIN active_version_deals d ON a.docid = d.docid
GROUP BY 
    a.branch,
    a.local_city,
    a.biz,
    a.ps,
    a.vfl,
    COALESCE(NULLIF(TRIM(d.modified_camp_name), ''), 'Others');
"""

def load_or_create_city_master(base_dir):
    """
    Loads city_master_mapping.json and synchronizes with
    pincode_city_data_city_branch.xlsx if present.
    """
    master_file = os.path.join(base_dir, "city_master_mapping.json")
    mapping = {}
    if os.path.exists(master_file):
        with open(master_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
            logging.info(f"Loaded stored city master mapping ({len(mapping):,} cities).")

    # If official Excel file is present, apply exact branch and main/remote mapping
    excel_file = os.path.join(base_dir, "pincode_city_data_city_branch.xlsx")
    if os.path.exists(excel_file):
        try:
            import pandas as pd
            df = pd.read_excel(excel_file)
            mapping_df = df[['Data City', 'Branch', 'Main/remote']].drop_duplicates().dropna(subset=['Data City'])
            updated_cnt = 0
            for _, row in mapping_df.iterrows():
                city_raw = str(row['Data City']).strip()
                k = city_raw.lower()
                branch_clean = str(row['Branch']).strip().lower()
                mr_raw = str(row['Main/remote']).strip().lower()
                mr_clean = "Main" if mr_raw == "main" else "Remote"
                flag = 1 if mr_clean == "Main" else 0

                if k in mapping:
                    mapping[k]['branch'] = branch_clean
                    mapping[k]['mainRemote'] = mr_clean
                    mapping[k]['main_city_flag'] = flag
                else:
                    bc = BRANCH_CENTERS.get(branch_clean, BRANCH_CENTERS['delhi'])
                    mapping[k] = {
                        'displayName': city_raw,
                        'branch': branch_clean,
                        'main_city_flag': flag,
                        'mainRemote': mr_clean,
                        'lat': bc['lat'],
                        'lon': bc['lon'],
                        'x': bc['x'],
                        'y': bc['y']
                    }
                updated_cnt += 1
            logging.info(f"✅ Synchronized {updated_cnt:,} cities from {excel_file}")
        except Exception as ex_err:
            logging.warning(f"Note: Could not parse Excel mapping ({ex_err}), using city_master_mapping.json.")

    return mapping, master_file


BRANCH_CENTERS = {
    "delhi": {"x": 350, "y": 325, "lat": 28.65, "lon": 77.21},
    "mumbai": {"x": 236, "y": 625, "lat": 19.20, "lon": 72.95},
    "bangalore": {"x": 352, "y": 812, "lat": 12.98, "lon": 77.60},
    "hyderabad": {"x": 395, "y": 672, "lat": 17.43, "lon": 78.48},
    "ahmedabad": {"x": 222, "y": 512, "lat": 23.02, "lon": 72.57},
    "chennai": {"x": 425, "y": 825, "lat": 13.08, "lon": 80.27},
    "kolkata": {"x": 648, "y": 542, "lat": 22.57, "lon": 88.36},
    "pune": {"x": 275, "y": 650, "lat": 18.52, "lon": 73.86},
    "jaipur": {"x": 298, "y": 385, "lat": 26.91, "lon": 75.79},
    "chandigarh": {"x": 328, "y": 268, "lat": 30.73, "lon": 76.78},
    "coimbatore": {"x": 350, "y": 890, "lat": 11.02, "lon": 76.96}
}

def save_city_master(mapping, master_file, base_dir):
    """Saves updated city master mapping to both JSON and CSV."""
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

    csv_file = os.path.join(base_dir, "city_master_mapping.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "displayName", "branch", "main_city_flag", "mainRemote", "lat", "lon", "x", "y", "stateId", "stateName"])
        for k, v in mapping.items():
            writer.writerow([
                k, 
                v.get("displayName", k), 
                v.get("branch", ""), 
                v.get("main_city_flag", 0), 
                v.get("mainRemote", "Remote"),
                v.get("lat", ""),
                v.get("lon", ""),
                v.get("x", ""),
                v.get("y", ""),
                v.get("stateId", ""),
                v.get("stateName", "")
            ])

STATE_META = [
    {"stateId": "MH", "stateKey": "mh", "stateName": "Maharashtra", "region": "West", "color": "#3b82f6", "accent": "#60a5fa"},
    {"stateId": "DL", "stateKey": "dl", "stateName": "Delhi", "region": "North", "color": "#0284c7", "accent": "#38bdf8"},
    {"stateId": "UP", "stateKey": "up", "stateName": "Uttar Pradesh", "region": "North", "color": "#10b981", "accent": "#34d399"},
    {"stateId": "TN", "stateKey": "tn", "stateName": "Tamil Nadu", "region": "South", "color": "#ec4899", "accent": "#f472b6"},
    {"stateId": "KA", "stateKey": "ka", "stateName": "Karnataka", "region": "South", "color": "#6366f1", "accent": "#818cf8"},
    {"stateId": "GJ", "stateKey": "gj", "stateName": "Gujarat", "region": "West", "color": "#f97316", "accent": "#fb923c"},
    {"stateId": "WB", "stateKey": "wb", "stateName": "West Bengal", "region": "East", "color": "#14b8a6", "accent": "#2dd4bf"},
    {"stateId": "TG", "stateKey": "tg", "stateName": "Telangana", "region": "South", "color": "#8b5cf6", "accent": "#a78bfa"},
    {"stateId": "RJ", "stateKey": "rj", "stateName": "Rajasthan", "region": "North", "color": "#eab308", "accent": "#facc15"},
    {"stateId": "MP", "stateKey": "mp", "stateName": "Madhya Pradesh", "region": "Central", "color": "#d97706", "accent": "#f59e0b"},
    {"stateId": "BR", "stateKey": "br", "stateName": "Bihar", "region": "East", "color": "#ea580c", "accent": "#f97316"},
    {"stateId": "KL", "stateKey": "kl", "stateName": "Kerala", "region": "South", "color": "#059669", "accent": "#10b981"},
    {"stateId": "AP", "stateKey": "ap", "stateName": "Andhra Pradesh", "region": "South", "color": "#7c3aed", "accent": "#8b5cf6"},
    {"stateId": "PB", "stateKey": "pb", "stateName": "Punjab", "region": "North", "color": "#f59e0b", "accent": "#fbbf24"},
    {"stateId": "HR", "stateKey": "hr", "stateName": "Haryana", "region": "North", "color": "#06b6d4", "accent": "#22d3ee"},
    {"stateId": "AS", "stateKey": "as", "stateName": "Assam", "region": "North East", "color": "#0d9488", "accent": "#14b8a6"},
    {"stateId": "OR", "stateKey": "or", "stateName": "Odisha", "region": "East", "color": "#0891b2", "accent": "#06b6d4"},
    {"stateId": "UT", "stateKey": "ut", "stateName": "Uttarakhand", "region": "North", "color": "#2563eb", "accent": "#3b82f6"},
    {"stateId": "JH", "stateKey": "jh", "stateName": "Jharkhand", "region": "East", "color": "#16a34a", "accent": "#22c55e"},
    {"stateId": "CT", "stateKey": "ct", "stateName": "Chhattisgarh", "region": "Central", "color": "#ca8a04", "accent": "#eab308"},
    {"stateId": "CH", "stateKey": "ch", "stateName": "Chandigarh", "region": "North", "color": "#9333ea", "accent": "#a855f7"},
    {"stateId": "JK", "stateKey": "jk", "stateName": "Jammu & Kashmir", "region": "North", "color": "#0284c7", "accent": "#38bdf8"},
    {"stateId": "HP", "stateKey": "hp", "stateName": "Himachal Pradesh", "region": "North", "color": "#4f46e5", "accent": "#6366f1"},
    {"stateId": "GA", "stateKey": "ga", "stateName": "Goa", "region": "West", "color": "#db2777", "accent": "#ec4899"},
    {"stateId": "DH", "stateKey": "dh", "stateName": "Dadra & Nagar Haveli and Daman & Diu", "region": "West", "color": "#f97316", "accent": "#fb923c"},
    {"stateId": "PY", "stateKey": "py", "stateName": "Puducherry", "region": "South", "color": "#db2777", "accent": "#f472b6"},
    {"stateId": "TR", "stateKey": "tr", "stateName": "Tripura", "region": "North East", "color": "#059669", "accent": "#10b981"},
    {"stateId": "MN", "stateKey": "mn", "stateName": "Manipur", "region": "North East", "color": "#d97706", "accent": "#f59e0b"},
    {"stateId": "ML", "stateKey": "ml", "stateName": "Meghalaya", "region": "North East", "color": "#0891b2", "accent": "#06b6d4"},
    {"stateId": "AR", "stateKey": "ar", "stateName": "Arunachal Pradesh", "region": "North East", "color": "#16a34a", "accent": "#22c55e"},
    {"stateId": "SK", "stateKey": "sk", "stateName": "Sikkim", "region": "North East", "color": "#2563eb", "accent": "#3b82f6"},
    {"stateId": "MZ", "stateKey": "mz", "stateName": "Mizoram", "region": "North East", "color": "#7c3aed", "accent": "#8b5cf6"},
    {"stateId": "NL", "stateKey": "nl", "stateName": "Nagaland", "region": "North East", "color": "#ea580c", "accent": "#f97316"},
    {"stateId": "AN", "stateKey": "an", "stateName": "Andaman & Nicobar", "region": "East", "color": "#0284c7", "accent": "#38bdf8"},
    {"stateId": "LA", "stateKey": "la", "stateName": "Ladakh", "region": "North", "color": "#6366f1", "accent": "#818cf8"},
    {"stateId": "LD", "stateKey": "ld", "stateName": "Lakshadweep", "region": "South", "color": "#14b8a6", "accent": "#2dd4bf"}
]

# Per-segment metric order, matches K in portal_data.js: T, C, N, p1, p2, m, c1p0, c0p1
SEG_FIELDS = ["total_listings", "callable_count", "non_callable_count", "active_paid_count",
              "expired_paid_count", "monetizable_count", "call_1_paid_0", "call_0_paid_1"]
UNIVERSE_SUM_FIELDS = SEG_FIELDS + ["never_paid_count", "call_1_paid_1", "call_1_paid_2", "call_0_paid_2", "call_0_paid_0"]


def collapse_segment_rows(universe_rows):
    """Universe rows come split by business flag (biz) and product/service flag (ps).
    Re-sum them per (branch, city) so the rest of the pipeline is unchanged, and keep
    the split as {(branch, city_key): {"B2B|PROD": [T, C, N, p1, p2, m, c1p0, c0p1], ...}}.
    VFL rows (vfl = 1) are left out of the base totals and kept in the split under "B2B|PROD|V" keys."""
    merged, seg = {}, {}
    for r in sorted(universe_rows, key=lambda r: int(r.get("vfl") or 0)):
        branch = str(r["branch"]).strip()
        city_raw = str(r["local_city"]).strip()
        key = (branch.lower(), city_raw.lower())
        vfl = int(r.get("vfl") or 0)
        m = merged.get(key)
        if m is None:
            if vfl:
                continue  # VFL-only (branch, city) pair: no base row to attach to
            m = merged[key] = {"branch": branch, "local_city": city_raw, **{f: 0 for f in UNIVERSE_SUM_FIELDS}}
        if not vfl:
            for f in UNIVERSE_SUM_FIELDS:
                m[f] += int(r[f] or 0)
        g = seg.setdefault(key, {})
        sk = f"{r.get('biz') or 'NA'}|{r.get('ps') or 'NA'}" + ("|V" if vfl else "")
        arr = g.setdefault(sk, [0] * len(SEG_FIELDS))
        for i, f in enumerate(SEG_FIELDS):
            arr[i] += int(r[f] or 0)
    return list(merged.values()), seg


# 4. Query 3: Collections of the active contracts. NOT RUN for now: the temp table has no version
#    column, so till Mar 2026 it can't be limited to active versions. Kept for when that is fixed.
# Till Mar 2026 from db_paidcontracts.temp_collection_master_tbl_tbd (parentid x source_city),
# from Apr 2026 from db_paidcontracts.tbl_collection_dump_data (parentid x source_city x active version).
# Collection = ecs_collection + nonecs_collection.
SQL_COLL = """
WITH RECURSIVE split_versions AS (
    -- active (docid, version) pairs from today's contracts dump, with the parentid x source_city collection key
    SELECT
        docid, parentid, source_city,
        TRIM(SUBSTRING_INDEX(version, ',', 1)) AS version,
        CASE WHEN version LIKE '%,%' THEN SUBSTRING(version, LOCATE(',', version) + 1) ELSE '' END AS remaining_versions
    FROM db_paidcontracts.tbl_daily_paid_contracts_dump
    WHERE docid <> '' AND version IS NOT NULL AND TRIM(version) <> ''

    UNION ALL

    SELECT
        docid, parentid, source_city,
        TRIM(SUBSTRING_INDEX(remaining_versions, ',', 1)),
        CASE WHEN remaining_versions LIKE '%,%' THEN SUBSTRING(remaining_versions, LOCATE(',', remaining_versions) + 1) ELSE '' END
    FROM split_versions
    WHERE remaining_versions <> ''
),
active_versions AS (
    SELECT DISTINCT docid, parentid, source_city, version
    FROM split_versions
    WHERE version REGEXP '^[0-9]+$'
),
active_contracts AS (
    SELECT DISTINCT docid, parentid, source_city FROM active_versions
),
active_docids AS (
    SELECT DISTINCT
        docid,
        COALESCE(NULLIF(TRIM(final_data_city), ''), 'Other') AS branch,
        COALESCE(NULLIF(TRIM(data_city), ''), 'Other') AS local_city,
        CASE WHEN UPPER(TRIM(business_flag)) IN ('B2B', 'B2C', 'BOTH') THEN UPPER(TRIM(business_flag)) ELSE 'NA' END AS biz,
        CASE WHEN UPPER(TRIM(prod_service_flag)) IN ('PROD', 'SERV', 'MIX') THEN UPPER(TRIM(prod_service_flag)) ELSE 'NA' END AS ps,
        CASE WHEN vfl_tag = 1 THEN 1 ELSE 0 END AS vfl
    FROM db_paidcontracts.tbl_b2b_panindia_data
    WHERE freeze = 0
      AND mask = 0
      AND (close_downflag NOT IN (1, 9, 10) OR close_downflag IS NULL)
      AND paid = 1
),
-- up to March 2026: temp_collection_master_tbl_tbd (no version column, so matched on parentid x source_city)
coll_till_mar26 AS (
    SELECT ac.docid,
           SUM(COALESCE(t.ecs_collection, 0) + COALESCE(t.nonecs_collection, 0)) AS coll,
           SUM(COALESCE(t.ecs_collection, 0)) AS ecs
    FROM db_paidcontracts.temp_collection_master_tbl_tbd t
    JOIN active_contracts ac ON ac.parentid = t.parentid AND ac.source_city = t.source_city
    WHERE t.year_no * 100 + t.month_no <= 202603
    GROUP BY ac.docid
),
-- from April 2026: tbl_collection_dump_data, matched on parentid x source_city x active version
coll_from_apr26 AS (
    SELECT av.docid,
           SUM(COALESCE(c.ecs_collection, 0) + COALESCE(c.nonecs_collection, 0)) AS coll,
           SUM(COALESCE(c.ecs_collection, 0)) AS ecs
    FROM db_paidcontracts.tbl_collection_dump_data c
    JOIN active_versions av ON av.parentid = c.parentid AND av.source_city = c.source_city AND av.version = TRIM(c.VERSION)
    WHERE c.to_date >= '2026-04-01'
    GROUP BY av.docid
),
coll_by_docid AS (
    SELECT docid, SUM(coll) AS coll, SUM(ecs) AS ecs, SUM(old) AS old
    FROM (SELECT docid, coll, ecs, coll AS old FROM coll_till_mar26
          UNION ALL
          SELECT docid, coll, ecs, 0 FROM coll_from_apr26) x
    GROUP BY docid
)
SELECT
    a.branch,
    a.local_city,
    a.biz,
    a.ps,
    a.vfl,
    SUM(c.coll) / 10000000 AS collection_cr,
    SUM(c.ecs) / 10000000 AS ecs_collection_cr,
    SUM(c.old) / 10000000 AS collection_till_mar26_cr,
    COUNT(*) AS docids
FROM active_docids a
JOIN coll_by_docid c ON c.docid = a.docid
GROUP BY a.branch, a.local_city, a.biz, a.ps, a.vfl;
"""


def build_segment_collections(coll_rows):
    """Collections split by biz|ps for Pan India ('all') and each branch:
    {scope: {"B2B|PROD": [collectionCr, ecsCollectionCr, collectionTillMar26Cr, docids]}}."""
    out = {}
    for d in coll_rows:
        vals = (float(d["collection_cr"] or 0), float(d["ecs_collection_cr"] or 0), float(d["collection_till_mar26_cr"] or 0), int(d["docids"]))
        sk = f"{d.get('biz') or 'NA'}|{d.get('ps') or 'NA'}" + ("|V" if int(d.get("vfl") or 0) else "")
        for scope in ("all", str(d["branch"]).strip().lower()):
            acc = out.setdefault(scope, {}).setdefault(sk, [0.0, 0.0, 0.0, 0])
            for i, v in enumerate(vals):
                acc[i] += v
    for blk in out.values():
        for sk, v in blk.items():
            blk[sk] = [round(x, 4) for x in v[:3]] + [v[3]]
    return out


def build_segment_deals(deals_rows):
    """Active-deal financials split by biz|ps for Pan India ('all') and each branch:
    {scope: {"B2B|PROD": {"Total"|"Package"|"PDG"|"Others"|"Multi": [deals, collectionCr, rv3yrCr, ecsDeals, originalBudgetCr, contracts]}}}.
    A combo deal (e.g. 'PDG|Package') counts toward each product it contains, as in build_macro_block;
    "Multi" holds only combo deals (two or more products) for the cross-sell rate."""
    prods = ("Package", "PDG", "Others")
    out = {}
    for d in deals_rows:
        camp = str(d["modified_camp_name"]).strip().lower()
        parts = [p for p in prods if p.lower() in camp.split("|")] or ["Others"]
        vals = (float(d["deals_sum"]), float(d["collection_cr"]), float(d["rv_3yr_cr"]), float(d["ecs_deals_sum"]),
                float(d["original_budget_cr"]), int(d["contracts_count"]))
        sk = f"{d.get('biz') or 'NA'}|{d.get('ps') or 'NA'}" + ("|V" if int(d.get("vfl") or 0) else "")
        for scope in ("all", str(d["branch"]).strip().lower()):
            blk = out.setdefault(scope, {}).setdefault(sk, {})
            for name in ["Total"] + parts + (["Multi"] if len(parts) > 1 else []):
                acc = blk.setdefault(name, [0.0, 0.0, 0.0, 0.0, 0.0, 0])
                for i, v in enumerate(vals):
                    acc[i] += v
    for blk in out.values():
        for sk in blk:
            blk[sk] = {k: [round(x, 4) for x in v] for k, v in blk[sk].items()}
    return out


def process_and_save(universe_rows, deals_rows, base_dir):
    universe_rows, seg_by_city = collapse_segment_rows(universe_rows)
    seg_deals = build_segment_deals(deals_rows)
    deals_rows = [d for d in deals_rows if not int(d.get("vfl") or 0)]  # base deal rollups exclude VFL
    logging.info(f"Processing {len(universe_rows):,} city universe rows and {len(deals_rows):,} deal aggregations...")

    city_master, master_file = load_or_create_city_master(base_dir)
    mapping_updated = False

    # A. Build City-by-City Universe
    cities_map = {}
    main_count = 0
    remote_count = 0
    total_pan_india = {
        "totalListings": 0, "monetizable": 0, "callable": 0, "nonCallable": 0,
        "paid0_never": 0, "paid1_active": 0, "paid2_expired": 0,
        "call_1_paid_1": 0, "call_0_paid_1": 0,
        "call_1_paid_2": 0, "call_0_paid_2": 0,
        "call_1_paid_0": 0, "call_0_paid_0": 0
    }

    for r in universe_rows:
        city_raw = str(r["local_city"]).strip()
        city_key = city_raw.lower()
        branch = str(r["branch"]).strip()

        # Lookup in stored city master mapping
        if city_key in city_master:
            entry = city_master[city_key]
            main_city_flag = int(entry.get("main_city_flag", 0))
            main_remote_str = entry.get("mainRemote", "Remote")
            display_name = entry.get("displayName", city_raw.title())
            lat = entry.get("lat")
            lon = entry.get("lon")
            x = entry.get("x")
            y = entry.get("y")
        else:
            # New city detected: auto-register as Remote
            main_city_flag = 0
            main_remote_str = "Remote"
            display_name = city_raw.title()
            lat = None
            lon = None
            x = None
            y = None
            entry = {
                "displayName": display_name,
                "branch": branch.lower(),
                "main_city_flag": main_city_flag,
                "mainRemote": main_remote_str,
                "lat": None,
                "lon": None,
                "x": None,
                "y": None
            }
            city_master[city_key] = entry
            mapping_updated = True

        # Calculate coordinates if missing
        if x is None or y is None:
            if lat is not None and lon is not None:
                x = round(350 + (lon - 77.2096) * 27.6, 1)
                y = round(325 + (28.6568 - lat) * 31.06, 1)
            else:
                b_center = BRANCH_CENTERS.get(branch.lower(), {"x": 350, "y": 325, "lat": 28.65, "lon": 77.21})
                h = abs(hash(city_key))
                dx = (h % 51) - 25
                dy = ((h // 51) % 51) - 25
                x = b_center["x"] + dx
                y = b_center["y"] + dy
                lat = round(b_center["lat"] - (dy / 31.06), 4)
                lon = round(b_center["lon"] + (dx / 27.6), 4)
            entry["x"] = x
            entry["y"] = y
            entry["lat"] = lat
            entry["lon"] = lon
            mapping_updated = True

        if main_city_flag == 1 or main_remote_str == "Main":
            main_count += 1
        else:
            remote_count += 1

        tot = int(r["total_listings"])
        call = int(r["callable_count"])
        non_call = int(r["non_callable_count"])
        p1 = int(r["active_paid_count"])
        p2 = int(r["expired_paid_count"])
        p0 = int(r["never_paid_count"])
        c1p1 = int(r["call_1_paid_1"])
        c0p1 = int(r["call_0_paid_1"])
        c1p2 = int(r["call_1_paid_2"])
        c0p2 = int(r["call_0_paid_2"])
        c1p0 = int(r["call_1_paid_0"])
        c0p0 = int(r["call_0_paid_0"])

        monetizable = int(r.get("monetizable_count", call + c0p1 + c0p2))
        cur_pen = round((p1 / monetizable) * 100, 2) if monetizable > 0 else 0.0
        life_pen = round(((p1 + p2) / monetizable) * 100, 2) if monetizable > 0 else 0.0

        cities_map[city_key] = {
            "city": city_key,
            "displayName": display_name,
            "branch": branch.lower(),
            "mainRemote": main_remote_str,
            "main_city_flag": main_city_flag,
            "stateId": entry.get("stateId", ""),
            "stateName": entry.get("stateName", ""),
            "lat": lat,
            "lon": lon,
            "x": x,
            "y": y,
            "totalListings": tot,
            "monetizable": monetizable,
            "callable": call,
            "nonCallable": non_call,
            "paid1": p1,
            "paid2": p2,
            "lifetime_paid": p1 + p2,
            "never_paid": p0,
            "curPenPct": cur_pen,
            "lifePenPct": life_pen,
            "call_1_paid_1": c1p1,
            "call_0_paid_1": c0p1,
            "call_1_paid_2": c1p2,
            "call_0_paid_2": c0p2,
            "call_1_paid_0": c1p0,
            "call_0_paid_0": c0p0,
            "seg": seg_by_city.get((branch.lower(), city_key), {})
        }

        total_pan_india["totalListings"] += tot
        total_pan_india["monetizable"] += monetizable
        total_pan_india["callable"] += call
        total_pan_india["nonCallable"] += non_call
        total_pan_india["paid1_active"] += p1
        total_pan_india["paid2_expired"] += p2
        total_pan_india["paid0_never"] += p0
        total_pan_india["call_1_paid_1"] += c1p1
        total_pan_india["call_0_paid_1"] += c0p1
        total_pan_india["call_1_paid_2"] += c1p2
        total_pan_india["call_0_paid_2"] += c0p2
        total_pan_india["call_1_paid_0"] += c1p0
        total_pan_india["call_0_paid_0"] += c0p0

    if mapping_updated:
        save_city_master(city_master, master_file, base_dir)
        logging.info(f"Updated {master_file} with newly detected cities.")

    all_cities_list = list(cities_map.values())
    all_cities_list.sort(key=lambda x: x["totalListings"], reverse=True)

    # B. Process Campaign Deals & Combinations
    combo_keys = [
        "Package", "PDG", "Others",
        "PDG|Package", "Package|Others", "PDG|Others", "PDG|Package|Others"
    ]

    pan_combos = {
        k: {"deals": 0.0, "txns": 0, "collectionCr": 0.0, "rv3yrCr": 0.0, "ecsDeals": 0.0, "ecsCollCr": 0.0, "ecsRv3yrCr": 0.0}
        for k in combo_keys
    }

    total_deals = 0.0
    total_txns = 0
    total_coll = 0.0
    total_rv3yr = 0.0
    total_ecs_deals = 0.0

    # Branch-level combinations tracking
    branch_combos = {}

    for d in deals_rows:
        camp = str(d["modified_camp_name"]).strip()
        b_key = str(d["branch"]).strip().lower()
        deals_val = float(d["deals_sum"])
        txns_val = int(d["txns_count"])
        coll_val = float(d["collection_cr"])
        rv_val = float(d["rv_3yr_cr"])
        ecs_deals_val = float(d["ecs_deals_sum"])
        ecs_coll_val = float(d["ecs_collection_cr"])
        ecs_rv_val = float(d["ecs_rv_3yr_cr"])

        # Match combination key
        matched_k = "Others"
        for k in combo_keys:
            if camp.lower() == k.lower():
                matched_k = k
                break

        # Pan India rollup
        target = pan_combos[matched_k]
        target["deals"] += deals_val
        target["txns"] += txns_val
        target["collectionCr"] += coll_val
        target["rv3yrCr"] += rv_val
        target["ecsDeals"] += ecs_deals_val
        target["ecsCollCr"] += ecs_coll_val
        target["ecsRv3yrCr"] += ecs_rv_val

        total_deals += deals_val
        total_txns += txns_val
        total_coll += coll_val
        total_rv3yr += rv_val
        total_ecs_deals += ecs_deals_val

        # Branch rollup
        if b_key not in branch_combos:
            branch_combos[b_key] = {
                "total_deals": 0.0, "total_txns": 0, "total_coll": 0.0, "total_rv3yr": 0.0, "total_ecs_deals": 0.0,
                "combos": {k: {"deals": 0.0, "txns": 0, "collectionCr": 0.0, "rv3yrCr": 0.0, "ecsDeals": 0.0, "ecsCollCr": 0.0, "ecsRv3yrCr": 0.0} for k in combo_keys}
            }
        bc = branch_combos[b_key]
        bc["total_deals"] += deals_val
        bc["total_txns"] += txns_val
        bc["total_coll"] += coll_val
        bc["total_rv3yr"] += rv_val
        bc["total_ecs_deals"] += ecs_deals_val
        bc_target = bc["combos"][matched_k]
        bc_target["deals"] += deals_val
        bc_target["txns"] += txns_val
        bc_target["collectionCr"] += coll_val
        bc_target["rv3yrCr"] += rv_val
        bc_target["ecsDeals"] += ecs_deals_val
        bc_target["ecsCollCr"] += ecs_coll_val
        bc_target["ecsRv3yrCr"] += ecs_rv_val

    # C. Calculate Master Product Rollups (Full Financials: Deals, Collections, RV_3yr, ECS %, Avg Ticket)
    PKG_KEYS = ["Package", "PDG|Package", "Package|Others", "PDG|Package|Others"]
    PDG_KEYS = ["PDG", "PDG|Package", "PDG|Others", "PDG|Package|Others"]
    OTH_KEYS = ["Others", "Package|Others", "PDG|Others", "PDG|Package|Others"]

    def build_macro_block(combos_source, total_d, total_c, total_r):
        macro_dict = {}
        for name, keys in [("Package", PKG_KEYS), ("PDG", PDG_KEYS), ("Others", OTH_KEYS)]:
            d_sum = sum(combos_source[k]["deals"] for k in keys)
            tx_sum = sum(combos_source[k]["txns"] for k in keys)
            c_sum = sum(combos_source[k]["collectionCr"] for k in keys)
            r_sum = sum(combos_source[k]["rv3yrCr"] for k in keys)
            ecs_sum = sum(combos_source[k]["ecsDeals"] for k in keys)
            non_ecs_sum = max(0.0, d_sum - ecs_sum)
            ecs_p = round((ecs_sum / d_sum * 100), 1) if d_sum > 0 else 0.0
            avg_t = round((c_sum * 10000000 / d_sum), 0) if d_sum > 0 else 0
            sh_d = round((d_sum / total_d * 100), 1) if total_d > 0 else 0.0
            sh_c = round((c_sum / total_c * 100), 1) if total_c > 0 else 0.0
            sh_r = round((r_sum / total_r * 100), 1) if total_r > 0 else 0.0
            macro_dict[name] = {
                "deals": round(d_sum, 2),
                "txns": tx_sum,
                "collectionCr": round(c_sum, 2),
                "rv3yrCr": round(r_sum, 2),
                "avgTicket": avg_t,
                "ecsPct": ecs_p,
                "ecsDeals": round(ecs_sum, 2),
                "nonEcsDeals": round(non_ecs_sum, 2),
                "shareOfDeals": sh_d,
                "shareOfColl": sh_c,
                "shareOfRv3yr": sh_r
            }
        return macro_dict

    pan_macro = build_macro_block(pan_combos, total_deals, total_coll, total_rv3yr)
    overall_ecs_pct = round((total_ecs_deals / total_deals * 100), 1) if total_deals > 0 else 0.0

    combos_formatted = {}
    for k, v in pan_combos.items():
        d_val = v["deals"]
        combos_formatted[k] = {
            "deals": round(d_val, 2),
            "txns": v["txns"],
            "collectionCr": round(v["collectionCr"], 2),
            "rv3yrCr": round(v["rv3yrCr"], 2),
            "avgTicket": round((v["collectionCr"] * 10000000 / d_val), 0) if d_val > 0 else 0,
            "ecsPct": round((v["ecsDeals"] / d_val * 100), 1) if d_val > 0 else 0.0,
            "ecsDeals": round(v["ecsDeals"], 2),
            "ecsCollCr": round(v["ecsCollCr"], 2),
            "ecsRv3yrCr": round(v["ecsRv3yrCr"], 2),
            "nonEcsDeals": round(d_val - v["ecsDeals"], 2),
            "nonEcsCollCr": round(v["collectionCr"] - v["ecsCollCr"], 2),
            "nonEcsRv3yrCr": round(v["rv3yrCr"] - v["ecsRv3yrCr"], 2),
            "shareOfDeals": round((d_val / total_deals * 100), 1) if total_deals > 0 else 0.0,
            "shareOfColl": round((v["collectionCr"] / total_coll * 100), 1) if total_coll > 0 else 0.0,
            "shareOfRv3yr": round((v["rv3yrCr"] / total_rv3yr * 100), 1) if total_rv3yr > 0 else 0.0
        }

    # Format branches object
    branches_formatted = {}
    for b_key, b_val in branch_combos.items():
        b_tot_deals = b_val["total_deals"]
        b_tot_coll = b_val["total_coll"]
        b_tot_rv = b_val["total_rv3yr"]
        b_macro = build_macro_block(b_val["combos"], b_tot_deals, b_tot_coll, b_tot_rv)
        b_pkg = b_macro["Package"]["deals"]
        b_pdg = b_macro["PDG"]["deals"]
        b_oth = b_macro["Others"]["deals"]

        branches_formatted[b_key] = {
            "total": {
                "deals": round(b_tot_deals, 2),
                "txns": b_val["total_txns"],
                "collectionCr": round(b_tot_coll, 2),
                "rv3yrCr": round(b_tot_rv, 2),
                "avgTicket": round((b_tot_coll * 10000000 / b_tot_deals), 0) if b_tot_deals > 0 else 0,
                "ecsPct": round((b_val["total_ecs_deals"] / b_tot_deals * 100), 1) if b_tot_deals > 0 else 0.0,
                "packageDeals": round(b_pkg, 2),
                "pdgDeals": round(b_pdg, 2),
                "otherDeals": round(b_oth, 2),
                "packagePct": b_macro["Package"]["shareOfDeals"],
                "pdgPct": b_macro["PDG"]["shareOfDeals"],
                "otherPct": b_macro["Others"]["shareOfDeals"]
            },
            "macro": b_macro,
            "combos": {
                ck: {
                    "deals": round(cv["deals"], 2),
                    "txns": cv["txns"],
                    "collectionCr": round(cv["collectionCr"], 2),
                    "rv3yrCr": round(cv["rv3yrCr"], 2),
                    "avgTicket": round((cv["collectionCr"] * 10000000 / cv["deals"]), 0) if cv["deals"] > 0 else 0,
                    "ecsPct": round((cv["ecsDeals"] / cv["deals"] * 100), 1) if cv["deals"] > 0 else 0.0,
                    "ecsDeals": round(cv["ecsDeals"], 2),
                    "ecsCollCr": round(cv["ecsCollCr"], 2),
                    "ecsRv3yrCr": round(cv["ecsRv3yrCr"], 2),
                    "nonEcsDeals": round(cv["deals"] - cv["ecsDeals"], 2),
                    "nonEcsCollCr": round(cv["collectionCr"] - cv["ecsCollCr"], 2),
                    "nonEcsRv3yrCr": round(cv["rv3yrCr"] - cv["ecsRv3yrCr"], 2),
                    "shareOfDeals": round((cv["deals"] / b_tot_deals * 100), 1) if b_tot_deals > 0 else 0.0,
                    "shareOfColl": round((cv["collectionCr"] / b_tot_coll * 100), 1) if b_tot_coll > 0 else 0.0,
                    "shareOfRv3yr": round((cv["rv3yrCr"] / b_tot_rv * 100), 1) if b_tot_rv > 0 else 0.0
                } for ck, cv in b_val["combos"].items()
            }
        }

    # E. Save Output File
    campaign_export = {"panIndia": {"total": {
        "deals": round(total_deals, 2), "txns": total_txns, "collectionCr": round(total_coll, 2),
        "rv3yrCr": round(total_rv3yr, 2),
        "avgTicket": round((total_coll * 10000000 / total_deals), 0) if total_deals > 0 else 0,
        "ecsPct": overall_ecs_pct, "ecsDeals": round(total_ecs_deals, 2),
        "packageDeals": pan_macro["Package"]["deals"], "pdgDeals": pan_macro["PDG"]["deals"],
        "otherDeals": pan_macro["Others"]["deals"], "packagePct": pan_macro["Package"]["shareOfDeals"],
        "pdgPct": pan_macro["PDG"]["shareOfDeals"], "otherPct": pan_macro["Others"]["shareOfDeals"]}}}

    # dashboard/portal_data.js
    export_portal_data(base_dir, all_cities_list, campaign_export, pan_macro, combos_formatted, branches_formatted,
                       seg_deals)

    logging.info("=" * 70)
    logging.info(f"  PAN INDIA REFRESH SUMMARY:")
    logging.info(f"  • Total Listings      : {total_pan_india['totalListings']:,}")
    logging.info(f"  • Monetizable Universe: {total_pan_india['monetizable']:,} ({(total_pan_india['monetizable']/total_pan_india['totalListings']*100):.1f}%)")
    logging.info(f"  • Total Callable      : {total_pan_india['callable']:,} ({(total_pan_india['callable']/total_pan_india['totalListings']*100):.1f}%)")
    monetizable_base = total_pan_india['monetizable'] if total_pan_india['monetizable'] > 0 else total_pan_india['totalListings']
    logging.info(f"  • Active Paid (paid=1): {total_pan_india['paid1_active']:,} ({(total_pan_india['paid1_active']/monetizable_base*100):.2f}% penetration)")
    logging.info(f"  • Expired (paid=2)    : {total_pan_india['paid2_expired']:,}")
    logging.info(f"  • Lifetime Paid       : {(total_pan_india['paid1_active'] + total_pan_india['paid2_expired']):,} ({((total_pan_india['paid1_active'] + total_pan_india['paid2_expired'])/monetizable_base*100):.2f}% penetration)")
    logging.info(f"  • Total Deals (genio) : {round(total_deals, 1):,}")
    logging.info(f"  • Total Collections   : ₹{round(total_coll, 2)} Cr")
    logging.info(f"  • Total 3-Year RV     : ₹{round(total_rv3yr, 2)} Cr")
    logging.info(f"  • Overall ECS Rate    : {overall_ecs_pct}%")
    logging.info(f"  • Cities Categorized  : {main_count} Main | {remote_count} Remote")
    logging.info("=" * 70)


def export_portal_data(base_dir, all_cities_list, campaign_export, pan_macro, combos_formatted, branches_formatted, seg_deals):
    # project layout keeps it in dashboard/, the HTML Drop bundle keeps it next to this script
    portal_file = os.path.join(base_dir, "dashboard", "portal_data.js")
    if not os.path.exists(portal_file):
        portal_file = os.path.join(base_dir, "portal_data.js")
    if not os.path.exists(portal_file):
        logging.error(f"{portal_file} not found")
        return

    with open(portal_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Build C compact array
    C = []
    for c in all_cities_list:
        C.append({
            "n": c.get("displayName", ""),
            "b": c.get("branch", ""),
            "h": c.get("main_city_flag", 0),
            "s": c.get("stateId", ""),
            "x": c.get("x", 0),
            "y": c.get("y", 0),
            "T": c.get("totalListings", 0),
            "C": c.get("callable", 0),
            "N": c.get("nonCallable", 0),
            "p1": c.get("paid1", 0),
            "p2": c.get("paid2", 0),
            "m": c.get("monetizable", 0),
            "c1p0": c.get("call_1_paid_0", 0),
            "c0p1": c.get("call_0_paid_1", 0),
            "g": {k: v for k, v in c.get("seg", {}).items() if v[0]}
        })

    # Build CP compact object
    branches_cp = {}
    for bk, bv in branches_formatted.items():
        branches_cp[bk] = {
            "m": bv["macro"],
            "c": bv["combos"],
            "t": bv["total"]
        }
    CP = {
        "all": {
            "m": pan_macro,
            "c": combos_formatted,
            "t": campaign_export["panIndia"]["total"]
        },
        "b": branches_cp
    }

    # Locate insertion indices
    idx_s = content.find(",S=[")
    idx_cp = content.find("const CP=")
    idx_cm = content.find("const CM=")

    if idx_s != -1 and idx_cp != -1 and idx_cm != -1:
        middle_block = content[idx_s:idx_cp]
        tail_block = content[idx_cm:]
        new_portal = f"// PORTAL DATA & SHARED METRICS (Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\nconst C=" + json.dumps(C) + middle_block + "const CP=" + json.dumps(CP) + ";\nconst CPS=" + json.dumps(seg_deals) + ";\n" + tail_block

        with open(portal_file, "w", encoding="utf-8") as f:
            f.write(new_portal)
        logging.info(f"Updated portal data: {len(C)} cities synced.")

def run():
    start_time = datetime.now()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        import pymysql
        logging.info("Connecting to Database...")
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            cursorclass=pymysql.cursors.DictCursor
        )

        with conn.cursor() as cur:
            logging.info("Step 1/2: Querying Universe from Table 1...")
            cur.execute(SQL_UNIVERSE)
            universe_rows = cur.fetchall()

        with conn.cursor() as cur:
            logging.info("Step 2/2: Querying Active Deals & Financials for active (docid, version) from tbl_daily_paid_contracts_dump...")
            cur.execute(SQL_DEALS)
            deals_rows = cur.fetchall()

        conn.close()
        process_and_save(universe_rows, deals_rows, base_dir)

        duration = (datetime.now() - start_time).total_seconds()
        logging.info(f"🚀 Daily Refresh completed successfully in {duration:.1f} seconds!")

        return True

    except Exception as e:
        logging.error(f"ETL execution failed: {e}")
        return False

if __name__ == "__main__":
    run()
