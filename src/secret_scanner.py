"""
NatLangChain - Outbound Secret Scanner

Scans outbound API responses and LLM outputs for accidentally leaked credentials.
Detects known API key formats, tokens, private keys, and high-entropy strings
that could indicate credential leakage.

SECURITY (Audit 2.3): Addresses the "Outbound Secret Scanning" gap identified
in the Agentic Security Audit. Ensures:
- All API response bodies are scanned before being sent to clients
- Known credential patterns (OpenAI, Anthropic, AWS, etc.) are detected
- Private key material in PEM format is caught
- High-entropy strings that may be secrets are flagged
- Detected secrets are redacted and incidents are logged

Configuration:
    NATLANGCHAIN_SECRET_SCANNING=true     Enable scanning (default: true)
    NATLANGCHAIN_SECRET_SCAN_MODE=redact  Mode: "redact" (replace) or "block" (reject response)
"""

import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# Environment configuration
SECRET_SCANNING_ENV = "NATLANGCHAIN_SECRET_SCANNING"
SECRET_SCAN_MODE_ENV = "NATLANGCHAIN_SECRET_SCAN_MODE"

# Redaction placeholder
REDACTED = "[SECRET_REDACTED]"


def _is_scanning_enabled() -> bool:
    """Check if outbound secret scanning is enabled."""
    return os.getenv(SECRET_SCANNING_ENV, "true").lower() != "false"


def _scan_mode() -> str:
    """Get scan mode: 'redact' (default) replaces secrets, 'block' rejects the response."""
    return os.getenv(SECRET_SCAN_MODE_ENV, "redact").lower()


# ============================================================
# Known Credential Patterns
# ============================================================

# Each pattern is a tuple of (name, compiled_regex)
# Patterns are ordered from most specific to most general
CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Anthropic API keys
    ("anthropic_api_key", re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}")),

    # OpenAI API keys (old and new format)
    ("openai_api_key", re.compile(r"sk-[a-zA-Z0-9]{20,}")),

    # AWS Access Key IDs
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),

    # AWS Secret Access Keys (40 chars, base64-like)
    ("aws_secret_key", re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])")),

    # Google API keys
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),

    # GitHub tokens (classic and fine-grained)
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),

    # Generic Bearer tokens in content
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9_-]{20,}")),

    # PEM private keys
    ("private_key_pem", re.compile(
        r"-----BEGIN\s+(RSA |EC |ED25519 |DSA )?PRIVATE KEY-----"
        r"[\s\S]*?"
        r"-----END\s+(RSA |EC |ED25519 |DSA )?PRIVATE KEY-----"
    )),

    # Generic hex secrets (64-char hex strings that look like SHA-256 hashes used as keys)
    ("hex_secret_64", re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{64}(?![a-fA-F0-9])")),

    # Base64-encoded secrets (44+ chars, common for 32-byte keys)
    ("base64_secret", re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{43}=(?![A-Za-z0-9+/=])")),
]

# Fields in JSON responses that are expected to contain hashes (not secrets)
# These are excluded from hex_secret_64 and high-entropy detection
HASH_FIELDS = {
    "hash", "block_hash", "previous_hash", "entry_hash",
    "chain_id", "fingerprint", "signer_fingerprint", "nonce",
}


def _shannon_entropy(s: str) -> float:
    """
    Calculate Shannon entropy of a string.

    High entropy (> 4.5 for base64, > 3.5 for hex) may indicate secrets.

    Args:
        s: String to measure

    Returns:
        Entropy in bits per character
    """
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


class ScanResult:
    """Result of scanning a value for secrets."""

    def __init__(self):
        self.detections: list[dict[str, str]] = []

    @property
    def has_secrets(self) -> bool:
        return len(self.detections) > 0

    def add(self, pattern_name: str, matched_text: str, location: str = ""):
        self.detections.append({
            "pattern": pattern_name,
            "location": location,
            # Only log first/last 4 chars of matched text for audit trail
            "preview": f"{matched_text[:4]}...{matched_text[-4:]}" if len(matched_text) > 12 else "***",
        })


def scan_string(text: str, location: str = "") -> ScanResult:
    """
    Scan a string for known credential patterns.

    Args:
        text: String to scan
        location: Description of where the string came from (for logging)

    Returns:
        ScanResult with any detections
    """
    result = ScanResult()

    if not text or not isinstance(text, str):
        return result

    for pattern_name, pattern in CREDENTIAL_PATTERNS:
        for match in pattern.finditer(text):
            matched = match.group(0)

            # Skip short matches and known false positives
            if len(matched) < 16:
                continue

            # For hex/base64 patterns, check entropy to reduce false positives
            if pattern_name in ("hex_secret_64", "base64_secret", "aws_secret_key"):
                entropy = _shannon_entropy(matched)
                # Low entropy suggests it's not a secret (e.g., repeated chars)
                if entropy < 3.0:
                    continue

            result.add(pattern_name, matched, location)

    return result


def scan_dict(data: Any, path: str = "", depth: int = 0) -> ScanResult:
    """
    Recursively scan a dictionary/JSON structure for secrets.

    Skips known hash fields (block_hash, previous_hash, etc.) to avoid
    false positives on blockchain data.

    Args:
        data: Data structure to scan (dict, list, str, or other)
        path: Current path in the data structure (for location reporting)
        depth: Current recursion depth

    Returns:
        ScanResult with any detections
    """
    result = ScanResult()

    if depth > 15:
        return result

    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = key.lower()
            # Skip fields that are expected to contain hashes
            if key_lower in HASH_FIELDS:
                continue
            child_path = f"{path}.{key}" if path else key
            child_result = scan_dict(value, child_path, depth + 1)
            result.detections.extend(child_result.detections)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            child_path = f"{path}[{i}]"
            child_result = scan_dict(item, child_path, depth + 1)
            result.detections.extend(child_result.detections)

    elif isinstance(data, str) and len(data) > 15:
        string_result = scan_string(data, path)
        result.detections.extend(string_result.detections)

    return result


def redact_secrets_in_string(text: str) -> str:
    """
    Replace detected secrets in a string with redaction placeholders.

    Args:
        text: String potentially containing secrets

    Returns:
        String with secrets replaced by [SECRET_REDACTED]
    """
    if not text or not isinstance(text, str):
        return text

    for pattern_name, pattern in CREDENTIAL_PATTERNS:
        text = pattern.sub(REDACTED, text)

    return text


def redact_secrets_in_dict(data: Any, depth: int = 0) -> Any:
    """
    Recursively redact secrets in a dictionary/JSON structure.

    Args:
        data: Data structure to redact
        depth: Current recursion depth

    Returns:
        Data with secrets replaced by [SECRET_REDACTED]
    """
    if depth > 15:
        return data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in HASH_FIELDS:
                result[key] = value  # Preserve hash fields as-is
            else:
                result[key] = redact_secrets_in_dict(value, depth + 1)
        return result

    elif isinstance(data, list):
        return [redact_secrets_in_dict(item, depth + 1) for item in data]

    elif isinstance(data, str) and len(data) > 15:
        return redact_secrets_in_string(data)

    else:
        return data


def scan_response_body(body: bytes | str, content_type: str = "") -> ScanResult:
    """
    Scan an HTTP response body for secrets.

    Handles JSON and plain text responses.

    Args:
        body: Response body bytes or string
        content_type: Content-Type header value

    Returns:
        ScanResult with any detections
    """
    if not body:
        return ScanResult()

    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return ScanResult()  # Binary data, skip
    else:
        text = body

    # For JSON responses, parse and scan structurally
    if "json" in content_type.lower():
        import json
        try:
            data = json.loads(text)
            return scan_dict(data, "response")
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to string scan

    # For all responses, scan as string
    return scan_string(text, "response_body")
