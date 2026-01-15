"""
Tests for NatLangChain Retry Logic with Exponential Backoff.

Tests:
- RetryConfig configuration
- RetryStats statistics tracking
- CircuitBreaker state management
- calculate_delay function
- retry_with_backoff decorator
- retry_call function
- RetryContext context manager
- Convenience decorators (retry_network, retry_llm_api, retry_database)
"""

import os
import sys
import threading
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retry import (
    CircuitBreaker,
    CircuitState,
    NonRetryableError,
    RetryableError,
    RetryConfig,
    RetryContext,
    RetryStats,
    calculate_delay,
    get_circuit_breaker,
    is_retryable_exception,
    is_retryable_status_code,
    retry_call,
    retry_database,
    retry_llm_api,
    retry_network,
    retry_with_backoff,
)


class TestRetryableErrors:
    """Tests for custom exception classes."""

    def test_retryable_error(self):
        """Test RetryableError is an exception."""
        error = RetryableError("Temporary failure")
        assert isinstance(error, Exception)
        assert str(error) == "Temporary failure"

    def test_non_retryable_error(self):
        """Test NonRetryableError is an exception."""
        error = NonRetryableError("Permanent failure")
        assert isinstance(error, Exception)
        assert str(error) == "Permanent failure"


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_states_exist(self):
        """Test all circuit states exist."""
        assert CircuitState.CLOSED is not None
        assert CircuitState.OPEN is not None
        assert CircuitState.HALF_OPEN is not None

    def test_circuit_state_values(self):
        """Test circuit state string values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == 0.1
        assert config.circuit_breaker_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=0.2,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0

    def test_retryable_exceptions(self):
        """Test default retryable exceptions."""
        config = RetryConfig()
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions
        assert OSError in config.retryable_exceptions

    def test_retryable_status_codes(self):
        """Test default retryable status codes."""
        config = RetryConfig()
        assert 429 in config.retryable_status_codes  # Too Many Requests
        assert 500 in config.retryable_status_codes  # Internal Server Error
        assert 502 in config.retryable_status_codes  # Bad Gateway
        assert 503 in config.retryable_status_codes  # Service Unavailable

    @patch.dict(os.environ, {
        "RETRY_MAX_ATTEMPTS": "5",
        "RETRY_BASE_DELAY": "2.5",
        "RETRY_MAX_DELAY": "120.0",
        "RETRY_EXPONENTIAL_BASE": "3.0",
        "RETRY_JITTER": "0.15",
    })
    def test_from_env(self):
        """Test creating config from environment variables."""
        config = RetryConfig.from_env()
        assert config.max_retries == 5
        assert config.base_delay == 2.5
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter == 0.15


class TestRetryStats:
    """Tests for RetryStats dataclass."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = RetryStats()
        assert stats.attempts == 0
        assert stats.successes == 0
        assert stats.failures == 0
        assert stats.retries == 0
        assert stats.total_delay == 0.0

    def test_record_success(self):
        """Test recording a successful attempt."""
        stats = RetryStats()
        stats.record_attempt(success=True)
        assert stats.attempts == 1
        assert stats.successes == 1
        assert stats.failures == 0

    def test_record_failure(self):
        """Test recording a failed attempt."""
        stats = RetryStats()
        stats.record_attempt(success=False, error="Connection refused")
        assert stats.attempts == 1
        assert stats.successes == 0
        assert stats.failures == 1
        assert stats.last_error == "Connection refused"

    def test_record_retry_with_delay(self):
        """Test recording a retry with delay."""
        stats = RetryStats()
        stats.record_attempt(success=False, delay=2.5, error="Timeout")
        assert stats.retries == 1
        assert stats.total_delay == 2.5

    def test_multiple_attempts(self):
        """Test recording multiple attempts."""
        stats = RetryStats()
        stats.record_attempt(success=False, delay=1.0, error="Error 1")
        stats.record_attempt(success=False, delay=2.0, error="Error 2")
        stats.record_attempt(success=True)

        assert stats.attempts == 3
        assert stats.successes == 1
        assert stats.failures == 2
        assert stats.retries == 2
        assert stats.total_delay == 3.0

    def test_last_attempt_time(self):
        """Test that last attempt time is updated."""
        stats = RetryStats()
        before = time.time()
        stats.record_attempt(success=True)
        after = time.time()

        assert before <= stats.last_attempt_time <= after


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test", failure_threshold=5)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_allowed() is True

    def test_record_success_resets_failures(self):
        """Test recording success resets failure count."""
        cb = CircuitBreaker("test", failure_threshold=5)
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        # Then success
        cb.record_success()
        # Circuit should still be closed with reset failure count
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.is_allowed() is False

    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Accessing state should transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.is_allowed() is True

    def test_half_open_success_closes_circuit(self):
        """Test success in HALF_OPEN state closes circuit."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)

        # Open and wait for half-open
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Record success
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN state reopens circuit."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)

        # Open and wait for half-open
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Record failure - should reopen
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        """Test circuit breaker reset."""
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb.is_allowed() is True

    def test_thread_safety(self):
        """Test circuit breaker is thread-safe."""
        cb = CircuitBreaker("test", failure_threshold=100)
        errors = []

        def record_failures():
            try:
                for _ in range(50):
                    cb.record_failure()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_failures) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestGetCircuitBreaker:
    """Tests for get_circuit_breaker function."""

    def test_creates_new_circuit_breaker(self):
        """Test creating a new circuit breaker."""
        # Use unique name to avoid conflicts
        cb = get_circuit_breaker("test_new_unique_123")
        assert cb is not None
        assert cb.name == "test_new_unique_123"

    def test_returns_same_instance(self):
        """Test getting same circuit breaker by name."""
        cb1 = get_circuit_breaker("test_same_unique_456")
        cb2 = get_circuit_breaker("test_same_unique_456")
        assert cb1 is cb2


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_first_attempt_delay(self):
        """Test delay for first attempt (attempt=0)."""
        delay = calculate_delay(
            attempt=0,
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=0.0,  # No jitter for predictable test
        )
        assert delay == 1.0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        # attempt=0: 1.0 * 2^0 = 1.0
        # attempt=1: 1.0 * 2^1 = 2.0
        # attempt=2: 1.0 * 2^2 = 4.0
        # attempt=3: 1.0 * 2^3 = 8.0

        delays = []
        for attempt in range(4):
            delay = calculate_delay(
                attempt=attempt,
                base_delay=1.0,
                exponential_base=2.0,
                max_delay=60.0,
                jitter=0.0,
            )
            delays.append(delay)

        assert delays == [1.0, 2.0, 4.0, 8.0]

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        delay = calculate_delay(
            attempt=10,  # Would be 1024 without cap
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=0.0,
        )
        assert delay == 60.0

    def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delay."""
        delays = set()
        for _ in range(10):
            delay = calculate_delay(
                attempt=0,
                base_delay=10.0,
                exponential_base=2.0,
                max_delay=60.0,
                jitter=0.5,  # High jitter
            )
            delays.add(round(delay, 2))

        # With jitter, we should get different delays
        assert len(delays) > 1

    def test_jitter_range(self):
        """Test jitter stays within expected range."""
        base = 10.0
        jitter = 0.2

        for _ in range(100):
            delay = calculate_delay(
                attempt=0,
                base_delay=base,
                exponential_base=2.0,
                max_delay=60.0,
                jitter=jitter,
            )
            # Delay should be within base +/- jitter*base
            min_expected = base * (1 - jitter)
            max_expected = base * (1 + jitter)
            assert min_expected <= delay <= max_expected

    def test_zero_jitter(self):
        """Test zero jitter gives exact delay."""
        delay1 = calculate_delay(0, 5.0, 2.0, 60.0, 0.0)
        delay2 = calculate_delay(0, 5.0, 2.0, 60.0, 0.0)
        assert delay1 == delay2 == 5.0


class TestIsRetryableException:
    """Tests for is_retryable_exception function."""

    def test_explicit_retryable_error(self):
        """Test RetryableError is always retryable."""
        result = is_retryable_exception(
            RetryableError("test"),
            retryable_types=(ValueError,),  # Even with different types
        )
        assert result is True

    def test_explicit_non_retryable_error(self):
        """Test NonRetryableError is never retryable."""
        result = is_retryable_exception(
            NonRetryableError("test"),
            retryable_types=(ConnectionError, NonRetryableError),  # Even if in list
        )
        assert result is False

    def test_connection_error_retryable(self):
        """Test ConnectionError is retryable by default."""
        result = is_retryable_exception(
            ConnectionError("Connection refused"),
            retryable_types=(ConnectionError, TimeoutError),
        )
        assert result is True

    def test_value_error_not_retryable(self):
        """Test ValueError is not retryable by default."""
        result = is_retryable_exception(
            ValueError("Invalid value"),
            retryable_types=(ConnectionError, TimeoutError),
        )
        assert result is False

    def test_subclass_is_retryable(self):
        """Test subclass of retryable exception is retryable."""
        class CustomConnectionError(ConnectionError):
            pass

        result = is_retryable_exception(
            CustomConnectionError("test"),
            retryable_types=(ConnectionError,),
        )
        assert result is True


class TestIsRetryableStatusCode:
    """Tests for is_retryable_status_code function."""

    def test_429_is_retryable(self):
        """Test 429 Too Many Requests is retryable."""
        assert is_retryable_status_code(429, (429, 500, 502, 503)) is True

    def test_500_is_retryable(self):
        """Test 500 Internal Server Error is retryable."""
        assert is_retryable_status_code(500, (429, 500, 502, 503)) is True

    def test_404_not_retryable(self):
        """Test 404 Not Found is not retryable."""
        assert is_retryable_status_code(404, (429, 500, 502, 503)) is False

    def test_200_not_retryable(self):
        """Test 200 OK is not retryable."""
        assert is_retryable_status_code(200, (429, 500, 502, 503)) is False


class TestRetryWithBackoffDecorator:
    """Tests for retry_with_backoff decorator."""

    def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_retryable_exception(self):
        """Test retries on retryable exception."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        """Test raises exception after max retries exceeded."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection refused")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_no_retry_on_non_retryable(self):
        """Test no retry on non-retryable exception."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
        )
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid value")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retries

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        retry_calls = []

        def on_retry(attempt, exception, delay):
            retry_calls.append((attempt, str(exception), delay))

        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
            on_retry=on_retry,
        )
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Test error")
            return "success"

        flaky_func()
        assert len(retry_calls) == 2
        assert retry_calls[0][0] == 1  # First retry
        assert retry_calls[1][0] == 2  # Second retry

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with decorator."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,),
            circuit_breaker_name="test_decorator_cb",
        )
        def circuit_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Test error")

        # First call should try and fail
        with pytest.raises(ConnectionError):
            circuit_func()


class TestRetryCall:
    """Tests for retry_call function."""

    def test_successful_call(self):
        """Test successful function call."""
        def success_func():
            return "result"

        result = retry_call(success_func)
        assert result == "result"

    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Test")
            return "success"

        config = RetryConfig(max_retries=3, base_delay=0.01)
        result = retry_call(flaky_func, config=config)
        assert result == "success"
        assert call_count == 2

    def test_with_args_and_kwargs(self):
        """Test calling function with arguments."""
        def add_func(a, b, multiplier=1):
            return (a + b) * multiplier

        result = retry_call(add_func, args=(2, 3), kwargs={"multiplier": 2})
        assert result == 10


class TestRetryContext:
    """Tests for RetryContext context manager."""

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        with RetryContext() as ctx:
            result = ctx.execute(lambda: "result")
        assert result == "result"

    def test_context_manager_with_config(self):
        """Test context manager with custom config."""
        config = RetryConfig(max_retries=5, base_delay=0.01)
        with RetryContext(config=config) as ctx:
            assert ctx.config.max_retries == 5

    def test_context_stats_tracking(self):
        """Test that context tracks statistics."""
        with RetryContext() as ctx:
            ctx.execute(lambda: "result")
        # Stats should be available
        assert ctx.stats is not None


class TestConvenienceDecorators:
    """Tests for convenience decorators."""

    def test_retry_network_decorator(self):
        """Test retry_network decorator applies correctly."""
        @retry_network
        def network_func():
            return "network_result"

        result = network_func()
        assert result == "network_result"

    def test_retry_llm_api_decorator(self):
        """Test retry_llm_api decorator applies correctly."""
        @retry_llm_api
        def llm_func():
            return "llm_result"

        result = llm_func()
        assert result == "llm_result"

    def test_retry_database_decorator(self):
        """Test retry_database decorator applies correctly."""
        @retry_database
        def db_func():
            return "db_result"

        result = db_func()
        assert result == "db_result"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_max_retries(self):
        """Test with zero max retries (single attempt)."""
        call_count = 0

        @retry_with_backoff(max_retries=0, base_delay=0.01)
        def single_attempt():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Test")

        with pytest.raises(ConnectionError):
            single_attempt()
        assert call_count == 1

    def test_very_high_jitter(self):
        """Test delay calculation with high jitter doesn't go negative."""
        for _ in range(100):
            delay = calculate_delay(
                attempt=0,
                base_delay=0.1,
                exponential_base=2.0,
                max_delay=60.0,
                jitter=1.0,  # 100% jitter
            )
            assert delay >= 0

    def test_empty_retryable_exceptions(self):
        """Test with empty retryable exceptions tuple."""
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(),  # No exceptions are retryable
        )
        def raises_error():
            raise ConnectionError("Test")

        with pytest.raises(ConnectionError):
            raises_error()

    def test_circuit_breaker_blocks_immediately(self):
        """Test open circuit breaker blocks calls immediately."""
        cb = get_circuit_breaker("test_blocking_cb", failure_threshold=1)
        cb.record_failure()  # Opens the circuit

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            circuit_breaker_name="test_blocking_cb",
        )
        def blocked_func():
            return "should not reach"

        with pytest.raises(ConnectionError) as exc_info:
            blocked_func()
        assert "open" in str(exc_info.value).lower()
