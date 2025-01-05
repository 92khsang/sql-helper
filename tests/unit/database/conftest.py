from dataclasses import replace
from typing import (
    AsyncGenerator,
    Generator,
)

import pytest

from sql_helper.database import (
    Database,
    DatabaseConfig,
    DatabaseCredentials,
    DatabaseType,
    SSLConfig,
)


### Configuration Fixtures ###
@pytest.fixture
def sqlite_config() -> DatabaseConfig:
    """SQLite configuration (sync only)."""
    return DatabaseConfig(
        type=DatabaseType.SQLITE,
        host="",
        port=0,
        database=":memory:",
        enable_async=False,
    )


@pytest.fixture
def postgres_config() -> DatabaseConfig:
    """PostgreSQL configuration."""
    return DatabaseConfig(
        type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test_db",
        credentials=DatabaseCredentials(
            username="test_user",
            password="test_pass",
        ),
    )


@pytest.fixture
def mysql_config() -> DatabaseConfig:
    """MySQL configuration."""
    return DatabaseConfig(
        type=DatabaseType.MYSQL,
        host="localhost",
        port=3306,
        database="test_db",
        credentials=DatabaseCredentials(
            username="test_user",
            password="test_pass",
        ),
        charset="utf8mb4",
    )


@pytest.fixture
def mariadb_config() -> DatabaseConfig:
    """MariaDB configuration."""
    return DatabaseConfig(
        type=DatabaseType.MARIADB,
        host="localhost",
        port=3306,
        database="test_db",
        credentials=DatabaseCredentials(
            username="test_user",
            password="test_pass",
        ),
        charset="utf8mb4",
    )


@pytest.fixture
def ssl_config(ssl_temp_files) -> SSLConfig:
    """SSL configuration for secure connections."""
    return SSLConfig(
        enabled=True,
        ca_cert=ssl_temp_files["ca_cert"],
        client_cert=ssl_temp_files["client_cert"],
        client_key=ssl_temp_files["client_key"],
        verify_cert=True,
    )


### Parameterized Database Fixture ###
@pytest.fixture(
    params=[
        pytest.param("sqlite", id="sqlite-sync"),
        pytest.param("postgres", id="postgres-sync"),
        pytest.param("mysql", id="mysql-sync"),
        pytest.param("mariadb", id="mariadb-sync"),
    ]
)
def sync_db(
    request, sqlite_config, postgres_config, mysql_config, mariadb_config
) -> Generator[Database, None, None]:
    """
    Unified database fixture for multiple database types and modes.

    Args:
        request: Pytest request object with params for database type and mode.
        sqlite_config: SQLite configuration fixture.
        postgres_config: PostgreSQL configuration fixture.
        mysql_config: MySQL configuration fixture.
        mariadb_config: MariaDB configuration fixture.

    Yields:
        Database instance for the requested type and mode.
    """
    db_type = request.param
    config_map = {
        "sqlite"  : sqlite_config,
        "postgres": postgres_config,
        "mysql"   : mysql_config,
        "mariadb" : mariadb_config,
    }

    db = Database(config_map[db_type])

    try:
        yield db
    finally:
        db.dispose_sync()


@pytest.fixture(
    params=[
        pytest.param("postgres", id="postgres-async"),
        pytest.param("mysql", id="mysql-async"),
        pytest.param("mariadb", id="mariadb-async"),
    ]
)
async def async_db(
    request, postgres_config, mysql_config, mariadb_config
) -> AsyncGenerator[Database, None]:
    """
    Unified asynchronous database fixture for multiple database types.

    Args:
        request: Pytest request object with params for database type and mode.
        postgres_config: PostgreSQL configuration fixture.
        mysql_config: MySQL configuration fixture.
        mariadb_config: MariaDB configuration fixture.

    Yields:
        Asynchronous Database instance for the requested type and mode.
    """
    db_type = request.param
    config_map = {
        "postgres": postgres_config,
        "mysql"   : mysql_config,
        "mariadb" : mariadb_config,
    }

    original_config = config_map[db_type]
    updated_config = replace(original_config, enable_async=True)
    db = Database(updated_config)

    try:
        yield db
    finally:
        await db.dispose_async()
