"""Settings for the Mumbai ME Team Performance refresh (main.py, next to this file).

The database logins below are filled in (read-only access is enough); main.py reads them.
DB_240 and DB_216 are needed. DB_120 is for TME mode's calls only: without it the refresh still runs and TME mode
shows no calls dialed / connected.
PRIVATE: this file holds passwords. Do not email it or put it in a public web folder.
"""

# the city whose appointments are counted (final_datacity in datagrowth.tbl_final_data_appt)
CITY = "mumbai"

# server 240: appointments (datagrowth.tbl_final_data_appt)
DB_240 = {
    "MYSQL_HOST": "192.168.24.240",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "muskan_10179794",
    "MYSQL_PASSWORD": "Mu$|<@^_94",
}

# server 216: deals and HR (db_paidcontracts.daily_deals_closed_dump, tbl_30_day_rolling_dealdump_data,
# tbl_working_days_final_data, hr_all_daily_copy_ganesh)
DB_216 = {
    "MYSQL_HOST": "172.29.0.216",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "muskan_10179794",
    "MYSQL_PASSWORD": "Mu$|<@^_94",
}

# server 120: the TMEs' dialer calls (sounak_db.tbl_dialer_data_mumbai_<yyyymm>), for TME mode's funnel. Optional.
DB_120 = {
    "MYSQL_HOST": "192.168.39.120",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "muskan_10179794",
    "MYSQL_PASSWORD": "Mu$|<@^_94",
}
