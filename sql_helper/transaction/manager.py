from threading import Lock
from typing import (
    Dict,
    Optional,
)

from ..core import get_logger
from ..database import Database


class TransactionManager:
    """Thread-safe transaction manager for database connections."""

    def __init__(self):
        self._databases: Dict[str, Database] = {}
        self._lock = Lock()
        self._logger = get_logger()

    def register_database(
        self,
        name: str,
        database: Database,
        *,
        override: bool = False
    ) -> None:
        """
        Register a database instance with a name.

        Args:
            name: Database identifier
            database: Database instance
            override: Allow overriding existing registration
        """
        with self._lock:
            if name in self._databases and not override:
                raise ValueError(f"Database '{name}' already registered")
            self._databases[name] = database
            self._logger.info(f"Database '{name}' registered successfully")

    def get_database(self, name: str) -> Database:
        """
        Get a registered database by name.

        Raises:
            KeyError: If a database is not registered
        """
        with self._lock:
            if name not in self._databases:
                raise KeyError(f"Database '{name}' not registered")
            return self._databases[name]

    def unregister_database(self, name: str) -> Optional[Database]:
        """
        Unregister a database instance.

        Returns:
            The unregistered database instance or None
        """
        with self._lock:
            if db := self._databases.pop(name, None):
                self._logger.info(f"Database '{name}' unregistered")
                return db
            return None

    def clear(self) -> None:
        """Remove all registered databases."""
        with self._lock:
            self._databases.clear()
            self._logger.info("All databases unregistered")


# Global singleton instance
transaction_manager = TransactionManager()
