"""
Unit Tests for Utils Modules

Tests exception classification, retry logic, circuit breaker transitions,
structured logging, and audio utilities.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.exceptions import (
    APIError,
    AuthenticationError,
    CircuitBreakerOpenError,
    ClientError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
    ServerError,
    SchemeFinderError,
    TimeoutError,
    ValidationError,
    AudioProcessingError,
    classify_http_error,
    wrap_httpx_error,
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
from utils.logging import (
    RequestContext,
    configure_logging,
    get_log_format,
    get_log_level,
    get_logger,
    log_api_call,
    log_circuit_breaker,
    log_retry_attempt,
)


# ==================== TESTS: EXCEPTIONS ====================


class TestExceptionHierarchy:
    """Test exception class hierarchy and behavior."""

    def test_scheme_finder_error_base(self):
        """Test base exception."""
        err = SchemeFinderError("base error", details={"key": "value"})
        assert str(err) == "base error | Details: {'key': 'value'}"
        assert err.details == {"key": "value"}

    def test_scheme_finder_error_no_details(self):
        """Test base exception without details."""
        err = SchemeFinderError("simple error")
        assert str(err) == "simple error"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        err = ConfigurationError("config missing")
        assert isinstance(err, SchemeFinderError)
        assert str(err) == "config missing"

    def test_api_error_base(self):
        """Test APIError base class."""
        err = APIError("api error", status_code=500, service="test", endpoint="/api")
        assert err.status_code == 500
        assert err.service == "test"
        assert err.endpoint == "/api"
        assert err.is_retryable() is True  # 500 is retryable

    def test_authentication_error(self):
        """Test AuthenticationError (401/403)."""
        err = AuthenticationError("invalid key", status_code=401)
        assert err.is_retryable() is False  # Never retry auth errors

    def test_rate_limit_error(self):
        """Test RateLimitError (429)."""
        err = RateLimitError("rate limited", retry_after=30.0, status_code=429)
        assert err.retry_after == 30.0
        assert err.is_retryable() is True

    def test_server_error(self):
        """Test ServerError (5xx)."""
        err = ServerError("server down", status_code=503)
        assert err.is_retryable() is True

    def test_client_error(self):
        """Test ClientError (4xx except 401,403,429)."""
        err = ClientError("bad request", status_code=400)
        assert err.is_retryable() is False

    def test_timeout_error(self):
        """Test TimeoutError."""
        err = TimeoutError("request timed out", timeout_type="read")
        assert err.timeout_type == "read"
        assert err.is_retryable() is True

    def test_connection_error(self):
        """Test ConnectionError."""
        err = ConnectionError("connection failed")
        assert err.is_retryable() is True

    def test_validation_error(self):
        """Test ValidationError."""
        err = ValidationError("invalid input")
        assert err.is_retryable() is False

    def test_audio_processing_error(self):
        """Test AudioProcessingError."""
        err = AudioProcessingError("conversion failed")
        assert err.is_retryable() is False

    def test_circuit_breaker_open_error(self):
        """Test CircuitBreakerOpenError."""
        err = CircuitBreakerOpenError("circuit open", service="test-service")
        assert err.service == "test-service"
        assert err.is_retryable() is True


class TestHTTPErrorClassification:
    """Test classify_http_error function."""

    def test_classify_401(self):
        """Test 401 -> AuthenticationError."""
        err = classify_http_error(401, "Unauthorized", "test-service", "/api")
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 401
        assert err.service == "test-service"

    def test_classify_403(self):
        """Test 403 -> AuthenticationError."""
        err = classify_http_error(403, "Forbidden", "test-service", "/api")
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 403

    def test_classify_429_with_retry_after(self):
        """Test 429 -> RateLimitError with retry-after extraction."""
        body = '{"error": "rate limited", "retry-after": 60}'
        err = classify_http_error(429, body, "test-service", "/api")
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 60.0

    def test_classify_429_without_retry_after(self):
        """Test 429 -> RateLimitError without retry-after."""
        err = classify_http_error(429, "rate limited", "test-service", "/api")
        assert isinstance(err, RateLimitError)
        assert err.retry_after is None

    def test_classify_500(self):
        """Test 500 -> ServerError."""
        err = classify_http_error(500, "Internal Server Error", "test-service", "/api")
        assert isinstance(err, ServerError)
        assert err.status_code == 500

    def test_classify_502(self):
        """Test 502 -> ServerError."""
        err = classify_http_error(502, "Bad Gateway", "test-service", "/api")
        assert isinstance(err, ServerError)

    def test_classify_503(self):
        """Test 503 -> ServerError."""
        err = classify_http_error(503, "Service Unavailable", "test-service", "/api")
        assert isinstance(err, ServerError)

    def test_classify_504(self):
        """Test 504 -> ServerError."""
        err = classify_http_error(504, "Gateway Timeout", "test-service", "/api")
        assert isinstance(err, ServerError)

    def test_classify_400(self):
        """Test 400 -> ClientError."""
        err = classify_http_error(400, "Bad Request", "test-service", "/api")
        assert isinstance(err, ClientError)
        assert err.status_code == 400

    def test_classify_404(self):
        """Test 404 -> ClientError."""
        err = classify_http_error(404, "Not Found", "test-service", "/api")
        assert isinstance(err, ClientError)

    def test_classify_unknown(self):
        """Test unknown status -> generic APIError."""
        err = classify_http_error(999, "Unknown", "test-service", "/api")
        assert isinstance(err, APIError)
        assert not isinstance(err, (AuthenticationError, RateLimitError, ServerError, ClientError))


class TestWrapHttpxError:
    """Test wrap_httpx_error function."""

    def test_wrap_timeout_exception(self):
        """Test wrapping httpx.TimeoutException."""
        import httpx

        exc = httpx.TimeoutException("timeout")
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, TimeoutError)
        assert err.timeout_type == "timeout"
        assert err.cause is exc

    def test_wrap_connect_error(self):
        """Test wrapping httpx.ConnectError."""
        import httpx

        exc = httpx.ConnectError("connection failed")
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, ConnectionError)
        assert err.cause is exc

    def test_wrap_http_status_error_401(self):
        """Test wrapping httpx.HTTPStatusError 401."""
        import httpx

        request = httpx.Request("GET", "https://api.test.com")
        response = httpx.Response(401, text="Unauthorized", request=request)
        exc = httpx.HTTPStatusError("401", request=request, response=response)
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 401

    def test_wrap_http_status_error_429(self):
        """Test wrapping httpx.HTTPStatusError 429."""
        import httpx

        request = httpx.Request("GET", "https://api.test.com")
        response = httpx.Response(429, text='{"retry-after": 30}', request=request)
        exc = httpx.HTTPStatusError("429", request=request, response=response)
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 30.0

    def test_wrap_http_status_error_500(self):
        """Test wrapping httpx.HTTPStatusError 500."""
        import httpx

        request = httpx.Request("GET", "https://api.test.com")
        response = httpx.Response(500, text="Server Error", request=request)
        exc = httpx.HTTPStatusError("500", request=request, response=response)
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, ServerError)

    def test_wrap_generic_request_error(self):
        """Test wrapping generic httpx.RequestError."""
        import httpx

        exc = httpx.RequestError("generic error")
        err = wrap_httpx_error(exc, service="test", endpoint="/api")
        assert isinstance(err, ConnectionError)


# ==================== TESTS: RETRY CONFIG ====================


class TestRetryConfig:
    """Test RetryConfig behavior."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == 0.1

    def test_calculate_delay_exponential(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=0.0)
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(10) == 60.0  # Capped at max_delay

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation includes jitter."""
        config = RetryConfig(base_delay=10.0, jitter=0.1)
        delays = [config.calculate_delay(0) for _ in range(100)]
        # All delays should be within 10% of base
        assert all(9.0 <= d <= 11.0 for d in delays)

    def test_is_retryable_timeout_error(self):
        """Test TimeoutError is retryable."""
        config = RetryConfig()
        assert config.is_retryable(TimeoutError("timeout")) is True

    def test_is_retryable_connection_error(self):
        """Test ConnectionError is retryable."""
        config = RetryConfig()
        assert config.is_retryable(ConnectionError("connection failed")) is True

    def test_is_retryable_rate_limit_error(self):
        """Test RateLimitError is retryable."""
        config = RetryConfig()
        assert config.is_retryable(RateLimitError("rate limited")) is True

    def test_is_retryable_server_error(self):
        """Test ServerError is retryable."""
        config = RetryConfig()
        assert config.is_retryable(ServerError("server error")) is True

    def test_is_retryable_circuit_breaker_open(self):
        """Test CircuitBreakerOpenError is retryable."""
        config = RetryConfig()
        assert config.is_retryable(CircuitBreakerOpenError("open")) is True

    def test_is_retryable_authentication_error(self):
        """Test AuthenticationError is NOT retryable."""
        config = RetryConfig()
        assert config.is_retryable(AuthenticationError("auth failed")) is False

    def test_is_retryable_client_error(self):
        """Test ClientError is NOT retryable."""
        config = RetryConfig()
        assert config.is_retryable(ClientError("bad request")) is False

    def test_is_retryable_validation_error(self):
        """Test ValidationError is NOT retryable."""
        config = RetryConfig()
        assert config.is_retryable(ValidationError("invalid")) is False

    def test_is_retryable_api_error_with_status(self):
        """Test APIError with retryable status code."""
        config = RetryConfig()
        err = APIError("error", status_code=503)
        assert config.is_retryable(err) is True

    def test_is_retryable_api_error_non_retryable_status(self):
        """Test APIError with non-retryable status code."""
        config = RetryConfig()
        err = APIError("error", status_code=400)
        assert config.is_retryable(err) is False

    def test_is_retryable_unknown_error(self):
        """Test unknown error is NOT retryable."""
        config = RetryConfig()
        assert config.is_retryable(ValueError("unknown")) is False


# ==================== TESTS: CIRCUIT BREAKER ====================


class TestCircuitBreaker:
    """Test CircuitBreaker state transitions."""

    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker with test config."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=0.1,  # Short timeout for testing
        )
        return CircuitBreaker("test-breaker", config)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, breaker):
        """Test initial state is CLOSED."""
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_closed_allows_requests(self, breaker):
        """Test CLOSED state allows requests."""
        assert breaker._should_attempt() is True

    @pytest.mark.asyncio
    async def test_failure_count_increments(self, breaker):
        """Test failure count increments on failure."""
        await breaker.record_failure(Exception("error"))
        assert breaker._failure_count == 1
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker):
        """Test circuit opens after failure threshold."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))
        assert breaker.state == CircuitState.OPEN
        assert breaker._failure_count == 3

    @pytest.mark.asyncio
    async def test_open_rejects_requests(self, breaker):
        """Test OPEN state rejects requests immediately."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))
        assert breaker._should_attempt() is False

    @pytest.mark.asyncio
    async def test_open_transitions_to_half_open_after_timeout(self, breaker):
        """Test OPEN -> HALF_OPEN after timeout."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)
        # Call _should_attempt to trigger state transition
        assert breaker._should_attempt() is True
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self, breaker):
        """Test HALF_OPEN -> CLOSED after success threshold."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))
        await asyncio.sleep(0.15)  # Transition to HALF_OPEN
        # Trigger state transition
        breaker._should_attempt()

        await breaker.record_success()
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker._success_count == 1

        await breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self, breaker):
        """Test HALF_OPEN -> OPEN on any failure."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))
        await asyncio.sleep(0.15)  # Transition to HALF_OPEN
        # Trigger state transition
        breaker._should_attempt()

        await breaker.record_failure(Exception("error"))
        assert breaker.state == CircuitState.OPEN
        assert breaker._success_count == 0

    @pytest.mark.asyncio
    async def test_success_in_closed_resets_failure_count(self, breaker):
        """Test success in CLOSED resets failure count."""
        await breaker.record_failure(Exception("error"))
        await breaker.record_failure(Exception("error"))
        assert breaker._failure_count == 2

        await breaker.record_success()
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted(self, breaker):
        """Test excluded exceptions don't count as failures."""
        await breaker.record_failure(ValueError("excluded"))
        await breaker.record_failure(TypeError("excluded"))
        assert breaker._failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_call_success(self, breaker):
        """Test call() executes function on success."""
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_call_failure(self, breaker):
        """Test call() records failure and re-raises."""
        async def fail_func():
            raise Exception("error")  # Not in excluded exceptions

        with pytest.raises(Exception):
            await breaker.call(fail_func)
        assert breaker._failure_count == 1

    @pytest.mark.asyncio
    async def test_call_rejects_when_open(self, breaker):
        """Test call() raises CircuitBreakerOpenError when OPEN."""
        for _ in range(3):
            await breaker.record_failure(Exception("error"))

        async def func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(func)


class TestRetryDecorator:
    """Test with_retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry on retryable error."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01, jitter=0.0))
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable(self):
        """Test no retry on non-retryable error."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("auth failed")

        with pytest.raises(AuthenticationError):
            await fail_func()
        assert call_count == 1  # No retry

    @pytest.mark.asyncio
    async def test_max_attempts_exhausted(self):
        """Test exception raised after max attempts."""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01, jitter=0.0))
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("persistent")

        with pytest.raises(ConnectionError):
            await always_fail()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry decorator with circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=0.1)
        breaker = CircuitBreaker("test", config)

        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01), circuit_breaker=breaker)
        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("error")

        # First 2 attempts fail and open circuit, 3rd attempt gets CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await fail_func()

        # Circuit breaker should be open after 2 failures
        assert breaker.state == CircuitState.OPEN
        assert call_count == 2  # Only 2 actual calls before circuit opens


class TestRetryAsync:
    """Test retry_async convenience function."""

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test retry_async succeeds on first try."""
        async def func():
            return "success"

        result = await retry_async(func, config=RetryConfig(max_attempts=3))
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_async_retries(self):
        """Test retry_async retries on failure."""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("error")
            return "success"

        result = await retry_async(func, config=RetryConfig(max_attempts=3, base_delay=0.01))
        assert result == "success"
        assert call_count == 2


class TestCreateCircuitBreaker:
    """Test create_circuit_breaker factory."""

    def test_create_with_defaults(self):
        """Test factory with defaults."""
        breaker = create_circuit_breaker("test")
        assert breaker.name == "test"
        assert breaker.config.failure_threshold == 5

    def test_create_with_custom_config(self):
        """Test factory with custom config."""
        breaker = create_circuit_breaker("test", failure_threshold=10, timeout=60.0)
        assert breaker.config.failure_threshold == 10
        assert breaker.config.timeout == 60.0


# ==================== TESTS: LOGGING ====================


class TestLoggingConfiguration:
    """Test logging configuration functions."""

    def test_get_log_level_default(self):
        """Test default log level."""
        with patch.dict("os.environ", {}, clear=True):
            level = get_log_level()
            assert level == 20  # INFO

    def test_get_log_level_from_env(self):
        """Test log level from environment."""
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}, clear=True):
            level = get_log_level()
            assert level == 10  # DEBUG

    def test_get_log_level_invalid_defaults_to_info(self):
        """Test invalid log level defaults to INFO."""
        with patch.dict("os.environ", {"LOG_LEVEL": "INVALID"}, clear=True):
            level = get_log_level()
            assert level == 20  # INFO

    def test_get_log_format_default(self):
        """Test default log format."""
        with patch.dict("os.environ", {}, clear=True):
            fmt = get_log_format()
            assert fmt == "json"

    def test_get_log_format_from_env(self):
        """Test log format from environment."""
        with patch.dict("os.environ", {"LOG_FORMAT": "console"}, clear=True):
            fmt = get_log_format()
            assert fmt == "console"

    def test_configure_logging_json(self):
        """Test configure_logging with JSON format."""
        # Should not raise
        configure_logging(level=10, format_type="json", service_name="test")

    def test_configure_logging_console(self):
        """Test configure_logging with console format."""
        # Should not raise
        configure_logging(level=10, format_type="console", service_name="test")

    def test_get_logger(self):
        """Test get_logger returns structlog logger."""
        logger = get_logger("test.module")
        assert logger is not None


class TestRequestContext:
    """Test RequestContext context manager."""

    def test_request_context_binds_and_unbinds(self):
        """Test context manager binds and unbinds contextvars."""
        with RequestContext(request_id="req-123", user_id="user-456") as ctx:
            assert ctx.context == {"request_id": "req-123", "user_id": "user-456"}
        # After exit, context should be unbound (no way to verify directly without structlog internals)

    def test_request_context_nested(self):
        """Test nested context managers."""
        with RequestContext(request_id="outer"):
            with RequestContext(user_id="inner"):
                pass
            # Outer context should still be active


class TestLogHelpers:
    """Test logging helper functions."""

    def test_log_api_call_success(self, caplog):
        """Test log_api_call for successful call."""
        import structlog

        logger = structlog.get_logger("test")
        log_api_call(logger, "test-service", "GET", "/api", status_code=200, duration_ms=100.5)

    def test_log_api_call_error(self, caplog):
        """Test log_api_call for error."""
        import structlog

        logger = structlog.get_logger("test")
        log_api_call(logger, "test-service", "POST", "/api", status_code=500, duration_ms=200.0, error=Exception("fail"))

    def test_log_retry_attempt(self, caplog):
        """Test log_retry_attempt."""
        import structlog

        logger = structlog.get_logger("test")
        log_retry_attempt(logger, "operation", 1, 3, 1.5, Exception("error"))

    def test_log_circuit_breaker(self, caplog):
        """Test log_circuit_breaker."""
        import structlog

        logger = structlog.get_logger("test")
        log_circuit_breaker(logger, "test-breaker", "OPEN", failure_count=5)


# ==================== TESTS: AUDIO UTILS (basic imports) ====================


class TestAudioUtilsImports:
    """Test audio utils can be imported."""

    def test_import_audio_utils(self):
        """Test all audio functions can be imported."""
        from utils.audio import (
            load_audio_file,
            save_audio_file,
            convert_mulaw_to_pcm,
            convert_pcm_to_mulaw,
            resample_audio,
            get_audio_duration,
            split_audio_chunks,
            convert_twilio_to_stt_format,
            convert_stt_to_twilio_format,
        )
        # All imported successfully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])