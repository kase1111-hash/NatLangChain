"""
Core blockchain operations blueprint.

This blueprint handles the fundamental blockchain operations:
- Health checks
- Chain retrieval and narrative
- Entry creation and validation
- Block mining and retrieval
- Statistics
"""

import json

from flask import Blueprint, jsonify, request

from .state import (
    blockchain,
    create_entry_with_encryption,
    save_chain,
)
from .utils import (
    managers,
    require_api_key,
    validate_json_schema,
    validate_pagination_params,
)

# Create the blueprint
core_bp = Blueprint("core", __name__)


@core_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": "NatLangChain API",
            "llm_validation_available": managers.llm_validator is not None,
            "blocks": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
        }
    )


@core_bp.route("/chain", methods=["GET"])
def get_chain():
    """
    Get the entire blockchain.

    Returns:
        Full blockchain data
    """
    return jsonify(
        {
            "length": len(blockchain.chain),
            "chain": blockchain.to_dict(),
            "valid": blockchain.validate_chain(),
        }
    )


@core_bp.route("/chain/narrative", methods=["GET"])
def get_narrative():
    """
    Get the full narrative history as human-readable text.

    This is a key feature: the entire ledger as readable prose.

    Returns:
        Complete narrative of all entries
    """
    narrative = blockchain.get_full_narrative()
    return narrative, 200, {"Content-Type": "text/plain; charset=utf-8"}


@core_bp.route("/entry", methods=["POST"])
@require_api_key
def add_entry():
    """
    Add a new natural language entry to the blockchain.

    Request body:
    {
        "content": "Natural language description of the transaction/event",
        "author": "identifier of the creator",
        "intent": "brief summary of purpose",
        "metadata": {} (optional),
        "validate": true/false (optional, default true),
        "auto_mine": true/false (optional, default false)
    }

    Returns:
        Entry status and validation results
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # SECURITY: Schema validation for entry payload
    ENTRY_MAX_LENGTHS = {
        "content": 50000,  # 50KB max for content
        "author": 500,  # 500 chars for author
        "intent": 2000,  # 2KB for intent
    }

    is_valid, error_msg = validate_json_schema(
        data,
        required_fields={"content": str, "author": str, "intent": str},
        optional_fields={
            "metadata": dict,
            "validate": bool,
            "auto_mine": bool,
            "validation_mode": str,
            "multi_validator": bool,
        },
        max_lengths=ENTRY_MAX_LENGTHS,
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Extract validated fields
    content = data["content"]
    author = data["author"]
    intent = data["intent"]

    # Validate metadata size if provided
    MAX_METADATA_LEN = 10000  # 10KB for metadata
    metadata = data.get("metadata", {})
    if metadata:
        try:
            metadata_str = json.dumps(metadata)
            if len(metadata_str) > MAX_METADATA_LEN:
                return jsonify(
                    {
                        "error": "Metadata too large",
                        "max_length": MAX_METADATA_LEN,
                        "received_length": len(metadata_str),
                    }
                ), 400
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid metadata format"}), 400

    # Create entry with encrypted sensitive metadata
    entry = create_entry_with_encryption(
        content=content, author=author, intent=intent, metadata=data.get("metadata", {})
    )

    # Validate if requested
    validate = data.get("validate", True)
    validation_result = None
    validation_mode = data.get("validation_mode", "standard")

    if validate:
        if validation_mode == "dialectic" and managers.dialectic_validator:
            dialectic_result = managers.dialectic_validator.validate_entry(content, intent, author)
            validation_result = {
                "validation_mode": "dialectic",
                "dialectic_validation": dialectic_result,
                "overall_decision": dialectic_result.get("decision", "ERROR"),
            }
        elif managers.hybrid_validator:
            validation_result = managers.hybrid_validator.validate(
                content=content,
                intent=intent,
                author=author,
                use_llm=True,
                multi_validator=(validation_mode == "multi" or data.get("multi_validator", False)),
            )
            validation_result["validation_mode"] = validation_mode
        else:
            validation_result = {
                "validation_mode": "none",
                "overall_decision": "ACCEPTED",
                "note": "No LLM validator configured - entry accepted without semantic validation",
            }

        # Update entry with validation results
        decision = validation_result.get("overall_decision", "PENDING")
        entry.validation_status = decision.lower()

        if validation_result.get("llm_validation"):
            llm_val = validation_result["llm_validation"]
            if "validations" in llm_val:
                entry.validation_paraphrases = llm_val.get("paraphrases", [])
            elif "validation" in llm_val:
                entry.validation_paraphrases = [llm_val["validation"].get("paraphrase", "")]

    # Add to blockchain
    result = blockchain.add_entry(entry)

    # Auto-mine if requested
    auto_mine = data.get("auto_mine", False)
    mined_block = None
    if auto_mine:
        mined_block = blockchain.mine_pending_entries()
        save_chain()

    response = {"status": "success", "entry": result, "validation": validation_result}

    if mined_block:
        response["mined_block"] = {"index": mined_block.index, "hash": mined_block.hash}

    return jsonify(response), 201


@core_bp.route("/entry/validate", methods=["POST"])
@require_api_key
def validate_entry():
    """
    Validate an entry without adding it to the blockchain.

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description",
        "multi_validator": true/false (optional)
    }

    Returns:
        Validation results
    """
    if not managers.hybrid_validator:
        return jsonify(
            {"error": "LLM validation not available", "reason": "ANTHROPIC_API_KEY not configured"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    is_valid, error_msg = validate_json_schema(
        data,
        required_fields={"content": str, "author": str, "intent": str},
        optional_fields={"multi_validator": bool},
        max_lengths={"content": 50000, "author": 500, "intent": 2000},
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify(
            {"error": "Missing required fields", "required": ["content", "author", "intent"]}
        ), 400

    validation_result = managers.hybrid_validator.validate(
        content=content,
        intent=intent,
        author=author,
        use_llm=True,
        multi_validator=data.get("multi_validator", False),
    )

    return jsonify(validation_result)


@core_bp.route("/mine", methods=["POST"])
@require_api_key
def mine_block():
    """
    Mine pending entries into a new block.

    Request body (optional):
    {
        "difficulty": 2 (optional, default from chain)
    }

    Returns:
        Mined block details
    """
    data = request.get_json() or {}
    difficulty = data.get("difficulty")

    if not blockchain.pending_entries:
        return jsonify({"error": "No pending entries to mine"}), 400

    # Mine the block
    if difficulty:
        new_block = blockchain.mine_pending_entries(difficulty=difficulty)
    else:
        new_block = blockchain.mine_pending_entries()

    # Persist to file
    save_chain()

    return jsonify(
        {
            "status": "success",
            "block": {
                "index": new_block.index,
                "timestamp": new_block.timestamp,
                "entries_count": len(new_block.entries),
                "hash": new_block.hash,
                "previous_hash": new_block.previous_hash,
            },
        }
    ), 201


@core_bp.route("/block/<int:index>", methods=["GET"])
def get_block(index: int):
    """
    Get a specific block by index.

    Args:
        index: Block index (0 = genesis block)

    Returns:
        Block details
    """
    if index < 0 or index >= len(blockchain.chain):
        return jsonify(
            {"error": "Block not found", "valid_range": f"0-{len(blockchain.chain) - 1}"}
        ), 404

    block = blockchain.chain[index]
    return jsonify(block.to_dict())


@core_bp.route("/block/latest", methods=["GET"])
def get_latest_block():
    """
    Get the most recent block.

    Returns:
        Latest block details with metadata
    """
    if not blockchain.chain:
        return jsonify({"error": "No blocks in chain"}), 404

    latest = blockchain.chain[-1]
    return jsonify(
        {
            "block": latest.to_dict(),
            "chain_length": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
        }
    )


@core_bp.route("/entries/author/<author>", methods=["GET"])
def get_entries_by_author(author: str):
    """
    Get all entries by a specific author.

    Args:
        author: Author identifier

    Returns:
        List of entries by the author
    """
    entries = blockchain.get_entries_by_author(author)
    return jsonify(
        {"author": author, "count": len(entries), "entries": [e.to_dict() for e in entries]}
    )


@core_bp.route("/entries/search", methods=["GET"])
def search_entries():
    """
    Search entries by content keyword.

    Query params:
        q: Search query
        limit: Maximum results (default 10)

    Returns:
        Matching entries
    """
    query = request.args.get("q", "")
    limit = request.args.get("limit", 10, type=int)

    # Bound the limit
    limit, _ = validate_pagination_params(limit)

    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400

    # Simple keyword search across all entries
    results = []
    for block in blockchain.chain:
        for entry in block.entries:
            if query.lower() in entry.content.lower():
                results.append(entry.to_dict())
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return jsonify({"query": query, "count": len(results), "entries": results})


@core_bp.route("/validate/chain", methods=["GET"])
def validate_blockchain():
    """
    Validate the entire blockchain integrity.

    Returns:
        Validation status
    """
    is_valid = blockchain.validate_chain()
    return jsonify(
        {
            "valid": is_valid,
            "blocks": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
        }
    )


@core_bp.route("/pending", methods=["GET"])
def get_pending_entries():
    """
    Get all pending (unmined) entries.

    Returns:
        List of pending entries
    """
    return jsonify(
        {
            "count": len(blockchain.pending_entries),
            "entries": [e.to_dict() for e in blockchain.pending_entries],
        }
    )


@core_bp.route("/stats", methods=["GET"])
def get_stats():
    """
    Get blockchain statistics.

    Returns:
        Comprehensive stats about the chain
    """
    # Count total entries across all blocks
    total_entries = sum(len(block.entries) for block in blockchain.chain)

    # Get unique authors
    authors = set()
    for block in blockchain.chain:
        for entry in block.entries:
            authors.add(entry.author)

    # Feature availability
    features = {
        "llm_validation": managers.llm_validator is not None,
        "semantic_search": managers.search_engine is not None,
        "drift_detection": managers.drift_detector is not None,
        "dialectic_consensus": managers.dialectic_validator is not None,
        "multi_model_consensus": managers.multi_model_consensus is not None,
        "contract_management": managers.contract_parser is not None,
        "dispute_management": managers.dispute_manager is not None,
        "temporal_fixity": managers.temporal_fixity is not None,
        "semantic_oracles": managers.semantic_oracle is not None,
        "escalation_forks": managers.escalation_fork_manager is not None,
        "observance_burns": managers.observance_burn_manager is not None,
        "anti_harassment": managers.anti_harassment_manager is not None,
        "treasury": managers.treasury is not None,
        "fido2_auth": managers.fido2_manager is not None,
        "zk_privacy": managers.zk_privacy_manager is not None,
        "negotiation": managers.negotiation_engine is not None,
        "market_pricing": managers.market_pricing is not None,
        "mobile_deployment": managers.mobile_deployment is not None,
    }

    return jsonify(
        {
            "blocks": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
            "total_entries": total_entries,
            "unique_authors": len(authors),
            "chain_valid": blockchain.validate_chain(),
            "features": features,
        }
    )
