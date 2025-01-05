import os
from pathlib import Path

# Project structure paths
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
TEST_DATA_DIR = TESTS_DIR / "data"

# Database settings
SQLITE_DB_PATH = str(TEST_DATA_DIR / "test_db.sqlite")

# Test database credentials
TEST_CREDENTIALS = {
    "username": "test_user",
    "password": "test_password"
}

# Test database ports
TEST_PORTS = {
    "postgresql": 5433,
    "mysql"     : 3307,
    "mariadb"   : 3308
}

# Logging configuration
LOGGING_CONFIG = {
    "format"       : "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "datefmt"      : "%Y-%m-%d %H:%M:%S",
    "default_level": "CRITICAL"
}

# Ensure required directories exist
os.makedirs(TEST_DATA_DIR, exist_ok=True)
