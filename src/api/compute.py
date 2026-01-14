"""
NatLangChain - Compute-to-Data API Blueprint

REST API endpoints for privacy-preserving computation on data.
Inspired by Ocean Protocol's compute-to-data paradigm.

Provides access to:
- Register data assets for compute
- Manage access tokens
- Submit and monitor compute jobs
- Retrieve privacy-filtered results
- List available algorithms
"""

from flask import Blueprint, jsonify, request

from .state import managers

compute_bp = Blueprint("compute", __name__)


# =============================================================================
# Data Asset Management Endpoints
# =============================================================================


@compute_bp.route("/compute/assets", methods=["POST"])
def register_asset():
    """
    Register a new data asset for compute.

    Request body:
        {
            "asset_type": "contract",           // contract, entry, entry_set, dispute, settlement, custom
            "owner": "did:nlc:...",             // Owner DID
            "name": "My Dataset",
            "data": [...],                      // The actual data records
            "description": "...",               // Optional
            "entry_refs": [...],                // Optional entry references
            "allowed_algorithms": [...],        // Optional algorithm IDs
            "allowed_compute_providers": [...], // Optional DIDs allowed to compute
            "privacy_level": "aggregated",      // raw, anonymized, aggregated, differential
            "min_aggregation_size": 5,          // Optional, default 5
            "metadata": {...}                   // Optional
        }

    Returns:
        Asset info with asset_id
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    required = ["asset_type", "owner", "name", "data"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    # Parse asset type
    from compute_to_data import DataAssetType, PrivacyLevel

    try:
        asset_type = DataAssetType(data["asset_type"])
    except ValueError:
        return jsonify({"error": f"Invalid asset_type: {data['asset_type']}"}), 400

    # Parse privacy level
    privacy_level = PrivacyLevel.AGGREGATED
    if data.get("privacy_level"):
        try:
            privacy_level = PrivacyLevel(data["privacy_level"])
        except ValueError:
            return jsonify({"error": f"Invalid privacy_level: {data['privacy_level']}"}), 400

    success, result = managers.compute_service.register_asset(
        asset_type=asset_type,
        owner=data["owner"],
        name=data["name"],
        data=data["data"],
        description=data.get("description"),
        entry_refs=data.get("entry_refs"),
        allowed_algorithms=data.get("allowed_algorithms"),
        allowed_compute_providers=data.get("allowed_compute_providers"),
        privacy_level=privacy_level,
        min_aggregation_size=data.get("min_aggregation_size", 5),
        metadata=data.get("metadata"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/assets/<asset_id>", methods=["GET"])
def get_asset(asset_id):
    """
    Get a data asset by ID.

    Path params:
        asset_id: The asset ID

    Returns:
        Asset info (excludes actual data)
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    asset = managers.compute_service.get_asset(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    return jsonify(asset.to_dict())


@compute_bp.route("/compute/assets/<asset_id>", methods=["PATCH"])
def update_asset(asset_id):
    """
    Update a data asset's configuration.

    Path params:
        asset_id: The asset ID

    Request body:
        {
            "owner": "did:nlc:...",               // Required for auth
            "allowed_algorithms": [...],         // Optional
            "allowed_compute_providers": [...],  // Optional
            "privacy_level": "...",              // Optional
            "min_aggregation_size": 10,          // Optional
            "metadata": {...}                    // Optional
        }

    Returns:
        Updated asset info
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("owner"):
        return jsonify({"error": "owner is required for authorization"}), 400

    success, result = managers.compute_service.update_asset(asset_id, data["owner"], data)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/assets/<asset_id>/revoke", methods=["POST"])
def revoke_asset(asset_id):
    """
    Revoke a data asset (disable for compute).

    Path params:
        asset_id: The asset ID

    Request body:
        {
            "owner": "did:nlc:..."  // Required for auth
        }

    Returns:
        Revocation result
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("owner"):
        return jsonify({"error": "owner is required for authorization"}), 400

    success, result = managers.compute_service.revoke_asset(asset_id, data["owner"])

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/assets", methods=["GET"])
def list_assets():
    """
    List data assets.

    Query params:
        owner: Filter by owner DID (optional)
        asset_type: Filter by asset type (optional)
        active_only: Only active assets (default: true)

    Returns:
        List of assets
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    from compute_to_data import DataAssetType

    owner = request.args.get("owner")
    asset_type_str = request.args.get("asset_type")
    active_only = request.args.get("active_only", "true").lower() == "true"

    asset_type = None
    if asset_type_str:
        try:
            asset_type = DataAssetType(asset_type_str)
        except ValueError:
            return jsonify({"error": f"Invalid asset_type: {asset_type_str}"}), 400

    assets = managers.compute_service.list_assets(
        owner=owner,
        asset_type=asset_type,
        active_only=active_only,
    )

    return jsonify({
        "count": len(assets),
        "assets": [a.to_dict() for a in assets],
    })


# =============================================================================
# Access Control Endpoints
# =============================================================================


@compute_bp.route("/compute/access/grant", methods=["POST"])
def grant_access():
    """
    Grant access to a data asset.

    Request body:
        {
            "asset_id": "asset_...",
            "owner": "did:nlc:...",           // Asset owner (for auth)
            "grantee": "did:nlc:...",         // DID to grant access to
            "access_level": "compute_only",   // none, metadata_only, aggregate_only, compute_only, full_compute, full_access
            "allowed_algorithms": [...],      // Optional specific algorithms
            "max_uses": 100,                  // Optional, default 100
            "expires_in_hours": 24            // Optional, default 24
        }

    Returns:
        Access token info
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    required = ["asset_id", "owner", "grantee", "access_level"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from compute_to_data import AccessLevel

    try:
        access_level = AccessLevel(data["access_level"])
    except ValueError:
        return jsonify({"error": f"Invalid access_level: {data['access_level']}"}), 400

    success, result = managers.compute_service.grant_access(
        asset_id=data["asset_id"],
        owner=data["owner"],
        grantee=data["grantee"],
        access_level=access_level,
        allowed_algorithms=data.get("allowed_algorithms"),
        max_uses=data.get("max_uses", 100),
        expires_in_hours=data.get("expires_in_hours", 24),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/access/<token_id>/revoke", methods=["POST"])
def revoke_access(token_id):
    """
    Revoke an access token.

    Path params:
        token_id: The token ID

    Request body:
        {
            "owner": "did:nlc:..."  // Asset owner (for auth)
        }

    Returns:
        Revocation result
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    if not data.get("owner"):
        return jsonify({"error": "owner is required for authorization"}), 400

    success, result = managers.compute_service.revoke_access(token_id, data["owner"])

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/access", methods=["GET"])
def list_access_tokens():
    """
    List access tokens.

    Query params:
        asset_id: Filter by asset ID (optional)
        grantee: Filter by grantee DID (optional)

    Returns:
        List of access tokens
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    asset_id = request.args.get("asset_id")
    grantee = request.args.get("grantee")

    tokens = managers.compute_service.get_access_tokens(asset_id=asset_id, grantee=grantee)

    return jsonify({
        "count": len(tokens),
        "tokens": [t.to_dict() for t in tokens],
    })


# =============================================================================
# Algorithm Management Endpoints
# =============================================================================


@compute_bp.route("/compute/algorithms", methods=["POST"])
def register_algorithm():
    """
    Register a custom algorithm.

    Request body:
        {
            "algorithm_type": "statistical",   // statistical, classification, matching, verification, extraction, analysis, custom
            "name": "My Algorithm",
            "code_hash": "sha256:...",         // Hash of the algorithm code
            "author": "did:nlc:...",           // Optional
            "description": "...",              // Optional
            "input_schema": {...},             // Optional
            "output_schema": {...},            // Optional
            "privacy_preserving": true         // Optional, default true
        }

    Returns:
        Algorithm info
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    required = ["algorithm_type", "name", "code_hash"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from compute_to_data import ComputeAlgorithmType

    try:
        algorithm_type = ComputeAlgorithmType(data["algorithm_type"])
    except ValueError:
        return jsonify({"error": f"Invalid algorithm_type: {data['algorithm_type']}"}), 400

    success, result = managers.compute_service.register_algorithm(
        algorithm_type=algorithm_type,
        name=data["name"],
        code_hash=data["code_hash"],
        author=data.get("author"),
        description=data.get("description"),
        input_schema=data.get("input_schema"),
        output_schema=data.get("output_schema"),
        privacy_preserving=data.get("privacy_preserving", True),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/algorithms/<algorithm_id>", methods=["GET"])
def get_algorithm(algorithm_id):
    """
    Get an algorithm by ID.

    Path params:
        algorithm_id: The algorithm ID

    Returns:
        Algorithm info
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    algorithm = managers.compute_service.get_algorithm(algorithm_id)
    if not algorithm:
        return jsonify({"error": "Algorithm not found"}), 404

    return jsonify(algorithm.to_dict())


@compute_bp.route("/compute/algorithms", methods=["GET"])
def list_algorithms():
    """
    List available algorithms.

    Query params:
        algorithm_type: Filter by type (optional)
        privacy_preserving_only: Only privacy-preserving (default: false)
        audited_only: Only audited algorithms (default: false)

    Returns:
        List of algorithms
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    from compute_to_data import ComputeAlgorithmType

    algorithm_type_str = request.args.get("algorithm_type")
    privacy_preserving_only = request.args.get("privacy_preserving_only", "false").lower() == "true"
    audited_only = request.args.get("audited_only", "false").lower() == "true"

    algorithm_type = None
    if algorithm_type_str:
        try:
            algorithm_type = ComputeAlgorithmType(algorithm_type_str)
        except ValueError:
            return jsonify({"error": f"Invalid algorithm_type: {algorithm_type_str}"}), 400

    algorithms = managers.compute_service.list_algorithms(
        algorithm_type=algorithm_type,
        privacy_preserving_only=privacy_preserving_only,
        audited_only=audited_only,
    )

    return jsonify({
        "count": len(algorithms),
        "algorithms": [a.to_dict() for a in algorithms],
    })


# =============================================================================
# Compute Job Endpoints
# =============================================================================


@compute_bp.route("/compute/jobs", methods=["POST"])
def submit_job():
    """
    Submit a compute job.

    Request body:
        {
            "asset_id": "asset_...",
            "algorithm_id": "builtin_count",
            "access_token_id": "token_...",
            "requester": "did:nlc:...",
            "parameters": {...},               // Optional algorithm params
            "privacy_level": "aggregated"      // Optional override
        }

    Returns:
        Job info with status
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    data = request.get_json() or {}

    required = ["asset_id", "algorithm_id", "access_token_id", "requester"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from compute_to_data import PrivacyLevel

    privacy_level = None
    if data.get("privacy_level"):
        try:
            privacy_level = PrivacyLevel(data["privacy_level"])
        except ValueError:
            return jsonify({"error": f"Invalid privacy_level: {data['privacy_level']}"}), 400

    success, result = managers.compute_service.submit_job(
        asset_id=data["asset_id"],
        algorithm_id=data["algorithm_id"],
        access_token_id=data["access_token_id"],
        requester=data["requester"],
        parameters=data.get("parameters"),
        privacy_level=privacy_level,
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """
    Get a compute job by ID.

    Path params:
        job_id: The job ID

    Returns:
        Job info with status
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    job = managers.compute_service.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict())


@compute_bp.route("/compute/jobs/<job_id>/result", methods=["GET"])
def get_job_result(job_id):
    """
    Get the result of a completed compute job.

    Path params:
        job_id: The job ID

    Query params:
        requester: Requester DID (for authorization)

    Returns:
        Privacy-filtered result
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    requester = request.args.get("requester")
    if not requester:
        return jsonify({"error": "requester query parameter required"}), 400

    success, result = managers.compute_service.get_job_result(job_id, requester)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@compute_bp.route("/compute/jobs", methods=["GET"])
def list_jobs():
    """
    List compute jobs.

    Query params:
        requester: Filter by requester DID (optional)
        asset_id: Filter by asset ID (optional)
        status: Filter by status (optional)

    Returns:
        List of jobs
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    from compute_to_data import JobStatus

    requester = request.args.get("requester")
    asset_id = request.args.get("asset_id")
    status_str = request.args.get("status")

    status = None
    if status_str:
        try:
            status = JobStatus(status_str)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_str}"}), 400

    jobs = managers.compute_service.list_jobs(
        requester=requester,
        asset_id=asset_id,
        status=status,
    )

    return jsonify({
        "count": len(jobs),
        "jobs": [j.to_dict() for j in jobs],
    })


# =============================================================================
# Statistics and Events
# =============================================================================


@compute_bp.route("/compute/statistics", methods=["GET"])
def get_statistics():
    """
    Get compute service statistics.

    Returns:
        Comprehensive statistics
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    return jsonify(managers.compute_service.get_statistics())


@compute_bp.route("/compute/events", methods=["GET"])
def get_events():
    """
    Get compute event log.

    Query params:
        limit: Maximum events to return (default: 100)
        event_type: Filter by event type (optional)

    Returns:
        List of events
    """
    if not managers.compute_service:
        return jsonify({"error": "Compute service not initialized"}), 503

    limit = request.args.get("limit", 100, type=int)
    event_type_filter = request.args.get("event_type")

    events = managers.compute_service.events

    if event_type_filter:
        events = [e for e in events if e.event_type.value == event_type_filter]

    events = events[-limit:]

    return jsonify({
        "count": len(events),
        "events": [e.to_dict() for e in reversed(events)],
    })


# =============================================================================
# Supported Types
# =============================================================================


@compute_bp.route("/compute/types/assets", methods=["GET"])
def get_asset_types():
    """
    Get supported data asset types.

    Returns:
        List of supported asset types
    """
    from compute_to_data import DataAssetType

    return jsonify({"types": [t.value for t in DataAssetType]})


@compute_bp.route("/compute/types/algorithms", methods=["GET"])
def get_algorithm_types():
    """
    Get supported algorithm types.

    Returns:
        List of supported algorithm types
    """
    from compute_to_data import ComputeAlgorithmType

    return jsonify({"types": [t.value for t in ComputeAlgorithmType]})


@compute_bp.route("/compute/types/access_levels", methods=["GET"])
def get_access_levels():
    """
    Get supported access levels.

    Returns:
        List of supported access levels
    """
    from compute_to_data import AccessLevel

    return jsonify({"levels": [level.value for level in AccessLevel]})


@compute_bp.route("/compute/types/privacy_levels", methods=["GET"])
def get_privacy_levels():
    """
    Get supported privacy levels.

    Returns:
        List of supported privacy levels
    """
    from compute_to_data import PrivacyLevel

    return jsonify({"levels": [level.value for level in PrivacyLevel]})


@compute_bp.route("/compute/types/job_statuses", methods=["GET"])
def get_job_statuses():
    """
    Get supported job statuses.

    Returns:
        List of supported job statuses
    """
    from compute_to_data import JobStatus

    return jsonify({"statuses": [s.value for s in JobStatus]})
