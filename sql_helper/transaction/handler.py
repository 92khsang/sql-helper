from contextlib import (
    asynccontextmanager,
    contextmanager,
)
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Generic,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from sqlalchemy import text

from .config import TransactionOptions
from .session import (
    SessionStack,
    current_session_stack,
)
from .timeout import (
    async_timeout,
    sync_timeout,
)
from .types import PropagationType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session
    from ..database import Database

T = TypeVar('T', bound=Union[Session, AsyncSession])
SessionOps = dict[str, Callable[..., Any]]


def _configure_session(session: Session, options: TransactionOptions) -> None:
    """Configure session with transaction options"""
    if options.isolation_level:
        session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {options.isolation_level}"))
    if options.read_only:
        session.execute(text("SET TRANSACTION READ ONLY"))


async def _configure_async_session(session: AsyncSession, options: TransactionOptions) -> None:
    """Configure async session with transaction options"""
    if options.isolation_level:
        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {options.isolation_level}"))
    if options.read_only:
        await session.execute(text("SET TRANSACTION READ ONLY"))


class TransactionError(str, Enum):
    NEVER_EXISTS = "Transaction already exists (NEVER propagation)"
    MANDATORY_REQUIRED = "No existing transaction (MANDATORY propagation)"


class TransactionHandler(Generic[T]):
    """Handles database transaction lifecycle and propagation.

    Args:
        database: Database instance to use for transaction
        options: Transaction configuration options
        is_async: Whether to use async or sync operations
    """

    def __init__(
        self,
        database: Database,
        options: TransactionOptions,
        is_async: bool = False
    ):
        self.database = database
        self.options = options
        self.is_async = is_async
        self.session_stack = current_session_stack.get()
        self.token = None

        if self.session_stack is None:
            self.session_stack = SessionStack()
            self.token = current_session_stack.set(self.session_stack)

    @staticmethod
    async def _handle_session_async(
        session: AsyncSession,
        ops: SessionOps
    ) -> AsyncGenerator[AsyncSession, None]:
        """Yield an async session from the session stack.

        Args:
            session: Async session to add to the stack
            ops: Session operations

        Yields:
            AsyncSession: The session added to the stack
        """

        session_id = await ops['push'](session)
        try:
            yield session
        finally:
            await ops['pop'](session_id)

    @contextmanager
    def _handle_session_sync(
        self,
        session: Session,
        ops: SessionOps
    ) -> Generator[Session, None, None]:
        """Yield a sync session from the session stack.

        Args:
            session: Sync session to add to the stack
            ops: Session operations

        Yields:
            Session: The session added to the stack
        """

        session_id = ops['push'](session)
        try:
            yield session
        finally:
            ops['pop'](session_id)

    async def _handle_required_async(
        self,
        existing_session: Optional[AsyncSession],
        ops: SessionOps
    ) -> AsyncGenerator[AsyncSession, None]:
        """Handle asynchronous transaction based on a propagation type.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            AsyncSession: The session to use for the transaction
        """

        if existing_session is not None:
            async for session in self._handle_session_async(existing_session, ops):
                yield session
            return

        async with ops['get_db']() as session:
            await ops['configure'](session, self.options)
            async for session_ in self._handle_session_async(session, ops):
                yield session_

    @contextmanager
    def _handle_required_sync(
        self,
        existing_session: Optional[Session],
        ops: SessionOps
    ) -> Generator[Session, None, None]:
        """Handle synchronous transaction based on a propagation type.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            Session: The session to use for the transaction
        """

        if existing_session is not None:
            with self._handle_session_sync(existing_session, ops):
                yield existing_session
            return

        with ops['get_db']() as session:
            ops['configure'](session, self.options)
            with self._handle_session_sync(session, ops):
                yield session

    async def _handle_requires_new_async(
        self,
        ops: SessionOps
    ) -> AsyncGenerator[AsyncSession, None]:
        """Handle asynchronous transaction with REQUIRES_NEW propagation.

        Args:
            ops: Session operations

        Yields:
            AsyncSession: The new session to use for the transaction
        """
        async with ops['get_db']() as session:
            await ops['configure'](session, self.options)
            async for session_ in self._handle_session_async(session, ops):
                yield session_

    @contextmanager
    def _handle_requires_new_sync(
        self,
        ops: SessionOps
    ) -> Generator[Session, None, None]:
        """Handle synchronous transaction based on a propagation type.

        Args:
            ops: Session operations

        Yields:
            Session: The session to use for the transaction
        """

        with ops['get_db']() as session:
            ops['configure'](session, self.options)
            with self._handle_session_sync(session, ops):
                yield session

    async def _handle_supports_async(
        self,
        existing_session: Optional[AsyncSession],
        ops: SessionOps
    ) -> AsyncGenerator[Optional[AsyncSession], None]:
        """Handle asynchronous transaction with SUPPORTS propagation.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            Optional[AsyncSession]: The session if exists, None otherwise
        """
        if existing_session is not None:
            async for session in self._handle_session_async(existing_session, ops):
                yield session
        else:
            yield None

    @contextmanager
    def _handle_supports_sync(
        self,
        existing_session: Optional[Session],
        ops: SessionOps
    ) -> Generator[Optional[Session], None, None]:
        """Handle synchronous transaction based on a propagation type.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            Optional[Session]: The session to use for the transaction or None if no existing session
        """

        if existing_session is not None:
            with self._handle_session_sync(existing_session, ops):
                yield existing_session
        else:
            yield None

    def _get_propagation_handler(self) -> dict[PropagationType, Callable]:
        """Get the appropriate handler for the propagation type.

        Returns:
            Dictionary mapping propagation types to their handlers:
            - REQUIRED: Uses existing transaction if available, creates new one if not
            - REQUIRES_NEW: Always creates new transaction
            - SUPPORTS: Uses existing transaction if available, proceeds without if not
            - NEVER: Errors if transaction exists, proceeds without if not
            - MANDATORY: Uses existing transaction, errors if none exists
        """

        if self.is_async:
            return {
                PropagationType.REQUIRED    : self._handle_required_async,
                PropagationType.REQUIRES_NEW: self._handle_requires_new_async,
                PropagationType.SUPPORTS    : self._handle_supports_async,
                PropagationType.NEVER       : self._handle_never,
                PropagationType.MANDATORY   : self._handle_mandatory_async,
            }
        else:
            return {
                PropagationType.REQUIRED    : self._handle_required_sync,
                PropagationType.REQUIRES_NEW: self._handle_requires_new_sync,
                PropagationType.SUPPORTS    : self._handle_supports_sync,
                PropagationType.NEVER       : self._handle_never,
                PropagationType.MANDATORY   : self._handle_mandatory_sync,
            }

    async def handle_async(self) -> AsyncGenerator[Optional[AsyncSession], None]:
        """
        Handle asynchronous transaction based on a propagation type.

        Yields:
            Optional[AsyncSession]: Database session
        """

        try:
            async with async_timeout(self.options.timeout):
                existing_session = self.session_stack.get_current() if self.session_stack else None
                ops = {
                    'push'     : self.session_stack.async_push,
                    'pop'      : self.session_stack.async_pop,
                    'configure': _configure_async_session,
                    'get_db'   : self.database.get_async_db,
                }
                handler = self._get_propagation_handler()[self.options.propagation]
                async for session in handler(existing_session, ops):
                    yield session
        finally:
            if self.token is not None:
                current_session_stack.reset(self.token)

    @contextmanager
    def handle_sync(self) -> Generator[Optional[Session], None, None]:
        """
        Handle synchronous transaction based on a propagation type.

        Yields:
            Optional[Session]: Database session
        """

        try:
            with sync_timeout(self.options.timeout):
                existing_session = self.session_stack.get_current() if self.session_stack else None
                ops = {
                    'push'     : self.session_stack.push,
                    'pop'      : self.session_stack.pop,
                    'configure': _configure_session,
                    'get_db'   : self.database.get_db,
                }
                handler = self._get_propagation_handler()[self.options.propagation]
                with handler(existing_session, ops) as session:
                    yield session
        finally:
            if self.token is not None:
                current_session_stack.reset(self.token)

    @staticmethod
    def _handle_never(
        existing_session: Optional[T],
        *_,
    ) -> Generator[Optional[T], None, None]:
        """
        Handle 'NEVER' transaction propagation type.

        If an existing session is provided, a ValueError is raised.

        Yields:
            Optional[AsyncSession]: None
        """

        if existing_session is not None:
            raise ValueError(TransactionError.NEVER_EXISTS)
        yield None

    async def _handle_mandatory_async(
        self,
        existing_session: Optional[AsyncSession],
        ops: SessionOps
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Handle MANDATORY transaction propagation type.

        If an existing session is not provided, a ValueError is raised.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            AsyncSession: The session to use for the transaction
        """

        if existing_session is None:
            raise ValueError(TransactionError.MANDATORY_REQUIRED)
        async for session in self._handle_session_async(existing_session, ops):
            yield session

    @contextmanager
    def _handle_mandatory_sync(
        self,
        existing_session: Optional[Session],
        ops: SessionOps
    ) -> Generator[Session, None, None]:
        """
        Handle MANDATORY transaction propagation type.

        If an existing session is not provided, a ValueError is raised.

        Args:
            existing_session: Existing session to re-use
            ops: Session operations

        Yields:
            Session: The session to use for the transaction
        """

        if existing_session is None:
            raise ValueError(TransactionError.MANDATORY_REQUIRED)
        with self._handle_session_sync(existing_session, ops):
            yield existing_session


@contextmanager
def handle_sync_transaction(
    database: Database,
    options: TransactionOptions,
) -> Generator[Optional[Session], None, None]:
    """
    Handle synchronous transaction based on a propagation type.

    Args:
        database: Database instance
        options: Transaction options

    Yields:
        Optional[Session]: Database session
    """

    handler = TransactionHandler[Session](database, options)
    with handler.handle_sync() as session:
        yield session


@asynccontextmanager
async def handle_async_transaction(
    database: Database,
    options: TransactionOptions,
) -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    Handle asynchronous transaction based on a propagation type.

    Args:
        database: Database instance
        options: Transaction options

    Yields:
        Optional[AsyncSession]: Database session
    """

    handler = TransactionHandler[AsyncSession](database, options, is_async=True)
    async for session in handler.handle_async():
        yield session
