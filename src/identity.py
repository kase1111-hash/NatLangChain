"""
NatLangChain - Cryptographic Agent Identity Module

Provides Ed25519 keypair generation, entry signing, and signature verification
for tamper-proof provenance on blockchain entries.

SECURITY (Audit 1.3): Addresses the "Cryptographic Agent Identity" gap identified
in the Agentic Security Audit. Ensures:
- Every agent gets a unique Ed25519 keypair
- All blockchain entries are signed by their author
- Signatures are verified on read to detect tampering
- Author identity is cryptographically proven, not self-asserted

Usage:
    # Generate a new identity
    identity = AgentIdentity.generate("alice")
    identity.save("/path/to/keystore/alice.key", passphrase="secret")

    # Load an existing identity
    identity = AgentIdentity.load("/path/to/keystore/alice.key", passphrase="secret")

    # Sign an entry dict
    signature = identity.sign_entry(entry_dict)

    # Verify a signature
    is_valid = AgentIdentity.verify_entry(entry_dict, signature, identity.public_key_bytes)
"""

import base64
import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Environment variables for identity configuration
IDENTITY_KEYSTORE_ENV = "NATLANGCHAIN_IDENTITY_KEYSTORE"
IDENTITY_PASSPHRASE_ENV = "NATLANGCHAIN_IDENTITY_PASSPHRASE"
IDENTITY_ENABLED_ENV = "NATLANGCHAIN_IDENTITY_ENABLED"
IDENTITY_REQUIRE_SIGNATURES_ENV = "NATLANGCHAIN_REQUIRE_SIGNATURES"

# Fields included in the signing payload (order matters for determinism)
SIGNED_FIELDS = ("content", "author", "intent", "timestamp")


def _is_identity_enabled() -> bool:
    """Check if identity signing is enabled via environment variable."""
    return os.getenv(IDENTITY_ENABLED_ENV, "false").lower() == "true"


def _require_signatures() -> bool:
    """Check if signature verification is required (reject unsigned entries)."""
    return os.getenv(IDENTITY_REQUIRE_SIGNATURES_ENV, "false").lower() == "true"


def _canonical_entry_payload(entry_dict: dict[str, Any]) -> bytes:
    """
    Create a canonical byte representation of an entry for signing/verification.

    Only includes the immutable content fields (not validation status, which
    changes after signing). Uses sorted JSON for deterministic serialization.

    Args:
        entry_dict: Entry dictionary with at least content, author, intent, timestamp

    Returns:
        Canonical bytes suitable for signing
    """
    payload = {}
    for field in SIGNED_FIELDS:
        value = entry_dict.get(field)
        if value is not None:
            payload[field] = value

    # Deterministic JSON serialization
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return canonical.encode("utf-8")


class AgentIdentity:
    """
    Cryptographic identity for a NatLangChain agent using Ed25519.

    Ed25519 chosen for:
    - Fast signing and verification (important for blockchain throughput)
    - Small key and signature sizes (32-byte keys, 64-byte signatures)
    - Deterministic signatures (same input always produces same signature)
    - No need for random number generator during signing (reduces attack surface)
    """

    def __init__(self, agent_name: str, private_key: Any, public_key: Any):
        """
        Initialize an agent identity.

        Args:
            agent_name: Human-readable agent identifier
            private_key: Ed25519 private key object
            public_key: Ed25519 public key object
        """
        self.agent_name = agent_name
        self._private_key = private_key
        self._public_key = public_key

    @classmethod
    def generate(cls, agent_name: str) -> "AgentIdentity":
        """
        Generate a new Ed25519 keypair for an agent.

        Args:
            agent_name: Human-readable agent identifier

        Returns:
            New AgentIdentity with fresh keypair
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        logger.info("Generated new identity for agent '%s'", agent_name)
        return cls(agent_name=agent_name, private_key=private_key, public_key=public_key)

    @property
    def public_key_bytes(self) -> bytes:
        """Get the raw public key bytes (32 bytes)."""
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )

        return self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    @property
    def public_key_b64(self) -> str:
        """Get the public key as a base64-encoded string."""
        return base64.b64encode(self.public_key_bytes).decode("ascii")

    @property
    def fingerprint(self) -> str:
        """
        Get a short fingerprint of the public key for display.

        Returns:
            First 16 hex chars of the SHA-256 hash of the public key
        """
        key_hash = hashlib.sha256(self.public_key_bytes).hexdigest()
        return key_hash[:16]

    def sign_entry(self, entry_dict: dict[str, Any]) -> str:
        """
        Sign a blockchain entry.

        Creates a deterministic signature over the canonical entry payload.

        Args:
            entry_dict: Entry dictionary with content, author, intent, timestamp

        Returns:
            Base64-encoded Ed25519 signature
        """
        payload = _canonical_entry_payload(entry_dict)
        signature = self._private_key.sign(payload)
        return base64.b64encode(signature).decode("ascii")

    @staticmethod
    def verify_entry(
        entry_dict: dict[str, Any],
        signature_b64: str,
        public_key_bytes: bytes,
    ) -> bool:
        """
        Verify a signature on a blockchain entry.

        Args:
            entry_dict: Entry dictionary with content, author, intent, timestamp
            signature_b64: Base64-encoded Ed25519 signature
            public_key_bytes: Raw public key bytes (32 bytes)

        Returns:
            True if signature is valid, False otherwise
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )

        try:
            signature = base64.b64decode(signature_b64)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            payload = _canonical_entry_payload(entry_dict)
            public_key.verify(signature, payload)
            return True
        except Exception as e:
            logger.warning("Signature verification failed: %s", e)
            return False

    @staticmethod
    def verify_entry_b64(
        entry_dict: dict[str, Any],
        signature_b64: str,
        public_key_b64: str,
    ) -> bool:
        """
        Verify a signature using base64-encoded public key.

        Convenience wrapper for verify_entry when keys are in base64 format
        (as stored in entry metadata).

        Args:
            entry_dict: Entry dictionary
            signature_b64: Base64-encoded signature
            public_key_b64: Base64-encoded public key

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            public_key_bytes = base64.b64decode(public_key_b64)
            return AgentIdentity.verify_entry(entry_dict, signature_b64, public_key_bytes)
        except Exception as e:
            logger.warning("Signature verification failed (b64 decode): %s", e)
            return False

    def save(self, path: str, passphrase: str | None = None) -> None:
        """
        Save the identity keypair to an encrypted file.

        Args:
            path: File path for the keystore
            passphrase: Optional passphrase for encryption (recommended)
        """
        from cryptography.hazmat.primitives.serialization import (
            BestAvailableEncryption,
            Encoding,
            NoEncryption,
            PrivateFormat,
        )

        if passphrase:
            encryption = BestAvailableEncryption(passphrase.encode("utf-8"))
        else:
            encryption = NoEncryption()

        private_bytes = self._private_key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, encryption
        )

        # Write with restrictive permissions (owner read/write only)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, private_bytes)
        finally:
            os.close(fd)

        logger.info("Saved identity for '%s' to %s", self.agent_name, path)

    @classmethod
    def load(cls, path: str, agent_name: str = "", passphrase: str | None = None) -> "AgentIdentity":
        """
        Load an identity keypair from an encrypted file.

        Args:
            path: File path for the keystore
            agent_name: Human-readable agent name (defaults to filename)
            passphrase: Passphrase for decryption (if encrypted)

        Returns:
            Loaded AgentIdentity
        """
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        with open(path, "rb") as f:
            private_bytes = f.read()

        pw = passphrase.encode("utf-8") if passphrase else None
        private_key = load_pem_private_key(private_bytes, password=pw)
        public_key = private_key.public_key()

        if not agent_name:
            agent_name = os.path.splitext(os.path.basename(path))[0]

        logger.info("Loaded identity for '%s' from %s", agent_name, path)
        return cls(agent_name=agent_name, private_key=private_key, public_key=public_key)

    @classmethod
    def from_environment(cls) -> "AgentIdentity | None":
        """
        Load identity from environment-configured keystore.

        Reads NATLANGCHAIN_IDENTITY_KEYSTORE for the key file path and
        NATLANGCHAIN_IDENTITY_PASSPHRASE for the decryption passphrase.

        Returns:
            AgentIdentity if configured, None otherwise
        """
        if not _is_identity_enabled():
            return None

        keystore_path = os.getenv(IDENTITY_KEYSTORE_ENV)
        if not keystore_path:
            logger.warning(
                "%s is enabled but %s is not set",
                IDENTITY_ENABLED_ENV, IDENTITY_KEYSTORE_ENV,
            )
            return None

        if not os.path.exists(keystore_path):
            logger.warning("Identity keystore not found at %s", keystore_path)
            return None

        passphrase = os.getenv(IDENTITY_PASSPHRASE_ENV)
        try:
            return cls.load(keystore_path, passphrase=passphrase)
        except Exception as e:
            logger.error("Failed to load identity from %s: %s", keystore_path, e)
            return None


def sign_entry_dict(entry_dict: dict[str, Any], identity: AgentIdentity) -> dict[str, Any]:
    """
    Add cryptographic signature to an entry dictionary.

    Adds 'signature' and 'public_key' fields to the entry's metadata.

    Args:
        entry_dict: Entry dictionary to sign
        identity: The signing agent's identity

    Returns:
        Entry dictionary with signature metadata added
    """
    signature = identity.sign_entry(entry_dict)

    entry_dict.setdefault("metadata", {})
    entry_dict["metadata"]["signature"] = signature
    entry_dict["metadata"]["public_key"] = identity.public_key_b64
    entry_dict["metadata"]["signer_fingerprint"] = identity.fingerprint

    return entry_dict


def verify_entry_signature(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Verify the cryptographic signature on an entry dictionary.

    Args:
        entry_dict: Entry dictionary with signature in metadata

    Returns:
        Dict with verification result:
        {
            "signed": bool,       # Whether entry has a signature
            "verified": bool,     # Whether signature is valid (False if unsigned)
            "signer": str | None, # Signer fingerprint if signed
            "error": str | None,  # Error message if verification failed
        }
    """
    metadata = entry_dict.get("metadata", {})
    signature = metadata.get("signature")
    public_key_b64 = metadata.get("public_key")

    if not signature or not public_key_b64:
        return {
            "signed": False,
            "verified": False,
            "signer": None,
            "error": None,
        }

    is_valid = AgentIdentity.verify_entry_b64(entry_dict, signature, public_key_b64)

    return {
        "signed": True,
        "verified": is_valid,
        "signer": metadata.get("signer_fingerprint"),
        "error": None if is_valid else "Signature verification failed",
    }
