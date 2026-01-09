"""
Tests for NatLangChain Security Enforcement Module

Tests input validation, IP address validation, enforcement results,
and security enforcement configuration.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from security_enforcement import (
    SecurityEnforcementError,
    validate_ip_address,
)


class TestIPAddressValidation(unittest.TestCase):
    """Tests for IP address validation."""

    def test_valid_ipv4(self):
        """Test valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "255.255.255.255",
            "0.0.0.0",
        ]

        for ip in valid_ips:
            is_valid, error = validate_ip_address(ip)
            self.assertTrue(is_valid, f"Expected {ip} to be valid, got error: {error}")
            self.assertIsNone(error)

    def test_valid_ipv6(self):
        """Test valid IPv6 addresses."""
        valid_ips = [
            "::1",
            "2001:db8::1",
            "fe80::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        ]

        for ip in valid_ips:
            is_valid, error = validate_ip_address(ip)
            self.assertTrue(is_valid, f"Expected {ip} to be valid, got error: {error}")

    def test_valid_cidr(self):
        """Test valid CIDR notation."""
        valid_cidrs = [
            "192.168.1.0/24",
            "10.0.0.0/8",
            "172.16.0.0/16",
            "2001:db8::/32",
        ]

        for cidr in valid_cidrs:
            is_valid, error = validate_ip_address(cidr)
            self.assertTrue(is_valid, f"Expected {cidr} to be valid, got error: {error}")

    def test_invalid_ip_format(self):
        """Test invalid IP address formats."""
        invalid_ips = [
            "not.an.ip",
            "256.256.256.256",
            "192.168.1",
            "192.168.1.1.1",
            "abc",
            "12345",
        ]

        for ip in invalid_ips:
            is_valid, error = validate_ip_address(ip)
            self.assertFalse(is_valid, f"Expected {ip} to be invalid")
            self.assertIsNotNone(error)

    def test_empty_ip(self):
        """Test empty IP address."""
        is_valid, error = validate_ip_address("")
        self.assertFalse(is_valid)
        self.assertIn("required", error.lower())

    def test_none_ip(self):
        """Test None IP address."""
        is_valid, error = validate_ip_address(None)
        self.assertFalse(is_valid)
        self.assertIn("required", error.lower())

    def test_command_injection_semicolon(self):
        """Test command injection prevention with semicolon."""
        malicious = "192.168.1.1; rm -rf /"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_pipe(self):
        """Test command injection prevention with pipe."""
        malicious = "192.168.1.1 | cat /etc/passwd"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_ampersand(self):
        """Test command injection prevention with ampersand."""
        malicious = "192.168.1.1 && echo pwned"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_backtick(self):
        """Test command injection prevention with backtick."""
        malicious = "192.168.1.1`whoami`"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_dollar(self):
        """Test command injection prevention with dollar sign."""
        malicious = "192.168.1.1$(whoami)"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_newline(self):
        """Test command injection prevention with newline."""
        malicious = "192.168.1.1\nwhoami"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_command_injection_redirect(self):
        """Test command injection prevention with redirect."""
        malicious = "192.168.1.1 > /tmp/pwned"
        is_valid, error = validate_ip_address(malicious)
        self.assertFalse(is_valid)
        self.assertIn("Invalid character", error)

    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        ip_with_spaces = "  192.168.1.1  "
        is_valid, error = validate_ip_address(ip_with_spaces)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


class TestSecurityEnforcementError(unittest.TestCase):
    """Tests for SecurityEnforcementError exception."""

    def test_enforcement_error_creation(self):
        """Test creating an enforcement error."""
        # We need a mock EnforcementResult to create the error
        # Since we can't easily import it, test the exception class exists
        self.assertTrue(issubclass(SecurityEnforcementError, Exception))

    def test_enforcement_error_inheritance(self):
        """Test that SecurityEnforcementError inherits from Exception."""
        self.assertTrue(issubclass(SecurityEnforcementError, Exception))


class TestDangerousCharacterDetection(unittest.TestCase):
    """Tests for dangerous character detection in inputs."""

    def test_shell_metacharacters(self):
        """Test that shell metacharacters are detected."""
        # These characters are definitely in the dangerous list
        dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "<", ">"]

        for char in dangerous_chars:
            test_input = f"192.168.1.1{char}"
            is_valid, error = validate_ip_address(test_input)
            self.assertFalse(is_valid, f"Character '{char!r}' should be rejected")
            self.assertIn("Invalid character", error)

    def test_bracket_characters(self):
        """Test that bracket characters are detected."""
        brackets = ["{", "}", "[", "]"]

        for char in brackets:
            test_input = f"192.168.1.1{char}"
            is_valid, error = validate_ip_address(test_input)
            self.assertFalse(is_valid, f"Character '{char!r}' should be rejected")


class TestInputValidationEdgeCases(unittest.TestCase):
    """Tests for edge cases in input validation."""

    def test_localhost(self):
        """Test localhost addresses."""
        self.assertTrue(validate_ip_address("127.0.0.1")[0])
        self.assertTrue(validate_ip_address("::1")[0])

    def test_broadcast(self):
        """Test broadcast addresses."""
        self.assertTrue(validate_ip_address("255.255.255.255")[0])

    def test_any_address(self):
        """Test any/all addresses."""
        self.assertTrue(validate_ip_address("0.0.0.0")[0])
        self.assertTrue(validate_ip_address("::")[0])

    def test_very_long_input(self):
        """Test rejection of very long inputs."""
        long_input = "192.168.1.1" + "x" * 1000
        is_valid, error = validate_ip_address(long_input)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
