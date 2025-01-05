import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class TestSyncDatabase:
    """Test suite for synchronous database operations."""

    def test_engine_initialization(self, sync_db):
        """Test synchronous engine initialization."""
        assert sync_db._sync_engine is None
        assert not sync_db._is_sync_initialized

        _ = sync_db.engine

        assert sync_db._is_sync_initialized
        assert sync_db._sync_engine is not None
        assert sync_db._sync_session_factory is not None

    def test_session_factory_configuration(self, sync_db):
        """Test session factory configuration."""
        _ = sync_db.engine  # Trigger initialization

        session_factory = sync_db._sync_session_factory
        assert session_factory.kw["autocommit"] is False
        assert session_factory.kw["autoflush"] is False
        assert session_factory.kw["expire_on_commit"] is False

    def test_session_lifecycle(self, sync_db, mocker):
        """Test complete session lifecycle including commit and close."""
        lifecycle_calls = []

        mock_commit = mocker.patch.object(
            Session,
            "commit",
            side_effect=lambda: lifecycle_calls.append("commit"),
        )
        mock_close = mocker.patch.object(
            Session,
            "close",
            side_effect=lambda: lifecycle_calls.append("close"),
        )

        with sync_db.get_db() as session:
            assert isinstance(session, Session)
            assert session.is_active

            assert not mock_commit.called
            assert not mock_close.called

        assert mock_commit.called
        assert mock_close.called
        assert lifecycle_calls == ["commit", "close"]

    def test_session_error_handling(self, sync_db, mocker):
        """Test session error handling and rollback."""
        mock_rollback = mocker.patch.object(Session, "rollback")
        mock_close = mocker.patch.object(Session, "close")

        mocker.patch.object(
            sync_db,
            "_log_and_raise_error",
            side_effect=Exception("Simulated session error"),
        )

        with pytest.raises(Exception, match="Simulated session error"):
            with sync_db.get_db() as session:
                assert session.is_active
                raise Exception("Simulated session error")

        mock_rollback.assert_called_once()
        mock_close.assert_called_once()

    def test_dispose_engine(self, sync_db):
        """Test engine disposal and session cleanup."""
        _ = sync_db.engine  # Initialize engine

        with sync_db.get_db() as session:
            assert session.is_active

        sync_db.dispose_sync()

        assert sync_db._sync_engine is None
        assert sync_db._sync_session_factory is None
        assert not sync_db._is_sync_initialized


class TestAsyncDatabase:
    """Test suite for asynchronous database operations."""

    @pytest.mark.asyncio
    async def test_engine_initialization(self, async_db):
        """Test asynchronous engine initialization."""
        assert async_db._async_engine is None
        assert not async_db._is_async_initialized

        _ = async_db.async_engine

        assert async_db._is_async_initialized
        assert async_db._async_engine is not None
        assert async_db._async_session_factory is not None

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, async_db, mocker):
        """
        Test the lifecycle of an asynchronous database session.

        Args:
            async_db: The asynchronous database fixture.
            mocker: Pytest mocker fixture for mocking dependencies.
        """
        # Mock the session commit and rollback methods
        mock_commit = mocker.patch.object(AsyncSession, "commit", autospec=True)
        mock_rollback = mocker.patch.object(AsyncSession, "rollback", autospec=True)

        # Initialize the async engine
        _ = async_db.async_engine

        # Ensure the async engine and session factory are initialized
        assert async_db._async_engine is not None
        assert async_db._async_session_factory is not None
        assert async_db._is_async_initialized

        # Test the session lifecycle with a successful operation
        async with async_db.get_async_db() as session:
            # Ensure the session is an instance of AsyncSession
            assert isinstance(session, AsyncSession)

        # Verify commit was called once
        assert mock_commit.call_count == 1
        assert mock_rollback.call_count == 0  # No rollback in a successful case

        # Test the session lifecycle with an error
        mocker.patch.object(
            async_db,
            "_log_and_raise_error",
            side_effect=Exception("Simulated session error"),
        )

        with pytest.raises(Exception, match="Simulated session error"):
            async with async_db.get_async_db():
                # Trigger an error during the session
                raise Exception("Simulated session error")

        # Verify rollback was called once during the error scenario
        assert mock_rollback.call_count == 1
        assert mock_commit.call_count == 1  # No new commit after the initial one

    @pytest.mark.asyncio
    async def test_dispose_engine(self, async_db):
        """Test async engine disposal."""
        _ = async_db.async_engine

        assert async_db._async_engine is not None
        assert async_db._async_session_factory is not None
        assert async_db._is_async_initialized

        await async_db.dispose_async()

        assert async_db._async_engine is None
        assert async_db._async_session_factory is None
        assert not async_db._is_async_initialized
