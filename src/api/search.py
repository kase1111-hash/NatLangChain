"""
Search and semantic analysis blueprint.

This blueprint handles semantic search, drift detection, and dialectic consensus:
- Semantic search across entries
- Similar entry finding
- Drift detection between intent and execution
- Dialectic consensus validation
- Oracle verification
"""

from flask import Blueprint, jsonify, request

from .state import blockchain
from .utils import managers, rate_limit_llm, require_api_key, validate_json_schema

# Create the blueprint
search_bp = Blueprint("search", __name__)


# ========== Semantic Search Endpoints ==========


@search_bp.route("/search/semantic", methods=["POST"])
@rate_limit_llm
def semantic_search():
    """
    Perform semantic search across blockchain entries.

    Request body:
    {
        "query": "natural language search query",
        "top_k": 5 (optional),
        "min_score": 0.0 (optional),
        "field": "content" | "intent" | "both" (optional)
    }

    Returns:
        List of semantically similar entries
    """
    if not managers.search_engine:
        return jsonify(
            {"error": "Semantic search not available", "reason": "Search engine not initialized"}
        ), 503

    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Missing required field: query"}), 400

    query = data["query"]
    top_k = data.get("top_k", 5)
    min_score = data.get("min_score", 0.0)
    field = data.get("field", "content")

    try:
        if field in ["content", "intent", "both"]:
            results = managers.search_engine.search_by_field(
                blockchain, query, field=field, top_k=top_k, min_score=min_score
            )
        else:
            results = managers.search_engine.search(
                blockchain, query, top_k=top_k, min_score=min_score
            )

        return jsonify({"query": query, "field": field, "count": len(results), "results": results})

    except Exception:
        return jsonify({"error": "Search failed", "reason": "Internal error occurred"}), 500


@search_bp.route("/search/similar", methods=["POST"])
@rate_limit_llm
def find_similar():
    """
    Find entries similar to a given content.

    Request body:
    {
        "content": "content to find similar entries for",
        "top_k": 5 (optional),
        "exclude_exact": true (optional)
    }

    Returns:
        List of similar entries
    """
    if not managers.search_engine:
        return jsonify({"error": "Semantic search not available"}), 503

    data = request.get_json()

    if not data or "content" not in data:
        return jsonify({"error": "Missing required field: content"}), 400

    content = data["content"]
    top_k = data.get("top_k", 5)
    exclude_exact = data.get("exclude_exact", True)

    try:
        results = managers.search_engine.find_similar_entries(
            blockchain, content, top_k=top_k, exclude_exact=exclude_exact
        )

        return jsonify({"content": content, "count": len(results), "similar_entries": results})

    except Exception:
        return jsonify({"error": "Search failed", "reason": "Internal error occurred"}), 500


# ========== Semantic Drift Detection Endpoints ==========


@search_bp.route("/drift/check", methods=["POST"])
@rate_limit_llm
def check_drift():
    """
    Check semantic drift between intent and execution.

    Request body:
    {
        "on_chain_intent": "the canonical intent from blockchain",
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis with score and recommendations
    """
    if not managers.drift_detector:
        return jsonify(
            {"error": "Drift detection not available", "reason": "ANTHROPIC_API_KEY not configured"}
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    on_chain_intent = data.get("on_chain_intent")
    execution_log = data.get("execution_log")

    if not all([on_chain_intent, execution_log]):
        return jsonify(
            {"error": "Missing required fields", "required": ["on_chain_intent", "execution_log"]}
        ), 400

    result = managers.drift_detector.check_alignment(on_chain_intent, execution_log)

    return jsonify(result)


@search_bp.route("/drift/entry/<int:block_index>/<int:entry_index>", methods=["POST"])
@rate_limit_llm
def check_entry_drift(block_index: int, entry_index: int):
    """
    Check drift for a specific blockchain entry against an execution log.

    Args:
        block_index: Block index containing the entry
        entry_index: Entry index within the block

    Request body:
    {
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis for the specific entry
    """
    if not managers.drift_detector:
        return jsonify({"error": "Drift detection not available"}), 503

    # Validate block index
    if block_index < 0 or block_index >= len(blockchain.chain):
        return jsonify(
            {"error": "Block not found", "valid_range": f"0-{len(blockchain.chain) - 1}"}
        ), 404

    block = blockchain.chain[block_index]

    # Validate entry index
    if entry_index < 0 or entry_index >= len(block.entries):
        return jsonify(
            {"error": "Entry not found", "valid_range": f"0-{len(block.entries) - 1}"}
        ), 404

    entry = block.entries[entry_index]

    # Get execution log from request
    data = request.get_json()
    if not data or "execution_log" not in data:
        return jsonify({"error": "Missing required field: execution_log"}), 400

    execution_log = data["execution_log"]

    # Check drift
    result = managers.drift_detector.check_entry_execution_alignment(
        entry.content, entry.intent, execution_log
    )

    result["entry_info"] = {
        "block_index": block_index,
        "entry_index": entry_index,
        "author": entry.author,
        "intent": entry.intent,
    }

    return jsonify(result)


# ========== Dialectic Consensus Endpoint ==========


@search_bp.route("/validate/dialectic", methods=["POST"])
@rate_limit_llm
def validate_dialectic():
    """
    Validate an entry using dialectic consensus (Skeptic/Facilitator debate).

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description"
    }

    Returns:
        Dialectic validation result with both perspectives
    """
    if not managers.dialectic_validator:
        return jsonify(
            {
                "error": "Dialectic consensus not available",
                "reason": "ANTHROPIC_API_KEY not configured",
            }
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify(
            {"error": "Missing required fields", "required": ["content", "author", "intent"]}
        ), 400

    result = managers.dialectic_validator.validate_entry(content, intent, author)

    return jsonify(result)


# ========== Oracle Verification Endpoint ==========


@search_bp.route("/oracle/verify", methods=["POST"])
@require_api_key
@rate_limit_llm
def verify_oracle_event():
    """
    Verify an external event using semantic oracles with circuit breaker protection.

    Request body:
    {
        "event_description": "description of the external event",
        "claimed_outcome": "the claimed outcome",
        "evidence": {} (optional),
        "validators": ["v1", "v2", ...] (optional, max 10)
    }

    Returns:
        Oracle verification results
    """
    if not managers.semantic_oracle:
        return jsonify(
            {
                "error": "Semantic oracles not available",
                "reason": "ANTHROPIC_API_KEY not configured",
            }
        ), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    is_valid, error_msg = validate_json_schema(
        data,
        required_fields={"event_description": str, "claimed_outcome": str},
        optional_fields={"evidence": dict, "validators": list},
        max_lengths={"event_description": 10000, "claimed_outcome": 5000},
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    event_description = data["event_description"]
    claimed_outcome = data["claimed_outcome"]
    evidence = data.get("evidence", {})

    # Check circuit breaker if available
    if managers.circuit_breaker:
        if not managers.circuit_breaker.should_allow_request():
            circuit_status = managers.circuit_breaker.get_status()
            return jsonify(
                {
                    "error": "Oracle circuit breaker open",
                    "reason": "Too many failures - oracle temporarily unavailable",
                    "circuit_status": circuit_status,
                    "retry_after": circuit_status.get("time_until_half_open", 60),
                }
            ), 503

    try:
        result = managers.semantic_oracle.verify_event(
            event_description=event_description, claimed_outcome=claimed_outcome, evidence=evidence
        )

        # Record success with circuit breaker
        if managers.circuit_breaker:
            managers.circuit_breaker.record_success()

        return jsonify(result)

    except Exception:
        # Record failure with circuit breaker
        if managers.circuit_breaker:
            managers.circuit_breaker.record_failure()

        return jsonify({"error": "Oracle verification failed", "reason": "Internal error occurred"}), 500
