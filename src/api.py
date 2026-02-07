"""
NatLangChain - REST API
API endpoints for Agent OS to interact with the blockchain
"""

import atexit
import json
import logging
import os
import secrets
import signal
import sys
import threading
import time
from functools import wraps
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from api.utils import managers

# Core imports (always required)
from blockchain import NatLangChain, NaturalLanguageEntry

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
        """Check if encryption is enabled (stub when encryption module unavailable)."""
        return False

    encrypt_chain_data = None
    decrypt_chain_data = None

    def encrypt_sensitive_fields(x, **kwargs):
        """Encrypt sensitive fields in data (passthrough stub when encryption unavailable)."""
        return x

    def decrypt_sensitive_fields(x, **kwargs):
        """Decrypt sensitive fields in data (passthrough stub when encryption unavailable)."""
        return x

    def is_encrypted(x):
        """Check if data is encrypted (stub returns False when encryption unavailable)."""
        return False

    EncryptionError = Exception
    ENCRYPTION_KEY_ENV = "NATLANGCHAIN_ENCRYPTION_KEY"

# Optional imports - these require heavy dependencies (PyTorch, Anthropic, etc.)
# The API will work without them, just with reduced functionality

try:
    from validator import HybridValidator, ProofOfUnderstanding
except ImportError:
    ProofOfUnderstanding = None
    HybridValidator = None


try:
    from semantic_search import SemanticSearchEngine
except ImportError:
    SemanticSearchEngine = None


try:
    from contract_parser import ContractParser
except ImportError:
    ContractParser = None

try:
    from contract_matcher import ContractMatcher
except ImportError:
    ContractMatcher = None


# SSRF protection utilities
try:
    from api.utils import is_safe_peer_endpoint, validate_url_for_ssrf

    SSRF_PROTECTION_AVAILABLE = True
except ImportError:
    SSRF_PROTECTION_AVAILABLE = False

    def is_safe_peer_endpoint(endpoint):
        """Check if a peer endpoint is safe from SSRF (stub allows all when unavailable)."""
        return True, None

    def validate_url_for_ssrf(url):
        """Validate a URL for SSRF vulnerabilities (stub allows all when unavailable)."""
        return True, None


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ============================================================
# Security Configuration
# ============================================================

# SECURITY: Request size limit reduced from 16MB to 2MB to prevent storage attacks
# Natural language entries shouldn't need more than 2MB
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# API Key for authentication (set via environment or generate secure default)
API_KEY = os.getenv("NATLANGCHAIN_API_KEY", None)
# SECURITY: Default to requiring authentication for production safety
# Set NATLANGCHAIN_REQUIRE_AUTH=false explicitly to disable for development
API_KEY_REQUIRED = os.getenv("NATLANGCHAIN_REQUIRE_AUTH", "true").lower() == "true"

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
rate_limit_store: dict[str, dict[str, Any]] = {}  # Legacy in-memory store

# Distributed rate limiter (Redis-backed when available)
try:
    from rate_limiter import get_rate_limiter

    DISTRIBUTED_RATE_LIMIT_AVAILABLE = True
except ImportError:
    DISTRIBUTED_RATE_LIMIT_AVAILABLE = False

# Bounded parameters - max values for iteration parameters
MAX_VALIDATORS = 10
MAX_RESULTS = 100
MAX_OFFSET = 100000  # Maximum offset to prevent memory exhaustion

# =============================================================================
# Graceful Shutdown Configuration
# =============================================================================
# Tracks server shutdown state for graceful termination
_shutdown_event = threading.Event()
_in_flight_requests = 0
_request_lock = threading.Lock()
_shutdown_timeout = int(os.getenv("SHUTDOWN_TIMEOUT", "30"))  # seconds

# Configure module logger
logger = logging.getLogger(__name__)


def _track_request_start():
    """Increment in-flight request counter."""
    global _in_flight_requests
    with _request_lock:
        _in_flight_requests += 1


def _track_request_end():
    """Decrement in-flight request counter."""
    global _in_flight_requests
    with _request_lock:
        _in_flight_requests -= 1


def _graceful_shutdown(signum: int, _frame) -> None:
    """
    Handle SIGTERM/SIGINT for graceful server shutdown.

    This handler:
    1. Signals the server to stop accepting new requests
    2. Waits for in-flight requests to complete (with timeout)
    3. Flushes pending entries to storage
    4. Exits cleanly

    Args:
        signum: Signal number received
        _frame: Current stack frame (unused)
    """
    signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
    logger.info(f"Received {signal_name} - initiating graceful shutdown...")
    print(f"\n[SHUTDOWN] Received {signal_name} - initiating graceful shutdown...")

    # Signal that we're shutting down
    _shutdown_event.set()

    # Wait for in-flight requests to complete
    waited = 0
    while waited < _shutdown_timeout:
        with _request_lock:
            current_requests = _in_flight_requests

        if current_requests == 0:
            logger.info("All in-flight requests completed")
            print("[SHUTDOWN] All in-flight requests completed")
            break

        logger.info(
            f"Waiting for {current_requests} in-flight request(s)... ({waited}s/{_shutdown_timeout}s)"
        )
        print(
            f"[SHUTDOWN] Waiting for {current_requests} in-flight request(s)... ({waited}s/{_shutdown_timeout}s)"
        )
        time.sleep(1)
        waited += 1

    if waited >= _shutdown_timeout:
        with _request_lock:
            remaining = _in_flight_requests
        logger.warning(f"Shutdown timeout reached with {remaining} request(s) still in flight")
        print(f"[SHUTDOWN] Timeout reached with {remaining} request(s) still in flight")

    # Flush pending data to storage
    try:
        logger.info("Saving blockchain state...")
        print("[SHUTDOWN] Saving blockchain state...")
        save_chain()
        logger.info("Blockchain state saved successfully")
        print("[SHUTDOWN] Blockchain state saved successfully")
    except Exception as e:
        logger.error(f"Failed to save blockchain state: {e}")
        print(f"[SHUTDOWN] WARNING: Failed to save blockchain state: {e}")

    logger.info("Graceful shutdown complete")
    print("[SHUTDOWN] Graceful shutdown complete")
    sys.exit(0)


def _register_shutdown_handlers():
    """Register signal handlers for graceful shutdown."""
    # Only register if not already in shutdown
    if not _shutdown_event.is_set():
        signal.signal(signal.SIGTERM, _graceful_shutdown)
        signal.signal(signal.SIGINT, _graceful_shutdown)
        # Register atexit handler for cleanup in case of unexpected exit
        atexit.register(_cleanup_on_exit)


def _cleanup_on_exit():
    """Cleanup handler called on process exit."""
    if not _shutdown_event.is_set():
        try:
            save_chain()
        except Exception:
            pass  # Best effort on exit


def is_shutting_down() -> bool:
    """Check if the server is in shutdown state."""
    return _shutdown_event.is_set()


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
    for field, expected_type in required_fields.items():
        if field not in data:
            return False, f"Missing required field: {field}"
        if not isinstance(data[field], expected_type):
            return False, f"Field '{field}' must be of type {expected_type.__name__}"

    # Check optional fields if present
    if optional_fields:
        for field, expected_type in optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    return False, f"Field '{field}' must be of type {expected_type.__name__}"

    # Check string lengths
    if max_lengths:
        for field, max_len in max_lengths.items():
            if field in data and isinstance(data[field], str):
                if len(data[field]) > max_len:
                    return False, f"Field '{field}' exceeds maximum length of {max_len}"

    return True, None


def is_valid_ip(ip_str: str) -> bool:
    """
    Validate that a string is a valid IPv4 or IPv6 address.

    Args:
        ip_str: String to validate as IP address

    Returns:
        True if valid IP address, False otherwise
    """
    import ipaddress

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
    ip.strip() for ip in os.getenv("NATLANGCHAIN_TRUSTED_PROXIES", "").split(",") if ip.strip()
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
    remote_addr = request.remote_addr or "unknown"

    # Only trust X-Forwarded-For if the request came from a trusted proxy
    if TRUSTED_PROXIES and remote_addr in TRUSTED_PROXIES:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            # Parse all IPs in the chain
            # Format: "client, proxy1, proxy2, ..."
            parts = [p.strip() for p in xff.split(",")]

            # Use rightmost IP that is NOT a trusted proxy
            # This is the IP that the last trusted proxy saw
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

    Uses distributed rate limiting (Redis) when available,
    falls back to in-memory rate limiting otherwise.

    Returns:
        None if within limit, error dict if exceeded
    """
    client_ip = get_client_ip()

    # Use distributed rate limiter if available
    if DISTRIBUTED_RATE_LIMIT_AVAILABLE:
        try:
            limiter = get_rate_limiter()
            result = limiter.check_limit(client_ip)

            if result.exceeded:
                return {
                    "error": "Rate limit exceeded",
                    "retry_after": result.retry_after,
                    "limit": result.limit,
                    "remaining": result.remaining,
                }
            return None
        except Exception as e:
            logger.warning(f"Distributed rate limiter failed, using fallback: {e}")
            # Fall through to legacy implementation

    # Legacy in-memory rate limiting
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


@app.before_request
def before_request_security():
    """Apply security checks before each request."""
    # Skip shutdown check for health endpoints (needed for K8s probes)
    if request.endpoint in ("health_check", "health_live", "health_ready", "api_health"):
        return None

    # Reject new requests during shutdown
    if is_shutting_down():
        response = jsonify(
            {"error": "Service is shutting down", "status": "unavailable", "retry_after": 30}
        )
        response.status_code = 503
        response.headers["Retry-After"] = "30"
        return response

    # Track this request for graceful shutdown
    _track_request_start()

    # Rate limiting
    rate_error = check_rate_limit()
    if rate_error:
        _track_request_end()  # Don't count rate-limited requests
        response = jsonify(rate_error)
        response.status_code = 429
        response.headers["Retry-After"] = str(rate_error.get("retry_after", 60))
        return response

    return None


@app.teardown_request
def teardown_request_tracking(exception=None):
    """Track request completion for graceful shutdown."""
    # Only decrement if we incremented (non-health endpoints, non-shutdown)
    if request.endpoint not in ("health_check", "health_live", "health_ready", "api_health"):
        if not is_shutting_down():
            _track_request_end()


@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"

    # SECURITY: Content Security Policy - restrictive defaults for API
    # This is an API server, so we restrict all content loading
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "  # Block everything by default
        "frame-ancestors 'none'; "  # Prevent embedding in frames
        "form-action 'none'; "  # Prevent form submissions
        "base-uri 'none'"  # Prevent base tag injection
    )

    # SECURITY: Strict Transport Security (only effective over HTTPS)
    # Tells browsers to always use HTTPS for this domain
    # max-age=31536000 = 1 year, includeSubDomains for all subdomains
    if os.getenv("NATLANGCHAIN_ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # SECURITY: CORS headers - restrictive by default
    # Set CORS_ALLOWED_ORIGINS to comma-separated list of allowed origins
    # Use "*" only for development (explicitly set, not default)
    allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")

    if allowed_origins_str == "*":
        # Explicitly allowed wildcard (development only)
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif allowed_origins_str:
        # Check if request origin matches any allowed origin
        request_origin = request.headers.get("Origin", "")
        allowed_list = [o.strip() for o in allowed_origins_str.split(",")]
        if request_origin in allowed_list:
            response.headers["Access-Control-Allow-Origin"] = request_origin
            response.headers["Vary"] = "Origin"
        # If origin not in list, don't set CORS header (request will be blocked)
    # If CORS_ALLOWED_ORIGINS not set, no CORS header = same-origin only

    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key, Authorization"

    return response


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle request too large error."""
    return jsonify(
        {
            "error": "Request too large",
            "max_size_mb": app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024),
        }
    ), 413


@app.errorhandler(400)
def bad_request(error):
    """
    Handle bad request errors including type coercion failures.

    SECURITY: Returns generic error message to prevent information disclosure
    about internal type expectations.
    """
    return jsonify({"error": "Bad request", "message": "Invalid request format or parameters"}), 400


@app.errorhandler(ValueError)
def handle_value_error(error):
    """
    Handle ValueError exceptions from type coercion.

    SECURITY: Catches errors from Flask's request.args.get(type=int) etc.
    Returns generic message to prevent leaking internal type information.
    """
    return jsonify(
        {
            "error": "Invalid parameter value",
            "message": "One or more parameters have invalid values",
        }
    ), 400


# Initialize blockchain and validator
blockchain = NatLangChain()


# ManagerRegistry and managers are imported from api.utils
# Backwards compatibility aliases (to avoid breaking existing code)
llm_validator = None
hybrid_validator = None
search_engine = None
contract_parser = None
contract_matcher = None

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")


def init_validators():
    """
    Initialize validators and advanced features if API key is available.

    Updates both the global ManagerRegistry and individual global variables
    for backwards compatibility.
    """
    global managers
    global llm_validator, hybrid_validator, search_engine
    global contract_parser, contract_matcher

    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Initialize semantic search (doesn't require API key)
    try:
        search_engine = SemanticSearchEngine()
        managers.search_engine = search_engine
        print("Semantic search engine initialized")
    except Exception as e:
        print(f"Warning: Could not initialize semantic search: {e}")

    # Initialize LLM-based features if API key available
    if api_key and api_key != "your_api_key_here":
        try:
            # LLM-based validators
            llm_validator = ProofOfUnderstanding(api_key)
            hybrid_validator = HybridValidator(llm_validator)

            # Contract management
            contract_parser = ContractParser(api_key)
            contract_matcher = ContractMatcher(api_key)

            # Update the centralized registry
            managers.llm_validator = llm_validator
            managers.hybrid_validator = hybrid_validator
            managers.contract_parser = contract_parser
            managers.contract_matcher = contract_matcher

            print("LLM-based features initialized (validators, contracts)")
        except Exception as e:
            print(f"Warning: Could not initialize LLM features: {e}")
            print("API will operate without LLM validation")


# SECURITY: Lock for file operations to prevent TOCTOU race conditions
# Used by load_chain and save_chain to ensure atomic read/write operations
_chain_file_lock = threading.Lock()


def load_chain():
    """
    Load blockchain from file if it exists, with automatic decryption support.

    If the file contains encrypted data (starts with ENC:1:), it will be
    automatically decrypted using the configured encryption key.

    Thread-safe: Uses _chain_file_lock to prevent race conditions.

    Handles specific error cases:
    - FileNotFoundError: File doesn't exist (normal for fresh start)
    - PermissionError: File exists but cannot be read
    - json.JSONDecodeError: File is corrupted or malformed
    - KeyError/TypeError: File data is missing required fields
    - EncryptionError: Encrypted data but decryption failed
    """
    global blockchain

    # SECURITY: Acquire lock to prevent race conditions during file operations
    with _chain_file_lock:
        if not os.path.exists(CHAIN_DATA_FILE):
            print("Chain data file not found - starting with fresh blockchain")
            return

        try:
            with open(CHAIN_DATA_FILE) as f:
                file_content = f.read()

            # Check if data is encrypted
            if ENCRYPTION_AVAILABLE and is_encrypted(file_content):
                if not is_encryption_enabled():
                    # SECURITY: Don't expose env var name in logs
                    print("ERROR: Chain data is encrypted but encryption key is not configured")
                    print("Please set the encryption key environment variable")
                    print("Starting with fresh blockchain (encrypted data preserved)")
                    return

                try:
                    data = decrypt_chain_data(file_content)
                    blockchain = NatLangChain.from_dict(data)
                    print(f"Loaded encrypted blockchain with {len(blockchain.chain)} blocks")
                    return
                except EncryptionError:
                    # SECURITY: Don't expose decryption error details
                    print("Failed to decrypt chain data - check encryption key")
                    print("Starting with fresh blockchain (encrypted data preserved)")
                    return

            # Not encrypted - load as JSON
            data = json.loads(file_content)
            blockchain = NatLangChain.from_dict(data)
            print(f"Loaded blockchain with {len(blockchain.chain)} blocks")

            # Warn if encryption is enabled but data is not encrypted
            if ENCRYPTION_AVAILABLE and is_encryption_enabled():
                print("WARNING: Existing chain data is not encrypted.")
                print("It will be encrypted on next save.")

        except PermissionError:
            # SECURITY: Don't expose permission error details
            print("Permission denied reading chain data - starting with fresh blockchain")
        except json.JSONDecodeError:
            # SECURITY: Don't expose JSON parsing details (line/column numbers)
            print("Chain data file is corrupted - starting with fresh blockchain")
            # Preserve corrupted file for recovery
            corrupted_path = f"{CHAIN_DATA_FILE}.corrupted.{int(time.time())}"
            try:
                os.rename(CHAIN_DATA_FILE, corrupted_path)
                print("Corrupted file preserved for recovery")
            except OSError:
                pass  # Silently fail rename - don't expose filesystem errors
        except (KeyError, TypeError):
            # SECURITY: Don't expose data structure details
            print("Chain data format invalid - starting with fresh blockchain")
        except Exception:
            # SECURITY: Don't expose unexpected error details
            print("Error loading chain data - starting with fresh blockchain")


def save_chain():
    """
    Save blockchain to file with optional encryption.

    If encryption is enabled (NATLANGCHAIN_ENCRYPTION_KEY is set),
    the chain data will be encrypted using AES-256-GCM before saving.

    Thread-safe: Uses _chain_file_lock to prevent TOCTOU race conditions
    between encryption check and file write.

    Handles specific error cases:
    - PermissionError: Cannot write to file/directory
    - OSError: Disk full or other I/O errors
    - TypeError: Data cannot be serialized to JSON
    - EncryptionError: Encryption failed
    """
    # SECURITY: Acquire lock to prevent TOCTOU race conditions
    # This ensures encryption state doesn't change between check and write
    with _chain_file_lock:
        try:
            chain_data = blockchain.to_dict()

            # Encrypt if enabled (check is now atomic with write)
            if ENCRYPTION_AVAILABLE and is_encryption_enabled():
                try:
                    encrypted_data = encrypt_chain_data(chain_data)
                    # Write encrypted data to file
                    temp_file = f"{CHAIN_DATA_FILE}.tmp"
                    with open(temp_file, "w") as f:
                        f.write(encrypted_data)
                    os.replace(temp_file, CHAIN_DATA_FILE)
                    print("Chain data saved with encryption")
                    return
                except EncryptionError:
                    # SECURITY: Don't expose encryption error details
                    print("Encryption failed - falling back to unencrypted save")
                    # Fall through to unencrypted save

            # Write to temporary file first for atomic operation (unencrypted)
            temp_file = f"{CHAIN_DATA_FILE}.tmp"
            with open(temp_file, "w") as f:
                json.dump(chain_data, f, indent=2)
            # Atomic rename for data integrity
            os.replace(temp_file, CHAIN_DATA_FILE)
        except PermissionError:
            # SECURITY: Don't expose permission error details or file paths
            print("WARNING: Permission denied - blockchain state may not be persisted")
        except OSError:
            # SECURITY: Don't expose OS error details
            print("WARNING: I/O error - blockchain state may not be persisted")
        except TypeError:
            # SECURITY: Don't expose serialization error details
            print("WARNING: Serialization error - blockchain state contains invalid data")
        except Exception:
            # SECURITY: Don't expose unexpected error details
            print("WARNING: Error saving chain data")


def create_entry_with_encryption(
    content: str, author: str, intent: str, metadata: dict[str, Any] | None = None
) -> NaturalLanguageEntry:
    """
    Create a NaturalLanguageEntry with sensitive metadata fields encrypted.

    This helper ensures that sensitive data in metadata (like financial terms,
    wallet addresses, personal info) is encrypted before being stored in the
    blockchain.

    Args:
        content: The entry content
        author: The entry author
        intent: The entry intent
        metadata: Optional metadata dictionary

    Returns:
        NaturalLanguageEntry with encrypted sensitive fields
    """
    processed_metadata = metadata or {}

    # Encrypt sensitive fields if encryption is enabled
    if ENCRYPTION_AVAILABLE and is_encryption_enabled() and processed_metadata:
        try:
            processed_metadata = encrypt_sensitive_fields(processed_metadata)
        except Exception as e:
            print(f"Warning: Failed to encrypt sensitive metadata fields: {e}")
            # Continue with unencrypted metadata

    return NaturalLanguageEntry(
        content=content, author=author, intent=intent, metadata=processed_metadata
    )


def decrypt_entry_metadata(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Decrypt sensitive fields in an entry's metadata for API responses.

    Args:
        entry_dict: Entry dictionary (from entry.to_dict())

    Returns:
        Entry dictionary with decrypted metadata
    """
    if not ENCRYPTION_AVAILABLE:
        return entry_dict

    result = entry_dict.copy()
    if result.get("metadata"):
        try:
            result["metadata"] = decrypt_sensitive_fields(result["metadata"])
        except Exception as e:
            print(f"Warning: Failed to decrypt some metadata fields: {e}")

    return result


# Initialize on startup
init_validators()
load_chain()


@app.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": "NatLangChain API",
            "llm_validation_available": llm_validator is not None,
            "blocks": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
        }
    )


@app.route("/health/live", methods=["GET"])
def health_live():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the process is alive and responding.
    This should be a simple check that doesn't depend on external services.
    """
    return jsonify(
        {"status": "alive", "service": "NatLangChain API", "timestamp": time.time()}
    ), 200


@app.route("/health/ready", methods=["GET"])
def health_ready():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Checks:
    - Blockchain is loaded and valid
    - Storage is accessible (can write/read)
    - Not in shutdown state

    Returns 503 if not ready.
    """
    checks = {
        "blockchain_loaded": False,
        "storage_accessible": False,
        "not_shutting_down": False,
        "chain_valid": False,
    }
    errors = []

    # Check if we're shutting down
    if is_shutting_down():
        errors.append("Service is shutting down")
    else:
        checks["not_shutting_down"] = True

    # Check blockchain is loaded
    try:
        if blockchain is not None and len(blockchain.chain) >= 1:
            checks["blockchain_loaded"] = True
        else:
            errors.append("Blockchain not loaded or empty")
    except Exception as e:
        errors.append(f"Blockchain check failed: {e!s}")

    # Check chain validity
    try:
        if blockchain.validate_chain():
            checks["chain_valid"] = True
        else:
            errors.append("Chain validation failed")
    except Exception as e:
        errors.append(f"Chain validation error: {e!s}")

    # Check storage accessibility
    try:
        # Verify we can access the chain data file or storage
        if os.path.exists(CHAIN_DATA_FILE):
            # Check file is readable
            with open(CHAIN_DATA_FILE) as f:
                f.read(1)  # Just read 1 byte to verify access
            checks["storage_accessible"] = True
        else:
            # No file yet is OK for fresh start - check directory is writable
            chain_dir = os.path.dirname(CHAIN_DATA_FILE) or "."
            if os.access(chain_dir, os.W_OK):
                checks["storage_accessible"] = True
            else:
                errors.append("Storage directory not writable")
    except PermissionError:
        errors.append("Storage file not readable")
    except Exception as e:
        errors.append(f"Storage check failed: {e!s}")

    # Determine overall status
    all_passed = all(checks.values())

    response = {
        "status": "ready" if all_passed else "not_ready",
        "checks": checks,
        "timestamp": time.time(),
    }

    if errors:
        response["errors"] = errors

    return jsonify(response), 200 if all_passed else 503


@app.route("/chain", methods=["GET"])
def get_chain():
    """
    Get the entire blockchain.

    Returns:
        Full blockchain data
    """
    return jsonify(
        {
            "length": len(blockchain.chain),
            "chain": blockchain.to_dict(),
            "valid": blockchain.validate_chain(),
        }
    )


@app.route("/chain/narrative", methods=["GET"])
def get_narrative():
    """
    Get the full narrative history as human-readable text.

    This is a key feature: the entire ledger as readable prose.

    Returns:
        Complete narrative of all entries
    """
    narrative = blockchain.get_full_narrative()
    return narrative, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/entry", methods=["POST"])
@require_api_key
def add_entry():
    """
    Add a new natural language entry to the blockchain.

    Request body:
    {
        "content": "Natural language description of the transaction/event",
        "author": "identifier of the creator",
        "intent": "brief summary of purpose",
        "metadata": {} (optional),
        "validate": true/false (optional, default true),
        "auto_mine": true/false (optional, default false)
    }

    Returns:
        Entry status and validation results
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # SECURITY: Schema validation for entry payload
    ENTRY_MAX_LENGTHS = {
        "content": 50000,  # 50KB max for content
        "author": 500,  # 500 chars for author
        "intent": 2000,  # 2KB for intent
    }

    is_valid, error_msg = validate_json_schema(
        data,
        required_fields={"content": str, "author": str, "intent": str},
        optional_fields={
            "metadata": dict,
            "validate": bool,
            "auto_mine": bool,
            "validation_mode": str,
            "multi_validator": bool,
        },
        max_lengths=ENTRY_MAX_LENGTHS,
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Extract validated fields
    content = data["content"]
    author = data["author"]
    intent = data["intent"]

    # Validate metadata size if provided
    MAX_METADATA_LEN = 10000  # 10KB for metadata
    metadata = data.get("metadata", {})
    if metadata:
        try:
            metadata_str = json.dumps(metadata)
            if len(metadata_str) > MAX_METADATA_LEN:
                return jsonify(
                    {
                        "error": "Metadata too large",
                        "max_length": MAX_METADATA_LEN,
                        "received_length": len(metadata_str),
                    }
                ), 400
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid metadata format"}), 400

    # Fields validated, continue with entry creation

    # Create entry with encrypted sensitive metadata
    entry = create_entry_with_encryption(
        content=content, author=author, intent=intent, metadata=data.get("metadata", {})
    )

    # Validate if requested
    validate = data.get("validate", True)
    validation_result = None
    validation_mode = data.get("validation_mode", "standard")  # "standard", "multi", or "dialectic"

    if validate:
        if hybrid_validator:
            # Use standard or multi-validator mode
            validation_result = hybrid_validator.validate(
                content=content,
                intent=intent,
                author=author,
                use_llm=True,
                multi_validator=(validation_mode == "multi" or data.get("multi_validator", False)),
            )
            validation_result["validation_mode"] = validation_mode
        else:
            # No validators available - accept without LLM validation
            validation_result = {
                "validation_mode": "none",
                "overall_decision": "ACCEPTED",
                "note": "No LLM validator configured - entry accepted without semantic validation",
            }

        # Update entry with validation results
        decision = validation_result.get("overall_decision", "PENDING")
        entry.validation_status = decision.lower()

        if validation_result.get("llm_validation"):
            llm_val = validation_result["llm_validation"]
            if "validations" in llm_val:
                # Multi-validator consensus
                entry.validation_paraphrases = llm_val.get("paraphrases", [])
            elif "validation" in llm_val:
                # Single validator
                entry.validation_paraphrases = [llm_val["validation"].get("paraphrase", "")]

    # Add to blockchain
    result = blockchain.add_entry(entry)

    # Auto-mine if requested
    auto_mine = data.get("auto_mine", False)
    mined_block = None
    if auto_mine:
        mined_block = blockchain.mine_pending_entries()
        save_chain()

    response = {"status": "success", "entry": result, "validation": validation_result}

    if mined_block:
        response["mined_block"] = {"index": mined_block.index, "hash": mined_block.hash}

    return jsonify(response), 201


@app.route("/entry/validate", methods=["POST"])
@require_api_key
def validate_entry():
    """
    Validate an entry without adding it to the blockchain.

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description",
        "multi_validator": true/false (optional)
    }

    Returns:
        Validation results
    """
    if not hybrid_validator:
        return jsonify(
            {"error": "LLM validation not available", "reason": "ANTHROPIC_API_KEY not configured"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # SECURITY: Schema validation for validate payload
    is_valid, error_msg = validate_json_schema(
        data,
        required_fields={"content": str, "author": str, "intent": str},
        optional_fields={"multi_validator": bool},
        max_lengths={"content": 50000, "author": 500, "intent": 2000},
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify(
            {"error": "Missing required fields", "required": ["content", "author", "intent"]}
        ), 400

    validation_result = hybrid_validator.validate(
        content=content,
        intent=intent,
        author=author,
        use_llm=True,
        multi_validator=data.get("multi_validator", False),
    )

    return jsonify(validation_result)


@app.route("/mine", methods=["POST"])
@require_api_key
def mine_block():
    """
    Mine pending entries into a new block.

    Automatically finds and proposes matches for contract entries before mining.

    Request body (optional):
    {
        "difficulty": 2 (number of leading zeros in hash),
        "miner_id": "miner identifier" (optional, for contract matching)
    }

    Returns:
        Newly mined block with any contract proposals
    """
    if not blockchain.pending_entries:
        return jsonify({"error": "No pending entries to mine"}), 400

    data = request.get_json() or {}
    difficulty = data.get("difficulty", 2)
    miner_id = data.get("miner_id", "miner")

    # Find contract matches if matcher is available
    proposals = []
    if contract_matcher:
        try:
            proposals = contract_matcher.find_matches(
                blockchain, blockchain.pending_entries, miner_id
            )

            # Add proposals to pending entries
            for proposal in proposals:
                blockchain.add_entry(proposal)

        except Exception as e:
            print(f"Contract matching failed: {e}")

    # Mine the block
    mined_block = blockchain.mine_pending_entries(difficulty=difficulty)
    save_chain()

    return jsonify(
        {
            "status": "success",
            "message": "Block mined successfully",
            "block": mined_block.to_dict(),
            "contract_proposals": len(proposals),
            "proposals": [p.to_dict() for p in proposals] if proposals else [],
        }
    )


@app.route("/block/<int:index>", methods=["GET"])
def get_block(index: int):
    """
    Get a specific block by index.

    Args:
        index: Block index

    Returns:
        Block data
    """
    if index < 0 or index >= len(blockchain.chain):
        return jsonify(
            {"error": "Block not found", "valid_range": f"0-{len(blockchain.chain) - 1}"}
        ), 404

    block = blockchain.chain[index]
    return jsonify(block.to_dict())


@app.route("/block/latest", methods=["GET"])
def get_latest_block():
    """
    Get the latest (most recent) block in the chain.

    Returns:
        Latest block data including block index, hash, timestamp, and entries.

    Notes:
        A properly initialized chain should always have at least the genesis block.
        An empty chain indicates initialization failure.
    """
    # Check if blockchain or chain is not properly initialized
    if blockchain is None or not hasattr(blockchain, "chain"):
        return jsonify(
            {
                "error": "Blockchain not initialized",
                "message": "The blockchain instance is not properly configured",
                "hint": "Restart the server or check initialization logs",
            }
        ), 503

    # Check for empty chain (should have at least genesis block)
    if not blockchain.chain or len(blockchain.chain) == 0:
        return jsonify(
            {
                "error": "Chain is empty",
                "message": "No blocks found in the chain. A genesis block should exist.",
                "hint": "The chain may not have been properly initialized. Try mining a block first.",
                "expected_minimum": 1,
            }
        ), 404

    block = blockchain.chain[-1]

    # Safely convert block to dict
    try:
        block_data = block.to_dict()
        block_data["_meta"] = {
            "is_genesis": block.index == 0,
            "chain_length": len(blockchain.chain),
        }
        return jsonify(block_data)
    except Exception as e:
        return jsonify(
            {
                "error": "Failed to serialize block",
                "message": str(e),
                "block_index": getattr(block, "index", "unknown"),
            }
        ), 500


@app.route("/entries/author/<author>", methods=["GET"])
def get_entries_by_author(author: str):
    """
    Get all entries by a specific author.

    Args:
        author: Author identifier

    Returns:
        List of entries by the author
    """
    entries = blockchain.get_entries_by_author(author)
    return jsonify({"author": author, "count": len(entries), "entries": entries})


@app.route("/entries/search", methods=["GET"])
def search_entries():
    """
    Search for entries by intent keyword.

    Query params:
        intent: Keyword to search for in intent field

    Returns:
        List of matching entries
    """
    intent_keyword = request.args.get("intent")

    if not intent_keyword:
        return jsonify({"error": "Missing 'intent' query parameter"}), 400

    # SECURITY: Validate intent query parameter
    MAX_SEARCH_LEN = 500  # Maximum search term length
    if len(intent_keyword) > MAX_SEARCH_LEN:
        return jsonify({"error": "Search term too long", "max_length": MAX_SEARCH_LEN}), 400

    # Strip whitespace and validate non-empty after strip
    intent_keyword = intent_keyword.strip()
    if not intent_keyword:
        return jsonify({"error": "Search term cannot be empty or whitespace only"}), 400

    entries = blockchain.get_entries_by_intent(intent_keyword)
    return jsonify({"keyword": intent_keyword, "count": len(entries), "entries": entries})


@app.route("/validate/chain", methods=["GET"])
def validate_blockchain():
    """
    Validate the entire blockchain for integrity.

    Returns:
        Validation status
    """
    is_valid = blockchain.validate_chain()
    return jsonify(
        {
            "valid": is_valid,
            "blocks": len(blockchain.chain),
            "message": "Blockchain is valid" if is_valid else "Blockchain integrity compromised",
        }
    )


@app.route("/pending", methods=["GET"])
def get_pending_entries():
    """
    Get all pending entries awaiting mining.

    Returns:
        List of pending entries
    """
    return jsonify(
        {
            "count": len(blockchain.pending_entries),
            "entries": [entry.to_dict() for entry in blockchain.pending_entries],
        }
    )


@app.route("/stats", methods=["GET"])
def get_stats():
    """
    Get blockchain statistics.

    Returns:
        Various statistics about the blockchain
    """
    return jsonify(_compute_stats())


def _compute_stats() -> dict:
    """Compute blockchain stats (extracted for caching)."""
    total_entries = sum(len(block.entries) for block in blockchain.chain)

    authors = set()
    validated_count = 0
    for block in blockchain.chain:
        for entry in block.entries:
            authors.add(entry.author)
            if entry.validation_status == "validated" or entry.validation_status == "valid":
                validated_count += 1

    # Count contracts
    total_contracts = 0
    open_contracts = 0
    matched_contracts = 0

    for block in blockchain.chain:
        for entry in block.entries:
            if entry.metadata.get("is_contract"):
                total_contracts += 1
                status = entry.metadata.get("status", "open")
                if status == "open":
                    open_contracts += 1
                elif status == "matched":
                    matched_contracts += 1

    return {
        "total_blocks": len(blockchain.chain),
        "total_entries": total_entries,
        "pending_entries": len(blockchain.pending_entries),
        "unique_authors": len(authors),
        "validated_entries": validated_count,
        "chain_valid": blockchain.validate_chain(),
        "latest_block_hash": blockchain.get_latest_block().hash,
        "llm_validation_enabled": llm_validator is not None,
        "semantic_search_enabled": search_engine is not None,
        "contract_features_enabled": contract_parser is not None and contract_matcher is not None,
        "total_contracts": total_contracts,
        "open_contracts": open_contracts,
        "matched_contracts": matched_contracts,
    }


# ========== Semantic Search Endpoints ==========


@app.route("/search/semantic", methods=["POST"])
def semantic_search():
    """
    Perform semantic search across blockchain entries.

    Request body:
    {
        "query": "natural language search query",
        "top_k": 5 (optional),
        "min_score": 0.0 (optional),
        "field": "content" | "intent" | "both" (optional)
    }

    Returns:
        List of semantically similar entries
    """
    if not search_engine:
        return jsonify(
            {"error": "Semantic search not available", "reason": "Search engine not initialized"}
        ), 503

    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Missing required field: query"}), 400

    query = data["query"]
    top_k = data.get("top_k", 5)
    min_score = data.get("min_score", 0.0)
    field = data.get("field", "content")

    try:
        if field in ["content", "intent", "both"]:
            results = search_engine.search_by_field(
                blockchain, query, field=field, top_k=top_k, min_score=min_score
            )
        else:
            results = search_engine.search(blockchain, query, top_k=top_k, min_score=min_score)

        return jsonify({"query": query, "field": field, "count": len(results), "results": results})

    except Exception as e:
        return jsonify({"error": "Search failed", "reason": str(e)}), 500


@app.route("/search/similar", methods=["POST"])
def find_similar():
    """
    Find entries similar to a given content.

    Request body:
    {
        "content": "content to find similar entries for",
        "top_k": 5 (optional),
        "exclude_exact": true (optional)
    }

    Returns:
        List of similar entries
    """
    if not search_engine:
        return jsonify({"error": "Semantic search not available"}), 503

    data = request.get_json()

    if not data or "content" not in data:
        return jsonify({"error": "Missing required field: content"}), 400

    content = data["content"]
    top_k = data.get("top_k", 5)
    exclude_exact = data.get("exclude_exact", True)

    try:
        results = search_engine.find_similar_entries(
            blockchain, content, top_k=top_k, exclude_exact=exclude_exact
        )

        return jsonify({"content": content, "count": len(results), "similar_entries": results})

    except Exception as e:
        return jsonify({"error": "Search failed", "reason": str(e)}), 500


# Live Contract Endpoints moved to api/contracts.py


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


def run_server():
    """Run the Flask development server with graceful shutdown support."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Register graceful shutdown handlers
    _register_shutdown_handlers()

    print(f"\n{'=' * 60}")
    print("NatLangChain API Server")
    print(f"{'=' * 60}")
    print(f"Listening on: http://{host}:{port}")
    print(f"Debug Mode: {'ENABLED (not for production!)' if debug else 'Disabled'}")
    print(f"Auth Required: {'Yes' if API_KEY_REQUIRED else 'No'}")
    print(f"Rate Limit: {RATE_LIMIT_REQUESTS} req/{RATE_LIMIT_WINDOW}s")
    print(f"LLM Validation: {'Enabled' if llm_validator else 'Disabled'}")
    print(f"Blockchain: {len(blockchain.chain)} blocks loaded")
    print(f"Graceful Shutdown: Enabled (timeout: {_shutdown_timeout}s)")
    print(f"{'=' * 60}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
