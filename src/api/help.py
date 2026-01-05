"""
Governance help API blueprint.

This blueprint provides documentation endpoints for:
- NCIPs (NatLangChain Improvement Proposals)
- MP specs (Mediator Protocol specifications)
- Core concepts and design philosophy
- Documentation search
"""

from flask import Blueprint, jsonify, request

# Try to import governance help system
try:
    from governance_help import get_help_system
    GOVERNANCE_HELP_AVAILABLE = True
except ImportError:
    GOVERNANCE_HELP_AVAILABLE = False
    get_help_system = None

# Create the blueprint
help_bp = Blueprint('help', __name__, url_prefix='/api/help')


def _check_available():
    """Check if governance help is available."""
    if not GOVERNANCE_HELP_AVAILABLE:
        return jsonify({"error": "Governance help not available"}), 503
    return None


@help_bp.route('/overview', methods=['GET'])
def help_overview():
    """Get help system overview."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_help_overview())


@help_bp.route('/ncips', methods=['GET'])
def list_ncips():
    """Get list of all NCIPs."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_ncip_list())


@help_bp.route('/ncips/by-category', methods=['GET'])
def ncips_by_category():
    """Get NCIPs organized by category."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_ncips_by_category())


@help_bp.route('/ncips/<ncip_id>', methods=['GET'])
def get_ncip(ncip_id):
    """Get a specific NCIP."""
    if (error := _check_available()):
        return error
    ncip = get_help_system().get_ncip(ncip_id)
    if not ncip:
        return jsonify({"error": f"NCIP {ncip_id} not found"}), 404
    return jsonify(ncip)


@help_bp.route('/ncips/<ncip_id>/full', methods=['GET'])
def get_ncip_full(ncip_id):
    """Get full markdown content of an NCIP."""
    if (error := _check_available()):
        return error
    content = get_help_system().get_ncip_full_text(ncip_id)
    if not content:
        return jsonify({"error": f"NCIP {ncip_id} content not found"}), 404
    return jsonify({"id": ncip_id, "content": content})


@help_bp.route('/mps', methods=['GET'])
def list_mps():
    """Get list of all Mediator Protocol specs."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_mp_list())


@help_bp.route('/mps/<mp_id>', methods=['GET'])
def get_mp(mp_id):
    """Get a specific MP spec."""
    if (error := _check_available()):
        return error
    mp = get_help_system().get_mp(mp_id)
    if not mp:
        return jsonify({"error": f"MP {mp_id} not found"}), 404
    return jsonify(mp)


@help_bp.route('/concepts', methods=['GET'])
def list_concepts():
    """Get all core concepts."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_core_concepts())


@help_bp.route('/concepts/<concept_id>', methods=['GET'])
def get_concept(concept_id):
    """Get a specific concept."""
    if (error := _check_available()):
        return error
    concept = get_help_system().get_concept(concept_id)
    if not concept:
        return jsonify({"error": f"Concept {concept_id} not found"}), 404
    return jsonify(concept)


@help_bp.route('/philosophy', methods=['GET'])
def get_philosophy():
    """Get design philosophy."""
    if (error := _check_available()):
        return error
    return jsonify(get_help_system().get_design_philosophy())


@help_bp.route('/search', methods=['GET'])
def search_governance():
    """Search governance documentation."""
    if (error := _check_available()):
        return error
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    return jsonify(get_help_system().search_governance(query))
