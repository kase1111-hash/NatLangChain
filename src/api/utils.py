"""
Shared utilities for NatLangChain API.

This module contains common utilities, decorators, and helpers
used across all API blueprints.
"""

import ipaddress
import os
import secrets
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

from flask import jsonify, request

# ============================================================
# Security Configuration
# ============================================================

# API Key for authentication (set via environment or generate secure default)
API_KEY = os.getenv("NATLANGCHAIN_API_KEY", None)
# SECURITY: Default to requiring authentication for production safety
API_KEY_REQUIRED = os.getenv("NATLANGCHAIN_REQUIRE_AUTH", "true").lower() == "true"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
rate_limit_store: dict[str, dict[str, Any]] = {}

# Bounded parameters - max values for iteration parameters
MAX_VALIDATORS = 10
MAX_ORACLES = 10
MAX_RESULTS = 100
MAX_OFFSET = 100000  # Maximum offset to prevent memory exhaustion


# ============================================================
# Validation Utilities
# ============================================================

def validate_pagination_params(
    limit: int,
    offset: int = 0,
    max_limit: int = MAX_RESULTS,
    max_offset: int = MAX_OFFSET
) -> tuple:
    """
    Validate and bound pagination parameters to prevent DoS attacks.

    Args:
        limit: Requested limit
        offset: Requested offset
        max_limit: Maximum allowed limit
        max_offset: Maximum allowed offset

    Returns:
        Tuple of (bounded_limit, bounded_offset)
    """
    # Bound limit to maximum allowed
    bounded_limit = max(1, min(int(limit) if limit else max_limit, max_limit))

    # Bound offset to maximum allowed and ensure non-negative
    bounded_offset = max(0, min(int(offset) if offset else 0, max_offset))

    return bounded_limit, bounded_offset


def validate_json_schema(
    data: dict[str, Any],
    required_fields: dict[str, type],
    optional_fields: dict[str, type] | None = None,
    max_lengths: dict[str, int] | None = None
) -> tuple:
    """
    Validate JSON payload against a simple schema.

    SECURITY: Provides type and structure validation for API payloads
    to prevent type confusion and injection attacks.

    Args:
        data: The JSON data to validate
        required_fields: Dict mapping field names to expected types
        optional_fields: Dict mapping optional field names to expected types
        max_lengths: Dict mapping field names to maximum string lengths

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    # Check required fields
    for field_name, expected_type in required_fields.items():
        if field_name not in data:
            return False, f"Missing required field: {field_name}"
        if not isinstance(data[field_name], expected_type):
            return False, f"Field '{field_name}' must be of type {expected_type.__name__}"

    # Check optional fields if present
    if optional_fields:
        for field_name, expected_type in optional_fields.items():
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], expected_type):
                    return False, f"Field '{field_name}' must be of type {expected_type.__name__}"

    # Check string lengths
    if max_lengths:
        for field_name, max_len in max_lengths.items():
            if field_name in data and isinstance(data[field_name], str):
                if len(data[field_name]) > max_len:
                    return False, f"Field '{field_name}' exceeds maximum length of {max_len}"

    return True, None


# ============================================================
# SSRF Protection Utilities
# ============================================================

# SECURITY: Block internal/private networks and sensitive hosts
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("127.0.0.0/8"),       # Localhost
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local (AWS metadata)
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # Documentation (TEST-NET-1)
    ipaddress.ip_network("198.51.100.0/24"),   # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),    # Documentation (TEST-NET-3)
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6 private ranges
    ipaddress.ip_network("::1/128"),           # Localhost
    ipaddress.ip_network("fc00::/7"),          # Unique local address
    ipaddress.ip_network("fe80::/10"),         # Link-local
    ipaddress.ip_network("ff00::/8"),          # Multicast
]

# SECURITY: Block known cloud metadata service hosts
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",       # GCP
    "metadata.google.com",            # GCP
    "metadata.gcp",                   # GCP
    "instance-data.ec2.internal",     # AWS
    "metadata.azure.com",             # Azure
    "management.azure.com",           # Azure
    "kubernetes.default",             # Kubernetes
    "kubernetes.default.svc",         # Kubernetes
    "kubernetes.default.svc.cluster.local",  # Kubernetes
}


def validate_url_for_ssrf(url: str) -> tuple[bool, str | None]:
    """
    Validate a URL to prevent SSRF attacks.

    SECURITY: This function prevents Server-Side Request Forgery by:
    - Blocking requests to internal/private IP ranges
    - Blocking requests to localhost and loopback addresses
    - Blocking requests to cloud metadata services
    - Restricting allowed URL schemes

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_safe, error_message)
        - (True, None) if URL is safe to request
        - (False, "error message") if URL should be blocked
    """
    import socket
    from urllib.parse import urlparse

    if not url or not isinstance(url, str):
        return False, "URL is required"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        return False, f"URL scheme must be http or https, got: {parsed.scheme}"

    # Get hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must contain a hostname"

    # Check blocked hostnames
    if hostname.lower() in BLOCKED_HOSTS:
        return False, f"Access to host '{hostname}' is blocked for security reasons"

    # Also block any hostname containing "metadata" or "internal"
    hostname_lower = hostname.lower()
    if "metadata" in hostname_lower or "internal" in hostname_lower:
        return False, f"Access to host '{hostname}' is blocked for security reasons"

    # Resolve hostname to IP and check against blocked ranges
    try:
        # Get all IPs for the hostname
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                # Check against blocked ranges
                for blocked_range in BLOCKED_IP_RANGES:
                    if ip in blocked_range:
                        return False, f"Access to internal IP addresses is blocked for security reasons"
            except ValueError:
                continue  # Skip invalid IPs
    except socket.gaierror as e:
        # DNS resolution failed - could be malicious, block it
        return False, f"DNS resolution failed for host '{hostname}': {e}"
    except Exception as e:
        return False, f"Failed to validate host '{hostname}': {e}"

    return True, None


def is_safe_peer_endpoint(endpoint: str) -> tuple[bool, str | None]:
    """
    Validate a P2P peer endpoint URL for safety.

    This is a wrapper around validate_url_for_ssrf specifically for
    P2P peer connections.

    Args:
        endpoint: The peer endpoint URL

    Returns:
        Tuple of (is_safe, error_message)
    """
    return validate_url_for_ssrf(endpoint)


# ============================================================
# IP and Rate Limiting Utilities
# ============================================================

def is_valid_ip(ip_str: str) -> bool:
    """
    Validate that a string is a valid IPv4 or IPv6 address.

    Args:
        ip_str: String to validate as IP address

    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except (ValueError, AttributeError):
        return False


# SECURITY: Trusted proxy configuration
# Only trust X-Forwarded-For headers from these IPs
# Set via environment variable as comma-separated list
# If not set, X-Forwarded-For is NOT trusted (secure default)
TRUSTED_PROXIES = set(
    ip.strip() for ip in os.getenv("NATLANGCHAIN_TRUSTED_PROXIES", "").split(",")
    if ip.strip()
)


def get_client_ip() -> str:
    """
    Get client IP address, considering proxies.

    SECURITY FIXES:
    - Only trusts X-Forwarded-For when request comes from a trusted proxy
    - Validates IP format to prevent rate limit bypass attacks
    - Uses rightmost untrusted IP (harder to spoof than leftmost)

    Configure trusted proxies via NATLANGCHAIN_TRUSTED_PROXIES env var.
    """
    remote_addr = request.remote_addr or 'unknown'

    # Only trust X-Forwarded-For if the request came from a trusted proxy
    if TRUSTED_PROXIES and remote_addr in TRUSTED_PROXIES:
        xff = request.headers.get('X-Forwarded-For')
        if xff:
            # Parse all IPs in the chain
            parts = [p.strip() for p in xff.split(',')]

            # Use rightmost IP that is NOT a trusted proxy
            for ip in reversed(parts):
                if ip and is_valid_ip(ip) and ip not in TRUSTED_PROXIES:
                    return ip

            # If all IPs are trusted proxies, use the leftmost
            for ip in parts:
                if ip and is_valid_ip(ip):
                    return ip

    # If no trusted proxies configured or request not from proxy,
    # use direct connection address (secure default)
    return remote_addr


def check_rate_limit() -> dict[str, Any] | None:
    """
    Check if client has exceeded rate limit.

    Returns:
        None if within limit, error dict if exceeded
    """
    client_ip = get_client_ip()
    current_time = time.time()

    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = {
            "count": 0,
            "window_start": current_time
        }

    client_data = rate_limit_store[client_ip]

    # Reset window if expired
    if current_time - client_data["window_start"] > RATE_LIMIT_WINDOW:
        client_data["count"] = 0
        client_data["window_start"] = current_time

    # Check limit
    if client_data["count"] >= RATE_LIMIT_REQUESTS:
        return {
            "error": "Rate limit exceeded",
            "retry_after": int(RATE_LIMIT_WINDOW - (current_time - client_data["window_start"]))
        }

    client_data["count"] += 1
    return None


# ============================================================
# Authentication Decorator
# ============================================================

def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not API_KEY_REQUIRED:
            return f(*args, **kwargs)

        # Check for API key in header
        provided_key = request.headers.get('X-API-Key')

        if not provided_key:
            return jsonify({
                "error": "API key required",
                "hint": "Provide API key in X-API-Key header"
            }), 401

        if not API_KEY:
            return jsonify({
                "error": "Server API key not configured",
                "hint": "Set NATLANGCHAIN_API_KEY environment variable"
            }), 503

        if not secrets.compare_digest(provided_key, API_KEY):
            return jsonify({"error": "Invalid API key"}), 403

        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# Manager Registry
# ============================================================

@dataclass
class ManagerRegistry:
    """
    Centralized registry for all optional managers and validators.

    This provides a clean interface for accessing optional features
    and makes it easy to check feature availability.
    """
    # LLM-based validators
    llm_validator: Any = None
    hybrid_validator: Any = None
    drift_detector: Any = None
    dialectic_validator: Any = None
    multi_model_consensus: Any = None

    # Search and semantic features
    search_engine: Any = None
    temporal_fixity: Any = None
    semantic_oracle: Any = None
    circuit_breaker: Any = None

    # Contract management
    contract_parser: Any = None
    contract_matcher: Any = None

    # Dispute and governance
    dispute_manager: Any = None
    escalation_fork_manager: Any = None

    # Economic features
    observance_burn_manager: Any = None
    anti_harassment_manager: Any = None
    treasury: Any = None

    # Authentication and privacy
    fido2_manager: Any = None
    zk_privacy_manager: Any = None

    # Advanced features
    negotiation_engine: Any = None
    market_pricing: Any = None
    mobile_deployment: Any = None

    # P2P network
    p2p_network: Any = None

    def is_llm_enabled(self) -> bool:
        """Check if LLM-based features are available."""
        return self.llm_validator is not None

    def is_dispute_enabled(self) -> bool:
        """Check if dispute management is available."""
        return self.dispute_manager is not None

    def is_economic_enabled(self) -> bool:
        """Check if economic features (burn, treasury) are available."""
        return self.treasury is not None

    def is_p2p_enabled(self) -> bool:
        """Check if P2P network is available."""
        return self.p2p_network is not None


# Global manager registry instance
managers = ManagerRegistry()
