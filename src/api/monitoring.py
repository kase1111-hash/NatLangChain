"""
Monitoring and metrics API endpoints.

This blueprint provides:
- /metrics: Prometheus-compatible metrics endpoint
- /metrics/json: JSON format metrics
- /health: Basic health check
- /health/live: Kubernetes liveness probe
- /health/ready: Kubernetes readiness probe
- /cluster/instances: List active instances
- /cluster/info: Cluster coordination info
"""

import os
import platform
import sys
import time

from flask import Blueprint, Response, jsonify

from . import state
from .state import get_storage
from .utils import require_api_key as _require_api_key

# Create the blueprint
monitoring_bp = Blueprint("monitoring", __name__)

# Track startup time
_startup_time = time.time()


@monitoring_bp.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text exposition format.
    """
    try:
        from monitoring import metrics

        # Update dynamic gauges before export
        _update_dynamic_metrics()

        return Response(metrics.to_prometheus(), mimetype="text/plain; charset=utf-8")
    except ImportError:
        return Response("# Metrics module not available\n", mimetype="text/plain; charset=utf-8")


@monitoring_bp.route("/metrics/json", methods=["GET"])
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


@monitoring_bp.route("/health", methods=["GET"])
def health():
    """
    Basic health check endpoint.

    Returns service status and key statistics.
    """
    from api.utils import managers

    return jsonify(
        {
            "status": "healthy",
            "service": "NatLangChain API",
            "version": _get_version(),
            "uptime_seconds": time.time() - _startup_time,
            "checks": {
                "blockchain": {
                    "status": "ok",
                    "blocks": len(state.blockchain.chain),
                    "pending_entries": len(state.blockchain.pending_entries),
                },
                "storage": _check_storage(),
                "llm": {
                    "status": "ok" if managers.llm_validator else "unavailable",
                    "available": managers.llm_validator is not None,
                },
            },
        }
    )


@monitoring_bp.route("/health/live", methods=["GET"])
def liveness():
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    Should only fail if the application needs to be restarted.
    """
    return jsonify({"status": "alive"})


@monitoring_bp.route("/health/ready", methods=["GET"])
def readiness():
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to accept traffic.
    Checks that critical dependencies are available.
    """
    issues = []

    # Check blockchain
    try:
        _ = len(state.blockchain.chain)
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
        return jsonify(
            {
                "status": "not_ready",
                "issues": issues,
            }
        ), 503

    return jsonify({"status": "ready"})


@monitoring_bp.route("/health/detailed", methods=["GET"])
@_require_api_key
def detailed_health():
    """
    Detailed health check with system information.

    Provides comprehensive system status for debugging.
    """
    from api.utils import managers

    return jsonify(
        {
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
                "blocks": len(state.blockchain.chain),
                "pending_entries": len(state.blockchain.pending_entries),
                "difficulty": getattr(state.blockchain, "difficulty", 2),
                "valid": state.blockchain.validate_chain()
                if hasattr(state.blockchain, "validate_chain")
                else None,
            },
            "storage": _get_storage_info(),
            "features": {
                "llm_validator": managers.llm_validator is not None,
                "hybrid_validator": managers.hybrid_validator is not None,
                "search_engine": managers.search_engine is not None,
                "contract_parser": managers.contract_parser is not None,
                "contract_matcher": managers.contract_matcher is not None,
            },
            "environment": {
                "debug": os.getenv("FLASK_DEBUG", "false").lower() == "true",
                "storage_backend": os.getenv("STORAGE_BACKEND", "json"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
            },
        }
    )


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
        metrics.set_gauge("blockchain_blocks_total", len(state.blockchain.chain))
        metrics.set_gauge("blockchain_pending_entries", len(state.blockchain.pending_entries))

        # Calculate total entries
        total_entries = sum(
            len(block.entries) if hasattr(block, "entries") else 0 for block in state.blockchain.chain
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


# ============================================================
# Cluster/Scaling Endpoints
# ============================================================


@monitoring_bp.route("/cluster/instances", methods=["GET"])
def cluster_instances():
    """
    Get list of active API instances.

    Returns all instances registered with the coordinator.
    """
    try:
        from scaling import get_coordinator

        coordinator = get_coordinator()
        instances = coordinator.get_instances()

        return jsonify(
            {
                "instance_count": len(instances),
                "instances": [
                    {
                        "instance_id": i.instance_id,
                        "hostname": i.hostname,
                        "port": i.port,
                        "started_at": i.started_at,
                        "last_heartbeat": i.last_heartbeat,
                        "is_leader": i.is_leader,
                        "healthy": i.is_healthy(),
                    }
                    for i in instances
                ],
            }
        )
    except ImportError:
        return jsonify(
            {
                "instance_count": 1,
                "instances": [
                    {
                        "instance_id": "local",
                        "hostname": platform.node(),
                        "is_leader": True,
                    }
                ],
            }
        )


@monitoring_bp.route("/cluster/info", methods=["GET"])
def cluster_info():
    """
    Get cluster coordination information.

    Returns current instance info, leader status, and scaling config.
    """
    try:
        from scaling import get_cache, get_coordinator, get_lock_manager

        coordinator = get_coordinator()
        lock_manager = get_lock_manager()
        cache = get_cache()

        return jsonify(
            {
                "instance": coordinator.get_info(),
                "leader": {
                    "is_leader": coordinator.is_leader(),
                    "leader_info": _serialize_instance_info(coordinator.get_leader()),
                },
                "lock_manager": {
                    "type": lock_manager.__class__.__name__,
                },
                "cache": cache.get_stats(),
                "scaling_config": {
                    "redis_url": bool(os.getenv("REDIS_URL")),
                    "storage_backend": os.getenv("STORAGE_BACKEND", "json"),
                },
            }
        )
    except ImportError:
        return jsonify(
            {
                "instance": {
                    "instance_id": "local",
                    "hostname": platform.node(),
                    "is_leader": True,
                },
                "scaling_config": {
                    "redis_url": False,
                    "storage_backend": os.getenv("STORAGE_BACKEND", "json"),
                },
            }
        )


def _serialize_instance_info(info) -> dict | None:
    """Serialize InstanceInfo to dict."""
    if info is None:
        return None
    return {
        "instance_id": info.instance_id,
        "hostname": info.hostname,
        "port": info.port,
        "started_at": info.started_at,
        "is_leader": info.is_leader,
    }


# ============================================================
# Module Manifest Endpoints (Audit 2.4)
# ============================================================


@monitoring_bp.route("/security/manifests", methods=["GET"])
@_require_api_key
def module_manifests():
    """
    Module manifest audit report.

    Returns all loaded manifests, declared capabilities, and any violations.
    Requires API key authentication.
    """
    try:
        from module_manifest import get_audit_report

        return jsonify(get_audit_report())
    except ImportError:
        return jsonify({"error": "Module manifest system not available"}), 503
