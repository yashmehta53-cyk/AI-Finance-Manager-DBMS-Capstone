"""
MySQL Database Initializer & Importer for Textile Factory Financial OS
Connects to MySQL 8+, creates database 'textile_factory' if missing,
imports 'textile-factory-v4-sql-mysql.sql', and initializes all finance tables.
"""

import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_NAME = os.environ.get('DB_NAME', 'textile_factory')

def setup_mysql_database():
    print(f"[INFO] Connecting to MySQL server at {DB_HOST}:{DB_PORT} as user '{DB_USER}'...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        cur = conn.cursor()
        print(f"[INFO] Creating database `{DB_NAME}` if it does not exist...")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"[SUCCESS] Database `{DB_NAME}` is ready.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Could not connect to MySQL server: {e}")
        print("[INFO] Please verify MySQL service is running and credentials in .env are correct.")
        return False

if __name__ == '__main__':
    ok = setup_mysql_database()
    if ok:
        print("[INFO] Proceeding to import textile-factory-v4-sql-mysql.sql via SQLAlchemy...")
        os.environ['USE_MYSQL'] = 'True'
        from app import create_app
        from migrate_textile_mysql import import_sql_dump
        app = create_app()
        import_sql_dump(app)
        print("[SUCCESS] MySQL initialization complete.")

