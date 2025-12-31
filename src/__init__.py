"""
NatLangChain - Natural Language Blockchain

A distributed ledger paradigm where natural language prose is the primary substrate.

Core Components:
    - NatLangChain: Main blockchain implementation
    - NaturalLanguageEntry: Entry type for prose-based transactions
    - Block: Immutable block in the chain
    - ProofOfUnderstanding: LLM-based validation
    - HybridValidator: Combined rule + LLM validation

Infrastructure (for production deployments):
    - storage: Pluggable storage backends (JSON, PostgreSQL, Memory)
    - monitoring: Metrics, logging, and health endpoints
    - scaling: Distributed locking, caching, instance coordination

Usage:
    from natlangchain import NatLangChain, NaturalLanguageEntry

    chain = NatLangChain()
    entry = NaturalLanguageEntry(
        content="Alice transfers the vintage car to Bob",
        author="alice",
        intent="asset_transfer"
    )
    chain.add_entry(entry)
"""

__version__ = "0.1.0"

# =============================================================================
# Core Components (always available)
# =============================================================================

from .blockchain import Block, NatLangChain, NaturalLanguageEntry

# Validator requires anthropic - use lazy import
try:
    from .validator import HybridValidator, ProofOfUnderstanding
    _HAS_VALIDATOR = True
except ImportError:
    HybridValidator = None  # type: ignore
    ProofOfUnderstanding = None  # type: ignore
    _HAS_VALIDATOR = False


# =============================================================================
# Infrastructure Components (lazy imports for optional dependencies)
# =============================================================================

def get_storage_backend():
    """
    Get the configured storage backend.

    Returns storage backend based on STORAGE_BACKEND environment variable:
    - "json" (default): Local JSON file storage
    - "postgresql": PostgreSQL database storage
    - "memory": In-memory storage (for testing)

    Requires: No additional dependencies for json/memory backends.
              PostgreSQL requires: psycopg2-binary

    Example:
        storage = get_storage_backend()
        storage.save_chain(chain.to_dict())
    """
    from .storage import get_storage_backend as _get_storage
    return _get_storage()


def get_metrics():
    """
    Get the global metrics collector.

    Provides counters, gauges, and histograms for application monitoring.
    Exports to Prometheus format via /metrics endpoint.

    Example:
        metrics = get_metrics()
        metrics.increment("entries_added")
        metrics.timing("request_duration_ms", 42.5)
    """
    from .monitoring import metrics
    return metrics


def get_logger(name: str):
    """
    Get a structured logger for a module.

    Returns a logger configured for JSON output in production
    and colored console output in development.

    Args:
        name: Logger name (typically __name__)

    Example:
        logger = get_logger(__name__)
        logger.info("Processing entry", extra={"entry_id": "abc123"})
    """
    from .monitoring import get_logger as _get_logger
    return _get_logger(name)


def get_lock_manager():
    """
    Get the distributed lock manager.

    Returns lock manager based on REDIS_URL environment variable:
    - Without REDIS_URL: Local thread-based locks
    - With REDIS_URL: Distributed Redis locks

    Example:
        lock_manager = get_lock_manager()
        with lock_manager.lock("mining"):
            mine_block()
    """
    from .scaling import get_lock_manager as _get_lock
    return _get_lock()


def get_cache():
    """
    Get the distributed cache.

    Returns cache based on REDIS_URL environment variable:
    - Without REDIS_URL: Local in-memory LRU cache
    - With REDIS_URL: Distributed Redis cache

    Example:
        cache = get_cache()
        cache.set("key", {"data": "value"}, ttl=300)
        value = cache.get("key")
    """
    from .scaling import get_cache as _get_cache
    return _get_cache()


def get_coordinator():
    """
    Get the instance coordinator for multi-instance deployments.

    Provides instance discovery, leader election, and health tracking.

    Example:
        coordinator = get_coordinator()
        if coordinator.is_leader():
            perform_singleton_task()
    """
    from .scaling import get_coordinator as _get_coord
    return _get_coord()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    # Core blockchain
    "Block",
    "NatLangChain",
    "NaturalLanguageEntry",
    # Validators (may be None if anthropic not installed)
    "HybridValidator",
    "ProofOfUnderstanding",
    # Infrastructure accessors
    "get_storage_backend",
    "get_metrics",
    "get_logger",
    "get_lock_manager",
    "get_cache",
    "get_coordinator",
]
