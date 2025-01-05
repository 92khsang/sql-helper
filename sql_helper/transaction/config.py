from dataclasses import (
    dataclass,
    field,
)
from typing import Optional

from .types import (
    ExceptionTypes,
    PropagationType,
    TransactionMode,
)


@dataclass(frozen=True)
class TransactionOptions:
    """Transaction configuration options."""
    mode: TransactionMode = field(default=TransactionMode.SYNC)
    read_only: bool = field(default=False)
    isolation_level: Optional[str] = field(default=None)
    propagation: PropagationType = field(default=PropagationType.REQUIRED)
    timeout: Optional[float] = field(default=None)
    retry_count: int = field(default=0)
    retry_backoff: float = field(default=0.1)
    rollback_for: ExceptionTypes = field(default=(Exception,))

    def __post_init__(self):
        """Validate options after initialization."""
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if self.retry_backoff <= 0:
            raise ValueError("retry_backoff must be positive")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")
