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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set up test environment before any imports
os.environ["NATLANGCHAIN_API_KEY"] = "test-api-key-12345"
os.environ["NATLANGCHAIN_REQUIRE_AUTH"] = "false"
os.environ["RATE_LIMIT_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW"] = "1"


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
        enable_quality_checks=False,
    )


@pytest.fixture(scope="function")
def flask_app(fresh_blockchain):
    """Create Flask test app with fresh blockchain for each test."""
    from api import create_app, state

    # Replace blockchain with fresh instance
    state.blockchain = fresh_blockchain

    app = create_app(testing=True)

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
    return {"Content-Type": "application/json", "X-API-Key": "test-api-key-12345"}
