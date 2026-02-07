"""
NatLangChain - DID Identity Layer

W3C-compliant Decentralized Identifier (DID) system for NatLangChain.
Inspired by Ceramic Network's approach to decentralized identity.

Features:
- W3C DID Core specification compliance
- Multiple verification method types (Ed25519, secp256k1, X25519)
- Service endpoints for discovery
- Controller relationships and delegation
- Key rotation with history
- Integration with NatLangChain entries for identity verification

DID Method: did:nlc (NatLangChain)
Format: did:nlc:<unique-identifier>

Example:
    did:nlc:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

DID_METHOD = "nlc"  # NatLangChain DID method
DID_CONTEXT = "https://www.w3.org/ns/did/v1"
DID_CONTEXT_ED25519 = "https://w3id.org/security/suites/ed25519-2020/v1"
DID_CONTEXT_SECP256K1 = "https://w3id.org/security/suites/secp256k1-2019/v1"
DID_CONTEXT_X25519 = "https://w3id.org/security/suites/x25519-2020/v1"

# Key configuration
DEFAULT_KEY_TYPE = "Ed25519VerificationKey2020"
KEY_ROTATION_GRACE_PERIOD_DAYS = 30

# Resolution caching
RESOLUTION_CACHE_TTL_SECONDS = 300


# =============================================================================
# Enums
# =============================================================================


class VerificationMethodType(Enum):
    """Supported verification method types."""

    ED25519_VERIFICATION_KEY_2020 = "Ed25519VerificationKey2020"
    ECDSA_SECP256K1_VERIFICATION_KEY_2019 = "EcdsaSecp256k1VerificationKey2019"
    X25519_KEY_AGREEMENT_KEY_2020 = "X25519KeyAgreementKey2020"
    JSON_WEB_KEY_2020 = "JsonWebKey2020"


class VerificationRelationship(Enum):
    """DID verification relationships."""

    AUTHENTICATION = "authentication"
    ASSERTION_METHOD = "assertionMethod"
    KEY_AGREEMENT = "keyAgreement"
    CAPABILITY_INVOCATION = "capabilityInvocation"
    CAPABILITY_DELEGATION = "capabilityDelegation"


class ServiceType(Enum):
    """Common service endpoint types."""

    NATLANGCHAIN_PROFILE = "NatLangChainProfile"
    NATLANGCHAIN_MESSAGING = "NatLangChainMessaging"
    LINKED_DOMAINS = "LinkedDomains"
    DID_COMM_MESSAGING = "DIDCommMessaging"
    CREDENTIAL_REGISTRY = "CredentialRegistry"


class DIDEventType(Enum):
    """Types of DID events."""

    CREATED = "created"
    UPDATED = "updated"
    DEACTIVATED = "deactivated"
    KEY_ADDED = "key_added"
    KEY_REVOKED = "key_revoked"
    KEY_ROTATED = "key_rotated"
    SERVICE_ADDED = "service_added"
    SERVICE_REMOVED = "service_removed"
    CONTROLLER_ADDED = "controller_added"
    CONTROLLER_REMOVED = "controller_removed"
    DELEGATION_GRANTED = "delegation_granted"
    DELEGATION_REVOKED = "delegation_revoked"


class DIDStatus(Enum):
    """DID document status."""

    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    SUSPENDED = "suspended"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VerificationMethod:
    """A verification method in a DID document."""

    id: str  # e.g., "did:nlc:abc123#key-1"
    type: VerificationMethodType
    controller: str  # DID that controls this key
    public_key_multibase: str | None = None  # Multibase-encoded public key
    public_key_jwk: dict[str, Any] | None = None  # JWK format
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    revoked_at: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to W3C DID document format."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "controller": self.controller,
        }
        if self.public_key_multibase:
            result["publicKeyMultibase"] = self.public_key_multibase
        if self.public_key_jwk:
            result["publicKeyJwk"] = self.public_key_jwk
        return result

    def is_valid(self) -> bool:
        """Check if verification method is currently valid."""
        if self.revoked_at:
            return False
        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at)
            if datetime.utcnow() > expiry:
                return False
        return True


@dataclass
class ServiceEndpoint:
    """A service endpoint in a DID document."""

    id: str  # e.g., "did:nlc:abc123#profile"
    type: str | ServiceType
    service_endpoint: str | list[str] | dict[str, Any]
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to W3C DID document format."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, ServiceType) else self.type,
            "serviceEndpoint": self.service_endpoint,
        }
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class DIDDocument:
    """W3C DID Document representation."""

    id: str  # The DID
    controller: str | list[str] | None = None
    also_known_as: list[str] = field(default_factory=list)
    verification_method: list[VerificationMethod] = field(default_factory=list)
    authentication: list[str] = field(default_factory=list)  # References to verification methods
    assertion_method: list[str] = field(default_factory=list)
    key_agreement: list[str] = field(default_factory=list)
    capability_invocation: list[str] = field(default_factory=list)
    capability_delegation: list[str] = field(default_factory=list)
    service: list[ServiceEndpoint] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: DIDStatus = DIDStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        """Convert to W3C DID document format."""
        result: dict[str, Any] = {
            "@context": [
                DID_CONTEXT,
                DID_CONTEXT_ED25519,
                DID_CONTEXT_SECP256K1,
                DID_CONTEXT_X25519,
            ],
            "id": self.id,
        }

        if self.controller:
            result["controller"] = self.controller
        if self.also_known_as:
            result["alsoKnownAs"] = self.also_known_as
        if self.verification_method:
            result["verificationMethod"] = [vm.to_dict() for vm in self.verification_method]
        if self.authentication:
            result["authentication"] = self.authentication
        if self.assertion_method:
            result["assertionMethod"] = self.assertion_method
        if self.key_agreement:
            result["keyAgreement"] = self.key_agreement
        if self.capability_invocation:
            result["capabilityInvocation"] = self.capability_invocation
        if self.capability_delegation:
            result["capabilityDelegation"] = self.capability_delegation
        if self.service:
            result["service"] = [s.to_dict() for s in self.service]

        return result

    def get_verification_method(self, method_id: str) -> VerificationMethod | None:
        """Get a verification method by ID."""
        for vm in self.verification_method:
            if vm.id == method_id or vm.id.endswith(f"#{method_id}"):
                return vm
        return None

    def get_valid_verification_methods(self) -> list[VerificationMethod]:
        """Get all valid (non-revoked, non-expired) verification methods."""
        return [vm for vm in self.verification_method if vm.is_valid()]


@dataclass
class DIDResolutionResult:
    """Result of DID resolution."""

    did_document: DIDDocument | None
    did_document_metadata: dict[str, Any]
    did_resolution_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to DID Resolution result format."""
        return {
            "didDocument": self.did_document.to_dict() if self.did_document else None,
            "didDocumentMetadata": self.did_document_metadata,
            "didResolutionMetadata": self.did_resolution_metadata,
        }


@dataclass
class Delegation:
    """Delegation of capabilities from one DID to another."""

    id: str
    delegator: str  # DID granting the delegation
    delegate: str  # DID receiving the delegation
    capabilities: list[str]  # What capabilities are delegated
    constraints: dict[str, Any] = field(default_factory=dict)  # Constraints on delegation
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str | None = None
    revoked_at: str | None = None

    def is_valid(self) -> bool:
        """Check if delegation is currently valid."""
        if self.revoked_at:
            return False
        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at)
            if datetime.utcnow() > expiry:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "delegator": self.delegator,
            "delegate": self.delegate,
            "capabilities": self.capabilities,
            "constraints": self.constraints,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "valid": self.is_valid(),
        }


@dataclass
class KeyRotationRecord:
    """Record of a key rotation event."""

    rotation_id: str
    did: str
    old_key_id: str
    new_key_id: str
    rotated_at: str
    reason: str | None = None
    grace_period_ends: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rotation_id": self.rotation_id,
            "did": self.did,
            "old_key_id": self.old_key_id,
            "new_key_id": self.new_key_id,
            "rotated_at": self.rotated_at,
            "reason": self.reason,
            "grace_period_ends": self.grace_period_ends,
        }


@dataclass
class DIDEvent:
    """Event in DID history."""

    event_id: str
    event_type: DIDEventType
    did: str
    timestamp: str
    data: dict[str, Any]
    signature: str | None = None  # Optional signature proving authorization

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "did": self.did,
            "timestamp": self.timestamp,
            "data": self.data,
            "signature": self.signature,
        }


# =============================================================================
# Key Generation Utilities
# =============================================================================


class KeyGenerator:
    """Utilities for generating cryptographic keys."""

    @staticmethod
    def generate_identifier() -> str:
        """Generate a unique identifier for a DID."""
        # Generate 32 random bytes and encode as multibase (base58btc)
        random_bytes = secrets.token_bytes(32)
        # Simplified: use base64url encoding prefixed with 'z' (base58btc indicator)
        encoded = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
        return f"z{encoded}"

    @staticmethod
    def generate_key_pair(
        key_type: VerificationMethodType = VerificationMethodType.ED25519_VERIFICATION_KEY_2020,
    ) -> tuple[str, str]:
        """
        Generate a key pair for the specified type.

        Returns:
            Tuple of (public_key_multibase, private_key_multibase)

        Note: In production, this would use actual cryptographic libraries.
        This is a simplified implementation for demonstration.
        """
        # Generate random bytes for keys (simplified)
        if key_type in [
            VerificationMethodType.ED25519_VERIFICATION_KEY_2020,
            VerificationMethodType.X25519_KEY_AGREEMENT_KEY_2020,
        ]:
            # Ed25519/X25519: 32-byte keys
            private_bytes = secrets.token_bytes(32)
            # Derive public key (simplified - in reality would use actual Ed25519)
            public_bytes = hashlib.sha256(private_bytes).digest()
        else:
            # secp256k1: 32-byte private, 33-byte compressed public
            private_bytes = secrets.token_bytes(32)
            public_bytes = hashlib.sha256(private_bytes).digest() + b"\x02"

        # Encode as multibase (base64url with 'z' prefix for base58btc compatibility)
        public_multibase = "z" + base64.urlsafe_b64encode(public_bytes).decode().rstrip("=")
        private_multibase = "z" + base64.urlsafe_b64encode(private_bytes).decode().rstrip("=")

        return public_multibase, private_multibase

    @staticmethod
    def generate_did() -> str:
        """Generate a new DID."""
        identifier = KeyGenerator.generate_identifier()
        return f"did:{DID_METHOD}:{identifier}"


# =============================================================================
# DID Registry
# =============================================================================


class DIDRegistry:
    """
    Registry for managing DID documents.

    This is the core storage and management layer for DIDs in NatLangChain.
    """

    def __init__(self):
        self.documents: dict[str, DIDDocument] = {}
        self.delegations: dict[str, Delegation] = {}
        self.rotation_history: dict[str, list[KeyRotationRecord]] = {}
        self.events: list[DIDEvent] = []
        self._resolution_cache: dict[str, tuple[DIDResolutionResult, float]] = {}

    def create_did(
        self,
        controller: str | None = None,
        also_known_as: list[str] | None = None,
        add_default_keys: bool = True,
        services: list[dict[str, Any]] | None = None,
    ) -> tuple[str, DIDDocument, dict[str, str]]:
        """
        Create a new DID with document.

        Args:
            controller: Optional controller DID (defaults to self)
            also_known_as: Optional alternative identifiers
            add_default_keys: Whether to add default verification methods
            services: Optional service endpoints to add

        Returns:
            Tuple of (did, document, private_keys)
        """
        did = KeyGenerator.generate_did()
        private_keys: dict[str, str] = {}

        # Create document
        doc = DIDDocument(
            id=did,
            controller=controller or did,
            also_known_as=also_known_as or [],
        )

        # Add default verification methods if requested
        if add_default_keys:
            # Authentication key (Ed25519)
            auth_pub, auth_priv = KeyGenerator.generate_key_pair(
                VerificationMethodType.ED25519_VERIFICATION_KEY_2020
            )
            auth_method = VerificationMethod(
                id=f"{did}#key-1",
                type=VerificationMethodType.ED25519_VERIFICATION_KEY_2020,
                controller=did,
                public_key_multibase=auth_pub,
            )
            doc.verification_method.append(auth_method)
            doc.authentication.append(f"{did}#key-1")
            doc.assertion_method.append(f"{did}#key-1")
            private_keys["key-1"] = auth_priv

            # Key agreement key (X25519)
            ka_pub, ka_priv = KeyGenerator.generate_key_pair(
                VerificationMethodType.X25519_KEY_AGREEMENT_KEY_2020
            )
            ka_method = VerificationMethod(
                id=f"{did}#key-2",
                type=VerificationMethodType.X25519_KEY_AGREEMENT_KEY_2020,
                controller=did,
                public_key_multibase=ka_pub,
            )
            doc.verification_method.append(ka_method)
            doc.key_agreement.append(f"{did}#key-2")
            private_keys["key-2"] = ka_priv

        # Add services if provided
        if services:
            for i, svc in enumerate(services):
                service = ServiceEndpoint(
                    id=f"{did}#service-{i + 1}",
                    type=svc.get("type", ServiceType.NATLANGCHAIN_PROFILE),
                    service_endpoint=svc.get("endpoint", ""),
                    description=svc.get("description"),
                )
                doc.service.append(service)

        # Store document
        self.documents[did] = doc

        # Emit creation event
        self._emit_event(
            DIDEventType.CREATED,
            did,
            {
                "verification_methods": len(doc.verification_method),
                "services": len(doc.service),
            },
        )

        return did, doc, private_keys

    def resolve(self, did: str, use_cache: bool = True) -> DIDResolutionResult:
        """
        Resolve a DID to its document.

        Args:
            did: The DID to resolve
            use_cache: Whether to use cached resolution

        Returns:
            DID Resolution result
        """
        import time

        # Check cache
        if use_cache and did in self._resolution_cache:
            cached, timestamp = self._resolution_cache[did]
            if time.time() - timestamp < RESOLUTION_CACHE_TTL_SECONDS:
                return cached

        # Validate DID format
        if not did.startswith(f"did:{DID_METHOD}:"):
            return DIDResolutionResult(
                did_document=None,
                did_document_metadata={},
                did_resolution_metadata={
                    "error": "invalidDid",
                    "message": f"Invalid DID method. Expected 'did:{DID_METHOD}:...'",
                },
            )

        # Look up document
        doc = self.documents.get(did)

        if not doc:
            return DIDResolutionResult(
                did_document=None,
                did_document_metadata={},
                did_resolution_metadata={
                    "error": "notFound",
                    "message": f"DID {did} not found",
                },
            )

        # Build metadata
        doc_metadata: dict[str, Any] = {
            "created": doc.created,
            "updated": doc.updated,
        }

        if doc.status == DIDStatus.DEACTIVATED:
            doc_metadata["deactivated"] = True

        # Add version info from events
        did_events = [e for e in self.events if e.did == did]
        if did_events:
            doc_metadata["versionId"] = len(did_events)

        result = DIDResolutionResult(
            did_document=doc,
            did_document_metadata=doc_metadata,
            did_resolution_metadata={"contentType": "application/did+json"},
        )

        # Cache result
        self._resolution_cache[did] = (result, time.time())

        return result

    def update_document(
        self,
        did: str,
        updates: dict[str, Any],
        authorized_by: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Update a DID document.

        Args:
            did: The DID to update
            updates: Dictionary of updates to apply
            authorized_by: DID authorizing the update (must be controller)

        Returns:
            Tuple of (success, result_or_error)
        """
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        # Check authorization
        controller = doc.controller
        if isinstance(controller, list):
            authorized = authorized_by in controller if authorized_by else did in controller
        else:
            authorized = authorized_by == controller if authorized_by else did == controller

        if not authorized and authorized_by:
            # Check if authorized_by has delegation
            delegation = self._find_valid_delegation(controller, authorized_by, "update")
            if not delegation:
                return False, {"error": "Not authorized to update this DID"}

        # Apply updates
        changes = []

        if "also_known_as" in updates:
            doc.also_known_as = updates["also_known_as"]
            changes.append("also_known_as")

        if "controller" in updates:
            doc.controller = updates["controller"]
            changes.append("controller")

        # Update timestamp
        doc.updated = datetime.utcnow().isoformat()

        # Clear cache
        if did in self._resolution_cache:
            del self._resolution_cache[did]

        # Emit event
        self._emit_event(DIDEventType.UPDATED, did, {"changes": changes})

        return True, {"did": did, "updated": doc.updated, "changes": changes}

    def add_verification_method(
        self,
        did: str,
        key_type: VerificationMethodType,
        relationships: list[VerificationRelationship] | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Add a new verification method to a DID document.

        Returns:
            Tuple of (success, result with new key info)
        """
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        # Generate new key
        public_key, private_key = KeyGenerator.generate_key_pair(key_type)

        # Find next key index
        existing_indices = []
        for vm in doc.verification_method:
            if "#key-" in vm.id:
                try:
                    idx = int(vm.id.split("#key-")[1])
                    existing_indices.append(idx)
                except ValueError:
                    pass
        next_index = max(existing_indices, default=0) + 1

        # Create verification method
        key_id = f"{did}#key-{next_index}"
        vm = VerificationMethod(
            id=key_id,
            type=key_type,
            controller=did,
            public_key_multibase=public_key,
            expires_at=(
                (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
                if expires_in_days
                else None
            ),
        )

        doc.verification_method.append(vm)

        # Add to relationships
        relationships = relationships or [VerificationRelationship.AUTHENTICATION]
        for rel in relationships:
            if rel == VerificationRelationship.AUTHENTICATION:
                doc.authentication.append(key_id)
            elif rel == VerificationRelationship.ASSERTION_METHOD:
                doc.assertion_method.append(key_id)
            elif rel == VerificationRelationship.KEY_AGREEMENT:
                doc.key_agreement.append(key_id)
            elif rel == VerificationRelationship.CAPABILITY_INVOCATION:
                doc.capability_invocation.append(key_id)
            elif rel == VerificationRelationship.CAPABILITY_DELEGATION:
                doc.capability_delegation.append(key_id)

        doc.updated = datetime.utcnow().isoformat()

        # Clear cache
        if did in self._resolution_cache:
            del self._resolution_cache[did]

        # Emit event
        self._emit_event(
            DIDEventType.KEY_ADDED,
            did,
            {"key_id": key_id, "type": key_type.value, "relationships": [r.value for r in relationships]},
        )

        return True, {
            "key_id": key_id,
            "type": key_type.value,
            "public_key": public_key,
            "private_key": private_key,
            "relationships": [r.value for r in relationships],
            "expires_at": vm.expires_at,
        }

    def revoke_verification_method(self, did: str, key_id: str) -> tuple[bool, dict[str, Any]]:
        """Revoke a verification method."""
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        vm = doc.get_verification_method(key_id)
        if not vm:
            return False, {"error": "Verification method not found"}

        if vm.revoked_at:
            return False, {"error": "Verification method already revoked"}

        # Ensure at least one valid authentication key remains
        valid_auth_keys = [
            k for k in doc.authentication if doc.get_verification_method(k) and doc.get_verification_method(k).is_valid()
        ]
        if len(valid_auth_keys) <= 1 and key_id in doc.authentication:
            return False, {"error": "Cannot revoke last authentication key"}

        # Revoke
        vm.revoked_at = datetime.utcnow().isoformat()
        doc.updated = datetime.utcnow().isoformat()

        # Clear cache
        if did in self._resolution_cache:
            del self._resolution_cache[did]

        # Emit event
        self._emit_event(DIDEventType.KEY_REVOKED, did, {"key_id": key_id})

        return True, {"key_id": key_id, "revoked_at": vm.revoked_at}

    def rotate_key(
        self,
        did: str,
        old_key_id: str,
        reason: str | None = None,
        grace_period_days: int = KEY_ROTATION_GRACE_PERIOD_DAYS,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Rotate a key - create new key and schedule old key for revocation.

        Args:
            did: The DID
            old_key_id: The key to rotate
            reason: Optional reason for rotation
            grace_period_days: Days before old key is revoked

        Returns:
            Tuple of (success, result with new key info)
        """
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        old_vm = doc.get_verification_method(old_key_id)
        if not old_vm:
            return False, {"error": "Verification method not found"}

        if not old_vm.is_valid():
            return False, {"error": "Cannot rotate an invalid key"}

        # Determine relationships of old key
        relationships = []
        if old_key_id in doc.authentication or old_vm.id in doc.authentication:
            relationships.append(VerificationRelationship.AUTHENTICATION)
        if old_key_id in doc.assertion_method or old_vm.id in doc.assertion_method:
            relationships.append(VerificationRelationship.ASSERTION_METHOD)
        if old_key_id in doc.key_agreement or old_vm.id in doc.key_agreement:
            relationships.append(VerificationRelationship.KEY_AGREEMENT)

        # Create new key with same type and relationships
        success, new_key_result = self.add_verification_method(did, old_vm.type, relationships)

        if not success:
            return False, new_key_result

        # Schedule old key for revocation (set expiry)
        grace_end = datetime.utcnow() + timedelta(days=grace_period_days)
        old_vm.expires_at = grace_end.isoformat()

        # Record rotation
        rotation_id = f"rot_{secrets.token_hex(8)}"
        rotation = KeyRotationRecord(
            rotation_id=rotation_id,
            did=did,
            old_key_id=old_vm.id,
            new_key_id=new_key_result["key_id"],
            rotated_at=datetime.utcnow().isoformat(),
            reason=reason,
            grace_period_ends=grace_end.isoformat(),
        )

        if did not in self.rotation_history:
            self.rotation_history[did] = []
        self.rotation_history[did].append(rotation)

        # Emit event
        self._emit_event(
            DIDEventType.KEY_ROTATED,
            did,
            {
                "rotation_id": rotation_id,
                "old_key_id": old_vm.id,
                "new_key_id": new_key_result["key_id"],
                "grace_period_days": grace_period_days,
            },
        )

        return True, {
            "rotation_id": rotation_id,
            "old_key": {
                "id": old_vm.id,
                "expires_at": old_vm.expires_at,
            },
            "new_key": new_key_result,
            "grace_period_days": grace_period_days,
        }

    def add_service(
        self,
        did: str,
        service_type: str | ServiceType,
        endpoint: str | list[str] | dict[str, Any],
        description: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Add a service endpoint to a DID document."""
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        # Find next service index
        next_index = len(doc.service) + 1
        service_id = f"{did}#service-{next_index}"

        service = ServiceEndpoint(
            id=service_id,
            type=service_type,
            service_endpoint=endpoint,
            description=description,
        )

        doc.service.append(service)
        doc.updated = datetime.utcnow().isoformat()

        # Clear cache
        if did in self._resolution_cache:
            del self._resolution_cache[did]

        # Emit event
        self._emit_event(
            DIDEventType.SERVICE_ADDED,
            did,
            {
                "service_id": service_id,
                "type": service_type.value if isinstance(service_type, ServiceType) else service_type,
            },
        )

        return True, {"service_id": service_id, "service": service.to_dict()}

    def remove_service(self, did: str, service_id: str) -> tuple[bool, dict[str, Any]]:
        """Remove a service endpoint from a DID document."""
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        # Find and remove service
        for i, svc in enumerate(doc.service):
            if svc.id == service_id:
                doc.service.pop(i)
                doc.updated = datetime.utcnow().isoformat()

                # Clear cache
                if did in self._resolution_cache:
                    del self._resolution_cache[did]

                # Emit event
                self._emit_event(DIDEventType.SERVICE_REMOVED, did, {"service_id": service_id})

                return True, {"service_id": service_id, "removed": True}

        return False, {"error": "Service not found"}

    def deactivate(self, did: str) -> tuple[bool, dict[str, Any]]:
        """Deactivate a DID (permanently disable it)."""
        doc = self.documents.get(did)
        if not doc:
            return False, {"error": "DID not found"}

        if doc.status == DIDStatus.DEACTIVATED:
            return False, {"error": "DID already deactivated"}

        doc.status = DIDStatus.DEACTIVATED
        doc.updated = datetime.utcnow().isoformat()

        # Clear cache
        if did in self._resolution_cache:
            del self._resolution_cache[did]

        # Emit event
        self._emit_event(DIDEventType.DEACTIVATED, did, {})

        return True, {"did": did, "status": "deactivated", "deactivated_at": doc.updated}

    # =========================================================================
    # Delegation Management
    # =========================================================================

    def grant_delegation(
        self,
        delegator: str,
        delegate: str,
        capabilities: list[str],
        constraints: dict[str, Any] | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Grant delegation from one DID to another.

        Args:
            delegator: DID granting the delegation
            delegate: DID receiving the delegation
            capabilities: List of capabilities being delegated
            constraints: Optional constraints on the delegation
            expires_in_days: Optional expiration

        Returns:
            Tuple of (success, delegation info)
        """
        # Verify both DIDs exist
        if delegator not in self.documents:
            return False, {"error": "Delegator DID not found"}
        if delegate not in self.documents:
            return False, {"error": "Delegate DID not found"}

        delegation_id = f"del_{secrets.token_hex(8)}"
        delegation = Delegation(
            id=delegation_id,
            delegator=delegator,
            delegate=delegate,
            capabilities=capabilities,
            constraints=constraints or {},
            expires_at=(
                (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
                if expires_in_days
                else None
            ),
        )

        self.delegations[delegation_id] = delegation

        # Update delegate's DID document to reference capability delegation
        delegate_doc = self.documents[delegate]
        delegator_doc = self.documents[delegator]

        # Add delegator's keys to delegate's capabilityDelegation
        for vm in delegator_doc.verification_method:
            if vm.is_valid() and vm.id not in delegate_doc.capability_delegation:
                delegate_doc.capability_delegation.append(vm.id)

        # Emit event
        self._emit_event(
            DIDEventType.DELEGATION_GRANTED,
            delegator,
            {
                "delegation_id": delegation_id,
                "delegate": delegate,
                "capabilities": capabilities,
            },
        )

        return True, delegation.to_dict()

    def revoke_delegation(self, delegation_id: str) -> tuple[bool, dict[str, Any]]:
        """Revoke a delegation."""
        delegation = self.delegations.get(delegation_id)
        if not delegation:
            return False, {"error": "Delegation not found"}

        if delegation.revoked_at:
            return False, {"error": "Delegation already revoked"}

        delegation.revoked_at = datetime.utcnow().isoformat()

        # Emit event
        self._emit_event(
            DIDEventType.DELEGATION_REVOKED,
            delegation.delegator,
            {"delegation_id": delegation_id, "delegate": delegation.delegate},
        )

        return True, {"delegation_id": delegation_id, "revoked_at": delegation.revoked_at}

    def get_delegations(
        self, did: str, as_delegator: bool = True, as_delegate: bool = True, valid_only: bool = True
    ) -> list[Delegation]:
        """Get delegations for a DID."""
        results = []
        for delegation in self.delegations.values():
            if valid_only and not delegation.is_valid():
                continue
            if (as_delegator and delegation.delegator == did) or (as_delegate and delegation.delegate == did):
                results.append(delegation)
        return results

    # =========================================================================
    # Verification
    # =========================================================================

    def verify_control(self, did: str, controller_did: str) -> bool:
        """Verify that controller_did controls did."""
        doc = self.documents.get(did)
        if not doc:
            return False

        controller = doc.controller
        if isinstance(controller, list):
            return controller_did in controller
        return controller_did == controller

    def verify_authentication(self, did: str, key_id: str) -> tuple[bool, str]:
        """
        Verify that a key can authenticate for a DID.

        Returns:
            Tuple of (is_valid, reason)
        """
        doc = self.documents.get(did)
        if not doc:
            return False, "DID not found"

        # Check if key is in authentication relationship
        if key_id not in doc.authentication and f"{did}#{key_id}" not in doc.authentication:
            # Check if key is from a controller
            for auth_ref in doc.authentication:
                if "#" in auth_ref:
                    ref_did = auth_ref.split("#")[0]
                    if self.verify_control(did, ref_did):
                        return True, "Authenticated via controller"

            return False, "Key not in authentication relationship"

        # Get verification method
        vm = doc.get_verification_method(key_id)
        if not vm:
            return False, "Verification method not found"

        if not vm.is_valid():
            if vm.revoked_at:
                return False, "Key has been revoked"
            return False, "Key has expired"

        return True, "Valid authentication key"

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _find_valid_delegation(
        self, controller: str | list[str], authorized_by: str, capability: str
    ) -> Delegation | None:
        """Find a valid delegation that grants the specified capability."""
        controllers = [controller] if isinstance(controller, str) else controller

        for delegation in self.delegations.values():
            if not delegation.is_valid():
                continue
            if delegation.delegator in controllers and delegation.delegate == authorized_by:
                if capability in delegation.capabilities or "*" in delegation.capabilities:
                    return delegation
        return None

    def _emit_event(self, event_type: DIDEventType, did: str, data: dict[str, Any]) -> None:
        """Emit a DID event."""
        event = DIDEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            event_type=event_type,
            did=did,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
        )
        self.events.append(event)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics."""
        status_counts = {}
        for doc in self.documents.values():
            status = doc.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        total_keys = sum(len(doc.verification_method) for doc in self.documents.values())
        total_services = sum(len(doc.service) for doc in self.documents.values())

        valid_delegations = len([d for d in self.delegations.values() if d.is_valid()])

        return {
            "total_dids": len(self.documents),
            "status_distribution": status_counts,
            "total_verification_methods": total_keys,
            "total_services": total_services,
            "delegations": {
                "total": len(self.delegations),
                "valid": valid_delegations,
                "revoked": len(self.delegations) - valid_delegations,
            },
            "total_events": len(self.events),
            "rotation_history_count": sum(len(r) for r in self.rotation_history.values()),
        }


# =============================================================================
# Identity Service (High-Level Interface)
# =============================================================================


class IdentityService:
    """
    High-level identity service for NatLangChain.

    Provides integration between DIDs and NatLangChain entries,
    enabling verified authorship and identity-linked operations.
    """

    def __init__(self, registry: DIDRegistry | None = None):
        self.registry = registry or DIDRegistry()
        self._author_mappings: dict[str, str] = {}  # email/identifier -> DID

    def create_identity(
        self,
        display_name: str | None = None,
        email: str | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> tuple[str, DIDDocument, dict[str, str]]:
        """
        Create a new identity with optional profile data.

        Args:
            display_name: Optional display name
            email: Optional email for mapping
            profile_data: Optional additional profile data

        Returns:
            Tuple of (did, document, private_keys)
        """
        # Prepare services
        services = []
        if profile_data or display_name:
            profile = {
                "type": ServiceType.NATLANGCHAIN_PROFILE,
                "endpoint": {
                    "displayName": display_name,
                    **(profile_data or {}),
                },
                "description": "NatLangChain identity profile",
            }
            services.append(profile)

        # Create DID
        did, doc, private_keys = self.registry.create_did(services=services if services else None)

        # Create mapping if email provided
        if email:
            self._author_mappings[email] = did
            doc.also_known_as.append(f"mailto:{email}")

        return did, doc, private_keys

    def link_author(self, author_identifier: str, did: str) -> tuple[bool, dict[str, Any]]:
        """
        Link an author identifier (e.g., email) to a DID.

        Args:
            author_identifier: The identifier to link
            did: The DID to link to

        Returns:
            Tuple of (success, result)
        """
        if did not in self.registry.documents:
            return False, {"error": "DID not found"}

        # Check if already linked to different DID
        if author_identifier in self._author_mappings:
            existing = self._author_mappings[author_identifier]
            if existing != did:
                return False, {
                    "error": "Author identifier already linked to different DID",
                    "existing_did": existing,
                }

        self._author_mappings[author_identifier] = did

        # Add to alsoKnownAs
        doc = self.registry.documents[did]
        if author_identifier not in doc.also_known_as:
            if "@" in author_identifier:
                doc.also_known_as.append(f"mailto:{author_identifier}")
            else:
                doc.also_known_as.append(author_identifier)

        return True, {"author": author_identifier, "did": did}

    def resolve_author(self, author: str) -> str | None:
        """
        Resolve an author identifier to a DID.

        Args:
            author: Author identifier (email, DID, or other identifier)

        Returns:
            DID if found, None otherwise
        """
        # If already a DID
        if author.startswith("did:"):
            return author if author in self.registry.documents else None

        # Check mappings
        return self._author_mappings.get(author)

    def verify_entry_authorship(
        self,
        entry_hash: str,
        claimed_author: str,
        signature: str | None = None,
    ) -> dict[str, Any]:
        """
        Verify that an entry was authored by the claimed author.

        Args:
            entry_hash: Hash of the entry content
            claimed_author: Claimed author (DID or identifier)
            signature: Optional cryptographic signature

        Returns:
            Verification result
        """
        # Resolve author to DID
        did = self.resolve_author(claimed_author)
        if not did:
            return {
                "verified": False,
                "reason": "Author not found or not linked to a DID",
                "author": claimed_author,
            }

        # Get DID document
        resolution = self.registry.resolve(did)
        if not resolution.did_document:
            return {
                "verified": False,
                "reason": "Could not resolve DID",
                "did": did,
            }

        doc = resolution.did_document

        # Check DID status
        if doc.status != DIDStatus.ACTIVE:
            return {
                "verified": False,
                "reason": f"DID is {doc.status.value}",
                "did": did,
            }

        # If signature provided, verify it
        if signature:
            # Get valid authentication keys
            valid_auth_keys = [
                doc.get_verification_method(k)
                for k in doc.authentication
                if doc.get_verification_method(k) and doc.get_verification_method(k).is_valid()
            ]

            if not valid_auth_keys:
                return {
                    "verified": False,
                    "reason": "No valid authentication keys",
                    "did": did,
                }

            # In production, would verify signature against public keys
            # Simplified: accept if signature is present and keys exist
            return {
                "verified": True,
                "did": did,
                "verification_method": valid_auth_keys[0].id if valid_auth_keys else None,
                "entry_hash": entry_hash,
            }

        # Without signature, we can only confirm the author mapping exists
        return {
            "verified": True,
            "did": did,
            "note": "Author mapping verified, no signature provided",
            "entry_hash": entry_hash,
        }

    def get_author_entries(self, author: str) -> dict[str, Any]:
        """
        Get information about entries by an author.

        Note: This would integrate with the blockchain to retrieve actual entries.
        """
        did = self.resolve_author(author)
        if not did:
            return {"error": "Author not found"}

        return {
            "did": did,
            "author": author,
            "note": "Entry retrieval would integrate with NatLangChain blockchain",
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get identity service statistics."""
        registry_stats = self.registry.get_statistics()
        return {
            "registry": registry_stats,
            "author_mappings": len(self._author_mappings),
        }
