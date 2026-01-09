"""
NatLangChain - Revenue Sharing API Blueprint

REST API endpoints for royalty configuration and revenue distribution.
Enables programmable royalties for derivative intent chains.

Provides access to:
- Configure royalties for entries/contracts
- Record revenue events
- Calculate and distribute royalties
- Claim accumulated revenue
- View earnings and analytics
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

from .state import managers

revenue_bp = Blueprint("revenue", __name__)


# =============================================================================
# Royalty Configuration Endpoints
# =============================================================================


@revenue_bp.route("/revenue/royalties", methods=["POST"])
def configure_royalties():
    """
    Configure royalties for an entry/contract.

    Request body:
        {
            "block_index": 1,
            "entry_index": 0,
            "owner": "did:nlc:...",
            "royalty_type": "fixed",              // fixed, tiered, split, none
            "base_rate": "5.0",                   // Percentage (0-50)
            "tiered_rates": {                     // Optional, for tiered type
                "amendment": "3.0",
                "extension": "5.0"
            },
            "split_recipients": {                 // Optional, for split type
                "did:nlc:coauthor...": "30"
            },
            "chain_propagation": true,            // Propagate through derivatives
            "max_depth": 10,                      // Max chain depth
            "depth_decay": "0.5",                 // Decay per level
            "min_payment": "0.01",                // Minimum payment threshold
            "metadata": {...}                     // Optional
        }

    Returns:
        Royalty configuration info
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    required = ["block_index", "entry_index", "owner"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from revenue_sharing import RoyaltyType

    # Parse royalty type
    royalty_type = RoyaltyType.FIXED
    if data.get("royalty_type"):
        try:
            royalty_type = RoyaltyType(data["royalty_type"])
        except ValueError:
            return jsonify({"error": f"Invalid royalty_type: {data['royalty_type']}"}), 400

    # Parse decimal values
    base_rate = Decimal(str(data.get("base_rate", "5.0"))) if data.get("base_rate") else None
    depth_decay = Decimal(str(data["depth_decay"])) if data.get("depth_decay") else None
    min_payment = Decimal(str(data["min_payment"])) if data.get("min_payment") else None

    tiered_rates = None
    if data.get("tiered_rates"):
        tiered_rates = {k: Decimal(str(v)) for k, v in data["tiered_rates"].items()}

    split_recipients = None
    if data.get("split_recipients"):
        split_recipients = {k: Decimal(str(v)) for k, v in data["split_recipients"].items()}

    success, result = managers.revenue_service.configure_royalties(
        block_index=data["block_index"],
        entry_index=data["entry_index"],
        owner=data["owner"],
        royalty_type=royalty_type,
        base_rate=base_rate,
        tiered_rates=tiered_rates,
        split_recipients=split_recipients,
        chain_propagation=data.get("chain_propagation", True),
        max_depth=data.get("max_depth", 10),
        depth_decay=depth_decay,
        min_payment=min_payment,
        metadata=data.get("metadata"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@revenue_bp.route("/revenue/royalties/<int:block_index>/<int:entry_index>", methods=["GET"])
def get_royalty_config(block_index, entry_index):
    """
    Get royalty configuration for an entry.

    Path params:
        block_index: Block index
        entry_index: Entry index

    Returns:
        Royalty configuration if exists
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    config = managers.revenue_service.get_royalty_config(block_index, entry_index)
    if not config:
        return jsonify({"error": "No royalty config found for entry"}), 404

    return jsonify(config.to_dict())


@revenue_bp.route("/revenue/royalties/<int:block_index>/<int:entry_index>", methods=["PATCH"])
def update_royalty_config(block_index, entry_index):
    """
    Update royalty configuration.

    Path params:
        block_index: Block index
        entry_index: Entry index

    Request body:
        {
            "owner": "did:nlc:...",               // Required for auth
            "base_rate": "7.5",                   // Optional
            "tiered_rates": {...},                // Optional
            "split_recipients": {...},            // Optional
            "chain_propagation": true,            // Optional
            "max_depth": 5,                       // Optional
            "is_active": true                     // Optional
        }

    Returns:
        Updated configuration
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("owner"):
        return jsonify({"error": "owner is required for authorization"}), 400

    # Convert decimal strings
    updates = dict(data)
    if "base_rate" in updates:
        updates["base_rate"] = Decimal(str(updates["base_rate"]))
    if "tiered_rates" in updates:
        updates["tiered_rates"] = {k: Decimal(str(v)) for k, v in updates["tiered_rates"].items()}
    if "split_recipients" in updates:
        updates["split_recipients"] = {k: Decimal(str(v)) for k, v in updates["split_recipients"].items()}

    success, result = managers.revenue_service.update_royalty_config(
        block_index=block_index,
        entry_index=entry_index,
        owner=data["owner"],
        updates=updates,
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@revenue_bp.route("/revenue/royalties/<int:block_index>/<int:entry_index>/disable", methods=["POST"])
def disable_royalties(block_index, entry_index):
    """
    Disable royalties for an entry.

    Path params:
        block_index: Block index
        entry_index: Entry index

    Request body:
        {
            "owner": "did:nlc:..."  // Required for auth
        }

    Returns:
        Disable result
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("owner"):
        return jsonify({"error": "owner is required for authorization"}), 400

    success, result = managers.revenue_service.disable_royalties(
        block_index=block_index,
        entry_index=entry_index,
        owner=data["owner"],
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


# =============================================================================
# Revenue Event Endpoints
# =============================================================================


@revenue_bp.route("/revenue/events", methods=["POST"])
def record_revenue_event():
    """
    Record a revenue-generating event.

    Request body:
        {
            "block_index": 1,
            "entry_index": 0,
            "event_type": "derivative_created",  // derivative_created, contract_executed, license_purchased, tip, bounty, marketplace_sale, custom
            "amount": "100.00",
            "currency": "NLC",                   // Optional, default NLC
            "payer": "did:nlc:...",             // Optional
            "derivative_type": "amendment",      // Optional
            "metadata": {...}                    // Optional
        }

    Returns:
        Event info with calculated royalties
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    required = ["block_index", "entry_index", "event_type", "amount"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from revenue_sharing import RevenueEventType

    try:
        event_type = RevenueEventType(data["event_type"])
    except ValueError:
        return jsonify({"error": f"Invalid event_type: {data['event_type']}"}), 400

    success, result = managers.revenue_service.record_revenue_event(
        block_index=data["block_index"],
        entry_index=data["entry_index"],
        event_type=event_type,
        amount=Decimal(str(data["amount"])),
        currency=data.get("currency", "NLC"),
        payer=data.get("payer"),
        derivative_type=data.get("derivative_type"),
        metadata=data.get("metadata"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@revenue_bp.route("/revenue/events/<event_id>", methods=["GET"])
def get_revenue_event(event_id):
    """
    Get a revenue event by ID.

    Path params:
        event_id: The event ID

    Returns:
        Event info
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    event = managers.revenue_service.revenue_events.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    return jsonify(event.to_dict())


@revenue_bp.route("/revenue/events", methods=["GET"])
def list_revenue_events():
    """
    List revenue events.

    Query params:
        block_index: Filter by source block (optional)
        entry_index: Filter by source entry (optional)
        event_type: Filter by event type (optional)
        limit: Max results (default: 100)

    Returns:
        List of events
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    block_index = request.args.get("block_index", type=int)
    entry_index = request.args.get("entry_index", type=int)
    event_type_str = request.args.get("event_type")
    limit = request.args.get("limit", 100, type=int)

    events = list(managers.revenue_service.revenue_events.values())

    # Apply filters
    if block_index is not None:
        events = [e for e in events if e.source_entry_ref["block_index"] == block_index]
    if entry_index is not None:
        events = [e for e in events if e.source_entry_ref["entry_index"] == entry_index]
    if event_type_str:
        events = [e for e in events if e.event_type.value == event_type_str]

    events = events[-limit:]

    return jsonify({
        "count": len(events),
        "events": [e.to_dict() for e in events],
    })


# =============================================================================
# Revenue Pool & Claims Endpoints
# =============================================================================


@revenue_bp.route("/revenue/pools/<path:recipient>", methods=["GET"])
def get_pool(recipient):
    """
    Get revenue pool for a recipient.

    Path params:
        recipient: Recipient DID

    Returns:
        Pool info with balances
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    pool = managers.revenue_service.get_pool(recipient)
    if not pool:
        return jsonify({
            "recipient": recipient,
            "balances": {},
            "total_earned": {},
            "total_claimed": {},
            "pending_payment_count": 0,
        })

    return jsonify(pool.to_dict())


@revenue_bp.route("/revenue/balance/<path:recipient>", methods=["GET"])
def get_balance(recipient):
    """
    Get available balance for a recipient.

    Path params:
        recipient: Recipient DID

    Query params:
        currency: Currency type (default: NLC)

    Returns:
        Available balance
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    currency = request.args.get("currency", "NLC")
    balance = managers.revenue_service.get_balance(recipient, currency)

    return jsonify({
        "recipient": recipient,
        "currency": currency,
        "available_balance": str(balance),
    })


@revenue_bp.route("/revenue/claims", methods=["POST"])
def claim_revenue():
    """
    Claim accumulated revenue.

    Request body:
        {
            "recipient": "did:nlc:...",
            "amount": "50.00",                   // Optional, null = all available
            "currency": "NLC",                   // Optional, default NLC
            "destination_address": "0x..."       // Optional external address
        }

    Returns:
        Claim info
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("recipient"):
        return jsonify({"error": "recipient is required"}), 400

    amount = Decimal(str(data["amount"])) if data.get("amount") else None

    success, result = managers.revenue_service.claim_revenue(
        recipient=data["recipient"],
        amount=amount,
        currency=data.get("currency", "NLC"),
        destination_address=data.get("destination_address"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@revenue_bp.route("/revenue/claims/<claim_id>", methods=["GET"])
def get_claim(claim_id):
    """
    Get a claim by ID.

    Path params:
        claim_id: The claim ID

    Returns:
        Claim info
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    claim = managers.revenue_service.claims.get(claim_id)
    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    return jsonify(claim.to_dict())


@revenue_bp.route("/revenue/claims", methods=["GET"])
def list_claims():
    """
    List claims.

    Query params:
        recipient: Filter by recipient DID (optional)
        status: Filter by status (optional)
        limit: Max results (default: 100)

    Returns:
        List of claims
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    from revenue_sharing import ClaimStatus

    recipient = request.args.get("recipient")
    status_str = request.args.get("status")
    limit = request.args.get("limit", 100, type=int)

    status = None
    if status_str:
        try:
            status = ClaimStatus(status_str)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_str}"}), 400

    claims = managers.revenue_service.get_claims(recipient=recipient, status=status)
    claims = claims[-limit:]

    return jsonify({
        "count": len(claims),
        "claims": [c.to_dict() for c in claims],
    })


# =============================================================================
# Payment Endpoints
# =============================================================================


@revenue_bp.route("/revenue/payments/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    """
    Get a payment by ID.

    Path params:
        payment_id: The payment ID

    Returns:
        Payment info
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    payment = managers.revenue_service.payments.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify(payment.to_dict())


@revenue_bp.route("/revenue/payments", methods=["GET"])
def list_payments():
    """
    List payments.

    Query params:
        recipient: Filter by recipient DID (optional)
        event_id: Filter by event ID (optional)
        status: Filter by status (optional)
        limit: Max results (default: 100)

    Returns:
        List of payments
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    from revenue_sharing import PaymentStatus

    recipient = request.args.get("recipient")
    event_id = request.args.get("event_id")
    status_str = request.args.get("status")
    limit = request.args.get("limit", 100, type=int)

    payments = list(managers.revenue_service.payments.values())

    if recipient:
        payments = [p for p in payments if p.recipient == recipient]
    if event_id:
        payments = [p for p in payments if p.event_id == event_id]
    if status_str:
        try:
            status = PaymentStatus(status_str)
            payments = [p for p in payments if p.status == status]
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_str}"}), 400

    payments = payments[-limit:]

    return jsonify({
        "count": len(payments),
        "payments": [p.to_dict() for p in payments],
    })


# =============================================================================
# Analytics Endpoints
# =============================================================================


@revenue_bp.route("/revenue/earnings/<int:block_index>/<int:entry_index>", methods=["GET"])
def get_entry_earnings(block_index, entry_index):
    """
    Get total earnings for an entry.

    Path params:
        block_index: Block index
        entry_index: Entry index

    Returns:
        Entry earnings summary
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    return jsonify(managers.revenue_service.get_entry_earnings(block_index, entry_index))


@revenue_bp.route("/revenue/chain/<int:block_index>/<int:entry_index>", methods=["GET"])
def get_chain_revenue(block_index, entry_index):
    """
    Get total revenue generated by an entry and its derivatives.

    Path params:
        block_index: Block index
        entry_index: Entry index

    Returns:
        Chain revenue breakdown
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    return jsonify(managers.revenue_service.get_chain_revenue(block_index, entry_index))


@revenue_bp.route("/revenue/estimate", methods=["POST"])
def estimate_royalties():
    """
    Estimate royalty distribution for a potential revenue event.

    Request body:
        {
            "block_index": 1,
            "entry_index": 0,
            "amount": "100.00",
            "derivative_type": "amendment"       // Optional
        }

    Returns:
        Estimated distribution breakdown
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    data = request.get_json() or {}

    required = ["block_index", "entry_index", "amount"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    result = managers.revenue_service.estimate_royalties(
        block_index=data["block_index"],
        entry_index=data["entry_index"],
        amount=Decimal(str(data["amount"])),
        derivative_type=data.get("derivative_type"),
    )

    return jsonify(result)


# =============================================================================
# Statistics and Events
# =============================================================================


@revenue_bp.route("/revenue/statistics", methods=["GET"])
def get_statistics():
    """
    Get revenue sharing statistics.

    Returns:
        Comprehensive statistics
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    return jsonify(managers.revenue_service.get_statistics())


@revenue_bp.route("/revenue/audit", methods=["GET"])
def get_audit_events():
    """
    Get audit trail events.

    Query params:
        limit: Maximum events to return (default: 100)
        event_type: Filter by event type (optional)

    Returns:
        List of audit events
    """
    if not managers.revenue_service:
        return jsonify({"error": "Revenue service not initialized"}), 503

    limit = request.args.get("limit", 100, type=int)
    event_type_filter = request.args.get("event_type")

    events = managers.revenue_service.events

    if event_type_filter:
        events = [e for e in events if e.event_type == event_type_filter]

    events = events[-limit:]

    return jsonify({
        "count": len(events),
        "events": [e.to_dict() for e in reversed(events)],
    })


# =============================================================================
# Supported Types
# =============================================================================


@revenue_bp.route("/revenue/types/royalty", methods=["GET"])
def get_royalty_types():
    """
    Get supported royalty types.

    Returns:
        List of supported royalty types
    """
    from revenue_sharing import RoyaltyType

    return jsonify({"types": [t.value for t in RoyaltyType]})


@revenue_bp.route("/revenue/types/events", methods=["GET"])
def get_event_types():
    """
    Get supported revenue event types.

    Returns:
        List of supported event types
    """
    from revenue_sharing import RevenueEventType

    return jsonify({"types": [t.value for t in RevenueEventType]})


@revenue_bp.route("/revenue/types/payment_status", methods=["GET"])
def get_payment_statuses():
    """
    Get supported payment statuses.

    Returns:
        List of supported payment statuses
    """
    from revenue_sharing import PaymentStatus

    return jsonify({"statuses": [s.value for s in PaymentStatus]})


@revenue_bp.route("/revenue/types/claim_status", methods=["GET"])
def get_claim_statuses():
    """
    Get supported claim statuses.

    Returns:
        List of supported claim statuses
    """
    from revenue_sharing import ClaimStatus

    return jsonify({"statuses": [s.value for s in ClaimStatus]})
