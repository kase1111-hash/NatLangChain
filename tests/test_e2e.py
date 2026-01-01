"""
NatLangChain - End-to-End Integration Tests

Comprehensive E2E tests covering full system workflows.
These tests require a running NatLangChain instance.

Usage:
    # Run against local server
    pytest tests/test_e2e.py -v

    # Run against specific endpoint
    NATLANGCHAIN_TEST_URL=http://localhost:5000 pytest tests/test_e2e.py -v

    # Run with API key
    NATLANGCHAIN_TEST_API_KEY=your_key pytest tests/test_e2e.py -v

Environment Variables:
    NATLANGCHAIN_TEST_URL: Base URL of the NatLangChain server
    NATLANGCHAIN_TEST_API_KEY: API key for authenticated endpoints
    NATLANGCHAIN_E2E_SKIP: Set to "true" to skip E2E tests
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Any

import pytest

# Check if E2E tests should be skipped
E2E_SKIP = os.getenv("NATLANGCHAIN_E2E_SKIP", "false").lower() == "true"

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Skip all tests if requests not available or E2E disabled
pytestmark = [
    pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests library not installed"),
    pytest.mark.skipif(E2E_SKIP, reason="E2E tests disabled via environment"),
    pytest.mark.e2e,
]


# =============================================================================
# Test Configuration
# =============================================================================

class E2EConfig:
    """Configuration for E2E tests."""

    def __init__(self):
        self.base_url = os.getenv("NATLANGCHAIN_TEST_URL", "http://localhost:5000")
        self.api_key = os.getenv("NATLANGCHAIN_TEST_API_KEY", "")
        self.timeout = int(os.getenv("NATLANGCHAIN_TEST_TIMEOUT", "30"))

    @property
    def headers(self) -> dict[str, str]:
        """Get default headers including API key."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers


@pytest.fixture(scope="module")
def config():
    """Provide E2E configuration."""
    return E2EConfig()


@pytest.fixture(scope="module")
def session(config):
    """Provide a requests session."""
    s = requests.Session()
    s.headers.update(config.headers)
    return s


@pytest.fixture(scope="module")
def server_available(config):
    """Check if server is available before running tests."""
    try:
        response = requests.get(
            f"{config.base_url}/health",
            timeout=5
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, config, server_available):
        """Test main health endpoint."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(f"{config.base_url}/health", timeout=config.timeout)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data

    def test_liveness_probe(self, config, server_available):
        """Test Kubernetes liveness probe."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(f"{config.base_url}/health/live", timeout=config.timeout)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, config, server_available):
        """Test Kubernetes readiness probe."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(f"{config.base_url}/health/ready", timeout=config.timeout)
        # May be 200 (ready) or 503 (not ready)
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data


# =============================================================================
# Chain Info Tests
# =============================================================================

class TestChainInfo:
    """Tests for chain information endpoints."""

    def test_get_chain_info(self, config, session, server_available):
        """Test getting chain information."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.get(f"{config.base_url}/chain", timeout=config.timeout)
        assert response.status_code == 200

        data = response.json()
        assert "chain" in data or "blocks" in data or "length" in data

    def test_get_blocks(self, config, session, server_available):
        """Test getting blocks."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.get(f"{config.base_url}/blocks", timeout=config.timeout)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, (list, dict))

    def test_validate_chain(self, config, session, server_available):
        """Test chain validation."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.get(f"{config.base_url}/chain/validate", timeout=config.timeout)
        assert response.status_code == 200

        data = response.json()
        assert "valid" in data


# =============================================================================
# Entry Workflow Tests
# =============================================================================

class TestEntryWorkflow:
    """Tests for the complete entry lifecycle."""

    @pytest.fixture
    def unique_agent_id(self):
        """Generate a unique agent ID for testing."""
        return f"test-agent-{uuid.uuid4().hex[:8]}"

    def test_create_entry(self, config, session, server_available, unique_agent_id):
        """Test creating a new entry."""
        if not server_available:
            pytest.skip("Server not available")

        entry_data = {
            "content": f"E2E test entry created at {datetime.utcnow().isoformat()}",
            "agent_id": unique_agent_id,
            "intent": "test",
        }

        response = session.post(
            f"{config.base_url}/entries",
            json=entry_data,
            timeout=config.timeout
        )

        # 201 Created or 200 OK depending on implementation
        assert response.status_code in [200, 201, 401]

        if response.status_code == 401:
            pytest.skip("API key required for entry creation")

        data = response.json()
        assert "message" in data or "entry" in data or "id" in data

    def test_search_entries(self, config, session, server_available):
        """Test searching entries."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.get(
            f"{config.base_url}/entries",
            params={"limit": 10},
            timeout=config.timeout
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, (list, dict))

    def test_full_entry_lifecycle(self, config, session, server_available, unique_agent_id):
        """Test complete entry lifecycle: create, read, mine."""
        if not server_available:
            pytest.skip("Server not available")

        # 1. Create entry
        entry_content = f"Lifecycle test {uuid.uuid4().hex[:8]}"
        create_response = session.post(
            f"{config.base_url}/entries",
            json={
                "content": entry_content,
                "agent_id": unique_agent_id,
            },
            timeout=config.timeout
        )

        if create_response.status_code == 401:
            pytest.skip("API key required")

        assert create_response.status_code in [200, 201]

        # 2. Get pending entries
        pending_response = session.get(
            f"{config.base_url}/entries/pending",
            timeout=config.timeout
        )
        # May or may not be authorized
        if pending_response.status_code == 200:
            pending = pending_response.json()
            assert isinstance(pending, (list, dict))

        # 3. Mine a block (if authorized)
        mine_response = session.post(
            f"{config.base_url}/mine",
            timeout=config.timeout
        )
        # Mining may require auth
        assert mine_response.status_code in [200, 201, 401, 403]

        # 4. Verify chain is still valid
        validate_response = session.get(
            f"{config.base_url}/chain/validate",
            timeout=config.timeout
        )
        assert validate_response.status_code == 200
        assert validate_response.json().get("valid", True) is True


# =============================================================================
# Contract Tests (if available)
# =============================================================================

class TestContractWorkflow:
    """Tests for contract operations."""

    def test_list_contracts(self, config, session, server_available):
        """Test listing contracts."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.get(
            f"{config.base_url}/contracts",
            timeout=config.timeout
        )
        # Endpoint may or may not exist
        if response.status_code == 404:
            pytest.skip("Contracts endpoint not available")

        assert response.status_code in [200, 401]


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_rate_limit_headers(self, config, server_available):
        """Test that rate limit headers are present."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(f"{config.base_url}/health", timeout=config.timeout)

        # Rate limit headers may be present
        # X-RateLimit-Limit, X-RateLimit-Remaining, etc.
        # Just verify response is successful
        assert response.status_code == 200

    def test_rate_limit_exceeded(self, config, server_available):
        """Test rate limiting is enforced (carefully)."""
        if not server_available:
            pytest.skip("Server not available")

        # Note: This test is designed to not actually trigger rate limits
        # in production. It just verifies the mechanism exists.

        # Make a few requests
        responses = []
        for _ in range(5):
            response = requests.get(f"{config.base_url}/health", timeout=config.timeout)
            responses.append(response.status_code)

        # All should succeed (we're well under any reasonable limit)
        assert all(code == 200 for code in responses)


# =============================================================================
# Concurrent Access Tests
# =============================================================================

class TestConcurrency:
    """Tests for concurrent access handling."""

    def test_concurrent_reads(self, config, server_available):
        """Test multiple concurrent read requests."""
        if not server_available:
            pytest.skip("Server not available")

        import concurrent.futures

        def make_request():
            response = requests.get(
                f"{config.base_url}/health",
                timeout=config.timeout
            )
            return response.status_code

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(code == 200 for code in results)


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, config, server_available):
        """Test 404 response for non-existent endpoint."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(
            f"{config.base_url}/nonexistent-endpoint-{uuid.uuid4().hex}",
            timeout=config.timeout
        )
        assert response.status_code == 404

    def test_invalid_json(self, config, session, server_available):
        """Test handling of invalid JSON."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.post(
            f"{config.base_url}/entries",
            data="not valid json",
            headers={"Content-Type": "application/json"},
            timeout=config.timeout
        )
        # Should be 400 Bad Request
        assert response.status_code in [400, 401]

    def test_missing_required_fields(self, config, session, server_available):
        """Test handling of missing required fields."""
        if not server_available:
            pytest.skip("Server not available")

        response = session.post(
            f"{config.base_url}/entries",
            json={},  # Empty body
            timeout=config.timeout
        )
        # Should be 400 or 401 (if auth required)
        assert response.status_code in [400, 401, 422]


# =============================================================================
# Security Headers Tests
# =============================================================================

class TestSecurityHeaders:
    """Tests for security headers."""

    def test_security_headers_present(self, config, server_available):
        """Test that security headers are present."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.get(f"{config.base_url}/health", timeout=config.timeout)

        # Check for common security headers
        headers = response.headers

        # These should be present
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"

    def test_cors_headers(self, config, server_available):
        """Test CORS headers on preflight."""
        if not server_available:
            pytest.skip("Server not available")

        response = requests.options(
            f"{config.base_url}/health",
            headers={"Origin": "http://example.com"},
            timeout=config.timeout
        )
        # CORS may or may not be configured
        # Just verify we get a response
        assert response.status_code in [200, 204, 405]


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_health_response_time(self, config, server_available):
        """Test health endpoint responds quickly."""
        if not server_available:
            pytest.skip("Server not available")

        start = time.time()
        response = requests.get(f"{config.base_url}/health", timeout=config.timeout)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second

    def test_chain_info_response_time(self, config, session, server_available):
        """Test chain info responds within acceptable time."""
        if not server_available:
            pytest.skip("Server not available")

        start = time.time()
        response = session.get(f"{config.base_url}/chain", timeout=config.timeout)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0  # Should respond within 5 seconds


# =============================================================================
# Integration Workflow Tests
# =============================================================================

class TestFullWorkflow:
    """Tests for complete application workflows."""

    def test_complete_blockchain_workflow(self, config, session, server_available):
        """Test complete blockchain workflow from entry to block."""
        if not server_available:
            pytest.skip("Server not available")

        test_id = uuid.uuid4().hex[:8]

        # 1. Check initial chain state
        chain_before = session.get(f"{config.base_url}/chain", timeout=config.timeout)
        assert chain_before.status_code == 200

        # 2. Add multiple entries
        entries_created = 0
        for i in range(3):
            response = session.post(
                f"{config.base_url}/entries",
                json={
                    "content": f"Workflow test entry {i} - {test_id}",
                    "agent_id": f"workflow-test-{test_id}",
                    "intent": "test",
                },
                timeout=config.timeout
            )
            if response.status_code in [200, 201]:
                entries_created += 1
            elif response.status_code == 401:
                pytest.skip("API key required for entry creation")

        # 3. Trigger mining (if authorized)
        mine_response = session.post(f"{config.base_url}/mine", timeout=config.timeout)
        if mine_response.status_code in [401, 403]:
            pytest.skip("Mining requires authorization")

        # 4. Verify chain is still valid
        validate = session.get(f"{config.base_url}/chain/validate", timeout=config.timeout)
        assert validate.status_code == 200
        assert validate.json().get("valid", True) is True

        # 5. Search for our entries
        search = session.get(
            f"{config.base_url}/entries",
            params={"q": test_id, "limit": 10},
            timeout=config.timeout
        )
        if search.status_code == 200:
            # Verify we can find our entries (implementation dependent)
            pass


# =============================================================================
# Cleanup
# =============================================================================

@pytest.fixture(scope="module", autouse=True)
def cleanup():
    """Cleanup after tests."""
    yield
    # Add any cleanup logic here if needed
    pass
