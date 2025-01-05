import asyncio
import time
from functools import wraps
from traceback import format_exc
from typing import (
    Any,
    Callable,
    Coroutine,
    NoReturn,
    Optional,
    Union,
)

from sqlalchemy.exc import SQLAlchemyError

from .config import TransactionOptions
from .handler import (
    handle_async_transaction,
    handle_sync_transaction,
)
from .manager import transaction_manager
from .types import (
    ExceptionTypes,
    PropagationType,
    RT,
    TransactionMode,
)
from ..core import (
    DatabaseError,
    get_logger,
)
from ..database import Database

logger = get_logger()


def handle_error(error: Exception, retry_remaining: int) -> NoReturn:
    """
    Handle transaction errors and log them.

    Args:
        error: The exception that occurred during the transaction.
        retry_remaining: The number of retry attempts left.

    Logs:
        - A warning message if retries are remaining.
        - An error message if no retries are remaining.
    """

    if retry_remaining > 0:
        logger.warning(
            "Transaction failed, retrying",
            extra={
                "error"          : str(error),
                "retry_remaining": retry_remaining,
                "error_type"     : type(error).__name__,
            }
        )
        return
    else:
        logger.error(
            "Transaction failed",
            extra={
                "error"     : str(error),
                "error_type": type(error).__name__,
                "traceback" : format_exc()
            },
            exc_info=True
        )
        if isinstance(error, SQLAlchemyError):
            raise DatabaseError(f"Database error after all retries") from error
        raise


async def retry_async(
    func: Callable[[], Coroutine[Any, Any, RT]],
    options: TransactionOptions,
) -> RT:
    """
    Handle async retry logic for transactions.

    Args:
        func: The coroutine to retry.
        options: The transaction options containing retry configuration.

    Returns:
        The result of the coroutine.
    """
    retry_remaining = options.retry_count

    while retry_remaining >= 0:
        try:
            return await func()
        except options.rollback_for as e:
            if retry_remaining <= 0:
                handle_error(e, retry_remaining)
            retry_remaining -= 1
            await asyncio.sleep(options.retry_backoff)
    raise RuntimeError("Unreachable code")


def retry_sync(
    func: Callable[[], RT],
    options: TransactionOptions,
) -> RT:
    """
    Handle sync retry logic for transactions.

    Args:
        func: The function to retry.
        options: The transaction options containing retry configuration.

    Returns:
        The result of the function.
    """
    retry_remaining = options.retry_count

    while retry_remaining >= 0:
        try:
            return func()
        except options.rollback_for as e:
            if retry_remaining <= 0:
                handle_error(e, retry_remaining)
            retry_remaining -= 1
            time.sleep(options.retry_backoff)
    raise RuntimeError("Unreachable code")


def transactional(
    db: Union[str, Database] = "default",
    *,
    mode: TransactionMode = TransactionMode.SYNC,
    read_only: bool = False,
    isolation_level: Optional[str] = None,
    propagation: PropagationType = PropagationType.REQUIRED,
    timeout: Optional[float] = None,
    retry_count: int = 0,
    retry_backoff: float = 0.1,
    rollback_for: ExceptionTypes = (Exception,),
) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """
    Transaction management decorator.

    Args:
        db: Database instance or name.
        mode: Transaction mode.
        read_only: Read-only mode.
        isolation_level: Transaction isolation level.
        propagation: Transaction propagation type.
        timeout: Transaction timeout.
        retry_count: Number of retries for transaction failures.
        retry_backoff: Backoff interval between retries.
        rollback_for: Exceptions that trigger a rollback.

    Returns:
        A decorated function.
    """
    options = TransactionOptions(
        mode=mode,
        read_only=read_only,
        isolation_level=isolation_level,
        propagation=propagation,
        timeout=timeout,
        retry_count=retry_count,
        retry_backoff=retry_backoff,
        rollback_for=rollback_for if isinstance(rollback_for, tuple) else (rollback_for,),
    )

    def decorator(func: Callable[..., RT]) -> Callable[..., RT]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> RT:
            database = transaction_manager.get_database(db)

            async def execute() -> RT:
                async with handle_async_transaction(database, options):
                    return await func(*args, **kwargs)

            return await retry_async(execute, options)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> RT:
            database = transaction_manager.get_database(db)

            def execute() -> RT:
                with handle_sync_transaction(database, options):
                    return func(*args, **kwargs)

            return retry_sync(execute, options)

        return async_wrapper if options.mode == TransactionMode.ASYNC else sync_wrapper

    return decorator
