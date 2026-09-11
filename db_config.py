"""db_config.py -- single place holding the MySQL connection details.
All 5 databases (4 sources + warehouse) live on this one local server,
each fully separate -- no cross-database foreign keys, matching the
"designed in isolation" premise of the brief.
"""

import mysql.connector

MYSQL_HOST = "127.0.0.1"
MYSQL_USER = "iia_app"
MYSQL_PASSWORD = "iia_app_pw"


def connect(database):
    return mysql.connector.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=database
    )
