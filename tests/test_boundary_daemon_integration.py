"""
Integration tests for Boundary Daemon <-> NatLangChain Blockchain

Tests the complete flow from daemon authorization to blockchain recording.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from boundary_daemon import (
    BoundaryDaemon,
    EnforcementMode,
    DataClassification,
)
from blockchain import NatLangChain, NaturalLanguageEntry


class TestBoundaryDaemonBlockchainIntegration:
    """Integration tests for Boundary Daemon with NatLangChain blockchain."""

    def test_record_violation_on_chain(self):
        """Violations should be recordable on the blockchain."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        chain = NatLangChain()

        # Trigger a violation
        daemon.authorize_request({
            "request_id": "REQ-INT-001",
            "source": "compromised_agent",
            "destination": "attacker_server",
            "payload": {"content": "api_key=stolen_key_12345"},
            "data_classification": "public"
        })

        # Get the violation
        violations = daemon.violations
        assert len(violations) > 0

        # Generate chain entry
        entry_data = daemon.generate_chain_entry(violations[-1])

        # Create NatLangChain entry
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"],
            metadata=entry_data["metadata"]
        )

        # Add to chain
        result = chain.add_entry(entry)
        assert result is not None

        # Mine the block
        mined_block = chain.mine_pending_entries(difficulty=1)
        assert mined_block is not None

        # Verify chain integrity
        assert chain.validate_chain() is True

        # Verify the entry is in the chain
        entries = chain.get_entries_by_author("boundary_daemon")
        assert len(entries) >= 1
        assert "policy_violation" in str(entries[-1])

        print("✓ Violation correctly recorded on blockchain")

    def test_authorized_request_flow(self):
        """Authorized requests should allow normal blockchain operations."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        chain = NatLangChain()

        # Prepare payload
        payload_content = "I offer web development services for $50/hour"

        # Authorize with daemon first
        auth_result = daemon.authorize_request({
            "request_id": "REQ-INT-002",
            "source": "agent_os",
            "destination": "natlangchain",
            "payload": {"content": payload_content},
            "data_classification": "public"
        })

        assert auth_result["authorized"] is True

        # If authorized, proceed with blockchain entry
        entry = NaturalLanguageEntry(
            content=payload_content,
            author="agent_os",
            intent="Post service offering",
            metadata={
                "authorization_id": auth_result["authorization_id"],
                "data_classification": auth_result["data_classification"]
            }
        )

        chain.add_entry(entry)
        mined_block = chain.mine_pending_entries(difficulty=1)

        assert mined_block is not None
        assert chain.validate_chain() is True
        print("✓ Authorized request flow works correctly")

    def test_blocked_request_prevents_chain_entry(self):
        """Blocked requests should not be added to the chain."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        chain = NatLangChain()

        # Prepare malicious payload
        payload_content = "password=super_secret_123"

        # Try to authorize
        auth_result = daemon.authorize_request({
            "request_id": "REQ-INT-003",
            "source": "agent_os",
            "destination": "natlangchain",
            "payload": {"content": payload_content},
            "data_classification": "public"
        })

        # Should be blocked
        assert auth_result["authorized"] is False

        # Do NOT add to chain when blocked
        # This simulates proper integration where blocked requests aren't processed
        if not auth_result["authorized"]:
            # Instead, record the violation
            entry_data = daemon.generate_chain_entry(daemon.violations[-1])
            violation_entry = NaturalLanguageEntry(
                content=entry_data["content"],
                author=entry_data["author"],
                intent=entry_data["intent"],
                metadata=entry_data["metadata"]
            )
            chain.add_entry(violation_entry)

        # Mine the block to commit entries
        chain.mine_pending_entries(difficulty=1)

        # Get narrative (which includes all mined entries)
        narrative = chain.get_full_narrative()

        # Original content should NOT be in any entry
        assert "password=super_secret" not in narrative
        assert "blocked" in narrative.lower()

        print("✓ Blocked request correctly prevented from chain, violation recorded")

    def test_audit_trail_integrity(self):
        """Audit trail should be maintained across multiple operations."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        # Perform multiple operations
        operations = [
            {
                "source": "agent_1",
                "destination": "natlangchain",
                "payload": {"content": "Normal message 1"},
                "data_classification": "public"
            },
            {
                "source": "agent_2",
                "destination": "external",
                "payload": {"content": "api_key=leaked"},
                "data_classification": "public"
            },
            {
                "source": "agent_1",
                "destination": "natlangchain",
                "payload": {"content": "Normal message 2"},
                "data_classification": "public"
            },
            {
                "source": "agent_3",
                "destination": "attacker",
                "payload": {"content": "password=stolen"},
                "data_classification": "public"
            },
        ]

        for op in operations:
            daemon.authorize_request(op)

        # Verify audit log
        audit_log = daemon.get_audit_log()
        assert len(audit_log) == 4

        # Verify granted vs denied
        granted = [r for r in audit_log if r["event_type"] == "authorization_granted"]
        denied = [r for r in audit_log if r["event_type"] == "authorization_denied"]

        assert len(granted) == 2
        assert len(denied) == 2

        # Verify violations
        violations = daemon.get_violations()
        assert len(violations) == 2

        print("✓ Audit trail integrity maintained across operations")

    def test_fail_safe_protects_chain(self):
        """Fail-safe behavior should protect the chain from sensitive data."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        chain = NatLangChain()

        # Various attack vectors that should all be blocked
        attack_payloads = [
            "Here's my password=admin123",
            "API key: sk-live-abc123xyz",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...",
            "ssh-rsa AAAAB3NzaC1yc2E...",
            "My SSN is 123-45-6789",
            "Card number: 4111111111111111",
            "mongodb://admin:password@host/db",
            "aws_secret_access_key=wJalrXUtnFEMI...",
        ]

        blocked_count = 0
        for payload in attack_payloads:
            result = daemon.authorize_request({
                "source": "test_agent",
                "destination": "external",
                "payload": {"content": payload},
                "data_classification": "public"
            })
            if not result["authorized"]:
                blocked_count += 1
                # Simulating proper integration: blocked requests don't get added to chain
                # Only violation records would be added

        # ALL attack vectors should be blocked
        assert blocked_count == len(attack_payloads), \
            f"Only {blocked_count}/{len(attack_payloads)} attack vectors blocked"

        # Verify that all violations were recorded
        violations = daemon.get_violations()
        assert len(violations) == len(attack_payloads), \
            f"Expected {len(attack_payloads)} violations, got {len(violations)}"

        # Verify chain still only has genesis block (no sensitive data leaked)
        # Note: chain starts with 1 block (genesis)
        assert len(chain.chain) == 1  # Only genesis block
        assert len(chain.pending_entries) == 0  # No pending entries

        print(f"✓ Fail-safe protected chain from {blocked_count} attack vectors")

    def test_classification_based_routing(self):
        """Data should be routed based on classification."""
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        # Test routing for each classification level
        test_cases = [
            # (classification, destination, should_allow)
            ("public", "natlangchain", True),
            ("public", "external_api", True),
            ("internal", "natlangchain", True),
            ("internal", "external_api", False),
            ("confidential", "memory_vault", True),
            ("confidential", "natlangchain", False),
            ("restricted", "memory_vault", False),
            ("restricted", "natlangchain", False),
        ]

        for classification, destination, should_allow in test_cases:
            result = daemon.authorize_request({
                "source": "test_agent",
                "destination": destination,
                "payload": {"content": "Test content for routing"},
                "data_classification": classification
            })

            assert result["authorized"] == should_allow, \
                f"Classification {classification} to {destination} should be {'allowed' if should_allow else 'blocked'}"

        print("✓ Classification-based routing works correctly")


def run_all_integration_tests():
    """Run all boundary daemon integration tests."""
    print("\n" + "=" * 60)
    print("Running Boundary Daemon <-> NatLangChain Integration Tests")
    print("=" * 60)

    test_class = TestBoundaryDaemonBlockchainIntegration()

    tests = [
        "test_record_violation_on_chain",
        "test_authorized_request_flow",
        "test_blocked_request_prevents_chain_entry",
        "test_audit_trail_integrity",
        "test_fail_safe_protects_chain",
        "test_classification_based_routing",
    ]

    passed = 0
    failed = []

    for test_name in tests:
        try:
            getattr(test_class, test_name)()
            passed += 1
        except AssertionError as e:
            failed.append((test_name, str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            failed.append((test_name, str(e)))
            print(f"✗ {test_name}: Unexpected error - {e}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} integration tests passed")

    if failed:
        print("\nFailed tests:")
        for test_name, error in failed:
            print(f"  - {test_name}: {error}")
        print("=" * 60)
        return False
    else:
        print("All integration tests passed! ✓")
        print("Boundary Daemon correctly integrates with NatLangChain.")
        print("=" * 60)
        return True


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
