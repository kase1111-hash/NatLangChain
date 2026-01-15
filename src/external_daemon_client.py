"""
NatLangChain - External Boundary Daemon Client

Client for communicating with the external Boundary Daemon (Agent Smith).
Supports Unix socket communication for local integration and HTTP API for remote.

Based on the Boundary Daemon specification:
https://github.com/kase1111-hash/boundary-daemon-

Key Features:
- RecallGate: Memory access control queries
- ToolGate: Tool execution authorization
- Mode synchronization with external daemon
- Event forwarding for unified audit trail
- Ceremony coordination for human overrides
"""

import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urljoin

# Optional HTTP client
try:
    pass

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DaemonDecision(Enum):
    """Decisions returned by the external daemon."""

    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class OperationType(Enum):
    """Types of operations to request from the daemon."""

    MODE_QUERY = "mode_query"
    MODE_SET = "mode_set"
    POLICY_EVAL = "policy_eval"
    RECALL_GATE = "recall_gate"
    TOOL_GATE = "tool_gate"
    EVENT_LOG = "event_log"
    CEREMONY_REQUEST = "ceremony_request"
    CEREMONY_CONFIRM = "ceremony_confirm"
    HEALTH_CHECK = "health_check"


@dataclass
class DaemonRequest:
    """Request to send to the external daemon."""

    operation: OperationType
    context: dict[str, Any]
    parameters: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: str = field(default_factory=lambda: f"REQ-{int(time.time() * 1000)}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for transmission."""
        return {
            "operation": self.operation.value,
            "context": self.context,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class DaemonResponse:
    """Response from the external daemon."""

    request_id: str
    decision: DaemonDecision
    reasoning: str
    metadata: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # For conditional approvals
    deadline: str | None = None
    ceremony_steps: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DaemonResponse":
        """Create from dictionary."""
        return cls(
            request_id=data.get("request_id", "unknown"),
            decision=DaemonDecision(data.get("decision", "deny")),
            reasoning=data.get("reasoning", ""),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            deadline=data.get("deadline"),
            ceremony_steps=data.get("ceremony_steps"),
        )

    @classmethod
    def deny(cls, request_id: str, reason: str) -> "DaemonResponse":
        """Create a denial response."""
        return cls(
            request_id=request_id, decision=DaemonDecision.DENY, reasoning=reason, metadata={}
        )


class ExternalDaemonConnectionError(Exception):
    """Raised when connection to external daemon fails."""



class ExternalDaemonClient:
    """
    Client for communicating with the external Boundary Daemon.

    Supports two transport methods:
    1. Unix socket (for local daemon on same host)
    2. HTTP API (for remote daemon)

    Fail-safe design:
    - Connection failures default to DENY
    - Timeouts default to DENY
    - Unknown responses default to DENY
    """

    DEFAULT_SOCKET_PATH = "/var/run/boundary-daemon/boundary.sock"
    DEFAULT_HTTP_URL = "http://localhost:8080/api/v1"
    DEFAULT_TIMEOUT = 5.0  # seconds

    def __init__(
        self,
        socket_path: str | None = None,
        http_url: str | None = None,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = 3,
        retry_delay: float = 0.5,
        fail_open: bool = False,  # Default to fail-closed (DENY on errors)
    ):
        """
        Initialize the external daemon client.

        Args:
            socket_path: Path to Unix socket (for local daemon)
            http_url: HTTP API URL (for remote daemon)
            api_key: API key for authentication
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Base delay between retries (exponential backoff)
            fail_open: If True, failures result in ALLOW (dangerous!)
        """
        self.socket_path = socket_path or os.getenv(
            "BOUNDARY_DAEMON_SOCKET", self.DEFAULT_SOCKET_PATH
        )
        self.http_url = http_url or os.getenv("BOUNDARY_DAEMON_URL")
        self.api_key = api_key or os.getenv("BOUNDARY_DAEMON_API_KEY")
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.fail_open = fail_open

        self._lock = threading.RLock()
        self._socket: socket.socket | None = None
        self._session: Any = None
        self._connected = False

        # Connection statistics
        self._stats = {
            "requests_sent": 0,
            "requests_succeeded": 0,
            "requests_failed": 0,
            "connection_errors": 0,
            "last_request_time": None,
        }

        # Initialize HTTP session if needed
        if self.http_url and REQUESTS_AVAILABLE:
            self._init_http_session()

    def _init_http_session(self) -> None:
        """Initialize HTTP session with connection pooling."""
        import requests

        self._session = requests.Session()
        if self.api_key:
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["User-Agent"] = "NatLangChain-DaemonClient/1.0"

    def connect(self) -> bool:
        """
        Establish connection to the daemon.

        Tries Unix socket first, then HTTP.

        Returns:
            True if connected successfully
        """
        with self._lock:
            # Try Unix socket first
            if os.path.exists(self.socket_path):
                try:
                    self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self._socket.settimeout(self.timeout)
                    self._socket.connect(self.socket_path)
                    self._connected = True
                    logger.info(f"Connected to daemon via Unix socket: {self.socket_path}")
                    return True
                except Exception as e:
                    logger.warning(f"Unix socket connection failed: {e}")
                    self._socket = None

            # Fall back to HTTP
            if self.http_url and self._session:
                try:
                    health_url = urljoin(self.http_url, "/health")
                    response = self._session.get(health_url, timeout=self.timeout)
                    if response.status_code == 200:
                        self._connected = True
                        logger.info(f"Connected to daemon via HTTP: {self.http_url}")
                        return True
                except Exception as e:
                    logger.warning(f"HTTP connection failed: {e}")

            logger.error("Failed to connect to external daemon via any transport")
            self._stats["connection_errors"] += 1
            return False

    def disconnect(self) -> None:
        """Close connection to the daemon."""
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None

            if self._session:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None

            self._connected = False
            logger.info("Disconnected from external daemon")

    def is_connected(self) -> bool:
        """Check if connected to daemon."""
        return self._connected

    def _send_request(self, request: DaemonRequest) -> DaemonResponse:
        """
        Send a request to the daemon.

        Implements retry with exponential backoff.

        Args:
            request: The request to send

        Returns:
            DaemonResponse
        """
        self._stats["requests_sent"] += 1
        self._stats["last_request_time"] = datetime.utcnow().isoformat() + "Z"

        last_error = None

        for attempt in range(self.retry_attempts):
            try:
                if self._socket:
                    response = self._send_socket(request)
                elif self._session:
                    response = self._send_http(request)
                else:
                    raise ExternalDaemonConnectionError("No connection available")

                self._stats["requests_succeeded"] += 1
                return response

            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Daemon request failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)

        # All retries failed
        self._stats["requests_failed"] += 1
        logger.error(f"Daemon request failed after {self.retry_attempts} attempts: {last_error}")

        # Fail-safe: return DENY (or ALLOW if fail_open)
        if self.fail_open:
            logger.warning("Fail-open mode: allowing request despite daemon failure")
            return DaemonResponse(
                request_id=request.request_id,
                decision=DaemonDecision.ALLOW,
                reasoning="Daemon unavailable, fail-open mode active",
                metadata={"fallback": True},
            )
        else:
            return DaemonResponse.deny(
                request_id=request.request_id,
                reason=f"Daemon unavailable (fail-closed): {last_error}",
            )

    # Maximum response size to prevent DoS via large responses (10MB)
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024

    def _send_socket(self, request: DaemonRequest) -> DaemonResponse:
        """Send request via Unix socket."""
        if not self._socket:
            raise ExternalDaemonConnectionError("Socket not connected")

        try:
            # Send request
            request_data = request.to_json().encode() + b"\n"
            self._socket.sendall(request_data)

            # Receive response with size limit to prevent DoS
            response_data = b""
            while True:
                chunk = self._socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                # Security: Prevent DoS via unbounded response
                if len(response_data) > self.MAX_RESPONSE_SIZE:
                    raise ExternalDaemonConnectionError(
                        f"Response exceeded max size ({self.MAX_RESPONSE_SIZE} bytes)"
                    )
                if b"\n" in chunk:
                    break

            response_dict = json.loads(response_data.decode().strip())
            return DaemonResponse.from_dict(response_dict)

        except TimeoutError:
            raise ExternalDaemonConnectionError("Socket timeout")
        except json.JSONDecodeError as e:
            raise ExternalDaemonConnectionError(f"Invalid response JSON: {e}")

    def _send_http(self, request: DaemonRequest) -> DaemonResponse:
        """Send request via HTTP API."""
        if not self._session:
            raise ExternalDaemonConnectionError("HTTP session not available")

        try:
            # Map operation to endpoint
            endpoint_map = {
                OperationType.MODE_QUERY: "/mode",
                OperationType.MODE_SET: "/mode",
                OperationType.POLICY_EVAL: "/policy/evaluate",
                OperationType.RECALL_GATE: "/gate/recall",
                OperationType.TOOL_GATE: "/gate/tool",
                OperationType.EVENT_LOG: "/events",
                OperationType.CEREMONY_REQUEST: "/ceremony/request",
                OperationType.CEREMONY_CONFIRM: "/ceremony/confirm",
                OperationType.HEALTH_CHECK: "/health",
            }

            endpoint = endpoint_map.get(request.operation, "/request")
            url = urljoin(self.http_url, endpoint)

            # Determine HTTP method
            if request.operation in [
                OperationType.MODE_SET,
                OperationType.EVENT_LOG,
                OperationType.CEREMONY_REQUEST,
                OperationType.CEREMONY_CONFIRM,
            ]:
                method = "POST"
            else:
                method = "POST"  # Use POST for all gated operations

            response = self._session.request(
                method, url, json=request.to_dict(), timeout=self.timeout
            )

            if response.status_code == 200:
                return DaemonResponse.from_dict(response.json())
            else:
                logger.warning(f"Daemon HTTP error {response.status_code}: {response.text}")
                return DaemonResponse.deny(request.request_id, f"HTTP error {response.status_code}")

        except Exception as e:
            raise ExternalDaemonConnectionError(f"HTTP request failed: {e}")

    # =========================================================================
    # RecallGate - Memory Access Control
    # =========================================================================

    def check_recall(self, memory_class: int, purpose: str, requester: str) -> DaemonResponse:
        """
        Query RecallGate for memory access permission.

        Args:
            memory_class: Memory classification level (0-5)
            purpose: Why the memory is being accessed
            requester: Who is requesting access

        Returns:
            DaemonResponse with ALLOW/DENY decision
        """
        request = DaemonRequest(
            operation=OperationType.RECALL_GATE,
            context={"requester": requester, "process": "NatLangChain"},
            parameters={"memory_class": memory_class, "purpose": purpose},
        )
        return self._send_request(request)

    # =========================================================================
    # ToolGate - Tool Execution Control
    # =========================================================================

    def check_tool(
        self, tool_name: str, parameters: dict[str, Any], requester: str
    ) -> DaemonResponse:
        """
        Query ToolGate for tool execution permission.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            requester: Who is requesting the tool

        Returns:
            DaemonResponse with ALLOW/DENY decision
        """
        request = DaemonRequest(
            operation=OperationType.TOOL_GATE,
            context={"requester": requester, "process": "NatLangChain"},
            parameters={"tool": tool_name, "tool_parameters": parameters},
        )
        return self._send_request(request)

    # =========================================================================
    # Mode Management
    # =========================================================================

    def get_mode(self) -> DaemonResponse:
        """
        Get current boundary mode from the daemon.

        Returns:
            DaemonResponse with mode in metadata
        """
        request = DaemonRequest(
            operation=OperationType.MODE_QUERY, context={"process": "NatLangChain"}, parameters={}
        )
        return self._send_request(request)

    def set_mode(self, mode: str, reason: str, requester: str) -> DaemonResponse:
        """
        Request mode change from the daemon.

        Args:
            mode: Target mode (open, restricted, trusted, airgap, coldroom, lockdown)
            reason: Why the mode change is needed
            requester: Who is requesting the change

        Returns:
            DaemonResponse
        """
        request = DaemonRequest(
            operation=OperationType.MODE_SET,
            context={"requester": requester, "process": "NatLangChain"},
            parameters={"target_mode": mode, "reason": reason},
        )
        return self._send_request(request)

    # =========================================================================
    # Policy Evaluation
    # =========================================================================

    def evaluate_policy(
        self, action: str, resource: str, context: dict[str, Any]
    ) -> DaemonResponse:
        """
        Evaluate a policy decision.

        Args:
            action: The action being attempted
            resource: The resource being accessed
            context: Additional context

        Returns:
            DaemonResponse with policy decision
        """
        request = DaemonRequest(
            operation=OperationType.POLICY_EVAL,
            context={"process": "NatLangChain", **context},
            parameters={"action": action, "resource": resource},
        )
        return self._send_request(request)

    # =========================================================================
    # Event Logging
    # =========================================================================

    def log_event(
        self, event_type: str, event_data: dict[str, Any], severity: int = 3
    ) -> DaemonResponse:
        """
        Forward an event to the daemon for unified audit trail.

        Args:
            event_type: Type of event (e.g., "policy_decision", "mode_change")
            event_data: Event details
            severity: Severity level (0-10)

        Returns:
            DaemonResponse
        """
        request = DaemonRequest(
            operation=OperationType.EVENT_LOG,
            context={"process": "NatLangChain"},
            parameters={"event_type": event_type, "event_data": event_data, "severity": severity},
        )
        return self._send_request(request)

    # =========================================================================
    # Human Override Ceremony
    # =========================================================================

    def request_ceremony(
        self, ceremony_type: str, reason: str, requester: str, target: str
    ) -> DaemonResponse:
        """
        Request a human override ceremony.

        Args:
            ceremony_type: Type of ceremony (e.g., "mode_change", "emergency_access")
            reason: Why the ceremony is needed
            requester: Who is requesting
            target: What the ceremony is for (e.g., target mode)

        Returns:
            DaemonResponse with ceremony_steps
        """
        request = DaemonRequest(
            operation=OperationType.CEREMONY_REQUEST,
            context={"requester": requester, "process": "NatLangChain"},
            parameters={"ceremony_type": ceremony_type, "reason": reason, "target": target},
        )
        return self._send_request(request)

    def confirm_ceremony(
        self, ceremony_id: str, confirmation_code: str, confirmed_by: str
    ) -> DaemonResponse:
        """
        Confirm a human override ceremony.

        Args:
            ceremony_id: ID of the ceremony to confirm
            confirmation_code: The confirmation code
            confirmed_by: Who is confirming

        Returns:
            DaemonResponse
        """
        request = DaemonRequest(
            operation=OperationType.CEREMONY_CONFIRM,
            context={"confirmed_by": confirmed_by, "process": "NatLangChain"},
            parameters={"ceremony_id": ceremony_id, "confirmation_code": confirmation_code},
        )
        return self._send_request(request)

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check against the daemon.

        Returns:
            Health status dictionary
        """
        request = DaemonRequest(
            operation=OperationType.HEALTH_CHECK, context={"process": "NatLangChain"}, parameters={}
        )

        try:
            response = self._send_request(request)
            return {
                "healthy": response.decision == DaemonDecision.ALLOW,
                "connected": self._connected,
                "transport": "socket" if self._socket else "http" if self._session else "none",
                "details": response.metadata,
                "stats": self._stats.copy(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "connected": False,
                "error": str(e),
                "stats": self._stats.copy(),
            }

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return self._stats.copy()


# =============================================================================
# Convenience Functions
# =============================================================================

_global_daemon_client: ExternalDaemonClient | None = None


def get_daemon_client() -> ExternalDaemonClient | None:
    """Get the global daemon client instance."""
    return _global_daemon_client


def init_daemon_client(**kwargs) -> ExternalDaemonClient:
    """
    Initialize the global daemon client.

    Args:
        **kwargs: Arguments to pass to ExternalDaemonClient

    Returns:
        The initialized client
    """
    global _global_daemon_client
    _global_daemon_client = ExternalDaemonClient(**kwargs)
    _global_daemon_client.connect()
    return _global_daemon_client


def shutdown_daemon_client() -> None:
    """Shutdown the global daemon client."""
    global _global_daemon_client
    if _global_daemon_client:
        _global_daemon_client.disconnect()
        _global_daemon_client = None
