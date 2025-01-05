from enum import (
    Enum,
)
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
    TypeAlias,
    Union,
)

if TYPE_CHECKING:
    from .logging import Logger

from .logging import get_logger

ErrorDetails: TypeAlias = Dict[str, Any]


class ErrorCode(str, Enum):
    """Error codes with auto-generation"""
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class SQLHelperException(Exception):
    """
    Base exception class for SQLHelper.

    Attributes:
        message (str): Human-readable error message
        code (ErrorCode): Error code for categorizing errors
        details (Dict[str, Any]): Additional error details
    """

    if TYPE_CHECKING:
        _logger: Logger

    _logger = get_logger()

    def __init__(
        self,
        message: str,
        code: Union[ErrorCode, str] = ErrorCode.INTERNAL_ERROR,
        details: Optional[ErrorDetails] = None,
        parent: Optional[Exception] = None
    ) -> None:
        """
        Initialize SQLHelper exception.

        Args:
            message: Human-readable error message
            code: Error code for categorizing errors
            details: Additional error details
        """
        self.message = message
        self.code = ErrorCode(code) if isinstance(code, str) else code
        self.details = details or {}
        self.parent = parent

        self._log_error()
        super().__init__(message)

    def _log_error(self) -> None:
        """Log the error with structured details."""
        log_details = {
            "error_code"   : self.code.value,
            "error_message": self.message,
            "error_details": self.details,
        }

        # Include parent exception if available
        if self.parent:
            log_details["parent_error"] = str(self.parent)
            log_details["parent_type"] = type(self.parent).__name__

        self._logger.error(f"Exception occurred: {self.code}", extra=log_details)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format.

        Returns:
            Dictionary representation of the exception.
        """
        error_dict = {
            "code"   : self.code.value,
            "message": self.message,
            "details": self.details
        }

        # Include parent exception if available
        if self.parent:
            error_dict["parent"] = {
                "message": str(self.parent),
                "type"   : type(self.parent).__name__,
            }

        return {
            "error": error_dict
        }


class DatabaseError(SQLHelperException):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize database error.

        Args:
            message: Human-readable error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            details=details
        )


class NotFoundError(SQLHelperException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize not found error.

        Args:
            message: Human-readable error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            details=details
        )


class ValidationError(SQLHelperException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str = "Validation error occurred",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Human-readable error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=details
        )


def format_error_details(error: Exception) -> Dict[str, Any]:
    """Format exception details for logging and error reporting."""
    return {
        "error"       : str(error),
        "error_type"  : type(error).__name__,
        "error_module": error.__class__.__module__
    }
