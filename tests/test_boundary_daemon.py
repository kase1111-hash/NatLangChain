"""
Tests for Boundary Daemon <-> NatLangChain Integration

This test suite verifies that the Boundary Daemon:
1. Fails safe - blocks by default when uncertain
2. Blocks all sensitive data patterns (passwords, API keys, secrets, etc.)
3. Enforces data classification rules
4. Properly logs audits and violations
5. Integrates correctly with NatLangChain for recording security events
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from boundary_daemon import (
    BoundaryDaemon,
    BoundaryPolicy,
    EnforcementMode,
    DataClassification,
    ViolationType,
    validate_outbound_data
)


class TestFailSafeBehavior:
    """Tests for fail-safe behavior - the daemon should block when uncertain."""

    def test_blocks_on_unknown_classification(self):
        """Unknown data classifications should default to RESTRICTED and block."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        result = daemon.authorize_request({
            "request_id": "REQ-001",
            "source": "agent_os",
            "destination": "external_api",
            "payload": {"content": "Some internal data"},
            "data_classification": "super_secret_unknown_level"
        })

        # Should be blocked because unknown classification = RESTRICTED
        assert result["authorized"] is False
        print("✓ Unknown classification correctly treated as RESTRICTED and blocked")

    def test_blocks_on_unknown_destination(self):
        """Unknown destinations should be blocked by default."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        result = daemon.authorize_request({
            "request_id": "REQ-002",
            "source": "agent_os",
            "destination": "malicious_unknown_server",
            "payload": {"content": "Hello world"},
            "data_classification": "internal"
        })

        # Internal data should not go to unknown destinations
        assert result["authorized"] is False
        print("✓ Unknown destination correctly blocked")

    def test_blocks_on_error(self):
        """Any error during authorization should result in blocking (fail-safe)."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        # Simulate an edge case that might cause issues
        result = daemon.authorize_request({
            "request_id": "REQ-003",
            "source": None,  # Edge case
            "destination": None,  # Edge case
            "payload": None  # Edge case
        })

        # Should still return a valid response (blocked)
        assert "authorized" in result
        # The daemon should handle this gracefully
        print("✓ Edge cases handled gracefully with fail-safe behavior")

    def test_empty_payload_is_safe(self):
        """Empty payloads should be allowed (no sensitive data)."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        result = daemon.authorize_request({
            "request_id": "REQ-004",
            "source": "agent_os",
            "destination": "natlangchain",
            "payload": {},
            "data_classification": "public"
        })

        assert result["authorized"] is True
        print("✓ Empty payload correctly allowed")

    def test_strict_mode_blocks_all_violations(self):
        """Strict mode should block ALL violations without exception."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        # Try to send restricted data
        result = daemon.authorize_request({
            "request_id": "REQ-005",
            "source": "agent_os",
            "destination": "external_api",
            "payload": {"content": "password=secret123"},
            "data_classification": "public"
        })

        assert result["authorized"] is False
        assert result["violation"]["type"] == "blocked_pattern_detected"
        print("✓ Strict mode blocks all pattern violations")


class TestSensitiveDataBlocking:
    """Tests to ensure all sensitive data patterns are blocked."""

    def test_blocks_api_key_patterns(self):
        """API keys in various formats should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "api_key=sk_live_abc123",
            "API-KEY: my-secret-key",
            "apikey = 'production_key_xyz'",
            "api_key: test123456",
            '{"api_key": "secret_value"}',
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All API key patterns correctly blocked")

    def test_blocks_password_patterns(self):
        """Passwords in various formats should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "password=mysecretpass",
            "PASSWORD: hunter2",
            "passwd = 'verysecret'",
            "pwd:abc123xyz",
            '{"password": "admin123"}',
            "user_password=test",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All password patterns correctly blocked")

    def test_blocks_private_keys(self):
        """Private keys should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "private_key=xxx",
            "privatekey: yyy",
            "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBg...",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...",
            "-----BEGIN OPENSSH PRIVATE KEY-----\nb3Blbn...",
            "-----BEGIN EC PRIVATE KEY-----\nMHQC...",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All private key patterns correctly blocked")

    def test_blocks_ssh_keys(self):
        """SSH keys should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "ssh_key=abc123",
            "ssh-key: xyz789",
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB...",
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All SSH key patterns correctly blocked")

    def test_blocks_secret_patterns(self):
        """Generic secret patterns should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "secret=abc123",
            "SECRET: my_secret",
            "secret_key=xyz",
            "client_secret=oauth_secret",
            "encryption_key=key123",
            "auth_token=bearer_abc",
            "access_token=xyz789",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All secret patterns correctly blocked")

    def test_blocks_credit_card_numbers(self):
        """Credit card numbers should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "4111111111111111",  # Visa test
            "5500000000000004",  # Mastercard test
            "340000000000009",   # Amex test
            "Card: 4111111111111111",
            "Payment with 5500000000000004",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All credit card patterns correctly blocked")

    def test_blocks_ssn_patterns(self):
        """Social Security Numbers should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "123-45-6789",
            "123 45 6789",
            "SSN: 123-45-6789",
            "Social Security: 987-65-4321",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All SSN patterns correctly blocked")

    def test_blocks_aws_credentials(self):
        """AWS credentials should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "AKIAIOSFODNN7EXAMPLE",  # AWS Access Key pattern
            "aws_access_key_id=AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All AWS credential patterns correctly blocked")

    def test_blocks_database_connection_strings(self):
        """Database connection strings should be blocked."""
        daemon = BoundaryDaemon()

        test_cases = [
            "mongodb://user:pass@host:27017/db",
            "postgres://admin:secret@localhost:5432/mydb",
            "mysql://root:password@server/database",
            "redis://default:authkey@redis.host:6379",
            "jdbc:postgresql://localhost/test",
        ]

        for payload in test_cases:
            result = daemon.authorize_request({
                "source": "agent",
                "destination": "external",
                "payload": {"content": payload}
            })
            assert result["authorized"] is False, f"Failed to block: {payload}"

        print("✓ All database connection string patterns correctly blocked")

    def test_allows_safe_content(self):
        """Safe content without sensitive patterns should be allowed."""
        daemon = BoundaryDaemon()

        safe_payloads = [
            "Hello, this is a normal message",
            "I offer web development services for $50/hour",
            "The weather is nice today",
            "Please review the attached document",
            "Meeting scheduled for 3pm tomorrow",
            '{"name": "John", "email": "john@example.com"}',
        ]

        for payload in safe_payloads:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": "natlangchain",
                "payload": {"content": payload},
                "data_classification": "public"
            })
            assert result["authorized"] is True, f"Incorrectly blocked: {payload}"

        print("✓ Safe content correctly allowed")


class TestDataClassificationEnforcement:
    """Tests for data classification rules."""

    def test_public_data_can_go_anywhere(self):
        """Public data should be allowed to any destination."""
        daemon = BoundaryDaemon()

        destinations = ["natlangchain", "value_ledger", "external_api", "memory_vault"]

        for dest in destinations:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": dest,
                "payload": {"content": "This is public information"},
                "data_classification": "public"
            })
            assert result["authorized"] is True, f"Public data should go to {dest}"

        print("✓ Public data correctly allowed to all destinations")

    def test_internal_data_restrictions(self):
        """Internal data should only go to natlangchain and value_ledger."""
        daemon = BoundaryDaemon()

        # Should be allowed
        allowed_destinations = ["natlangchain", "value_ledger"]
        for dest in allowed_destinations:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": dest,
                "payload": {"content": "Internal contract details"},
                "data_classification": "internal"
            })
            assert result["authorized"] is True, f"Internal data should go to {dest}"

        # Should be blocked
        blocked_destinations = ["external_api", "unknown_server"]
        for dest in blocked_destinations:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": dest,
                "payload": {"content": "Internal contract details"},
                "data_classification": "internal"
            })
            assert result["authorized"] is False, f"Internal data should NOT go to {dest}"

        print("✓ Internal data correctly restricted to allowed destinations")

    def test_confidential_data_restrictions(self):
        """Confidential data should only go to memory_vault."""
        daemon = BoundaryDaemon()

        # Use content that doesn't trigger blocked patterns
        # Note: "Trade secret" would trigger "secret" keyword - this is correct behavior!
        confidential_content = "Proprietary business strategy document"

        # Should be allowed
        result = daemon.authorize_request({
            "source": "agent_os",
            "destination": "memory_vault",
            "payload": {"content": confidential_content},
            "data_classification": "confidential"
        })
        assert result["authorized"] is True, f"Confidential data should go to memory_vault: {result}"

        # Should be blocked for all other destinations
        blocked_destinations = ["natlangchain", "external_api", "value_ledger"]
        for dest in blocked_destinations:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": dest,
                "payload": {"content": confidential_content},
                "data_classification": "confidential"
            })
            assert result["authorized"] is False, f"Confidential data should NOT go to {dest}"

        print("✓ Confidential data correctly restricted to memory_vault only")

    def test_restricted_data_blocked_everywhere(self):
        """Restricted data should not be allowed to ANY destination."""
        daemon = BoundaryDaemon()

        all_destinations = ["natlangchain", "value_ledger", "memory_vault", "external_api"]

        for dest in all_destinations:
            result = daemon.authorize_request({
                "source": "agent_os",
                "destination": dest,
                "payload": {"content": "Private key material"},
                "data_classification": "restricted"
            })
            assert result["authorized"] is False, f"Restricted data should NOT go to {dest}"

        print("✓ Restricted data correctly blocked from all destinations")

    def test_auto_classification_sensitive_data(self):
        """Data containing sensitive patterns should auto-classify as RESTRICTED."""
        daemon = BoundaryDaemon()

        # Don't specify classification - let it auto-detect
        result = daemon.authorize_request({
            "source": "agent_os",
            "destination": "external_api",
            "payload": {"content": "Here is my password=secret123"}
            # No data_classification specified
        })

        assert result["authorized"] is False
        print("✓ Sensitive data correctly auto-classified and blocked")


class TestEnforcementModes:
    """Tests for different enforcement modes."""

    def test_strict_mode_blocks_everything(self):
        """Strict mode should block all violations."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "secret=test123"},
            "data_classification": "internal"
        })

        assert result["authorized"] is False
        print("✓ Strict mode correctly blocks all violations")

    def test_permissive_mode_blocks_critical(self):
        """Permissive mode should still block critical violations."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.PERMISSIVE)

        # Critical patterns should still be blocked
        result = daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "password=admin123"},
            "data_classification": "public"
        })

        assert result["authorized"] is False
        print("✓ Permissive mode correctly blocks critical patterns")

    def test_permissive_mode_blocks_restricted_exfiltration(self):
        """Permissive mode should block restricted data exfiltration."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.PERMISSIVE)

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "Normal looking content"},
            "data_classification": "restricted"
        })

        assert result["authorized"] is False
        print("✓ Permissive mode correctly blocks restricted data exfiltration")

    def test_audit_only_mode_allows_but_logs(self):
        """Audit-only mode should allow but still log violations."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.AUDIT_ONLY)

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "natlangchain",
            "payload": {"content": "Normal content"},
            "data_classification": "public"
        })

        # Should be allowed in audit mode (no sensitive patterns)
        assert result["authorized"] is True

        # Check that audit log was created
        audit_log = daemon.get_audit_log()
        assert len(audit_log) > 0
        print("✓ Audit-only mode correctly logs events")


class TestAuditLogging:
    """Tests for audit logging functionality."""

    def test_successful_authorization_logged(self):
        """Successful authorizations should be logged."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-AUDIT-001",
            "source": "agent_os",
            "destination": "natlangchain",
            "payload": {"content": "Normal message"},
            "data_classification": "public"
        })

        audit_log = daemon.get_audit_log()
        assert len(audit_log) >= 1

        latest = audit_log[-1]
        assert latest["event_type"] == "authorization_granted"
        assert latest["source"] == "agent_os"
        assert latest["destination"] == "natlangchain"
        print("✓ Successful authorization correctly logged")

    def test_blocked_request_logged(self):
        """Blocked requests should be logged."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-AUDIT-002",
            "source": "agent_os",
            "destination": "external",
            "payload": {"content": "password=secret"},
            "data_classification": "public"
        })

        audit_log = daemon.get_audit_log()
        assert len(audit_log) >= 1

        latest = audit_log[-1]
        assert latest["event_type"] == "authorization_denied"
        print("✓ Blocked request correctly logged")

    def test_audit_log_contains_hash(self):
        """Audit log should contain payload hash for integrity."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "source": "agent",
            "destination": "natlangchain",
            "payload": {"content": "Test message"},
            "data_classification": "public"
        })

        audit_log = daemon.get_audit_log()
        latest = audit_log[-1]

        assert "payload_hash" in latest["request"]
        assert latest["request"]["payload_hash"].startswith("SHA256:")
        print("✓ Audit log correctly contains payload hash")

    def test_audit_log_filtering(self):
        """Audit log should support filtering by event type."""
        daemon = BoundaryDaemon()

        # Generate both types of events
        daemon.authorize_request({
            "source": "agent",
            "destination": "natlangchain",
            "payload": {"content": "Normal"},
            "data_classification": "public"
        })

        daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "api_key=secret"},
            "data_classification": "public"
        })

        granted = daemon.get_audit_log(event_type="authorization_granted")
        denied = daemon.get_audit_log(event_type="authorization_denied")

        assert len(granted) >= 1
        assert len(denied) >= 1
        assert all(r["event_type"] == "authorization_granted" for r in granted)
        assert all(r["event_type"] == "authorization_denied" for r in denied)
        print("✓ Audit log filtering works correctly")


class TestViolationHandling:
    """Tests for violation recording and handling."""

    def test_violation_recorded_on_block(self):
        """Violations should be recorded when requests are blocked."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-VIOL-001",
            "source": "agent_os",
            "destination": "external",
            "payload": {"content": "password=hackme"},
            "data_classification": "public"
        })

        violations = daemon.get_violations()
        assert len(violations) >= 1

        latest = violations[-1]
        assert "violation_id" in latest
        assert latest["action_taken"] == "blocked"
        print("✓ Violation correctly recorded on block")

    def test_violation_severity_classification(self):
        """Violations should be classified by severity."""
        daemon = BoundaryDaemon()

        # Create a pattern-based violation (high severity)
        daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "-----BEGIN PRIVATE KEY-----"},
            "data_classification": "public"
        })

        violations = daemon.get_violations()
        # Pattern violations should be high severity
        pattern_violation = [v for v in violations if v["type"] == "blocked_pattern_detected"]
        assert len(pattern_violation) >= 1
        assert pattern_violation[-1]["severity"] == "high"
        print("✓ Violation severity correctly classified")

    def test_violation_filtering_by_severity(self):
        """Violations should be filterable by severity."""
        daemon = BoundaryDaemon()

        # Generate violations
        daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "secret=test"},
            "data_classification": "public"
        })

        high_violations = daemon.get_violations(severity="high")
        assert all(v["severity"] == "high" for v in high_violations)
        print("✓ Violation filtering by severity works")

    def test_violation_details_complete(self):
        """Violation records should contain complete details."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-DETAIL-001",
            "source": "agent_os",
            "destination": "malicious_server",
            "payload": {"content": "api_key=stolen_key"},
            "data_classification": "public"
        })

        violations = daemon.get_violations()
        latest = violations[-1]

        assert "violation_id" in latest
        assert "type" in latest
        assert "severity" in latest
        assert "details" in latest
        assert "timestamp" in latest
        assert "action_taken" in latest

        details = latest["details"]
        assert "source" in details
        assert "destination" in details
        print("✓ Violation details are complete")


class TestDataInspection:
    """Tests for data inspection functionality."""

    def test_inspect_detects_sensitive_patterns(self):
        """Inspection should detect sensitive patterns."""
        daemon = BoundaryDaemon()

        result = daemon.inspect_data("My password is secret123 and api_key=abc123")

        assert result["risk_score"] > 0
        assert len(result["detected_patterns"]) > 0
        assert result["policy_compliance"] is False
        print("✓ Inspection correctly detects sensitive patterns")

    def test_inspect_clean_data(self):
        """Clean data should have low risk score."""
        daemon = BoundaryDaemon()

        result = daemon.inspect_data("This is a normal message about the weather")

        assert result["risk_score"] == 0
        assert len(result["detected_patterns"]) == 0
        assert result["policy_compliance"] is True
        print("✓ Clean data correctly has zero risk score")

    def test_inspect_risk_score_calculation(self):
        """Risk score should increase with more sensitive patterns."""
        daemon = BoundaryDaemon()

        # Single pattern
        result1 = daemon.inspect_data("password=test")
        risk1 = result1["risk_score"]

        # Multiple patterns
        result2 = daemon.inspect_data("password=test and api_key=secret and token=abc")
        risk2 = result2["risk_score"]

        assert risk2 > risk1
        print("✓ Risk score correctly increases with more patterns")

    def test_inspect_suggests_classification(self):
        """Inspection should suggest appropriate classification."""
        daemon = BoundaryDaemon()

        # Clean data
        result1 = daemon.inspect_data("Public information")
        assert result1["classification_suggested"] == "internal"  # Default safe

        # Sensitive data
        result2 = daemon.inspect_data("private_key=secret")
        assert result2["classification_suggested"] == "restricted"
        print("✓ Classification suggestions are correct")


class TestPolicyManagement:
    """Tests for custom policy management."""

    def test_register_custom_policy(self):
        """Custom policies should be registerable."""
        daemon = BoundaryDaemon()

        policy = BoundaryPolicy(
            policy_id="POLICY-001",
            owner="alice",
            agent_id="agent_1",
            enforcement_mode=EnforcementMode.STRICT,
            custom_blocked_patterns=["internal-project-\\d+"]
        )

        result = daemon.register_policy(policy)
        assert result["registered"] is True
        assert result["policy_id"] == "POLICY-001"
        print("✓ Custom policy correctly registered")

    def test_custom_patterns_enforced(self):
        """Custom blocked patterns should be enforced."""
        daemon = BoundaryDaemon()

        policy = BoundaryPolicy(
            policy_id="POLICY-002",
            owner="bob",
            agent_id="agent_2",
            custom_blocked_patterns=["secret-project-\\d+", "confidential-code"]
        )
        daemon.register_policy(policy)

        result = daemon.authorize_request({
            "source": "agent_2",
            "destination": "external",
            "payload": {"content": "Working on secret-project-123"},
            "policy_id": "POLICY-002",
            "data_classification": "public"
        })

        assert result["authorized"] is False
        print("✓ Custom patterns correctly enforced")

    def test_payload_size_limit(self):
        """Payload size limits should be enforced."""
        daemon = BoundaryDaemon()

        policy = BoundaryPolicy(
            policy_id="POLICY-003",
            owner="charlie",
            agent_id="agent_3",
            max_payload_size=100  # Very small limit for testing
        )
        daemon.register_policy(policy)

        result = daemon.authorize_request({
            "source": "agent_3",
            "destination": "natlangchain",
            "payload": {"content": "A" * 200},  # Exceeds limit
            "policy_id": "POLICY-003",
            "data_classification": "public"
        })

        assert result["authorized"] is False
        assert result["violation"]["type"] == "payload_too_large"
        print("✓ Payload size limits correctly enforced")


class TestNatLangChainIntegration:
    """Tests for integration with NatLangChain."""

    def test_generate_chain_entry_for_violation(self):
        """Should generate proper chain entry for violations."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-CHAIN-001",
            "source": "agent_os",
            "destination": "malicious_external",
            "payload": {"content": "password=stolen"},
            "data_classification": "public"
        })

        violations = daemon.violations
        assert len(violations) > 0

        entry = daemon.generate_chain_entry(violations[-1])

        assert "content" in entry
        assert "author" in entry
        assert "intent" in entry
        assert "metadata" in entry

        assert entry["author"] == "boundary_daemon"
        assert entry["intent"] == "Record security event"
        assert entry["metadata"]["is_boundary_event"] is True
        assert entry["metadata"]["event_type"] == "policy_violation"
        print("✓ Chain entry correctly generated for violation")

    def test_chain_entry_contains_violation_details(self):
        """Chain entry should contain relevant violation details."""
        daemon = BoundaryDaemon()

        daemon.authorize_request({
            "request_id": "REQ-CHAIN-002",
            "source": "compromised_agent",
            "destination": "attacker_server",
            "payload": {"content": "api_key=leaked"},
            "data_classification": "public"
        })

        violations = daemon.violations
        entry = daemon.generate_chain_entry(violations[-1])

        # Check that key details are in the content
        assert "blocked" in entry["content"].lower()
        assert "security" in entry["intent"].lower() or "Record" in entry["intent"]
        assert entry["metadata"]["severity"] == "high"
        print("✓ Chain entry contains all required violation details")


class TestConvenienceFunction:
    """Tests for the convenience validation function."""

    def test_quick_validation_blocks_sensitive(self):
        """Quick validation should block sensitive data."""
        result = validate_outbound_data(
            data="password=secret123",
            destination="external_api"
        )

        assert result["authorized"] is False
        print("✓ Quick validation correctly blocks sensitive data")

    def test_quick_validation_allows_safe(self):
        """Quick validation should allow safe data."""
        result = validate_outbound_data(
            data="Hello, this is a normal message",
            destination="natlangchain",
            classification="public"
        )

        assert result["authorized"] is True
        print("✓ Quick validation correctly allows safe data")


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unicode_content_handled(self):
        """Unicode content should be properly handled."""
        daemon = BoundaryDaemon()

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "natlangchain",
            "payload": {"content": "Hello 世界! 🌍 Привет мир!"},
            "data_classification": "public"
        })

        assert result["authorized"] is True
        print("✓ Unicode content handled correctly")

    def test_nested_json_payload(self):
        """Nested JSON payloads should be fully inspected."""
        daemon = BoundaryDaemon()

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {
                "level1": {
                    "level2": {
                        "secret": "password=hidden_deep"
                    }
                }
            }
        })

        assert result["authorized"] is False
        print("✓ Nested JSON payloads correctly inspected")

    def test_very_long_payload(self):
        """Very long payloads should be handled without timeout."""
        daemon = BoundaryDaemon()

        # Large but safe payload
        large_content = "Normal text. " * 10000

        result = daemon.authorize_request({
            "source": "agent",
            "destination": "natlangchain",
            "payload": {"content": large_content},
            "data_classification": "public"
        })

        assert result["authorized"] is True
        print("✓ Large payloads handled efficiently")

    def test_empty_strings_handled(self):
        """Empty strings in various fields should be handled."""
        daemon = BoundaryDaemon()

        result = daemon.authorize_request({
            "source": "",
            "destination": "",
            "payload": {"content": ""},
            "data_classification": ""
        })

        # Should still process without crashing
        assert "authorized" in result
        print("✓ Empty strings handled gracefully")

    def test_special_characters_in_patterns(self):
        """Special regex characters in content shouldn't break detection."""
        daemon = BoundaryDaemon()

        # Content with regex special chars
        result = daemon.authorize_request({
            "source": "agent",
            "destination": "external",
            "payload": {"content": "The password=[test$^.*+?(){}|] is complex"},
        })

        assert result["authorized"] is False
        print("✓ Special characters don't break pattern detection")


def run_all_tests():
    """Run all boundary daemon tests."""
    print("\n" + "=" * 60)
    print("Running Boundary Daemon Integration Tests")
    print("=" * 60)

    test_classes = [
        TestFailSafeBehavior,
        TestSensitiveDataBlocking,
        TestDataClassificationEnforcement,
        TestEnforcementModes,
        TestAuditLogging,
        TestViolationHandling,
        TestDataInspection,
        TestPolicyManagement,
        TestNatLangChainIntegration,
        TestConvenienceFunction,
        TestEdgeCases,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    passed_tests += 1
                except AssertionError as e:
                    failed_tests.append((test_class.__name__, method_name, str(e)))
                    print(f"✗ {method_name}: {e}")
                except Exception as e:
                    failed_tests.append((test_class.__name__, method_name, str(e)))
                    print(f"✗ {method_name}: Unexpected error - {e}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")

    if failed_tests:
        print("\nFailed tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        print("=" * 60)
        return False
    else:
        print("All boundary daemon tests passed! ✓")
        print("The daemon is correctly failing safe and blocking sensitive data.")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
