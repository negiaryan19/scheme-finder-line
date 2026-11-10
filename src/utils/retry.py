"""
Retry Logic with Exponential Backoff and Circuit Breaker

Provides configurable retry policies for transient failures (HTTP 429, 5xx)
and a circuit breaker to prevent cascade failures.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

from utils.exceptions import (
    APIError,
    CircuitBreakerOpenError,
    ConnectionError,
    RateLimitError,
    SchemeFinderError,
    ServerError,
    TimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests rejected immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential_base: Multiplier for exponential backoff (default: 2.0)
        jitter: Jitter factor 0-1 to prevent thundering herd (default: 0.1)
        retryable_exceptions: Exception types that trigger retry
        retryable_status_codes: HTTP status codes that trigger retry
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retryable_exceptions: tuple[type[Exception], ...] = (
        TimeoutError,
        ConnectionError,
        RateLimitError,
        ServerError,
        CircuitBreakerOpenError,
    )
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay,
        )
        # Add jitter
        jitter_amount = delay * self.jitter
        return delay + random.uniform(-jitter_amount, jitter_amount)

    def is_retryable(self, error: Exception) -> bool:
        """Check if an error should trigger a retry."""
        # Check exception type
        if isinstance(error, self.retryable_exceptions):
            return True
        # Check for APIError with retryable status code
        if isinstance(error, APIError):
            if error.status_code in self.retryable_status_codes:
                return True
            # Also check the error's own is_retryable method
            return error.is_retryable()
        return False


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 30.0  # Seconds before half-open
    excluded_exceptions: tuple[type[Exception], ...] = (
        # Don't count these as circuit-breaker failures
        # (they indicate client-side issues, not service health)
        TypeError,
        ValueError,
    )


class CircuitBreaker:
    """
    Circuit breaker to prevent cascade failures.

    State transitions:
    - CLOSED → OPEN: After `failure_threshold` consecutive failures
    - OPEN → HALF_OPEN: After `timeout` seconds
    - HALF_OPEN → CLOSED: After `success_threshold` consecutive successes
    - HALF_OPEN → OPEN: On any failure
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def _should_attempt(self) -> bool:
        """Check if a request should be attempted based on circuit state."""
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed to transition to half-open
            if self._last_failure_time and (
                time.monotonic() - self._last_failure_time >= self.config.timeout
            ):
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' HALF_OPEN after timeout")
                return True
            return False
        # HALF_OPEN: allow one request through
        return True

    async def record_success(self) -> None:
        """Record a successful request."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0  # Reset on success

    async def record_failure(self, error: Exception) -> None:
        """Record a failed request."""
        async with self._lock:
            # Don't count excluded exceptions
            if isinstance(error, self.config.excluded_exceptions):
                return

            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(f"Circuit breaker '{self.name}' OPEN after half-open failure")
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPEN after "
                        f"{self._failure_count} consecutive failures"
                    )

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if not self._should_attempt():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN",
                service=self.name,
            )

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure(e)
            raise


# ==================== RETRY DECORATOR ====================


def with_retry(
    config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to add retry logic with exponential backoff to async functions.

    Args:
        config: RetryConfig instance (uses defaults if None)
        circuit_breaker: Optional CircuitBreaker for cascade protection

    Returns:
        Decorated function with retry logic
    """
    retry_config = config or RetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None

            for attempt in range(retry_config.max_attempts):
                try:
                    # If circuit breaker provided, use it
                    if circuit_breaker:
                        return await circuit_breaker.call(func, *args, **kwargs)
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Check if we should retry
                    if not retry_config.is_retryable(e):
                        logger.debug(
                            f"Non-retryable error in {func.__name__}: {e}",
                            extra={"attempt": attempt + 1, "error_type": type(e).__name__},
                        )
                        raise

                    # Check if we have more attempts
                    if attempt < retry_config.max_attempts - 1:
                        delay = retry_config.calculate_delay(attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{retry_config.max_attempts} for {func.__name__} "
                            f"after {delay:.2f}s: {e}",
                            extra={
                                "attempt": attempt + 1,
                                "max_attempts": retry_config.max_attempts,
                                "delay": delay,
                                "error_type": type(e).__name__,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {retry_config.max_attempts} attempts failed for {func.__name__}: {e}",
                            extra={
                                "max_attempts": retry_config.max_attempts,
                                "error_type": type(e).__name__,
                            },
                        )

            # This shouldn't be reached, but just in case
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


# ==================== CONVENIENCE FUNCTIONS ====================


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with retry logic (non-decorator form).

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: RetryConfig instance
        circuit_breaker: Optional CircuitBreaker
        **kwargs: Keyword arguments for func

    Returns:
        Result of func
    """
    retry_config = config or RetryConfig()
    last_error: Exception | None = None

    for attempt in range(retry_config.max_attempts):
        try:
            if circuit_breaker:
                return await circuit_breaker.call(func, *args, **kwargs)
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if not retry_config.is_retryable(e) or attempt >= retry_config.max_attempts - 1:
                raise
            delay = retry_config.calculate_delay(attempt)
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error


def create_circuit_breaker(name: str, **config_kwargs: Any) -> CircuitBreaker:
    """Factory function to create a CircuitBreaker with custom config."""
    config = CircuitBreakerConfig(**config_kwargs) if config_kwargs else None
    return CircuitBreaker(name, config)