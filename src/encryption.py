"""
NatLangChain - Data Encryption Module

Provides encryption/decryption utilities for protecting sensitive data at rest.
Uses AES-256-GCM for authenticated encryption with PBKDF2 key derivation.

Security Features:
- AES-256-GCM for encryption with authentication
- PBKDF2-HMAC-SHA256 for key derivation (1,000,000 iterations)
- Random salt and IV for each encryption operation
- Secure key management via environment variables
- Field-level encryption support for sensitive metadata
"""

import base64
import hashlib
import json
import os
import secrets
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Constants
SALT_SIZE = 16  # 128 bits
IV_SIZE = 12  # 96 bits for GCM (recommended)
KEY_SIZE = 32  # 256 bits
# SECURITY: 1M iterations exceeds OWASP 2023 minimum (600k) for better protection
# against brute-force attacks on modern hardware
PBKDF2_ITERATIONS = 1_000_000

# Environment variable for encryption key
ENCRYPTION_KEY_ENV = "NATLANGCHAIN_ENCRYPTION_KEY"
ENCRYPTION_ENABLED_ENV = "NATLANGCHAIN_ENCRYPTION_ENABLED"

# Sensitive metadata fields that should be encrypted at field level
SENSITIVE_METADATA_FIELDS = {
    "contract_terms",
    "financial_terms",
    "payment_amount",
    "wallet_address",
    "private_notes",
    "negotiation_strategy",
    "batna",  # Best Alternative To Negotiated Agreement
    "reservation_price",
    "personal_info",
    "identity_data",
    "api_key",
    "credentials",
    "secret",
    "password",
    "ssn",
    "tax_id",
}

# Encrypted data prefix for identification
ENCRYPTED_PREFIX = "ENC:1:"  # Version 1 encrypted data


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""



class KeyDerivationError(Exception):
    """Raised when key derivation fails."""



def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit encryption key from a password using PBKDF2.

    Args:
        password: The password/passphrase to derive the key from
        salt: Random salt for key derivation

    Returns:
        32-byte derived key
    """
    if not password:
        raise KeyDerivationError("Password cannot be empty")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def _get_encryption_key() -> str | None:
    """
    Get the encryption key from environment variable.

    Returns:
        The encryption key or None if not configured
    """
    return os.getenv(ENCRYPTION_KEY_ENV)


def is_encryption_enabled() -> bool:
    """
    Check if encryption is enabled.

    Returns:
        True if encryption is enabled and a key is configured
    """
    enabled = os.getenv(ENCRYPTION_ENABLED_ENV, "true").lower()
    if enabled in ("false", "0", "no", "off"):
        return False
    return _get_encryption_key() is not None


def generate_encryption_key() -> str:
    """
    Generate a cryptographically secure encryption key.

    Returns:
        Base64-encoded 256-bit random key
    """
    key_bytes = secrets.token_bytes(KEY_SIZE)
    return base64.b64encode(key_bytes).decode("utf-8")


def encrypt_data(data: str | bytes | dict[str, Any], key: str | None = None) -> str:
    """
    Encrypt data using AES-256-GCM.

    Args:
        data: Data to encrypt (string, bytes, or JSON-serializable dict)
        key: Optional encryption key. If not provided, uses environment variable.

    Returns:
        Base64-encoded encrypted data with format: ENCRYPTED_PREFIX + salt + iv + ciphertext

    Raises:
        EncryptionError: If encryption fails
    """
    encryption_key = key or _get_encryption_key()
    if not encryption_key:
        raise EncryptionError(
            f"No encryption key provided. Set {ENCRYPTION_KEY_ENV} environment variable "
            "or generate one with generate_encryption_key()"
        )

    try:
        # Convert data to bytes
        if isinstance(data, dict):
            data_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        # Generate random salt and IV
        salt = secrets.token_bytes(SALT_SIZE)
        iv = secrets.token_bytes(IV_SIZE)

        # Derive key from password
        derived_key = _derive_key(encryption_key, salt)

        # Encrypt using AES-256-GCM
        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(iv, data_bytes, None)

        # Combine salt + iv + ciphertext and encode
        encrypted_blob = salt + iv + ciphertext
        encoded = base64.b64encode(encrypted_blob).decode("utf-8")

        return ENCRYPTED_PREFIX + encoded

    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e!s}") from e


def decrypt_data(
    encrypted_data: str, key: str | None = None, return_type: str = "auto"
) -> str | bytes | dict[str, Any]:
    """
    Decrypt AES-256-GCM encrypted data.

    Args:
        encrypted_data: Base64-encoded encrypted data with ENCRYPTED_PREFIX
        key: Optional decryption key. If not provided, uses environment variable.
        return_type: "auto", "str", "bytes", or "json"

    Returns:
        Decrypted data as string, bytes, or dict based on return_type

    Raises:
        EncryptionError: If decryption fails
    """
    encryption_key = key or _get_encryption_key()
    if not encryption_key:
        raise EncryptionError(
            f"No decryption key provided. Set {ENCRYPTION_KEY_ENV} environment variable."
        )

    try:
        # Check and remove prefix
        if not encrypted_data.startswith(ENCRYPTED_PREFIX):
            raise EncryptionError("Invalid encrypted data format: missing prefix")

        encoded_data = encrypted_data[len(ENCRYPTED_PREFIX) :]

        # Decode from base64
        encrypted_blob = base64.b64decode(encoded_data)

        # Extract salt, iv, and ciphertext
        if len(encrypted_blob) < SALT_SIZE + IV_SIZE + 16:  # 16 = minimum ciphertext with tag
            raise EncryptionError("Invalid encrypted data: too short")

        salt = encrypted_blob[:SALT_SIZE]
        iv = encrypted_blob[SALT_SIZE : SALT_SIZE + IV_SIZE]
        ciphertext = encrypted_blob[SALT_SIZE + IV_SIZE :]

        # Derive key from password
        derived_key = _derive_key(encryption_key, salt)

        # Decrypt using AES-256-GCM
        aesgcm = AESGCM(derived_key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)

        # Return in requested format
        if return_type == "bytes":
            return plaintext

        plaintext_str = plaintext.decode("utf-8")

        if return_type == "str":
            return plaintext_str

        # Auto-detect or explicit JSON
        if return_type in ("auto", "json"):
            try:
                return json.loads(plaintext_str)
            except json.JSONDecodeError:
                if return_type == "json":
                    raise
                return plaintext_str

        return plaintext_str

    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e!s}") from e


def is_encrypted(data: str) -> bool:
    """
    Check if a string is encrypted data.

    Args:
        data: String to check

    Returns:
        True if data appears to be encrypted
    """
    return isinstance(data, str) and data.startswith(ENCRYPTED_PREFIX)


def encrypt_sensitive_fields(
    metadata: dict[str, Any], key: str | None = None, additional_fields: set | None = None
) -> dict[str, Any]:
    """
    Encrypt sensitive fields within metadata dictionary.

    Args:
        metadata: Metadata dictionary to process
        key: Optional encryption key
        additional_fields: Additional field names to encrypt

    Returns:
        New dictionary with sensitive fields encrypted
    """
    if not metadata:
        return metadata

    if not is_encryption_enabled():
        return metadata

    fields_to_encrypt = SENSITIVE_METADATA_FIELDS.copy()
    if additional_fields:
        fields_to_encrypt.update(additional_fields)

    result = {}
    for field, value in metadata.items():
        field_lower = field.lower()
        # Normalize separators (hyphens to underscores) for consistent matching
        field_normalized = field_lower.replace("-", "_")
        # Check if field name matches any sensitive pattern
        # Use word-boundary matching to avoid false positives like "secretary" matching "secret"
        # A sensitive field matches if it appears as a complete word (delimited by _ or at start/end)
        field_parts = set(field_normalized.split("_"))
        should_encrypt = (
            field_normalized in fields_to_encrypt
            or any(sensitive in field_parts for sensitive in fields_to_encrypt)
            or any(
                field_normalized.startswith(sensitive + "_")
                or field_normalized.endswith("_" + sensitive)
                or ("_" + sensitive + "_") in field_normalized
                for sensitive in fields_to_encrypt
            )
        )

        if should_encrypt and value is not None:
            # Support strings, dicts, lists, and numeric types
            if isinstance(value, (str, dict, list, int, float, bool)) and not is_encrypted(
                str(value)
            ):
                try:
                    if isinstance(value, str):
                        result[field] = encrypt_data(value, key)
                    else:
                        # Convert non-strings to JSON for encryption
                        result[field] = encrypt_data(json.dumps(value), key)
                except EncryptionError:
                    # If encryption fails, keep original value with warning marker
                    result[field] = value
                    result[f"__{field}_encryption_failed"] = True
            else:
                result[field] = value
        else:
            result[field] = value

    return result


def decrypt_sensitive_fields(metadata: dict[str, Any], key: str | None = None) -> dict[str, Any]:
    """
    Decrypt sensitive fields within metadata dictionary.

    Args:
        metadata: Metadata dictionary with encrypted fields
        key: Optional decryption key

    Returns:
        New dictionary with encrypted fields decrypted
    """
    if not metadata:
        return metadata

    result = {}
    for field, value in metadata.items():
        # Skip encryption failure markers
        if field.startswith("__") and field.endswith("_encryption_failed"):
            continue

        if isinstance(value, str) and is_encrypted(value):
            try:
                decrypted = decrypt_data(value, key)
                # Try to parse as JSON
                if isinstance(decrypted, str):
                    try:
                        result[field] = json.loads(decrypted)
                    except json.JSONDecodeError:
                        result[field] = decrypted
                else:
                    result[field] = decrypted
            except EncryptionError:
                # If decryption fails, keep encrypted value
                result[field] = value
        else:
            result[field] = value

    return result


def encrypt_chain_data(chain_data: dict[str, Any], key: str | None = None) -> str:
    """
    Encrypt entire blockchain data for storage.

    Args:
        chain_data: Full blockchain data dictionary
        key: Optional encryption key

    Returns:
        Encrypted blockchain data string
    """
    return encrypt_data(chain_data, key)


def decrypt_chain_data(encrypted_data: str, key: str | None = None) -> dict[str, Any]:
    """
    Decrypt entire blockchain data from storage.

    Args:
        encrypted_data: Encrypted blockchain data string
        key: Optional decryption key

    Returns:
        Decrypted blockchain data dictionary
    """
    return decrypt_data(encrypted_data, key, return_type="json")


def hash_sensitive_value(value: str, salt: str | None = None) -> str:
    """
    Create a one-way hash of a sensitive value for comparison/lookup.
    Useful for wallet addresses or identifiers that need to be searchable
    without storing the plain value.

    Args:
        value: Value to hash
        salt: Optional salt (uses random if not provided)

    Returns:
        Salted hash in format "HASH:1:salt:hash"
    """
    if salt is None:
        salt = secrets.token_hex(16)

    hash_input = f"{salt}:{value}".encode()
    hash_value = hashlib.sha256(hash_input).hexdigest()

    return f"HASH:1:{salt}:{hash_value}"


def verify_hashed_value(value: str, hashed: str) -> bool:
    """
    Verify a value against its hash.

    Args:
        value: Plain value to verify
        hashed: Previously created hash

    Returns:
        True if value matches hash
    """
    if not hashed.startswith("HASH:1:"):
        return False

    parts = hashed.split(":")
    if len(parts) != 4:
        return False

    salt = parts[2]
    expected_hash = parts[3]

    hash_input = f"{salt}:{value}".encode()
    actual_hash = hashlib.sha256(hash_input).hexdigest()

    # Constant-time comparison
    return secrets.compare_digest(actual_hash, expected_hash)


# Export public API
__all__ = [
    "ENCRYPTION_ENABLED_ENV",
    "ENCRYPTION_KEY_ENV",
    "SENSITIVE_METADATA_FIELDS",
    "EncryptionError",
    "KeyDerivationError",
    "decrypt_chain_data",
    "decrypt_data",
    "decrypt_sensitive_fields",
    "encrypt_chain_data",
    "encrypt_data",
    "encrypt_sensitive_fields",
    "generate_encryption_key",
    "hash_sensitive_value",
    "is_encrypted",
    "is_encryption_enabled",
    "verify_hashed_value",
]
