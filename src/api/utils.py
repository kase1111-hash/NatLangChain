"""
Shared utilities for NatLangChain API.

This module contains common utilities, decorators, and helpers
used across all API blueprints.
"""

import os
import secrets
import time
from dataclasses import dataclass
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

# Pagination configuration
DEFAULT_PAGE_LIMIT = int(os.getenv("NATLANGCHAIN_DEFAULT_PAGE_LIMIT", "100"))
MAX_PAGE_LIMIT = int(os.getenv("NATLANGCHAIN_MAX_PAGE_LIMIT", "1000"))
DEFAULT_HISTORY_LIMIT = int(os.getenv("NATLANGCHAIN_DEFAULT_HISTORY_LIMIT", "50"))


# ============================================================
# Validation Utilities
# ============================================================


def validate_pagination_params(
    limit: int, offset: int = 0, max_limit: int = MAX_RESULTS, max_offset: int = MAX_OFFSET
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
    max_lengths: dict[str, int] | None = None,
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
# Standardized Error Responses
# ============================================================


def error_response(
    error: str,
    status_code: int = 400,
    details: str | None = None,
    field: str | None = None,
) -> tuple:
    """
    Create a standardized error response.

    This provides consistent error formatting across all API endpoints.
    Never include internal implementation details in error responses.

    Args:
        error: Brief error description (user-facing)
        status_code: HTTP status code
        details: Additional context (optional, must be safe to expose)
        field: The field that caused the error (optional)

    Returns:
        Tuple of (Flask response dict, status_code)
    """
    response = {"error": error}

    if details:
        response["details"] = details

    if field:
        response["field"] = field

    return jsonify(response), status_code


def validation_error(field: str, message: str) -> tuple:
    """Create a standardized validation error response."""
    return error_response(
        error="Validation failed",
        status_code=400,
        details=message,
        field=field,
    )


def not_found_error(resource: str) -> tuple:
    """Create a standardized not found error response."""
    return error_response(
        error=f"{resource} not found",
        status_code=404,
    )


def internal_error() -> tuple:
    """
    Create a standardized internal error response.
    Never expose internal details in this response.
    """
    return error_response(
        error="Internal error occurred",
        status_code=500,
    )


def service_unavailable_error(service: str, reason: str | None = None) -> tuple:
    """Create a standardized service unavailable error response."""
    return error_response(
        error=f"{service} not available",
        status_code=503,
        details=reason,
    )


# ============================================================
# SSRF Protection Utilities
# ============================================================
# Import from standalone module (no Flask dependency for testing)
from .ssrf_protection import (
    TRUSTED_PROXIES,
    get_client_ip_from_headers,
)

# ============================================================
# IP and Rate Limiting Utilities
# ============================================================
# Note: is_valid_ip, TRUSTED_PROXIES, and get_client_ip_from_headers
# are imported from ssrf_protection module above


def get_client_ip() -> str:
    """
    Get client IP address, considering proxies.

    SECURITY FIXES:
    - Only trusts X-Forwarded-For when request comes from a trusted proxy
    - Validates IP format to prevent rate limit bypass attacks
    - Uses rightmost untrusted IP (harder to spoof than leftmost)

    Configure trusted proxies via NATLANGCHAIN_TRUSTED_PROXIES env var.
    """
    # Use the standalone implementation with Flask request context
    return get_client_ip_from_headers(
        remote_addr=request.remote_addr or "unknown",
        xff_header=request.headers.get("X-Forwarded-For"),
        trusted_proxies=TRUSTED_PROXIES,
    )


def check_rate_limit() -> dict[str, Any] | None:
    """
    Check if client has exceeded rate limit.

    Returns:
        None if within limit, error dict if exceeded
    """
    client_ip = get_client_ip()
    current_time = time.time()

    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = {"count": 0, "window_start": current_time}

    client_data = rate_limit_store[client_ip]

    # Reset window if expired
    if current_time - client_data["window_start"] > RATE_LIMIT_WINDOW:
        client_data["count"] = 0
        client_data["window_start"] = current_time

    # Check limit
    if client_data["count"] >= RATE_LIMIT_REQUESTS:
        return {
            "error": "Rate limit exceeded",
            "retry_after": int(RATE_LIMIT_WINDOW - (current_time - client_data["window_start"])),
        }

    client_data["count"] += 1
    return None


# ============================================================
# Rate Limiting for LLM Endpoints
# ============================================================

# Stricter rate limits for expensive LLM-backed operations
LLM_RATE_LIMIT_REQUESTS = int(os.getenv("LLM_RATE_LIMIT_REQUESTS", "10"))
LLM_RATE_LIMIT_WINDOW = int(os.getenv("LLM_RATE_LIMIT_WINDOW", "60"))  # seconds
llm_rate_limit_store: dict[str, dict[str, Any]] = {}


def check_llm_rate_limit() -> dict[str, Any] | None:
    """
    Check if client has exceeded LLM rate limit.
    Uses stricter limits than standard endpoints due to API costs.

    Returns:
        None if within limit, error dict if exceeded
    """
    client_ip = get_client_ip()
    current_time = time.time()

    if client_ip not in llm_rate_limit_store:
        llm_rate_limit_store[client_ip] = {"count": 0, "window_start": current_time}

    client_data = llm_rate_limit_store[client_ip]

    # Reset window if expired
    if current_time - client_data["window_start"] > LLM_RATE_LIMIT_WINDOW:
        client_data["count"] = 0
        client_data["window_start"] = current_time

    # Check limit
    if client_data["count"] >= LLM_RATE_LIMIT_REQUESTS:
        return {
            "error": "LLM rate limit exceeded",
            "message": "Too many requests to LLM-backed endpoints",
            "retry_after": int(LLM_RATE_LIMIT_WINDOW - (current_time - client_data["window_start"])),
        }

    client_data["count"] += 1
    return None


def rate_limit_llm(f):
    """
    Decorator to apply stricter rate limiting to LLM-backed endpoints.
    These endpoints are expensive (API costs) and should be rate-limited
    more aggressively than standard endpoints.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        rate_limit_error = check_llm_rate_limit()
        if rate_limit_error:
            return jsonify(rate_limit_error), 429
        return f(*args, **kwargs)

    return decorated_function


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
        provided_key = request.headers.get("X-API-Key")

        if not provided_key:
            return jsonify(
                {"error": "API key required", "hint": "Provide API key in X-API-Key header"}
            ), 401

        if not API_KEY:
            return jsonify(
                {
                    "error": "Server API key not configured",
                    "hint": "Set NATLANGCHAIN_API_KEY environment variable",
                }
            ), 503

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

    # Advanced features
    negotiation_engine: Any = None

    def is_llm_enabled(self) -> bool:
        """Check if LLM-based features are available."""
        return self.llm_validator is not None

    def is_dispute_enabled(self) -> bool:
        """Check if dispute management is available."""
        return self.dispute_manager is not None


# Global manager registry instance
managers = ManagerRegistry()
