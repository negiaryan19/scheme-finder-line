"""
Standardized API Exceptions

Provides a consistent exception hierarchy for all external API interactions
(Prisma STT, Timbre TTS, Evon LLM, Twilio) with automatic HTTP status classification.
"""

from __future__ import annotations

from typing import Any


class SchemeFinderError(Exception):
    """Base exception for all Scheme Finder errors."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(SchemeFinderError):
    """Raised when configuration is invalid or missing (e.g., missing API keys)."""

    pass


class APIError(SchemeFinderError):
    """Base class for all external API errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        service: str | None = None,
        endpoint: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        self.service = service
        self.endpoint = endpoint

    def is_retryable(self) -> bool:
        """Whether this error should trigger a retry."""
        return self.status_code is not None and self.status_code in (429, 500, 502, 503, 504)


class AuthenticationError(APIError):
    """Raised for 401/403 errors — credentials invalid or missing."""

    def is_retryable(self) -> bool:
        return False  # Never retry auth errors


class RateLimitError(APIError):
    """Raised for HTTP 429 — rate limited by the service."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

    def is_retryable(self) -> bool:
        return True


class ServerError(APIError):
    """Raised for 5xx server errors."""

    def is_retryable(self) -> bool:
        return True


class ClientError(APIError):
    """Raised for 4xx client errors (except 401, 403, 429)."""

    def is_retryable(self) -> bool:
        return False


class TimeoutError(SchemeFinderError):
    """Raised when an API request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        timeout_type: str | None = None,  # "connect", "read", "write", "pool"
        service: str | None = None,
        endpoint: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.timeout_type = timeout_type
        self.service = service
        self.endpoint = endpoint

    def is_retryable(self) -> bool:
        return True


class ConnectionError(SchemeFinderError):
    """Raised when a network connection fails."""

    def __init__(
        self,
        message: str = "Connection failed",
        *,
        service: str | None = None,
        endpoint: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.service = service
        self.endpoint = endpoint

    def is_retryable(self) -> bool:
        return True


class ValidationError(SchemeFinderError):
    """Raised when request/response validation fails."""

    def is_retryable(self) -> bool:
        return False


class AudioProcessingError(SchemeFinderError):
    """Raised when audio conversion or processing fails."""

    def is_retryable(self) -> bool:
        return False


class CircuitBreakerOpenError(SchemeFinderError):
    """Raised when circuit breaker is open and rejecting requests."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        *,
        service: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.service = service

    def is_retryable(self) -> bool:
        return True  # Retry after circuit breaker resets


# ==================== HTTP ERROR CLASSIFICATION ====================


def classify_http_error(
    status_code: int,
    response_body: str | None = None,
    service: str | None = None,
    endpoint: str | None = None,
) -> APIError:
    """
    Classify an HTTP status code into the appropriate exception type.

    Args:
        status_code: HTTP status code
        response_body: Optional response body for context
        service: Name of the service (e.g., "prisma-stt", "timbre-tts")
        endpoint: API endpoint that was called

    Returns:
        Appropriate APIError subclass instance
    """
    base_kwargs = {
        "status_code": status_code,
        "response_body": response_body,
        "service": service,
        "endpoint": endpoint,
    }

    if status_code == 401:
        return AuthenticationError(
            f"Authentication failed (401): Invalid or missing API key",
            **base_kwargs,
        )
    elif status_code == 403:
        return AuthenticationError(
            f"Access forbidden (403): Insufficient permissions",
            **base_kwargs,
        )
    elif status_code == 429:
        # Try to extract retry-after header from response body if present
        retry_after = None
        if response_body:
            import re

            match = re.search(r"retry[-\s]?after[\s:\x22]+(\d+)", response_body, re.IGNORECASE)
            if match:
                retry_after = float(match.group(1))
        return RateLimitError(
            f"Rate limited (429): Too many requests",
            retry_after=retry_after,
            **base_kwargs,
        )
    elif 500 <= status_code < 600:
        return ServerError(
            f"Server error ({status_code}): {response_body or 'No response body'}",
            **base_kwargs,
        )
    elif 400 <= status_code < 500:
        return ClientError(
            f"Client error ({status_code}): {response_body or 'No response body'}",
            **base_kwargs,
        )
    else:
        return APIError(
            f"Unexpected HTTP status ({status_code})",
            **base_kwargs,
        )


# ==================== HTTX ERROR WRAPPER ====================


def wrap_httpx_error(
    error: Exception,
    service: str | None = None,
    endpoint: str | None = None,
) -> SchemeFinderError:
    """
    Convert httpx exceptions to SchemeFinderError hierarchy.

    Args:
        error: The caught exception
        service: Service name for context
        endpoint: Endpoint for context

    Returns:
        Appropriate SchemeFinderError subclass
    """
    import httpx

    if isinstance(error, httpx.TimeoutException):
        # Extract timeout type from exception class name (e.g., ReadTimeout -> "read")
        timeout_type = type(error).__name__.lower().replace("timeout", "")
        # Handle base TimeoutException class
        if timeout_type == "exception":
            timeout_type = "timeout"
        return TimeoutError(
            f"Request to {service or 'service'} timed out: {error}",
            timeout_type=timeout_type,
            service=service,
            endpoint=endpoint,
            cause=error,
        )

    if isinstance(error, httpx.ConnectError):
        return ConnectionError(
            f"Connection failed to {service or 'service'}: {error}",
            service=service,
            endpoint=endpoint,
            cause=error,
        )

    if isinstance(error, httpx.HTTPStatusError):
        return classify_http_error(
            status_code=error.response.status_code,
            response_body=error.response.text,
            service=service,
            endpoint=endpoint,
        )

    if isinstance(error, httpx.RequestError):
        return ConnectionError(
            f"Request to {service or 'service'} failed: {error}",
            service=service,
            endpoint=endpoint,
            cause=error,
        )

    # Unknown error — wrap generically
    return SchemeFinderError(
        f"Unexpected error calling {service or 'service'}: {error}",
        service=service,
        endpoint=endpoint,
        cause=error,
    )