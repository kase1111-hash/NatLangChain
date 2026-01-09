"""
NatLangChain - Distributed Rate Limiting

Production-ready rate limiting with:
- Redis-backed distributed rate limiting for multi-instance deployments
- Sliding window algorithm for accurate rate limiting
- Fallback to in-memory when Redis is unavailable
- Per-IP, per-user, and per-endpoint rate limits
- Rate limit headers (X-RateLimit-*)

Usage:
    from rate_limiter import RateLimiter, RateLimitConfig

    # Create rate limiter (auto-selects Redis or memory based on config)
    limiter = RateLimiter(RateLimitConfig.from_env())

    # Check rate limit
    result = limiter.check_limit("client_ip_123")
    if result.exceeded:
        return 429, {"retry_after": result.retry_after}

Environment Variables:
    RATE_LIMIT_BACKEND=memory|redis
    RATE_LIMIT_REQUESTS=100
    RATE_LIMIT_WINDOW=60
    RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
    RATE_LIMIT_REDIS_PREFIX=natlangchain:ratelimit:
    RATE_LIMIT_BURST_MULTIPLIER=1.5
"""

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RateLimitBackend(Enum):
    """Supported rate limit storage backends."""

    MEMORY = "memory"
    REDIS = "redis"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Backend selection
    backend: str = "memory"

    # Limits
    requests_per_window: int = 100
    window_seconds: int = 60
    burst_multiplier: float = 1.5  # Allow burst up to this multiplier

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "natlangchain:ratelimit:"
    redis_timeout: float = 1.0  # Connection timeout

    # Fallback behavior
    fallback_to_memory: bool = True  # Use memory if Redis fails

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create configuration from environment variables."""
        return cls(
            backend=os.getenv("RATE_LIMIT_BACKEND", "memory"),
            requests_per_window=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
            burst_multiplier=float(os.getenv("RATE_LIMIT_BURST_MULTIPLIER", "1.5")),
            redis_url=os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0"),
            redis_prefix=os.getenv("RATE_LIMIT_REDIS_PREFIX", "natlangchain:ratelimit:"),
            redis_timeout=float(os.getenv("RATE_LIMIT_REDIS_TIMEOUT", "1.0")),
            fallback_to_memory=os.getenv("RATE_LIMIT_FALLBACK", "true").lower() == "true",
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    exceeded: bool
    remaining: int
    limit: int
    reset_at: float  # Unix timestamp when window resets
    retry_after: int  # Seconds until retry allowed (0 if not exceeded)

    def to_headers(self) -> dict[str, str]:
        """Convert to rate limit response headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }


class RateLimitStore(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    def increment(self, key: str, window_seconds: int) -> tuple[int, float]:
        """
        Increment counter for key and return (count, window_reset_time).

        Args:
            key: The rate limit key (e.g., "ip:192.168.1.1")
            window_seconds: Window duration in seconds

        Returns:
            Tuple of (current_count, reset_timestamp)
        """
        pass

    @abstractmethod
    def get_count(self, key: str) -> int:
        """Get current count for key."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the store is available."""
        pass


class MemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit storage (single instance only)."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def increment(self, key: str, window_seconds: int) -> tuple[int, float]:
        """Increment counter using sliding window."""
        current_time = time.time()

        with self._lock:
            if key not in self._store:
                self._store[key] = {"count": 0, "window_start": current_time}

            data = self._store[key]
            window_start = data["window_start"]
            reset_at = window_start + window_seconds

            # Reset if window expired
            if current_time >= reset_at:
                data["count"] = 0
                data["window_start"] = current_time
                reset_at = current_time + window_seconds

            # Increment
            data["count"] += 1

            return data["count"], reset_at

    def get_count(self, key: str) -> int:
        """Get current count."""
        with self._lock:
            if key in self._store:
                return self._store[key]["count"]
            return 0

    def is_available(self) -> bool:
        """Memory store is always available."""
        return True

    def cleanup_expired(self, window_seconds: int):
        """Remove expired entries to prevent memory growth."""
        current_time = time.time()
        expired_threshold = current_time - window_seconds * 2

        with self._lock:
            expired_keys = [
                k for k, v in self._store.items() if v["window_start"] < expired_threshold
            ]
            for k in expired_keys:
                del self._store[k]


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit storage for distributed deployments."""

    def __init__(self, url: str, prefix: str = "", timeout: float = 1.0):
        self.url = url
        self.prefix = prefix
        self.timeout = timeout
        self._client = None
        self._available = False

    def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis

                self._client = redis.from_url(
                    self.url,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True,
                )
                # Test connection
                self._client.ping()
                self._available = True
                logger.info(f"Connected to Redis at {self.url}")
            except ImportError:
                logger.warning("redis package not installed. Install with: pip install redis")
                self._available = False
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._available = False

        return self._client

    def _full_key(self, key: str) -> str:
        """Get full Redis key with prefix."""
        return f"{self.prefix}{key}"

    def increment(self, key: str, window_seconds: int) -> tuple[int, float]:
        """
        Increment counter using Redis sliding window.

        Uses Redis MULTI/EXEC for atomic operations.
        """
        try:
            client = self._get_client()
            if client is None:
                raise ConnectionError("Redis not available")

            full_key = self._full_key(key)
            current_time = time.time()

            # Use Redis pipeline for atomic increment with expiry
            pipe = client.pipeline()

            # Increment counter
            pipe.incr(full_key)

            # Set expiry if not already set (only on first request in window)
            pipe.expire(full_key, window_seconds, nx=True)

            # Get TTL to calculate reset time
            pipe.ttl(full_key)

            results = pipe.execute()

            count = results[0]  # Current count after increment
            ttl = results[2]  # Time to live

            # Calculate reset time
            if ttl > 0:
                reset_at = current_time + ttl
            else:
                reset_at = current_time + window_seconds

            self._available = True
            return count, reset_at

        except Exception as e:
            logger.error(f"Redis increment failed: {e}")
            self._available = False
            raise

    def get_count(self, key: str) -> int:
        """Get current count from Redis."""
        try:
            client = self._get_client()
            if client is None:
                return 0

            full_key = self._full_key(key)
            value = client.get(full_key)
            return int(value) if value else 0

        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return 0

    def is_available(self) -> bool:
        """Check if Redis is available."""
        try:
            client = self._get_client()
            if client is None:
                return False
            client.ping()
            self._available = True
            return True
        except Exception:
            self._available = False
            return False


class RateLimiter:
    """
    Distributed rate limiter with Redis support and memory fallback.

    Implements a sliding window algorithm for accurate rate limiting.
    Automatically falls back to in-memory storage if Redis is unavailable.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig.from_env()
        self._primary_store: RateLimitStore | None = None
        self._fallback_store: MemoryRateLimitStore | None = None
        self._init_stores()

    def _init_stores(self):
        """Initialize rate limit stores."""
        backend = self.config.backend.lower()

        if backend == "redis":
            self._primary_store = RedisRateLimitStore(
                url=self.config.redis_url,
                prefix=self.config.redis_prefix,
                timeout=self.config.redis_timeout,
            )

            if self.config.fallback_to_memory:
                self._fallback_store = MemoryRateLimitStore()
                logger.info("Rate limiter: Redis primary with memory fallback")
            else:
                logger.info("Rate limiter: Redis only (no fallback)")

        else:
            self._primary_store = MemoryRateLimitStore()
            logger.info("Rate limiter: Memory only")

    def _get_store(self) -> RateLimitStore:
        """Get the active store (primary or fallback)."""
        if self._primary_store and self._primary_store.is_available():
            return self._primary_store

        if self._fallback_store:
            logger.warning("Primary rate limit store unavailable, using fallback")
            return self._fallback_store

        # Last resort: return primary anyway (will raise on use)
        return self._primary_store

    def check_limit(
        self, identifier: str, limit: int | None = None, window: int | None = None
    ) -> RateLimitResult:
        """
        Check if the identifier has exceeded its rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            limit: Custom limit (uses config default if None)
            window: Custom window in seconds (uses config default if None)

        Returns:
            RateLimitResult with exceeded status and headers
        """
        effective_limit = limit or self.config.requests_per_window
        effective_window = window or self.config.window_seconds

        try:
            store = self._get_store()
            count, reset_at = store.increment(identifier, effective_window)

            exceeded = count > effective_limit
            remaining = max(0, effective_limit - count)

            retry_after = 0
            if exceeded:
                retry_after = max(1, int(reset_at - time.time()))

            return RateLimitResult(
                exceeded=exceeded,
                remaining=remaining,
                limit=effective_limit,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")

            # On error, allow the request (fail open)
            return RateLimitResult(
                exceeded=False,
                remaining=effective_limit,
                limit=effective_limit,
                reset_at=time.time() + effective_window,
                retry_after=0,
            )

    def check_limit_multi(
        self, identifiers: list[str], limits: dict[str, int] | None = None
    ) -> dict[str, RateLimitResult]:
        """
        Check multiple rate limits at once.

        Useful for checking both IP and user limits simultaneously.

        Args:
            identifiers: List of identifiers to check
            limits: Optional dict of identifier -> limit overrides

        Returns:
            Dict mapping identifier to RateLimitResult
        """
        results = {}
        limits = limits or {}

        for identifier in identifiers:
            limit = limits.get(identifier)
            results[identifier] = self.check_limit(identifier, limit=limit)

        return results

    def get_status(self, identifier: str) -> RateLimitResult:
        """
        Get current rate limit status without incrementing counter.

        Args:
            identifier: Unique identifier to check

        Returns:
            RateLimitResult with current status
        """
        try:
            store = self._get_store()
            count = store.get_count(identifier)

            remaining = max(0, self.config.requests_per_window - count)
            exceeded = count >= self.config.requests_per_window

            return RateLimitResult(
                exceeded=exceeded,
                remaining=remaining,
                limit=self.config.requests_per_window,
                reset_at=time.time() + self.config.window_seconds,
                retry_after=self.config.window_seconds if exceeded else 0,
            )

        except Exception as e:
            logger.error(f"Rate limit status check failed: {e}")
            return RateLimitResult(
                exceeded=False,
                remaining=self.config.requests_per_window,
                limit=self.config.requests_per_window,
                reset_at=time.time() + self.config.window_seconds,
                retry_after=0,
            )

    def is_healthy(self) -> dict[str, Any]:
        """Check health of rate limiter stores."""
        primary_available = self._primary_store.is_available() if self._primary_store else False
        fallback_available = self._fallback_store.is_available() if self._fallback_store else False

        return {
            "backend": self.config.backend,
            "primary_available": primary_available,
            "fallback_available": fallback_available,
            "effective_backend": (
                "primary" if primary_available else "fallback" if fallback_available else "none"
            ),
        }


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter

    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()

    return _rate_limiter


def check_rate_limit_distributed(identifier: str) -> RateLimitResult:
    """
    Convenience function to check rate limit using global limiter.

    Args:
        identifier: Client identifier (e.g., IP address)

    Returns:
        RateLimitResult
    """
    return get_rate_limiter().check_limit(identifier)


# Flask integration helper
def create_rate_limit_response(result: RateLimitResult) -> tuple[dict, int, dict]:
    """
    Create a Flask-compatible rate limit exceeded response.

    Args:
        result: RateLimitResult from check_limit

    Returns:
        Tuple of (body, status_code, headers)
    """
    body = {
        "error": "Rate limit exceeded",
        "message": f"Too many requests. Please retry after {result.retry_after} seconds.",
        "retry_after": result.retry_after,
    }

    headers = result.to_headers()
    headers["Retry-After"] = str(result.retry_after)

    return body, 429, headers
