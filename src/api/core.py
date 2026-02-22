"""
Core blockchain operations blueprint.

This blueprint handles the fundamental blockchain operations:
- Chain retrieval and narrative
- Entry creation and validation
- Block mining and retrieval
- Statistics
"""

import json

from flask import Blueprint, jsonify, request

from . import state
from .state import (
    create_entry_with_encryption,
    save_chain,
)
from .utils import (
    DEFAULT_PAGE_LIMIT,
    managers,
    require_api_key,
    validate_json_schema,
    validate_pagination_params,
)

# Create the blueprint
core_bp = Blueprint("core", __name__)


@core_bp.route("/chain", methods=["GET"])
@require_api_key
def get_chain():
    """
    Get the entire blockchain.

    Returns:
        Full blockchain data
    """
    return jsonify(
        {
            "length": len(state.blockchain.chain),
            "chain": state.blockchain.to_dict(),
            "valid": state.blockchain.validate_chain(),
        }
    )


@core_bp.route("/chain/narrative", methods=["GET"])
@require_api_key
def get_narrative():
    """
    Get the full narrative history as human-readable text.

    This is a key feature: the entire ledger as readable prose.

    Returns:
        Complete narrative of all entries
    """
    narrative = state.blockchain.get_full_narrative()
    # SECURITY: Sanitize narrative output to prevent injection payload passthrough (Finding 2.2)
    from sanitization import sanitize_output
    narrative = sanitize_output(narrative)
    return narrative, 200, {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": "inline",
    }


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

    # Validate metadata size and structure if provided
    MAX_METADATA_LEN = 10000  # 10KB for metadata
    MAX_METADATA_KEYS = 100  # Maximum number of top-level keys
    MAX_METADATA_DEPTH = 5  # Maximum nesting depth
    metadata = data.get("metadata", {})
    if metadata:
        # Validate key count to prevent resource exhaustion
        if len(metadata) > MAX_METADATA_KEYS:
            return jsonify(
                {"error": "Metadata has too many keys", "max_keys": MAX_METADATA_KEYS}
            ), 400

        # Validate nesting depth
        def _check_depth(obj, depth=1):
            if depth > MAX_METADATA_DEPTH:
                return False
            if isinstance(obj, dict):
                return all(_check_depth(v, depth + 1) for v in obj.values())
            if isinstance(obj, list):
                return all(_check_depth(v, depth + 1) for v in obj)
            return True

        if not _check_depth(metadata):
            return jsonify(
                {"error": "Metadata nesting too deep", "max_depth": MAX_METADATA_DEPTH}
            ), 400

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
        if managers.hybrid_validator:
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
    result = state.blockchain.add_entry(entry)

    # Check if the blockchain rejected the entry (e.g., rate limit, duplicate, quality)
    if result.get("status") in ("rejected", "needs_revision"):
        return jsonify(result), 422

    # Auto-mine if requested
    auto_mine = data.get("auto_mine", False)
    mined_block = None
    if auto_mine:
        mined_block = state.blockchain.mine_pending_entries()
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

    if not state.blockchain.pending_entries:
        return jsonify({"error": "No pending entries to mine"}), 400

    # Mine the block
    if difficulty:
        new_block = state.blockchain.mine_pending_entries(difficulty=difficulty)
    else:
        new_block = state.blockchain.mine_pending_entries()

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
@require_api_key
def get_block(index: int):
    """
    Get a specific block by index.

    Args:
        index: Block index (0 = genesis block)

    Returns:
        Block details
    """
    if index < 0 or index >= len(state.blockchain.chain):
        return jsonify(
            {"error": "Block not found", "valid_range": f"0-{len(state.blockchain.chain) - 1}"}
        ), 404

    block = state.blockchain.chain[index]
    return jsonify(block.to_dict())


@core_bp.route("/block/latest", methods=["GET"])
@require_api_key
def get_latest_block():
    """
    Get the most recent block.

    Returns:
        Latest block details with metadata
    """
    if not state.blockchain.chain:
        return jsonify({"error": "No blocks in chain"}), 404

    latest = state.blockchain.chain[-1]
    return jsonify(
        {
            "block": latest.to_dict(),
            "chain_length": len(state.blockchain.chain),
            "pending_entries": len(state.blockchain.pending_entries),
        }
    )


@core_bp.route("/entries/author/<author>", methods=["GET"])
@require_api_key
def get_entries_by_author(author: str):
    """
    Get all entries by a specific author.

    Args:
        author: Author identifier

    Returns:
        List of entries by the author
    """
    entries = state.blockchain.get_entries_by_author(author)
    return jsonify(
        {"author": author, "count": len(entries), "entries": entries}
    )


@core_bp.route("/entries/search", methods=["GET"])
@require_api_key
def search_entries():
    """
    Search entries by content keyword.

    Query params:
        query: Search query (also accepts 'q' for backward compatibility)
        limit: Maximum results (default 10)

    Returns:
        Matching entries
    """
    query = request.args.get("query", "") or request.args.get("q", "")
    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)

    # Bound the limit
    limit, _ = validate_pagination_params(limit)

    if not query:
        return jsonify({"error": "Query parameter 'query' required"}), 400

    # Simple keyword search across all entries
    results = []
    for block in state.blockchain.chain:
        for entry in block.entries:
            if query.lower() in entry.content.lower():
                results.append(entry.to_dict())
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return jsonify({"query": query, "count": len(results), "entries": results})


@core_bp.route("/validate/chain", methods=["GET"])
@require_api_key
def validate_blockchain():
    """
    Validate the entire blockchain integrity.

    Returns:
        Validation status
    """
    is_valid = state.blockchain.validate_chain()

    # Verify entry signatures across the chain (Audit 1.3)
    sig_stats = {"total_entries": 0, "signed": 0, "verified": 0, "unsigned": 0, "invalid": 0}
    try:
        from identity import verify_entry_signature
        for block in state.blockchain.chain:
            for entry in block.entries:
                sig_stats["total_entries"] += 1
                result = verify_entry_signature(entry.to_dict())
                if result["signed"]:
                    sig_stats["signed"] += 1
                    if result["verified"]:
                        sig_stats["verified"] += 1
                    else:
                        sig_stats["invalid"] += 1
                else:
                    sig_stats["unsigned"] += 1
    except ImportError:
        sig_stats = None

    response = {
        "valid": is_valid,
        "blocks": len(state.blockchain.chain),
        "pending_entries": len(state.blockchain.pending_entries),
    }
    if sig_stats is not None:
        response["signatures"] = sig_stats

    return jsonify(response)


@core_bp.route("/pending", methods=["GET"])
@require_api_key
def get_pending_entries():
    """
    Get all pending (unmined) entries.

    Returns:
        List of pending entries
    """
    return jsonify(
        {
            "count": len(state.blockchain.pending_entries),
            "entries": [e.to_dict() for e in state.blockchain.pending_entries],
        }
    )


@core_bp.route("/stats", methods=["GET"])
@require_api_key
def get_stats():
    """
    Get blockchain statistics.

    Returns:
        Comprehensive stats about the chain
    """
    # Count total entries across all blocks
    total_entries = sum(len(block.entries) for block in state.blockchain.chain)

    # Get unique authors
    authors = set()
    for block in state.blockchain.chain:
        for entry in block.entries:
            authors.add(entry.author)

    # Feature availability
    manifest_count = 0
    try:
        from module_manifest import registry
        manifest_count = len(registry.manifests)
    except ImportError:
        pass

    features = {
        "llm_validation": managers.llm_validator is not None,
        "semantic_search": managers.search_engine is not None,
        "contract_management": managers.contract_parser is not None,
        "identity_signing": state.agent_identity is not None,
        "module_manifests": manifest_count,
    }

    return jsonify(
        {
            "blocks": len(state.blockchain.chain),
            "pending_entries": len(state.blockchain.pending_entries),
            "total_entries": total_entries,
            "unique_authors": len(authors),
            "chain_valid": state.blockchain.validate_chain(),
            "features": features,
        }
    )
