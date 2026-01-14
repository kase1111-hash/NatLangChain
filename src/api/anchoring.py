"""
NatLangChain - Anchoring API Blueprint

REST API endpoints for external blockchain anchoring.
Provides access to:
- Queue entries for anchoring
- Create anchor batches
- Retrieve and verify anchor proofs
- Cost estimation
"""

from flask import Blueprint, jsonify, request

from .state import managers

anchoring_bp = Blueprint("anchoring", __name__)


# =============================================================================
# Queue Management Endpoints
# =============================================================================


@anchoring_bp.route("/anchoring/queue", methods=["POST"])
def queue_for_anchoring():
    """
    Queue an entry for external anchoring.

    Request body:
        {
            "entry_hash": "abc123...",
            "block_index": 5,        // Optional
            "entry_index": 2,        // Optional
            "priority": 0            // Optional, higher = sooner
        }

    Returns:
        Queue result with position
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    data = request.get_json() or {}
    entry_hash = data.get("entry_hash")

    if not entry_hash:
        return jsonify({"error": "entry_hash is required"}), 400

    result = managers.anchoring_service.queue_entry(
        entry_hash=entry_hash,
        block_index=data.get("block_index"),
        entry_index=data.get("entry_index"),
        priority=data.get("priority", 0),
        metadata=data.get("metadata"),
    )

    return jsonify(result), 201 if result.get("status") == "queued" else 200


@anchoring_bp.route("/anchoring/queue/block", methods=["POST"])
def queue_block_for_anchoring():
    """
    Queue an entire block for anchoring.

    Request body:
        {
            "block_hash": "abc123...",
            "block_index": 5,
            "entry_count": 10
        }

    Returns:
        Queue result
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    data = request.get_json() or {}

    required = ["block_hash", "block_index", "entry_count"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    result = managers.anchoring_service.queue_block(
        block_hash=data["block_hash"],
        block_index=data["block_index"],
        entry_count=data["entry_count"],
    )

    return jsonify(result), 201


@anchoring_bp.route("/anchoring/queue/status", methods=["GET"])
def get_queue_status():
    """
    Get current anchor queue status.

    Returns:
        Queue status with pending entries
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    return jsonify(managers.anchoring_service.get_queue_status())


# =============================================================================
# Anchor Operations
# =============================================================================


@anchoring_bp.route("/anchoring/anchor", methods=["POST"])
def create_anchor():
    """
    Create and submit an anchor batch.

    Request body (optional):
        {
            "chain": "ethereum_mainnet",  // Optional, anchors to all if omitted
            "max_entries": 50             // Optional
        }

    Returns:
        Anchor result with batch details
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    data = request.get_json() or {}

    chain = None
    if data.get("chain"):
        try:
            from external_anchoring import AnchorChain

            chain = AnchorChain(data["chain"])
        except ValueError:
            return jsonify({"error": f"Invalid chain: {data['chain']}"}), 400

    success, result = managers.anchoring_service.create_anchor_batch(
        chain=chain,
        max_entries=data.get("max_entries"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@anchoring_bp.route("/anchoring/batch/<batch_id>/confirm", methods=["POST"])
def confirm_anchor(batch_id):
    """
    Confirm an anchor batch is confirmed on-chain.

    Path params:
        batch_id: The batch to confirm

    Returns:
        Confirmation result
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    success, result = managers.anchoring_service.confirm_anchor(batch_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@anchoring_bp.route("/anchoring/batch/<batch_id>", methods=["GET"])
def get_batch(batch_id):
    """
    Get anchor batch details.

    Path params:
        batch_id: The batch ID

    Returns:
        Batch details
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    if batch_id not in managers.anchoring_service.anchor_batches:
        return jsonify({"error": "Batch not found"}), 404

    batch = managers.anchoring_service.anchor_batches[batch_id]
    return jsonify(batch.to_dict())


# =============================================================================
# Proof Endpoints
# =============================================================================


@anchoring_bp.route("/anchoring/proof/<entry_hash>", methods=["GET"])
def get_proof(entry_hash):
    """
    Get anchor proofs for an entry.

    Path params:
        entry_hash: The entry hash

    Returns:
        List of anchor proofs
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    proofs = managers.anchoring_service.get_proof(entry_hash)

    if not proofs:
        return jsonify({"error": "No proofs found for entry"}), 404

    return jsonify({"entry_hash": entry_hash, "proofs": proofs})


@anchoring_bp.route("/anchoring/proof/<entry_hash>/verify", methods=["POST"])
def verify_proof(entry_hash):
    """
    Verify anchor proofs for an entry.

    Path params:
        entry_hash: The entry hash

    Request body (optional):
        {
            "chain": "ethereum_mainnet"  // Verify specific chain only
        }

    Returns:
        Verification result
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    data = request.get_json() or {}

    chain = None
    if data.get("chain"):
        try:
            from external_anchoring import AnchorChain

            chain = AnchorChain(data["chain"])
        except ValueError:
            return jsonify({"error": f"Invalid chain: {data['chain']}"}), 400

    result = managers.anchoring_service.verify_proof(entry_hash, chain)

    status_code = 200 if result.get("verified") else 400
    return jsonify(result), status_code


@anchoring_bp.route("/anchoring/proof/<entry_hash>/legal", methods=["GET"])
def get_legal_proof(entry_hash):
    """
    Generate legal proof document for an entry.

    Path params:
        entry_hash: The entry hash

    Returns:
        Comprehensive legal proof document
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    result = managers.anchoring_service.generate_legal_proof(entry_hash)

    if "error" in result:
        return jsonify(result), 404

    return jsonify(result)


# =============================================================================
# Cost Estimation
# =============================================================================


@anchoring_bp.route("/anchoring/estimate", methods=["GET"])
def estimate_costs():
    """
    Estimate anchoring costs.

    Query params:
        entries: Number of entries (uses pending count if omitted)

    Returns:
        Cost estimates per provider
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    entry_count = request.args.get("entries", type=int)

    return jsonify(managers.anchoring_service.estimate_costs(entry_count))


# =============================================================================
# Statistics and Configuration
# =============================================================================


@anchoring_bp.route("/anchoring/statistics", methods=["GET"])
def get_statistics():
    """
    Get anchoring statistics.

    Returns:
        Comprehensive statistics
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    return jsonify(managers.anchoring_service.get_statistics())


@anchoring_bp.route("/anchoring/providers", methods=["GET"])
def get_providers():
    """
    Get configured anchor providers.

    Returns:
        List of providers
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    return jsonify({"providers": managers.anchoring_service.get_providers()})


@anchoring_bp.route("/anchoring/chains", methods=["GET"])
def get_supported_chains():
    """
    Get all supported anchor chains.

    Returns:
        List of supported chains
    """
    from external_anchoring import AnchorChain

    return jsonify({"chains": [c.value for c in AnchorChain]})


# =============================================================================
# Events
# =============================================================================


@anchoring_bp.route("/anchoring/events", methods=["GET"])
def get_events():
    """
    Get anchoring event log.

    Query params:
        limit: Maximum events to return (default: 100)
        event_type: Filter by event type (optional)

    Returns:
        List of events
    """
    if not managers.anchoring_service:
        return jsonify({"error": "Anchoring service not initialized"}), 503

    limit = request.args.get("limit", 100, type=int)
    event_type = request.args.get("event_type")

    events = managers.anchoring_service.events

    if event_type:
        events = [e for e in events if e["event_type"] == event_type]

    events = events[-limit:]

    return jsonify({"count": len(events), "events": list(reversed(events))})
