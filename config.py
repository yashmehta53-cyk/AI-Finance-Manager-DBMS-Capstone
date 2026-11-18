import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-finance-manager-super-secure-production-key-2026')
    
    # Target MySQL configuration:
    # USE_MYSQL=True
    # DB_USER=root
    # DB_PASSWORD=YOUR_ACTUAL_PASSWORD
    # DB_HOST=localhost
    # DB_PORT=3306
    # DB_NAME=textile_factory
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'textile_factory')
    
    DEFAULT_SQLITE_URI = f"sqlite:///{BASE_DIR / 'finance_db.sqlite3'}"
    
    USE_MYSQL = os.environ.get('USE_MYSQL', 'false').lower() in ('true', '1', 'yes')
    if USE_MYSQL:
        # Build standard MySQL PyMySQL connection string
        if DB_PASSWORD:
            user_auth = f"{DB_USER}:{DB_PASSWORD}"
        else:
            user_auth = f"{DB_USER}"
            
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            'DATABASE_URL', 
            f"mysql+pymysql://{user_auth}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', DEFAULT_SQLITE_URI)
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600
    }
    
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    UPLOAD_FOLDER = BASE_DIR / 'uploads'

    # Indian Currency Configuration
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'INR')
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '₹')
    CURRENCY_LOCALE = os.environ.get('CURRENCY_LOCALE', 'en-IN')
    FINANCIAL_YEAR_START_MONTH = 4 # April
