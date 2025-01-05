from __future__ import annotations

from contextlib import (
    asynccontextmanager,
    contextmanager,
)
from typing import (
    AsyncGenerator,
    Generator,
    Optional,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from .config import DatabaseConfig
from .engine import EngineFactory
from ..core import (
    DatabaseError,
    format_error_details,
    get_logger,
)

if TYPE_CHECKING:
    from sqlalchemy.engine.base import (
        Connection,
        Engine,
    )
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
    )
    from sqlalchemy.ext.asyncio.engine import AsyncConnection
    from ..core import Logger

    # Type aliases
    SyncSessionContext = Generator[Session, None, None]
    AsyncSessionContext = AsyncGenerator[AsyncSession, None]
    SyncConnectionContext = Generator[Connection, None, None]
    AsyncConnectionContext = AsyncGenerator[AsyncConnection, None]


class Database:
    """
    SQLAlchemy database connection manager with connection pooling.
    Supports both synchronous and asynchronous operations.
    """

    if TYPE_CHECKING:
        config: DatabaseConfig
        _logger: Logger
        _sync_engine: Optional[Engine]
        _async_engine: Optional[AsyncEngine]
        _sync_session_factory: Optional[sessionmaker]
        _async_session_factory: Optional[async_sessionmaker]
        _is_sync_initialized: bool
        _is_async_initialized: bool

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize the database manager."""
        self.config = config
        self._logger = get_logger()

        # Initialize engines and session factories
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None

        # Lazy initialization flags
        self._is_sync_initialized = False
        self._is_async_initialized = False

    def _create_engine(self, async_mode: bool = False) -> Union[Engine, AsyncEngine]:
        """Create database engine based on mode."""
        return EngineFactory.create_engine(self.config, async_mode)

    def _initialize_sync(self) -> None:
        """Initialize the synchronous engine and session factory."""
        if self._is_sync_initialized:
            return
        try:
            self._sync_engine = self._create_engine()
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            self._is_sync_initialized = True
            self._logger.info("Synchronous database initialized successfully.")
        except Exception as e:
            self._log_and_raise_error("Failed to initialize sync database", e)

    def _initialize_async(self) -> None:
        """Initialize the asynchronous engine and session factory."""
        if self._is_async_initialized:
            return
        try:
            if not self.config.enable_async:
                raise ValueError("Async support is not enabled in configuration.")

            self._async_engine = self._create_engine(async_mode=True)
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            self._is_async_initialized = True
            self._logger.info("Asynchronous database initialized successfully.")
        except Exception as e:
            self._log_and_raise_error("Failed to initialize async database", e)

    def _log_and_raise_error(self, message: str, exception: Exception) -> None:
        """Log an error and raise a DatabaseError."""
        error_details = format_error_details(exception)
        self._logger.error(f"{message}: {error_details}")
        raise DatabaseError(details=error_details) from exception

    @property
    def engine(self) -> Engine:
        """Get the synchronous SQLAlchemy engine instance."""
        if self._sync_engine is None:
            self._initialize_sync()
        return self._sync_engine

    @property
    def async_engine(self) -> AsyncEngine:
        """Get the asynchronous SQLAlchemy engine instance."""
        if self._async_engine is None:
            self._initialize_async()
        return self._async_engine

    @contextmanager
    def get_db(self) -> Generator["Session", None, None]:
        """Synchronous database session context manager."""
        self._initialize_sync()
        session = self._sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self._log_and_raise_error("Error during synchronous session", e)
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_db(self) -> AsyncGenerator["AsyncSession", None]:
        """Asynchronous database session context manager."""
        self._initialize_async()
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                self._log_and_raise_error("Error during asynchronous session", e)

    def dispose_sync(self) -> None:
        """
        Dispose synchronous engine and reset related states.
        Should be used in synchronous contexts.
        """
        try:
            if self._sync_engine:
                self._sync_engine.dispose()
                self._sync_engine = None
                self._sync_session_factory = None
                self._is_sync_initialized = False
                self._logger.info("Synchronous engine disposed and state reset.")
        except Exception as e:
            self._log_and_raise_error("Error during sync engine disposal", e)

    async def dispose_async(self) -> None:
        """
        Dispose asynchronous engine and reset related states.
        Should be used in asynchronous contexts.
        """
        try:
            if self._async_engine:
                await self._async_engine.dispose()
                self._async_engine = None
                self._async_session_factory = None
                self._is_async_initialized = False
                self._logger.info("Asynchronous engine disposed and state reset.")
        except Exception as e:
            self._log_and_raise_error("Error during async engine disposal", e)
