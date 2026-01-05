"""
Pytest configuration and shared fixtures for NatLangChain tests.

This module provides shared fixtures and test configuration including:
- Flask app setup with test configuration
- Blockchain instances with validation disabled
- API authentication headers
- Rate limiting reset between tests
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up test environment before any imports
os.environ["NATLANGCHAIN_API_KEY"] = "test-api-key-12345"
os.environ["NATLANGCHAIN_REQUIRE_AUTH"] = "false"
os.environ["RATE_LIMIT_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW"] = "1"


# Store module for reset
_api_module = None


def get_api_module():
    """Get or create the API module singleton."""
    global _api_module
    if _api_module is None:
        import importlib.util
        api_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'api.py')
        spec = importlib.util.spec_from_file_location("api_main", api_path)
        _api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_api_module)
    return _api_module


@pytest.fixture(scope="session")
def api_module():
    """Provide the API module (session-scoped for efficiency)."""
    return get_api_module()


@pytest.fixture(scope="function")
def fresh_blockchain():
    """Create a fresh blockchain with validation disabled."""
    from blockchain import NatLangChain
    return NatLangChain(
        require_validation=False,
        enable_deduplication=False,
        enable_rate_limiting=False,
        enable_timestamp_validation=False,
        enable_metadata_sanitization=False,
        enable_asset_tracking=False,
        enable_quality_checks=False
    )


@pytest.fixture(scope="function")
def flask_app(api_module, fresh_blockchain):
    """Create Flask test app with fresh blockchain for each test."""
    app = api_module.app
    app.config['TESTING'] = True

    # Replace blockchain with fresh instance
    api_module.blockchain = fresh_blockchain

    # Register blueprints if not already registered
    try:
        from api import ALL_BLUEPRINTS
        for blueprint, url_prefix in ALL_BLUEPRINTS:
            # Only register if not already registered
            if blueprint.name not in app.blueprints:
                app.register_blueprint(blueprint, url_prefix=url_prefix)
    except ImportError:
        pass

    # Reset rate limit store
    try:
        from api.utils import rate_limit_store
        rate_limit_store.clear()
    except (ImportError, AttributeError):
        pass

    return app


@pytest.fixture(scope="function")
def flask_client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def test_auth_headers():
    """Headers for authenticated requests."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": "test-api-key-12345"
    }
