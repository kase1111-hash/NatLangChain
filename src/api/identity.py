"""
NatLangChain - Identity API Blueprint

REST API endpoints for DID identity management.
Provides access to:
- Create and resolve DIDs
- Manage verification methods (keys)
- Key rotation
- Service endpoints
- Delegations
- Author linking and verification
"""

import re

from flask import Blueprint, jsonify, request

from .state import managers
from .utils import DEFAULT_PAGE_LIMIT, require_api_key

identity_bp = Blueprint("identity", __name__)

# Email validation pattern (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email: str) -> tuple[bool, str | None]:
    """
    Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return True, None  # Email is optional

    if len(email) > 254:  # RFC 5321 max email length
        return False, "Email address exceeds maximum length of 254 characters"

    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email address format"

    return True, None


# =============================================================================
# DID Management Endpoints
# =============================================================================


@identity_bp.route("/identity/did", methods=["POST"])
@require_api_key
def create_did():
    """
    Create a new DID with document.

    Request body:
        {
            "display_name": "Alice",           // Optional
            "email": "alice@example.com",      // Optional, creates mapping
            "profile_data": {...},             // Optional profile data
            "also_known_as": ["..."],          // Optional alternative IDs
            "services": [                      // Optional service endpoints
                {
                    "type": "LinkedDomains",
                    "endpoint": "https://example.com"
                }
            ]
        }

    Returns:
        DID, document, and private keys (STORE SECURELY!)
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    # Validate email if provided
    email = data.get("email")
    if email:
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

    # Create identity
    did, doc, private_keys = managers.identity_service.create_identity(
        display_name=data.get("display_name"),
        email=email,
        profile_data=data.get("profile_data"),
    )

    # Add any additional also_known_as
    if data.get("also_known_as"):
        for aka in data["also_known_as"]:
            if aka not in doc.also_known_as:
                doc.also_known_as.append(aka)

    # Add additional services
    if data.get("services"):
        for svc in data["services"]:
            managers.identity_service.registry.add_service(
                did,
                svc.get("type", "LinkedDomains"),
                svc.get("endpoint", ""),
                svc.get("description"),
            )

    return (
        jsonify(
            {
                "did": did,
                "document": doc.to_dict(),
                "private_keys": private_keys,
                "warning": "Store private keys securely! They cannot be recovered.",
            }
        ),
        201,
    )


@identity_bp.route("/identity/did/<path:did>", methods=["GET"])
@require_api_key
def resolve_did(did):
    """
    Resolve a DID to its document.

    Path params:
        did: The DID to resolve (e.g., did:nlc:z6Mk...)

    Returns:
        DID Resolution result with document and metadata
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    result = managers.identity_service.registry.resolve(did)

    if result.did_resolution_metadata.get("error"):
        return jsonify(result.to_dict()), 404

    return jsonify(result.to_dict())


@identity_bp.route("/identity/did/<path:did>", methods=["PATCH"])
@require_api_key
def update_did(did):
    """
    Update a DID document.

    Path params:
        did: The DID to update

    Request body:
        {
            "also_known_as": ["..."],      // Optional
            "controller": "did:nlc:...",   // Optional
            "authorized_by": "did:nlc:..." // Required, DID authorizing update
        }

    Returns:
        Update result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    # Require authorization
    if not data.get("authorized_by"):
        return jsonify({"error": "authorized_by is required for DID updates"}), 400

    updates = {}
    if "also_known_as" in data:
        updates["also_known_as"] = data["also_known_as"]
    if "controller" in data:
        updates["controller"] = data["controller"]

    success, result = managers.identity_service.registry.update_document(
        did, updates, authorized_by=data["authorized_by"]
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/did/<path:did>/deactivate", methods=["POST"])
@require_api_key
def deactivate_did(did):
    """
    Deactivate a DID (permanent).

    Path params:
        did: The DID to deactivate

    Returns:
        Deactivation result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    success, result = managers.identity_service.registry.deactivate(did)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


# =============================================================================
# Verification Method (Key) Endpoints
# =============================================================================


@identity_bp.route("/identity/did/<path:did>/keys", methods=["POST"])
@require_api_key
def add_key(did):
    """
    Add a new verification method (key) to a DID.

    Path params:
        did: The DID to add key to

    Request body:
        {
            "type": "Ed25519VerificationKey2020",  // Key type
            "relationships": ["authentication", "assertionMethod"],  // Optional
            "expires_in_days": 365  // Optional expiration
        }

    Returns:
        New key info including private key (STORE SECURELY!)
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    # Parse key type
    from did_identity import VerificationMethodType, VerificationRelationship

    try:
        key_type = VerificationMethodType(data.get("type", "Ed25519VerificationKey2020"))
    except ValueError:
        return jsonify({"error": f"Invalid key type: {data.get('type')}"}), 400

    # Parse relationships
    relationships = None
    if data.get("relationships"):
        try:
            relationships = [VerificationRelationship(r) for r in data["relationships"]]
        except ValueError as e:
            return jsonify({"error": f"Invalid relationship: {e}"}), 400

    success, result = managers.identity_service.registry.add_verification_method(
        did,
        key_type,
        relationships=relationships,
        expires_in_days=data.get("expires_in_days"),
    )

    if success:
        result["warning"] = "Store private key securely! It cannot be recovered."
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/did/<path:did>/keys/<key_id>/revoke", methods=["POST"])
@require_api_key
def revoke_key(did, key_id):
    """
    Revoke a verification method (key).

    Path params:
        did: The DID
        key_id: The key ID (e.g., "key-1" or full ID)

    Returns:
        Revocation result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    # Handle both short and full key IDs
    full_key_id = key_id if key_id.startswith("did:") else f"{did}#{key_id}"

    success, result = managers.identity_service.registry.revoke_verification_method(did, full_key_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/did/<path:did>/keys/<key_id>/rotate", methods=["POST"])
@require_api_key
def rotate_key(did, key_id):
    """
    Rotate a key - create new key and schedule old for revocation.

    Path params:
        did: The DID
        key_id: The key ID to rotate

    Request body:
        {
            "reason": "Scheduled rotation",  // Optional
            "grace_period_days": 30          // Optional, default 30
        }

    Returns:
        Rotation result with new key info
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    # Handle both short and full key IDs
    full_key_id = key_id if key_id.startswith("did:") else f"{did}#{key_id}"

    success, result = managers.identity_service.registry.rotate_key(
        did,
        full_key_id,
        reason=data.get("reason"),
        grace_period_days=data.get("grace_period_days", 30),
    )

    if success:
        result["new_key"]["warning"] = "Store private key securely!"
        return jsonify(result)
    else:
        return jsonify(result), 400


# =============================================================================
# Service Endpoint Management
# =============================================================================


@identity_bp.route("/identity/did/<path:did>/services", methods=["POST"])
@require_api_key
def add_service(did):
    """
    Add a service endpoint to a DID.

    Path params:
        did: The DID

    Request body:
        {
            "type": "LinkedDomains",
            "endpoint": "https://example.com",
            "description": "My website"  // Optional
        }

    Returns:
        Service info
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("type") or not data.get("endpoint"):
        return jsonify({"error": "type and endpoint are required"}), 400

    success, result = managers.identity_service.registry.add_service(
        did,
        data["type"],
        data["endpoint"],
        data.get("description"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/did/<path:did>/services/<service_id>", methods=["DELETE"])
@require_api_key
def remove_service(did, service_id):
    """
    Remove a service endpoint from a DID.

    Path params:
        did: The DID
        service_id: The service ID (e.g., "service-1")

    Returns:
        Removal result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    # Handle both short and full service IDs
    full_service_id = service_id if service_id.startswith("did:") else f"{did}#{service_id}"

    success, result = managers.identity_service.registry.remove_service(did, full_service_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


# =============================================================================
# Delegation Endpoints
# =============================================================================


@identity_bp.route("/identity/delegations", methods=["POST"])
@require_api_key
def grant_delegation():
    """
    Grant delegation from one DID to another.

    Request body:
        {
            "delegator": "did:nlc:...",
            "delegate": "did:nlc:...",
            "capabilities": ["update", "sign"],
            "constraints": {...},        // Optional
            "expires_in_days": 90        // Optional
        }

    Returns:
        Delegation info
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    required = ["delegator", "delegate", "capabilities"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    success, result = managers.identity_service.registry.grant_delegation(
        delegator=data["delegator"],
        delegate=data["delegate"],
        capabilities=data["capabilities"],
        constraints=data.get("constraints"),
        expires_in_days=data.get("expires_in_days"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/delegations/<delegation_id>/revoke", methods=["POST"])
@require_api_key
def revoke_delegation(delegation_id):
    """
    Revoke a delegation.

    Path params:
        delegation_id: The delegation ID

    Returns:
        Revocation result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    success, result = managers.identity_service.registry.revoke_delegation(delegation_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/did/<path:did>/delegations", methods=["GET"])
@require_api_key
def get_delegations(did):
    """
    Get delegations for a DID.

    Path params:
        did: The DID

    Query params:
        as_delegator: Include delegations where DID is delegator (default: true)
        as_delegate: Include delegations where DID is delegate (default: true)
        valid_only: Only include valid delegations (default: true)

    Returns:
        List of delegations
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    as_delegator = request.args.get("as_delegator", "true").lower() == "true"
    as_delegate = request.args.get("as_delegate", "true").lower() == "true"
    valid_only = request.args.get("valid_only", "true").lower() == "true"

    delegations = managers.identity_service.registry.get_delegations(
        did, as_delegator=as_delegator, as_delegate=as_delegate, valid_only=valid_only
    )

    return jsonify({"did": did, "count": len(delegations), "delegations": [d.to_dict() for d in delegations]})


# =============================================================================
# Author Linking and Verification
# =============================================================================


@identity_bp.route("/identity/link", methods=["POST"])
@require_api_key
def link_author():
    """
    Link an author identifier (e.g., email) to a DID.

    Request body:
        {
            "author": "alice@example.com",
            "did": "did:nlc:..."
        }

    Returns:
        Link result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("author") or not data.get("did"):
        return jsonify({"error": "author and did are required"}), 400

    success, result = managers.identity_service.link_author(data["author"], data["did"])

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@identity_bp.route("/identity/resolve/<path:author>", methods=["GET"])
@require_api_key
def resolve_author(author):
    """
    Resolve an author identifier to a DID.

    Path params:
        author: Author identifier (email, DID, or other)

    Returns:
        DID if found
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    did = managers.identity_service.resolve_author(author)

    if did:
        return jsonify({"author": author, "did": did})
    else:
        return jsonify({"error": "Author not found", "author": author}), 404


@identity_bp.route("/identity/verify", methods=["POST"])
@require_api_key
def verify_authorship():
    """
    Verify entry authorship.

    Request body:
        {
            "entry_hash": "abc123...",
            "claimed_author": "alice@example.com",
            "signature": "..."  // Optional
        }

    Returns:
        Verification result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("entry_hash") or not data.get("claimed_author"):
        return jsonify({"error": "entry_hash and claimed_author are required"}), 400

    result = managers.identity_service.verify_entry_authorship(
        entry_hash=data["entry_hash"],
        claimed_author=data["claimed_author"],
        signature=data.get("signature"),
    )

    status_code = 200 if result.get("verified") else 400
    return jsonify(result), status_code


@identity_bp.route("/identity/authenticate", methods=["POST"])
@require_api_key
def verify_authentication():
    """
    Verify that a key can authenticate for a DID.

    Request body:
        {
            "did": "did:nlc:...",
            "key_id": "key-1"
        }

    Returns:
        Authentication verification result
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("did") or not data.get("key_id"):
        return jsonify({"error": "did and key_id are required"}), 400

    # Handle both short and full key IDs
    key_id = data["key_id"]
    if not key_id.startswith("did:"):
        key_id = f"{data['did']}#{key_id}"

    is_valid, reason = managers.identity_service.registry.verify_authentication(data["did"], key_id)

    return jsonify({"valid": is_valid, "reason": reason, "did": data["did"], "key_id": key_id})


# =============================================================================
# Statistics and Events
# =============================================================================


@identity_bp.route("/identity/statistics", methods=["GET"])
@require_api_key
def get_statistics():
    """
    Get identity service statistics.

    Returns:
        Comprehensive statistics
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    return jsonify(managers.identity_service.get_statistics())


@identity_bp.route("/identity/events", methods=["GET"])
@require_api_key
def get_events():
    """
    Get DID event log.

    Query params:
        limit: Maximum events to return (default: 100)
        did: Filter by DID (optional)
        event_type: Filter by event type (optional)

    Returns:
        List of events
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    did_filter = request.args.get("did")
    event_type = request.args.get("event_type")

    events = managers.identity_service.registry.events

    if did_filter:
        events = [e for e in events if e.did == did_filter]

    if event_type:
        events = [e for e in events if e.event_type.value == event_type]

    events = events[-limit:]

    return jsonify({"count": len(events), "events": [e.to_dict() for e in reversed(events)]})


@identity_bp.route("/identity/did/<path:did>/history", methods=["GET"])
@require_api_key
def get_did_history(did):
    """
    Get event history for a specific DID.

    Path params:
        did: The DID

    Returns:
        Event history
    """
    if not managers.identity_service:
        return jsonify({"error": "Identity service not initialized"}), 503

    events = [e for e in managers.identity_service.registry.events if e.did == did]

    # Include rotation history
    rotations = managers.identity_service.registry.rotation_history.get(did, [])

    return jsonify(
        {
            "did": did,
            "events": [e.to_dict() for e in events],
            "key_rotations": [r.to_dict() for r in rotations],
        }
    )


# =============================================================================
# Supported Types
# =============================================================================


@identity_bp.route("/identity/types/keys", methods=["GET"])
def get_key_types():
    """
    Get supported verification method types.

    Returns:
        List of supported key types
    """
    from did_identity import VerificationMethodType

    return jsonify({"types": [t.value for t in VerificationMethodType]})


@identity_bp.route("/identity/types/relationships", methods=["GET"])
def get_relationship_types():
    """
    Get supported verification relationships.

    Returns:
        List of supported relationships
    """
    from did_identity import VerificationRelationship

    return jsonify({"relationships": [r.value for r in VerificationRelationship]})


@identity_bp.route("/identity/types/services", methods=["GET"])
def get_service_types():
    """
    Get common service endpoint types.

    Returns:
        List of common service types
    """
    from did_identity import ServiceType

    return jsonify({"types": [t.value for t in ServiceType]})
