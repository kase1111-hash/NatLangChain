"""
Shared state for NatLangChain API.

This module holds the shared instances that are used across all blueprints.
The instances are initialized by the main api module and then shared via
this module for clean dependency injection.
"""

import json
import os
import threading
from typing import Any

# Import blockchain - always required
from blockchain import NatLangChain

# Import manager registry
from api.utils import managers

# ============================================================
# Shared State
# ============================================================

# The blockchain instance
blockchain: NatLangChain = NatLangChain()

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")

# SECURITY: Lock for file operations to prevent TOCTOU race conditions
_chain_file_lock = threading.Lock()


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
# Chain Persistence
# ============================================================

def load_chain():
    """
    Load blockchain from file if it exists, with automatic decryption support.

    Thread-safe: Uses _chain_file_lock to prevent race conditions.
    """
    global blockchain

    with _chain_file_lock:
        try:
            with open(CHAIN_DATA_FILE, 'r') as f:
                raw_data = f.read()

            # Check if data is encrypted
            if is_encryption_enabled() and is_encrypted(raw_data):
                try:
                    raw_data = decrypt_chain_data(raw_data)
                except Exception as e:
                    print(f"Warning: Failed to decrypt chain data: {e}")
                    print("Starting with empty blockchain")
                    return

            data = json.loads(raw_data)
            blockchain = NatLangChain.from_dict(data)
            print(f"Loaded blockchain with {len(blockchain.chain)} blocks")

        except FileNotFoundError:
            print("No existing chain data found. Starting fresh.")
        except PermissionError:
            print(f"Warning: Cannot read {CHAIN_DATA_FILE} - permission denied")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid chain data format: {e}")
        except Exception as e:
            print(f"Warning: Error loading chain: {e}")


def save_chain():
    """
    Save blockchain to file with optional encryption.

    Thread-safe: Uses _chain_file_lock to prevent race conditions.
    """
    global blockchain

    with _chain_file_lock:
        try:
            data = json.dumps(blockchain.to_dict(), indent=2)

            # Encrypt if enabled
            if is_encryption_enabled() and encrypt_chain_data:
                data = encrypt_chain_data(data)

            with open(CHAIN_DATA_FILE, 'w') as f:
                f.write(data)

        except PermissionError:
            print(f"Warning: Cannot write to {CHAIN_DATA_FILE} - permission denied")
        except Exception as e:
            print(f"Warning: Error saving chain: {e}")
