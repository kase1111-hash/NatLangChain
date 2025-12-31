"""
Monitoring and metrics API endpoints.

This blueprint provides:
- /metrics: Prometheus-compatible metrics endpoint
- /metrics/json: JSON format metrics
- /health: Basic health check
- /health/live: Kubernetes liveness probe
- /health/ready: Kubernetes readiness probe
"""

import os
import platform
import sys
import time

from flask import Blueprint, Response, jsonify

from api.state import blockchain, get_storage

# Create the blueprint
monitoring_bp = Blueprint('monitoring', __name__)

# Track startup time
_startup_time = time.time()


@monitoring_bp.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    """
    try:
        from monitoring import metrics

        # Update dynamic gauges before export
        _update_dynamic_metrics()

        return Response(
            metrics.to_prometheus(),
            mimetype='text/plain; charset=utf-8'
        )
    except ImportError:
        return Response(
            "# Metrics module not available\n",
            mimetype='text/plain; charset=utf-8'
        )


@monitoring_bp.route('/metrics/json', methods=['GET'])
def json_metrics():
    """
    JSON format metrics endpoint.

    Returns all collected metrics as JSON.
    """
    try:
        from monitoring import metrics

        _update_dynamic_metrics()

        return jsonify(metrics.get_all())
    except ImportError:
        return jsonify({"error": "Metrics module not available"}), 503


@monitoring_bp.route('/health', methods=['GET'])
def health():
    """
    Basic health check endpoint.

    Returns service status and key statistics.
    """
    from api.utils import managers

    return jsonify({
        "status": "healthy",
        "service": "NatLangChain API",
        "version": _get_version(),
        "uptime_seconds": time.time() - _startup_time,
        "checks": {
            "blockchain": {
                "status": "ok",
                "blocks": len(blockchain.chain),
                "pending_entries": len(blockchain.pending_entries),
            },
            "storage": _check_storage(),
            "llm": {
                "status": "ok" if managers.llm_validator else "unavailable",
                "available": managers.llm_validator is not None,
            },
        }
    })


@monitoring_bp.route('/health/live', methods=['GET'])
def liveness():
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    Should only fail if the application needs to be restarted.
    """
    return jsonify({"status": "alive"})


@monitoring_bp.route('/health/ready', methods=['GET'])
def readiness():
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to accept traffic.
    Checks that critical dependencies are available.
    """
    issues = []

    # Check blockchain
    try:
        _ = len(blockchain.chain)
    except Exception as e:
        issues.append(f"blockchain: {e}")

    # Check storage
    try:
        storage = get_storage()
        if not storage.is_available():
            issues.append("storage: not available")
    except Exception as e:
        issues.append(f"storage: {e}")

    if issues:
        return jsonify({
            "status": "not_ready",
            "issues": issues,
        }), 503

    return jsonify({"status": "ready"})


@monitoring_bp.route('/health/detailed', methods=['GET'])
def detailed_health():
    """
    Detailed health check with system information.

    Provides comprehensive system status for debugging.
    """
    from api.utils import managers

    return jsonify({
        "status": "healthy",
        "service": "NatLangChain API",
        "version": _get_version(),
        "uptime_seconds": time.time() - _startup_time,
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
        },
        "blockchain": {
            "blocks": len(blockchain.chain),
            "pending_entries": len(blockchain.pending_entries),
            "difficulty": getattr(blockchain, 'difficulty', 2),
            "valid": blockchain.validate_chain() if hasattr(blockchain, 'validate_chain') else None,
        },
        "storage": _get_storage_info(),
        "features": {
            "llm_validator": managers.llm_validator is not None,
            "hybrid_validator": managers.hybrid_validator is not None,
            "search_engine": managers.search_engine is not None,
            "drift_detector": managers.drift_detector is not None,
            "dialectic_validator": managers.dialectic_validator is not None,
            "contract_parser": managers.contract_parser is not None,
            "contract_matcher": managers.contract_matcher is not None,
            "dispute_manager": managers.dispute_manager is not None,
            "temporal_fixity": managers.temporal_fixity is not None,
            "mobile_deployment": managers.mobile_deployment is not None,
        },
        "environment": {
            "debug": os.getenv("FLASK_DEBUG", "false").lower() == "true",
            "storage_backend": os.getenv("STORAGE_BACKEND", "json"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        },
    })


def _get_version() -> str:
    """Get application version."""
    try:
        # Try to get from package metadata
        from importlib.metadata import version
        return version("natlangchain")
    except Exception:
        return "0.1.0"


def _check_storage() -> dict:
    """Check storage backend status."""
    try:
        storage = get_storage()
        available = storage.is_available()
        return {
            "status": "ok" if available else "degraded",
            "available": available,
            "backend": storage.__class__.__name__,
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e),
        }


def _get_storage_info() -> dict:
    """Get detailed storage information."""
    try:
        storage = get_storage()
        return storage.get_info()
    except Exception as e:
        return {"error": str(e)}


def _update_dynamic_metrics():
    """Update dynamic metrics (gauges) before export."""
    try:
        from monitoring import metrics

        # Blockchain metrics
        metrics.set_gauge("blockchain_blocks_total", len(blockchain.chain))
        metrics.set_gauge("blockchain_pending_entries", len(blockchain.pending_entries))

        # Calculate total entries
        total_entries = sum(
            len(block.entries) if hasattr(block, 'entries') else 0
            for block in blockchain.chain
        )
        metrics.set_gauge("blockchain_entries_total", total_entries)

        # Storage metrics
        try:
            storage = get_storage()
            if storage.is_available():
                metrics.set_gauge("storage_available", 1)
                info = storage.get_info()
                if "block_count" in info:
                    metrics.set_gauge("storage_block_count", info["block_count"])
                if "entry_count" in info:
                    metrics.set_gauge("storage_entry_count", info["entry_count"])
            else:
                metrics.set_gauge("storage_available", 0)
        except Exception:
            metrics.set_gauge("storage_available", 0)

    except ImportError:
        pass
