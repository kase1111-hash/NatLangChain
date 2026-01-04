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

import os
from typing import Any

# Import blockchain - always required
from blockchain import NatLangChain

# Import manager registry
from .utils import managers

# ============================================================
# Shared State
# ============================================================

# The blockchain instance
blockchain: NatLangChain = NatLangChain()

# Storage backend (lazy initialized)
_storage = None


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


def create_entry_with_encryption(content: str, author: str, intent: str,
                                  metadata: dict[str, Any] | None = None) -> Any:
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
            encrypted_metadata,
            sensitive_keys=["private_notes", "internal_id", "contact_info"]
        )

    return NaturalLanguageEntry(
        content=content,
        author=author,
        intent=intent,
        metadata=encrypted_metadata
    )


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

    if "metadata" in entry_dict and entry_dict["metadata"]:
        entry_dict["metadata"] = decrypt_sensitive_fields(
            entry_dict["metadata"],
            sensitive_keys=["private_notes", "internal_id", "contact_info"]
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
            print("No existing chain data found. Starting fresh.")
            return

        blockchain = NatLangChain.from_dict(data)
        print(f"Loaded blockchain with {len(blockchain.chain)} blocks")
        print(f"Storage backend: {storage.__class__.__name__}")

    except Exception as e:
        print(f"Warning: Error loading chain: {e}")
        print("Starting with empty blockchain")


def save_chain():
    """
    Save blockchain to storage backend.

    Uses the configured storage backend (JSON file, PostgreSQL, etc.)
    """
    global blockchain

    try:
        storage = get_storage()
        storage.save_chain(blockchain.to_dict())

    except Exception as e:
        print(f"Warning: Error saving chain: {e}")


def get_storage_info() -> dict[str, Any]:
    """
    Get information about the current storage backend.

    Returns:
        Dictionary with storage backend info
    """
    try:
        storage = get_storage()
        return storage.get_info()
    except Exception as e:
        return {
            "error": str(e),
            "available": False,
        }
