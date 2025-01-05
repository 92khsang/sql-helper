from enum import Enum
from typing import (
    Type,
    TypeVar,
    Union,
)


class TransactionMode(str, Enum):
    """Transaction modes."""
    SYNC = "SYNC"
    ASYNC = "ASYNC"


class PropagationType(str, Enum):
    """Transaction propagation types."""
    REQUIRED = "REQUIRED"  # Use existing transaction or create a new one
    REQUIRES_NEW = "REQUIRES_NEW"  # Always create a new transaction
    NESTED = "NESTED"  # Create a nested transaction
    SUPPORTS = "SUPPORTS"  # Use existing transaction (do not create if none exists)
    NOT_SUPPORTED = "NOT_SUPPORTED"  # Execute without a transaction
    NEVER = "NEVER"  # Throw exception if a transaction exists
    MANDATORY = "MANDATORY"  # Throw exception if no existing transaction

    @classmethod
    def validate(cls, value: Union[str, 'PropagationType']) -> 'PropagationType':
        """Validate and convert propagation type value."""
        if isinstance(value, cls):
            return value
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid propagation type: {value}")


RT = TypeVar('RT')
ExceptionTypes = Union[Type[Exception], tuple[Type[Exception], ...]]
