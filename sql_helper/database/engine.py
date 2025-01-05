from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Dict,
    Type,
    Union,
)

from sqlalchemy import (
    Engine,
    create_engine,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

from .config import (
    DatabaseConfig,
    SSLConfig,
)
from .types import DatabaseType


class DatabaseEngineFactory(ABC):
    """Abstract base class for creating database engines."""

    @abstractmethod
    def create_engine(self, config: DatabaseConfig, async_mode: bool) -> Union[Engine, AsyncEngine]:
        """Create a database engine."""
        pass

    @staticmethod
    def _get_base_kwargs(config: DatabaseConfig) -> dict:
        """Get common engine configuration."""
        return {
            "echo"         : config.echo_sql,
            "pool_pre_ping": config.pool_pre_ping,
        }

    @staticmethod
    def _get_url(config: DatabaseConfig, async_mode: bool) -> str:
        """Get database URL based on mode."""
        return config.async_url if async_mode else config.url


class PostgresEngineFactory(DatabaseEngineFactory):
    def create_engine(self, config: DatabaseConfig, async_mode: bool) -> Union[Engine, AsyncEngine]:
        engine_kwargs = {
            **self._get_base_kwargs(config),
            "pool_size"   : config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
            "pool_recycle": config.pool_recycle,
        }

        if config.ssl and config.ssl.enabled:
            engine_kwargs["connect_args"] = self._get_ssl_args(config.ssl)

        engine_class = create_async_engine if async_mode else create_engine
        return engine_class(self._get_url(config, async_mode), **engine_kwargs)

    @staticmethod
    def _get_ssl_args(ssl_config: SSLConfig) -> dict:
        """Get PostgreSQL SSL configuration."""
        return {
            "sslrootcert": ssl_config.ca_cert,
            "sslcert"    : ssl_config.client_cert,
            "sslkey"     : ssl_config.client_key,
            "sslmode"    : "verify-ca" if ssl_config.verify_cert else "require",
        }


class MySQLEngineFactory(DatabaseEngineFactory):
    def create_engine(self, config: DatabaseConfig, async_mode: bool) -> Union[Engine, AsyncEngine]:
        engine_kwargs = {
            **self._get_base_kwargs(config),
            "pool_size"   : config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
            "pool_recycle": config.pool_recycle,
        }

        connect_args = {}
        if config.charset:
            connect_args["charset"] = config.charset

        if config.ssl and config.ssl.enabled:
            connect_args.update(self._get_ssl_args(config.ssl))

        if connect_args:
            engine_kwargs["connect_args"] = connect_args

        engine_class = create_async_engine if async_mode else create_engine
        return engine_class(self._get_url(config, async_mode), **engine_kwargs)

    @staticmethod
    def _get_ssl_args(ssl_config: SSLConfig) -> dict:
        """Get MySQL SSL configuration."""
        return {
            "ssl_ca"         : ssl_config.ca_cert,
            "ssl_cert"       : ssl_config.client_cert,
            "ssl_key"        : ssl_config.client_key,
            "ssl_verify_cert": ssl_config.verify_cert,
        }


class SQLiteEngineFactory(DatabaseEngineFactory):
    def create_engine(self, config: DatabaseConfig, async_mode: bool) -> Union[Engine, AsyncEngine]:
        if async_mode:
            raise ValueError("SQLite does not support asynchronous mode")

        engine_kwargs = {
            **self._get_base_kwargs(config),
            "connect_args": {
                "check_same_thread": False
            }
        }

        engine_class = create_engine
        return engine_class(self._get_url(config, False), **engine_kwargs)


class EngineFactory:
    """Factory for creating database engines based on database type."""

    _factories: Dict[DatabaseType, Type[DatabaseEngineFactory]] = {
        DatabaseType.POSTGRESQL: PostgresEngineFactory,
        DatabaseType.MYSQL     : MySQLEngineFactory,
        DatabaseType.MARIADB   : MySQLEngineFactory,
        DatabaseType.SQLITE    : SQLiteEngineFactory,
    }

    @classmethod
    def create_engine(cls, config: DatabaseConfig, async_mode: bool = False) -> Union[Engine, AsyncEngine]:
        """Create a database engine based on configuration."""
        factory_class = cls._factories.get(config.type)
        if not factory_class:
            raise ValueError(f"Unsupported database type: {config.type}")

        return factory_class().create_engine(config, async_mode)
