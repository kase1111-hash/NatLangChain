"""
NatLangChain API Package — App Factory.

This package contains the modular Flask blueprints for the NatLangChain API.
Use create_app() to create a configured Flask application.

Blueprints:
- core: Blockchain operations (chain, entries, blocks, mining, stats)
- search: Semantic search
- contracts: Contract parsing, matching, and management
- derivatives: Derivative tracking routes
- monitoring: Health, metrics, cluster endpoints
"""

import os

from flask import Flask, jsonify, request


def create_app(testing=False):
    """
    Create and configure the Flask application.

    Args:
        testing: If True, skip manager initialization and chain loading.

    Returns:
        Configured Flask application with all blueprints registered.
    """
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # SECURITY: Request size limit — natural language entries shouldn't need more than 2MB
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

    if testing:
        app.config["TESTING"] = True

    # Register security middleware and error handlers
    _register_security_middleware(app)
    _register_error_handlers(app)

    # Initialize feature managers (LLM validators, search, contracts)
    if not testing:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        init_managers(api_key)

    # Load blockchain from storage
    if not testing:
        from . import state

        state.load_chain()

    # Register blueprints
    _register_blueprints(app)

    return app


def _register_blueprints(app):
    """Register all API blueprints with the Flask app."""
    from .contracts import contracts_bp
    from .core import core_bp
    from .derivatives import derivatives_bp
    from .monitoring import monitoring_bp
    from .search import search_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(contracts_bp)
    app.register_blueprint(derivatives_bp)


def _register_security_middleware(app):
    """Register security middleware (rate limiting, security headers, shutdown checks)."""

    @app.before_request
    def before_request_security():
        """Apply security checks before each request."""
        # Skip shutdown/rate-limit checks for health endpoints (needed for K8s probes)
        if request.endpoint in (
            "monitoring.health",
            "monitoring.liveness",
            "monitoring.readiness",
        ):
            return None

        # Reject new requests during shutdown
        from . import state

        if state.is_shutting_down():
            response = jsonify(
                {"error": "Service is shutting down", "status": "unavailable", "retry_after": 30}
            )
            response.status_code = 503
            response.headers["Retry-After"] = "30"
            return response

        # Track this request for graceful shutdown
        state.track_request_start()

        # Rate limiting
        from .utils import check_rate_limit

        rate_error = check_rate_limit()
        if rate_error:
            state.track_request_end()  # Don't count rate-limited requests
            response = jsonify(rate_error)
            response.status_code = 429
            response.headers["Retry-After"] = str(rate_error.get("retry_after", 60))
            return response

        # SECURITY: CSRF protection via Origin header validation (Finding 9.4)
        if request.method in ("POST", "PUT", "DELETE"):
            origin = request.headers.get("Origin")
            if origin:
                allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
                if allowed_origins_str and allowed_origins_str != "*":
                    allowed_list = [o.strip() for o in allowed_origins_str.split(",")]
                    if origin not in allowed_list:
                        state.track_request_end()
                        return jsonify({"error": "Origin not allowed"}), 403

        return None

    @app.teardown_request
    def teardown_request_tracking(exception=None):
        """Track request completion for graceful shutdown."""
        if request.endpoint not in (
            "monitoring.health",
            "monitoring.liveness",
            "monitoring.readiness",
        ):
            from . import state

            state.track_request_end()

    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # SECURITY: Content Security Policy — restrictive defaults for API
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'none'; "
            "base-uri 'none'"
        )

        # SECURITY: Strict Transport Security (only effective over HTTPS)
        if os.getenv("NATLANGCHAIN_ENABLE_HSTS", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # SECURITY: CORS headers — restrictive by default
        allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")

        if allowed_origins_str == "*":
            # SECURITY: Wildcard CORS is not allowed (Finding 9.2)
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "CORS_ALLOWED_ORIGINS='*' is not supported. Ignoring wildcard."
            )
        elif allowed_origins_str:
            request_origin = request.headers.get("Origin", "")
            allowed_list = [o.strip() for o in allowed_origins_str.split(",")]
            if request_origin in allowed_list:
                response.headers["Access-Control-Allow-Origin"] = request_origin
                response.headers["Vary"] = "Origin"

        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, X-API-Key, Authorization"
        )

        # SECURITY: Additional security headers (Finding 9.3)
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response

    @app.after_request
    def scan_outbound_secrets(response):
        """SECURITY (Audit 2.3): Scan outbound responses for leaked secrets."""
        import logging as _logging

        _secret_logger = _logging.getLogger("natlangchain.secret_scanner")

        try:
            from secret_scanner import (
                _is_scanning_enabled,
                _scan_mode,
                redact_secrets_in_dict,
                scan_response_body,
            )
        except ImportError:
            return response  # Module not available, skip

        if not _is_scanning_enabled():
            return response

        # Only scan JSON responses (most likely to contain leaked secrets)
        content_type = response.content_type or ""
        if "json" not in content_type.lower():
            return response

        # Skip error responses and empty bodies
        if response.status_code >= 400 or not response.data:
            return response

        scan_result = scan_response_body(response.data, content_type)

        if scan_result.has_secrets:
            for detection in scan_result.detections:
                _secret_logger.warning(
                    "SECRET DETECTED in outbound response: pattern=%s location=%s preview=%s",
                    detection["pattern"],
                    detection["location"],
                    detection["preview"],
                )

            mode = _scan_mode()

            if mode == "block":
                # Block the entire response
                _secret_logger.warning(
                    "BLOCKED outbound response due to %d detected secret(s)",
                    len(scan_result.detections),
                )
                blocked = jsonify({
                    "error": "Response blocked by secret scanner",
                    "message": "The response contained potentially sensitive credentials and has been blocked.",
                    "detections_count": len(scan_result.detections),
                })
                blocked.status_code = 500
                return blocked

            else:
                # Redact mode (default): replace secrets in the response body
                import json as _json

                try:
                    data = _json.loads(response.data)
                    redacted_data = redact_secrets_in_dict(data)
                    response.data = _json.dumps(redacted_data).encode("utf-8")
                    _secret_logger.info(
                        "Redacted %d secret(s) from outbound response",
                        len(scan_result.detections),
                    )
                except (ValueError, _json.JSONDecodeError):
                    pass  # If we can't parse, leave as-is (scan already logged)

        return response


def _register_error_handlers(app):
    """Register error handlers for common HTTP errors."""

    @app.errorhandler(400)
    def bad_request(error):
        return (
            jsonify({"error": "Bad request", "message": "Invalid request format or parameters"}),
            400,
        )

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return (
            jsonify(
                {
                    "error": "Request too large",
                    "max_size_mb": app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024),
                }
            ),
            413,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return (
            jsonify(
                {
                    "error": "Invalid parameter value",
                    "message": "One or more parameters have invalid values",
                }
            ),
            400,
        )


def init_managers(api_key=None):
    """
    Initialize all managers and validators.

    Populates the shared ManagerRegistry with initialized instances
    of all optional features (search engine, LLM validators, contracts).

    Args:
        api_key: Anthropic API key for LLM features
    """
    from .utils import managers

    # Initialize semantic search (doesn't require API key)
    try:
        from semantic_search import SemanticSearchEngine

        managers.search_engine = SemanticSearchEngine()
        print("Semantic search engine initialized")
    except Exception as e:
        print(f"Warning: Could not initialize semantic search: {e}")

    # Initialize LLM-based features if API key available
    if api_key and api_key != "your_api_key_here":
        try:
            from validator import HybridValidator, ProofOfUnderstanding

            managers.llm_validator = ProofOfUnderstanding(api_key)
            managers.hybrid_validator = HybridValidator(managers.llm_validator)
            print("LLM validators initialized")
        except Exception as e:
            print(f"Warning: Could not initialize LLM validators: {e}")

        try:
            from contract_matcher import ContractMatcher
            from contract_parser import ContractParser

            managers.contract_parser = ContractParser(api_key)
            managers.contract_matcher = ContractMatcher(api_key)
        except Exception:
            pass

        print("LLM-based features initialized")

    # Initialize cryptographic agent identity (Audit 1.3)
    try:
        from identity import AgentIdentity

        identity = AgentIdentity.from_environment()
        if identity:
            from . import state
            state.agent_identity = identity
            print(f"Agent identity loaded: fingerprint={identity.fingerprint}")
        else:
            print("Agent identity not configured (set NATLANGCHAIN_IDENTITY_ENABLED=true)")
    except ImportError:
        print("Warning: identity module not available")
