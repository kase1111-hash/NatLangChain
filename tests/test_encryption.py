"""
Tests for NatLangChain encryption module.

These tests verify that:
1. Key generation produces valid keys
2. Encryption and decryption work correctly
3. Field-level encryption handles sensitive metadata
4. Chain data encryption/decryption works
5. Error cases are handled properly
"""

import os
import sys
import json
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from encryption import (
    generate_encryption_key,
    encrypt_data,
    decrypt_data,
    is_encrypted,
    encrypt_sensitive_fields,
    decrypt_sensitive_fields,
    encrypt_chain_data,
    decrypt_chain_data,
    hash_sensitive_value,
    verify_hashed_value,
    EncryptionError,
    ENCRYPTED_PREFIX,
    SENSITIVE_METADATA_FIELDS,
)


class TestKeyGeneration:
    """Tests for encryption key generation."""

    def test_generate_key_returns_string(self):
        """Key generation should return a string."""
        key = generate_encryption_key()
        assert isinstance(key, str)

    def test_generate_key_is_base64(self):
        """Generated key should be valid base64."""
        import base64
        key = generate_encryption_key()
        # Should not raise
        decoded = base64.b64decode(key)
        assert len(decoded) == 32  # 256 bits

    def test_generate_key_unique(self):
        """Each generated key should be unique."""
        keys = [generate_encryption_key() for _ in range(10)]
        assert len(set(keys)) == 10


class TestEncryptDecrypt:
    """Tests for basic encryption and decryption."""

    @pytest.fixture
    def test_key(self):
        """Generate a test encryption key."""
        return generate_encryption_key()

    def test_encrypt_string(self, test_key):
        """Should encrypt a string."""
        plaintext = "Hello, World!"
        encrypted = encrypt_data(plaintext, key=test_key)

        assert encrypted.startswith(ENCRYPTED_PREFIX)
        assert encrypted != plaintext

    def test_decrypt_string(self, test_key):
        """Should decrypt back to original string."""
        plaintext = "Hello, World!"
        encrypted = encrypt_data(plaintext, key=test_key)
        decrypted = decrypt_data(encrypted, key=test_key, return_type="str")

        assert decrypted == plaintext

    def test_encrypt_dict(self, test_key):
        """Should encrypt a dictionary."""
        data = {"name": "Alice", "balance": 1000}
        encrypted = encrypt_data(data, key=test_key)

        assert encrypted.startswith(ENCRYPTED_PREFIX)

    def test_decrypt_dict(self, test_key):
        """Should decrypt back to original dictionary."""
        data = {"name": "Alice", "balance": 1000}
        encrypted = encrypt_data(data, key=test_key)
        decrypted = decrypt_data(encrypted, key=test_key)

        assert decrypted == data

    def test_encrypt_with_unicode(self, test_key):
        """Should handle unicode characters."""
        plaintext = "Hello, \u4e16\u754c! \U0001F600"
        encrypted = encrypt_data(plaintext, key=test_key)
        decrypted = decrypt_data(encrypted, key=test_key, return_type="str")

        assert decrypted == plaintext

    def test_encrypt_empty_string(self, test_key):
        """Should handle empty strings."""
        encrypted = encrypt_data("", key=test_key)
        decrypted = decrypt_data(encrypted, key=test_key, return_type="str")

        assert decrypted == ""

    def test_encrypt_large_data(self, test_key):
        """Should handle large data."""
        plaintext = "x" * 1_000_000  # 1MB
        encrypted = encrypt_data(plaintext, key=test_key)
        decrypted = decrypt_data(encrypted, key=test_key, return_type="str")

        assert decrypted == plaintext

    def test_wrong_key_fails(self, test_key):
        """Decryption with wrong key should fail."""
        plaintext = "Secret message"
        encrypted = encrypt_data(plaintext, key=test_key)
        wrong_key = generate_encryption_key()

        with pytest.raises(EncryptionError):
            decrypt_data(encrypted, key=wrong_key)

    def test_corrupted_data_fails(self, test_key):
        """Decryption of corrupted data should fail."""
        plaintext = "Secret message"
        encrypted = encrypt_data(plaintext, key=test_key)
        # Corrupt the data
        corrupted = encrypted[:-5] + "XXXXX"

        with pytest.raises(EncryptionError):
            decrypt_data(corrupted, key=test_key)


class TestIsEncrypted:
    """Tests for encrypted data detection."""

    def test_encrypted_data_detected(self):
        """Should detect encrypted data."""
        key = generate_encryption_key()
        encrypted = encrypt_data("test", key=key)

        assert is_encrypted(encrypted) is True

    def test_plain_string_not_detected(self):
        """Should not detect plain strings as encrypted."""
        assert is_encrypted("Hello, World!") is False

    def test_json_not_detected(self):
        """Should not detect JSON as encrypted."""
        assert is_encrypted('{"key": "value"}') is False

    def test_none_not_detected(self):
        """Should handle None gracefully."""
        assert is_encrypted(None) is False

    def test_empty_string_not_detected(self):
        """Should handle empty strings."""
        assert is_encrypted("") is False


class TestSensitiveFields:
    """Tests for field-level encryption."""

    @pytest.fixture
    def test_key(self):
        return generate_encryption_key()

    @pytest.fixture(autouse=True)
    def setup_env(self, test_key):
        """Set up encryption key in environment."""
        os.environ["NATLANGCHAIN_ENCRYPTION_KEY"] = test_key
        yield
        del os.environ["NATLANGCHAIN_ENCRYPTION_KEY"]

    def test_encrypt_sensitive_field(self):
        """Should encrypt fields matching sensitive patterns."""
        metadata = {
            "wallet_address": "0x1234567890abcdef",
            "author": "Alice",
            "timestamp": "2024-01-01"
        }

        encrypted = encrypt_sensitive_fields(metadata)

        assert is_encrypted(encrypted["wallet_address"])
        assert encrypted["author"] == "Alice"  # Not sensitive
        assert encrypted["timestamp"] == "2024-01-01"

    def test_decrypt_sensitive_field(self):
        """Should decrypt encrypted fields."""
        metadata = {
            "wallet_address": "0x1234567890abcdef",
            "author": "Alice"
        }

        encrypted = encrypt_sensitive_fields(metadata)
        decrypted = decrypt_sensitive_fields(encrypted)

        assert decrypted["wallet_address"] == "0x1234567890abcdef"
        assert decrypted["author"] == "Alice"

    def test_encrypt_payment_amount(self):
        """Should encrypt payment_amount field."""
        metadata = {
            "payment_amount": 50000,
            "currency": "USD"
        }

        encrypted = encrypt_sensitive_fields(metadata)

        assert is_encrypted(encrypted["payment_amount"])
        assert encrypted["currency"] == "USD"

    def test_encrypt_contract_terms(self):
        """Should encrypt contract_terms field."""
        metadata = {
            "contract_terms": {"price": 100, "delivery": "30 days"},
            "type": "purchase"
        }

        encrypted = encrypt_sensitive_fields(metadata)

        assert is_encrypted(encrypted["contract_terms"])
        assert encrypted["type"] == "purchase"

    def test_empty_metadata(self):
        """Should handle empty metadata."""
        result = encrypt_sensitive_fields({})
        assert result == {}

    def test_none_metadata(self):
        """Should handle None metadata."""
        result = encrypt_sensitive_fields(None)
        assert result is None

    def test_custom_sensitive_fields(self):
        """Should encrypt custom sensitive fields."""
        metadata = {
            "custom_secret": "very secret",
            "normal_field": "normal"
        }

        encrypted = encrypt_sensitive_fields(
            metadata,
            additional_fields={"custom_secret"}
        )

        assert is_encrypted(encrypted["custom_secret"])
        assert encrypted["normal_field"] == "normal"


class TestChainDataEncryption:
    """Tests for full chain data encryption."""

    @pytest.fixture
    def test_key(self):
        return generate_encryption_key()

    @pytest.fixture
    def sample_chain_data(self):
        return {
            "chain": [
                {
                    "index": 0,
                    "hash": "abc123",
                    "entries": [
                        {
                            "content": "Genesis block",
                            "author": "system",
                            "metadata": {"type": "genesis"}
                        }
                    ]
                },
                {
                    "index": 1,
                    "hash": "def456",
                    "entries": [
                        {
                            "content": "I offer to sell 100 shares",
                            "author": "Alice",
                            "metadata": {
                                "is_contract": True,
                                "payment_amount": 5000
                            }
                        }
                    ]
                }
            ],
            "pending_entries": []
        }

    def test_encrypt_chain_data(self, test_key, sample_chain_data):
        """Should encrypt entire chain data."""
        encrypted = encrypt_chain_data(sample_chain_data, key=test_key)

        assert is_encrypted(encrypted)
        assert "Genesis block" not in encrypted
        assert "Alice" not in encrypted

    def test_decrypt_chain_data(self, test_key, sample_chain_data):
        """Should decrypt chain data back to original."""
        encrypted = encrypt_chain_data(sample_chain_data, key=test_key)
        decrypted = decrypt_chain_data(encrypted, key=test_key)

        assert decrypted == sample_chain_data

    def test_chain_data_integrity(self, test_key, sample_chain_data):
        """Decrypted chain should match original exactly."""
        encrypted = encrypt_chain_data(sample_chain_data, key=test_key)
        decrypted = decrypt_chain_data(encrypted, key=test_key)

        # Verify structure
        assert len(decrypted["chain"]) == 2
        assert decrypted["chain"][0]["index"] == 0
        assert decrypted["chain"][1]["entries"][0]["author"] == "Alice"


class TestHashingUtilities:
    """Tests for one-way hashing utilities."""

    def test_hash_value(self):
        """Should create a salted hash."""
        value = "0x1234567890abcdef"
        hashed = hash_sensitive_value(value)

        assert hashed.startswith("HASH:1:")
        assert value not in hashed

    def test_verify_correct_value(self):
        """Should verify correct value against hash."""
        value = "secret123"
        hashed = hash_sensitive_value(value)

        assert verify_hashed_value(value, hashed) is True

    def test_verify_wrong_value(self):
        """Should reject incorrect value."""
        value = "secret123"
        hashed = hash_sensitive_value(value)

        assert verify_hashed_value("wrong_value", hashed) is False

    def test_hash_with_custom_salt(self):
        """Should use custom salt when provided."""
        value = "test_value"
        salt = "custom_salt_123"

        hashed1 = hash_sensitive_value(value, salt=salt)
        hashed2 = hash_sensitive_value(value, salt=salt)

        # Same salt should produce same hash
        assert hashed1 == hashed2

    def test_unique_hashes_different_salts(self):
        """Different salts should produce different hashes."""
        value = "test_value"

        hashed1 = hash_sensitive_value(value)
        hashed2 = hash_sensitive_value(value)

        # Random salts should produce different hashes
        assert hashed1 != hashed2


class TestErrorHandling:
    """Tests for error handling."""

    def test_encrypt_without_key(self):
        """Should raise error when no key is available."""
        # Ensure no key in environment
        if "NATLANGCHAIN_ENCRYPTION_KEY" in os.environ:
            del os.environ["NATLANGCHAIN_ENCRYPTION_KEY"]

        with pytest.raises(EncryptionError):
            encrypt_data("test")

    def test_decrypt_invalid_format(self):
        """Should raise error for invalid format."""
        key = generate_encryption_key()

        with pytest.raises(EncryptionError):
            decrypt_data("not_encrypted_data", key=key)

    def test_decrypt_truncated_data(self):
        """Should raise error for truncated data."""
        key = generate_encryption_key()
        encrypted = encrypt_data("test", key=key)
        truncated = encrypted[:20]  # Too short

        with pytest.raises(EncryptionError):
            decrypt_data(truncated, key=key)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
