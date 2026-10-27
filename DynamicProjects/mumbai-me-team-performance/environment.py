"""Settings for the Mumbai ME Team Performance refresh (main.py, next to this file).

Fill in the two database logins below (read-only access is enough); main.py reads them.
PRIVATE once filled in: this file then holds passwords. Do not email it or put it in a public web folder.
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
