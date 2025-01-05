import pytest

from sql_helper.database import DatabaseType


def test_database_type_sync_driver():
    """Test sync_driver property for all supported database types."""
    assert DatabaseType.POSTGRESQL.sync_driver == "postgresql+psycopg"
    assert DatabaseType.MYSQL.sync_driver == "mysql+pymysql"
    assert DatabaseType.MARIADB.sync_driver == "mysql+pymysql"
    assert DatabaseType.SQLITE.sync_driver == "sqlite"


def test_database_type_async_driver():
    """Test async_driver property for all supported database types."""
    assert DatabaseType.POSTGRESQL.async_driver == "postgresql+psycopg"
    assert DatabaseType.MYSQL.async_driver == "mysql+aiomysql"
    assert DatabaseType.MARIADB.async_driver == "mysql+aiomysql"

    with pytest.raises(ValueError, match="No async driver available for sqlite"):
        _ = DatabaseType.SQLITE.async_driver


def test_database_type_supports_async():
    """Test supports_async property for all database types."""
    assert DatabaseType.POSTGRESQL.supports_async is True
    assert DatabaseType.MYSQL.supports_async is True
    assert DatabaseType.MARIADB.supports_async is True
    assert DatabaseType.SQLITE.supports_async is False


def test_database_type_requires_auth():
    """Test requires_auth property for all database types."""
    assert DatabaseType.POSTGRESQL.requires_auth is True
    assert DatabaseType.MYSQL.requires_auth is True
    assert DatabaseType.MARIADB.requires_auth is True
    assert DatabaseType.SQLITE.requires_auth is False
