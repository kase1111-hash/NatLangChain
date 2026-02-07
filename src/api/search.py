"""
Search and semantic analysis blueprint.

This blueprint handles semantic search:
- Semantic search across entries
- Similar entry finding
"""

from flask import Blueprint, jsonify, request

from .state import blockchain
from .utils import managers, rate_limit_llm

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
