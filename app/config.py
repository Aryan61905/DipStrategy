# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'DATABASE_URL': os.getenv('DATABASE_URL'),
    'POOL_MIN': int(os.getenv('POOL_MIN', 1)),
    'POOL_MAX': int(os.getenv('POOL_MAX', 10))
}

FMP_API_KEY = os.getenv('FMP_API_KEY')

# Remove the Database import from here!