"""Structured logger setup using structlog.

Provides a configured structlog logger factory for consistent logging
throughout PyMotion. Never use print() in library code.
"""

from __future__ import annotations

import structlog


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Logger name, typically the module's __name__.

    Returns:
        Configured BoundLogger instance.
    """
    log: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return log


def configure_logging(*, debug: bool = False) -> None:
    """Configure structlog for PyMotion.

    Sets up structured logging with appropriate processors for
    development (debug=True) or production use.

    Args:
        debug: If True, enable verbose debug output with pretty printing.
    """
    processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
