from dataclasses import replace

import pytest

from sql_helper.database.utils import (
    DatabaseConfigValidator,
    DatabaseURLBuilder,
)
from tests.utils import ConfigUtils


class TestDatabaseConfigValidator:
    """Test suite for DatabaseConfigValidator."""

    def test_validate_valid_config(self, postgres_config):
        """Test validation with a valid configuration."""
        try:
            DatabaseConfigValidator.validate(postgres_config)
        except ValueError:
            pytest.fail("Validation should pass for valid configuration")

    def test_missing_credentials(self, postgres_config):
        """Test validation raises error for missing credentials."""
        invalid_config = ConfigUtils.update_config(postgres_config, credentials=None)
        with pytest.raises(ValueError, match="postgresql requires credentials"):
            DatabaseConfigValidator.validate(invalid_config)

    def test_invalid_async_support(self, sqlite_config):
        """Test validation raises error for invalid async support."""
        invalid_config = ConfigUtils.update_config(sqlite_config, enable_async=True)
        with pytest.raises(ValueError, match="sqlite does not support async operations"):
            DatabaseConfigValidator.validate(invalid_config)

    def test_invalid_port_number(self, postgres_config):
        """Test validation raises error for invalid port number."""
        invalid_config = ConfigUtils.update_config(postgres_config, port=-1)
        with pytest.raises(ValueError, match="Invalid port number"):
            DatabaseConfigValidator.validate(invalid_config)

    def test_empty_database_name(self, postgres_config):
        """Test validation raises error for empty database name."""
        invalid_config = ConfigUtils.update_config(postgres_config, database="")
        with pytest.raises(ValueError, match="Database name cannot be empty"):
            DatabaseConfigValidator.validate(invalid_config)

    def test_invalid_pool_settings(self, postgres_config):
        """Test validation raises error for invalid pool settings."""
        invalid_configs = [
            ("pool_size", 0, "Pool size must be at least 1"),
            ("max_overflow", -1, "Max overflow must be non-negative"),
            ("pool_timeout", -5, "Pool timeout must be non-negative"),
            ("pool_recycle", -10, "Pool recycle must be non-negative"),
        ]

        for field, value, error_message in invalid_configs:
            invalid_config = ConfigUtils.update_config(
                postgres_config,
                **{
                    field: value
                }
            )
            with pytest.raises(ValueError, match=error_message):
                DatabaseConfigValidator.validate(invalid_config)


class TestDatabaseURLBuilder:
    """Test suite for DatabaseURLBuilder."""

    def test_build_url_sync_postgres(self, postgres_config):
        """Test sync URL generation for PostgreSQL."""
        expected_url = "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db"
        assert DatabaseURLBuilder.build_url(postgres_config) == expected_url

    def test_build_url_async_postgres(self, postgres_config):
        """Test async URL generation for PostgreSQL."""
        expected_url = "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db"
        assert DatabaseURLBuilder.build_url(postgres_config, async_mode=True) == expected_url

    def test_build_url_sqlite(self, sqlite_config):
        """Test URL generation for SQLite."""
        expected_url = "sqlite:///:memory:"
        assert DatabaseURLBuilder.build_url(sqlite_config) == expected_url

    def test_build_url_with_schema(self, postgres_config):
        """Test URL generation with schema for PostgreSQL."""
        postgres_config_with_schema = replace(postgres_config, schema="public")
        expected_url = (
            "postgresql+psycopg://test_user:test_pass@localhost:5432/test_db?options=-c%20search_path=public"
        )
        assert DatabaseURLBuilder.build_url(postgres_config_with_schema) == expected_url

    def test_build_url_with_charset(self, mysql_config):
        """Test URL generation with charset for MySQL."""
        mysql_config_with_charset = replace(mysql_config, charset="utf8mb4")
        expected_url = "mysql+pymysql://test_user:test_pass@localhost:3306/test_db?charset=utf8mb4"
        assert DatabaseURLBuilder.build_url(mysql_config_with_charset) == expected_url

    def test_invalid_async_support(self, sqlite_config):
        """Test async URL generation for unsupported database raises error."""
        with pytest.raises(ValueError, match="sqlite does not support async operations"):
            DatabaseURLBuilder.build_url(sqlite_config, async_mode=True)
