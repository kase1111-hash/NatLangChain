"""
Tests for the FIDO2/YubiKey Security Integration.

Tests hardware-backed authentication and signing for phishing-resistant
identity verification.
"""

import base64
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, "src")

from fido2_auth import (
    AuthChallenge,
    AuthenticatorAttachment,
    CredentialType,
    FIDO2AuthManager,
    FIDO2Credential,
    SignatureType,
    UserVerification,
)


class TestCredentialRegistration(unittest.TestCase):
    """Tests for FIDO2 credential registration."""

    def setUp(self):
        self.manager = FIDO2AuthManager(rp_id="natlangchain.local", rp_name="NatLangChain")

    def test_begin_registration_returns_options(self):
        """Test that begin_registration returns proper options."""
        result = self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )

        self.assertIn("challenge_id", result)
        self.assertIn("publicKey", result)
        self.assertIn("challenge", result["publicKey"])
        self.assertIn("rp", result["publicKey"])
        self.assertEqual(result["publicKey"]["rp"]["id"], "natlangchain.local")

    def test_begin_registration_generates_challenge(self):
        """Test that a unique challenge is generated."""
        result1 = self.manager.begin_registration(
            user_id="user1", user_name="alice@example.com", user_display_name="Alice"
        )
        result2 = self.manager.begin_registration(
            user_id="user2", user_name="bob@example.com", user_display_name="Bob"
        )

        self.assertNotEqual(result1["publicKey"]["challenge"], result2["publicKey"]["challenge"])

    def test_begin_registration_stores_challenge(self):
        """Test that challenge is stored for verification."""
        result = self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )

        challenge_id = result["challenge_id"]
        self.assertIn(challenge_id, self.manager.challenges)

    def test_begin_registration_with_platform_authenticator(self):
        """Test registration with platform authenticator requirement."""
        result = self.manager.begin_registration(
            user_id="user123",
            user_name="alice@example.com",
            user_display_name="Alice",
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
        )

        auth_selection = result["publicKey"]["authenticatorSelection"]
        self.assertEqual(auth_selection["authenticatorAttachment"], "platform")

    def test_begin_registration_with_resident_key(self):
        """Test registration with discoverable credential."""
        result = self.manager.begin_registration(
            user_id="user123",
            user_name="alice@example.com",
            user_display_name="Alice",
            require_resident_key=True,
        )

        auth_selection = result["publicKey"]["authenticatorSelection"]
        self.assertEqual(auth_selection["residentKey"], "required")

    def test_max_credentials_per_user_limit(self):
        """Test that users can't register too many credentials."""
        user_id = "user123"

        # Register max credentials
        for i in range(self.manager.MAX_CREDENTIALS_PER_USER):
            # Simulate registered credential
            self.manager.user_credentials.setdefault(user_id, []).append(f"cred_{i}")
            self.manager.credentials[f"cred_{i}"] = FIDO2Credential(
                credential_id=f"cred_{i}",
                user_id=user_id,
                public_key="test_key",
                public_key_algorithm=-7,
                sign_count=0,
                created_at=datetime.utcnow().isoformat(),
            )

        # Next should fail
        result = self.manager.begin_registration(
            user_id=user_id, user_name="alice@example.com", user_display_name="Alice"
        )

        self.assertIn("error", result)
        self.assertIn("Maximum credentials", result["error"])

    def test_complete_registration_success(self):
        """Test successful credential registration completion."""
        # Begin registration
        begin_result = self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )
        challenge_id = begin_result["challenge_id"]

        # Complete registration
        success, result = self.manager.complete_registration(
            challenge_id=challenge_id,
            credential_id="new_credential_id",
            public_key=base64.b64encode(b"test_public_key").decode(),
            public_key_algorithm=-7,  # ES256
            authenticator_data=base64.b64encode(b"auth_data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            transports=["usb"],
            device_name="My YubiKey",
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "registered")
        self.assertIn("credential_id", result)

    def test_complete_registration_invalid_challenge(self):
        """Test that invalid challenge is rejected."""
        success, result = self.manager.complete_registration(
            challenge_id="nonexistent_challenge",
            credential_id="cred_id",
            public_key="key",
            public_key_algorithm=-7,
            authenticator_data="data",
            client_data_json="{}",
        )

        self.assertFalse(success)
        self.assertIn("not found", result["error"].lower())

    def test_complete_registration_expired_challenge(self):
        """Test that expired challenge is rejected."""
        # Begin registration
        begin_result = self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )
        challenge_id = begin_result["challenge_id"]

        # Expire the challenge
        challenge = self.manager.challenges[challenge_id]
        challenge.expires_at = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        # Try to complete
        success, result = self.manager.complete_registration(
            challenge_id=challenge_id,
            credential_id="cred_id",
            public_key=base64.b64encode(b"key").decode(),
            public_key_algorithm=-7,
            authenticator_data=base64.b64encode(b"data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
        )

        self.assertFalse(success)
        self.assertIn("expired", result["error"].lower())

    def test_complete_registration_unsupported_algorithm(self):
        """Test that unsupported algorithms are rejected."""
        begin_result = self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )
        challenge_id = begin_result["challenge_id"]

        success, result = self.manager.complete_registration(
            challenge_id=challenge_id,
            credential_id="cred_id",
            public_key=base64.b64encode(b"key").decode(),
            public_key_algorithm=-999,  # Unsupported
            authenticator_data=base64.b64encode(b"data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
        )

        self.assertFalse(success)
        self.assertIn("Unsupported algorithm", result["error"])


class TestAuthentication(unittest.TestCase):
    """Tests for FIDO2 authentication."""

    def setUp(self):
        self.manager = FIDO2AuthManager()
        # Register a credential for testing
        self._register_test_credential("user123", "cred123")

    def _register_test_credential(self, user_id: str, cred_id: str):
        """Helper to register a test credential."""
        credential = FIDO2Credential(
            credential_id=cred_id,
            user_id=user_id,
            public_key=base64.b64encode(b"test_public_key").decode(),
            public_key_algorithm=-7,
            sign_count=0,
            created_at=datetime.utcnow().isoformat(),
            transports=["usb"],
        )
        self.manager.credentials[cred_id] = credential
        self.manager.user_credentials.setdefault(user_id, []).append(cred_id)

    def test_begin_authentication_returns_options(self):
        """Test that begin_authentication returns proper options."""
        result = self.manager.begin_authentication(user_id="user123")

        self.assertIn("challenge_id", result)
        self.assertIn("publicKey", result)
        self.assertIn("challenge", result["publicKey"])

    def test_begin_authentication_includes_credentials(self):
        """Test that allowed credentials are included."""
        result = self.manager.begin_authentication(user_id="user123")

        allowed = result["publicKey"]["allowCredentials"]
        self.assertEqual(len(allowed), 1)
        self.assertEqual(allowed[0]["id"], "cred123")

    def test_begin_authentication_unknown_user(self):
        """Test authentication for unknown user."""
        result = self.manager.begin_authentication(user_id="unknown")

        # Should return options for discoverable credentials
        self.assertIn("publicKey", result)

    def test_verify_authentication_success(self):
        """Test successful authentication verification."""
        # Begin authentication
        begin_result = self.manager.begin_authentication(user_id="user123")
        challenge_id = begin_result["challenge_id"]

        # Verify
        success, result = self.manager.verify_authentication(
            challenge_id=challenge_id,
            credential_id="cred123",
            authenticator_data=base64.b64encode(b"auth_data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"signature").decode(),
            user_handle=base64.urlsafe_b64encode(b"user123").decode().rstrip("="),
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["user_id"], "user123")

    def test_verify_authentication_invalid_credential(self):
        """Test authentication with invalid credential."""
        begin_result = self.manager.begin_authentication(user_id="user123")
        challenge_id = begin_result["challenge_id"]

        success, result = self.manager.verify_authentication(
            challenge_id=challenge_id,
            credential_id="nonexistent",
            authenticator_data=base64.b64encode(b"data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"sig").decode(),
        )

        self.assertFalse(success)
        self.assertIn("not found", result["error"].lower())


class TestSigning(unittest.TestCase):
    """Tests for FIDO2 message signing."""

    def setUp(self):
        self.manager = FIDO2AuthManager()
        # Register a credential
        credential = FIDO2Credential(
            credential_id="cred123",
            user_id="user123",
            public_key=base64.b64encode(b"test_key").decode(),
            public_key_algorithm=-7,
            sign_count=0,
            created_at=datetime.utcnow().isoformat(),
        )
        self.manager.credentials["cred123"] = credential
        self.manager.user_credentials["user123"] = ["cred123"]

    def test_begin_sign_proposal(self):
        """Test beginning a proposal signing flow."""
        result = self.manager.sign_proposal(
            user_id="user123",
            dispute_id="DISPUTE-001",
            proposal_action="accept",
            proposal_hash="abc123",
        )

        self.assertIn("challenge_id", result)
        self.assertIn("publicKey", result)

    def test_begin_sign_contract(self):
        """Test beginning a contract signing flow."""
        result = self.manager.sign_contract(
            user_id="user123", contract_hash="contract_hash_123", counterparty="bob"
        )

        self.assertIn("challenge_id", result)
        self.assertIn("publicKey", result)

    def test_complete_sign_success(self):
        """Test successful proposal signing."""
        # Begin signing
        begin_result = self.manager.sign_proposal(
            user_id="user123",
            dispute_id="DISPUTE-001",
            proposal_action="accept",
            proposal_hash="abc123",
        )
        challenge_id = begin_result["challenge_id"]

        # Complete signing using verify_authentication
        success, result = self.manager.verify_authentication(
            challenge_id=challenge_id,
            credential_id="cred123",
            authenticator_data=base64.b64encode(b"auth_data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"signature").decode(),
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "verified")
        self.assertIn("signature_id", result)


class TestAgentDelegation(unittest.TestCase):
    """Tests for agent delegation with hardware authorization."""

    def setUp(self):
        self.manager = FIDO2AuthManager()
        # Register a credential for the principal
        credential = FIDO2Credential(
            credential_id="principal_cred",
            user_id="principal",
            public_key=base64.b64encode(b"key").decode(),
            public_key_algorithm=-7,
            sign_count=0,
            created_at=datetime.utcnow().isoformat(),
        )
        self.manager.credentials["principal_cred"] = credential
        self.manager.user_credentials["principal"] = ["principal_cred"]

    def test_begin_agent_delegation(self):
        """Test beginning agent delegation."""
        result = self.manager.begin_agent_delegation(
            principal_user_id="principal",
            agent_id="agent001",
            permissions=["read_contracts", "propose_settlements"],
            duration_hours=24,
        )

        self.assertIn("challenge_id", result)
        self.assertIn("message_to_sign", result)
        self.assertIn("agent001", result["message_to_sign"])

    def test_complete_agent_delegation(self):
        """Test completing agent delegation."""
        # Begin delegation
        begin_result = self.manager.begin_agent_delegation(
            principal_user_id="principal",
            agent_id="agent001",
            permissions=["read_contracts"],
            duration_hours=24,
        )
        challenge_id = begin_result["challenge_id"]

        # Complete
        success, result = self.manager.complete_agent_delegation(
            challenge_id=challenge_id,
            credential_id="principal_cred",
            authenticator_data=base64.b64encode(b"auth_data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"sig").decode(),
        )

        self.assertTrue(success)
        self.assertIn("delegation_id", result)

    def test_verify_agent_action_valid(self):
        """Test verifying an agent action with valid delegation."""
        # Create delegation
        begin_result = self.manager.begin_agent_delegation(
            principal_user_id="principal",
            agent_id="agent001",
            permissions=["read_contracts"],
            duration_hours=24,
        )
        self.manager.complete_agent_delegation(
            challenge_id=begin_result["challenge_id"],
            credential_id="principal_cred",
            authenticator_data=base64.b64encode(b"data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"sig").decode(),
        )

        # Verify permission
        is_valid, delegation_id = self.manager.verify_agent_permission(
            agent_id="agent001", permission="read_contracts", principal_user_id="principal"
        )

        self.assertTrue(is_valid)

    def test_verify_agent_action_out_of_scope(self):
        """Test that out-of-scope actions are rejected."""
        # Create delegation with limited scope
        begin_result = self.manager.begin_agent_delegation(
            principal_user_id="principal",
            agent_id="agent001",
            permissions=["read_contracts"],
            duration_hours=24,
        )
        self.manager.complete_agent_delegation(
            challenge_id=begin_result["challenge_id"],
            credential_id="principal_cred",
            authenticator_data=base64.b64encode(b"data").decode(),
            client_data_json=base64.b64encode(b"{}").decode(),
            signature=base64.b64encode(b"sig").decode(),
        )

        # Try permission outside scope
        is_valid, delegation_id = self.manager.verify_agent_permission(
            agent_id="agent001",
            permission="delete_contracts",  # Not in scope
            principal_user_id="principal",
        )

        self.assertFalse(is_valid)
        self.assertIsNone(delegation_id)


class TestCredentialManagement(unittest.TestCase):
    """Tests for credential listing and management."""

    def setUp(self):
        self.manager = FIDO2AuthManager()
        # Register credentials
        for i in range(3):
            cred = FIDO2Credential(
                credential_id=f"cred_{i}",
                user_id="user123",
                public_key=base64.b64encode(b"key").decode(),
                public_key_algorithm=-7,
                sign_count=i * 10,
                created_at=datetime.utcnow().isoformat(),
                device_name=f"YubiKey {i}",
            )
            self.manager.credentials[f"cred_{i}"] = cred
            self.manager.user_credentials.setdefault("user123", []).append(f"cred_{i}")

    def test_get_user_credentials(self):
        """Test getting user's credentials."""
        result = self.manager.get_user_credentials("user123")

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["credential_id"], "cred_0")

    def test_get_user_credentials_empty(self):
        """Test getting credentials for user with none."""
        result = self.manager.get_user_credentials("unknown_user")

        self.assertEqual(result, [])

    def test_remove_credential(self):
        """Test credential removal."""
        success, result = self.manager.remove_credential(credential_id="cred_0", user_id="user123")

        self.assertTrue(success)
        self.assertEqual(result["status"], "removed")
        self.assertNotIn("cred_0", self.manager.credentials)
        self.assertNotIn("cred_0", self.manager.user_credentials["user123"])


class TestStatisticsAndAudit(unittest.TestCase):
    """Tests for statistics and audit trail."""

    def setUp(self):
        self.manager = FIDO2AuthManager()

    def test_get_statistics(self):
        """Test getting statistics."""
        stats = self.manager.get_statistics()

        self.assertIn("credentials", stats)
        self.assertIn("signatures", stats)
        self.assertIn("delegations", stats)
        self.assertIn("total", stats["credentials"])

    def test_audit_trail_records_events(self):
        """Test that events are recorded in audit trail."""
        # Perform an action
        self.manager.begin_registration(
            user_id="user123", user_name="alice@example.com", user_display_name="Alice"
        )

        trail = self.manager.get_audit_trail()

        self.assertGreater(len(trail), 0)
        self.assertEqual(trail[0]["event_type"], "RegistrationStarted")


class TestDataclasses(unittest.TestCase):
    """Tests for FIDO2 dataclasses."""

    def test_fido2_credential_defaults(self):
        """Test FIDO2Credential default values."""
        cred = FIDO2Credential(
            credential_id="cred123",
            user_id="user123",
            public_key="key",
            public_key_algorithm=-7,
            sign_count=0,
            created_at="2024-01-01T00:00:00",
        )

        self.assertIsNone(cred.last_used_at)
        self.assertEqual(cred.authenticator_attachment, "cross-platform")
        self.assertEqual(cred.transports, ["usb"])
        self.assertFalse(cred.user_verified)

    def test_auth_challenge_defaults(self):
        """Test AuthChallenge default values."""
        challenge = AuthChallenge(
            challenge_id="ch123",
            challenge="random_challenge",
            user_id="user123",
            signature_type="login",
            message_hash=None,
            created_at="2024-01-01T00:00:00",
            expires_at="2024-01-01T00:05:00",
        )

        self.assertFalse(challenge.used)
        self.assertEqual(challenge.metadata, {})


class TestEnums(unittest.TestCase):
    """Tests for FIDO2 enums."""

    def test_credential_type_values(self):
        """Test CredentialType enum values."""
        self.assertEqual(CredentialType.PLATFORM.value, "platform")
        self.assertEqual(CredentialType.CROSS_PLATFORM.value, "cross-platform")

    def test_signature_type_values(self):
        """Test SignatureType enum values."""
        self.assertEqual(SignatureType.PROPOSAL_ACCEPT.value, "proposal_accept")
        self.assertEqual(SignatureType.CONTRACT_SIGN.value, "contract_sign")
        self.assertEqual(SignatureType.AGENT_DELEGATE.value, "agent_delegate")

    def test_user_verification_values(self):
        """Test UserVerification enum values."""
        self.assertEqual(UserVerification.REQUIRED.value, "required")
        self.assertEqual(UserVerification.PREFERRED.value, "preferred")


if __name__ == "__main__":
    unittest.main()
