"""
Shared state for NatLangChain API.

This module holds the shared instances that are used across all blueprints.
The instances are initialized by the main api module and then shared via
this module for clean dependency injection.

Storage backends are pluggable - set STORAGE_BACKEND environment variable:
- "json" (default): JSON file storage
- "postgresql": PostgreSQL database
- "memory": In-memory (for testing)
"""

import logging
import threading
from typing import Any

# Import blockchain - always required
from blockchain import NatLangChain

logger = logging.getLogger(__name__)

# ============================================================
# Shared State
# ============================================================

# The blockchain instance
blockchain: NatLangChain = NatLangChain()

# Cryptographic agent identity (Audit 1.3)
agent_identity = None  # Initialized via init_identity()

# Storage backend (lazy initialized)
_storage = None

# ============================================================
# Graceful Shutdown State
# ============================================================

_shutdown_event = threading.Event()
_in_flight_requests = 0
_request_lock = threading.Lock()


def is_shutting_down() -> bool:
    """Check if the server is in shutdown state."""
    return _shutdown_event.is_set()


def set_shutting_down():
    """Signal that the server is shutting down."""
    _shutdown_event.set()


def track_request_start():
    """Increment in-flight request counter."""
    global _in_flight_requests
    with _request_lock:
        _in_flight_requests += 1


def track_request_end():
    """Decrement in-flight request counter."""
    global _in_flight_requests
    with _request_lock:
        _in_flight_requests = max(0, _in_flight_requests - 1)


def get_in_flight_count() -> int:
    """Get number of in-flight requests."""
    with _request_lock:
        return _in_flight_requests


def get_storage():
    """Get or create the storage backend."""
    global _storage
    if _storage is None:
        from storage import get_storage_backend

        _storage = get_storage_backend()
    return _storage


# ============================================================
# Encryption Helpers
# ============================================================

# Encryption support for data at rest
try:
    from encryption import (
        ENCRYPTION_KEY_ENV,
        EncryptionError,
        decrypt_chain_data,
        decrypt_sensitive_fields,
        encrypt_chain_data,
        encrypt_sensitive_fields,
        is_encrypted,
        is_encryption_enabled,
    )

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

    def is_encryption_enabled():
        return False

    encrypt_chain_data = None
    decrypt_chain_data = None

    def encrypt_sensitive_fields(x, **kwargs):
        return x

    def decrypt_sensitive_fields(x, **kwargs):
        return x

    def is_encrypted(x):
        return False

    EncryptionError = Exception
    ENCRYPTION_KEY_ENV = "NATLANGCHAIN_ENCRYPTION_KEY"


def create_entry_with_encryption(
    content: str, author: str, intent: str, metadata: dict[str, Any] | None = None
) -> Any:
    """
    Create an entry with optional encryption of sensitive metadata fields.

    Args:
        content: Entry content
        author: Entry author
        intent: Entry intent
        metadata: Optional metadata dictionary

    Returns:
        NaturalLanguageEntry with encrypted sensitive fields if encryption enabled
    """
    from blockchain import NaturalLanguageEntry

    # Encrypt sensitive metadata fields if encryption is enabled
    encrypted_metadata = metadata or {}
    if is_encryption_enabled() and encrypted_metadata:
        encrypted_metadata = encrypt_sensitive_fields(
            encrypted_metadata, additional_fields={"private_notes", "internal_id", "contact_info"}
        )

    entry = NaturalLanguageEntry(
        content=content, author=author, intent=intent, metadata=encrypted_metadata
    )

    # Sign entry with cryptographic identity if available (Audit 1.3)
    if agent_identity is not None:
        try:
            from identity import sign_entry_dict
            entry_dict = entry.to_dict()
            signed = sign_entry_dict(entry_dict, agent_identity)
            entry.signature = signed["metadata"].get("signature")
            entry.public_key = signed["metadata"].get("public_key")
        except (ImportError, ValueError, OSError) as e:
            logger.warning("Failed to sign entry: %s", e)

    return entry


def decrypt_entry_metadata(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Decrypt sensitive fields in entry metadata if encryption is enabled.

    Args:
        entry_dict: Entry dictionary with potentially encrypted metadata

    Returns:
        Entry dictionary with decrypted metadata
    """
    if not is_encryption_enabled():
        return entry_dict

    if entry_dict.get("metadata"):
        entry_dict["metadata"] = decrypt_sensitive_fields(
            entry_dict["metadata"]
        )

    return entry_dict


# ============================================================
# Chain Persistence (using storage abstraction)
# ============================================================


def load_chain():
    """
    Load blockchain from storage backend.

    Uses the configured storage backend (JSON file, PostgreSQL, etc.)
    """
    global blockchain

    try:
        storage = get_storage()
        data = storage.load_chain()

        if data is None:
            logger.info("No existing chain data found. Starting fresh.")
            return

        blockchain = NatLangChain.from_dict(data)
        logger.info("Loaded blockchain with %d blocks", len(blockchain.chain))
        logger.info("Storage backend: %s", storage.__class__.__name__)

    except (OSError, KeyError, ValueError) as e:
        logger.warning("Error loading chain: %s", e)
        logger.info("Starting with empty blockchain")


def save_chain():
    """
    Save blockchain to storage backend.

    Uses the configured storage backend (JSON file, PostgreSQL, etc.)
    """
    global blockchain

    try:
        storage = get_storage()
        storage.save_chain(blockchain.to_dict())

    except (OSError, ValueError) as e:
        logger.warning("Error saving chain: %s", e)


def get_storage_info() -> dict[str, Any]:
    """
    Get information about the current storage backend.

    Returns:
        Dictionary with storage backend info
    """
    try:
        storage = get_storage()
        return storage.get_info()
    except (OSError, ValueError, RuntimeError) as e:
        return {
            "error": str(e),
            "available": False,
        }
