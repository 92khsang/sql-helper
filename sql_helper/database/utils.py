from typing import (
    List,
    TYPE_CHECKING,
)
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from .config import DatabaseConfigProtocol


class DatabaseConfigValidator:
    """Validator for database configuration."""

    @staticmethod
    def validate(config: 'DatabaseConfigProtocol') -> None:
        """Validate database configuration."""
        DatabaseConfigValidator._validate_charset(config)
        DatabaseConfigValidator._validate_credentials(config)
        DatabaseConfigValidator._validate_async_support(config)
        DatabaseConfigValidator._validate_port(config)
        DatabaseConfigValidator._validate_database(config)
        DatabaseConfigValidator._validate_pool_settings(config)

    @staticmethod
    def _validate_charset(config: 'DatabaseConfigProtocol') -> None:
        """Validate database charset."""
        if config.charset and not config.type.supports_charset:
            raise ValueError(f"{config.type.value} does not support charset")

    @staticmethod
    def _validate_credentials(config: 'DatabaseConfigProtocol') -> None:
        """Validate database credentials."""
        if config.type.requires_auth:
            if not config.credentials:
                raise ValueError(f"{config.type.value} requires credentials")
            if not config.credentials.username or not config.credentials.password:
                raise ValueError("Both username and password must be provided")

    @staticmethod
    def _validate_async_support(config: 'DatabaseConfigProtocol') -> None:
        """Validate async support."""
        if config.enable_async and not config.type.supports_async:
            raise ValueError(f"{config.type.value} does not support async operations")

    @staticmethod
    def _validate_port(config: 'DatabaseConfigProtocol') -> None:
        """Validate port number."""
        if not (0 <= config.port <= 65535):
            raise ValueError(f"Invalid port number: {config.port}")

    @staticmethod
    def _validate_database(config: 'DatabaseConfigProtocol') -> None:
        """Validate database name."""
        if not config.database:
            raise ValueError("Database name cannot be empty")

    @staticmethod
    def _validate_pool_settings(config: 'DatabaseConfigProtocol') -> None:
        """Validate connection pool settings."""
        if config.pool_size < 1:
            raise ValueError("Pool size must be at least 1")
        if config.max_overflow < 0:
            raise ValueError("Max overflow must be non-negative")
        if config.pool_timeout < 0:
            raise ValueError("Pool timeout must be non-negative")
        if config.pool_recycle < 0:
            raise ValueError("Pool recycle must be non-negative")


class DatabaseURLBuilder:
    """Database URL builder with support for different database types."""

    @staticmethod
    def build_url(config: 'DatabaseConfigProtocol', async_mode: bool = False) -> str:
        """Build database URL based on configuration."""
        if async_mode and not config.type.supports_async:
            raise ValueError(f"{config.type.value} does not support async operations")

        if config.type.value == "sqlite":
            return f"sqlite:///{config.database}"

        driver = config.type.async_driver if async_mode else config.type.sync_driver
        auth = DatabaseURLBuilder._build_auth_string(config)
        params = DatabaseURLBuilder._build_query_params(config)
        query_string = "?" + "&".join(params) if params else ""

        return f"{driver}://{auth}{config.host}:{config.port}/{config.database}{query_string}"

    @staticmethod
    def _build_query_params(config: 'DatabaseConfigProtocol') -> List[str]:
        """Build query parameters for database URL."""
        params = []
        if config.charset and config.type.supports_charset:
            params.append(f"charset={quote_plus(config.charset)}")
        if config.schema and config.type.value == "postgresql":
            params.append(f"options=-c%20search_path={quote_plus(config.schema)}")
        return params

    @staticmethod
    def _build_auth_string(config: 'DatabaseConfigProtocol') -> str:
        """Build authentication string for database URL."""
        if not config.credentials or not config.type.requires_auth:
            return ""
        return f"{quote_plus(config.credentials.username)}:{quote_plus(config.credentials.password)}@"
