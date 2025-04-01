import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "your_db",
    "user": "your_user",
    "password": "your_password",
    "host": "your_host",
    "port": "your_port",
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)
