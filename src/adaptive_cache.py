"""
NatLangChain - Adaptive Query Cache

Congestion-aware caching for mediator node queries.
Adjusts cache TTLs based on system load to balance freshness vs performance.

Features:
- Congestion detection via pending queue depth
- Adaptive TTLs that increase under load
- Specialized caches for intents, contracts, stats
- Cache invalidation on blockchain events
- Thread-safe with statistics tracking

Usage:
    from adaptive_cache import get_adaptive_cache, CacheCategory

    cache = get_adaptive_cache()

    # Get with congestion-aware TTL
    result = cache.get_or_compute(
        CacheCategory.INTENTS,
        key="pending:open:100",
        compute_fn=lambda: expensive_query()
    )

    # Invalidate on new block
    cache.invalidate_category(CacheCategory.INTENTS)
"""

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Congestion thresholds (pending queue depth)
CONGESTION_THRESHOLD_LOW = 50      # Below this: light load
CONGESTION_THRESHOLD_MEDIUM = 100  # Above this: moderate congestion
CONGESTION_THRESHOLD_HIGH = 200    # Above this: heavy congestion

# Base TTLs (seconds) - used during light load
BASE_TTL_INTENTS = 30
BASE_TTL_CONTRACTS = 30
BASE_TTL_STATS = 10
BASE_TTL_SEARCH = 60
BASE_TTL_METADATA = 60

# Maximum TTLs (seconds) - used during heavy congestion
MAX_TTL_INTENTS = 120
MAX_TTL_CONTRACTS = 120
MAX_TTL_STATS = 60
MAX_TTL_SEARCH = 300
MAX_TTL_METADATA = 180

# Cache size limits
MAX_CACHE_ENTRIES = 5000
CLEANUP_INTERVAL = 30  # seconds


class CacheCategory(Enum):
    """Categories of cached data with different TTL characteristics."""
    INTENTS = "intents"           # Pending intents for mediators
    CONTRACTS = "contracts"       # Open contract queries
    STATS = "stats"               # Chain statistics
    SEARCH = "search"             # Semantic search results
    METADATA = "metadata"         # Entry/contract metadata
    BLOCKS = "blocks"             # Block data (for sync)


class CongestionLevel(Enum):
    """System congestion levels."""
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    CRITICAL = "critical"


@dataclass
class CacheConfig:
    """Configuration for a cache category."""
    base_ttl: float
    max_ttl: float
    priority: int = 1  # Higher = kept longer during eviction

    def get_ttl(self, congestion_factor: float) -> float:
        """Calculate TTL based on congestion (0.0 to 1.0)."""
        # Linear interpolation between base and max TTL
        return self.base_ttl + (self.max_ttl - self.base_ttl) * congestion_factor


# Default configurations per category
DEFAULT_CACHE_CONFIGS: dict[CacheCategory, CacheConfig] = {
    CacheCategory.INTENTS: CacheConfig(BASE_TTL_INTENTS, MAX_TTL_INTENTS, priority=3),
    CacheCategory.CONTRACTS: CacheConfig(BASE_TTL_CONTRACTS, MAX_TTL_CONTRACTS, priority=3),
    CacheCategory.STATS: CacheConfig(BASE_TTL_STATS, MAX_TTL_STATS, priority=1),
    CacheCategory.SEARCH: CacheConfig(BASE_TTL_SEARCH, MAX_TTL_SEARCH, priority=2),
    CacheCategory.METADATA: CacheConfig(BASE_TTL_METADATA, MAX_TTL_METADATA, priority=2),
    CacheCategory.BLOCKS: CacheConfig(30, 60, priority=1),
}


@dataclass
class AdaptiveCacheEntry:
    """A cached value with metadata for the adaptive cache system."""
    value: Any
    category: CacheCategory
    created_at: float
    expires_at: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at

    @property
    def age(self) -> float:
        """Age in seconds."""
        return time.time() - self.created_at

    @property
    def ttl_remaining(self) -> float:
        """Remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


@dataclass
class CongestionState:
    """Current congestion state of the system."""
    pending_count: int = 0
    request_rate: float = 0.0  # requests per second
    level: CongestionLevel = CongestionLevel.LIGHT
    factor: float = 0.0  # 0.0 (light) to 1.0 (critical)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pending_count": self.pending_count,
            "request_rate": round(self.request_rate, 2),
            "level": self.level.value,
            "factor": round(self.factor, 3),
            "last_updated": self.last_updated,
        }


@dataclass
class CacheStats:
    """Statistics for cache operations."""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    evictions: int = 0
    computations: int = 0
    compute_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def avg_compute_time_ms(self) -> float:
        """Average computation time."""
        return self.compute_time_ms / self.computations if self.computations > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "invalidations": self.invalidations,
            "evictions": self.evictions,
            "computations": self.computations,
            "hit_rate": round(self.hit_rate * 100, 2),
            "avg_compute_time_ms": round(self.avg_compute_time_ms, 3),
        }


class CongestionDetector:
    """
    Monitors system congestion and provides congestion factor.

    Uses pending queue depth as primary metric, with request rate
    as secondary indicator.
    """

    def __init__(
        self,
        threshold_low: int = CONGESTION_THRESHOLD_LOW,
        threshold_medium: int = CONGESTION_THRESHOLD_MEDIUM,
        threshold_high: int = CONGESTION_THRESHOLD_HIGH,
    ):
        """Initialize congestion detector."""
        self.threshold_low = threshold_low
        self.threshold_medium = threshold_medium
        self.threshold_high = threshold_high

        self._state = CongestionState()
        self._request_times: list[float] = []
        self._request_window = 60.0  # 1 minute window
        self._lock = threading.Lock()

        # Callback to get pending count from blockchain
        self._get_pending_count: Callable[[], int] | None = None

    def set_pending_count_callback(self, callback: Callable[[], int]) -> None:
        """Set callback to get pending entry count."""
        self._get_pending_count = callback

    def record_request(self) -> None:
        """Record an incoming request for rate calculation."""
        with self._lock:
            now = time.time()
            self._request_times.append(now)

            # Clean old entries
            cutoff = now - self._request_window
            self._request_times = [t for t in self._request_times if t > cutoff]

    def update(self, pending_count: int | None = None) -> CongestionState:
        """
        Update congestion state.

        Args:
            pending_count: Override pending count (otherwise uses callback)

        Returns:
            Updated congestion state
        """
        with self._lock:
            now = time.time()

            # Get pending count
            if pending_count is None and self._get_pending_count:
                try:
                    pending_count = self._get_pending_count()
                except Exception:
                    pending_count = 0
            pending_count = pending_count or 0

            # Calculate request rate
            cutoff = now - self._request_window
            recent_requests = [t for t in self._request_times if t > cutoff]
            request_rate = len(recent_requests) / self._request_window

            # Calculate congestion level and factor
            if pending_count >= self.threshold_high * 2:
                level = CongestionLevel.CRITICAL
                factor = 1.0
            elif pending_count >= self.threshold_high:
                level = CongestionLevel.HEAVY
                factor = 0.75 + 0.25 * min(1.0, (pending_count - self.threshold_high) / self.threshold_high)
            elif pending_count >= self.threshold_medium:
                level = CongestionLevel.MODERATE
                factor = 0.5 + 0.25 * (pending_count - self.threshold_medium) / (self.threshold_high - self.threshold_medium)
            elif pending_count >= self.threshold_low:
                level = CongestionLevel.LIGHT
                factor = 0.25 * (pending_count - self.threshold_low) / (self.threshold_medium - self.threshold_low)
            else:
                level = CongestionLevel.LIGHT
                factor = 0.0

            self._state = CongestionState(
                pending_count=pending_count,
                request_rate=request_rate,
                level=level,
                factor=factor,
                last_updated=now,
            )

            return self._state

    def get_state(self) -> CongestionState:
        """Get current congestion state."""
        with self._lock:
            # Update if stale (> 5 seconds old)
            if time.time() - self._state.last_updated > 5.0:
                return self.update()
            return self._state

    @property
    def factor(self) -> float:
        """Get current congestion factor (0.0 to 1.0)."""
        return self.get_state().factor


class AdaptiveCache:
    """
    Congestion-aware cache for query results.

    Adjusts TTLs based on system load:
    - Light load: Short TTLs for fresh data
    - Heavy load: Long TTLs to reduce computation
    """

    def __init__(
        self,
        max_entries: int = MAX_CACHE_ENTRIES,
        configs: dict[CacheCategory, CacheConfig] | None = None,
        enabled: bool = True,
    ):
        """
        Initialize adaptive cache.

        Args:
            max_entries: Maximum cache entries
            configs: Category configurations (uses defaults if None)
            enabled: Whether caching is enabled
        """
        self.max_entries = max_entries
        self.configs = configs or DEFAULT_CACHE_CONFIGS.copy()
        self.enabled = enabled

        self._cache: dict[str, AdaptiveCacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._stats_by_category: dict[CacheCategory, CacheStats] = {
            cat: CacheStats() for cat in CacheCategory
        }

        self._last_cleanup = time.time()

        # Congestion detection
        self.congestion = CongestionDetector()

        logger.info(
            f"AdaptiveCache initialized: max_entries={max_entries}, "
            f"enabled={enabled}"
        )

    def _make_key(self, category: CacheCategory, key: str) -> str:
        """Create internal cache key."""
        return f"{category.value}:{key}"

    def _get_ttl(self, category: CacheCategory) -> float:
        """Get TTL for category based on current congestion."""
        config = self.configs.get(category, CacheConfig(30, 120))
        return config.get_ttl(self.congestion.factor)

    def _maybe_cleanup(self) -> None:
        """Periodically remove expired entries."""
        now = time.time()
        if now - self._last_cleanup < CLEANUP_INTERVAL:
            return

        self._last_cleanup = now
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired:
            self._cache.pop(key, None)

    def _evict_if_needed(self) -> None:
        """Evict entries if cache is full."""
        if len(self._cache) < self.max_entries:
            return

        # Remove expired first
        self._maybe_cleanup()

        # If still full, evict by priority then age
        if len(self._cache) >= self.max_entries:
            # Sort by (priority, -age) and remove lowest priority/oldest
            entries = sorted(
                self._cache.items(),
                key=lambda x: (
                    self.configs.get(x[1].category, CacheConfig(30, 120)).priority,
                    -x[1].age
                )
            )

            # Remove 10% of entries
            to_remove = max(1, len(entries) // 10)
            for key, _ in entries[:to_remove]:
                self._cache.pop(key, None)
                self._stats.evictions += 1

    def get(self, category: CacheCategory, key: str) -> Any | None:
        """
        Get a cached value.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None

        with self._lock:
            self._maybe_cleanup()

            full_key = self._make_key(category, key)
            entry = self._cache.get(full_key)

            if entry is None:
                self._stats.misses += 1
                self._stats_by_category[category].misses += 1
                return None

            if entry.is_expired():
                del self._cache[full_key]
                self._stats.misses += 1
                self._stats_by_category[category].misses += 1
                return None

            entry.hit_count += 1
            self._stats.hits += 1
            self._stats_by_category[category].hits += 1
            return entry.value

    def set(
        self,
        category: CacheCategory,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> bool:
        """
        Set a cached value.

        Args:
            category: Cache category
            key: Cache key
            value: Value to cache
            ttl: Override TTL (uses adaptive TTL if None)

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        with self._lock:
            self._evict_if_needed()

            if ttl is None:
                ttl = self._get_ttl(category)

            now = time.time()
            full_key = self._make_key(category, key)

            self._cache[full_key] = AdaptiveCacheEntry(
                value=value,
                category=category,
                created_at=now,
                expires_at=now + ttl,
            )
            return True

    def get_or_compute(
        self,
        category: CacheCategory,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: float | None = None,
    ) -> Any:
        """
        Get cached value or compute and cache it.

        Args:
            category: Cache category
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl: Override TTL (uses adaptive TTL if None)

        Returns:
            Cached or computed value
        """
        # Record request for rate calculation
        self.congestion.record_request()

        # Try cache first
        result = self.get(category, key)
        if result is not None:
            return result

        # Compute value
        start = time.perf_counter()
        result = compute_fn()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Update stats
        with self._lock:
            self._stats.computations += 1
            self._stats.compute_time_ms += elapsed_ms
            self._stats_by_category[category].computations += 1
            self._stats_by_category[category].compute_time_ms += elapsed_ms

        # Cache result
        self.set(category, key, result, ttl)

        return result

    def invalidate(self, category: CacheCategory, key: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            True if entry existed and was removed
        """
        with self._lock:
            full_key = self._make_key(category, key)
            if full_key in self._cache:
                del self._cache[full_key]
                self._stats.invalidations += 1
                self._stats_by_category[category].invalidations += 1
                return True
            return False

    def invalidate_category(self, category: CacheCategory) -> int:
        """
        Invalidate all entries in a category.

        Args:
            category: Cache category to invalidate

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            prefix = f"{category.value}:"
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]

            for key in keys_to_remove:
                del self._cache[key]

            count = len(keys_to_remove)
            self._stats.invalidations += count
            self._stats_by_category[category].invalidations += count

            logger.debug(f"Invalidated {count} entries in category {category.value}")
            return count

    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries.

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.invalidations += count
            logger.info(f"Invalidated all {count} cache entries")
            return count

    def on_new_block(self) -> None:
        """Called when a new block is mined. Invalidates affected caches."""
        self.invalidate_category(CacheCategory.INTENTS)
        self.invalidate_category(CacheCategory.CONTRACTS)
        self.invalidate_category(CacheCategory.STATS)
        logger.debug("Cache invalidated for new block")

    def on_new_entry(self) -> None:
        """Called when a new entry is submitted. Invalidates pending caches."""
        self.invalidate_category(CacheCategory.INTENTS)
        logger.debug("Intent cache invalidated for new entry")

    def on_settlement(self) -> None:
        """Called when a settlement is accepted. Invalidates contract caches."""
        self.invalidate_category(CacheCategory.CONTRACTS)
        self.invalidate_category(CacheCategory.INTENTS)
        logger.debug("Cache invalidated for settlement")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            congestion_state = self.congestion.get_state()

            return {
                "enabled": self.enabled,
                "size": len(self._cache),
                "max_size": self.max_entries,
                "congestion": congestion_state.to_dict(),
                "overall": self._stats.to_dict(),
                "by_category": {
                    cat.value: stats.to_dict()
                    for cat, stats in self._stats_by_category.items()
                },
                "current_ttls": {
                    cat.value: round(self._get_ttl(cat), 1)
                    for cat in CacheCategory
                },
            }


# =============================================================================
# Helper Functions
# =============================================================================

def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key from arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Stable cache key string
    """
    key_parts = [str(a) for a in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = ":".join(key_parts)

    # Hash if too long
    if len(key_str) > 200:
        return hashlib.md5(key_str.encode()).hexdigest()
    return key_str


def create_cache_from_env() -> AdaptiveCache:
    """
    Create an AdaptiveCache from environment variables.

    Environment variables:
        NATLANGCHAIN_QUERY_CACHE_ENABLED: true/false (default: true)
        NATLANGCHAIN_QUERY_CACHE_MAX_SIZE: max entries (default: 5000)
        NATLANGCHAIN_CONGESTION_THRESHOLD_LOW: pending count (default: 50)
        NATLANGCHAIN_CONGESTION_THRESHOLD_HIGH: pending count (default: 200)

    Returns:
        Configured AdaptiveCache instance
    """
    enabled = os.getenv('NATLANGCHAIN_QUERY_CACHE_ENABLED', 'true').lower() == 'true'
    max_size = int(os.getenv('NATLANGCHAIN_QUERY_CACHE_MAX_SIZE', str(MAX_CACHE_ENTRIES)))

    threshold_low = int(os.getenv('NATLANGCHAIN_CONGESTION_THRESHOLD_LOW', str(CONGESTION_THRESHOLD_LOW)))
    threshold_high = int(os.getenv('NATLANGCHAIN_CONGESTION_THRESHOLD_HIGH', str(CONGESTION_THRESHOLD_HIGH)))

    cache = AdaptiveCache(max_entries=max_size, enabled=enabled)
    cache.congestion.threshold_low = threshold_low
    cache.congestion.threshold_high = threshold_high

    return cache


# =============================================================================
# Global Instance
# =============================================================================

_adaptive_cache: AdaptiveCache | None = None
_cache_lock = threading.Lock()


def get_adaptive_cache() -> AdaptiveCache:
    """
    Get the global adaptive cache instance.

    Returns:
        Shared AdaptiveCache instance
    """
    global _adaptive_cache

    with _cache_lock:
        if _adaptive_cache is None:
            _adaptive_cache = create_cache_from_env()
        return _adaptive_cache


def reset_adaptive_cache() -> None:
    """Reset the global adaptive cache (for testing)."""
    global _adaptive_cache

    with _cache_lock:
        if _adaptive_cache is not None:
            _adaptive_cache.invalidate_all()
        _adaptive_cache = None
