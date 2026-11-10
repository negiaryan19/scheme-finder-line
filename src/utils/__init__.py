"""
Utils Package

Common utilities for audio processing, HTTP retry logic, structured logging,
and standardized exception handling.
"""

from utils.audio import (
    convert_mulaw_to_pcm,
    convert_pcm_to_mulaw,
    get_audio_duration,
    load_audio_file,
    resample_audio,
    save_audio_file,
    split_audio_chunks,
)
from utils.exceptions import (
    APIError,
    AudioProcessingError,
    AuthenticationError,
    CircuitBreakerOpenError,
    ClientError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
    SchemeFinderError,
    ServerError,
    TimeoutError,
    ValidationError,
    classify_http_error,
    wrap_httpx_error,
)
from utils.logging import (
    RequestContext,
    configure_logging,
    get_logger,
    log_api_call,
    log_circuit_breaker,
    log_retry_attempt,
)
from utils.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryConfig,
    create_circuit_breaker,
    retry_async,
    with_retry,
)

__all__ = [
    # Audio
    "load_audio_file",
    "save_audio_file",
    "convert_mulaw_to_pcm",
    "convert_pcm_to_mulaw",
    "resample_audio",
    "get_audio_duration",
    "split_audio_chunks",
    # Exceptions
    "SchemeFinderError",
    "ConfigurationError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "TimeoutError",
    "ConnectionError",
    "ValidationError",
    "AudioProcessingError",
    "CircuitBreakerOpenError",
    "classify_http_error",
    "wrap_httpx_error",
    # Retry
    "RetryConfig",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "with_retry",
    "retry_async",
    "create_circuit_breaker",
    # Logging
    "configure_logging",
    "get_logger",
    "RequestContext",
    "log_api_call",
    "log_retry_attempt",
    "log_circuit_breaker",
]