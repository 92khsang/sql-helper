import asyncio
import signal
from contextlib import (
    asynccontextmanager,
    contextmanager,
)
from typing import Optional


@contextmanager
def sync_timeout(seconds: Optional[float]):
    """Timeout context manager for synchronous transactions."""
    if not seconds:
        yield
        return

    def timeout_handler(*_):
        raise TimeoutError("Transaction timeout")

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    try:
        signal.alarm(int(seconds))
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


@asynccontextmanager
async def async_timeout(seconds: Optional[float]):
    """Timeout context manager for asynchronous transactions."""
    if not seconds:
        yield
        return

    async def timeout():
        await asyncio.sleep(seconds)
        raise TimeoutError("Transaction timeout")

    task = asyncio.create_task(timeout())
    try:
        yield
    finally:
        task.cancel()
