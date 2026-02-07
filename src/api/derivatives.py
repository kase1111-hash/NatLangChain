"""
Derivative tracking API blueprint.

This blueprint provides endpoints for intent evolution tracking:
- Get derivatives of an entry
- Get lineage/ancestry of an entry
- Get complete derivation tree
- Check derivative status
"""

from flask import Blueprint, jsonify, request

from . import state
from .utils import require_api_key, validate_json_schema

# Import derivative type constants
try:
    from blockchain import VALID_DERIVATIVE_TYPES
except ImportError:
    try:
        from src.blockchain import VALID_DERIVATIVE_TYPES
    except ImportError:
        VALID_DERIVATIVE_TYPES = {
            "amendment",
            "extension",
            "response",
            "revision",
            "reference",
            "fulfillment",
        }

# Create the blueprint
derivatives_bp = Blueprint("derivatives", __name__, url_prefix="/derivatives")


def _check_derivative_tracking():
    """Check if derivative tracking is enabled."""
    if not state.blockchain.enable_derivative_tracking:
        return jsonify(
            {
                "error": "Derivative tracking not enabled",
                "reason": "enable_derivative_tracking is False",
            }
        ), 503
    return None


def _validate_entry_ref(block_index: int, entry_index: int):
    """Validate that a block/entry reference exists."""
    if block_index < 0 or block_index >= len(state.blockchain.chain):
        return jsonify(
            {
                "error": "Block not found",
                "block_index": block_index,
                "valid_range": f"0-{len(state.blockchain.chain) - 1}",
            }
        ), 404

    block = state.blockchain.chain[block_index]
    if entry_index < 0 or entry_index >= len(block.entries):
        return jsonify(
            {
                "error": "Entry not found",
                "entry_index": entry_index,
                "valid_range": f"0-{len(block.entries) - 1}",
            }
        ), 404

    return None


@derivatives_bp.route("/types", methods=["GET"])
def get_derivative_types():
    """
    Get all valid derivative types.

    Returns:
        List of valid derivative type strings
    """
    return jsonify(
        {
            "types": list(VALID_DERIVATIVE_TYPES),
            "descriptions": {
                "amendment": "Modifies terms of parent entry",
                "extension": "Adds to parent without modifying",
                "response": "Response to parent entry",
                "revision": "Supersedes parent entirely",
                "reference": "Simply references parent",
                "fulfillment": "Fulfills/completes parent intent",
            },
        }
    )


@derivatives_bp.route("/<int:block_index>/<int:entry_index>", methods=["GET"])
def get_derivatives(block_index: int, entry_index: int):
    """
    Get all derivatives of a specific entry.

    Args:
        block_index: Block containing the parent entry
        entry_index: Index of the parent entry within the block

    Query params:
        recursive: If "true", get all descendants recursively (default: false)
        max_depth: Maximum recursion depth (default: 10)
        include_entries: If "true", include full entry data (default: false)

    Returns:
        List of derivative entry references
    """
    if error := _check_derivative_tracking():
        return error

    if error := _validate_entry_ref(block_index, entry_index):
        return error

    recursive = request.args.get("recursive", "false").lower() == "true"
    max_depth = request.args.get("max_depth", 10, type=int)
    include_entries = request.args.get("include_entries", "false").lower() == "true"

    # Bound max_depth to prevent abuse
    max_depth = min(max(1, max_depth), 50)

    result = state.blockchain.get_derivatives(
        block_index,
        entry_index,
        recursive=recursive,
        max_depth=max_depth,
        include_entries=include_entries,
    )

    return jsonify(result)


@derivatives_bp.route("/<int:block_index>/<int:entry_index>/lineage", methods=["GET"])
def get_lineage(block_index: int, entry_index: int):
    """
    Get the full ancestry/lineage of an entry.

    Traces back through all parent relationships to find
    the original root entries.

    Args:
        block_index: Block containing the entry
        entry_index: Index of the entry within the block

    Query params:
        max_depth: Maximum traversal depth (default: 10)
        include_entries: If "true", include full entry data (default: false)

    Returns:
        Lineage information including ancestors and roots
    """
    if error := _check_derivative_tracking():
        return error

    if error := _validate_entry_ref(block_index, entry_index):
        return error

    max_depth = request.args.get("max_depth", 10, type=int)
    include_entries = request.args.get("include_entries", "false").lower() == "true"

    # Bound max_depth
    max_depth = min(max(1, max_depth), 50)

    result = state.blockchain.get_lineage(
        block_index, entry_index, max_depth=max_depth, include_entries=include_entries
    )

    return jsonify(result)


@derivatives_bp.route("/<int:block_index>/<int:entry_index>/tree", methods=["GET"])
def get_derivation_tree(block_index: int, entry_index: int):
    """
    Get the complete derivation tree for an entry.

    Returns both ancestors and descendants in a tree structure.

    Args:
        block_index: Block containing the entry
        entry_index: Index of the entry within the block

    Query params:
        max_depth: Maximum traversal depth in each direction (default: 10)
        include_entries: If "true", include full entry data (default: false)

    Returns:
        Complete derivation tree with parents, lineage, roots, and derivatives
    """
    if error := _check_derivative_tracking():
        return error

    if error := _validate_entry_ref(block_index, entry_index):
        return error

    max_depth = request.args.get("max_depth", 10, type=int)
    include_entries = request.args.get("include_entries", "false").lower() == "true"

    # Bound max_depth
    max_depth = min(max(1, max_depth), 50)

    result = state.blockchain.get_derivation_tree(
        block_index, entry_index, max_depth=max_depth, include_entries=include_entries
    )

    return jsonify(result)


@derivatives_bp.route("/<int:block_index>/<int:entry_index>/status", methods=["GET"])
def get_derivative_status(block_index: int, entry_index: int):
    """
    Get derivative status for an entry.

    Returns whether the entry is a derivative and/or has derivatives.

    Args:
        block_index: Block containing the entry
        entry_index: Index of the entry within the block

    Returns:
        Derivative status information
    """
    if error := _check_derivative_tracking():
        return error

    if error := _validate_entry_ref(block_index, entry_index):
        return error

    is_derivative = state.blockchain.is_derivative(block_index, entry_index)
    has_derivatives = state.blockchain.has_derivatives(block_index, entry_index)

    # Get the entry to check for parent refs
    entry = state.blockchain.chain[block_index].entries[entry_index]

    result = {
        "block_index": block_index,
        "entry_index": entry_index,
        "is_derivative": is_derivative,
        "has_derivatives": has_derivatives,
        "derivative_type": entry.derivative_type if is_derivative else None,
        "parent_count": len(entry.parent_refs) if entry.parent_refs else 0,
    }

    if is_derivative and entry.parent_refs:
        result["parent_refs"] = entry.parent_refs

    return jsonify(result)


@derivatives_bp.route("/validate", methods=["POST"])
@require_api_key
def validate_derivative_refs():
    """
    Validate parent references before creating a derivative entry.

    Request body:
    {
        "parent_refs": [
            {"block_index": 1, "entry_index": 0},
            ...
        ],
        "derivative_type": "amendment"
    }

    Returns:
        Validation result with any issues found
    """
    if error := _check_derivative_tracking():
        return error

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    is_valid, error_msg = validate_json_schema(
        data, required_fields={"parent_refs": list, "derivative_type": str}, optional_fields={}
    )

    if not is_valid:
        return jsonify({"error": error_msg}), 400

    parent_refs = data["parent_refs"]
    derivative_type = data["derivative_type"]

    # Validate derivative type
    if derivative_type not in VALID_DERIVATIVE_TYPES:
        return jsonify(
            {
                "valid": False,
                "error": "Invalid derivative type",
                "derivative_type": derivative_type,
                "valid_types": list(VALID_DERIVATIVE_TYPES),
            }
        ), 400

    # Validate each parent reference
    issues = []
    valid_refs = []

    for i, ref in enumerate(parent_refs):
        block_idx = ref.get("block_index")
        entry_idx = ref.get("entry_index")

        if block_idx is None or entry_idx is None:
            issues.append({"ref_index": i, "error": "Missing block_index or entry_index"})
            continue

        if block_idx < 0 or block_idx >= len(state.blockchain.chain):
            issues.append({"ref_index": i, "block_index": block_idx, "error": "Block not found"})
            continue

        block = state.blockchain.chain[block_idx]
        if entry_idx < 0 or entry_idx >= len(block.entries):
            issues.append({"ref_index": i, "entry_index": entry_idx, "error": "Entry not found"})
            continue

        # Valid reference
        entry = block.entries[entry_idx]
        valid_refs.append(
            {
                "block_index": block_idx,
                "entry_index": entry_idx,
                "author": entry.author,
                "intent": entry.intent,
            }
        )

    return jsonify(
        {
            "valid": len(issues) == 0,
            "derivative_type": derivative_type,
            "total_refs": len(parent_refs),
            "valid_refs": valid_refs,
            "issues": issues,
        }
    )
