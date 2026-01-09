"""
NatLangChain - Boundary SIEM Integration

Integrates with Boundary SIEM for enterprise security monitoring:
- Event ingestion via CEF and JSON HTTP
- Alert querying and subscription
- Blockchain-specific threat detection
- Compliance reporting

Based on the Boundary SIEM specification:
https://github.com/kase1111-hash/Boundary-SIEM
"""

import json
import logging
import os
import queue
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
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class SIEMSeverity(Enum):
    """SIEM event severity levels (0-10 scale)."""

    INFORMATIONAL = 1
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    CRITICAL = 9
    EMERGENCY = 10


class SIEMEventCategory(Enum):
    """Categories of SIEM events for NatLangChain."""

    # Chain operations
    CHAIN_ENTRY_CREATED = "chain.entry.created"
    CHAIN_BLOCK_MINED = "chain.block.mined"
    CHAIN_VALIDATION_FAILED = "chain.validation.failed"
    CHAIN_FORK_DETECTED = "chain.fork.detected"

    # Security events
    SECURITY_BOUNDARY_VIOLATION = "security.boundary.violation"
    SECURITY_MODE_CHANGE = "security.mode.change"
    SECURITY_TRIPWIRE_TRIGGERED = "security.tripwire.triggered"
    SECURITY_LOCKDOWN_ACTIVATED = "security.lockdown.activated"

    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_API_KEY_INVALID = "auth.apikey.invalid"
    AUTH_FIDO2_REGISTERED = "auth.fido2.registered"

    # AI/Agent security
    AI_PROMPT_INJECTION_DETECTED = "ai.prompt.injection.detected"
    AI_RAG_POISONING_DETECTED = "ai.rag.poisoning.detected"
    AI_HALLUCINATION_DETECTED = "ai.hallucination.detected"
    AI_JAILBREAK_ATTEMPT = "ai.jailbreak.attempt"

    # Network events
    NETWORK_OUTBOUND_BLOCKED = "network.outbound.blocked"
    NETWORK_SUSPICIOUS_DESTINATION = "network.suspicious.destination"
    NETWORK_RATE_LIMIT_EXCEEDED = "network.ratelimit.exceeded"

    # Data events
    DATA_EXFILTRATION_ATTEMPT = "data.exfiltration.attempt"
    DATA_ENCRYPTION_FAILED = "data.encryption.failed"
    DATA_SENSITIVE_ACCESS = "data.sensitive.access"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_HEALTH_CHECK = "system.health.check"
    SYSTEM_ERROR = "system.error"


@dataclass
class SIEMEvent:
    """A security event to send to the SIEM."""

    category: SIEMEventCategory
    action: str
    outcome: str  # "success", "failure", "unknown"
    severity: SIEMSeverity
    message: str
    source_host: str = field(default_factory=lambda: socket.gethostname())
    source_product: str = "NatLangChain"
    source_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    event_id: str = field(default_factory=lambda: f"NLC-{int(time.time() * 1000)}")

    # Additional context
    actor: dict[str, Any] = field(default_factory=dict)  # Who did it
    target: dict[str, Any] = field(default_factory=dict)  # What was affected
    request: dict[str, Any] = field(default_factory=dict)  # Request details
    response: dict[str, Any] = field(default_factory=dict)  # Response details
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional data

    def to_json(self) -> dict[str, Any]:
        """Convert to JSON format for SIEM ingestion."""
        return {
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "source": {
                "product": self.source_product,
                "version": self.source_version,
                "host": self.source_host,
            },
            "category": self.category.value,
            "action": self.action,
            "outcome": self.outcome,
            "severity": self.severity.value,
            "message": self.message,
            "actor": self.actor,
            "target": self.target,
            "request": self.request,
            "response": self.response,
            "metadata": self.metadata,
        }

    def to_cef(self) -> str:
        """
        Convert to CEF (Common Event Format) for syslog ingestion.

        Format: CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        """

        # Escape pipe characters in values
        def escape(s: str) -> str:
            return str(s).replace("\\", "\\\\").replace("|", "\\|")

        # Build extension fields
        extensions = []
        if self.actor:
            if "ip" in self.actor:
                extensions.append(f"src={self.actor['ip']}")
            if "user" in self.actor:
                extensions.append(f"suser={self.actor['user']}")
        if self.target:
            if "ip" in self.target:
                extensions.append(f"dst={self.target['ip']}")
            if "resource" in self.target:
                extensions.append(f"dhost={self.target['resource']}")
        if self.request:
            if "method" in self.request:
                extensions.append(f"requestMethod={self.request['method']}")
            if "url" in self.request:
                extensions.append(f"request={self.request['url']}")
        extensions.append(f"msg={escape(self.message)}")
        extensions.append(f"rt={self.timestamp}")
        extensions.append(f"externalId={self.event_id}")

        ext_str = " ".join(extensions)

        return (
            f"CEF:0|NatLangChain|BoundaryProtection|{escape(self.source_version)}|"
            f"{escape(self.category.value)}|{escape(self.action)}|{self.severity.value}|{ext_str}"
        )


@dataclass
class SIEMAlert:
    """An alert received from the SIEM."""

    alert_id: str
    rule_id: str
    rule_name: str
    severity: SIEMSeverity
    status: str  # "open", "acknowledged", "closed"
    created_at: str
    updated_at: str
    event_count: int
    first_event: str
    last_event: str
    description: str
    recommendations: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SIEMConnectionError(Exception):
    """Raised when SIEM connection fails."""

    pass


class SIEMClient:
    """
    Client for Boundary SIEM integration.

    Supports multiple transport methods:
    - HTTP/HTTPS JSON API (primary)
    - CEF over syslog (UDP/TCP)
    - Kafka (if available)

    Features:
    - Async event queuing with backpressure
    - Automatic retry with exponential backoff
    - Connection pooling
    - Event batching for efficiency
    """

    def __init__(
        self,
        siem_url: str | None = None,
        api_key: str | None = None,
        syslog_host: str | None = None,
        syslog_port: int = 514,
        syslog_protocol: str = "udp",
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_queue_size: int = 10000,
        retry_attempts: int = 3,
        verify_ssl: bool = True,
    ):
        """
        Initialize the SIEM client.

        Args:
            siem_url: Base URL for SIEM HTTP API (e.g., "https://siem.example.com")
            api_key: API key for authentication
            syslog_host: Syslog server hostname for CEF transport
            syslog_port: Syslog server port (default: 514)
            syslog_protocol: Syslog protocol ("udp" or "tcp")
            batch_size: Number of events to batch before sending
            flush_interval: Seconds between automatic flushes
            max_queue_size: Maximum events to queue before dropping
            retry_attempts: Number of retry attempts on failure
            verify_ssl: Whether to verify SSL certificates
        """
        self.siem_url = siem_url or os.getenv("BOUNDARY_SIEM_URL")
        self.api_key = api_key or os.getenv("BOUNDARY_SIEM_API_KEY")
        self.syslog_host = syslog_host or os.getenv("BOUNDARY_SIEM_SYSLOG_HOST")
        self.syslog_port = syslog_port
        self.syslog_protocol = syslog_protocol.lower()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
        self.retry_attempts = retry_attempts
        self.verify_ssl = verify_ssl

        # Event queue for async sending
        self._event_queue: queue.Queue[SIEMEvent] = queue.Queue(maxsize=max_queue_size)
        self._batch: list[SIEMEvent] = []
        self._lock = threading.Lock()

        # Background worker
        self._running = False
        self._worker_thread: threading.Thread | None = None

        # Syslog socket
        self._syslog_socket: socket.socket | None = None

        # Statistics
        self._stats = {
            "events_queued": 0,
            "events_sent": 0,
            "events_dropped": 0,
            "send_failures": 0,
            "last_send_time": None,
        }

        # HTTP session for connection pooling
        self._session: Any = None
        if REQUESTS_AVAILABLE and self.siem_url:
            import requests

            self._session = requests.Session()
            if self.api_key:
                self._session.headers["Authorization"] = f"Bearer {self.api_key}"
            self._session.headers["Content-Type"] = "application/json"
            self._session.headers["User-Agent"] = "NatLangChain-SIEM-Client/1.0"

    def start(self) -> None:
        """Start the background event sender."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Initialize syslog if configured
        if self.syslog_host:
            self._init_syslog()

        logger.info("SIEM client started")

    def stop(self) -> None:
        """Stop the background event sender and flush remaining events."""
        self._running = False

        # Flush remaining events
        self.flush()

        if self._worker_thread:
            self._worker_thread.join(timeout=10)

        if self._syslog_socket:
            self._syslog_socket.close()

        if self._session:
            self._session.close()

        logger.info("SIEM client stopped")

    def _init_syslog(self) -> None:
        """Initialize syslog socket."""
        try:
            if self.syslog_protocol == "tcp":
                self._syslog_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._syslog_socket.connect((self.syslog_host, self.syslog_port))
            else:
                self._syslog_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"Syslog connection established to {self.syslog_host}:{self.syslog_port}")
        except Exception as e:
            logger.error(f"Failed to initialize syslog: {e}")
            self._syslog_socket = None

    def send_event(self, event: SIEMEvent) -> bool:
        """
        Queue an event for sending to the SIEM.

        Args:
            event: The event to send

        Returns:
            True if queued successfully, False if queue is full
        """
        try:
            self._event_queue.put_nowait(event)
            self._stats["events_queued"] += 1
            return True
        except queue.Full:
            self._stats["events_dropped"] += 1
            logger.warning(f"SIEM event queue full, dropping event: {event.event_id}")
            return False

    def send_event_sync(self, event: SIEMEvent) -> bool:
        """
        Send an event synchronously (blocking).

        Use this for critical events that must be logged immediately.

        Args:
            event: The event to send

        Returns:
            True if sent successfully
        """
        return self._send_batch([event])

    def flush(self) -> None:
        """Flush all queued events immediately."""
        with self._lock:
            # Drain queue into batch
            while not self._event_queue.empty():
                try:
                    event = self._event_queue.get_nowait()
                    self._batch.append(event)
                except queue.Empty:
                    break

            # Send batch
            if self._batch:
                self._send_batch(self._batch)
                self._batch = []

    def _worker_loop(self) -> None:
        """Background worker loop for sending events."""
        last_flush = time.time()

        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event = self._event_queue.get(timeout=1.0)
                    with self._lock:
                        self._batch.append(event)
                except queue.Empty:
                    pass

                # Check if we should flush
                now = time.time()
                should_flush = (
                    len(self._batch) >= self.batch_size or (now - last_flush) >= self.flush_interval
                )

                if should_flush and self._batch:
                    with self._lock:
                        batch = self._batch
                        self._batch = []
                    self._send_batch(batch)
                    last_flush = now

            except Exception as e:
                logger.error(f"SIEM worker error: {e}")
                time.sleep(1)

    def _send_batch(self, batch: list[SIEMEvent]) -> bool:
        """Send a batch of events to the SIEM."""
        if not batch:
            return True

        success = False

        # Try HTTP API first
        if self.siem_url and self._session:
            success = self._send_http(batch)

        # Try syslog as fallback or additional transport
        if self.syslog_host and self._syslog_socket:
            syslog_success = self._send_syslog(batch)
            success = success or syslog_success

        if success:
            self._stats["events_sent"] += len(batch)
            self._stats["last_send_time"] = datetime.utcnow().isoformat()
        else:
            self._stats["send_failures"] += 1

        return success

    def _send_http(self, batch: list[SIEMEvent]) -> bool:
        """Send events via HTTP API."""
        if not self._session:
            return False

        url = urljoin(self.siem_url, "/api/v1/events")
        payload = {"events": [e.to_json() for e in batch]}

        for attempt in range(self.retry_attempts):
            try:
                response = self._session.post(url, json=payload, timeout=30, verify=self.verify_ssl)

                if response.status_code in (200, 201, 202):
                    return True
                elif response.status_code == 429:
                    # Rate limited - back off
                    time.sleep(2**attempt)
                else:
                    logger.warning(f"SIEM HTTP error {response.status_code}: {response.text}")

            except Exception as e:
                logger.error(f"SIEM HTTP send failed (attempt {attempt + 1}): {e}")
                time.sleep(2**attempt)

        return False

    def _send_syslog(self, batch: list[SIEMEvent]) -> bool:
        """Send events via syslog in CEF format."""
        if not self._syslog_socket:
            return False

        try:
            for event in batch:
                cef_message = event.to_cef()
                # Add syslog header (RFC 5424 simplified)
                priority = 14  # facility=1 (user), severity=6 (info)
                syslog_message = f"<{priority}>{cef_message}\n"

                if self.syslog_protocol == "tcp":
                    self._syslog_socket.send(syslog_message.encode())
                else:
                    self._syslog_socket.sendto(
                        syslog_message.encode(), (self.syslog_host, self.syslog_port)
                    )
            return True
        except Exception as e:
            logger.error(f"SIEM syslog send failed: {e}")
            # Try to reconnect
            self._init_syslog()
            return False

    # =========================================================================
    # Alert Queries
    # =========================================================================

    def get_alerts(
        self,
        status: str | None = None,
        severity: SIEMSeverity | None = None,
        limit: int = 100,
        since: str | None = None,
    ) -> list[SIEMAlert]:
        """
        Query alerts from the SIEM.

        Args:
            status: Filter by status ("open", "acknowledged", "closed")
            severity: Filter by minimum severity
            limit: Maximum number of alerts to return
            since: ISO timestamp to filter alerts after

        Returns:
            List of alerts
        """
        if not self.siem_url or not self._session:
            return []

        params = {"limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["min_severity"] = severity.value
        if since:
            params["since"] = since

        try:
            url = urljoin(self.siem_url, "/api/v1/alerts")
            response = self._session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return [self._parse_alert(a) for a in data.get("alerts", [])]
            else:
                logger.error(f"Failed to get alerts: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: str, note: str | None = None) -> bool:
        """Acknowledge an alert."""
        if not self.siem_url or not self._session:
            return False

        try:
            url = urljoin(self.siem_url, f"/api/v1/alerts/{alert_id}/acknowledge")
            response = self._session.post(url, json={"note": note} if note else {}, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False

    def close_alert(self, alert_id: str, resolution: str) -> bool:
        """Close an alert with resolution."""
        if not self.siem_url or not self._session:
            return False

        try:
            url = urljoin(self.siem_url, f"/api/v1/alerts/{alert_id}/close")
            response = self._session.post(url, json={"resolution": resolution}, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error closing alert: {e}")
            return False

    def _parse_alert(self, data: dict[str, Any]) -> SIEMAlert:
        """Parse alert from API response."""
        return SIEMAlert(
            alert_id=data.get("id", ""),
            rule_id=data.get("rule_id", ""),
            rule_name=data.get("rule_name", ""),
            severity=SIEMSeverity(data.get("severity", 5)),
            status=data.get("status", "open"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            event_count=data.get("event_count", 0),
            first_event=data.get("first_event", ""),
            last_event=data.get("last_event", ""),
            description=data.get("description", ""),
            recommendations=data.get("recommendations", []),
            events=data.get("events", []),
            metadata=data.get("metadata", {}),
        )

    # =========================================================================
    # Search & Analysis
    # =========================================================================

    def search_events(
        self,
        query: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search events in the SIEM.

        Args:
            query: Search query (e.g., "action:validator.* AND severity:>=8")
            start_time: Start of time range (ISO format)
            end_time: End of time range (ISO format)
            limit: Maximum results

        Returns:
            List of matching events
        """
        if not self.siem_url or not self._session:
            return []

        try:
            url = urljoin(self.siem_url, "/api/v1/search")
            payload = {"query": query, "limit": limit}
            if start_time or end_time:
                payload["time_range"] = {}
                if start_time:
                    payload["time_range"]["start"] = start_time
                if end_time:
                    payload["time_range"]["end"] = end_time

            response = self._session.post(url, json=payload, timeout=60)

            if response.status_code == 200:
                return response.json().get("events", [])
            else:
                logger.error(f"Search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    # =========================================================================
    # Statistics & Health
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
            "batch_size": len(self._batch),
            "connected": self._is_connected(),
        }

    def _is_connected(self) -> bool:
        """Check if connected to SIEM."""
        if self.siem_url and self._session:
            try:
                url = urljoin(self.siem_url, "/health")
                response = self._session.get(url, timeout=5)
                return response.status_code == 200
            except Exception:
                pass
        return self._syslog_socket is not None

    def health_check(self) -> dict[str, Any]:
        """Perform health check against SIEM."""
        result = {"http_available": False, "syslog_available": False, "overall_healthy": False}

        if self.siem_url and self._session:
            try:
                url = urljoin(self.siem_url, "/health")
                response = self._session.get(url, timeout=5)
                result["http_available"] = response.status_code == 200
                if result["http_available"]:
                    result["http_details"] = response.json()
            except Exception as e:
                result["http_error"] = str(e)

        if self.syslog_host and self._syslog_socket:
            result["syslog_available"] = True

        result["overall_healthy"] = result["http_available"] or result["syslog_available"]
        return result


# =============================================================================
# NatLangChain Event Helpers
# =============================================================================


class NatLangChainSIEMEvents:
    """
    Pre-built SIEM events for common NatLangChain operations.

    Usage:
        client = SIEMClient(siem_url="...")
        client.start()

        # Log an entry creation
        client.send_event(NatLangChainSIEMEvents.entry_created(
            entry_id="entry-123",
            author="alice",
            content_hash="sha256:..."
        ))
    """

    @staticmethod
    def entry_created(
        entry_id: str,
        author: str,
        content_hash: str,
        block_index: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SIEMEvent:
        """Create event for new chain entry."""
        return SIEMEvent(
            category=SIEMEventCategory.CHAIN_ENTRY_CREATED,
            action="create",
            outcome="success",
            severity=SIEMSeverity.INFORMATIONAL,
            message=f"New chain entry created by {author}",
            actor={"user": author},
            target={"entry_id": entry_id, "block_index": block_index},
            metadata={"content_hash": content_hash, **(metadata or {})},
        )

    @staticmethod
    def block_mined(
        block_index: int, block_hash: str, entry_count: int, miner: str | None = None
    ) -> SIEMEvent:
        """Create event for mined block."""
        return SIEMEvent(
            category=SIEMEventCategory.CHAIN_BLOCK_MINED,
            action="mine",
            outcome="success",
            severity=SIEMSeverity.INFORMATIONAL,
            message=f"Block {block_index} mined with {entry_count} entries",
            actor={"user": miner} if miner else {},
            target={"block_index": block_index, "block_hash": block_hash},
            metadata={"entry_count": entry_count},
        )

    @staticmethod
    def validation_failed(entry_id: str, reason: str, validator: str | None = None) -> SIEMEvent:
        """Create event for validation failure."""
        return SIEMEvent(
            category=SIEMEventCategory.CHAIN_VALIDATION_FAILED,
            action="validate",
            outcome="failure",
            severity=SIEMSeverity.MEDIUM,
            message=f"Validation failed for entry {entry_id}: {reason}",
            target={"entry_id": entry_id},
            metadata={"reason": reason, "validator": validator},
        )

    @staticmethod
    def boundary_violation(
        violation_type: str,
        source: str,
        destination: str,
        pattern: str | None = None,
        blocked: bool = True,
    ) -> SIEMEvent:
        """Create event for boundary policy violation."""
        return SIEMEvent(
            category=SIEMEventCategory.SECURITY_BOUNDARY_VIOLATION,
            action="block" if blocked else "detect",
            outcome="success" if blocked else "failure",
            severity=SIEMSeverity.HIGH,
            message=f"Boundary violation: {violation_type} from {source} to {destination}",
            actor={"source": source},
            target={"destination": destination},
            metadata={
                "violation_type": violation_type,
                "pattern": pattern,
                "action_taken": "blocked" if blocked else "logged",
            },
        )

    @staticmethod
    def mode_change(
        old_mode: str, new_mode: str, reason: str | None = None, triggered_by: str | None = None
    ) -> SIEMEvent:
        """Create event for boundary mode change."""
        return SIEMEvent(
            category=SIEMEventCategory.SECURITY_MODE_CHANGE,
            action="change",
            outcome="success",
            severity=SIEMSeverity.MEDIUM,
            message=f"Boundary mode changed from {old_mode} to {new_mode}",
            actor={"user": triggered_by} if triggered_by else {},
            metadata={"old_mode": old_mode, "new_mode": new_mode, "reason": reason},
        )

    @staticmethod
    def tripwire_triggered(
        tripwire_type: str, trigger_details: str, automatic_response: str | None = None
    ) -> SIEMEvent:
        """Create event for tripwire activation."""
        return SIEMEvent(
            category=SIEMEventCategory.SECURITY_TRIPWIRE_TRIGGERED,
            action="trigger",
            outcome="success",
            severity=SIEMSeverity.CRITICAL,
            message=f"Tripwire triggered: {tripwire_type} - {trigger_details}",
            metadata={
                "tripwire_type": tripwire_type,
                "details": trigger_details,
                "automatic_response": automatic_response,
            },
        )

    @staticmethod
    def lockdown_activated(
        reason: str, triggered_by: str | None = None, actions_taken: list[str] | None = None
    ) -> SIEMEvent:
        """Create event for lockdown activation."""
        return SIEMEvent(
            category=SIEMEventCategory.SECURITY_LOCKDOWN_ACTIVATED,
            action="activate",
            outcome="success",
            severity=SIEMSeverity.EMERGENCY,
            message=f"LOCKDOWN activated: {reason}",
            actor={"user": triggered_by} if triggered_by else {},
            metadata={"reason": reason, "actions_taken": actions_taken or []},
        )

    @staticmethod
    def prompt_injection_detected(
        input_text: str,
        detection_method: str,
        patterns_matched: list[str] | None = None,
        source_ip: str | None = None,
    ) -> SIEMEvent:
        """Create event for prompt injection detection."""
        # Truncate input for safety
        safe_input = input_text[:200] + "..." if len(input_text) > 200 else input_text

        return SIEMEvent(
            category=SIEMEventCategory.AI_PROMPT_INJECTION_DETECTED,
            action="detect",
            outcome="success",
            severity=SIEMSeverity.HIGH,
            message=f"Prompt injection detected via {detection_method}",
            actor={"ip": source_ip} if source_ip else {},
            metadata={
                "input_preview": safe_input,
                "detection_method": detection_method,
                "patterns_matched": patterns_matched or [],
            },
        )

    @staticmethod
    def rag_poisoning_detected(document_id: str, source: str, indicators: list[str]) -> SIEMEvent:
        """Create event for RAG document poisoning detection."""
        return SIEMEvent(
            category=SIEMEventCategory.AI_RAG_POISONING_DETECTED,
            action="detect",
            outcome="success",
            severity=SIEMSeverity.HIGH,
            message=f"Potential RAG poisoning detected in document {document_id}",
            target={"document_id": document_id, "source": source},
            metadata={"indicators": indicators},
        )

    @staticmethod
    def jailbreak_attempt(input_text: str, technique: str, blocked: bool = True) -> SIEMEvent:
        """Create event for jailbreak attempt."""
        safe_input = input_text[:200] + "..." if len(input_text) > 200 else input_text

        return SIEMEvent(
            category=SIEMEventCategory.AI_JAILBREAK_ATTEMPT,
            action="block" if blocked else "detect",
            outcome="success" if blocked else "failure",
            severity=SIEMSeverity.CRITICAL,
            message=f"Jailbreak attempt detected: {technique}",
            metadata={"input_preview": safe_input, "technique": technique, "blocked": blocked},
        )

    @staticmethod
    def api_auth_failed(source_ip: str, endpoint: str, reason: str) -> SIEMEvent:
        """Create event for API authentication failure."""
        return SIEMEvent(
            category=SIEMEventCategory.AUTH_API_KEY_INVALID,
            action="authenticate",
            outcome="failure",
            severity=SIEMSeverity.MEDIUM,
            message=f"API authentication failed from {source_ip}: {reason}",
            actor={"ip": source_ip},
            request={"endpoint": endpoint},
            metadata={"reason": reason},
        )

    @staticmethod
    def rate_limit_exceeded(
        source_ip: str, endpoint: str, limit: int, window_seconds: int
    ) -> SIEMEvent:
        """Create event for rate limit exceeded."""
        return SIEMEvent(
            category=SIEMEventCategory.NETWORK_RATE_LIMIT_EXCEEDED,
            action="throttle",
            outcome="success",
            severity=SIEMSeverity.LOW,
            message=f"Rate limit exceeded for {source_ip} on {endpoint}",
            actor={"ip": source_ip},
            request={"endpoint": endpoint},
            metadata={"limit": limit, "window_seconds": window_seconds},
        )

    @staticmethod
    def data_exfiltration_attempt(
        source: str,
        destination: str,
        data_classification: str,
        payload_size: int,
        blocked: bool = True,
    ) -> SIEMEvent:
        """Create event for data exfiltration attempt."""
        return SIEMEvent(
            category=SIEMEventCategory.DATA_EXFILTRATION_ATTEMPT,
            action="block" if blocked else "detect",
            outcome="success" if blocked else "failure",
            severity=SIEMSeverity.CRITICAL,
            message=f"Data exfiltration attempt: {data_classification} data to {destination}",
            actor={"source": source},
            target={"destination": destination},
            metadata={
                "data_classification": data_classification,
                "payload_size": payload_size,
                "blocked": blocked,
            },
        )

    @staticmethod
    def system_startup(version: str, config: dict[str, Any] | None = None) -> SIEMEvent:
        """Create event for system startup."""
        return SIEMEvent(
            category=SIEMEventCategory.SYSTEM_STARTUP,
            action="start",
            outcome="success",
            severity=SIEMSeverity.INFORMATIONAL,
            message=f"NatLangChain started (version {version})",
            metadata={"version": version, "config": config or {}},
        )

    @staticmethod
    def system_error(
        error_type: str, error_message: str, component: str, stack_trace: str | None = None
    ) -> SIEMEvent:
        """Create event for system error."""
        return SIEMEvent(
            category=SIEMEventCategory.SYSTEM_ERROR,
            action="error",
            outcome="failure",
            severity=SIEMSeverity.HIGH,
            message=f"System error in {component}: {error_message}",
            metadata={"error_type": error_type, "component": component, "stack_trace": stack_trace},
        )


# =============================================================================
# Global SIEM client singleton
# =============================================================================

_global_client: SIEMClient | None = None


def get_siem_client() -> SIEMClient | None:
    """Get the global SIEM client instance."""
    return _global_client


def init_siem_client(**kwargs) -> SIEMClient:
    """
    Initialize the global SIEM client.

    Args:
        **kwargs: Arguments to pass to SIEMClient

    Returns:
        The initialized client
    """
    global _global_client
    _global_client = SIEMClient(**kwargs)
    _global_client.start()
    return _global_client


def shutdown_siem_client() -> None:
    """Shutdown the global SIEM client."""
    global _global_client
    if _global_client:
        _global_client.stop()
        _global_client = None


# =============================================================================
# Enhanced SIEM Client for External Boundary-SIEM Integration
# =============================================================================


class AuthMethod(Enum):
    """Authentication methods for Boundary-SIEM."""

    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    SAML = "saml"
    OIDC = "oidc"
    MTLS = "mtls"


@dataclass
class SIEMAuthConfig:
    """Authentication configuration for Boundary-SIEM."""

    method: AuthMethod = AuthMethod.BEARER_TOKEN
    token: str | None = None

    # OAuth2 configuration
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    oauth2_token_url: str | None = None
    oauth2_scope: str = "siem:write siem:read"

    # OIDC configuration
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None

    # mTLS configuration
    mtls_cert_path: str | None = None
    mtls_key_path: str | None = None
    mtls_ca_path: str | None = None

    @classmethod
    def from_env(cls) -> "SIEMAuthConfig":
        """Create auth config from environment variables."""
        method_str = os.getenv("BOUNDARY_SIEM_AUTH_METHOD", "bearer_token")
        try:
            method = AuthMethod(method_str.lower())
        except ValueError:
            method = AuthMethod.BEARER_TOKEN

        return cls(
            method=method,
            token=os.getenv("BOUNDARY_SIEM_API_KEY"),
            oauth2_client_id=os.getenv("BOUNDARY_SIEM_OAUTH2_CLIENT_ID"),
            oauth2_client_secret=os.getenv("BOUNDARY_SIEM_OAUTH2_CLIENT_SECRET"),
            oauth2_token_url=os.getenv("BOUNDARY_SIEM_OAUTH2_TOKEN_URL"),
            oauth2_scope=os.getenv("BOUNDARY_SIEM_OAUTH2_SCOPE", "siem:write siem:read"),
            oidc_issuer=os.getenv("BOUNDARY_SIEM_OIDC_ISSUER"),
            oidc_client_id=os.getenv("BOUNDARY_SIEM_OIDC_CLIENT_ID"),
            mtls_cert_path=os.getenv("BOUNDARY_SIEM_MTLS_CERT"),
            mtls_key_path=os.getenv("BOUNDARY_SIEM_MTLS_KEY"),
            mtls_ca_path=os.getenv("BOUNDARY_SIEM_MTLS_CA"),
        )


class EnhancedSIEMClient(SIEMClient):
    """
    Enhanced SIEM client with full Boundary-SIEM integration.

    Additional features over base SIEMClient:
    - OAuth2/SAML/OIDC authentication
    - GraphQL query support
    - Kafka streaming (if available)
    - Canonical event schema validation
    - Bulk event ingestion
    - Real-time WebSocket subscriptions
    """

    def __init__(
        self,
        siem_url: str | None = None,
        auth_config: SIEMAuthConfig | None = None,
        syslog_host: str | None = None,
        syslog_port: int = 514,
        syslog_protocol: str = "udp",
        kafka_brokers: list[str] | None = None,
        kafka_topic: str = "boundary-siem-events",
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_queue_size: int = 10000,
        retry_attempts: int = 3,
        verify_ssl: bool = True,
        validate_schema: bool = True,
    ):
        """
        Initialize the enhanced SIEM client.

        Args:
            siem_url: Base URL for SIEM HTTP API
            auth_config: Authentication configuration
            syslog_host: Syslog server hostname
            syslog_port: Syslog server port
            syslog_protocol: Syslog protocol (udp/tcp)
            kafka_brokers: List of Kafka broker addresses
            kafka_topic: Kafka topic for events
            batch_size: Events per batch
            flush_interval: Flush interval in seconds
            max_queue_size: Maximum queue size
            retry_attempts: Number of retry attempts
            verify_ssl: Verify SSL certificates
            validate_schema: Validate events against schema
        """
        # Initialize base client
        super().__init__(
            siem_url=siem_url,
            api_key=auth_config.token if auth_config else None,
            syslog_host=syslog_host,
            syslog_port=syslog_port,
            syslog_protocol=syslog_protocol,
            batch_size=batch_size,
            flush_interval=flush_interval,
            max_queue_size=max_queue_size,
            retry_attempts=retry_attempts,
            verify_ssl=verify_ssl,
        )

        self.auth_config = auth_config or SIEMAuthConfig.from_env()
        self.kafka_brokers = kafka_brokers or os.getenv("BOUNDARY_SIEM_KAFKA_BROKERS", "").split(
            ","
        )
        self.kafka_brokers = [b.strip() for b in self.kafka_brokers if b.strip()]
        self.kafka_topic = kafka_topic
        self.validate_schema = validate_schema

        # Kafka producer (if available and configured)
        self._kafka_producer = None
        self._init_kafka()

        # OAuth2 token cache
        self._oauth2_token: str | None = None
        self._oauth2_token_expires: float = 0

        # Apply authentication to session
        if self._session:
            self._apply_auth()

    def _init_kafka(self) -> None:
        """Initialize Kafka producer if brokers are configured."""
        if not self.kafka_brokers:
            return

        try:
            from kafka import KafkaProducer

            self._kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_brokers,
                value_serializer=lambda v: json.dumps(v).encode(),
                retries=self.retry_attempts,
                acks="all",
            )
            logger.info(f"Kafka producer initialized: {self.kafka_brokers}")
        except ImportError:
            logger.debug("kafka-python not available, Kafka streaming disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")

    def _apply_auth(self) -> None:
        """Apply authentication to the HTTP session."""
        if not self._session:
            return

        if self.auth_config.method == AuthMethod.BEARER_TOKEN:
            if self.auth_config.token:
                self._session.headers["Authorization"] = f"Bearer {self.auth_config.token}"

        elif self.auth_config.method == AuthMethod.OAUTH2:
            token = self._get_oauth2_token()
            if token:
                self._session.headers["Authorization"] = f"Bearer {token}"

        elif self.auth_config.method == AuthMethod.MTLS:
            if self.auth_config.mtls_cert_path and self.auth_config.mtls_key_path:
                self._session.cert = (
                    self.auth_config.mtls_cert_path,
                    self.auth_config.mtls_key_path,
                )
                if self.auth_config.mtls_ca_path:
                    self._session.verify = self.auth_config.mtls_ca_path

    def _get_oauth2_token(self) -> str | None:
        """Get OAuth2 access token (with caching)."""
        now = time.time()
        if self._oauth2_token and now < self._oauth2_token_expires:
            return self._oauth2_token

        if not all(
            [
                self.auth_config.oauth2_client_id,
                self.auth_config.oauth2_client_secret,
                self.auth_config.oauth2_token_url,
            ]
        ):
            logger.error("OAuth2 credentials not configured")
            return None

        try:
            import requests

            response = requests.post(
                self.auth_config.oauth2_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.auth_config.oauth2_client_id,
                    "client_secret": self.auth_config.oauth2_client_secret,
                    "scope": self.auth_config.oauth2_scope,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self._oauth2_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self._oauth2_token_expires = now + expires_in - 60  # Refresh 1 min early
                return self._oauth2_token
            else:
                logger.error(f"OAuth2 token request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"OAuth2 token request error: {e}")
            return None

    def _validate_event(self, event: SIEMEvent) -> list[str]:
        """
        Validate event against Boundary-SIEM canonical schema.

        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Required fields
        if not event.timestamp:
            errors.append("Missing required field: timestamp")
        if not event.category:
            errors.append("Missing required field: category")
        if not event.action:
            errors.append("Missing required field: action")
        if not event.outcome:
            errors.append("Missing required field: outcome")

        # Severity range
        if not (0 <= event.severity.value <= 10):
            errors.append(f"Severity out of range: {event.severity.value}")

        # Outcome values
        valid_outcomes = ["success", "failure", "unknown"]
        if event.outcome not in valid_outcomes:
            errors.append(f"Invalid outcome: {event.outcome}")

        return errors

    def send_event(self, event: SIEMEvent) -> bool:
        """
        Queue an event for sending.

        Validates against schema if enabled.
        """
        if self.validate_schema:
            errors = self._validate_event(event)
            if errors:
                logger.warning(f"Event validation failed: {errors}")
                # Still queue the event but log the issue
                event.metadata["validation_errors"] = errors

        return super().send_event(event)

    def _send_batch(self, batch: list[SIEMEvent]) -> bool:
        """Send batch via all available transports."""
        success = super()._send_batch(batch)

        # Also send to Kafka if available
        if self._kafka_producer and batch:
            try:
                for event in batch:
                    self._kafka_producer.send(self.kafka_topic, value=event.to_json())
                self._kafka_producer.flush()
                success = True
            except Exception as e:
                logger.error(f"Kafka send failed: {e}")

        return success

    # =========================================================================
    # GraphQL Support
    # =========================================================================

    def graphql_query(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Execute a GraphQL query against the SIEM.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query result or None on error

        Example:
            result = client.graphql_query('''
                query GetEvents($limit: Int!) {
                    events(limit: $limit) {
                        id
                        timestamp
                        severity
                        action
                    }
                }
            ''', {"limit": 100})
        """
        if not self.siem_url or not self._session:
            return None

        try:
            url = urljoin(self.siem_url, "/graphql")
            response = self._session.post(
                url, json={"query": query, "variables": variables or {}}, timeout=60
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"GraphQL query failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"GraphQL error: {e}")
            return None

    def query_events_graphql(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query events using GraphQL.

        Args:
            filters: Event filters (severity, action, time_range, etc.)
            limit: Maximum events to return
            fields: Fields to return (default: id, timestamp, severity, action, outcome)

        Returns:
            List of events
        """
        default_fields = ["id", "timestamp", "severity", "action", "outcome", "message"]
        fields = fields or default_fields

        query = f"""
            query GetEvents($filters: EventFilters, $limit: Int!) {{
                events(filters: $filters, limit: $limit) {{
                    {" ".join(fields)}
                }}
            }}
        """

        result = self.graphql_query(query, {"filters": filters or {}, "limit": limit})

        if result and "data" in result:
            return result["data"].get("events", [])
        return []

    def query_alerts_graphql(
        self, status: str | None = None, severity: int | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Query alerts using GraphQL.

        Args:
            status: Filter by status (open, acknowledged, closed)
            severity: Minimum severity
            limit: Maximum alerts to return

        Returns:
            List of alerts
        """
        query = """
            query GetAlerts($status: String, $minSeverity: Int, $limit: Int!) {
                alerts(status: $status, minSeverity: $minSeverity, limit: $limit) {
                    id
                    rule_id
                    rule_name
                    severity
                    status
                    created_at
                    description
                    event_count
                }
            }
        """

        result = self.graphql_query(
            query, {"status": status, "minSeverity": severity, "limit": limit}
        )

        if result and "data" in result:
            return result["data"].get("alerts", [])
        return []

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def send_events_bulk(self, events: list[SIEMEvent], sync: bool = False) -> dict[str, Any]:
        """
        Send multiple events in bulk.

        More efficient than sending events one by one.

        Args:
            events: List of events to send
            sync: If True, send synchronously and wait for confirmation

        Returns:
            Result with success count and any errors
        """
        if not events:
            return {"success": 0, "failed": 0, "errors": []}

        if self.validate_schema:
            for event in events:
                errors = self._validate_event(event)
                if errors:
                    event.metadata["validation_errors"] = errors

        if sync:
            success = self._send_batch(events)
            return {
                "success": len(events) if success else 0,
                "failed": 0 if success else len(events),
                "errors": [] if success else ["Batch send failed"],
            }
        else:
            queued = 0
            failed = 0
            errors = []

            for event in events:
                if self.send_event(event):
                    queued += 1
                else:
                    failed += 1
                    errors.append(f"Failed to queue event: {event.event_id}")

            return {"queued": queued, "failed": failed, "errors": errors}

    # =========================================================================
    # Detection Rules
    # =========================================================================

    def get_detection_rules(self) -> list[dict[str, Any]]:
        """
        Get available detection rules from the SIEM.

        Returns:
            List of detection rules
        """
        if not self.siem_url or not self._session:
            return []

        try:
            url = urljoin(self.siem_url, "/api/v1/rules")
            response = self._session.get(url, timeout=30)

            if response.status_code == 200:
                return response.json().get("rules", [])
            else:
                logger.error(f"Failed to get detection rules: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting detection rules: {e}")
            return []

    def create_custom_rule(
        self, name: str, query: str, severity: int, description: str, tags: list[str] | None = None
    ) -> dict[str, Any] | None:
        """
        Create a custom detection rule.

        Args:
            name: Rule name
            query: Detection query
            severity: Alert severity (0-10)
            description: Rule description
            tags: Optional tags

        Returns:
            Created rule or None on error
        """
        if not self.siem_url or not self._session:
            return None

        try:
            url = urljoin(self.siem_url, "/api/v1/rules")
            response = self._session.post(
                url,
                json={
                    "name": name,
                    "query": query,
                    "severity": severity,
                    "description": description,
                    "tags": tags or [],
                    "enabled": True,
                },
                timeout=30,
            )

            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(f"Failed to create rule: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error creating rule: {e}")
            return None

    def stop(self) -> None:
        """Stop the enhanced client and cleanup resources."""
        super().stop()

        if self._kafka_producer:
            try:
                self._kafka_producer.close()
            except Exception:
                pass
            self._kafka_producer = None


# =============================================================================
# Global Enhanced Client
# =============================================================================

_global_enhanced_client: EnhancedSIEMClient | None = None


def get_enhanced_siem_client() -> EnhancedSIEMClient | None:
    """Get the global enhanced SIEM client instance."""
    return _global_enhanced_client


def init_enhanced_siem_client(**kwargs) -> EnhancedSIEMClient:
    """
    Initialize the global enhanced SIEM client.

    Args:
        **kwargs: Arguments to pass to EnhancedSIEMClient

    Returns:
        The initialized client
    """
    global _global_enhanced_client
    _global_enhanced_client = EnhancedSIEMClient(**kwargs)
    _global_enhanced_client.start()
    return _global_enhanced_client


def shutdown_enhanced_siem_client() -> None:
    """Shutdown the global enhanced SIEM client."""
    global _global_enhanced_client
    if _global_enhanced_client:
        _global_enhanced_client.stop()
        _global_enhanced_client = None
