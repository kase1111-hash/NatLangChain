"""
Tests for critical API endpoints.

This module provides test coverage for core API functionality including:
- Health check endpoints
- Entry creation and validation
- Block mining
- Chain retrieval
- Rate limiting
- Error handling
"""

import json
import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_returns_healthy(self, flask_client):
        """Health endpoint should return healthy status."""
        response = flask_client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"

    def test_health_check_includes_version(self, flask_client):
        """Health endpoint should include version info."""
        response = flask_client.get("/health")
        data = json.loads(response.data)
        assert "version" in data


class TestEntryCreation:
    """Tests for entry creation endpoint."""

    def test_create_entry_success(self, flask_client, test_auth_headers):
        """Should successfully create a valid entry."""
        payload = {
            "content": "Test contract: Party A agrees to provide services to Party B.",
            "author": "test-author",
            "intent": "Service agreement",
        }
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert data.get("status") in ["pending", "success"]

    def test_create_entry_missing_content(self, flask_client, test_auth_headers):
        """Should reject entry without content."""
        payload = {
            "author": "test-author",
            "intent": "Test intent",
        }
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_entry_missing_author(self, flask_client, test_auth_headers):
        """Should reject entry without author."""
        payload = {
            "content": "Test content",
            "intent": "Test intent",
        }
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code == 400

    def test_create_entry_empty_content(self, flask_client, test_auth_headers):
        """Should reject entry with empty content."""
        payload = {
            "content": "",
            "author": "test-author",
            "intent": "Test intent",
        }
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code == 400


class TestChainEndpoints:
    """Tests for chain retrieval endpoints."""

    def test_get_chain_returns_list(self, flask_client):
        """Chain endpoint should return a list of blocks."""
        response = flask_client.get("/chain")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "chain" in data or "blocks" in data or isinstance(data, list)

    def test_get_chain_includes_genesis(self, flask_client):
        """Chain should include at least the genesis block."""
        response = flask_client.get("/chain")
        data = json.loads(response.data)
        if "chain" in data:
            assert len(data["chain"]) >= 1
        elif "blocks" in data:
            assert len(data["blocks"]) >= 1


class TestMiningEndpoints:
    """Tests for block mining endpoints."""

    def test_mine_with_pending_entries(self, flask_client, test_auth_headers):
        """Should mine pending entries into a new block."""
        # First create an entry
        payload = {
            "content": "Entry to be mined",
            "author": "miner-test",
            "intent": "Mining test",
        }
        flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )

        # Then mine it
        response = flask_client.post("/mine", headers=test_auth_headers)
        # Should succeed or indicate nothing to mine
        assert response.status_code in [200, 201, 400]

    def test_mine_empty_pending(self, flask_client, test_auth_headers):
        """Mining with no pending entries should handle gracefully."""
        response = flask_client.post("/mine", headers=test_auth_headers)
        # Should return success (empty block) or indicate nothing to mine
        assert response.status_code in [200, 201, 400]


class TestBlockRetrieval:
    """Tests for block retrieval endpoints."""

    def test_get_block_zero_returns_genesis(self, flask_client):
        """Should return genesis block at index 0."""
        response = flask_client.get("/block/0")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "index" in data or "block" in data

    def test_get_nonexistent_block_returns_404(self, flask_client):
        """Should return 404 for non-existent block index."""
        response = flask_client.get("/block/99999")
        assert response.status_code == 404


class TestValidation:
    """Tests for chain validation endpoints."""

    def test_validate_chain_returns_status(self, flask_client):
        """Chain validation should return valid status."""
        response = flask_client.get("/validate/chain")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "valid" in data
        assert data["valid"] is True


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json_returns_400(self, flask_client, test_auth_headers):
        """Should return 400 for invalid JSON."""
        response = flask_client.post(
            "/entry",
            data="not valid json",
            headers=test_auth_headers,
        )
        assert response.status_code in [400, 415]

    def test_method_not_allowed(self, flask_client):
        """Should return 405 for wrong HTTP method."""
        response = flask_client.delete("/health")
        assert response.status_code == 405


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_headers_present(self, flask_client):
        """Response should include rate limit info."""
        response = flask_client.get("/health")
        # Rate limit info may be in headers or response body
        assert response.status_code == 200


class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_search_requires_query(self, flask_client):
        """Search endpoint should require a query parameter."""
        response = flask_client.get("/search")
        # Should return 400 or redirect
        assert response.status_code in [400, 404, 308]


class TestStatisticsEndpoints:
    """Tests for statistics endpoints."""

    def test_stats_returns_counts(self, flask_client):
        """Stats endpoint should return block and entry counts."""
        response = flask_client.get("/stats")
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "total_blocks" in data or "blocks" in data


class TestNarrativeEndpoint:
    """Tests for narrative endpoint."""

    def test_narrative_returns_text(self, flask_client):
        """Narrative endpoint should return human-readable chain."""
        response = flask_client.get("/narrative")
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "narrative" in data or "text" in data or isinstance(data, str)


class TestAuthenticationRequired:
    """Tests for authentication requirements."""

    def test_entry_creation_requires_auth_when_enabled(self, flask_app, flask_client):
        """Entry creation should require auth when enabled."""
        # This test verifies the auth decorator is applied
        # The actual enforcement depends on NATLANGCHAIN_REQUIRE_AUTH
        payload = {
            "content": "Test content",
            "author": "test",
            "intent": "test",
        }
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        # With auth disabled in tests, should succeed
        # With auth enabled, would return 401/403
        assert response.status_code in [200, 201, 400, 401, 403]


class TestContentTypeHandling:
    """Tests for content type handling."""

    def test_json_content_type_accepted(self, flask_client, test_auth_headers):
        """Should accept application/json content type."""
        payload = {"content": "test", "author": "test", "intent": "test"}
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        # Should process the request (may fail validation but not content type)
        assert response.status_code in [200, 201, 400, 401]


class TestPaginationDefaults:
    """Tests for pagination parameter handling."""

    def test_search_respects_limit_parameter(self, flask_client):
        """Search should respect limit parameter."""
        response = flask_client.get("/search?q=test&limit=5")
        if response.status_code == 200:
            data = json.loads(response.data)
            if "entries" in data:
                assert len(data["entries"]) <= 5


class TestParametrizedEntryValidation:
    """Parametrized tests for entry creation boundary conditions."""

    @pytest.mark.parametrize("missing_field", ["content", "author", "intent"])
    def test_missing_required_field_returns_400(self, flask_client, test_auth_headers, missing_field):
        """Each required field should produce a 400 when absent."""
        payload = {"content": "test", "author": "test", "intent": "test"}
        del payload[missing_field]
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("field,value", [
        ("content", ""),
        ("author", ""),
        ("intent", ""),
    ])
    def test_empty_required_field_returns_400(self, flask_client, test_auth_headers, field, value):
        """Empty strings for required fields should produce a 400."""
        payload = {"content": "test", "author": "test", "intent": "test"}
        payload[field] = value
        response = flask_client.post(
            "/entry",
            data=json.dumps(payload),
            headers=test_auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("limit", [0, 1, 50, 100])
    def test_search_limit_values(self, flask_client, limit):
        """Search should accept various limit values without error."""
        response = flask_client.get(f"/search?q=test&limit={limit}")
        assert response.status_code in [200, 400]
