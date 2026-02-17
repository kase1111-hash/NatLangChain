"""
Live contract management API blueprint.

This blueprint provides endpoints for contract operations:
- Contract parsing and term extraction
- Contract matching for pending entries
- Contract posting (offers and seeks)
- Contract listing and filtering
- Contract response and counter-offers
"""

from flask import Blueprint, jsonify, request

from . import state
from .state import (
    create_entry_with_encryption,
    save_chain,
)
from .utils import managers, rate_limit_llm, require_api_key

# Try to import ContractParser for type constants
try:
    from contract_parser import ContractParser

    CONTRACT_AVAILABLE = True
except ImportError:
    CONTRACT_AVAILABLE = False
    ContractParser = None

# Create the blueprint
contracts_bp = Blueprint("contracts", __name__, url_prefix="/contract")


def _check_contract_features():
    """Check if contract features are available."""
    if not managers.contract_parser:
        return jsonify(
            {
                "error": "Contract features not available",
                "reason": "ANTHROPIC_API_KEY not configured",
            }
        ), 503
    return None


@contracts_bp.route("/parse", methods=["POST"])
@rate_limit_llm
def parse_contract_endpoint():
    """
    Parse natural language contract content and extract structured terms.

    Request body:
    {
        "content": "Natural language contract text"
    }

    Returns:
        Parsed contract with extracted terms, type, and structure
    """
    if error := _check_contract_features():
        return error

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")

    if not content:
        return jsonify({"error": "Missing required field", "required": ["content"]}), 400

    try:
        parsed = managers.contract_parser.parse_contract(content)
        return jsonify({"status": "success", "parsed": parsed})
    except Exception:
        return jsonify({"error": "Failed to parse contract", "details": "Internal error occurred"}), 500


@contracts_bp.route("/match", methods=["POST"])
@rate_limit_llm
def match_contracts():
    """
    Find matching contracts for pending entries.

    Request body:
    {
        "pending_entries": [...],  (optional - uses blockchain pending if not provided)
        "miner_id": "miner identifier"
    }

    Returns:
        List of matched contract proposals
    """
    if not managers.contract_matcher:
        return jsonify(
            {
                "error": "Contract features not available",
                "reason": "ANTHROPIC_API_KEY not configured",
            }
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    miner_id = data.get("miner_id", "anonymous-miner")
    pending_entries = data.get("pending_entries")

    # Use blockchain pending entries if not provided
    if pending_entries is None:
        pending_entries = state.blockchain.pending_entries

    try:
        matches = managers.contract_matcher.find_matches(state.blockchain, pending_entries, miner_id)
        return jsonify(
            {
                "status": "success",
                "matches": [m.to_dict() if hasattr(m, "to_dict") else m for m in matches],
                "count": len(matches),
            }
        )
    except Exception:
        return jsonify({"error": "Failed to find matches", "details": "Internal error occurred"}), 500


@contracts_bp.route("/post", methods=["POST"])
@require_api_key
@rate_limit_llm
def post_contract():
    """
    Post a new live contract (offer or seek).

    Request body:
    {
        "content": "Natural language contract description",
        "author": "author identifier",
        "intent": "Contract intent",
        "contract_type": "offer" | "seek",
        "terms": {"key": "value"},  (optional, will be extracted if not provided)
        "auto_mine": true/false (optional)
    }

    Returns:
        Contract entry with validation results
    """
    if error := _check_contract_features():
        return error

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    # Get contract type with fallback
    default_type = ContractParser.TYPE_OFFER if ContractParser else "offer"
    contract_type = data.get("contract_type", default_type)

    if not all([content, author, intent]):
        return jsonify(
            {"error": "Missing required fields", "required": ["content", "author", "intent"]}
        ), 400

    try:
        # Parse contract
        contract_data = managers.contract_parser.parse_contract(content, use_llm=True)

        # Override type if provided
        if contract_type:
            contract_data["contract_type"] = contract_type

        # Override terms if provided
        if "terms" in data:
            contract_data["terms"] = data["terms"]

        # Validate clarity
        is_valid, reason = managers.contract_parser.validate_contract_clarity(content)
        if not is_valid:
            return jsonify({"error": "Contract validation failed", "reason": reason}), 400

        # Create entry with contract metadata (encrypted sensitive fields)
        entry = create_entry_with_encryption(
            content=content, author=author, intent=intent, metadata=contract_data
        )

        entry.validation_status = "valid"

        # Add to blockchain
        result = state.blockchain.add_entry(entry)

        # Auto-mine if requested
        auto_mine = data.get("auto_mine", False)
        mined_block = None
        if auto_mine:
            mined_block = state.blockchain.mine_pending_entries()
            save_chain()

        response = {"status": "success", "entry": result, "contract_metadata": contract_data}

        if mined_block:
            response["mined_block"] = {"index": mined_block.index, "hash": mined_block.hash}

        return jsonify(response), 201

    except Exception:
        return jsonify({"error": "Contract posting failed", "reason": "Internal error occurred"}), 500


@contracts_bp.route("/list", methods=["GET"])
@require_api_key
def list_contracts():
    """
    List all contracts, optionally filtered by status or type.

    Query params:
        status: Filter by status (open, matched, negotiating, closed, cancelled)
        type: Filter by type (offer, seek, proposal)
        author: Filter by author

    Returns:
        List of contract entries
    """
    status_filter = request.args.get("status")
    type_filter = request.args.get("type")
    author_filter = request.args.get("author")

    contracts = []

    for block in state.blockchain.chain:
        for entry in block.entries:
            # Skip if not a contract
            if not entry.metadata.get("is_contract"):
                continue

            # Apply filters
            if status_filter and entry.metadata.get("status") != status_filter:
                continue

            if type_filter and entry.metadata.get("contract_type") != type_filter:
                continue

            if author_filter and entry.author != author_filter:
                continue

            contracts.append(
                {"block_index": block.index, "block_hash": block.hash, "entry": entry.to_dict()}
            )

    return jsonify({"count": len(contracts), "contracts": contracts})


@contracts_bp.route("/respond", methods=["POST"])
@require_api_key
@rate_limit_llm
def respond_to_contract():
    """
    Respond to a contract proposal or create a counter-offer.

    Request body:
    {
        "to_block": block_index,
        "to_entry": entry_index,
        "response_content": "Natural language response",
        "author": "author identifier",
        "response_type": "accept" | "counter" | "reject",
        "counter_terms": {"key": "value"} (optional, for counter-offers)
    }

    Returns:
        Response entry with mediation if counter-offer
    """
    if not managers.contract_parser or not managers.contract_matcher:
        return jsonify({"error": "Contract features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    to_block = data.get("to_block")
    to_entry = data.get("to_entry")
    response_content = data.get("response_content")
    author = data.get("author")
    response_type = data.get("response_type", "counter")

    if not all([to_block is not None, to_entry is not None, response_content, author]):
        return jsonify(
            {
                "error": "Missing required fields",
                "required": ["to_block", "to_entry", "response_content", "author"],
            }
        ), 400

    # Get original entry
    if to_block < 0 or to_block >= len(state.blockchain.chain):
        return jsonify({"error": "Block not found"}), 404

    block = state.blockchain.chain[to_block]

    if to_entry < 0 or to_entry >= len(block.entries):
        return jsonify({"error": "Entry not found"}), 404

    original_entry = block.entries[to_entry]

    # Determine response type constant
    response_type_const = ContractParser.TYPE_RESPONSE if ContractParser else "response"

    # Create response entry
    response_metadata = {
        "is_contract": True,
        "contract_type": response_type_const,
        "response_type": response_type,
        "links": [block.hash],  # Link to original
        "terms": data.get("counter_terms", {}),
    }

    # If counter-offer, get mediation
    mediation_result = None
    if response_type == "counter" and managers.contract_matcher:
        mediation_result = managers.contract_matcher.mediate_negotiation(
            original_entry.content,
            original_entry.metadata.get("terms", {}),
            response_content,
            data.get("counter_terms", {}),
            original_entry.metadata.get("negotiation_round", 0) + 1,
        )

        response_metadata["mediation"] = mediation_result
        response_metadata["negotiation_round"] = (
            original_entry.metadata.get("negotiation_round", 0) + 1
        )

    response_entry = create_entry_with_encryption(
        content=f"[RESPONSE TO: {block.hash[:8]}] {response_content}",
        author=author,
        intent=f"Response to contract: {response_type}",
        metadata=response_metadata,
    )

    state.blockchain.add_entry(response_entry)

    return jsonify(
        {"status": "success", "response": response_entry.to_dict(), "mediation": mediation_result}
    ), 201
