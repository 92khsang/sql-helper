import logging
from contextlib import contextmanager
from typing import (
    Optional,
    Protocol,
)


class Logger(Protocol):
    """Logger interface for SQLHelper operations"""

    def info(self, msg: str, *args, **kwargs) -> None: ...

    def error(self, msg: str, *args, **kwargs) -> None: ...

    def debug(self, msg: str, *args, **kwargs) -> None: ...

    def warning(self, msg: str, *args, **kwargs) -> None: ...


class SQLHelperLogger:
    """
    Singleton logger manager for SQLHelper library.
    Handles default logging configuration and custom logger injection.
    """
    _instance = None
    _logger: Optional[Logger] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_logger(cls) -> Logger:
        """Returns the currently configured logger instance"""
        if cls._logger is None:
            cls._logger = cls._setup_default_logger()
        return cls._logger

    @classmethod
    def set_logger(cls, logger: Logger) -> None:
        """Sets a custom logger for SQLHelper operations"""
        cls._logger = logger

    @classmethod
    def _setup_default_logger(cls) -> logging.Logger:
        """
        Configures and returns the default logger with basic formatting.
        Prevents duplicate handlers by checking existing configurations.
        """
        logger = logging.getLogger("sql_helper")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    @classmethod
    @contextmanager
    def use_logger(cls, logger: Logger):
        """
        Context manager for temporary logger usage.
        Restores the previous logger after the context exits.
        """
        previous_logger = cls._logger
        cls.set_logger(logger)
        try:
            yield
        finally:
            cls._logger = previous_logger


# Convenience functions for global logger access
def get_logger() -> Logger:
    """Global accessor for the current SQLHelper logger"""
    return SQLHelperLogger.get_logger()


def set_logger(logger: Logger) -> None:
    """Global setter for the SQLHelper logger"""
    SQLHelperLogger.set_logger(logger)
