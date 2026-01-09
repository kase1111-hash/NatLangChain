"""
Comprehensive Permutation Tests for Boundary Daemon

Tests ALL possible input permutations to ensure:
1. No soft locks (system never gets stuck)
2. No dead ends (always returns valid response)
3. State consistency after any operation sequence
4. Proper error handling for all edge cases

Test Strategy:
- Systematic enumeration of all input combinations
- Random fuzzing with valid and invalid inputs
- Sequential chain testing with state verification
- Concurrent-style stress testing
"""

import itertools
import os
import random
import string
import sys
import time
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchain import NatLangChain, NaturalLanguageEntry
from boundary_daemon import (
    BoundaryDaemon,
    BoundaryPolicy,
    EnforcementMode,
)

# ============================================================
# Test Configuration
# ============================================================

# All possible sources
SOURCES = [
    "agent_os",
    "agent_os_instance_1",
    "agent_os_instance_2",
    "mediator_node",
    "external_client",
    "boundary_daemon",
    "unknown_source",
    "",
    None,
]

# All possible destinations
DESTINATIONS = [
    "natlangchain",
    "value_ledger",
    "memory_vault",
    "external_api",
    "mediator_node",
    "attacker_server",
    "unknown_destination",
    "",
    None,
]

# All possible classifications
CLASSIFICATIONS = [
    "public",
    "internal",
    "confidential",
    "restricted",
    "unknown_class",
    "INVALID",
    "",
    None,
]

# All enforcement modes
ENFORCEMENT_MODES = [
    EnforcementMode.STRICT,
    EnforcementMode.PERMISSIVE,
    EnforcementMode.AUDIT_ONLY,
]

# Sample payloads - safe and sensitive
SAFE_PAYLOADS = [
    "Hello, this is a normal message",
    "I offer web development services",
    "Meeting scheduled for tomorrow",
    {"content": "JSON payload with safe data"},
    {"nested": {"data": "still safe"}},
    "",
    {},
    None,
]

SENSITIVE_PAYLOADS = [
    "password=secret123",
    "api_key=sk-live-abc123",
    "-----BEGIN PRIVATE KEY-----",
    "ssh-rsa AAAAB3NzaC1yc2E",
    "123-45-6789",  # SSN
    "4111111111111111",  # Credit card
    "mongodb://user:pass@host/db",
    {"secret": "hidden", "api_key": "exposed"},
    {"deep": {"nested": {"password": "found"}}},
]

# All payload types combined
ALL_PAYLOADS = SAFE_PAYLOADS + SENSITIVE_PAYLOADS


@dataclass
class PermutationResult:
    """Result of a single permutation test."""

    source: Any
    destination: Any
    classification: Any
    payload_type: str
    enforcement_mode: str
    authorized: bool
    has_response: bool
    has_violation: bool
    error: str = None
    response_time_ms: float = 0


class PermutationTestSuite:
    """Comprehensive permutation testing for Boundary Daemon."""

    def __init__(self):
        self.results: list[PermutationResult] = []
        self.soft_locks: list[dict] = []
        self.dead_ends: list[dict] = []
        self.errors: list[dict] = []
        self.start_time = None

    def _create_request(
        self, source: Any, destination: Any, payload: Any, classification: Any
    ) -> dict[str, Any]:
        """Create a test request with given parameters."""
        request = {
            "request_id": f"REQ-{random.randint(1000, 9999)}",
        }

        if source is not None:
            request["source"] = source
        if destination is not None:
            request["destination"] = destination
        if payload is not None:
            if isinstance(payload, dict):
                request["payload"] = payload
            else:
                request["payload"] = {"content": payload}
        if classification is not None:
            request["data_classification"] = classification

        return request

    def _test_single_permutation(
        self,
        daemon: BoundaryDaemon,
        source: Any,
        destination: Any,
        payload: Any,
        classification: Any,
        payload_type: str,
    ) -> PermutationResult:
        """Test a single input permutation."""
        request = self._create_request(source, destination, payload, classification)

        start = time.time()
        try:
            # Set timeout for soft lock detection (should complete in < 1 second)
            result = daemon.authorize_request(request)
            elapsed_ms = (time.time() - start) * 1000

            # Check for valid response structure
            has_response = isinstance(result, dict) and "authorized" in result

            has_violation = not result.get("authorized", True) and "violation" in result

            return PermutationResult(
                source=source,
                destination=destination,
                classification=classification,
                payload_type=payload_type,
                enforcement_mode=daemon.enforcement_mode.value,
                authorized=result.get("authorized", False),
                has_response=has_response,
                has_violation=has_violation,
                response_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return PermutationResult(
                source=source,
                destination=destination,
                classification=classification,
                payload_type=payload_type,
                enforcement_mode=daemon.enforcement_mode.value,
                authorized=False,
                has_response=False,
                has_violation=False,
                error=str(e),
                response_time_ms=elapsed_ms,
            )

    def test_all_source_destination_classification_combinations(self) -> dict[str, Any]:
        """
        Test ALL combinations of source, destination, and classification.
        This is the core permutation test.
        """
        print("\n" + "=" * 60)
        print("Testing Source × Destination × Classification Combinations")
        print("=" * 60)

        total_combinations = (
            len(SOURCES) * len(DESTINATIONS) * len(CLASSIFICATIONS) * len(ENFORCEMENT_MODES)
        )
        print(f"Total combinations to test: {total_combinations}")

        tested = 0
        passed = 0
        failed = 0

        for mode in ENFORCEMENT_MODES:
            daemon = BoundaryDaemon(enforcement_mode=mode)

            for source in SOURCES:
                for destination in DESTINATIONS:
                    for classification in CLASSIFICATIONS:
                        # Test with safe payload
                        result = self._test_single_permutation(
                            daemon, source, destination, "Safe test content", classification, "safe"
                        )
                        self.results.append(result)
                        tested += 1

                        if result.has_response and result.error is None:
                            passed += 1
                        else:
                            failed += 1
                            if result.error:
                                self.errors.append(
                                    {
                                        "source": source,
                                        "destination": destination,
                                        "classification": classification,
                                        "mode": mode.value,
                                        "error": result.error,
                                    }
                                )

                        # Check for soft lock (> 5 seconds)
                        if result.response_time_ms > 5000:
                            self.soft_locks.append(
                                {
                                    "source": source,
                                    "destination": destination,
                                    "classification": classification,
                                    "mode": mode.value,
                                    "time_ms": result.response_time_ms,
                                }
                            )

                        # Progress update every 100 tests
                        if tested % 100 == 0:
                            print(
                                f"  Progress: {tested}/{total_combinations} ({100 * tested // total_combinations}%)"
                            )

        print(f"\nResults: {passed}/{tested} passed, {failed} failed")
        return {
            "total": tested,
            "passed": passed,
            "failed": failed,
            "soft_locks": len(self.soft_locks),
            "errors": len(self.errors),
        }

    def test_all_payload_types(self) -> dict[str, Any]:
        """Test all payload types with different configurations."""
        print("\n" + "=" * 60)
        print("Testing All Payload Types")
        print("=" * 60)

        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        tested = 0
        safe_allowed = 0
        sensitive_blocked = 0
        issues = []

        # Test safe payloads - should be allowed to valid destinations
        print("\nTesting safe payloads...")
        for payload in SAFE_PAYLOADS:
            result = self._test_single_permutation(
                daemon, "agent_os", "natlangchain", payload, "public", "safe"
            )
            tested += 1

            if result.has_response:
                if result.authorized:
                    safe_allowed += 1
                else:
                    # Safe payload blocked - check if it's a valid block reason
                    issues.append(
                        {"type": "safe_blocked", "payload": str(payload)[:50], "result": result}
                    )

        # Test sensitive payloads - should be blocked
        print("Testing sensitive payloads...")
        for payload in SENSITIVE_PAYLOADS:
            result = self._test_single_permutation(
                daemon, "agent_os", "external_api", payload, "public", "sensitive"
            )
            tested += 1

            if result.has_response:
                if not result.authorized:
                    sensitive_blocked += 1
                else:
                    issues.append(
                        {
                            "type": "sensitive_allowed",
                            "payload": str(payload)[:50],
                            "result": result,
                        }
                    )

        print("\nResults:")
        print(f"  Safe payloads allowed: {safe_allowed}/{len(SAFE_PAYLOADS)}")
        print(f"  Sensitive payloads blocked: {sensitive_blocked}/{len(SENSITIVE_PAYLOADS)}")
        print(f"  Issues found: {len(issues)}")

        return {
            "tested": tested,
            "safe_allowed": safe_allowed,
            "sensitive_blocked": sensitive_blocked,
            "issues": issues,
        }

    def test_enforcement_mode_transitions(self) -> dict[str, Any]:
        """Test that mode transitions don't cause soft locks."""
        print("\n" + "=" * 60)
        print("Testing Enforcement Mode Transitions")
        print("=" * 60)

        transitions = list(itertools.permutations(ENFORCEMENT_MODES, 2))
        print(f"Testing {len(transitions)} mode transitions")

        issues = []

        for from_mode, to_mode in transitions:
            # Create daemon in first mode
            daemon = BoundaryDaemon(enforcement_mode=from_mode)

            # Make some requests
            for _ in range(5):
                daemon.authorize_request(
                    {
                        "source": "agent",
                        "destination": "natlangchain",
                        "payload": {"content": "test"},
                        "data_classification": "public",
                    }
                )

            # Change mode
            daemon.enforcement_mode = to_mode

            # Make more requests - should not cause issues
            for _ in range(5):
                result = daemon.authorize_request(
                    {
                        "source": "agent",
                        "destination": "natlangchain",
                        "payload": {"content": "test after transition"},
                        "data_classification": "public",
                    }
                )

                if "authorized" not in result:
                    issues.append(
                        {
                            "from": from_mode.value,
                            "to": to_mode.value,
                            "issue": "Missing authorized field after transition",
                        }
                    )

            print(f"  {from_mode.value} → {to_mode.value}: OK")

        print(f"\nMode transitions: {len(transitions) - len(issues)}/{len(transitions)} passed")
        return {"transitions": len(transitions), "issues": issues}

    def test_sequential_operation_chains(self) -> dict[str, Any]:
        """
        Test sequential chains of operations to find state corruption.
        """
        print("\n" + "=" * 60)
        print("Testing Sequential Operation Chains")
        print("=" * 60)

        chain_lengths = [10, 50, 100, 500]
        issues = []

        for chain_length in chain_lengths:
            print(f"\n  Testing chain of {chain_length} operations...")
            daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

            for i in range(chain_length):
                # Randomly choose operation type
                op_type = random.choice(["safe", "sensitive", "edge"])

                if op_type == "safe":
                    payload = random.choice(SAFE_PAYLOADS)
                    classification = "public"
                elif op_type == "sensitive":
                    payload = random.choice(SENSITIVE_PAYLOADS)
                    classification = random.choice(CLASSIFICATIONS)
                else:
                    # Edge case
                    payload = random.choice([None, "", {}, {"": ""}])
                    classification = random.choice([None, "", "invalid"])

                result = daemon.authorize_request(
                    {
                        "source": random.choice(SOURCES),
                        "destination": random.choice(DESTINATIONS),
                        "payload": {"content": payload}
                        if not isinstance(payload, dict)
                        else payload,
                        "data_classification": classification,
                    }
                )

                # Verify response is valid
                if not isinstance(result, dict) or "authorized" not in result:
                    issues.append(
                        {
                            "chain_length": chain_length,
                            "operation": i,
                            "issue": "Invalid response structure",
                        }
                    )

            # Verify state consistency after chain
            audit_log = daemon.get_audit_log(limit=chain_length + 10)
            violations = daemon.get_violations(limit=chain_length + 10)

            # Should have logged something
            if len(audit_log) == 0:
                issues.append(
                    {"chain_length": chain_length, "issue": "No audit log entries after chain"}
                )

            # Verify counters are consistent (audit log should match chain length)
            expected_audit = chain_length
            if len(audit_log) != expected_audit:
                issues.append(
                    {
                        "chain_length": chain_length,
                        "issue": f"Audit count mismatch: {len(audit_log)} vs {expected_audit}",
                    }
                )

            print(f"    Completed: {len(audit_log)} audit entries, {len(violations)} violations")

        return {"chains_tested": len(chain_lengths), "issues": issues}

    def test_state_consistency(self) -> dict[str, Any]:
        """
        Test that daemon state remains consistent after any operation.
        """
        print("\n" + "=" * 60)
        print("Testing State Consistency")
        print("=" * 60)

        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        issues = []

        # Track expected state
        expected_audit_count = 0
        expected_violation_count = 0

        operations = [
            # (source, dest, payload, classification, expect_violation)
            ("agent", "natlangchain", "safe", "public", False),
            ("agent", "external", "password=x", "public", True),
            ("agent", "natlangchain", "normal", "internal", False),
            ("agent", "external", "api_key=y", "public", True),
            ("agent", "memory_vault", "safe", "confidential", False),
            ("agent", "external", "secret=z", "public", True),
        ]

        for source, dest, payload, classification, expect_violation in operations:
            daemon.authorize_request(
                {
                    "source": source,
                    "destination": dest,
                    "payload": {"content": payload},
                    "data_classification": classification,
                }
            )

            expected_audit_count += 1
            if expect_violation:
                expected_violation_count += 1

            # Verify state
            actual_audit = len(daemon.get_audit_log())
            actual_violations = len(daemon.get_violations())

            if actual_audit != expected_audit_count:
                issues.append(
                    {
                        "operation": payload,
                        "issue": f"Audit count: {actual_audit} vs expected {expected_audit_count}",
                    }
                )

            if actual_violations != expected_violation_count:
                issues.append(
                    {
                        "operation": payload,
                        "issue": f"Violation count: {actual_violations} vs expected {expected_violation_count}",
                    }
                )

        print(
            f"  Final state: {expected_audit_count} audits, {expected_violation_count} violations"
        )
        print(f"  State consistency: {'PASS' if len(issues) == 0 else 'FAIL'}")

        return {"operations": len(operations), "issues": issues}

    def test_blockchain_integration_chains(self) -> dict[str, Any]:
        """
        Test end-to-end chains with blockchain integration.
        """
        print("\n" + "=" * 60)
        print("Testing Blockchain Integration Chains")
        print("=" * 60)

        issues = []
        chain = NatLangChain()
        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)

        # Sequence of operations simulating real usage
        operations = [
            {"type": "post", "content": "I offer services", "expect": "allow"},
            {"type": "post", "content": "password=admin", "expect": "block"},
            {"type": "post", "content": "Looking for contractor", "expect": "allow"},
            {"type": "post", "content": "api_key=secret", "expect": "block"},
            {"type": "mine", "expect": "success"},
            {"type": "post", "content": "Contract agreed", "expect": "allow"},
            {"type": "violation_record", "expect": "success"},
            {"type": "mine", "expect": "success"},
        ]

        entries_added = 0
        violations_recorded = 0

        for op in operations:
            try:
                if op["type"] == "post":
                    result = daemon.authorize_request(
                        {
                            "source": "agent_os",
                            "destination": "natlangchain",
                            "payload": {"content": op["content"]},
                            "data_classification": "public",
                        }
                    )

                    if result["authorized"]:
                        if op["expect"] == "allow":
                            entry = NaturalLanguageEntry(
                                content=op["content"], author="agent_os", intent="Test entry"
                            )
                            chain.add_entry(entry)
                            entries_added += 1
                        else:
                            issues.append({"op": op, "issue": "Expected block but was allowed"})
                    else:
                        if op["expect"] == "block":
                            violations_recorded += 1
                        else:
                            issues.append({"op": op, "issue": "Expected allow but was blocked"})

                elif op["type"] == "mine":
                    if chain.pending_entries:
                        mined = chain.mine_pending_entries(difficulty=1)
                        if not mined:
                            issues.append({"op": op, "issue": "Mining failed"})
                    # OK if no pending entries

                elif op["type"] == "violation_record":
                    if daemon.violations:
                        entry_data = daemon.generate_chain_entry(daemon.violations[-1])
                        entry = NaturalLanguageEntry(
                            content=entry_data["content"],
                            author=entry_data["author"],
                            intent=entry_data["intent"],
                            metadata=entry_data["metadata"],
                        )
                        chain.add_entry(entry)
                        entries_added += 1

            except Exception as e:
                issues.append({"op": op, "issue": f"Exception: {e!s}"})

        # Verify chain integrity
        if not chain.validate_chain():
            issues.append({"issue": "Chain validation failed at end"})

        print(f"  Operations completed: {len(operations)}")
        print(f"  Entries added: {entries_added}")
        print(f"  Violations recorded: {violations_recorded}")
        print(f"  Chain valid: {chain.validate_chain()}")
        print(f"  Issues: {len(issues)}")

        return {
            "operations": len(operations),
            "entries_added": entries_added,
            "violations_recorded": violations_recorded,
            "chain_valid": chain.validate_chain(),
            "issues": issues,
        }

    def test_fuzzing(self, iterations: int = 1000) -> dict[str, Any]:
        """
        Random fuzzing with edge cases and malformed inputs.
        """
        print("\n" + "=" * 60)
        print(f"Fuzzing Test ({iterations} iterations)")
        print("=" * 60)

        daemon = BoundaryDaemon(enforcement_mode=EnforcementMode.STRICT)
        issues = []
        crashes = []

        # Fuzz generators
        def random_string(length: int = 10) -> str:
            return "".join(random.choices(string.printable, k=length))

        def random_nested_dict(depth: int = 3) -> dict:
            if depth <= 0:
                return random_string(5)
            return {random_string(3): random_nested_dict(depth - 1)}

        fuzz_payloads = [
            lambda: random_string(random.randint(0, 1000)),
            lambda: random_nested_dict(random.randint(1, 5)),
            lambda: [random_string(5) for _ in range(random.randint(0, 10))],
            lambda: random.randint(-1000000, 1000000),
            lambda: random.random(),
            lambda: None,
            lambda: "",
            lambda: "x" * 100000,  # Very long string
            lambda: "\x00\x01\x02",  # Binary data
            lambda: "🎉" * 100,  # Unicode
            lambda: {"__proto__": "polluted"},  # Prototype pollution attempt
            lambda: {"constructor": {"prototype": {}}},
        ]

        for i in range(iterations):
            try:
                payload_gen = random.choice(fuzz_payloads)
                payload = payload_gen()

                result = daemon.authorize_request(
                    {
                        "source": random.choice([*SOURCES, random_string(10)]),
                        "destination": random.choice([*DESTINATIONS, random_string(10)]),
                        "payload": {"content": payload}
                        if not isinstance(payload, dict)
                        else payload,
                        "data_classification": random.choice([*CLASSIFICATIONS, random_string(5)]),
                    }
                )

                # Must always return valid response
                if not isinstance(result, dict):
                    issues.append({"iteration": i, "issue": f"Non-dict response: {type(result)}"})
                elif "authorized" not in result:
                    issues.append({"iteration": i, "issue": "Missing 'authorized' field"})

            except Exception as e:
                crashes.append({"iteration": i, "error": str(e), "type": type(e).__name__})

            if (i + 1) % 200 == 0:
                print(f"  Progress: {i + 1}/{iterations}")

        print("\nFuzzing results:")
        print(f"  Iterations: {iterations}")
        print(f"  Issues: {len(issues)}")
        print(f"  Crashes: {len(crashes)}")

        return {"iterations": iterations, "issues": issues, "crashes": crashes}

    def test_policy_permutations(self) -> dict[str, Any]:
        """
        Test all policy configuration permutations.
        """
        print("\n" + "=" * 60)
        print("Testing Policy Permutations")
        print("=" * 60)

        issues = []

        # Test different max payload sizes
        payload_sizes = [100, 1000, 10000, 100000, 1000000]

        for size in payload_sizes:
            daemon = BoundaryDaemon()
            policy = BoundaryPolicy(
                policy_id=f"POLICY-SIZE-{size}",
                owner="test",
                agent_id="test_agent",
                max_payload_size=size,
            )
            daemon.register_policy(policy)

            # Test at boundary
            result = daemon.authorize_request(
                {
                    "source": "test_agent",
                    "destination": "natlangchain",
                    "payload": {"content": "x" * (size - 50)},  # Just under limit
                    "policy_id": policy.policy_id,
                    "data_classification": "public",
                }
            )

            if not result.get("authorized"):
                issues.append({"size": size, "issue": "Blocked under limit"})

            # Test over boundary
            result = daemon.authorize_request(
                {
                    "source": "test_agent",
                    "destination": "natlangchain",
                    "payload": {"content": "x" * (size + 100)},  # Over limit
                    "policy_id": policy.policy_id,
                    "data_classification": "public",
                }
            )

            if result.get("authorized"):
                issues.append({"size": size, "issue": "Allowed over limit"})

        # Test custom patterns
        custom_patterns = [
            r"project-\d+",
            r"internal-ref-\w+",
            r"secret-code-[a-z]+",
        ]

        for pattern in custom_patterns:
            daemon = BoundaryDaemon()
            policy = BoundaryPolicy(
                policy_id="POLICY-PATTERN",
                owner="test",
                agent_id="test_agent",
                custom_blocked_patterns=[pattern],
            )
            daemon.register_policy(policy)

            # Should block matching content
            test_content = "Working on project-123 today"
            result = daemon.authorize_request(
                {
                    "source": "test_agent",
                    "destination": "external",
                    "payload": {"content": test_content},
                    "policy_id": policy.policy_id,
                    "data_classification": "public",
                }
            )

            # First pattern should match and block
            if pattern == r"project-\d+" and result.get("authorized"):
                issues.append({"pattern": pattern, "issue": "Failed to block matching content"})

        print(f"  Payload size tests: {len(payload_sizes)}")
        print(f"  Pattern tests: {len(custom_patterns)}")
        print(f"  Issues: {len(issues)}")

        return {"issues": issues}

    def run_all_tests(self) -> dict[str, Any]:
        """Run all permutation tests and generate report."""
        self.start_time = time.time()

        print("\n" + "=" * 70)
        print("     BOUNDARY DAEMON COMPREHENSIVE PERMUTATION TESTS")
        print("=" * 70)

        results = {}

        # Run all test categories
        results["combinations"] = self.test_all_source_destination_classification_combinations()
        results["payloads"] = self.test_all_payload_types()
        results["mode_transitions"] = self.test_enforcement_mode_transitions()
        results["sequential_chains"] = self.test_sequential_operation_chains()
        results["state_consistency"] = self.test_state_consistency()
        results["blockchain_integration"] = self.test_blockchain_integration_chains()
        results["fuzzing"] = self.test_fuzzing(iterations=500)
        results["policy_permutations"] = self.test_policy_permutations()

        elapsed = time.time() - self.start_time

        # Generate summary
        print("\n" + "=" * 70)
        print("                    FINAL SUMMARY")
        print("=" * 70)

        total_issues = sum(
            len(r.get("issues", [])) + r.get("failed", 0)
            for r in results.values()
            if isinstance(r, dict)
        )

        total_soft_locks = len(self.soft_locks)
        total_errors = len(self.errors)

        print(f"\nTest Duration: {elapsed:.2f} seconds")
        print("\nResults by Category:")

        for category, result in results.items():
            if isinstance(result, dict):
                issues = len(result.get("issues", [])) + result.get("failed", 0)
                status = "✓ PASS" if issues == 0 else f"✗ FAIL ({issues} issues)"
                print(f"  {category}: {status}")

        print("\nOverall Statistics:")
        print(f"  Total Issues: {total_issues}")
        print(f"  Soft Locks: {total_soft_locks}")
        print(f"  Errors: {total_errors}")

        # Final verdict
        all_passed = total_issues == 0 and total_soft_locks == 0 and total_errors == 0

        print("\n" + "=" * 70)
        if all_passed:
            print("  ✓ ALL PERMUTATION TESTS PASSED")
            print("  The daemon handles all input combinations without soft locks or dead ends.")
        else:
            print("  ✗ SOME TESTS FAILED")
            print("  Review the issues above for details.")
        print("=" * 70)

        return {
            "passed": all_passed,
            "duration_seconds": elapsed,
            "total_issues": total_issues,
            "soft_locks": total_soft_locks,
            "errors": total_errors,
            "details": results,
        }


def run_permutation_tests():
    """Main entry point for permutation tests."""
    suite = PermutationTestSuite()
    results = suite.run_all_tests()
    return results["passed"]


if __name__ == "__main__":
    success = run_permutation_tests()
    sys.exit(0 if success else 1)
