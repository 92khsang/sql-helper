import asyncio
import contextvars
from threading import Lock
from typing import (
    ClassVar,
    Dict,
    Optional,
    Union,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class SessionStack:
    """
    Manages multiple database sessions in a stack-like structure.
    Thread-safe singleton implementation.
    """
    _instance: ClassVar[Optional['SessionStack']] = None
    _init_lock: ClassVar[Lock] = Lock()

    def __new__(cls) -> 'SessionStack':
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        with self._init_lock:
            if getattr(self, '_initialized', False):
                return

            self.sessions: Dict[str, Union[Session, AsyncSession]] = {}
            self._counter: int = 0
            self._lock: Lock = Lock()
            self._async_lock: asyncio.Lock = asyncio.Lock()
            self._counter_lock: Lock = Lock()
            self._initialized = True

    def _get_next_session_id(self) -> str:
        """
        Thread-safe method to get next session ID.

        Returns:
            str: Unique session identifier
        """
        with self._counter_lock:
            session_id = f"session_{self._counter}"
            self._counter += 1
            return session_id

    def push(self, session: Union[Session, AsyncSession]) -> str:
        """
        Add a new session to the stack and return its ID.
        Thread-safe implementation.

        Args:
            session: Database session to add

        Returns:
            str: Unique session identifier
        """
        session_id = self._get_next_session_id()
        with self._lock:
            self.sessions[session_id] = session
            return session_id

    async def async_push(self, session: Union[Session, AsyncSession]) -> str:
        """
        Asynchronously add a new session to the stack and return its ID.

        Args:
            session: Database session to add

        Returns:
            str: Unique session identifier
        """
        session_id = self._get_next_session_id()
        async with self._async_lock:
            self.sessions[session_id] = session
            return session_id

    def pop(self, session_id: str) -> Optional[Union[Session, AsyncSession]]:
        """
        Remove and return a session by its ID.
        Thread-safe implementation.

        Args:
            session_id: Session identifier to remove

        Returns:
            Optional[Session]: Removed session or None if not found
        """
        with self._lock:
            return self.sessions.pop(session_id, None)

    async def async_pop(self, session_id: str) -> Optional[Union[Session, AsyncSession]]:
        """
        Asynchronously remove and return a session by its ID.

        Args:
            session_id: Session identifier to remove

        Returns:
            Optional[Session]: Removed session or None if not found
        """
        async with self._async_lock:
            return self.sessions.pop(session_id, None)

    def get_current(self) -> Optional[Union[Session, AsyncSession]]:
        """
        Get the current active session.
        Thread-safe implementation.

        Returns:
            Optional[Session]: Current session or None if no sessions exist
        """
        with self._lock:
            if not self.sessions:
                return None
                # Create a copy of values to avoid potential race conditions
            sessions = list(self.sessions.values())
            return sessions[-1] if sessions else None

    async def async_get_current(self) -> Optional[Union[Session, AsyncSession]]:
        """
        Asynchronously get the current active session.

        Returns:
            Optional[Session]: Current session or None if no sessions exist
        """
        async with self._async_lock:
            if not self.sessions:
                return None
                # Create a copy of values to avoid potential race conditions
            sessions = list(self.sessions.values())
            return sessions[-1] if sessions else None

    def clear(self) -> None:
        """
        Clear all sessions from the stack.
        Thread-safe implementation.
        """
        with self._lock:
            self.sessions.clear()
            self._counter = 0

    async def async_clear(self) -> None:
        """
        Asynchronously clear all sessions from the stack.
        """
        async with self._async_lock:
            self.sessions.clear()
            self._counter = 0


# Context variable for session stack management
current_session_stack = contextvars.ContextVar('current_session_stack', default=None)
