"""
NatLangChain - REST API
API endpoints for Agent OS to interact with the blockchain
"""

import atexit
import hashlib
import json
import logging
import os
import secrets
import signal
import sys
import threading
import time
from datetime import datetime
from functools import wraps
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from api.utils import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT

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
    from semantic_diff import SemanticDriftDetector
except ImportError:
    SemanticDriftDetector = None

try:
    from semantic_search import SemanticSearchEngine
except ImportError:
    SemanticSearchEngine = None

try:
    from dialectic_consensus import DialecticConsensus
except ImportError:
    DialecticConsensus = None

try:
    from contract_parser import ContractParser
except ImportError:
    ContractParser = None

try:
    from contract_matcher import ContractMatcher
except ImportError:
    ContractMatcher = None

try:
    from temporal_fixity import TemporalFixity
except ImportError:
    TemporalFixity = None

try:
    from dispute import DisputeManager
except ImportError:
    DisputeManager = None

try:
    from semantic_oracles import SemanticCircuitBreaker, SemanticOracle
except ImportError:
    SemanticOracle = None
    SemanticCircuitBreaker = None

try:
    from multi_model_consensus import MultiModelConsensus
except ImportError:
    MultiModelConsensus = None

try:
    from anti_harassment import AntiHarassmentManager, DisputeResolution, InitiationPath
except ImportError:
    AntiHarassmentManager = None
    InitiationPath = None
    DisputeResolution = None

try:
    from negotiation_engine import (
        AutomatedNegotiationEngine,
        ClauseType,
        NegotiationPhase,
        OfferType,
    )
except ImportError:
    AutomatedNegotiationEngine = None
    NegotiationPhase = None
    OfferType = None
    ClauseType = None

try:
    from ollama_chat_helper import OllamaChatHelper, get_chat_helper
except ImportError:
    OllamaChatHelper = None
    get_chat_helper = None

try:
    from p2p_network import (
        ConsensusMode,
        NodeRole,
        P2PNetwork,
        init_p2p_network,
    )

    P2P_AVAILABLE = True
except ImportError:
    P2P_AVAILABLE = False
    P2PNetwork = None
    init_p2p_network = None

    def get_p2p_network():
        """Get the P2P network instance (stub returns None when P2P unavailable)."""
        return None

    NodeRole = None
    ConsensusMode = None

# Adaptive query cache for mediator nodes
try:
    from adaptive_cache import (
        AdaptiveCache,
        CacheCategory,
        get_adaptive_cache,
        make_cache_key,
    )

    ADAPTIVE_CACHE_AVAILABLE = True
except ImportError:
    ADAPTIVE_CACHE_AVAILABLE = False
    AdaptiveCache = None
    CacheCategory = None
    get_adaptive_cache = None
    make_cache_key = None

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
MAX_ORACLES = 10
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
drift_detector = None
search_engine = None
dialectic_validator = None
contract_parser = None
contract_matcher = None
temporal_fixity = None
semantic_oracle = None
circuit_breaker = None
multi_model_consensus = None
dispute_manager = None
negotiation_engine = None

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")


def init_validators():
    """
    Initialize validators and advanced features if API key is available.

    Updates both the global ManagerRegistry and individual global variables
    for backwards compatibility.
    """
    global managers
    global llm_validator, hybrid_validator, drift_detector, search_engine
    global dialectic_validator, contract_parser, contract_matcher, temporal_fixity
    global semantic_oracle, circuit_breaker, multi_model_consensus, dispute_manager
    global negotiation_engine

    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Initialize temporal fixity (doesn't require API key)
    try:
        temporal_fixity = TemporalFixity()
        managers.temporal_fixity = temporal_fixity
        print("Temporal fixity (T0 preservation) initialized")
    except Exception as e:
        print(f"Warning: Could not initialize temporal fixity: {e}")

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
            drift_detector = SemanticDriftDetector(api_key)
            dialectic_validator = DialecticConsensus(api_key)
            multi_model_consensus = MultiModelConsensus(api_key)

            # Contract management
            contract_parser = ContractParser(api_key)
            contract_matcher = ContractMatcher(api_key)

            # Semantic features
            semantic_oracle = SemanticOracle(api_key)
            circuit_breaker = SemanticCircuitBreaker(semantic_oracle) if semantic_oracle else None

            # Dispute and governance
            dispute_manager = DisputeManager(api_key)

            # Negotiation
            negotiation_engine = AutomatedNegotiationEngine(api_key)

            # Update the centralized registry
            managers.llm_validator = llm_validator
            managers.hybrid_validator = hybrid_validator
            managers.drift_detector = drift_detector
            managers.dialectic_validator = dialectic_validator
            managers.multi_model_consensus = multi_model_consensus
            managers.contract_parser = contract_parser
            managers.contract_matcher = contract_matcher
            managers.semantic_oracle = semantic_oracle
            managers.circuit_breaker = circuit_breaker
            managers.dispute_manager = dispute_manager
            managers.negotiation_engine = negotiation_engine

            print(
                "LLM-based features initialized (contracts, oracles, disputes, "
                "negotiation, multi-model consensus)"
            )
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
        if validation_mode == "dialectic" and dialectic_validator:
            # Use dialectic consensus validation
            dialectic_result = dialectic_validator.validate_entry(content, intent, author)
            validation_result = {
                "validation_mode": "dialectic",
                "dialectic_validation": dialectic_result,
                "overall_decision": dialectic_result.get("decision", "ERROR"),
            }
        elif hybrid_validator:
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

    # Invalidate pending intent cache on new entry
    if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
        cache = get_adaptive_cache()
        cache.on_new_entry()

    # Auto-mine if requested
    auto_mine = data.get("auto_mine", False)
    mined_block = None
    if auto_mine:
        mined_block = blockchain.mine_pending_entries()
        save_chain()
        # Invalidate all affected caches on new block
        if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
            cache = get_adaptive_cache()
            cache.on_new_block()

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

    # Invalidate caches affected by new block
    if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
        cache = get_adaptive_cache()
        cache.on_new_block()

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
    Uses adaptive caching to reduce load during congestion.

    Returns:
        Various statistics about the blockchain
    """
    # Try adaptive cache first
    if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
        cache = get_adaptive_cache()

        def compute_stats():
            return _compute_stats()

        result = cache.get_or_compute(CacheCategory.STATS, "blockchain_stats", compute_stats)
        return jsonify(result)

    # Fallback: compute directly without cache
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
        "drift_detection_enabled": drift_detector is not None,
        "dialectic_consensus_enabled": dialectic_validator is not None,
        "contract_features_enabled": contract_parser is not None and contract_matcher is not None,
        "dispute_features_enabled": dispute_manager is not None,
        "total_contracts": total_contracts,
        "open_contracts": open_contracts,
        "matched_contracts": matched_contracts,
        "total_disputes": sum(
            1
            for block in blockchain.chain
            for entry in block.entries
            if entry.metadata.get("is_dispute")
            and entry.metadata.get("dispute_type") == "dispute_declaration"
        ),
        "open_disputes": sum(
            1
            for block in blockchain.chain
            for entry in block.entries
            if entry.metadata.get("is_dispute")
            and entry.metadata.get("dispute_type") == "dispute_declaration"
            and entry.metadata.get("status") == "open"
        ),
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


# ========== Semantic Drift Detection Endpoints ==========


@app.route("/drift/check", methods=["POST"])
def check_drift():
    """
    Check semantic drift between intent and execution.

    Request body:
    {
        "on_chain_intent": "the canonical intent from blockchain",
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis with score and recommendations
    """
    if not drift_detector:
        return jsonify(
            {"error": "Drift detection not available", "reason": "ANTHROPIC_API_KEY not configured"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    on_chain_intent = data.get("on_chain_intent")
    execution_log = data.get("execution_log")

    if not all([on_chain_intent, execution_log]):
        return jsonify(
            {"error": "Missing required fields", "required": ["on_chain_intent", "execution_log"]}
        ), 400

    result = drift_detector.check_alignment(on_chain_intent, execution_log)

    return jsonify(result)


@app.route("/drift/entry/<int:block_index>/<int:entry_index>", methods=["POST"])
def check_entry_drift(block_index: int, entry_index: int):
    """
    Check drift for a specific blockchain entry against an execution log.

    Args:
        block_index: Block index containing the entry
        entry_index: Entry index within the block

    Request body:
    {
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis for the specific entry
    """
    if not drift_detector:
        return jsonify({"error": "Drift detection not available"}), 503

    # Validate block index
    if block_index < 0 or block_index >= len(blockchain.chain):
        return jsonify(
            {"error": "Block not found", "valid_range": f"0-{len(blockchain.chain) - 1}"}
        ), 404

    block = blockchain.chain[block_index]

    # Validate entry index
    if entry_index < 0 or entry_index >= len(block.entries):
        return jsonify(
            {"error": "Entry not found", "valid_range": f"0-{len(block.entries) - 1}"}
        ), 404

    entry = block.entries[entry_index]

    # Get execution log from request
    data = request.get_json()
    if not data or "execution_log" not in data:
        return jsonify({"error": "Missing required field: execution_log"}), 400

    execution_log = data["execution_log"]

    # Check drift
    result = drift_detector.check_entry_execution_alignment(
        entry.content, entry.intent, execution_log
    )

    result["entry_info"] = {
        "block_index": block_index,
        "entry_index": entry_index,
        "author": entry.author,
        "intent": entry.intent,
    }

    return jsonify(result)


# ========== Dialectic Consensus Endpoint ==========


@app.route("/validate/dialectic", methods=["POST"])
def validate_dialectic():
    """
    Validate an entry using dialectic consensus (Skeptic/Facilitator debate).

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description"
    }

    Returns:
        Dialectic validation result with both perspectives
    """
    if not dialectic_validator:
        return jsonify(
            {
                "error": "Dialectic consensus not available",
                "reason": "ANTHROPIC_API_KEY not configured",
            }
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify(
            {"error": "Missing required fields", "required": ["content", "author", "intent"]}
        ), 400

    result = dialectic_validator.validate_entry(content, intent, author)

    return jsonify(result)


# ========== Semantic Oracle Endpoints ==========


@app.route("/oracle/verify", methods=["POST"])
def verify_oracle_event():
    """
    Verify if an external event triggers a contract condition using semantic analysis.

    Request body:
    {
        "contract_condition": "Original contract condition (prose)",
        "contract_intent": "Intent behind the condition",
        "event_description": "Description of the external event",
        "event_data": {} (optional structured data about the event)
    }

    Returns:
        Oracle verification result with trigger decision and reasoning
    """
    if not semantic_oracle:
        return jsonify(
            {"error": "Semantic oracle not available", "reason": "ANTHROPIC_API_KEY not configured"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    contract_condition = data.get("contract_condition")
    contract_intent = data.get("contract_intent")
    event_description = data.get("event_description")
    event_data = data.get("event_data", {})

    if not all([contract_condition, contract_intent, event_description]):
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["contract_condition", "contract_intent", "event_description"],
            }
        ), 400

    try:
        result = semantic_oracle.verify_event_trigger(
            contract_condition=contract_condition,
            contract_intent=contract_intent,
            event_description=event_description,
            event_data=event_data,
        )
        return jsonify({"status": "success", "verification": result})
    except Exception as e:
        return jsonify({"error": "Oracle verification failed", "details": str(e)}), 500


# Live Contract Endpoints moved to api/contracts.py

# ========== Dispute Protocol (MP-03) Endpoints ==========


@app.route("/dispute/file", methods=["POST"])
@require_api_key
def file_dispute():
    """
    File a new dispute (MP-03 Dispute Declaration).

    Disputes are signals, not failures. Filing a dispute:
    1. Creates an immutable record of the dispute
    2. Freezes contested entries (prevents mutation)
    3. Establishes the escalation path

    Request body:
    {
        "claimant": "identifier of party filing dispute",
        "respondent": "identifier of party being disputed against",
        "contested_refs": [{"block": 1, "entry": 0}, ...],
        "description": "Natural language description of the dispute",
        "escalation_path": "mediator_node" | "external_arbitrator" | "legal_court" (optional),
        "supporting_evidence": ["hash1", "hash2", ...] (optional),
        "auto_mine": true/false (optional)
    }

    Returns:
        Dispute entry with frozen evidence confirmation
    """
    global dispute_manager
    if not dispute_manager:
        # Initialize basic dispute manager without LLM
        dispute_manager = DisputeManager()

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    claimant = data.get("claimant")
    respondent = data.get("respondent")
    contested_refs = data.get("contested_refs", [])
    description = data.get("description")

    if not all([claimant, respondent, description]):
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["claimant", "respondent", "description"],
            }
        ), 400

    if not contested_refs:
        return jsonify(
            {
                "error": "No contested entries specified",
                "required": 'contested_refs: [{"block": int, "entry": int}, ...]',
            }
        ), 400

    # Validate contested refs exist
    for ref in contested_refs:
        block_idx = ref.get("block", -1)
        entry_idx = ref.get("entry", -1)

        if block_idx < 0 or block_idx >= len(blockchain.chain):
            return jsonify(
                {
                    "error": f"Invalid block reference: {block_idx}",
                    "valid_range": f"0-{len(blockchain.chain) - 1}",
                }
            ), 400

        block = blockchain.chain[block_idx]
        if entry_idx < 0 or entry_idx >= len(block.entries):
            return jsonify(
                {
                    "error": f"Invalid entry reference in block {block_idx}: {entry_idx}",
                    "valid_range": f"0-{len(block.entries) - 1}",
                }
            ), 400

    # Validate dispute clarity
    is_valid, reason = dispute_manager.validate_dispute_clarity(description)
    if not is_valid:
        return jsonify({"error": "Dispute validation failed", "reason": reason}), 400

    try:
        # Create dispute
        dispute_data = dispute_manager.create_dispute(
            claimant=claimant,
            respondent=respondent,
            contested_refs=contested_refs,
            description=description,
            escalation_path=data.get("escalation_path", DisputeManager.ESCALATION_MEDIATOR),
            supporting_evidence=data.get("supporting_evidence"),
        )

        # Format dispute content
        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_DECLARATION, description, dispute_data["dispute_id"]
        )

        # Create blockchain entry with encrypted sensitive fields
        entry = create_entry_with_encryption(
            content=formatted_content,
            author=claimant,
            intent=f"File dispute against {respondent}",
            metadata=dispute_data,
        )
        entry.validation_status = "valid"

        # Add to blockchain
        result = blockchain.add_entry(entry)

        # Auto-mine if requested
        auto_mine = data.get("auto_mine", False)
        mined_block = None
        if auto_mine:
            mined_block = blockchain.mine_pending_entries()
            save_chain()

        response = {
            "status": "success",
            "message": "Dispute filed successfully",
            "dispute_id": dispute_data["dispute_id"],
            "entry": result,
            "evidence_frozen": True,
            "frozen_entries_count": len(contested_refs),
        }

        if mined_block:
            response["mined_block"] = {"index": mined_block.index, "hash": mined_block.hash}

        return jsonify(response), 201

    except Exception as e:
        return jsonify({"error": "Failed to file dispute", "reason": str(e)}), 500


@app.route("/dispute/list", methods=["GET"])
def list_disputes():
    """
    List all disputes, optionally filtered.

    Query params:
        status: Filter by status (open, clarifying, escalated, resolved)
        claimant: Filter by claimant
        respondent: Filter by respondent

    Returns:
        List of dispute entries
    """
    status_filter = request.args.get("status")
    claimant_filter = request.args.get("claimant")
    respondent_filter = request.args.get("respondent")

    disputes = []

    for block in blockchain.chain:
        for entry_idx, entry in enumerate(block.entries):
            metadata = entry.metadata or {}

            # Skip if not a dispute declaration
            if not metadata.get("is_dispute"):
                continue
            if metadata.get("dispute_type") != DisputeManager.TYPE_DECLARATION:
                continue

            # Apply filters
            if status_filter and metadata.get("status") != status_filter:
                continue

            if claimant_filter and metadata.get("claimant") != claimant_filter:
                continue

            if respondent_filter and metadata.get("respondent") != respondent_filter:
                continue

            disputes.append(
                {
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "entry_index": entry_idx,
                    "dispute_id": metadata.get("dispute_id"),
                    "claimant": metadata.get("claimant"),
                    "respondent": metadata.get("respondent"),
                    "status": metadata.get("status"),
                    "created_at": metadata.get("created_at"),
                    "entry": entry.to_dict(),
                }
            )

    return jsonify({"count": len(disputes), "disputes": disputes})


@app.route("/dispute/<dispute_id>", methods=["GET"])
def get_dispute(dispute_id: str):
    """
    Get detailed status of a specific dispute.

    Args:
        dispute_id: The dispute identifier

    Returns:
        Complete dispute status and history
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    status = dispute_manager.get_dispute_status(dispute_id, blockchain)

    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    return jsonify(status)


@app.route("/dispute/<dispute_id>/evidence", methods=["POST"])
@require_api_key
def add_dispute_evidence(dispute_id: str):
    """
    Add evidence to an existing dispute.

    Evidence is append-only and timestamped.

    Request body:
    {
        "author": "who is submitting",
        "evidence_content": "description/content of evidence",
        "evidence_type": "document" | "testimony" | "receipt" | "screenshot" | "other",
        "evidence_hash": "hash of external file" (optional)
    }

    Returns:
        Evidence entry confirmation
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    if status.get("is_resolved"):
        return jsonify(
            {"error": "Cannot add evidence to resolved dispute", "dispute_id": dispute_id}
        ), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    author = data.get("author")
    evidence_content = data.get("evidence_content")

    if not all([author, evidence_content]):
        return jsonify(
            {"error": "Missing required fields", "required": ["author", "evidence_content"]}
        ), 400

    try:
        evidence_data = dispute_manager.add_evidence(
            dispute_id=dispute_id,
            author=author,
            evidence_content=evidence_content,
            evidence_type=data.get("evidence_type", "document"),
            evidence_hash=data.get("evidence_hash"),
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_EVIDENCE, evidence_content, dispute_id
        )

        entry = create_entry_with_encryption(
            content=formatted_content,
            author=author,
            intent=f"Submit evidence for dispute {dispute_id}",
            metadata=evidence_data,
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)

        return jsonify(
            {
                "status": "success",
                "message": "Evidence added to dispute",
                "dispute_id": dispute_id,
                "evidence_hash": evidence_data.get("evidence_hash"),
                "entry": result,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": "Failed to add evidence", "reason": str(e)}), 500


@app.route("/dispute/<dispute_id>/escalate", methods=["POST"])
@require_api_key
def escalate_dispute(dispute_id: str):
    """
    Escalate a dispute to higher authority.

    Request body:
    {
        "escalating_party": "who is escalating",
        "escalation_path": "mediator_node" | "external_arbitrator" | "legal_court",
        "escalation_reason": "why escalation is needed",
        "escalation_authority": "specific authority if known" (optional)
    }

    Returns:
        Escalation entry confirmation
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    if status.get("is_resolved"):
        return jsonify({"error": "Cannot escalate resolved dispute", "dispute_id": dispute_id}), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    escalating_party = data.get("escalating_party")
    escalation_path = data.get("escalation_path")
    escalation_reason = data.get("escalation_reason")

    if not all([escalating_party, escalation_path, escalation_reason]):
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["escalating_party", "escalation_path", "escalation_reason"],
            }
        ), 400

    try:
        escalation_data = dispute_manager.escalate_dispute(
            dispute_id=dispute_id,
            escalating_party=escalating_party,
            escalation_path=escalation_path,
            escalation_reason=escalation_reason,
            escalation_authority=data.get("escalation_authority"),
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_ESCALATION, escalation_reason, dispute_id
        )

        entry = create_entry_with_encryption(
            content=formatted_content,
            author=escalating_party,
            intent=f"Escalate dispute {dispute_id} to {escalation_path}",
            metadata=escalation_data,
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)

        return jsonify(
            {
                "status": "success",
                "message": f"Dispute escalated to {escalation_path}",
                "dispute_id": dispute_id,
                "escalation_path": escalation_path,
                "entry": result,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": "Failed to escalate dispute", "reason": str(e)}), 500


@app.route("/dispute/<dispute_id>/resolve", methods=["POST"])
@require_api_key
def resolve_dispute(dispute_id: str):
    """
    Record the resolution of a dispute.

    Note: Per Refusal Doctrine, this only RECORDS resolution.
    Actual resolution is determined by humans/authorities.

    Request body:
    {
        "resolution_authority": "who authorized the resolution",
        "resolution_type": "settled" | "arbitrated" | "adjudicated" | "withdrawn",
        "resolution_content": "Natural language resolution description",
        "findings": {"key": "value"} (optional),
        "remedies": ["remedy1", "remedy2", ...] (optional)
    }

    Returns:
        Resolution entry with unfrozen entries
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    if status.get("is_resolved"):
        return jsonify({"error": "Dispute already resolved", "dispute_id": dispute_id}), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    resolution_authority = data.get("resolution_authority")
    resolution_type = data.get("resolution_type")
    resolution_content = data.get("resolution_content")

    if not all([resolution_authority, resolution_type, resolution_content]):
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["resolution_authority", "resolution_type", "resolution_content"],
            }
        ), 400

    valid_resolution_types = ["settled", "arbitrated", "adjudicated", "withdrawn"]
    if resolution_type not in valid_resolution_types:
        return jsonify(
            {"error": f"Invalid resolution_type. Must be one of: {valid_resolution_types}"}
        ), 400

    try:
        resolution_data = dispute_manager.record_resolution(
            dispute_id=dispute_id,
            resolution_authority=resolution_authority,
            resolution_type=resolution_type,
            resolution_content=resolution_content,
            findings=data.get("findings"),
            remedies=data.get("remedies"),
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_RESOLUTION, resolution_content, dispute_id
        )

        entry = create_entry_with_encryption(
            content=formatted_content,
            author=resolution_authority,
            intent=f"Resolve dispute {dispute_id}: {resolution_type}",
            metadata=resolution_data,
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)
        save_chain()

        return jsonify(
            {
                "status": "success",
                "message": f"Dispute resolved: {resolution_type}",
                "dispute_id": dispute_id,
                "entries_unfrozen": resolution_data.get("entries_unfrozen", 0),
                "entry": result,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": "Failed to record resolution", "reason": str(e)}), 500


@app.route("/dispute/<dispute_id>/package", methods=["GET"])
def get_dispute_package(dispute_id: str):
    """
    Generate a complete dispute package for external arbitration.

    This package contains all information needed for an external
    authority to review and resolve the dispute.

    Query params:
        include_entries: true/false (whether to include full frozen entries, default true)

    Returns:
        Complete dispute package with integrity hash
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    include_entries = request.args.get("include_entries", "true").lower() == "true"

    try:
        package = dispute_manager.generate_dispute_package(
            dispute_id=dispute_id, blockchain=blockchain, include_frozen_entries=include_entries
        )

        return jsonify(package)

    except Exception as e:
        return jsonify({"error": "Failed to generate dispute package", "reason": str(e)}), 500


@app.route("/dispute/<dispute_id>/analyze", methods=["GET"])
def analyze_dispute(dispute_id: str):
    """
    Get LLM analysis of a dispute (for understanding, not resolution).

    Note: Per Refusal Doctrine, this analysis is for UNDERSTANDING only.
    LLMs do not resolve disputes.

    Returns:
        Dispute analysis with key issues identified
    """
    if not dispute_manager or not dispute_manager.client:
        return jsonify(
            {"error": "Dispute analysis not available", "reason": "LLM features not configured"}
        ), 503

    # Verify dispute exists and get details
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({"error": "Dispute not found", "dispute_id": dispute_id}), 404

    # Get the dispute description and contested content
    dispute_description = None
    contested_content = []

    for block in blockchain.chain:
        for entry in block.entries:
            metadata = entry.metadata or {}

            if metadata.get("dispute_id") == dispute_id:
                if metadata.get("dispute_type") == DisputeManager.TYPE_DECLARATION:
                    dispute_description = entry.content

                    # Get contested entries
                    for ref in metadata.get("contested_refs", []):
                        block_idx = ref.get("block", 0)
                        entry_idx = ref.get("entry", 0)
                        if block_idx < len(blockchain.chain):
                            contested_block = blockchain.chain[block_idx]
                            if entry_idx < len(contested_block.entries):
                                contested_entry = contested_block.entries[entry_idx]
                                contested_content.append(contested_entry.content)
                    break

    if not dispute_description:
        return jsonify(
            {"error": "Could not find dispute description", "dispute_id": dispute_id}
        ), 404

    try:
        analysis = dispute_manager.analyze_dispute(
            dispute_description=dispute_description,
            contested_content="\n\n---\n\n".join(contested_content),
        )

        if not analysis:
            return jsonify(
                {"error": "Analysis failed", "reason": "LLM analysis returned empty result"}
            ), 500

        return jsonify(
            {
                "dispute_id": dispute_id,
                "analysis": analysis,
                "disclaimer": "This analysis is for understanding only. Per NatLangChain Refusal Doctrine, dispute resolution requires human judgment.",
            }
        )

    except Exception as e:
        return jsonify({"error": "Analysis failed", "reason": str(e)}), 500


@app.route("/entry/frozen/<int:block_index>/<int:entry_index>", methods=["GET"])
def check_entry_frozen(block_index: int, entry_index: int):
    """
    Check if an entry is frozen due to dispute.

    Args:
        block_index: Block index
        entry_index: Entry index

    Returns:
        Frozen status and dispute ID if frozen
    """
    if not dispute_manager:
        return jsonify(
            {"frozen": False, "dispute_id": None, "message": "Dispute features not initialized"}
        )

    is_frozen, dispute_id = dispute_manager.is_entry_frozen(block_index, entry_index)

    return jsonify(
        {
            "block_index": block_index,
            "entry_index": entry_index,
            "frozen": is_frozen,
            "dispute_id": dispute_id,
        }
    )


# ========== Escalation Fork Endpoints ==========


# ========== Observance Burn Endpoints ==========


# ========== Anti-Harassment Economic Layer Endpoints ==========


# ========== Treasury System Endpoints ==========


# ========== FIDO2/WebAuthn Endpoints ==========


# ========== ZK Privacy Infrastructure Endpoints ==========

# ----- Phase 14A: Dispute Membership Circuit -----


# ----- Phase 14B: Viewing Key Infrastructure -----


# ----- Phase 14C: Inference Attack Mitigations -----


# ----- Phase 14D: Threshold Decryption / Compliance -----


# ----- ZK Privacy General -----


# ========== Automated Negotiation Engine Endpoints ==========


@app.route("/negotiation/session", methods=["POST"])
@require_api_key
def initiate_negotiation_session():
    """
    Initiate a new negotiation session.

    Request body:
    {
        "initiator": "alice",
        "counterparty": "bob",
        "subject": "Software development contract",
        "initiator_statement": "I want to hire a developer for 3 months...",
        "initial_terms": {"budget": "50000", "timeline": "3 months"} (optional)
    }

    Returns:
        Session info with ID and next steps
    """
    if not negotiation_engine:
        return jsonify(
            {"error": "Negotiation engine not available", "reason": "Features not initialized"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["initiator", "counterparty", "subject", "initiator_statement"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({"error": "Missing required fields", "missing": missing}), 400

    success, result = negotiation_engine.initiate_session(
        initiator=data["initiator"],
        counterparty=data["counterparty"],
        subject=data["subject"],
        initiator_statement=data["initiator_statement"],
        initial_terms=data.get("initial_terms"),
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/negotiation/session/<session_id>/join", methods=["POST"])
def join_negotiation_session(session_id: str):
    """
    Counterparty joins a negotiation session.

    Request body:
    {
        "counterparty": "bob",
        "counterparty_statement": "I'm available for contract work..."
    }

    Returns:
        Alignment analysis and next steps
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "counterparty" not in data or "counterparty_statement" not in data:
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["counterparty", "counterparty_statement"],
            }
        ), 400

    success, result = negotiation_engine.join_session(
        session_id=session_id,
        counterparty=data["counterparty"],
        counterparty_statement=data["counterparty_statement"],
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/negotiation/session/<session_id>", methods=["GET"])
def get_negotiation_session(session_id: str):
    """Get negotiation session details."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    session = negotiation_engine.get_session(session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(session)


@app.route("/negotiation/session/<session_id>/advance", methods=["POST"])
def advance_negotiation_phase(session_id: str):
    """
    Advance session to next phase.

    Request body:
    {
        "party": "alice"
    }

    Returns:
        Phase transition info
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    success, result = negotiation_engine.advance_phase(session_id=session_id, party=data["party"])

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/negotiation/session/<session_id>/clause", methods=["POST"])
def add_negotiation_clause(session_id: str):
    """
    Add a clause to the session.

    Request body:
    {
        "clause_type": "payment|delivery|quality|timeline|...",
        "parameters": {"amount": "50000", "method": "wire transfer", ...},
        "proposed_by": "alice"
    }

    Returns:
        Generated clause with alternatives
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["clause_type", "parameters", "proposed_by"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({"error": "Missing required fields", "missing": missing}), 400

    try:
        clause_type = ClauseType(data["clause_type"])
    except ValueError:
        return jsonify(
            {"error": "Invalid clause_type", "valid_values": [t.value for t in ClauseType]}
        ), 400

    success, result = negotiation_engine.add_clause(
        session_id=session_id,
        clause_type=clause_type,
        parameters=data["parameters"],
        proposed_by=data["proposed_by"],
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/negotiation/session/<session_id>/clause/<clause_id>/respond", methods=["POST"])
def respond_to_negotiation_clause(session_id: str, clause_id: str):
    """
    Respond to a proposed clause.

    Request body:
    {
        "party": "bob",
        "response": "accept|reject|modify",
        "modified_content": "New clause text..." (required if modify)
    }

    Returns:
        Clause status update
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "party" not in data or "response" not in data:
        return jsonify({"error": "Missing required fields", "required": ["party", "response"]}), 400

    if data["response"] not in ["accept", "reject", "modify"]:
        return jsonify(
            {"error": "Invalid response", "valid_values": ["accept", "reject", "modify"]}
        ), 400

    success, result = negotiation_engine.respond_to_clause(
        session_id=session_id,
        clause_id=clause_id,
        party=data["party"],
        response=data["response"],
        modified_content=data.get("modified_content"),
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/negotiation/session/<session_id>/clauses", methods=["GET"])
def get_negotiation_clauses(session_id: str):
    """Get all clauses in a session."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    clauses = negotiation_engine.get_session_clauses(session_id)

    return jsonify({"session_id": session_id, "count": len(clauses), "clauses": clauses})


@app.route("/negotiation/session/<session_id>/offer", methods=["POST"])
def make_negotiation_offer(session_id: str):
    """
    Make an offer in the negotiation.

    Request body:
    {
        "from_party": "alice",
        "terms": {"price": "45000", "timeline": "2.5 months", ...},
        "message": "I've adjusted the timeline to accommodate...",
        "offer_type": "initial|counter|final" (optional, default initial)
    }

    Returns:
        Offer confirmation
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["from_party", "terms", "message"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({"error": "Missing required fields", "missing": missing}), 400

    offer_type = OfferType.INITIAL
    if data.get("offer_type"):
        try:
            offer_type = OfferType(data["offer_type"])
        except ValueError:
            return jsonify(
                {"error": "Invalid offer_type", "valid_values": [t.value for t in OfferType]}
            ), 400

    success, result = negotiation_engine.make_offer(
        session_id=session_id,
        from_party=data["from_party"],
        terms=data["terms"],
        message=data["message"],
        offer_type=offer_type,
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/negotiation/session/<session_id>/offer/<offer_id>/respond", methods=["POST"])
def respond_to_negotiation_offer(session_id: str, offer_id: str):
    """
    Respond to an offer.

    Request body:
    {
        "party": "bob",
        "response": "accept|reject|counter",
        "counter_terms": {...} (required if counter),
        "message": "Response message..." (optional)
    }

    Returns:
        Response result (agreement if accepted)
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "party" not in data or "response" not in data:
        return jsonify({"error": "Missing required fields", "required": ["party", "response"]}), 400

    if data["response"] not in ["accept", "reject", "counter"]:
        return jsonify(
            {"error": "Invalid response", "valid_values": ["accept", "reject", "counter"]}
        ), 400

    success, result = negotiation_engine.respond_to_offer(
        session_id=session_id,
        offer_id=offer_id,
        party=data["party"],
        response=data["response"],
        counter_terms=data.get("counter_terms"),
        message=data.get("message"),
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/negotiation/session/<session_id>/offers", methods=["GET"])
def get_negotiation_offers(session_id: str):
    """Get all offers in a session."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    offers = negotiation_engine.get_session_offers(session_id)

    return jsonify({"session_id": session_id, "count": len(offers), "offers": offers})


@app.route("/negotiation/session/<session_id>/auto-counter", methods=["POST"])
def auto_draft_counter_offer(session_id: str):
    """
    Automatically draft a counter-offer using AI.

    Request body:
    {
        "party": "bob",
        "strategy": "aggressive|balanced|cooperative" (optional, default balanced)
    }

    Returns:
        AI-drafted counter-offer
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    strategy = data.get("strategy", "balanced")
    if strategy not in ["aggressive", "balanced", "cooperative"]:
        return jsonify(
            {"error": "Invalid strategy", "valid_values": ["aggressive", "balanced", "cooperative"]}
        ), 400

    success, result = negotiation_engine.auto_draft_counter(
        session_id=session_id, party=data["party"], strategy=strategy
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route("/negotiation/session/<session_id>/strategies", methods=["GET"])
def get_alignment_strategies(session_id: str):
    """
    Get alignment strategies for a party.

    Query params:
        party: Party to get strategies for
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    party = request.args.get("party")
    if not party:
        return jsonify({"error": "Missing required query param: party"}), 400

    strategies = negotiation_engine.get_alignment_strategies(session_id, party)

    return jsonify({"session_id": session_id, "party": party, "strategies": strategies})


@app.route("/negotiation/session/<session_id>/finalize", methods=["POST"])
def finalize_negotiation_agreement(session_id: str):
    """
    Finalize an agreed negotiation into a contract.

    Request body:
    {
        "party": "alice"
    }

    Returns:
        Final contract document
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    success, result = negotiation_engine.finalize_agreement(
        session_id=session_id, party=data["party"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/negotiation/stats", methods=["GET"])
def get_negotiation_stats():
    """Get negotiation engine statistics."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    stats = negotiation_engine.get_statistics()
    return jsonify(stats)


@app.route("/negotiation/audit", methods=["GET"])
def get_negotiation_audit():
    """
    Get negotiation audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    limit = request.args.get("limit", 100, type=int)
    # SECURITY: Validate limit parameter
    limit, _ = validate_pagination_params(limit, 0)

    trail = negotiation_engine.get_audit_trail(limit=limit)

    return jsonify({"count": len(trail), "audit_trail": trail})


@app.route("/negotiation/clause-types", methods=["GET"])
def get_clause_types():
    """Get available clause types."""
    return jsonify(
        {
            "clause_types": [
                {
                    "value": t.value,
                    "name": t.name,
                    "description": {
                        "payment": "Payment terms and conditions",
                        "delivery": "Delivery location and timing",
                        "quality": "Quality standards and verification",
                        "timeline": "Project timeline and milestones",
                        "liability": "Liability limits and exclusions",
                        "termination": "Contract termination conditions",
                        "dispute_resolution": "Dispute resolution method",
                        "confidentiality": "Confidentiality and NDA terms",
                        "custom": "Custom clause",
                    }.get(t.value, "Contract clause"),
                }
                for t in ClauseType
            ]
        }
    )


# ========== Market-Aware Pricing Endpoints ==========


# ============================================================
# Mobile Deployment Endpoints (Plan 17)
# ============================================================


# Chat Helper Endpoints moved to api/chat.py

# =============================================================================
# P2P Network & Mediator Node API (api/v1/)
# =============================================================================

# Global P2P network instance
p2p_network = None


def init_p2p():
    """Initialize P2P network if available."""
    global p2p_network
    if P2P_AVAILABLE and p2p_network is None:
        bootstrap_peers = os.getenv("NATLANGCHAIN_BOOTSTRAP_PEERS", "").split(",")
        bootstrap_peers = [p.strip() for p in bootstrap_peers if p.strip()]

        p2p_network = init_p2p_network(
            node_id=os.getenv("NATLANGCHAIN_NODE_ID"),
            endpoint=os.getenv(
                "NATLANGCHAIN_ENDPOINT", f"http://localhost:{os.getenv('PORT', 5000)}"
            ),
            bootstrap_peers=bootstrap_peers if bootstrap_peers else None,
        )

        # Set up chain provider callbacks
        p2p_network.set_chain_provider(
            get_chain_info=lambda: blockchain.to_dict(),
            get_blocks=lambda start, end: [
                blockchain.chain[i].to_dict()
                for i in range(start, min(end + 1, len(blockchain.chain)))
            ],
            add_block=lambda block_data: _add_synced_block(block_data),
        )

        # Set up broadcast handlers
        p2p_network.on_entry_received(_handle_broadcast_entry)
        p2p_network.on_block_received(_handle_broadcast_block)
        p2p_network.on_settlement_received(_handle_broadcast_settlement)

        p2p_network.start()
        return True
    return False


def _add_synced_block(block_data):
    """Add a block received from sync."""
    try:
        from blockchain import Block

        block = Block.from_dict(block_data)
        # Verify block links to our chain
        if len(blockchain.chain) > 0 and block.previous_hash != blockchain.chain[-1].hash:
            return False
        blockchain.chain.append(block)
        save_chain()
        return True
    except Exception as e:
        print(f"Failed to add synced block: {e}")
        return False


def _handle_broadcast_entry(entry_data):
    """Handle a broadcast entry from peers."""
    try:
        from blockchain import NaturalLanguageEntry

        entry = NaturalLanguageEntry.from_dict(entry_data)
        blockchain.add_entry(entry)
    except Exception as e:
        print(f"Failed to handle broadcast entry: {e}")


def _handle_broadcast_block(block_data):
    """Handle a broadcast block from peers."""
    _add_synced_block(block_data)


def _handle_broadcast_settlement(settlement_data):
    """Handle a broadcast settlement from mediator."""
    try:
        # Create settlement entry
        entry = create_entry_with_encryption(
            content=settlement_data.get("content", ""),
            author=settlement_data.get("author", "mediator"),
            intent="settlement",
            metadata=settlement_data.get("metadata", {}),
        )
        blockchain.add_entry(entry)
    except Exception as e:
        print(f"Failed to handle broadcast settlement: {e}")


@app.route("/api/v1/node/info", methods=["GET"])
def get_node_info():
    """
    Get this node's information for peer discovery.

    Returns:
        Node ID, role, chain height, capabilities
    """
    if not P2P_AVAILABLE:
        return jsonify(
            {
                "node_id": "standalone",
                "role": "full_node",
                "chain_height": len(blockchain.chain) - 1,
                "chain_tip_hash": blockchain.chain[-1].hash if blockchain.chain else "",
                "version": "0.1.0-alpha",
                "p2p_enabled": False,
            }
        )

    if p2p_network is None:
        init_p2p()

    if p2p_network:
        return jsonify(p2p_network.get_node_info())
    else:
        return jsonify({"error": "P2P network not initialized"}), 503


@app.route("/api/v1/health", methods=["GET"])
def p2p_health():
    """P2P health check endpoint for peers."""
    response = {
        "status": "healthy",
        "chain_height": len(blockchain.chain) - 1,
        "pending_entries": len(blockchain.pending_entries),
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Include cache congestion info if available
    if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
        cache = get_adaptive_cache()
        congestion = cache.congestion.get_state()
        response["congestion"] = {
            "level": congestion.level.value,
            "factor": round(congestion.factor, 2),
        }

    return jsonify(response)


@app.route("/api/v1/cache/stats", methods=["GET"])
def get_cache_stats():
    """
    Get adaptive cache statistics.

    Returns cache performance metrics and current congestion state.
    Useful for monitoring mediator node performance.
    """
    if not ADAPTIVE_CACHE_AVAILABLE or not get_adaptive_cache:
        return jsonify({"enabled": False, "reason": "Adaptive cache not available"})

    cache = get_adaptive_cache()
    return jsonify(cache.get_stats())


@app.route("/api/v1/peers/register", methods=["POST"])
def register_peer():
    """
    Register a peer with this node.

    Request body:
    {
        "node_id": "peer_id",
        "endpoint": "http://peer:5000",
        "role": "full_node",
        "chain_height": 100,
        ...
    }

    SECURITY: Endpoint URLs are validated to prevent SSRF attacks.
    """
    if not P2P_AVAILABLE or p2p_network is None:
        return jsonify({"error": "P2P not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    peer_id = data.get("node_id")
    endpoint = data.get("endpoint")

    if not peer_id or not endpoint:
        return jsonify({"error": "node_id and endpoint required"}), 400

    # SECURITY FIX: Validate endpoint to prevent SSRF attacks
    # This endpoint is stored and could be used later to connect back to the peer
    is_safe, ssrf_error = is_safe_peer_endpoint(endpoint)
    if not is_safe:
        logger.warning(f"SSRF attempt blocked in peer registration: {endpoint} - {ssrf_error}")
        return jsonify({"error": f"Invalid endpoint: {ssrf_error}"}), 400

    from p2p_network import NodeRole, PeerInfo, PeerStatus

    peer = PeerInfo(
        peer_id=peer_id,
        endpoint=endpoint,
        role=NodeRole(data.get("role", "full_node")),
        status=PeerStatus.CONNECTED,
        chain_height=data.get("chain_height", 0),
        chain_tip_hash=data.get("chain_tip_hash", ""),
        last_seen=datetime.utcnow(),
        version=data.get("version", "unknown"),
        capabilities=set(data.get("capabilities", [])),
    )

    p2p_network.peers[peer_id] = peer

    return jsonify({"status": "registered", "node_id": p2p_network.node_id})


@app.route("/api/v1/peers", methods=["GET"])
def list_peers():
    """List all connected peers."""
    if not P2P_AVAILABLE or p2p_network is None:
        return jsonify({"peers": [], "count": 0})

    peers = [p.to_dict() for p in p2p_network.get_connected_peers()]
    return jsonify({"peers": peers, "count": len(peers)})


@app.route("/api/v1/peers/connect", methods=["POST"])
def connect_peer():
    """
    Connect to a new peer.

    Request body:
    {
        "endpoint": "http://peer:5000"
    }

    SECURITY: Endpoint URLs are validated to prevent SSRF attacks.
    """
    if not P2P_AVAILABLE:
        return jsonify({"error": "P2P not available"}), 503

    if p2p_network is None:
        init_p2p()

    data = request.get_json()
    endpoint = data.get("endpoint") if data else None

    if not endpoint:
        return jsonify({"error": "endpoint required"}), 400

    # SECURITY FIX: Validate endpoint to prevent SSRF attacks
    is_safe, ssrf_error = is_safe_peer_endpoint(endpoint)
    if not is_safe:
        logger.warning(f"SSRF attempt blocked: {endpoint} - {ssrf_error}")
        return jsonify({"error": f"Invalid endpoint: {ssrf_error}"}), 400

    success, peer = p2p_network.connect_to_peer(endpoint)

    if success:
        return jsonify({"status": "connected", "peer": peer.to_dict()})
    else:
        return jsonify({"error": "Failed to connect to peer"}), 500


# =============================================================================
# Mediator Node Integration API
# =============================================================================


@app.route("/api/v1/intents", methods=["GET"])
def get_intents():
    """
    Get pending intents for mediator nodes.

    This is the primary endpoint mediators poll to find matching opportunities.
    Uses adaptive caching to reduce load during congestion.

    Query params:
        status: Filter by status (pending, open)
        limit: Max results (default 100)

    Returns:
        List of intent entries ready for matching
    """
    status_filter = request.args.get("status", "open")
    limit = min(int(request.args.get("limit", DEFAULT_PAGE_LIMIT)), MAX_PAGE_LIMIT)

    # Try adaptive cache first
    if ADAPTIVE_CACHE_AVAILABLE and get_adaptive_cache:
        cache = get_adaptive_cache()
        cache_key = make_cache_key(status_filter, limit)

        # Update congestion state with pending count
        cache.congestion.update(len(blockchain.pending_entries))

        def compute_intents():
            return _compute_intents(status_filter, limit)

        result = cache.get_or_compute(CacheCategory.INTENTS, cache_key, compute_intents)
        return jsonify(result)

    # Fallback: compute directly without cache
    return jsonify(_compute_intents(status_filter, limit))


def _compute_intents(status_filter: str, limit: int) -> dict:
    """Compute intents (extracted for caching)."""
    intents = []

    # Get pending entries
    for entry in blockchain.pending_entries[:limit]:
        if entry.metadata.get("is_contract"):
            intent_id = hashlib.sha256(
                json.dumps(entry.to_dict(), sort_keys=True).encode()
            ).hexdigest()[:16]

            intents.append(
                {
                    "intent_id": intent_id,
                    "content": entry.content,
                    "author": entry.author,
                    "intent": entry.intent,
                    "metadata": decrypt_entry_metadata(entry.to_dict()).get("metadata", {}),
                    "timestamp": entry.timestamp,
                    "status": "pending",
                }
            )

    # Get open contracts from chain
    if status_filter in ("open", "all"):
        for block in blockchain.chain:
            for entry in block.entries:
                if len(intents) >= limit:
                    break
                metadata = entry.metadata or {}
                if metadata.get("is_contract") and metadata.get("status") == "open":
                    intent_id = hashlib.sha256(
                        json.dumps(entry.to_dict(), sort_keys=True).encode()
                    ).hexdigest()[:16]

                    intents.append(
                        {
                            "intent_id": intent_id,
                            "block_index": block.index,
                            "block_hash": block.hash,
                            "content": entry.content,
                            "author": entry.author,
                            "intent": entry.intent,
                            "metadata": decrypt_entry_metadata(entry.to_dict()).get("metadata", {}),
                            "timestamp": entry.timestamp,
                            "status": "open",
                        }
                    )

    return {"intents": intents, "count": len(intents)}


@app.route("/api/v1/entries", methods=["POST"])
@require_api_key
def submit_entry_v1():
    """
    Submit an entry to the chain (used by mediator nodes).

    Request body:
    {
        "type": "settlement",
        "author": "mediator_id",
        "content": {...},
        "metadata": {...},
        "signature": "optional_signature"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    entry_type = data.get("type")
    author = data.get("author")
    content = data.get("content")
    metadata = data.get("metadata", {})

    if not all([entry_type, author, content]):
        return jsonify({"error": "type, author, and content required"}), 400

    try:
        # Create entry with encryption for sensitive fields
        entry = create_entry_with_encryption(
            content=content if isinstance(content, str) else json.dumps(content),
            author=author,
            intent=entry_type,
            metadata=metadata,
        )

        result = blockchain.add_entry(entry)

        # Broadcast to network if P2P enabled
        if P2P_AVAILABLE and p2p_network:
            p2p_network.broadcast_entry(entry.to_dict())

        return jsonify(
            {
                "status": "accepted",
                "entryId": hashlib.sha256(
                    json.dumps(entry.to_dict(), sort_keys=True).encode()
                ).hexdigest()[:16],
                "result": result,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/settlements", methods=["POST"])
@require_api_key
def submit_settlement():
    """
    Submit a settlement from a mediator node.

    Request body:
    {
        "mediator_id": "mediator_xxx",
        "intent_a": "intent_id_1",
        "intent_b": "intent_id_2",
        "terms": {...},
        "settlement_text": "Natural language settlement...",
        "model_hash": "reproducibility_hash",
        "consensus_mode": "permissionless",
        "acceptance_window": 72
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["mediator_id", "intent_a", "intent_b", "terms", "settlement_text"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        # Create settlement entry
        settlement_id = secrets.token_hex(8)
        metadata = {
            "is_settlement": True,
            "settlement_id": settlement_id,
            "intent_a": data["intent_a"],
            "intent_b": data["intent_b"],
            "terms": data["terms"],
            "mediator_id": data["mediator_id"],
            "model_hash": data.get("model_hash"),
            "consensus_mode": data.get("consensus_mode", "permissionless"),
            "acceptance_window_hours": data.get("acceptance_window", 72),
            "status": "proposed",
            "proposed_at": datetime.utcnow().isoformat(),
        }

        entry = create_entry_with_encryption(
            content=data["settlement_text"],
            author=data["mediator_id"],
            intent="settlement",
            metadata=metadata,
        )

        result = blockchain.add_entry(entry)

        # Broadcast to network
        if P2P_AVAILABLE and p2p_network:
            p2p_network.broadcast_settlement(entry.to_dict())

        return jsonify(
            {
                "status": "proposed",
                "settlement_id": settlement_id,
                "acceptance_window_hours": metadata["acceptance_window_hours"],
                "result": result,
            }
        ), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/settlements/<settlement_id>/status", methods=["GET"])
def get_settlement_status(settlement_id):
    """Get status of a settlement."""
    for block in blockchain.chain:
        for entry in block.entries:
            if entry.metadata.get("settlement_id") == settlement_id:
                return jsonify(
                    {
                        "settlement_id": settlement_id,
                        "status": entry.metadata.get("status", "unknown"),
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "metadata": entry.metadata,
                    }
                )

    # Check pending
    for entry in blockchain.pending_entries:
        if entry.metadata.get("settlement_id") == settlement_id:
            return jsonify(
                {"settlement_id": settlement_id, "status": "pending", "metadata": entry.metadata}
            )

    return jsonify({"error": "Settlement not found"}), 404


@app.route("/api/v1/settlements/<settlement_id>/accept", methods=["POST"])
def accept_settlement(settlement_id):
    """
    Accept a settlement.

    Request body:
    {
        "party": "A" or "B",
        "party_id": "user_identifier",
        "signature": "optional_signature"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    party = data.get("party")
    party_id = data.get("party_id")

    if not party or not party_id:
        return jsonify({"error": "party and party_id required"}), 400

    # Find settlement and update
    for block in blockchain.chain:
        for entry in block.entries:
            if entry.metadata.get("settlement_id") == settlement_id:
                # Create acceptance entry
                acceptance = create_entry_with_encryption(
                    content=f"Party {party} ({party_id}) accepts settlement {settlement_id}",
                    author=party_id,
                    intent="settlement_accept",
                    metadata={
                        "settlement_id": settlement_id,
                        "party": party,
                        "party_id": party_id,
                        "accepted_at": datetime.utcnow().isoformat(),
                    },
                )
                blockchain.add_entry(acceptance)

                return jsonify(
                    {"status": "accepted", "settlement_id": settlement_id, "party": party}
                )

    return jsonify({"error": "Settlement not found"}), 404


@app.route("/api/v1/reputation/<mediator_id>", methods=["GET"])
def get_mediator_reputation(mediator_id):
    """Get reputation metrics for a mediator."""
    # Count successful settlements
    successes = 0
    violations = 0
    total = 0

    for block in blockchain.chain:
        for entry in block.entries:
            if entry.metadata.get("mediator_id") == mediator_id:
                total += 1
                status = entry.metadata.get("status", "")
                if status in ("accepted", "finalized"):
                    successes += 1
                elif status in ("challenged", "rejected"):
                    violations += 1

    # Calculate reputation score
    if total > 0:
        score = (successes - violations) / total
        score = max(0, min(1, (score + 1) / 2))  # Normalize to 0-1
    else:
        score = 0.5  # Default for new mediators

    return jsonify(
        {
            "mediator_id": mediator_id,
            "reputation_score": score,
            "total_settlements": total,
            "successful": successes,
            "violations": violations,
        }
    )


@app.route("/api/v1/reputation", methods=["POST"])
def update_reputation():
    """
    Update mediator reputation (called after settlement finalization).

    Request body:
    {
        "mediator_id": "mediator_xxx",
        "settlement_id": "settlement_xxx",
        "outcome": "success" | "violation",
        "reason": "optional reason"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Create reputation update entry
    entry = create_entry_with_encryption(
        content=f"Reputation update for {data.get('mediator_id')}",
        author="system",
        intent="reputation_update",
        metadata={
            "mediator_id": data.get("mediator_id"),
            "settlement_id": data.get("settlement_id"),
            "outcome": data.get("outcome"),
            "reason": data.get("reason"),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )
    blockchain.add_entry(entry)

    return jsonify({"status": "updated"})


# =============================================================================
# Chain Sync API
# =============================================================================


@app.route("/api/v1/blocks", methods=["GET"])
def get_blocks_range():
    """
    Get blocks in a range (for chain sync).

    Query params:
        start: Start block index
        end: End block index
    """
    start = int(request.args.get("start", 0))
    end = int(request.args.get("end", len(blockchain.chain) - 1))

    # Limit range
    end = min(end, start + 100)
    end = min(end, len(blockchain.chain) - 1)

    blocks = [
        blockchain.chain[i].to_dict() for i in range(start, end + 1) if i < len(blockchain.chain)
    ]

    return jsonify({"blocks": blocks, "start": start, "end": end, "total": len(blockchain.chain)})


@app.route("/api/v1/sync", methods=["POST"])
def trigger_sync():
    """
    Trigger chain synchronization with peers.

    Request body:
    {
        "target_peer": "optional_peer_id"
    }
    """
    if not P2P_AVAILABLE or p2p_network is None:
        return jsonify({"error": "P2P not available"}), 503

    data = request.get_json() or {}
    target_peer = data.get("target_peer")

    success = p2p_network.sync_chain(target_peer)

    return jsonify(
        {"status": "success" if success else "failed", "chain_height": len(blockchain.chain) - 1}
    )


@app.route("/api/v1/broadcast", methods=["POST"])
@require_api_key
def receive_broadcast():
    """
    Receive a broadcast message from a peer.

    This endpoint is called by peers when broadcasting entries/blocks.
    """
    if not P2P_AVAILABLE or p2p_network is None:
        return jsonify({"error": "P2P not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    success = p2p_network.handle_broadcast(data)

    return jsonify({"status": "received" if success else "duplicate"})


@app.route("/api/v1/network/stats", methods=["GET"])
def network_stats():
    """Get P2P network statistics."""
    if not P2P_AVAILABLE or p2p_network is None:
        return jsonify({"p2p_enabled": False, "peer_count": 0})

    return jsonify(p2p_network.get_network_stats())


# =============================================================================
# Governance Help API Endpoints - MOVED to api/help.py
# =============================================================================
# These endpoints are now handled by the help_bp blueprint.
# See api/help.py for the implementation.


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

    # Initialize OpenAPI/Swagger documentation
    swagger_enabled = False
    try:
        from swagger import init_swagger

        swagger_enabled = init_swagger(app)
    except ImportError:
        pass

    print(f"\n{'=' * 60}")
    print("NatLangChain API Server")
    print(f"{'=' * 60}")
    print(f"Listening on: http://{host}:{port}")
    print(
        f"API Docs: http://{host}:{port}/docs"
        if swagger_enabled
        else "API Docs: Disabled (install flask-swagger-ui)"
    )
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
