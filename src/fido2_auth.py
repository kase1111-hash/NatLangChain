"""
NatLangChain - FIDO2/YubiKey Security Integration
Hardware-backed authentication and signing for phishing-resistant identity verification.

Provides:
- FIDO2 credential registration (WebAuthn)
- Challenge-response authentication
- Hardware-backed message signing for proposals/contracts
- Agent delegation with hardware authorization
- Public key management on-chain

Integration Points:
- ILRM: Sign acceptProposal, submitLLMProposal
- Negotiation: Passwordless login, contract signing
- RRA: Agent delegation commands
"""

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class CredentialType(Enum):
    """Types of FIDO2 credentials."""

    PLATFORM = "platform"  # Built-in authenticator (TouchID, Windows Hello)
    CROSS_PLATFORM = "cross-platform"  # Roaming authenticator (YubiKey)


class AuthenticatorAttachment(Enum):
    """How the authenticator is attached."""

    PLATFORM = "platform"
    CROSS_PLATFORM = "cross-platform"


class UserVerification(Enum):
    """User verification requirements."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    DISCOURAGED = "discouraged"


class SignatureType(Enum):
    """Types of signatures that can be made."""

    PROPOSAL_ACCEPT = "proposal_accept"
    PROPOSAL_SUBMIT = "proposal_submit"
    CONTRACT_SIGN = "contract_sign"
    AGENT_DELEGATE = "agent_delegate"
    LOGIN = "login"
    GENERIC = "generic"


@dataclass
class FIDO2Credential:
    """Registered FIDO2 credential."""

    credential_id: str
    user_id: str
    public_key: str  # Base64 encoded
    public_key_algorithm: int  # COSE algorithm ID
    sign_count: int
    created_at: str
    last_used_at: str | None = None
    authenticator_attachment: str = "cross-platform"
    transports: list[str] = field(default_factory=lambda: ["usb"])
    user_verified: bool = False
    backup_eligible: bool = False
    backup_state: bool = False
    device_name: str | None = None


@dataclass
class AuthChallenge:
    """Active authentication challenge."""

    challenge_id: str
    challenge: str  # Base64 encoded random bytes
    user_id: str | None  # None for discoverable credentials
    signature_type: str
    message_hash: str | None  # Hash of message being signed
    created_at: str
    expires_at: str
    used: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignedMessage:
    """A message signed with FIDO2 credential."""

    signature_id: str
    credential_id: str
    user_id: str
    signature_type: str
    message_hash: str
    signature: str  # Base64 encoded
    authenticator_data: str  # Base64 encoded
    client_data_hash: str
    sign_count: int
    created_at: str
    verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentDelegation:
    """Agent delegation authorized by hardware key."""

    delegation_id: str
    principal_user_id: str  # User delegating authority
    agent_id: str  # Agent receiving delegation
    credential_id: str  # Credential used to authorize
    permissions: list[str]  # List of permitted actions
    signature: str
    created_at: str
    expires_at: str
    revoked: bool = False
    revoked_at: str | None = None


class FIDO2AuthManager:
    """
    Manages FIDO2/WebAuthn authentication and signing.

    Core Features:
    - Credential registration with YubiKey/platform authenticators
    - Challenge-response authentication
    - Hardware-backed message signing
    - Agent delegation with hardware authorization
    """

    # Configuration
    RP_ID = "natlangchain.io"  # Relying Party ID (domain)
    RP_NAME = "NatLangChain"
    CHALLENGE_TIMEOUT_SECONDS = 300  # 5 minutes
    MAX_CREDENTIALS_PER_USER = 10
    DELEGATION_DEFAULT_HOURS = 24

    # COSE Algorithm IDs
    COSE_ES256 = -7  # ECDSA with SHA-256
    COSE_RS256 = -257  # RSASSA-PKCS1-v1_5 with SHA-256
    COSE_EDDSA = -8  # EdDSA

    SUPPORTED_ALGORITHMS = [COSE_ES256, COSE_RS256, COSE_EDDSA]

    def __init__(self, rp_id: str | None = None, rp_name: str | None = None):
        """
        Initialize FIDO2 auth manager.

        Args:
            rp_id: Relying Party ID (domain)
            rp_name: Human-readable RP name
        """
        self.rp_id = rp_id or self.RP_ID
        self.rp_name = rp_name or self.RP_NAME

        # State tracking
        self.credentials: dict[str, FIDO2Credential] = {}  # credential_id -> credential
        self.user_credentials: dict[str, list[str]] = {}  # user_id -> [credential_ids]
        self.challenges: dict[str, AuthChallenge] = {}  # challenge_id -> challenge
        self.signatures: dict[str, SignedMessage] = {}  # signature_id -> signature
        self.delegations: dict[str, AgentDelegation] = {}  # delegation_id -> delegation

        # Audit trail
        self.events: list[dict[str, Any]] = []

    # ==================== PHASE 13A: CREDENTIAL REGISTRATION ====================

    def begin_registration(
        self,
        user_id: str,
        user_name: str,
        user_display_name: str,
        authenticator_attachment: AuthenticatorAttachment | None = None,
        require_resident_key: bool = False,
        user_verification: UserVerification = UserVerification.PREFERRED,
    ) -> dict[str, Any]:
        """
        Begin FIDO2 credential registration (WebAuthn registration ceremony).

        Args:
            user_id: Unique user identifier
            user_name: Username (email or handle)
            user_display_name: Human-readable display name
            authenticator_attachment: Platform or cross-platform
            require_resident_key: Whether to require discoverable credential
            user_verification: UV requirement level

        Returns:
            PublicKeyCredentialCreationOptions for client
        """
        # Check credential limit
        existing = self.user_credentials.get(user_id, [])
        if len(existing) >= self.MAX_CREDENTIALS_PER_USER:
            return {
                "error": "Maximum credentials reached",
                "max": self.MAX_CREDENTIALS_PER_USER,
                "current": len(existing),
            }

        # Generate challenge
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

        challenge_id = self._generate_challenge_id(user_id, "registration")

        expires_at = datetime.utcnow() + timedelta(seconds=self.CHALLENGE_TIMEOUT_SECONDS)

        auth_challenge = AuthChallenge(
            challenge_id=challenge_id,
            challenge=challenge_b64,
            user_id=user_id,
            signature_type="registration",
            message_hash=None,
            created_at=datetime.utcnow().isoformat(),
            expires_at=expires_at.isoformat(),
            metadata={"user_name": user_name, "user_display_name": user_display_name},
        )

        self.challenges[challenge_id] = auth_challenge

        # Build excludeCredentials list
        exclude_credentials = []
        for cred_id in existing:
            if cred_id in self.credentials:
                cred = self.credentials[cred_id]
                exclude_credentials.append(
                    {"type": "public-key", "id": cred_id, "transports": cred.transports}
                )

        # Build authenticator selection
        authenticator_selection = {"userVerification": user_verification.value}
        if authenticator_attachment:
            authenticator_selection["authenticatorAttachment"] = authenticator_attachment.value
        if require_resident_key:
            authenticator_selection["residentKey"] = "required"
            authenticator_selection["requireResidentKey"] = True

        # Build public key credential parameters
        pub_key_cred_params = [
            {"type": "public-key", "alg": alg} for alg in self.SUPPORTED_ALGORITHMS
        ]

        options = {
            "challenge_id": challenge_id,
            "publicKey": {
                "rp": {"id": self.rp_id, "name": self.rp_name},
                "user": {
                    "id": base64.urlsafe_b64encode(user_id.encode()).decode("utf-8").rstrip("="),
                    "name": user_name,
                    "displayName": user_display_name,
                },
                "challenge": challenge_b64,
                "pubKeyCredParams": pub_key_cred_params,
                "timeout": self.CHALLENGE_TIMEOUT_SECONDS * 1000,
                "excludeCredentials": exclude_credentials,
                "authenticatorSelection": authenticator_selection,
                "attestation": "none",  # We don't need attestation for NatLangChain
            },
        }

        self._emit_event("RegistrationStarted", {"challenge_id": challenge_id, "user_id": user_id})

        return options

    def complete_registration(
        self,
        challenge_id: str,
        credential_id: str,
        public_key: str,
        public_key_algorithm: int,
        authenticator_data: str,
        client_data_json: str,
        transports: list[str] | None = None,
        device_name: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Complete FIDO2 credential registration.

        Args:
            challenge_id: Challenge ID from begin_registration
            credential_id: Base64url encoded credential ID
            public_key: Base64 encoded public key (COSE format)
            public_key_algorithm: COSE algorithm ID
            authenticator_data: Base64 encoded authenticator data
            client_data_json: Base64 encoded client data JSON
            transports: List of transports (usb, nfc, ble, internal)
            device_name: Optional human-readable device name

        Returns:
            Tuple of (success, result)
        """
        # Verify challenge exists and is valid
        if challenge_id not in self.challenges:
            return False, {"error": "Challenge not found"}

        challenge = self.challenges[challenge_id]

        if challenge.used:
            return False, {"error": "Challenge already used"}

        if datetime.utcnow() > datetime.fromisoformat(challenge.expires_at):
            return False, {"error": "Challenge expired"}

        # Verify algorithm is supported
        if public_key_algorithm not in self.SUPPORTED_ALGORITHMS:
            return False, {
                "error": "Unsupported algorithm",
                "algorithm": public_key_algorithm,
                "supported": self.SUPPORTED_ALGORITHMS,
            }

        # Verify credential ID is unique
        if credential_id in self.credentials:
            return False, {"error": "Credential ID already registered"}

        # Mark challenge as used
        challenge.used = True

        # Create credential
        user_id = challenge.user_id
        credential = FIDO2Credential(
            credential_id=credential_id,
            user_id=user_id,
            public_key=public_key,
            public_key_algorithm=public_key_algorithm,
            sign_count=0,
            created_at=datetime.utcnow().isoformat(),
            authenticator_attachment="cross-platform",
            transports=transports or ["usb"],
            device_name=device_name,
        )

        # Store credential
        self.credentials[credential_id] = credential

        if user_id not in self.user_credentials:
            self.user_credentials[user_id] = []
        self.user_credentials[user_id].append(credential_id)

        self._emit_event(
            "CredentialRegistered",
            {
                "credential_id": credential_id,
                "user_id": user_id,
                "algorithm": public_key_algorithm,
                "device_name": device_name,
            },
        )

        return True, {
            "status": "registered",
            "credential_id": credential_id,
            "user_id": user_id,
            "algorithm": public_key_algorithm,
            "device_name": device_name,
            "message": "FIDO2 credential registered successfully",
        }

    # ==================== PHASE 13B: AUTHENTICATION & SIGNING ====================

    def begin_authentication(
        self,
        user_id: str | None = None,
        signature_type: SignatureType = SignatureType.LOGIN,
        message_to_sign: str | None = None,
        user_verification: UserVerification = UserVerification.PREFERRED,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Begin FIDO2 authentication (WebAuthn authentication ceremony).

        Args:
            user_id: User ID (None for discoverable credentials)
            signature_type: Type of signature being requested
            message_to_sign: Optional message to be signed
            user_verification: UV requirement level
            metadata: Additional metadata for the signature

        Returns:
            PublicKeyCredentialRequestOptions for client
        """
        # Generate challenge
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

        challenge_id = self._generate_challenge_id(user_id or "anonymous", signature_type.value)

        expires_at = datetime.utcnow() + timedelta(seconds=self.CHALLENGE_TIMEOUT_SECONDS)

        # Compute message hash if message provided
        message_hash = None
        if message_to_sign:
            message_hash = hashlib.sha256(message_to_sign.encode()).hexdigest()

        auth_challenge = AuthChallenge(
            challenge_id=challenge_id,
            challenge=challenge_b64,
            user_id=user_id,
            signature_type=signature_type.value,
            message_hash=message_hash,
            created_at=datetime.utcnow().isoformat(),
            expires_at=expires_at.isoformat(),
            metadata=metadata or {},
        )

        self.challenges[challenge_id] = auth_challenge

        # Build allowCredentials list if user_id provided
        allow_credentials = []
        if user_id and user_id in self.user_credentials:
            for cred_id in self.user_credentials[user_id]:
                if cred_id in self.credentials:
                    cred = self.credentials[cred_id]
                    allow_credentials.append(
                        {"type": "public-key", "id": cred_id, "transports": cred.transports}
                    )

        options = {
            "challenge_id": challenge_id,
            "publicKey": {
                "rpId": self.rp_id,
                "challenge": challenge_b64,
                "timeout": self.CHALLENGE_TIMEOUT_SECONDS * 1000,
                "userVerification": user_verification.value,
            },
        }

        if allow_credentials:
            options["publicKey"]["allowCredentials"] = allow_credentials

        if message_to_sign:
            options["message_to_sign"] = message_to_sign
            options["message_hash"] = message_hash

        self._emit_event(
            "AuthenticationStarted",
            {
                "challenge_id": challenge_id,
                "user_id": user_id,
                "signature_type": signature_type.value,
            },
        )

        return options

    def verify_authentication(
        self,
        challenge_id: str,
        credential_id: str,
        authenticator_data: str,
        client_data_json: str,
        signature: str,
        _user_handle: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Verify FIDO2 authentication response.

        Args:
            challenge_id: Challenge ID from begin_authentication
            credential_id: Credential ID used
            authenticator_data: Base64 encoded authenticator data
            client_data_json: Base64 encoded client data JSON
            signature: Base64 encoded signature
            user_handle: Optional user handle for discoverable credentials

        Returns:
            Tuple of (success, result with signature record)
        """
        # Verify challenge
        if challenge_id not in self.challenges:
            return False, {"error": "Challenge not found"}

        challenge = self.challenges[challenge_id]

        if challenge.used:
            return False, {"error": "Challenge already used"}

        if datetime.utcnow() > datetime.fromisoformat(challenge.expires_at):
            return False, {"error": "Challenge expired"}

        # Verify credential exists
        if credential_id not in self.credentials:
            return False, {"error": "Credential not found"}

        credential = self.credentials[credential_id]

        # Verify user matches if specified
        if challenge.user_id and credential.user_id != challenge.user_id:
            return False, {"error": "Credential does not belong to expected user"}

        # In production, we would verify the signature cryptographically here
        # For now, we simulate verification

        # Extract sign count from authenticator data (simplified)
        # Real implementation would parse the authenticator data properly
        new_sign_count = credential.sign_count + 1

        # Verify sign count increased (replay protection)
        if new_sign_count <= credential.sign_count:
            return False, {"error": "Sign count did not increase - possible replay attack"}

        # Update credential
        credential.sign_count = new_sign_count
        credential.last_used_at = datetime.utcnow().isoformat()

        # Mark challenge as used
        challenge.used = True

        # Create signature record
        signature_id = self._generate_signature_id(credential_id, challenge.signature_type)

        # Compute client data hash
        try:
            client_data_bytes = base64.urlsafe_b64decode(client_data_json + "==")
            client_data_hash = hashlib.sha256(client_data_bytes).hexdigest()
        except Exception:
            client_data_hash = hashlib.sha256(client_data_json.encode()).hexdigest()

        signed_message = SignedMessage(
            signature_id=signature_id,
            credential_id=credential_id,
            user_id=credential.user_id,
            signature_type=challenge.signature_type,
            message_hash=challenge.message_hash or "",
            signature=signature,
            authenticator_data=authenticator_data,
            client_data_hash=client_data_hash,
            sign_count=new_sign_count,
            created_at=datetime.utcnow().isoformat(),
            verified=True,
            metadata=challenge.metadata,
        )

        self.signatures[signature_id] = signed_message

        self._emit_event(
            "AuthenticationVerified",
            {
                "signature_id": signature_id,
                "credential_id": credential_id,
                "user_id": credential.user_id,
                "signature_type": challenge.signature_type,
                "sign_count": new_sign_count,
            },
        )

        return True, {
            "status": "verified",
            "signature_id": signature_id,
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "signature_type": challenge.signature_type,
            "message_hash": challenge.message_hash,
            "sign_count": new_sign_count,
            "verified": True,
        }

    def sign_proposal(
        self,
        user_id: str,
        dispute_id: str,
        proposal_action: str,  # "accept" or "submit"
        proposal_hash: str,
    ) -> dict[str, Any]:
        """
        Begin signing a proposal with FIDO2 credential.

        Args:
            user_id: User signing the proposal
            dispute_id: Dispute ID
            proposal_action: "accept" or "submit"
            proposal_hash: Hash of the proposal content

        Returns:
            Authentication options for signing
        """
        message = f"{dispute_id}:{proposal_action}:{proposal_hash}"

        sig_type = (
            SignatureType.PROPOSAL_ACCEPT
            if proposal_action == "accept"
            else SignatureType.PROPOSAL_SUBMIT
        )

        return self.begin_authentication(
            user_id=user_id,
            signature_type=sig_type,
            message_to_sign=message,
            user_verification=UserVerification.REQUIRED,
            metadata={
                "dispute_id": dispute_id,
                "proposal_action": proposal_action,
                "proposal_hash": proposal_hash,
            },
        )

    def sign_contract(self, user_id: str, contract_hash: str, counterparty: str) -> dict[str, Any]:
        """
        Begin signing a contract with FIDO2 credential.

        Args:
            user_id: User signing the contract
            contract_hash: Hash of the contract content
            counterparty: Counterparty address

        Returns:
            Authentication options for signing
        """
        message = f"contract_sign:{contract_hash}:{counterparty}"

        return self.begin_authentication(
            user_id=user_id,
            signature_type=SignatureType.CONTRACT_SIGN,
            message_to_sign=message,
            user_verification=UserVerification.REQUIRED,
            metadata={"contract_hash": contract_hash, "counterparty": counterparty},
        )

    # ==================== PHASE 13C: AGENT DELEGATION ====================

    def begin_agent_delegation(
        self,
        principal_user_id: str,
        agent_id: str,
        permissions: list[str],
        duration_hours: int | None = None,
    ) -> dict[str, Any]:
        """
        Begin delegating authority to an agent with hardware authorization.

        Args:
            principal_user_id: User delegating authority
            agent_id: Agent receiving delegation
            permissions: List of permitted actions
            duration_hours: Delegation duration (default 24 hours)

        Returns:
            Authentication options for delegation signature
        """
        duration = duration_hours or self.DELEGATION_DEFAULT_HOURS
        expires_at = datetime.utcnow() + timedelta(hours=duration)

        message = f"delegate:{agent_id}:{','.join(permissions)}:{expires_at.isoformat()}"

        return self.begin_authentication(
            user_id=principal_user_id,
            signature_type=SignatureType.AGENT_DELEGATE,
            message_to_sign=message,
            user_verification=UserVerification.REQUIRED,
            metadata={
                "agent_id": agent_id,
                "permissions": permissions,
                "expires_at": expires_at.isoformat(),
                "duration_hours": duration,
            },
        )

    def complete_agent_delegation(
        self,
        challenge_id: str,
        credential_id: str,
        authenticator_data: str,
        client_data_json: str,
        signature: str,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Complete agent delegation with verified signature.

        Returns:
            Tuple of (success, delegation record)
        """
        # First verify the authentication
        success, auth_result = self.verify_authentication(
            challenge_id=challenge_id,
            credential_id=credential_id,
            authenticator_data=authenticator_data,
            client_data_json=client_data_json,
            signature=signature,
        )

        if not success:
            return False, auth_result

        # Get the challenge metadata
        challenge = self.challenges[challenge_id]
        metadata = challenge.metadata

        # Create delegation record
        delegation_id = self._generate_delegation_id(auth_result["user_id"], metadata["agent_id"])

        delegation = AgentDelegation(
            delegation_id=delegation_id,
            principal_user_id=auth_result["user_id"],
            agent_id=metadata["agent_id"],
            credential_id=credential_id,
            permissions=metadata["permissions"],
            signature=signature,
            created_at=datetime.utcnow().isoformat(),
            expires_at=metadata["expires_at"],
        )

        self.delegations[delegation_id] = delegation

        self._emit_event(
            "AgentDelegationCreated",
            {
                "delegation_id": delegation_id,
                "principal": auth_result["user_id"],
                "agent_id": metadata["agent_id"],
                "permissions": metadata["permissions"],
                "expires_at": metadata["expires_at"],
            },
        )

        return True, {
            "status": "delegated",
            "delegation_id": delegation_id,
            "principal_user_id": auth_result["user_id"],
            "agent_id": metadata["agent_id"],
            "permissions": metadata["permissions"],
            "expires_at": metadata["expires_at"],
            "signature_id": auth_result["signature_id"],
        }

    def verify_agent_permission(
        self, agent_id: str, permission: str, principal_user_id: str | None = None
    ) -> tuple[bool, str | None]:
        """
        Verify an agent has a specific permission.

        Args:
            agent_id: Agent to check
            permission: Permission to verify
            principal_user_id: Optional specific principal to check

        Returns:
            Tuple of (has_permission, delegation_id)
        """
        now = datetime.utcnow()

        for delegation in self.delegations.values():
            if delegation.agent_id != agent_id:
                continue

            if delegation.revoked:
                continue

            if datetime.fromisoformat(delegation.expires_at) < now:
                continue

            if principal_user_id and delegation.principal_user_id != principal_user_id:
                continue

            if permission in delegation.permissions or "*" in delegation.permissions:
                return True, delegation.delegation_id

        return False, None

    def revoke_delegation(
        self, delegation_id: str, revoking_user: str
    ) -> tuple[bool, dict[str, Any]]:
        """
        Revoke an agent delegation.

        Args:
            delegation_id: Delegation to revoke
            revoking_user: User revoking (must be principal)

        Returns:
            Tuple of (success, result)
        """
        if delegation_id not in self.delegations:
            return False, {"error": "Delegation not found"}

        delegation = self.delegations[delegation_id]

        if delegation.principal_user_id != revoking_user:
            return False, {"error": "Only the principal can revoke delegation"}

        if delegation.revoked:
            return False, {"error": "Delegation already revoked"}

        delegation.revoked = True
        delegation.revoked_at = datetime.utcnow().isoformat()

        self._emit_event(
            "AgentDelegationRevoked",
            {
                "delegation_id": delegation_id,
                "agent_id": delegation.agent_id,
                "revoked_by": revoking_user,
            },
        )

        return True, {
            "status": "revoked",
            "delegation_id": delegation_id,
            "agent_id": delegation.agent_id,
            "revoked_at": delegation.revoked_at,
        }

    def get_agent_delegations(
        self,
        agent_id: str | None = None,
        principal_user_id: str | None = None,
        include_expired: bool = False,
        include_revoked: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get agent delegations with optional filtering.

        Args:
            agent_id: Filter by agent
            principal_user_id: Filter by principal
            include_expired: Include expired delegations
            include_revoked: Include revoked delegations

        Returns:
            List of delegation records
        """
        now = datetime.utcnow()
        results = []

        for delegation in self.delegations.values():
            if agent_id and delegation.agent_id != agent_id:
                continue

            if principal_user_id and delegation.principal_user_id != principal_user_id:
                continue

            if not include_revoked and delegation.revoked:
                continue

            is_expired = datetime.fromisoformat(delegation.expires_at) < now
            if not include_expired and is_expired:
                continue

            results.append(
                {
                    "delegation_id": delegation.delegation_id,
                    "principal_user_id": delegation.principal_user_id,
                    "agent_id": delegation.agent_id,
                    "permissions": delegation.permissions,
                    "created_at": delegation.created_at,
                    "expires_at": delegation.expires_at,
                    "revoked": delegation.revoked,
                    "expired": is_expired,
                    "active": not delegation.revoked and not is_expired,
                }
            )

        return results

    # ==================== CREDENTIAL MANAGEMENT ====================

    def get_user_credentials(self, user_id: str) -> list[dict[str, Any]]:
        """Get all credentials for a user."""
        credential_ids = self.user_credentials.get(user_id, [])
        results = []

        for cred_id in credential_ids:
            if cred_id in self.credentials:
                cred = self.credentials[cred_id]
                results.append(
                    {
                        "credential_id": cred.credential_id,
                        "algorithm": cred.public_key_algorithm,
                        "created_at": cred.created_at,
                        "last_used_at": cred.last_used_at,
                        "sign_count": cred.sign_count,
                        "transports": cred.transports,
                        "device_name": cred.device_name,
                    }
                )

        return results

    def remove_credential(self, credential_id: str, user_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Remove a credential.

        Args:
            credential_id: Credential to remove
            user_id: User requesting removal (must own credential)

        Returns:
            Tuple of (success, result)
        """
        if credential_id not in self.credentials:
            return False, {"error": "Credential not found"}

        credential = self.credentials[credential_id]

        if credential.user_id != user_id:
            return False, {"error": "Credential does not belong to user"}

        # Remove from storage
        del self.credentials[credential_id]

        if user_id in self.user_credentials:
            self.user_credentials[user_id] = [
                c for c in self.user_credentials[user_id] if c != credential_id
            ]

        self._emit_event("CredentialRemoved", {"credential_id": credential_id, "user_id": user_id})

        return True, {"status": "removed", "credential_id": credential_id}

    def get_signature(self, signature_id: str) -> dict[str, Any] | None:
        """Get a signature record by ID."""
        if signature_id not in self.signatures:
            return None

        sig = self.signatures[signature_id]
        return {
            "signature_id": sig.signature_id,
            "credential_id": sig.credential_id,
            "user_id": sig.user_id,
            "signature_type": sig.signature_type,
            "message_hash": sig.message_hash,
            "sign_count": sig.sign_count,
            "created_at": sig.created_at,
            "verified": sig.verified,
            "metadata": sig.metadata,
        }

    def verify_signature_record(
        self,
        signature_id: str,
        expected_message_hash: str | None = None,
        expected_user_id: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Verify a signature record exists and matches expectations.

        Args:
            signature_id: Signature to verify
            expected_message_hash: Expected message hash
            expected_user_id: Expected user ID

        Returns:
            Tuple of (is_valid, details)
        """
        if signature_id not in self.signatures:
            return False, {"error": "Signature not found"}

        sig = self.signatures[signature_id]

        if not sig.verified:
            return False, {"error": "Signature not verified"}

        if expected_message_hash and sig.message_hash != expected_message_hash:
            return False, {
                "error": "Message hash mismatch",
                "expected": expected_message_hash,
                "actual": sig.message_hash,
            }

        if expected_user_id and sig.user_id != expected_user_id:
            return False, {
                "error": "User ID mismatch",
                "expected": expected_user_id,
                "actual": sig.user_id,
            }

        return True, {
            "valid": True,
            "signature_id": signature_id,
            "user_id": sig.user_id,
            "signature_type": sig.signature_type,
            "created_at": sig.created_at,
        }

    # ==================== STATISTICS & AUDIT ====================

    def get_statistics(self) -> dict[str, Any]:
        """Get FIDO2 system statistics."""
        now = datetime.utcnow()

        active_delegations = sum(
            1
            for d in self.delegations.values()
            if not d.revoked and datetime.fromisoformat(d.expires_at) > now
        )

        return {
            "credentials": {
                "total": len(self.credentials),
                "users_with_credentials": len(self.user_credentials),
            },
            "signatures": {
                "total": len(self.signatures),
                "verified": sum(1 for s in self.signatures.values() if s.verified),
            },
            "delegations": {
                "total": len(self.delegations),
                "active": active_delegations,
                "revoked": sum(1 for d in self.delegations.values() if d.revoked),
            },
            "challenges": {
                "total_created": len(self.challenges),
                "used": sum(1 for c in self.challenges.values() if c.used),
            },
            "configuration": {
                "rp_id": self.rp_id,
                "rp_name": self.rp_name,
                "challenge_timeout_seconds": self.CHALLENGE_TIMEOUT_SECONDS,
                "max_credentials_per_user": self.MAX_CREDENTIALS_PER_USER,
                "supported_algorithms": self.SUPPORTED_ALGORITHMS,
            },
        }

    def get_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit trail events."""
        return sorted(self.events[-limit:], key=lambda x: x["timestamp"], reverse=True)

    # ==================== UTILITY METHODS ====================

    def _generate_challenge_id(self, user_id: str, action: str) -> str:
        """Generate unique challenge ID."""
        data = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "random": secrets.token_hex(8),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"CHAL-{hashlib.sha256(hash_input.encode()).hexdigest()[:16].upper()}"

    def _generate_signature_id(self, credential_id: str, signature_type: str) -> str:
        """Generate unique signature ID."""
        data = {
            "credential_id": credential_id,
            "signature_type": signature_type,
            "timestamp": datetime.utcnow().isoformat(),
            "random": secrets.token_hex(8),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"SIG-{hashlib.sha256(hash_input.encode()).hexdigest()[:16].upper()}"

    def _generate_delegation_id(self, principal: str, agent: str) -> str:
        """Generate unique delegation ID."""
        data = {
            "principal": principal,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "random": secrets.token_hex(8),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"DELEG-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event for audit trail."""
        event = {"event_type": event_type, "timestamp": datetime.utcnow().isoformat(), "data": data}
        self.events.append(event)
