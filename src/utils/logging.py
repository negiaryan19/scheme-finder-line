"""
Structured Logging Configuration

Provides environment-based structured logging using structlog with
JSON output for production and pretty console output for development.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def get_log_level() -> int:
    """Get log level from environment variable."""
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def get_log_format() -> str:
    """Get log format from environment variable."""
    return os.getenv("LOG_FORMAT", "json").lower()


def configure_logging(
    level: int | None = None,
    format_type: str | None = None,
    service_name: str = "scheme-finder",
) -> None:
    """
    Configure structlog with appropriate processors based on environment.

    Args:
        level: Logging level (defaults to LOG_LEVEL env or INFO)
        format_type: "json" for production, "console" for development
        service_name: Service name for log context
    """
    level = level or get_log_level()
    format_type = format_type or get_log_format()

    # Standard library logging config
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Add service name to all logs
        lambda _, __, event_dict: {**event_dict, "service": service_name},
    ]

    if format_type == "json":
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# ==================== CONTEXT MANAGERS FOR REQUEST SCOPING ====================


class RequestContext:
    """
    Context manager for request-scoped logging context.

    Usage:
        with RequestContext(request_id="req-123", user_id="user-456"):
            logger.info("Processing request")
    """

    def __init__(self, **context: Any):
        self.context = context
        self._tokens: list[structlog.contextvars.Token] = []

    def __enter__(self) -> RequestContext:
        for key, value in self.context.items():
            token = structlog.contextvars.bind_contextvars(**{key: value})
            self._tokens.append(token)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Unbind in reverse order
        for token in reversed(self._tokens):
            structlog.contextvars.unbind_contextvars(token)


# ==================== CONVENIENCE FUNCTIONS ====================


def log_api_call(
    logger: structlog.stdlib.BoundLogger,
    service: str,
    method: str,
    endpoint: str,
    *,
    status_code: int | None = None,
    duration_ms: float | None = None,
    error: Exception | None = None,
    **extra: Any,
) -> None:
    """Log an API call with structured fields."""
    log_data = {
        "service": service,
        "method": method,
        "endpoint": endpoint,
        **extra,
    }
    if status_code is not None:
        log_data["status_code"] = status_code
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    if error:
        log_data["error"] = str(error)
        log_data["error_type"] = type(error).__name__
        logger.error("API call failed", **log_data)
    elif status_code and status_code >= 400:
        logger.warning("API call returned error status", **log_data)
    else:
        logger.info("API call completed", **log_data)


def log_retry_attempt(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    attempt: int,
    max_attempts: int,
    delay: float,
    error: Exception,
) -> None:
    """Log a retry attempt."""
    logger.warning(
        "Retrying operation",
        operation=operation,
        attempt=attempt,
        max_attempts=max_attempts,
        delay_seconds=round(delay, 2),
        error=str(error),
        error_type=type(error).__name__,
    )


def log_circuit_breaker(
    logger: structlog.stdlib.BoundLogger,
    name: str,
    state: str,
    **extra: Any,
) -> None:
    """Log circuit breaker state change."""
    logger.warning(
        "Circuit breaker state change",
        circuit_breaker=name,
        state=state,
        **extra,
    )