"""
NatLangChain - Retry Logic with Exponential Backoff

Production-ready retry utilities for:
- LLM API calls (Anthropic, OpenAI, etc.)
- Network requests (P2P, HTTP)
- Database operations
- External service calls

Features:
- Exponential backoff with jitter
- Configurable retry conditions
- Circuit breaker integration
- Detailed logging and metrics

Usage:
    from retry import retry_with_backoff, RetryConfig

    # Decorator usage
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def call_api():
        return api.request()

    # Context manager usage
    with RetryContext(config) as ctx:
        result = ctx.execute(call_api)

    # Functional usage
    result = retry_call(call_api, max_retries=3)

Environment Variables:
    RETRY_MAX_ATTEMPTS=3
    RETRY_BASE_DELAY=1.0
    RETRY_MAX_DELAY=60.0
    RETRY_EXPONENTIAL_BASE=2.0
    RETRY_JITTER=0.1
"""

import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT trigger a retry."""
    pass


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    # Retry limits
    max_retries: int = 3
    max_delay: float = 60.0  # Maximum delay between retries

    # Backoff configuration
    base_delay: float = 1.0  # Initial delay in seconds
    exponential_base: float = 2.0  # Multiplier for exponential backoff
    jitter: float = 0.1  # Random jitter factor (0.0 to 1.0)

    # Retry conditions
    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5  # Failures before opening circuit
    circuit_breaker_timeout: float = 30.0  # Seconds before trying again

    # Logging
    log_retries: bool = True
    log_level: int = logging.WARNING

    @classmethod
    def from_env(cls) -> "RetryConfig":
        """Create configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("RETRY_MAX_DELAY", "60.0")),
            exponential_base=float(os.getenv("RETRY_EXPONENTIAL_BASE", "2.0")),
            jitter=float(os.getenv("RETRY_JITTER", "0.1")),
        )


@dataclass
class RetryStats:
    """Statistics from retry operations."""

    attempts: int = 0
    successes: int = 0
    failures: int = 0
    retries: int = 0
    total_delay: float = 0.0
    last_error: str | None = None
    last_attempt_time: float = 0.0

    def record_attempt(self, success: bool, delay: float = 0.0, error: str | None = None):
        """Record an attempt."""
        self.attempts += 1
        self.last_attempt_time = time.time()

        if success:
            self.successes += 1
        else:
            self.failures += 1
            self.last_error = error

        if delay > 0:
            self.retries += 1
            self.total_delay += delay


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by temporarily blocking requests
    when a service is experiencing problems.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")

            return self._state

    def is_allowed(self) -> bool:
        """Check if requests are allowed."""
        return self.state != CircuitState.OPEN

    def record_success(self):
        """Record a successful request."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Recovery successful, close circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    def record_failure(self):
        """Record a failed request."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Still failing, reopen circuit
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (still failing)")

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit {self.name}: CLOSED -> OPEN "
                        f"(failures: {self._failure_count})"
                    )

    def reset(self):
        """Reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0


# Global circuit breakers by name
_circuit_breakers: dict[str, CircuitBreaker] = {}
_circuit_breakers_lock = threading.Lock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _circuit_breakers_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
        return _circuit_breakers[name]


def calculate_delay(
    attempt: int,
    base_delay: float,
    exponential_base: float,
    max_delay: float,
    jitter: float
) -> float:
    """
    Calculate delay with exponential backoff and jitter.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Initial delay in seconds
        exponential_base: Multiplier for exponential growth
        max_delay: Maximum delay cap
        jitter: Random jitter factor (0.0 to 1.0)

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ** attempt)
    delay = base_delay * (exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter: delay * (1 + random(-jitter, +jitter))
    if jitter > 0:
        jitter_amount = delay * jitter * (2 * random.random() - 1)
        delay += jitter_amount

    return max(0, delay)


def is_retryable_exception(
    exception: Exception,
    retryable_types: tuple[Type[Exception], ...]
) -> bool:
    """Check if an exception should trigger a retry."""
    # Explicit non-retryable
    if isinstance(exception, NonRetryableError):
        return False

    # Explicit retryable
    if isinstance(exception, RetryableError):
        return True

    # Check against retryable types
    return isinstance(exception, retryable_types)


def is_retryable_status_code(status_code: int, retryable_codes: tuple[int, ...]) -> bool:
    """Check if an HTTP status code should trigger a retry."""
    return status_code in retryable_codes


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple = (ConnectionError, TimeoutError, OSError),
    circuit_breaker_name: str | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Random jitter factor (0.0 to 1.0)
        retryable_exceptions: Tuple of exception types to retry
        circuit_breaker_name: Optional circuit breaker name
        on_retry: Optional callback called on each retry (attempt, exception, delay)

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit = None
            if circuit_breaker_name:
                circuit = get_circuit_breaker(circuit_breaker_name)

            last_exception = None

            for attempt in range(max_retries + 1):
                # Check circuit breaker
                if circuit and not circuit.is_allowed():
                    raise ConnectionError(
                        f"Circuit breaker {circuit_breaker_name} is open"
                    )

                try:
                    result = func(*args, **kwargs)

                    # Record success
                    if circuit:
                        circuit.record_success()

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if retryable
                    if not is_retryable_exception(e, retryable_exceptions):
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise

                    # Record failure
                    if circuit:
                        circuit.record_failure()

                    # Check if we have retries left
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = calculate_delay(
                        attempt, base_delay, exponential_base, max_delay, jitter
                    )

                    # Log retry
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s delay: {e}"
                    )

                    # Callback
                    if on_retry:
                        on_retry(attempt + 1, e, delay)

                    # Wait
                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_call(
    func: Callable,
    args: tuple = (),
    kwargs: dict | None = None,
    config: RetryConfig | None = None,
    circuit_breaker_name: str | None = None,
) -> Any:
    """
    Execute a function with retry logic.

    Args:
        func: Function to call
        args: Positional arguments
        kwargs: Keyword arguments
        config: Retry configuration
        circuit_breaker_name: Optional circuit breaker name

    Returns:
        Result of the function call
    """
    config = config or RetryConfig()
    kwargs = kwargs or {}

    circuit = None
    if circuit_breaker_name:
        circuit = get_circuit_breaker(circuit_breaker_name)

    stats = RetryStats()
    last_exception = None

    for attempt in range(config.max_retries + 1):
        # Check circuit breaker
        if circuit and not circuit.is_allowed():
            raise ConnectionError(
                f"Circuit breaker {circuit_breaker_name} is open"
            )

        try:
            result = func(*args, **kwargs)

            # Record success
            stats.record_attempt(success=True)
            if circuit:
                circuit.record_success()

            return result

        except Exception as e:
            last_exception = e
            error_str = str(e)

            # Check if retryable
            if not is_retryable_exception(e, config.retryable_exceptions):
                stats.record_attempt(success=False, error=error_str)
                if config.log_retries:
                    logger.log(config.log_level, f"Non-retryable error: {e}")
                raise

            # Record failure
            if circuit:
                circuit.record_failure()

            # Check if we have retries left
            if attempt >= config.max_retries:
                stats.record_attempt(success=False, error=error_str)
                if config.log_retries:
                    logger.log(
                        config.log_level,
                        f"Max retries ({config.max_retries}) exceeded: {e}"
                    )
                raise

            # Calculate delay
            delay = calculate_delay(
                attempt,
                config.base_delay,
                config.exponential_base,
                config.max_delay,
                config.jitter
            )

            stats.record_attempt(success=False, delay=delay, error=error_str)

            # Log retry
            if config.log_retries:
                logger.log(
                    config.log_level,
                    f"Retry {attempt + 1}/{config.max_retries} after {delay:.2f}s: {e}"
                )

            # Wait
            time.sleep(delay)

    # Should not reach here
    if last_exception:
        raise last_exception


class RetryContext:
    """
    Context manager for retry operations with shared state.

    Useful when you need to track retry statistics across
    multiple operations or share a circuit breaker.
    """

    def __init__(
        self,
        config: RetryConfig | None = None,
        circuit_breaker_name: str | None = None
    ):
        self.config = config or RetryConfig()
        self.circuit_breaker_name = circuit_breaker_name
        self.stats = RetryStats()
        self._circuit = None

    def __enter__(self):
        if self.circuit_breaker_name:
            self._circuit = get_circuit_breaker(self.circuit_breaker_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't suppress exceptions
        return False

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic."""
        return retry_call(
            func,
            args=args,
            kwargs=kwargs,
            config=self.config,
            circuit_breaker_name=self.circuit_breaker_name,
        )


# Convenience decorators for common use cases

def retry_network(func: Callable) -> Callable:
    """Decorator for network operations with sensible defaults."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=0.2,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
    )(func)


def retry_llm_api(func: Callable) -> Callable:
    """Decorator for LLM API calls with rate limit awareness."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=2.0,  # Longer initial delay for rate limits
        max_delay=60.0,
        exponential_base=2.0,
        jitter=0.3,  # More jitter to spread out retries
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
        circuit_breaker_name="llm_api",
    )(func)


def retry_database(func: Callable) -> Callable:
    """Decorator for database operations."""
    return retry_with_backoff(
        max_retries=2,
        base_delay=0.5,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=0.1,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            OSError,
        ),
        circuit_breaker_name="database",
    )(func)
