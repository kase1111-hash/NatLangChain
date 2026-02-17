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
            response.headers["Access-Control-Allow-Origin"] = "*"
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
