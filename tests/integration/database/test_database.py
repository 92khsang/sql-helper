import asyncio
from contextlib import asynccontextmanager
from typing import (
    Any,
    Callable,
    Coroutine,
)

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from sql_helper.core.exceptions import DatabaseError


@asynccontextmanager
async def transaction(
    async_db, operation: Callable[[AsyncSession], Coroutine[Any, Any, Any]]
):
    """Manage a transaction context for async operations."""
    async with async_db.get_async_db() as session:
        async with session.begin():
            try:
                yield await operation(session)
            except Exception as e:
                await session.rollback()
                raise e
            else:
                await session.commit()


class TestDatabaseIntegration:
    """Integration tests for Database class."""

    @pytest.fixture(autouse=True)
    async def setup_and_cleanup_table(self, async_db):
        """Setup and cleanup test table before and after each test."""
        async with async_db.get_async_db() as session:
            await session.execute(text("DROP TABLE IF EXISTS test_table"))
            await session.execute(
                text("CREATE TABLE test_table (id SERIAL PRIMARY KEY, value TEXT)")
            )

        yield

        async with async_db.get_async_db() as session:
            await session.execute(text("DROP TABLE IF EXISTS test_table"))

    async def test_async_session_execution(self, async_db):
        """Test async session can execute queries."""
        async with async_db.get_async_db() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_sync_session_execution(self, db):
        """Test sync session can execute queries."""
        with db.get_db() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_async_transaction_commit(self, async_db):
        """Test async transaction commits successfully."""
        test_id = 1
        async with async_db.get_async_db() as session:
            await session.execute(
                text("INSERT INTO test_table (id, value) VALUES (:id, :value)"),
                {
                    "id"   : test_id,
                    "value": "test"
                },
            )

        async with async_db.get_async_db() as session:
            result = await session.execute(
                text("SELECT value FROM test_table WHERE id = :id"),
                {
                    "id": test_id
                },
            )
            assert result.scalar() == "test"

    def test_sync_transaction_commit(self, db):
        """Test sync transaction commits successfully."""
        test_id = 1
        with db.get_db() as session:
            session.execute(
                text("INSERT INTO test_table (id, value) VALUES (:id, :value)"),
                {
                    "id"   : test_id,
                    "value": "test"
                },
            )

        with db.get_db() as session:
            result = session.execute(
                text("SELECT value FROM test_table WHERE id = :id"),
                {
                    "id": test_id
                },
            )
            assert result.scalar() == "test"

    @pytest.mark.asyncio
    async def test_async_transaction_rollback(self, async_db):
        """Test async transaction rolls back on error."""
        async with async_db.get_async_db() as session:
            await session.execute(
                text("INSERT INTO test_table (value) VALUES ('initial')")
            )

        with pytest.raises(DatabaseError):
            async with async_db.get_async_db() as session:
                await session.execute(
                    text("INSERT INTO test_table (value) VALUES ('should_rollback')")
                )
                raise Exception("Simulated error")

        async with async_db.get_async_db() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM test_table"))
            assert result.scalar() == 1  # Only 'initial' record should exist

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, async_db):
        """Test multiple concurrent database operations."""

        async def insert_and_verify(session_, value: str) -> tuple[int, str]:
            """Insert a value and return it with its ID."""
            # Check if the dialect is MySQL
            if session_.bind.dialect.name == "mysql":
                await session_.execute(
                    text("INSERT INTO test_table (value) VALUES (:value)"),
                    {
                        "value": value
                    },
                )
                result = await session_.execute(
                    text("SELECT id, value FROM test_table WHERE value = :value"),
                    {
                        "value": value
                    },
                )
            else:
                # For PostgreSQL or other databases that support RETURNING
                result = await session_.execute(
                    text("INSERT INTO test_table (value) VALUES (:value) RETURNING id, value"),
                    {
                        "value": value
                    },
                )
            return result.first()

        test_values = [f"value{i}" for i in range(3)]

        async def wrapped_transaction(value: str):
            """Wrap transaction as a coroutine."""
            async with transaction(async_db, lambda s: insert_and_verify(s, value)) as result:
                return result

        # When
        results = await asyncio.gather(
            *[wrapped_transaction(value) for value in test_values]
        )

        # Then
        assert len(results) == 3
        assert all(result[1] in test_values for result in results)

        # Verify total count
        async with async_db.get_async_db() as session:
            count = await session.execute(text("SELECT COUNT(*) FROM test_table"))
            assert count.scalar() == 3
