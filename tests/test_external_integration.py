"""
Tests for External Boundary-SIEM and Boundary-Daemon Integration.

Tests the integration layer with external systems:
- External daemon client (Unix socket and HTTP)
- Enhanced SIEM client (GraphQL, Kafka, authentication)
- Unified protection with external systems
"""

import sys
import time
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

sys.path.insert(0, "src")


class TestExternalDaemonClient(unittest.TestCase):
    """Test the external daemon client."""

    def setUp(self):
        from external_daemon_client import (
            DaemonDecision,
            DaemonRequest,
            DaemonResponse,
            ExternalDaemonClient,
            OperationType,
        )

        self.ExternalDaemonClient = ExternalDaemonClient
        self.DaemonDecision = DaemonDecision
        self.DaemonRequest = DaemonRequest
        self.DaemonResponse = DaemonResponse
        self.OperationType = OperationType

    def test_daemon_request_serialization(self):
        """Test DaemonRequest serialization."""
        request = self.DaemonRequest(
            operation=self.OperationType.TOOL_GATE,
            context={"requester": "test", "process": "NatLangChain"},
            parameters={"tool": "file_read", "path": "/etc/passwd"},
        )

        data = request.to_dict()
        self.assertEqual(data["operation"], "tool_gate")
        self.assertEqual(data["context"]["requester"], "test")
        self.assertEqual(data["parameters"]["tool"], "file_read")

        json_str = request.to_json()
        self.assertIn("tool_gate", json_str)

    def test_daemon_response_parsing(self):
        """Test DaemonResponse parsing."""
        data = {
            "request_id": "REQ-123",
            "decision": "allow",
            "reasoning": "Tool is allowed in current mode",
            "metadata": {"mode": "restricted"},
        }

        response = self.DaemonResponse.from_dict(data)
        self.assertEqual(response.decision, self.DaemonDecision.ALLOW)
        self.assertEqual(response.reasoning, "Tool is allowed in current mode")

    def test_daemon_response_deny_helper(self):
        """Test DaemonResponse.deny() helper."""
        response = self.DaemonResponse.deny("REQ-123", "Access denied")
        self.assertEqual(response.decision, self.DaemonDecision.DENY)
        self.assertEqual(response.reasoning, "Access denied")

    def test_client_fail_closed_default(self):
        """Test that client defaults to fail-closed."""
        client = self.ExternalDaemonClient(
            socket_path="/nonexistent/socket", http_url=None, fail_open=False
        )

        # Without connection, should return DENY
        response = client.check_tool("dangerous_tool", {}, "test")
        self.assertEqual(response.decision, self.DaemonDecision.DENY)

    def test_client_fail_open_mode(self):
        """Test fail-open mode (dangerous but sometimes needed)."""
        client = self.ExternalDaemonClient(
            socket_path="/nonexistent/socket", http_url=None, fail_open=True
        )

        # With fail_open, should return ALLOW on connection failure
        response = client.check_tool("dangerous_tool", {}, "test")
        self.assertEqual(response.decision, self.DaemonDecision.ALLOW)
        self.assertTrue(response.metadata.get("fallback"))

    @patch("socket.socket")
    def test_unix_socket_connection(self, mock_socket_class):
        """Test Unix socket connection."""
        import os

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # Simulate socket exists
        with patch("os.path.exists", return_value=True):
            client = self.ExternalDaemonClient(socket_path="/var/run/test.sock")
            connected = client.connect()

            # Socket should be created and connected
            mock_socket.connect.assert_called_once()

    @patch("requests.Session")
    def test_http_connection(self, mock_session_class):
        """Test HTTP API connection."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        with patch("os.path.exists", return_value=False):  # No socket
            client = self.ExternalDaemonClient(
                http_url="http://localhost:8080/api/v1", api_key="test-key"
            )
            connected = client.connect()

            # HTTP health check should be called
            mock_session.get.assert_called()

    def test_recall_gate_request(self):
        """Test RecallGate request construction."""
        client = self.ExternalDaemonClient()

        # Mock the internal send method
        mock_response = self.DaemonResponse(
            request_id="test",
            decision=self.DaemonDecision.ALLOW,
            reasoning="Memory access allowed",
            metadata={"mode": "restricted"},
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            response = client.check_recall(
                memory_class=2, purpose="Research", requester="test_agent"
            )

            self.assertEqual(response.decision, self.DaemonDecision.ALLOW)

    def test_tool_gate_request(self):
        """Test ToolGate request construction."""
        client = self.ExternalDaemonClient()

        mock_response = self.DaemonResponse(
            request_id="test",
            decision=self.DaemonDecision.DENY,
            reasoning="Tool blocked in current mode",
            metadata={},
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            response = client.check_tool(
                tool_name="shell_execute",
                parameters={"command": "rm -rf /"},
                requester="test_agent",
            )

            self.assertEqual(response.decision, self.DaemonDecision.DENY)

    def test_mode_operations(self):
        """Test mode query and set operations."""
        client = self.ExternalDaemonClient()

        # Test mode query
        mock_response = self.DaemonResponse(
            request_id="test",
            decision=self.DaemonDecision.ALLOW,
            reasoning="Mode retrieved",
            metadata={"mode": "airgap"},
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            response = client.get_mode()
            self.assertEqual(response.metadata["mode"], "airgap")

    def test_ceremony_workflow(self):
        """Test ceremony request and confirmation."""
        client = self.ExternalDaemonClient()

        # Request ceremony
        ceremony_response = self.DaemonResponse(
            request_id="test",
            decision=self.DaemonDecision.CONDITIONAL,
            reasoning="Ceremony required",
            metadata={"ceremony_id": "CEREMONY-123"},
            ceremony_steps=["Confirm identity", "Enter code", "Wait for cooldown"],
            deadline="2025-01-02T12:00:00Z",
        )

        with patch.object(client, "_send_request", return_value=ceremony_response):
            response = client.request_ceremony(
                ceremony_type="mode_change",
                reason="Maintenance required",
                requester="admin",
                target="open",
            )

            self.assertEqual(response.decision, self.DaemonDecision.CONDITIONAL)
            self.assertEqual(len(response.ceremony_steps), 3)

    def test_health_check(self):
        """Test health check functionality."""
        client = self.ExternalDaemonClient()

        mock_response = self.DaemonResponse(
            request_id="health",
            decision=self.DaemonDecision.ALLOW,
            reasoning="Healthy",
            metadata={"version": "1.0.0", "uptime": 12345},
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            with patch.object(client, "_connected", True):
                health = client.health_check()

                self.assertTrue(health["healthy"])
                self.assertTrue(health["connected"])


class TestEnhancedSIEMClient(unittest.TestCase):
    """Test the enhanced SIEM client."""

    def setUp(self):
        from boundary_siem import (
            AuthMethod,
            EnhancedSIEMClient,
            SIEMAuthConfig,
            SIEMEvent,
            SIEMEventCategory,
            SIEMSeverity,
        )

        self.EnhancedSIEMClient = EnhancedSIEMClient
        self.SIEMAuthConfig = SIEMAuthConfig
        self.AuthMethod = AuthMethod
        self.SIEMEvent = SIEMEvent
        self.SIEMEventCategory = SIEMEventCategory
        self.SIEMSeverity = SIEMSeverity

    def test_auth_config_from_env(self):
        """Test SIEMAuthConfig loading from environment."""
        with patch.dict(
            "os.environ",
            {
                "BOUNDARY_SIEM_AUTH_METHOD": "oauth2",
                "BOUNDARY_SIEM_API_KEY": "test-key",
                "BOUNDARY_SIEM_OAUTH2_CLIENT_ID": "client-123",
                "BOUNDARY_SIEM_OAUTH2_CLIENT_SECRET": "secret-xyz",
                "BOUNDARY_SIEM_OAUTH2_TOKEN_URL": "https://auth.example.com/token",
            },
        ):
            config = self.SIEMAuthConfig.from_env()

            self.assertEqual(config.method, self.AuthMethod.OAUTH2)
            self.assertEqual(config.oauth2_client_id, "client-123")
            self.assertEqual(config.oauth2_token_url, "https://auth.example.com/token")

    def test_bearer_token_auth(self):
        """Test bearer token authentication."""
        auth_config = self.SIEMAuthConfig(
            method=self.AuthMethod.BEARER_TOKEN, token="test-token-123"
        )

        with patch("requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session.headers = {}
            mock_session_class.return_value = mock_session

            client = self.EnhancedSIEMClient(
                siem_url="https://siem.example.com", auth_config=auth_config
            )

            # Check that authorization header is set
            self.assertIn("Authorization", mock_session.headers)
            self.assertEqual(mock_session.headers["Authorization"], "Bearer test-token-123")

    def test_event_validation(self):
        """Test event schema validation."""
        with patch("requests.Session"):
            client = self.EnhancedSIEMClient(
                siem_url="https://siem.example.com", validate_schema=True
            )

            # Valid event
            valid_event = self.SIEMEvent(
                category=self.SIEMEventCategory.CHAIN_ENTRY_CREATED,
                action="create",
                outcome="success",
                severity=self.SIEMSeverity.INFORMATIONAL,
                message="Test event",
            )

            errors = client._validate_event(valid_event)
            self.assertEqual(len(errors), 0)

            # Event with invalid outcome
            invalid_event = self.SIEMEvent(
                category=self.SIEMEventCategory.CHAIN_ENTRY_CREATED,
                action="create",
                outcome="maybe",  # Invalid
                severity=self.SIEMSeverity.INFORMATIONAL,
                message="Test event",
            )

            errors = client._validate_event(invalid_event)
            self.assertGreater(len(errors), 0)

    @patch("requests.Session")
    def test_graphql_query(self, mock_session_class):
        """Test GraphQL query execution."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"events": [{"id": "1", "action": "create", "severity": 3}]}
        }
        mock_session.post.return_value = mock_response
        mock_session.headers = {}
        mock_session_class.return_value = mock_session

        client = self.EnhancedSIEMClient(siem_url="https://siem.example.com")

        result = client.graphql_query(
            """
            query GetEvents($limit: Int!) {
                events(limit: $limit) {
                    id
                    action
                    severity
                }
            }
        """,
            {"limit": 10},
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(result["data"]["events"]), 1)

    @patch("requests.Session")
    def test_bulk_event_send(self, mock_session_class):
        """Test bulk event sending."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response
        mock_session.headers = {}
        mock_session_class.return_value = mock_session

        client = self.EnhancedSIEMClient(siem_url="https://siem.example.com")

        events = [
            self.SIEMEvent(
                category=self.SIEMEventCategory.CHAIN_ENTRY_CREATED,
                action="create",
                outcome="success",
                severity=self.SIEMSeverity.INFORMATIONAL,
                message=f"Event {i}",
            )
            for i in range(5)
        ]

        result = client.send_events_bulk(events, sync=True)

        self.assertEqual(result["success"], 5)
        self.assertEqual(result["failed"], 0)

    @patch("requests.Session")
    def test_detection_rules_api(self, mock_session_class):
        """Test detection rules retrieval."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rules": [
                {"id": "1", "name": "Prompt Injection", "severity": 8},
                {"id": "2", "name": "Data Exfiltration", "severity": 9},
            ]
        }
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        mock_session_class.return_value = mock_session

        client = self.EnhancedSIEMClient(siem_url="https://siem.example.com")

        rules = client.get_detection_rules()

        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["name"], "Prompt Injection")


class TestUnifiedProtectionWithExternalSystems(unittest.TestCase):
    """Test BoundaryProtection with external integrations."""

    def setUp(self):
        from boundary_daemon import EnforcementMode
        from boundary_modes import BoundaryMode
        from boundary_protection import (
            BoundaryProtection,
            ProtectionConfig,
            ProtectionResult,
        )

        self.BoundaryProtection = BoundaryProtection
        self.ProtectionConfig = ProtectionConfig
        self.ProtectionResult = ProtectionResult
        self.BoundaryMode = BoundaryMode
        self.EnforcementMode = EnforcementMode

    def test_config_external_daemon_settings(self):
        """Test configuration for external daemon."""
        with patch.dict(
            "os.environ",
            {
                "BOUNDARY_ENABLE_EXTERNAL_DAEMON": "true",
                "BOUNDARY_DAEMON_SOCKET": "/var/run/boundary.sock",
                "BOUNDARY_DAEMON_URL": "http://localhost:8080/api/v1",
                "BOUNDARY_DAEMON_TIMEOUT": "10.0",
                "BOUNDARY_DAEMON_FAIL_OPEN": "false",
                "BOUNDARY_SYNC_MODE_WITH_DAEMON": "true",
            },
        ):
            config = self.ProtectionConfig.from_env()

            self.assertTrue(config.enable_external_daemon)
            self.assertEqual(config.external_daemon_socket, "/var/run/boundary.sock")
            self.assertEqual(config.external_daemon_timeout, 10.0)
            self.assertFalse(config.external_daemon_fail_open)
            self.assertTrue(config.sync_mode_with_daemon)

    def test_config_enhanced_siem_settings(self):
        """Test configuration for enhanced SIEM."""
        with patch.dict(
            "os.environ",
            {
                "BOUNDARY_USE_ENHANCED_SIEM": "true",
                "BOUNDARY_SIEM_URL": "https://siem.example.com",
                "BOUNDARY_SIEM_KAFKA_BROKERS": "kafka1:9092,kafka2:9092",
                "BOUNDARY_SIEM_KAFKA_TOPIC": "security-events",
                "BOUNDARY_SIEM_VALIDATE_SCHEMA": "true",
            },
        ):
            config = self.ProtectionConfig.from_env()

            self.assertTrue(config.use_enhanced_siem)
            self.assertEqual(config.siem_url, "https://siem.example.com")
            self.assertEqual(config.siem_kafka_brokers, ["kafka1:9092", "kafka2:9092"])
            self.assertEqual(config.siem_kafka_topic, "security-events")

    @patch("boundary_protection.init_siem_client")
    @patch("boundary_protection.init_mode_manager")
    @patch("boundary_protection.init_agent_security")
    @patch("boundary_protection.SecurityEnforcementManager")
    def test_protection_without_external_daemon(
        self, mock_enforcement, mock_agent, mock_mode, mock_siem
    ):
        """Test protection works without external daemon."""
        config = self.ProtectionConfig(enable_external_daemon=False)

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)
            protection.external_daemon = None
            protection.modes = MagicMock()
            protection.modes.is_tool_allowed.return_value = True

            # External tool gate should fall back to local check
            result = protection.check_external_tool_gate("test_tool", {})

            self.assertTrue(result.allowed)
            self.assertEqual(result.details["source"], "local")

    @patch("boundary_protection.init_daemon_client")
    @patch("boundary_protection.init_siem_client")
    @patch("boundary_protection.init_mode_manager")
    @patch("boundary_protection.init_agent_security")
    @patch("boundary_protection.SecurityEnforcementManager")
    def test_protection_with_external_daemon(
        self, mock_enforcement, mock_agent, mock_mode, mock_siem, mock_daemon
    ):
        """Test protection with external daemon enabled."""
        from external_daemon_client import DaemonDecision, DaemonResponse

        mock_daemon_client = MagicMock()
        mock_daemon_client.check_tool.return_value = DaemonResponse(
            request_id="test",
            decision=DaemonDecision.DENY,
            reasoning="Tool blocked by policy",
            metadata={},
        )
        mock_daemon.return_value = mock_daemon_client

        config = self.ProtectionConfig(enable_external_daemon=True)

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)
            protection.external_daemon = mock_daemon_client
            protection.modes = MagicMock()

            result = protection.check_external_tool_gate("dangerous_tool", {})

            self.assertFalse(result.allowed)
            self.assertEqual(result.details["source"], "external_daemon")
            self.assertEqual(result.details["decision"], "deny")

    @patch("boundary_protection.init_enhanced_siem_client")
    @patch("boundary_protection.init_mode_manager")
    @patch("boundary_protection.init_agent_security")
    @patch("boundary_protection.SecurityEnforcementManager")
    def test_graphql_query_with_enhanced_siem(
        self, mock_enforcement, mock_agent, mock_mode, mock_enhanced_siem
    ):
        """Test GraphQL queries work with enhanced SIEM."""
        mock_siem_client = MagicMock()
        mock_siem_client.graphql_query.return_value = {"data": {"events": []}}
        mock_enhanced_siem.return_value = mock_siem_client

        config = self.ProtectionConfig(use_enhanced_siem=True, siem_url="https://siem.example.com")

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)
            protection.siem = mock_siem_client
            protection._using_enhanced_siem = True

            result = protection.graphql_query("query { events { id } }")

            self.assertIsNotNone(result)
            mock_siem_client.graphql_query.assert_called_once()

    def test_external_daemon_status_not_configured(self):
        """Test external daemon status when not configured."""
        config = self.ProtectionConfig(enable_external_daemon=False)

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)
            protection.external_daemon = None

            status = protection.get_external_daemon_status()

            self.assertFalse(status["enabled"])
            self.assertFalse(status["connected"])


class TestModeSynchronization(unittest.TestCase):
    """Test mode synchronization with external daemon."""

    def setUp(self):
        from boundary_modes import BoundaryMode
        from boundary_protection import BoundaryProtection, ProtectionConfig

        self.BoundaryProtection = BoundaryProtection
        self.ProtectionConfig = ProtectionConfig
        self.BoundaryMode = BoundaryMode

    @patch("boundary_protection.init_daemon_client")
    @patch("boundary_protection.init_siem_client")
    @patch("boundary_protection.init_mode_manager")
    @patch("boundary_protection.init_agent_security")
    @patch("boundary_protection.SecurityEnforcementManager")
    def test_mode_sync_from_daemon(
        self, mock_enforcement, mock_agent, mock_mode_manager, mock_siem, mock_daemon
    ):
        """Test mode synchronization from external daemon."""
        from external_daemon_client import DaemonDecision, DaemonResponse

        mock_daemon_client = MagicMock()
        mock_daemon_client.get_mode.return_value = DaemonResponse(
            request_id="test",
            decision=DaemonDecision.ALLOW,
            reasoning="Mode retrieved",
            metadata={"mode": "airgap"},
        )
        mock_daemon.return_value = mock_daemon_client

        mock_mode = MagicMock()
        mock_mode_manager.return_value = mock_mode

        config = self.ProtectionConfig(
            enable_external_daemon=True,
            sync_mode_with_daemon=True,
            initial_mode=self.BoundaryMode.RESTRICTED,
        )

        # Create protection - this should trigger sync
        with patch.object(self.BoundaryProtection, "_sync_mode_from_daemon") as mock_sync:
            protection = self.BoundaryProtection(config)
            # Sync would be called during init


class TestEventForwarding(unittest.TestCase):
    """Test event forwarding between systems."""

    def setUp(self):
        from boundary_protection import BoundaryProtection, ProtectionConfig

        self.BoundaryProtection = BoundaryProtection
        self.ProtectionConfig = ProtectionConfig

    def test_forward_event_to_daemon(self):
        """Test event forwarding to external daemon."""
        from external_daemon_client import DaemonDecision, DaemonResponse

        config = self.ProtectionConfig(enable_external_daemon=True)

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)

            mock_daemon = MagicMock()
            mock_daemon.log_event.return_value = DaemonResponse(
                request_id="test",
                decision=DaemonDecision.ALLOW,
                reasoning="Event logged",
                metadata={},
            )
            protection.external_daemon = mock_daemon

            result = protection.forward_event_to_daemon(
                event_type="policy_decision",
                event_data={"action": "block", "reason": "sensitive data"},
                severity=7,
            )

            self.assertTrue(result)
            mock_daemon.log_event.assert_called_once()

    def test_forward_event_without_daemon(self):
        """Test event forwarding when daemon not configured."""
        config = self.ProtectionConfig(enable_external_daemon=False)

        with patch.object(self.BoundaryProtection, "_init_components"):
            protection = self.BoundaryProtection(config)
            protection.external_daemon = None

            result = protection.forward_event_to_daemon(
                event_type="test", event_data={}, severity=3
            )

            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
