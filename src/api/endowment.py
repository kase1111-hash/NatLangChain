"""
NatLangChain - Endowment API Blueprint

REST API endpoints for the Permanence Endowment system.
Provides access to:
- Fee calculations
- Permanence guarantee creation
- Guarantee verification
- Pool status and sustainability reports
- Yield accrual triggers
"""

from flask import Blueprint, jsonify, request

from .state import managers
from .utils import DEFAULT_HISTORY_LIMIT, DEFAULT_PAGE_LIMIT

endowment_bp = Blueprint("endowment", __name__)


# =============================================================================
# Fee Calculation Endpoints
# =============================================================================


@endowment_bp.route("/endowment/calculate-fee", methods=["POST"])
def calculate_permanence_fee():
    """
    Calculate the permanence fee for an entry.

    Request body:
        {
            "entry_size_bytes": 2048  // Size of entry in bytes
        }

    Returns:
        Fee breakdown with endowment allocation and projections
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}
    entry_size = data.get("entry_size_bytes")

    if not entry_size or entry_size <= 0:
        return jsonify({"error": "entry_size_bytes must be a positive integer"}), 400

    try:
        result = managers.permanence_endowment.calculate_permanence_fee(int(entry_size))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@endowment_bp.route("/endowment/estimate", methods=["GET"])
def estimate_fee_quick():
    """
    Quick fee estimate for common entry sizes.

    Query params:
        size: Entry size in bytes (default: 2048)

    Returns:
        Simplified fee estimate
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    size = request.args.get("size", 2048, type=int)

    if size <= 0:
        return jsonify({"error": "Size must be positive"}), 400

    try:
        result = managers.permanence_endowment.calculate_permanence_fee(size)
        return jsonify(
            {
                "entry_size_bytes": size,
                "permanence_fee": result["total_fee"],
                "currency": "USD",
                "guarantee_years": result["sustainability"]["projected_years"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Guarantee Management Endpoints
# =============================================================================


@endowment_bp.route("/endowment/guarantee", methods=["POST"])
def create_permanence_guarantee():
    """
    Create a permanence guarantee for an entry.

    Request body:
        {
            "entry_hash": "abc123...",
            "entry_size_bytes": 2048,
            "fee_amount": 0.05,
            "payer": "alice"
        }

    Returns:
        Guarantee details or error
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}

    required_fields = ["entry_hash", "entry_size_bytes", "fee_amount", "payer"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        success, result = managers.permanence_endowment.deposit_for_permanence(
            entry_hash=data["entry_hash"],
            entry_size_bytes=int(data["entry_size_bytes"]),
            fee_amount=float(data["fee_amount"]),
            payer=data["payer"],
            metadata=data.get("metadata"),
        )

        if success:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@endowment_bp.route("/endowment/guarantee/<entry_hash>", methods=["GET"])
def get_guarantee(entry_hash):
    """
    Get permanence guarantee for an entry.

    Path params:
        entry_hash: Hash of the entry

    Returns:
        Guarantee details or 404
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    guarantee = managers.permanence_endowment.get_guarantee(entry_hash)

    if guarantee:
        return jsonify(guarantee)
    else:
        return jsonify({"error": "No guarantee found for entry"}), 404


@endowment_bp.route("/endowment/guarantee/<entry_hash>/verify", methods=["POST"])
def verify_guarantee(entry_hash):
    """
    Verify a permanence guarantee cryptographically.

    Path params:
        entry_hash: Hash of the entry

    Request body:
        {
            "guarantee_hash": "0xabc123..."
        }

    Returns:
        Verification result
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}
    guarantee_hash = data.get("guarantee_hash")

    if not guarantee_hash:
        return jsonify({"error": "guarantee_hash is required"}), 400

    result = managers.permanence_endowment.verify_guarantee(entry_hash, guarantee_hash)
    status_code = 200 if result.get("valid") else 400

    return jsonify(result), status_code


@endowment_bp.route("/endowment/guarantee/<entry_hash>/topup", methods=["POST"])
def topup_guarantee(entry_hash):
    """
    Top up a partial permanence guarantee.

    Path params:
        entry_hash: Hash of the entry

    Request body:
        {
            "additional_fee": 0.02,
            "payer": "alice"
        }

    Returns:
        Updated guarantee details
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}

    additional_fee = data.get("additional_fee")
    payer = data.get("payer")

    if not additional_fee or additional_fee <= 0:
        return jsonify({"error": "additional_fee must be positive"}), 400
    if not payer:
        return jsonify({"error": "payer is required"}), 400

    try:
        success, result = managers.permanence_endowment.top_up_guarantee(
            entry_hash=entry_hash,
            additional_fee=float(additional_fee),
            payer=payer,
        )

        if success:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Pool Status Endpoints
# =============================================================================


@endowment_bp.route("/endowment/status", methods=["GET"])
def get_pool_status():
    """
    Get current endowment pool status.

    Returns:
        Pool status including principal, yield, sustainability
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    return jsonify(managers.permanence_endowment.get_pool_status())


@endowment_bp.route("/endowment/statistics", methods=["GET"])
def get_statistics():
    """
    Get comprehensive endowment statistics.

    Returns:
        Detailed statistics about pool, guarantees, yields, payouts
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    return jsonify(managers.permanence_endowment.get_statistics())


@endowment_bp.route("/endowment/sustainability", methods=["GET"])
def get_sustainability_report():
    """
    Get sustainability report with projections.

    Returns:
        10-year projection and sustainability analysis
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    return jsonify(managers.permanence_endowment.get_sustainability_report())


@endowment_bp.route("/endowment/health", methods=["GET"])
def get_health():
    """
    Quick health check for the endowment.

    Returns:
        Simple health status
    """
    if not managers.permanence_endowment:
        return jsonify({"status": "unavailable", "message": "Endowment not initialized"}), 503

    status = managers.permanence_endowment.get_pool_status()

    return jsonify(
        {
            "status": status["health_status"],
            "principal": status["principal"],
            "sustainability_ratio": status["sustainability_ratio"],
            "entries_guaranteed": status["entries_guaranteed"],
        }
    )


# =============================================================================
# Yield Management Endpoints
# =============================================================================


@endowment_bp.route("/endowment/yield/accrue", methods=["POST"])
def accrue_yield():
    """
    Trigger yield accrual on the endowment.

    Request body (optional):
        {
            "days_elapsed": 7  // Override days (auto-calculated if omitted)
        }

    Returns:
        Yield accrual result
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}
    days_elapsed = data.get("days_elapsed")

    try:
        result = managers.permanence_endowment.accrue_yield(days_elapsed)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@endowment_bp.route("/endowment/yield/history", methods=["GET"])
def get_yield_history():
    """
    Get yield accrual history.

    Query params:
        limit: Maximum records to return (default: 50)

    Returns:
        List of yield accruals
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_HISTORY_LIMIT, type=int)

    accruals = managers.permanence_endowment.yield_accruals[-limit:]

    return jsonify(
        {
            "count": len(accruals),
            "total_yield_generated": managers.permanence_endowment.total_yield_generated,
            "accruals": [
                {
                    "accrual_id": a.accrual_id,
                    "period_start": a.period_start,
                    "period_end": a.period_end,
                    "yield_amount": a.yield_amount,
                    "yield_rate": a.yield_rate,
                    "strategy": a.strategy,
                }
                for a in reversed(accruals)
            ],
        }
    )


# =============================================================================
# Storage Payout Endpoints
# =============================================================================


@endowment_bp.route("/endowment/payout", methods=["POST"])
def process_storage_payout():
    """
    Process a storage payout to a provider.

    Request body:
        {
            "storage_provider": "provider_001",
            "entries_stored": 100,
            "bytes_stored": 204800
        }

    Returns:
        Payout result
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    data = request.get_json() or {}

    required_fields = ["storage_provider", "entries_stored", "bytes_stored"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    try:
        success, result = managers.permanence_endowment.process_storage_payout(
            storage_provider=data["storage_provider"],
            entries_stored=int(data["entries_stored"]),
            bytes_stored=int(data["bytes_stored"]),
        )

        if success:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@endowment_bp.route("/endowment/payouts", methods=["GET"])
def get_payout_history():
    """
    Get storage payout history.

    Query params:
        limit: Maximum records to return (default: 50)

    Returns:
        List of storage payouts
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_HISTORY_LIMIT, type=int)

    payouts = managers.permanence_endowment.storage_payouts[-limit:]

    return jsonify(
        {
            "count": len(payouts),
            "total_payouts": managers.permanence_endowment.total_payouts,
            "payouts": [
                {
                    "payout_id": p.payout_id,
                    "period": p.period,
                    "storage_provider": p.storage_provider,
                    "entries_covered": p.entries_covered,
                    "bytes_stored": p.bytes_stored,
                    "amount": p.amount,
                    "funded_from": p.funded_from,
                }
                for p in reversed(payouts)
            ],
        }
    )


# =============================================================================
# Event Log Endpoint
# =============================================================================


@endowment_bp.route("/endowment/events", methods=["GET"])
def get_events():
    """
    Get endowment event log.

    Query params:
        limit: Maximum events to return (default: 100)
        event_type: Filter by event type (optional)

    Returns:
        List of events
    """
    if not managers.permanence_endowment:
        return jsonify({"error": "Permanence endowment not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    event_type = request.args.get("event_type")

    events = managers.permanence_endowment.events

    if event_type:
        events = [e for e in events if e["event_type"] == event_type]

    events = events[-limit:]

    return jsonify(
        {
            "count": len(events),
            "events": list(reversed(events)),
        }
    )
