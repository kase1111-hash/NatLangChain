"""
Boundary Protection API Blueprint.

This blueprint provides REST endpoints for the boundary protection system:
- Mode management (get/set boundary modes)
- Security status and statistics
- SIEM alerts and events
- Input/output protection checks
- Human override ceremonies
- Audit log access

All endpoints are protected by API key authentication.
"""

import logging

from flask import Blueprint, jsonify, request

from .utils import (
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    require_api_key,
)

logger = logging.getLogger(__name__)

# Create the blueprint
boundary_bp = Blueprint("boundary", __name__, url_prefix="/boundary")


def _error_response(
    message: str, status_code: int = 400, error_type: str = "request_error", details: dict = None
):
    """
    Create a structured error response.

    Args:
        message: Human-readable error message
        status_code: HTTP status code
        error_type: Error classification
        details: Additional error context
    """
    response = {"error": message, "error_type": error_type, "status": status_code}
    if details:
        response["details"] = details

    logger.warning(
        f"API error response: {message}",
        extra={"status_code": status_code, "error_type": error_type, "details": details},
    )

    return jsonify(response), status_code


def _get_protection():
    """Get the boundary protection instance."""
    try:
        from boundary_protection import get_protection

        return get_protection()
    except ImportError:
        return None


# =============================================================================
# Status and Health
# =============================================================================


@boundary_bp.route("/status", methods=["GET"])
@require_api_key
def get_status():
    """
    Get comprehensive boundary protection status.

    Returns:
        Full status including mode, enforcement, SIEM, and statistics
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized", "initialized": False}), 503

    return jsonify({"initialized": True, **protection.get_status()})


@boundary_bp.route("/stats", methods=["GET"])
@require_api_key
def get_stats():
    """
    Get protection statistics.

    Returns:
        Statistics about requests, blocks, threats detected
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    return jsonify(protection.get_stats())


# =============================================================================
# Mode Management
# =============================================================================


@boundary_bp.route("/mode", methods=["GET"])
@require_api_key
def get_mode():
    """
    Get current boundary mode.

    Returns:
        Current mode and configuration
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    mode_status = protection.modes.get_status()
    return jsonify(
        {
            "current_mode": protection.current_mode.value,
            "config": mode_status.get("config", {}),
            "cooldown_remaining": mode_status.get("cooldown_remaining", 0),
        }
    )


@boundary_bp.route("/mode", methods=["PUT"])
@require_api_key
def set_mode():
    """
    Change the boundary mode.

    Request body:
    {
        "mode": "open|restricted|trusted|airgap|coldroom|lockdown",
        "reason": "Reason for the mode change",
        "triggered_by": "identifier" (optional)
    }

    Note: Relaxing security (going to less restrictive mode) requires
    a human override ceremony. See /boundary/override endpoints.

    Returns:
        Mode transition result
    """
    protection = _get_protection()
    if not protection:
        return _error_response(
            "Boundary protection not initialized", status_code=503, error_type="service_unavailable"
        )

    data = request.get_json()
    if not data:
        return _error_response("No data provided", error_type="validation_error")

    mode_str = data.get("mode")
    reason = data.get("reason", "API request")
    triggered_by = data.get("triggered_by")

    if not mode_str:
        return _error_response("Mode is required", error_type="validation_error")

    # Validate mode
    valid_modes = ["open", "restricted", "trusted", "airgap", "coldroom", "lockdown"]
    if mode_str.lower() not in valid_modes:
        return _error_response(
            f"Invalid mode. Valid modes: {valid_modes}",
            error_type="validation_error",
            details={"provided_mode": mode_str, "valid_modes": valid_modes},
        )

    try:
        from boundary_modes import BoundaryMode

        new_mode = BoundaryMode(mode_str.lower())
    except ValueError:
        return _error_response(f"Invalid mode: {mode_str}", error_type="validation_error")

    try:
        transition = protection.set_mode(new_mode, reason, triggered_by)

        if transition.success:
            logger.info(
                f"API mode change: {transition.from_mode.value} -> {transition.to_mode.value}",
                extra={
                    "transition_id": transition.transition_id,
                    "triggered_by": triggered_by,
                    "reason": reason,
                },
            )
            return jsonify(
                {
                    "success": True,
                    "transition_id": transition.transition_id,
                    "from_mode": transition.from_mode.value,
                    "to_mode": transition.to_mode.value,
                    "actions_taken": transition.actions_taken,
                }
            )
        else:
            return _error_response(
                transition.error,
                error_type="mode_transition_failed",
                details={
                    "from_mode": transition.from_mode.value,
                    "to_mode": transition.to_mode.value,
                },
            )
    except Exception as e:
        logger.error(
            f"Mode transition failed unexpectedly: {e}",
            extra={"mode": mode_str, "reason": reason},
            exc_info=True,
        )
        return _error_response(
            "Internal error during mode transition", status_code=500, error_type="internal_error"
        )


@boundary_bp.route("/mode/lockdown", methods=["POST"])
@require_api_key
def trigger_lockdown():
    """
    Immediately enter LOCKDOWN mode.

    Request body:
    {
        "reason": "Reason for lockdown"
    }

    Returns:
        Lockdown transition result
    """
    protection = _get_protection()
    if not protection:
        return _error_response(
            "Boundary protection not initialized", status_code=503, error_type="service_unavailable"
        )

    data = request.get_json() or {}
    reason = data.get("reason", "Manual lockdown via API")

    try:
        logger.warning("LOCKDOWN triggered via API", extra={"reason": reason})

        transition = protection.trigger_lockdown(reason)

        return jsonify(
            {
                "success": transition.success,
                "transition_id": transition.transition_id,
                "actions_taken": transition.actions_taken,
                "error": transition.error,
            }
        )
    except Exception as e:
        logger.error(f"Lockdown trigger failed: {e}", extra={"reason": reason}, exc_info=True)
        return _error_response(
            "Failed to trigger lockdown", status_code=500, error_type="internal_error"
        )


@boundary_bp.route("/mode/history", methods=["GET"])
@require_api_key
def get_mode_history():
    """
    Get mode transition history.

    Query parameters:
    - limit: Maximum entries to return (default 50)

    Returns:
        List of mode transitions
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_HISTORY_LIMIT, type=int)
    limit = min(limit, MAX_PAGE_LIMIT)

    history = protection.get_transition_history(limit=limit)
    return jsonify({"count": len(history), "transitions": history})


# =============================================================================
# Human Override Ceremony
# =============================================================================


@boundary_bp.route("/override/request", methods=["POST"])
@require_api_key
def request_override():
    """
    Request a human override ceremony.

    Required when relaxing security (moving to less restrictive mode).
    Returns a confirmation code that must be provided to confirm.

    Request body:
    {
        "to_mode": "target mode",
        "reason": "Reason for override",
        "requested_by": "identifier",
        "validity_minutes": 5 (optional, default 5)
    }

    Returns:
        Override request with confirmation code
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    to_mode_str = data.get("to_mode")
    reason = data.get("reason")
    requested_by = data.get("requested_by", "api_user")
    data.get("validity_minutes", 5)

    if not to_mode_str or not reason:
        return jsonify({"error": "to_mode and reason are required"}), 400

    try:
        from boundary_modes import BoundaryMode

        to_mode = BoundaryMode(to_mode_str.lower())
    except ValueError:
        return jsonify({"error": f"Invalid mode: {to_mode_str}"}), 400

    override_request = protection.request_mode_override(to_mode, reason, requested_by)

    return jsonify(
        {
            "request_id": override_request.request_id,
            "from_mode": override_request.from_mode.value,
            "to_mode": override_request.to_mode.value,
            "confirmation_code": override_request.confirmation_code,
            "expires_at": override_request.expires_at,
            "instructions": "Provide this confirmation_code to /boundary/override/confirm to complete the ceremony",
        }
    )


@boundary_bp.route("/override/confirm", methods=["POST"])
@require_api_key
def confirm_override():
    """
    Confirm a human override ceremony.

    Request body:
    {
        "request_id": "ID from the request",
        "confirmation_code": "Code from the request",
        "confirmed_by": "identifier"
    }

    Returns:
        Mode transition result
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    request_id = data.get("request_id")
    confirmation_code = data.get("confirmation_code")
    confirmed_by = data.get("confirmed_by", "api_user")

    if not request_id or not confirmation_code:
        return jsonify({"error": "request_id and confirmation_code are required"}), 400

    transition = protection.confirm_mode_override(request_id, confirmation_code, confirmed_by)

    if transition.success:
        return jsonify(
            {
                "success": True,
                "transition_id": transition.transition_id,
                "from_mode": transition.from_mode.value,
                "to_mode": transition.to_mode.value,
                "actions_taken": transition.actions_taken,
            }
        )
    else:
        return jsonify({"success": False, "error": transition.error}), 400


# =============================================================================
# Security Checks
# =============================================================================


@boundary_bp.route("/check/input", methods=["POST"])
@require_api_key
def check_input():
    """
    Check input for security threats (prompt injection, jailbreak, etc).

    Request body:
    {
        "text": "The input text to check",
        "context": "user_input|document|tool_output" (optional, default "user_input")
    }

    Returns:
        Protection result with risk assessment
    """
    protection = _get_protection()
    if not protection:
        return _error_response(
            "Boundary protection not initialized", status_code=503, error_type="service_unavailable"
        )

    data = request.get_json()
    if not data:
        return _error_response("No data provided", error_type="validation_error")

    text = data.get("text")
    context = data.get("context", "user_input")

    if not text:
        return _error_response("text is required", error_type="validation_error")

    try:
        result = protection.check_input(text, context)

        # Log if threat detected
        result_dict = result.to_dict()
        if result_dict.get("blocked", False) or result_dict.get("threat_detected", False):
            logger.warning(
                "Threat detected in input check",
                extra={
                    "context": context,
                    "text_length": len(text),
                    "risk_level": result_dict.get("risk_level"),
                    "threat_category": result_dict.get("threat_category"),
                },
            )

        return jsonify(result_dict)
    except Exception as e:
        logger.error(
            f"Input check failed: {e}",
            extra={"context": context, "text_length": len(text)},
            exc_info=True,
        )
        # Fail-safe: return as blocked when check fails
        return jsonify(
            {
                "blocked": True,
                "error": "Security check failed - treating as blocked for safety",
                "risk_level": "high",
            }
        )


@boundary_bp.route("/check/document", methods=["POST"])
@require_api_key
def check_document():
    """
    Check a document for RAG poisoning.

    Request body:
    {
        "content": "Document content",
        "document_id": "Identifier for the document",
        "source": "Source of the document (URL, file path, etc)"
    }

    Returns:
        Protection result with poisoning indicators
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    document_id = data.get("document_id", "unknown")
    source = data.get("source", "unknown")

    if not content:
        return jsonify({"error": "content is required"}), 400

    result = protection.check_document(content, document_id, source)
    return jsonify(result.to_dict())


@boundary_bp.route("/check/response", methods=["POST"])
@require_api_key
def check_response():
    """
    Check an AI response for safety issues.

    Request body:
    {
        "response": "The AI response to check"
    }

    Returns:
        Protection result with safety assessment
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    response = data.get("response")
    if not response:
        return jsonify({"error": "response is required"}), 400

    result = protection.check_response(response)
    return jsonify(result.to_dict())


@boundary_bp.route("/check/request", methods=["POST"])
@require_api_key
def check_request():
    """
    Check an outbound data request for authorization.

    Request body:
    {
        "source": "Where the request originates",
        "destination": "Where the data is going",
        "payload": "The data being sent" (object or string),
        "classification": "public|internal|confidential|restricted" (optional)
    }

    Returns:
        Authorization result
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    source = data.get("source", "api")
    destination = data.get("destination")
    payload = data.get("payload", {})
    classification = data.get("classification")

    if not destination:
        return jsonify({"error": "destination is required"}), 400

    result = protection.authorize_request(source, destination, payload, classification)
    return jsonify(result.to_dict())


@boundary_bp.route("/sanitize", methods=["POST"])
@require_api_key
def sanitize_output():
    """
    Sanitize tool output before including in context.

    Request body:
    {
        "output": "The output to sanitize",
        "tool_name": "Name of the tool" (optional)
    }

    Returns:
        Sanitized output
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    output = data.get("output")
    tool_name = data.get("tool_name", "unknown")

    if output is None:
        return jsonify({"error": "output is required"}), 400

    sanitized = protection.sanitize_tool_output(output, tool_name)
    return jsonify(
        {"sanitized": sanitized, "original_length": len(output), "sanitized_length": len(sanitized)}
    )


# =============================================================================
# Audit and Violations
# =============================================================================


@boundary_bp.route("/violations", methods=["GET"])
@require_api_key
def get_violations():
    """
    Get recent policy violations.

    Query parameters:
    - limit: Maximum entries to return (default 100)
    - severity: Filter by severity (low, medium, high, critical)

    Returns:
        List of violations
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    limit = min(limit, MAX_PAGE_LIMIT)

    violations = protection.get_violations(limit=limit)

    # Filter by severity if specified
    severity = request.args.get("severity")
    if severity:
        violations = [v for v in violations if v.get("severity") == severity]

    return jsonify({"count": len(violations), "violations": violations})


@boundary_bp.route("/audit", methods=["GET"])
@require_api_key
def get_audit_log():
    """
    Get audit log entries.

    Query parameters:
    - limit: Maximum entries to return (default 100)
    - event_type: Filter by event type

    Returns:
        List of audit entries
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    limit = min(limit, MAX_PAGE_LIMIT)

    audit_log = protection.get_audit_log(limit=limit)

    # Filter by event type if specified
    event_type = request.args.get("event_type")
    if event_type:
        audit_log = [e for e in audit_log if e.get("event_type") == event_type]

    return jsonify({"count": len(audit_log), "entries": audit_log})


# =============================================================================
# SIEM Integration
# =============================================================================


@boundary_bp.route("/siem/alerts", methods=["GET"])
@require_api_key
def get_siem_alerts():
    """
    Get alerts from the SIEM.

    Query parameters:
    - status: Filter by status (open, acknowledged, closed)
    - limit: Maximum entries to return (default 100)

    Returns:
        List of SIEM alerts
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    status = request.args.get("status")
    limit = request.args.get("limit", DEFAULT_PAGE_LIMIT, type=int)
    limit = min(limit, MAX_PAGE_LIMIT)

    alerts = protection.get_siem_alerts(status=status, limit=limit)

    return jsonify(
        {
            "count": len(alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "rule_id": a.rule_id,
                    "rule_name": a.rule_name,
                    "severity": a.severity.value,
                    "status": a.status,
                    "created_at": a.created_at,
                    "description": a.description,
                    "event_count": a.event_count,
                }
                for a in alerts
            ],
        }
    )


@boundary_bp.route("/siem/alerts/<alert_id>/acknowledge", methods=["POST"])
@require_api_key
def acknowledge_alert(alert_id):
    """
    Acknowledge a SIEM alert.

    Request body:
    {
        "note": "Optional acknowledgement note"
    }

    Returns:
        Acknowledgement result
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    data = request.get_json() or {}
    note = data.get("note")

    success = protection.acknowledge_siem_alert(alert_id, note)

    if success:
        return jsonify({"success": True, "alert_id": alert_id})
    else:
        return jsonify({"success": False, "error": "Failed to acknowledge alert"}), 400


# =============================================================================
# Policy Checks
# =============================================================================


@boundary_bp.route("/policy/tool/<tool_name>", methods=["GET"])
@require_api_key
def check_tool_allowed(tool_name):
    """
    Check if a tool is allowed in the current mode.

    Returns:
        Whether the tool is allowed
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    allowed = protection.is_tool_allowed(tool_name)
    return jsonify(
        {"tool": tool_name, "allowed": allowed, "current_mode": protection.current_mode.value}
    )


@boundary_bp.route("/policy/network", methods=["GET"])
@require_api_key
def check_network_allowed():
    """
    Check if network access is allowed in the current mode.

    Returns:
        Whether network is allowed
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    return jsonify(
        {
            "network_allowed": protection.is_network_allowed(),
            "current_mode": protection.current_mode.value,
        }
    )


# =============================================================================
# Enforcement Status
# =============================================================================


@boundary_bp.route("/enforcement", methods=["GET"])
@require_api_key
def get_enforcement_status():
    """
    Get security enforcement status.

    Returns:
        Enforcement capabilities and active rules
    """
    protection = _get_protection()
    if not protection:
        return jsonify({"error": "Boundary protection not initialized"}), 503

    return jsonify(protection.enforcement.get_enforcement_status())


# =============================================================================
# Dreaming Status
# =============================================================================


@boundary_bp.route("/dreaming", methods=["GET"])
def get_dreaming_status():
    """
    Get the current dreaming status.

    This endpoint is lightweight and designed to be polled every 5 seconds.
    No authentication required for status checks.

    Returns:
        Current system activity status
    """
    try:
        from dreaming import get_dream_status

        return jsonify(get_dream_status())
    except ImportError:
        return jsonify(
            {
                "message": "Dreaming module not available",
                "state": "idle",
                "duration": 0,
                "timestamp": None,
            }
        )
