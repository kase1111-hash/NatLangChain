"""
SSRF Protection Utilities for NatLangChain.

This module provides Server-Side Request Forgery (SSRF) protection
without any Flask dependencies, making it suitable for testing
and use in non-web contexts.

SECURITY: These utilities prevent attacks by:
- Blocking requests to internal/private IP ranges
- Blocking requests to localhost and loopback addresses
- Blocking requests to cloud metadata services
- Restricting allowed URL schemes
"""

import ipaddress
import os
import socket
from urllib.parse import urlparse

# ============================================================
# SSRF Protection Configuration
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


# ============================================================
# IP Validation Utilities
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


def is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address is in a private/blocked range.

    Args:
        ip_str: IP address string to check

    Returns:
        True if the IP is private/blocked, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        for blocked_range in BLOCKED_IP_RANGES:
            if ip in blocked_range:
                return True
        return False
    except (ValueError, AttributeError):
        return False


# ============================================================
# SSRF Validation Functions
# ============================================================

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
                        return False, "Access to internal IP addresses is blocked for security reasons"
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
# Trusted Proxy Configuration
# ============================================================

# SECURITY: Trusted proxy configuration
# Only trust X-Forwarded-For headers from these IPs
# Set via environment variable as comma-separated list
# If not set, X-Forwarded-For is NOT trusted (secure default)
TRUSTED_PROXIES = set(
    ip.strip() for ip in os.getenv("NATLANGCHAIN_TRUSTED_PROXIES", "").split(",")
    if ip.strip()
)


def get_client_ip_from_headers(
    remote_addr: str,
    xff_header: str | None,
    trusted_proxies: set[str] | None = None
) -> str:
    """
    Get client IP address from request headers, considering proxies.

    SECURITY FIXES:
    - Only trusts X-Forwarded-For when request comes from a trusted proxy
    - Validates IP format to prevent rate limit bypass attacks
    - Uses rightmost untrusted IP (harder to spoof than leftmost)

    Args:
        remote_addr: The direct connection IP address
        xff_header: The X-Forwarded-For header value (or None)
        trusted_proxies: Set of trusted proxy IPs (defaults to TRUSTED_PROXIES)

    Returns:
        The determined client IP address
    """
    if trusted_proxies is None:
        trusted_proxies = TRUSTED_PROXIES

    if not remote_addr:
        return 'unknown'

    # Only trust X-Forwarded-For if the request came from a trusted proxy
    if trusted_proxies and remote_addr in trusted_proxies:
        if xff_header:
            # Parse all IPs in the chain
            parts = [p.strip() for p in xff_header.split(',')]

            # Use rightmost IP that is NOT a trusted proxy
            for ip in reversed(parts):
                if ip and is_valid_ip(ip) and ip not in trusted_proxies:
                    return ip

            # If all IPs are trusted proxies, use the leftmost
            for ip in parts:
                if ip and is_valid_ip(ip):
                    return ip

    # If no trusted proxies configured or request not from proxy,
    # use direct connection address (secure default)
    return remote_addr
