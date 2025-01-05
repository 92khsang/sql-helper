import asyncio
import logging
import os
import sys
from typing import (
    AsyncGenerator,
    Generator,
)

import pytest
from sqlalchemy import (
    create_engine,
    text,
)

from sql_helper import (
    Database,
    DatabaseConfig,
    DatabaseCredentials,
    DatabaseType,
)
from tests.settings import (
    SQLITE_DB_PATH,
    TEST_CREDENTIALS,
    TEST_PORTS,
)
from tests.utils import DockerUtils

# Configure logger
logger = logging.getLogger(__name__)

# Database initialization scripts
INIT_SCRIPTS = {
    "postgresql+psycopg://test_user:test_password@localhost:5433/test_db": """  
        CREATE TABLE IF NOT EXISTS test_table (  
            id SERIAL PRIMARY KEY,  
            value TEXT  
        );  
    """,
    "mysql+pymysql://test_user:test_password@localhost:3307/test_db"     : """  
        CREATE TABLE IF NOT EXISTS test_table (  
            id INT AUTO_INCREMENT PRIMARY KEY,  
            value TEXT  
        );  
    """,
    "mysql+pymysql://test_user:test_password@localhost:3308/test_db"     : """  
        CREATE TABLE IF NOT EXISTS test_table (  
            id INT AUTO_INCREMENT PRIMARY KEY,  
            value TEXT  
        );  
    """,
    f"sqlite:///{SQLITE_DB_PATH}"                                        : """  
        CREATE TABLE IF NOT EXISTS test_table (  
            id INTEGER PRIMARY KEY AUTOINCREMENT,  
            value TEXT  
        );  
    """
}


@pytest.fixture(scope="session", autouse=True)
def database_setup():
    """Set up test databases and initialize schemas."""
    # Setup Docker containers for non-SQLite databases
    containers = ["postgres", "mysql", "mariadb"]
    for container in containers:
        if not DockerUtils.wait_for_healthcheck(container):
            pytest.fail(f"Container {container} did not become healthy")

    # Initialize all databases including SQLite
    for url, script in INIT_SCRIPTS.items():
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text(script))
                conn.commit()
        except Exception as e:
            pytest.fail(f"Database initialization failed for {url}: {e}")

    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_sqlite():
    """Clean up SQLite database file before and after all tests."""
    if os.path.exists(SQLITE_DB_PATH):
        try:
            os.remove(SQLITE_DB_PATH)
        except PermissionError:
            pass

    yield

    if os.path.exists(SQLITE_DB_PATH):
        try:
            os.remove(SQLITE_DB_PATH)
        except PermissionError:
            pass


@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure event loop policy for Windows compatibility."""
    if sys.platform == 'win32':
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


def create_db_config(db_type: DatabaseType, port: int = None, path: str = None) -> DatabaseConfig:
    """Helper function to create database configurations."""
    if db_type == DatabaseType.SQLITE:
        return DatabaseConfig(
            type=db_type,
            database=path or SQLITE_DB_PATH,
            enable_async=False
        )

    return DatabaseConfig(
        type=db_type,
        host="localhost",
        port=port,
        database="test_db",
        credentials=DatabaseCredentials(**TEST_CREDENTIALS),
        enable_async=True
    )


@pytest.fixture(scope="session")
def sqlite_config() -> DatabaseConfig:
    return create_db_config(DatabaseType.SQLITE)


@pytest.fixture(scope="session")
def postgres_config() -> DatabaseConfig:
    return create_db_config(DatabaseType.POSTGRESQL, TEST_PORTS["postgresql"])


@pytest.fixture(scope="session")
def mysql_config() -> DatabaseConfig:
    return create_db_config(DatabaseType.MYSQL, TEST_PORTS["mysql"])


@pytest.fixture(scope="session")
def mariadb_config() -> DatabaseConfig:
    return create_db_config(DatabaseType.MARIADB, TEST_PORTS["mariadb"])


@pytest.fixture(params=["sqlite_config", "postgres_config", "mysql_config", "mariadb_config"])
def sync_config(request) -> DatabaseConfig:
    return request.getfixturevalue(request.param)

@pytest.fixture(params=["postgres_config", "mysql_config", "mariadb_config"])
def async_config(request) -> DatabaseConfig:
    return request.getfixturevalue(request.param)


@pytest.fixture
def db(sync_config: DatabaseConfig) -> Generator[Database, None, None]:
    """Create and dispose Database instance for each test."""
    database = Database(sync_config)
    yield database
    database.dispose_sync()


@pytest.fixture
async def async_db(async_config: DatabaseConfig) -> AsyncGenerator[Database, None]:
    """Create and dispose async Database instance for each test."""
    database = Database(async_config)
    yield database
    await database.dispose_async()
