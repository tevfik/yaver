"""
Structured Logging Utility for Yaver AI
Provides consistent logging across all modules with proper formatting and levels
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class YaverLogger:
    """Centralized logging configuration for Yaver AI"""

    _loggers = {}

    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        console: bool = True,
    ) -> logging.Logger:
        """
        Get or create a logger with consistent formatting

        Args:
            name: Logger name (usually __name__)
            log_file: Optional log file path
            level: Logging level (default: INFO)
            console: Whether to log to console (default: True)

        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        # Clear existing handlers
        logger.handlers.clear()

        # Formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler with rotation
        if log_file:
            log_path = Path(log_file).expanduser().resolve()
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """Convenience function to get a logger"""
    return YaverLogger.get_logger(name, **kwargs)
