from enum import Enum


class DatabaseType(Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"

    @property
    def sync_driver(self) -> str:
        """Get a sync driver for a database type"""
        drivers = {
            DatabaseType.POSTGRESQL: "postgresql+psycopg",
            DatabaseType.MYSQL     : "mysql+pymysql",
            DatabaseType.MARIADB   : "mysql+pymysql",
            DatabaseType.SQLITE    : "sqlite",
        }
        if self not in drivers:
            raise ValueError(f"No sync driver available for {self.value}")
        return drivers[self]

    @property
    def async_driver(self) -> str:
        """Get an async driver for a database type"""
        drivers = {
            DatabaseType.POSTGRESQL: "postgresql+psycopg",
            DatabaseType.MYSQL     : "mysql+aiomysql",
            DatabaseType.MARIADB   : "mysql+aiomysql",
        }
        if self not in drivers:
            raise ValueError(f"No async driver available for {self.value}")
        return drivers[self]

    @property
    def supports_async(self) -> bool:
        """Check if a database type supports async operations"""
        return self != DatabaseType.SQLITE

    @property
    def supports_charset(self) -> bool:
        """Check if a database type supports charset"""
        return self not in {DatabaseType.SQLITE, DatabaseType.POSTGRESQL}

    @property
    def requires_host(self) -> bool:
        """Check if a database type requires host and port"""
        return self != DatabaseType.SQLITE

    @property
    def requires_auth(self) -> bool:
        """Check if a database type requires authentication"""
        return self != DatabaseType.SQLITE
