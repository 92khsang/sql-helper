import pytest

from sql_helper.database import (
    DatabaseConfig,
    DatabaseType,
    SSLConfig,
)


def test_database_config_url_sqlite(sqlite_config):
    """Test SQLite URL generation."""
    expected_url = "sqlite:///:memory:"
    assert sqlite_config.url == expected_url


def test_database_config_url_postgres(postgres_config):
    """Test PostgreSQL URL generation."""
    expected_url = "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db"
    assert postgres_config.url == expected_url


def test_database_config_url_mysql(mysql_config):
    """Test MySQL URL generation."""
    expected_url = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4"
    assert mysql_config.url == expected_url


def test_database_config_url_mariadb(mariadb_config):
    """Test MariaDB URL generation."""
    expected_url = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4"
    assert mariadb_config.url == expected_url


def test_database_config_async_url_postgres(postgres_config):
    """Test PostgreSQL async URL generation."""
    expected_async_url = "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db"
    assert postgres_config.async_url == expected_async_url


def test_database_config_async_url_mariadb(mariadb_config):
    """Test MariaDB async URL generation."""
    expected_async_url = "mysql+aiomysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4"
    assert mariadb_config.async_url == expected_async_url


def test_missing_credentials_validation():
    """Test that missing credentials raise a ValueError for PostgreSQL."""
    with pytest.raises(ValueError, match="postgresql requires credentials"):
        DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test_db",
        )


def test_invalid_async_support_for_sqlite(sqlite_config):
    """Test that enabling async for SQLite raises a ValueError."""
    with pytest.raises(ValueError, match="sqlite does not support async operations"):
        DatabaseConfig(
            type=DatabaseType.SQLITE,
            host=sqlite_config.host,
            port=sqlite_config.port,
            database=sqlite_config.database,
            enable_async=True,
        )


def test_ssl_config_valid_paths(ssl_config, ssl_temp_files):
    """Test that SSL configuration accepts valid file paths."""
    assert ssl_config.enabled is True
    assert ssl_config.verify_cert is True
    assert ssl_config.ca_cert == ssl_temp_files["ca_cert"]
    assert ssl_config.client_cert == ssl_temp_files["client_cert"]
    assert ssl_config.client_key == ssl_temp_files["client_key"]


def test_ssl_config_invalid_paths():
    """Test that SSL configuration raises a ValueError for invalid file paths."""
    with pytest.raises(ValueError, match="Invalid file path for ca_cert"):
        SSLConfig(
            enabled=True,
            ca_cert="/invalid/path/to/ca.pem",
            client_cert="/invalid/path/to/client-cert.pem",
            client_key="/invalid/path/to/client-key.pem",
        )
