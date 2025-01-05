# tests/unit/database/test_engine.py
from dataclasses import replace

import pytest
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from sql_helper.database.engine import (
    DatabaseEngineFactory,
    EngineFactory,
    MySQLEngineFactory,
    PostgresEngineFactory,
    SQLiteEngineFactory,
)


class TestDatabaseEngineFactory:
    def test_abstract_class(self):
        with pytest.raises(TypeError):
            DatabaseEngineFactory()

    def test_get_base_kwargs(self, postgres_config):
        base_kwargs = DatabaseEngineFactory._get_base_kwargs(postgres_config)
        assert "echo" in base_kwargs
        assert "pool_pre_ping" in base_kwargs
        assert base_kwargs["echo"] == postgres_config.echo_sql
        assert base_kwargs["pool_pre_ping"] == postgres_config.pool_pre_ping

    def test_get_url(self, postgres_config):
        sync_url = DatabaseEngineFactory._get_url(postgres_config, async_mode=False)
        async_url = DatabaseEngineFactory._get_url(postgres_config, async_mode=True)
        assert sync_url == postgres_config.url
        assert async_url == postgres_config.async_url


class TestEngineFactory:
    def test_create_sqlite_engine(self, mocker, sqlite_config):
        mock_engine = mocker.Mock(spec=Engine if not sqlite_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if sqlite_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        engine = EngineFactory.create_engine(sqlite_config, async_mode=sqlite_config.enable_async)

        mock_create.assert_called_once()
        assert isinstance(engine, mocker.Mock)
        expected_url = sqlite_config.async_url if sqlite_config.enable_async else sqlite_config.url
        assert mock_create.call_args[0][0] == expected_url

    def test_create_postgres_engine(self, mocker, postgres_config):
        mock_engine = mocker.Mock(spec=Engine if not postgres_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if postgres_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        engine = EngineFactory.create_engine(postgres_config, async_mode=postgres_config.enable_async)

        mock_create.assert_called_once()
        assert isinstance(engine, mocker.Mock)
        expected_url = postgres_config.async_url if postgres_config.enable_async else postgres_config.url
        assert mock_create.call_args[0][0] == expected_url

    def test_create_mysql_engine(self, mocker, mysql_config):
        mock_engine = mocker.Mock(spec=Engine if not mysql_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mysql_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        engine = EngineFactory.create_engine(mysql_config, async_mode=mysql_config.enable_async)

        mock_create.assert_called_once()
        assert isinstance(engine, mocker.Mock)
        expected_url = mysql_config.async_url if mysql_config.enable_async else mysql_config.url
        assert mock_create.call_args[0][0] == expected_url

    def test_create_mariadb_engine(self, mocker, mariadb_config):
        mock_engine = mocker.Mock(spec=Engine if not mariadb_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mariadb_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        engine = EngineFactory.create_engine(mariadb_config, async_mode=mariadb_config.enable_async)

        mock_create.assert_called_once()
        assert isinstance(engine, mocker.Mock)
        expected_url = mariadb_config.async_url if mariadb_config.enable_async else mariadb_config.url
        assert mock_create.call_args[0][0] == expected_url

    def test_unsupported_database_type(self, mocker):
        mock_config = mocker.Mock()
        mock_config.type = "unsupported"

        with pytest.raises(ValueError, match="Unsupported database type"):
            EngineFactory.create_engine(mock_config)


class TestPostgresEngineFactory:
    def test_create_engine_basic(self, mocker, postgres_config):
        mock_engine = mocker.Mock(spec=Engine if not postgres_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if postgres_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = PostgresEngineFactory()
        engine = factory.create_engine(postgres_config, async_mode=postgres_config.enable_async)

        called_kwargs = mock_create.call_args[1]
        assert called_kwargs.get('pool_size', None) == postgres_config.pool_size
        assert called_kwargs.get('max_overflow', None) == postgres_config.max_overflow
        assert called_kwargs.get('pool_timeout', None) == postgres_config.pool_timeout
        assert called_kwargs.get('pool_recycle', None) == postgres_config.pool_recycle

    def test_ssl_configuration(self, mocker, postgres_config, ssl_config):
        mock_engine = mocker.Mock(spec=Engine if not postgres_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if postgres_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        updated_config = replace(postgres_config, ssl=ssl_config)
        factory = PostgresEngineFactory()
        factory.create_engine(updated_config, async_mode=updated_config.enable_async)

        ssl_args = mock_create.call_args[1]['connect_args']
        assert ssl_args['sslmode'] == 'verify-ca'
        assert ssl_args['sslrootcert'] == ssl_config.ca_cert
        assert ssl_args['sslcert'] == ssl_config.client_cert
        assert ssl_args['sslkey'] == ssl_config.client_key


class TestMySQLEngineFactory:
    def test_create_mysql_engine_basic(self, mocker, mysql_config):
        mock_engine = mocker.Mock(spec=Engine if not mysql_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mysql_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = MySQLEngineFactory()
        engine = factory.create_engine(mysql_config, async_mode=mysql_config.enable_async)

        called_kwargs = mock_create.call_args[1]
        assert called_kwargs.get('pool_size', None) == mysql_config.pool_size
        assert called_kwargs.get('max_overflow', None) == mysql_config.max_overflow
        assert called_kwargs.get('pool_timeout', None) == mysql_config.pool_timeout
        assert called_kwargs.get('pool_recycle', None) == mysql_config.pool_recycle

    def test_create_mariadb_engine_basic(self, mocker, mariadb_config):
        mock_engine = mocker.Mock(spec=Engine if not mariadb_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mariadb_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = MySQLEngineFactory()
        engine = factory.create_engine(mariadb_config, async_mode=mariadb_config.enable_async)

        called_kwargs = mock_create.call_args[1]
        assert called_kwargs.get('pool_size', None) == mariadb_config.pool_size
        assert called_kwargs.get('max_overflow', None) == mariadb_config.max_overflow
        assert called_kwargs.get('pool_timeout', None) == mariadb_config.pool_timeout
        assert called_kwargs.get('pool_recycle', None) == mariadb_config.pool_recycle

    def test_mysql_charset_configuration(self, mocker, mysql_config):
        mock_engine = mocker.Mock(spec=Engine if not mysql_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mysql_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = MySQLEngineFactory()
        factory.create_engine(mysql_config, async_mode=mysql_config.enable_async)

        connect_args = mock_create.call_args[1]['connect_args']
        assert connect_args['charset'] == mysql_config.charset

    def test_mysql_ssl_configuration(self, mocker, mysql_config, ssl_config):
        mock_engine = mocker.Mock(spec=Engine if not mysql_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if mysql_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        mysql_config_with_ssl = replace(mysql_config, ssl=ssl_config)
        factory = MySQLEngineFactory()
        factory.create_engine(mysql_config_with_ssl, async_mode=mysql_config_with_ssl.enable_async)

        ssl_args = mock_create.call_args[1]['connect_args']
        assert ssl_args['ssl_ca'] == ssl_config.ca_cert
        assert ssl_args['ssl_cert'] == ssl_config.client_cert
        assert ssl_args['ssl_key'] == ssl_config.client_key
        assert ssl_args['ssl_verify_cert'] == ssl_config.verify_cert


class TestSQLiteEngineFactory:
    def test_create_engine_basic(self, mocker, sqlite_config):
        mock_engine = mocker.Mock(spec=Engine if not sqlite_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if sqlite_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = SQLiteEngineFactory()
        engine = factory.create_engine(sqlite_config, async_mode=sqlite_config.enable_async)

        called_kwargs = mock_create.call_args[1]
        assert 'connect_args' in called_kwargs
        assert called_kwargs['connect_args']['check_same_thread'] is False

    def test_memory_database(self, mocker, sqlite_config):
        mock_engine = mocker.Mock(spec=Engine if not sqlite_config.enable_async else AsyncEngine)
        mock_create = mocker.patch(
            'sql_helper.database.engine.create_async_engine' if sqlite_config.enable_async else
            'sql_helper.database.engine.create_engine',
            return_value=mock_engine
        )

        factory = SQLiteEngineFactory()
        engine = factory.create_engine(sqlite_config, async_mode=sqlite_config.enable_async)

        url = mock_create.call_args[0][0]
        assert ':memory:' in url
