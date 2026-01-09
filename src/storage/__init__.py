"""
Storage abstraction layer for NatLangChain.

This package provides a pluggable storage backend system that allows
the blockchain to be persisted to different storage systems:

- JSON file (default, current behavior)
- PostgreSQL (for production scalability)
- Memory (for testing)

Usage:
    from storage import get_storage_backend, StorageBackend

    # Get configured backend (based on environment)
    storage = get_storage_backend()

    # Save chain data
    storage.save_chain(blockchain.to_dict())

    # Load chain data
    data = storage.load_chain()
"""

import os
from typing import TYPE_CHECKING

from storage.base import StorageBackend, StorageError
from storage.json_file import JSONFileStorage
from storage.memory import MemoryStorage

# Lazy import for PostgreSQL to avoid requiring psycopg2
if TYPE_CHECKING:
    from storage.postgresql import PostgreSQLStorage

__all__ = [
    "JSONFileStorage",
    "MemoryStorage",
    "StorageBackend",
    "StorageError",
    "get_storage_backend",
]


def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend based on environment variables.

    Environment variables:
        STORAGE_BACKEND: Backend type ("json", "postgresql", "memory")
        CHAIN_DATA_FILE: Path for JSON file storage (default: chain_data.json)
        DATABASE_URL: PostgreSQL connection URL

    Returns:
        Configured StorageBackend instance
    """
    backend_type = os.getenv("STORAGE_BACKEND", "json").lower()

    if backend_type == "json":
        data_file = os.getenv("CHAIN_DATA_FILE", "chain_data.json")
        return JSONFileStorage(data_file)

    elif backend_type == "postgresql" or backend_type == "postgres":
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise StorageError("DATABASE_URL environment variable required for PostgreSQL backend")
        from storage.postgresql import PostgreSQLStorage

        return PostgreSQLStorage(database_url)

    elif backend_type == "memory":
        return MemoryStorage()

    else:
        raise StorageError(f"Unknown storage backend: {backend_type}")


# Default storage instance (lazy initialization)
_default_storage: StorageBackend | None = None


def get_default_storage() -> StorageBackend:
    """Get or create the default storage backend."""
    global _default_storage
    if _default_storage is None:
        _default_storage = get_storage_backend()
    return _default_storage
