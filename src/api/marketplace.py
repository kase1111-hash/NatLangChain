"""
NatLangChain Marketplace API Blueprint.

Provides REST API endpoints for the module marketplace:
- Module listing and registration
- Pricing and terms display
- License purchase and verification
- Story Protocol integration

All endpoints are prefixed with /marketplace/
"""

from flask import Blueprint, jsonify, request

from api.utils import managers, require_api_key, validate_json_schema

marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')


# ============================================================
# Module Listing Endpoints
# ============================================================

@marketplace_bp.route('/modules', methods=['GET'])
def list_modules():
    """
    List all available modules in the marketplace.

    Returns:
        JSON list of modules with basic info
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized",
            "available": False
        }), 503

    modules = managers.marketplace_manager.list_modules()
    return jsonify({
        "modules": modules,
        "count": len(modules),
        "network": managers.marketplace_manager.network.value
    })


@marketplace_bp.route('/modules/<module_id>', methods=['GET'])
def get_module(module_id: str):
    """
    Get detailed information about a specific module.

    Args:
        module_id: The module identifier (IP Asset ID or hash)

    Returns:
        Module details including pricing and terms
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    config = managers.marketplace_manager.get_module(module_id)
    if config is None:
        return jsonify({
            "error": f"Module not found: {module_id}"
        }), 404

    return jsonify({
        "module_id": module_id,
        "config": config.to_dict()
    })


@marketplace_bp.route('/modules/<module_id>/pricing', methods=['GET'])
def get_module_pricing(module_id: str):
    """
    Get detailed pricing information for a module.

    Args:
        module_id: The module identifier

    Returns:
        Pricing details including tier prices and PIL terms
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    pricing = managers.marketplace_manager.get_module_pricing(module_id)
    if pricing is None:
        return jsonify({
            "error": f"Module not found: {module_id}"
        }), 404

    return jsonify(pricing)


# ============================================================
# Module Registration Endpoints
# ============================================================

@marketplace_bp.route('/register', methods=['POST'])
@require_api_key
def register_module():
    """
    Register a new module from its GitHub repository.

    Request body:
        {
            "github_url": "https://github.com/owner/repo",
            "branch": "main"  // optional, default: main
        }

    Returns:
        Registration result with module details
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate input
    valid, error = validate_json_schema(
        data,
        required_fields={"github_url": str},
        optional_fields={"branch": str},
        max_lengths={"github_url": 500, "branch": 100}
    )
    if not valid:
        return jsonify({"error": error}), 400

    github_url = data["github_url"]
    branch = data.get("branch", "main")

    result = managers.marketplace_manager.register_module(github_url, branch)

    if result.get("success"):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


# ============================================================
# Purchase Endpoints
# ============================================================

@marketplace_bp.route('/purchase', methods=['POST'])
@require_api_key
def purchase_license():
    """
    Purchase a license for a module.

    This will:
    1. Validate the module and pricing
    2. Process payment with revenue splits
    3. Mint a license NFT via Story Protocol
    4. Record the purchase

    Request body:
        {
            "module_id": "0x...",  // IP Asset ID or module hash
            "buyer_wallet": "0x...",  // Buyer's wallet address
            "tier": "standard"  // optional: standard, premium, enterprise
        }

    Returns:
        Purchase result with license NFT details
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate input
    valid, error = validate_json_schema(
        data,
        required_fields={"module_id": str, "buyer_wallet": str},
        optional_fields={"tier": str},
        max_lengths={"module_id": 100, "buyer_wallet": 100, "tier": 20}
    )
    if not valid:
        return jsonify({"error": error}), 400

    module_id = data["module_id"]
    buyer_wallet = data["buyer_wallet"]
    tier_str = data.get("tier", "standard").lower()

    # Validate wallet address format
    if not buyer_wallet.startswith("0x") or len(buyer_wallet) != 42:
        return jsonify({
            "error": "Invalid wallet address format"
        }), 400

    # Parse tier
    from marketplace import LicenseTier
    try:
        tier = LicenseTier(tier_str)
    except ValueError:
        return jsonify({
            "error": f"Invalid tier: {tier_str}. Must be one of: standard, premium, enterprise"
        }), 400

    result = managers.marketplace_manager.purchase_license(
        module_id=module_id,
        buyer_wallet=buyer_wallet,
        tier=tier
    )

    if result.get("success"):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@marketplace_bp.route('/purchases/<purchase_id>', methods=['GET'])
def get_purchase(purchase_id: str):
    """
    Get details of a specific purchase.

    Args:
        purchase_id: The purchase identifier

    Returns:
        Purchase details including license info
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    purchase = managers.marketplace_manager.get_purchase(purchase_id)
    if purchase is None:
        return jsonify({
            "error": f"Purchase not found: {purchase_id}"
        }), 404

    return jsonify(purchase.to_dict())


@marketplace_bp.route('/purchases/wallet/<wallet>', methods=['GET'])
def get_wallet_purchases(wallet: str):
    """
    Get all purchases for a wallet.

    Args:
        wallet: The wallet address

    Returns:
        List of purchases for the wallet
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    purchases = managers.marketplace_manager.get_purchases_by_wallet(wallet)
    return jsonify({
        "wallet": wallet,
        "purchases": [p.to_dict() for p in purchases],
        "count": len(purchases)
    })


# ============================================================
# License Verification Endpoints
# ============================================================

@marketplace_bp.route('/verify', methods=['POST'])
def verify_license():
    """
    Verify that a wallet has a valid license for a module.

    Request body:
        {
            "module_id": "0x...",
            "wallet": "0x..."
        }

    Returns:
        Verification result with license details
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate input
    valid, error = validate_json_schema(
        data,
        required_fields={"module_id": str, "wallet": str},
        max_lengths={"module_id": 100, "wallet": 100}
    )
    if not valid:
        return jsonify({"error": error}), 400

    result = managers.marketplace_manager.verify_license(
        module_id=data["module_id"],
        wallet=data["wallet"]
    )

    return jsonify(result)


# ============================================================
# Story Protocol Endpoints
# ============================================================

@marketplace_bp.route('/story-protocol/status', methods=['GET'])
def story_protocol_status():
    """
    Get Story Protocol SDK status and configuration.

    Returns:
        SDK availability and network configuration
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    client = managers.marketplace_manager.story_client
    return jsonify({
        "available": client.is_available(),
        "network": client.network.value,
        "rpc_url": client.rpc_url,
        "chain_id": client.chain_id
    })


@marketplace_bp.route('/story-protocol/ip-asset/<ip_asset_id>', methods=['GET'])
def get_ip_asset(ip_asset_id: str):
    """
    Get IP asset details from Story Protocol.

    Args:
        ip_asset_id: The IP Asset ID

    Returns:
        IP asset details from Story Protocol
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    result = managers.marketplace_manager.story_client.get_ip_asset(ip_asset_id)
    if result is None or "error" in result:
        return jsonify({
            "error": f"IP Asset not found: {ip_asset_id}",
            "details": result
        }), 404

    return jsonify(result)


# ============================================================
# RRA Module Specific Endpoints
# ============================================================

@marketplace_bp.route('/rra-module', methods=['GET'])
def get_rra_module():
    """
    Get the pre-registered RRA-Module configuration.

    Returns:
        RRA-Module details including pricing and Story Protocol info
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    from marketplace import RRA_MODULE_CONFIG

    # The RRA module is registered with its IP Asset ID
    rra_module_id = RRA_MODULE_CONFIG.ip_asset_id
    config = managers.marketplace_manager.get_module(rra_module_id)

    if config is None:
        # Re-register if not found
        managers.marketplace_manager.register_module_direct(
            module_id=rra_module_id,
            config=RRA_MODULE_CONFIG
        )
        config = RRA_MODULE_CONFIG

    return jsonify({
        "module_id": rra_module_id,
        "module_name": config.module_name,
        "description": config.description,
        "github_url": config.github_url,
        "ip_asset_id": config.ip_asset_id,
        "owner_wallet": config.owner_wallet,
        "pricing": {
            "base_price_eth": config.base_price_eth,
            "floor_price_eth": config.floor_price_eth,
            "ceiling_price_eth": config.ceiling_price_eth,
            "tiers": {
                tier.value: {
                    "price_eth": config.get_tier_price(tier),
                    "features": config.tiers[tier].features
                }
                for tier in config.tiers
            }
        },
        "pil_terms": config.pil_terms.to_dict(),
        "revenue_split": config.revenue_split.to_dict(),
        "license_info": {
            "auto_convert_license": config.auto_convert_license,
            "auto_convert_date": config.auto_convert_date
        }
    })


@marketplace_bp.route('/rra-module/purchase', methods=['POST'])
@require_api_key
def purchase_rra_license():
    """
    Purchase a license for the RRA-Module.

    Request body:
        {
            "buyer_wallet": "0x...",
            "tier": "standard"  // optional
        }

    Returns:
        Purchase result with license NFT details
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "error": "Marketplace not initialized"
        }), 503

    from marketplace import RRA_MODULE_CONFIG

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Validate input
    valid, error = validate_json_schema(
        data,
        required_fields={"buyer_wallet": str},
        optional_fields={"tier": str},
        max_lengths={"buyer_wallet": 100, "tier": 20}
    )
    if not valid:
        return jsonify({"error": error}), 400

    # Use the RRA module's IP Asset ID
    rra_module_id = RRA_MODULE_CONFIG.ip_asset_id

    # Ensure RRA module is registered
    if managers.marketplace_manager.get_module(rra_module_id) is None:
        managers.marketplace_manager.register_module_direct(
            module_id=rra_module_id,
            config=RRA_MODULE_CONFIG
        )

    buyer_wallet = data["buyer_wallet"]
    tier_str = data.get("tier", "standard").lower()

    # Validate wallet address format
    if not buyer_wallet.startswith("0x") or len(buyer_wallet) != 42:
        return jsonify({
            "error": "Invalid wallet address format"
        }), 400

    # Parse tier
    from marketplace import LicenseTier
    try:
        tier = LicenseTier(tier_str)
    except ValueError:
        return jsonify({
            "error": f"Invalid tier: {tier_str}. Must be one of: standard, premium, enterprise"
        }), 400

    result = managers.marketplace_manager.purchase_license(
        module_id=rra_module_id,
        buyer_wallet=buyer_wallet,
        tier=tier
    )

    if result.get("success"):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


# ============================================================
# Marketplace Status Endpoint
# ============================================================

@marketplace_bp.route('/status', methods=['GET'])
def marketplace_status():
    """
    Get overall marketplace status.

    Returns:
        Marketplace availability and statistics
    """
    if managers.marketplace_manager is None:
        return jsonify({
            "available": False,
            "error": "Marketplace not initialized"
        }), 503

    modules = managers.marketplace_manager.list_modules()
    story_client = managers.marketplace_manager.story_client

    return jsonify({
        "available": True,
        "network": managers.marketplace_manager.network.value,
        "story_protocol": {
            "available": story_client.is_available(),
            "rpc_url": story_client.rpc_url,
            "chain_id": story_client.chain_id
        },
        "modules": {
            "count": len(modules),
            "registered": [m["module_name"] for m in modules]
        }
    })
