"""  
Transaction management module providing decorators and utilities  
for handling database transactions.  
"""
from .config import TransactionOptions
from .decorator import transactional
from .manager import (
    TransactionManager,
    transaction_manager,
)
from .types import (
    PropagationType,
    TransactionMode,
)

__all__ = [
    'TransactionMode',
    'PropagationType',
    'TransactionOptions',
    'TransactionManager',
    'transaction_manager',
    'transactional',
]
