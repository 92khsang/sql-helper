import os
from dataclasses import dataclass
from typing import (
    Optional,
    Protocol,
)

from .types import DatabaseType
from .utils import (
    DatabaseConfigValidator,
    DatabaseURLBuilder,
)


@dataclass(frozen=True)
class DatabaseCredentials:
    """Database credentials configuration"""
    username: str
    password: str


@dataclass(frozen=True)
class SSLConfig:
    """SSL configuration."""
    enabled: bool = False
    ca_cert: Optional[str] = None
    client_cert: Optional[str] = None
    client_key: Optional[str] = None
    verify_cert: bool = True

    def __post_init__(self):
        """Validate SSL configuration."""
        if self.enabled:
            for field in ["ca_cert", "client_cert", "client_key"]:
                value = getattr(self, field)
                if value and not os.path.isfile(value):
                    raise ValueError(f"Invalid file path for {field}: {value}")


class DatabaseConfigProtocol(Protocol):
    """Protocol defining the required attributes for database configuration."""
    type: DatabaseType
    database: str
    host: Optional[str]
    port: Optional[int]
    credentials: Optional[DatabaseCredentials]
    ssl: Optional[SSLConfig]
    charset: Optional[str]
    schema: Optional[str]
    enable_async: bool
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    pool_pre_ping: bool
    echo_sql: bool


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration"""
    type: DatabaseType
    database: str
    host: Optional[str] = None
    port: Optional[int] = None
    credentials: Optional[DatabaseCredentials] = None
    ssl: Optional[SSLConfig] = None
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    enable_async: bool = False
    charset: Optional[str] = None
    schema: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        DatabaseConfigValidator.validate(self)

    @property
    def url(self) -> str:
        """Get synchronous database URL."""
        return DatabaseURLBuilder.build_url(self)

    @property
    def async_url(self) -> str:
        """Get asynchronous database URL."""
        return DatabaseURLBuilder.build_url(self, async_mode=True)

    @property
    def pool_settings(self) -> dict:
        """Get connection pool settings."""
        return {
            "pool_size"    : self.pool_size,
            "max_overflow" : self.max_overflow,
            "pool_timeout" : self.pool_timeout,
            "pool_recycle" : self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
        }

    @property
    def engine_settings(self) -> dict:
        """Get engine configuration settings."""
        return {
            "echo": self.echo_sql,
            **self.pool_settings
        }
