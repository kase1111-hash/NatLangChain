"""
Mobile deployment blueprint.

This blueprint handles mobile device management, edge AI, wallet connections,
and offline synchronization.
"""

from flask import Blueprint, jsonify, request

from .utils import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, managers, require_api_key

# Create the blueprint
mobile_bp = Blueprint('mobile', __name__, url_prefix='/mobile')


# ========== Device Management ==========

@mobile_bp.route('/device/register', methods=['POST'])
@require_api_key
def register_device():
    """
    Register a new mobile device.

    Request body:
        device_type: Type of device (ios, android, web, desktop)
        device_name: User-friendly device name
        capabilities: Dict of device capabilities
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    # Import DeviceType locally to avoid circular imports
    try:
        from mobile_deployment import DeviceType
    except ImportError:
        return jsonify({"error": "Mobile deployment module not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_type_str = data.get("device_type", "web")
    device_name = data.get("device_name", "Unknown Device")
    capabilities = data.get("capabilities", {})

    try:
        device_type = DeviceType[device_type_str.upper()]
    except KeyError:
        return jsonify({
            "error": f"Invalid device_type. Valid: {[t.name.lower() for t in DeviceType]}"
        }), 400

    device_id = managers.mobile_deployment.register_device(
        device_type=device_type,
        device_name=device_name,
        capabilities=capabilities
    )

    return jsonify({
        "device_id": device_id,
        "device_type": device_type_str,
        "device_name": device_name,
        "registered": True
    })


@mobile_bp.route('/device/<device_id>', methods=['GET'])
def get_device_info(device_id: str):
    """Get information about a registered device."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    device = managers.mobile_deployment.portable.devices.get(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    return jsonify({
        "device_id": device.device_id,
        "device_type": device.device_type.name.lower(),
        "device_name": device.device_name,
        "capabilities": device.capabilities,
        "registered_at": device.registered_at.isoformat(),
        "last_sync": device.last_sync.isoformat() if device.last_sync else None,
        "is_active": device.is_active,
        "platform_version": device.platform_version
    })


@mobile_bp.route('/device/<device_id>/features', methods=['GET'])
def get_device_features(device_id: str):
    """Get feature flags for a specific device."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    features = managers.mobile_deployment.get_device_features(device_id)
    if not features:
        return jsonify({"error": "Device not found"}), 404

    return jsonify({
        "device_id": device_id,
        "features": features
    })


# ========== Edge AI ==========

@mobile_bp.route('/edge/model/load', methods=['POST'])
@require_api_key
def load_edge_model():
    """
    Load an AI model for edge inference.

    Request body:
        model_id: Unique identifier for the model
        model_type: Type of model (contract_parser, intent_classifier, etc.)
        model_path: Path to model file
        device_id: Device to load model on
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    model_id = data.get("model_id")
    model_type = data.get("model_type", "generic")
    model_path = data.get("model_path")
    device_id = data.get("device_id")

    if not model_id:
        return jsonify({"error": "model_id required"}), 400

    success = managers.mobile_deployment.load_edge_model(
        model_id=model_id,
        model_type=model_type,
        model_path=model_path,
        device_id=device_id
    )

    return jsonify({
        "model_id": model_id,
        "loaded": success,
        "device_id": device_id
    })


@mobile_bp.route('/edge/inference', methods=['POST'])
@require_api_key
def run_edge_inference():
    """
    Run inference on a loaded edge model.

    Request body:
        model_id: ID of loaded model
        input_data: Input data for inference
        device_id: Device to run inference on
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    model_id = data.get("model_id")
    input_data = data.get("input_data")
    device_id = data.get("device_id")

    if not model_id or input_data is None:
        return jsonify({"error": "model_id and input_data required"}), 400

    result = managers.mobile_deployment.run_inference(
        model_id=model_id,
        input_data=input_data,
        device_id=device_id
    )

    return jsonify(result)


@mobile_bp.route('/edge/models', methods=['GET'])
def list_edge_models():
    """List all loaded edge models."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    models = []
    for model_id, config in managers.mobile_deployment.edge_ai.loaded_models.items():
        models.append({
            "model_id": model_id,
            "model_type": config.model_type,
            "is_quantized": config.is_quantized,
            "loaded_at": config.loaded_at.isoformat(),
            "inference_count": config.inference_count
        })

    return jsonify({
        "count": len(models),
        "models": models
    })


@mobile_bp.route('/edge/resources', methods=['GET'])
def get_edge_resources():
    """Get current edge AI resource usage."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    resources = managers.mobile_deployment.edge_ai.resource_limits
    stats = managers.mobile_deployment.edge_ai.get_statistics()

    return jsonify({
        "limits": {
            "max_memory_mb": resources.max_memory_mb,
            "max_cpu_percent": resources.max_cpu_percent,
            "max_battery_drain_percent": resources.max_battery_drain_percent,
            "prefer_wifi": resources.prefer_wifi
        },
        "current": stats
    })


# ========== Wallet Management ==========

@mobile_bp.route('/wallet/connect', methods=['POST'])
@require_api_key
def connect_mobile_wallet():
    """
    Connect a mobile wallet.

    Request body:
        wallet_type: Type of wallet (walletconnect, metamask, coinbase, native, hardware)
        device_id: Device ID
        wallet_address: Wallet address
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    try:
        from mobile_deployment import WalletType
    except ImportError:
        return jsonify({"error": "Mobile deployment module not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    wallet_type_str = data.get("wallet_type", "native")
    device_id = data.get("device_id")
    wallet_address = data.get("wallet_address")

    if not device_id or not wallet_address:
        return jsonify({"error": "device_id and wallet_address required"}), 400

    try:
        wallet_type = WalletType[wallet_type_str.upper()]
    except KeyError:
        return jsonify({
            "error": f"Invalid wallet_type. Valid: {[t.name.lower() for t in WalletType]}"
        }), 400

    connection_id = managers.mobile_deployment.connect_wallet(
        wallet_type=wallet_type,
        device_id=device_id,
        wallet_address=wallet_address
    )

    return jsonify({
        "connection_id": connection_id,
        "wallet_type": wallet_type_str,
        "device_id": device_id,
        "connected": True
    })


@mobile_bp.route('/wallet/<connection_id>', methods=['GET'])
def get_wallet_connection(connection_id: str):
    """Get wallet connection details."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    conn = managers.mobile_deployment.wallet_manager.connections.get(connection_id)
    if not conn:
        return jsonify({"error": "Connection not found"}), 404

    return jsonify({
        "connection_id": conn.connection_id,
        "wallet_type": conn.wallet_type.name.lower(),
        "wallet_address": conn.wallet_address,
        "state": conn.state.name.lower(),
        "connected_at": conn.connected_at.isoformat(),
        "signature_count": conn.signature_count
    })


@mobile_bp.route('/wallet/<connection_id>/disconnect', methods=['POST'])
@require_api_key
def disconnect_mobile_wallet(connection_id: str):
    """Disconnect a wallet."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    success = managers.mobile_deployment.disconnect_wallet(connection_id)

    return jsonify({
        "connection_id": connection_id,
        "disconnected": success
    })


@mobile_bp.route('/wallet/<connection_id>/sign', methods=['POST'])
@require_api_key
def sign_with_wallet(connection_id: str):
    """
    Sign a message with the connected wallet.

    Request body:
        message: Message to sign
        sign_type: Type of signature (personal, typed_data, transaction)
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    message = data.get("message")
    sign_type = data.get("sign_type", "personal")

    if not message:
        return jsonify({"error": "message required"}), 400

    result = managers.mobile_deployment.sign_message(
        connection_id=connection_id,
        message=message,
        sign_type=sign_type
    )

    return jsonify(result)


@mobile_bp.route('/wallet/list', methods=['GET'])
def list_wallet_connections():
    """List all wallet connections."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    connections = []
    for conn_id, conn in managers.mobile_deployment.wallet_manager.connections.items():
        connections.append({
            "connection_id": conn.connection_id,
            "wallet_type": conn.wallet_type.name.lower(),
            "wallet_address": conn.wallet_address,
            "state": conn.state.name.lower(),
            "device_id": conn.device_id
        })

    return jsonify({
        "count": len(connections),
        "connections": connections
    })


# ========== Offline Management ==========

@mobile_bp.route('/offline/state/save', methods=['POST'])
@require_api_key
def save_offline_state():
    """
    Save offline state for a device.

    Request body:
        device_id: Device ID
        state_type: Type of state (contracts, entries, settings, cache)
        state_data: State data to save
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    state_type = data.get("state_type")
    state_data = data.get("state_data")

    if not device_id or not state_type or state_data is None:
        return jsonify({"error": "device_id, state_type, and state_data required"}), 400

    state_id = managers.mobile_deployment.save_offline_state(
        device_id=device_id,
        state_type=state_type,
        state_data=state_data
    )

    return jsonify({
        "state_id": state_id,
        "device_id": device_id,
        "state_type": state_type,
        "saved": True
    })


@mobile_bp.route('/offline/state/<device_id>', methods=['GET'])
def get_offline_state(device_id: str):
    """Get offline state for a device."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    state_type = request.args.get("state_type")
    state = managers.mobile_deployment.get_offline_state(device_id, state_type)

    return jsonify({
        "device_id": device_id,
        "state_type": state_type,
        "state": state
    })


@mobile_bp.route('/offline/queue/add', methods=['POST'])
@require_api_key
def add_to_sync_queue():
    """
    Add an operation to the sync queue.

    Request body:
        device_id: Device ID
        operation_type: Type of operation (create, update, delete)
        resource_type: Type of resource (contract, entry, proposal, draft, settings)
        resource_data: Resource data
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    operation_type = data.get("operation_type")
    resource_type = data.get("resource_type")
    resource_data = data.get("resource_data")

    if not all([device_id, operation_type, resource_type, resource_data]):
        return jsonify({
            "error": "device_id, operation_type, resource_type, and resource_data required"
        }), 400

    op_id = managers.mobile_deployment.queue_offline_operation(
        device_id=device_id,
        operation_type=operation_type,
        resource_type=resource_type,
        resource_data=resource_data
    )

    return jsonify({
        "operation_id": op_id,
        "device_id": device_id,
        "queued": True
    })


@mobile_bp.route('/offline/sync', methods=['POST'])
@require_api_key
def sync_offline_data():
    """
    Sync offline data for a device.

    Request body:
        device_id: Device ID
        force: Force sync even if recently synced (optional)
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    force = data.get("force", False)

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    result = managers.mobile_deployment.sync_device(device_id, force=force)

    return jsonify(result)


@mobile_bp.route('/offline/queue/<device_id>', methods=['GET'])
def get_sync_queue(device_id: str):
    """Get sync queue for a device."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    queue = managers.mobile_deployment.get_sync_queue(device_id)

    return jsonify({
        "device_id": device_id,
        "queue_length": len(queue),
        "operations": queue
    })


@mobile_bp.route('/offline/conflicts/<device_id>', methods=['GET'])
def get_sync_conflicts(device_id: str):
    """Get sync conflicts for a device."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    conflicts = managers.mobile_deployment.get_conflicts(device_id)

    return jsonify({
        "device_id": device_id,
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    })


@mobile_bp.route('/offline/conflict/resolve', methods=['POST'])
@require_api_key
def resolve_sync_conflict():
    """
    Resolve a sync conflict.

    Request body:
        conflict_id: Conflict ID
        resolution: Resolution strategy (local, remote, merge)
        merged_data: Merged data if using merge strategy (optional)
    """
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    conflict_id = data.get("conflict_id")
    resolution = data.get("resolution")
    merged_data = data.get("merged_data")

    if not conflict_id or not resolution:
        return jsonify({"error": "conflict_id and resolution required"}), 400

    if resolution not in ["local", "remote", "merge"]:
        return jsonify({"error": "resolution must be local, remote, or merge"}), 400

    if resolution == "merge" and merged_data is None:
        return jsonify({"error": "merged_data required for merge resolution"}), 400

    success = managers.mobile_deployment.resolve_conflict(
        conflict_id=conflict_id,
        resolution=resolution,
        merged_data=merged_data
    )

    return jsonify({
        "conflict_id": conflict_id,
        "resolved": success,
        "resolution": resolution
    })


# ========== Statistics ==========

@mobile_bp.route('/stats', methods=['GET'])
def get_mobile_stats():
    """Get mobile deployment statistics."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    return jsonify(managers.mobile_deployment.get_statistics())


@mobile_bp.route('/audit', methods=['GET'])
def get_mobile_audit():
    """Get mobile deployment audit trail."""
    if not managers.mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    limit = min(limit, MAX_PAGE_LIMIT)

    audit = managers.mobile_deployment.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(audit),
        "entries": audit
    })
