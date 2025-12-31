"""
Instance coordination for NatLangChain.

Provides coordination between multiple API instances:
- Instance registration and discovery
- Health tracking and leader election
- Work distribution helpers

Usage:
    from scaling import get_coordinator

    coordinator = get_coordinator()

    # Register this instance
    coordinator.register()

    # Get all active instances
    instances = coordinator.get_instances()

    # Leader election
    if coordinator.is_leader():
        perform_leader_tasks()
"""

import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class InstanceInfo:
    """Information about an API instance."""
    instance_id: str
    hostname: str
    port: int
    started_at: float
    last_heartbeat: float
    metadata: dict[str, Any] = field(default_factory=dict)
    is_leader: bool = False

    def is_healthy(self, timeout: float = 30.0) -> bool:
        """Check if instance is healthy (recent heartbeat)."""
        return (time.time() - self.last_heartbeat) < timeout


class InstanceCoordinator:
    """
    Coordinates multiple API instances.

    In single-instance deployments, this is a no-op.
    In multi-instance deployments with Redis, enables:
    - Instance discovery
    - Leader election
    - Health monitoring
    """

    def __init__(
        self,
        redis_url: str | None = None,
        instance_id: str | None = None,
        heartbeat_interval: float = 10.0,
        instance_timeout: float = 30.0,
    ):
        """
        Initialize instance coordinator.

        Args:
            redis_url: Redis URL for coordination (None = local only)
            instance_id: Unique instance identifier (auto-generated if None)
            heartbeat_interval: Seconds between heartbeats
            instance_timeout: Seconds before instance considered dead
        """
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        self._redis = None
        self._instance_id = instance_id or self._generate_instance_id()
        self._heartbeat_interval = heartbeat_interval
        self._instance_timeout = instance_timeout

        self._hostname = socket.gethostname()
        self._port = int(os.getenv("PORT", 5000))
        self._started_at = time.time()
        self._metadata: dict[str, Any] = {}

        self._heartbeat_thread: threading.Thread | None = None
        self._running = False

        self._key_prefix = "natlangchain:instances:"
        self._leader_key = "natlangchain:leader"

        if self._redis_url:
            self._init_redis()

    def _generate_instance_id(self) -> str:
        """Generate a unique instance ID."""
        hostname = socket.gethostname()
        unique = str(uuid.uuid4())[:8]
        return f"{hostname}-{unique}"

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(self._redis_url)
        except ImportError:
            self._redis = None

    @property
    def instance_id(self) -> str:
        """Get this instance's ID."""
        return self._instance_id

    def register(self, metadata: dict[str, Any] | None = None) -> None:
        """
        Register this instance and start heartbeat.

        Args:
            metadata: Optional metadata about this instance
        """
        if metadata:
            self._metadata.update(metadata)

        self._send_heartbeat()

        if not self._running:
            self._running = True
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="instance-heartbeat",
            )
            self._heartbeat_thread.start()

    def unregister(self) -> None:
        """Unregister this instance."""
        self._running = False

        if self._redis:
            key = f"{self._key_prefix}{self._instance_id}"
            self._redis.delete(key)

            # Release leader if we are leader
            if self.is_leader():
                self._release_leadership()

    def _send_heartbeat(self) -> None:
        """Send a heartbeat to Redis."""
        if not self._redis:
            return

        info = InstanceInfo(
            instance_id=self._instance_id,
            hostname=self._hostname,
            port=self._port,
            started_at=self._started_at,
            last_heartbeat=time.time(),
            metadata=self._metadata,
            is_leader=self.is_leader(),
        )

        key = f"{self._key_prefix}{self._instance_id}"
        self._redis.setex(
            key,
            int(self._instance_timeout * 2),  # TTL = 2x timeout
            self._serialize_instance(info),
        )

    def _heartbeat_loop(self) -> None:
        """Background thread for sending heartbeats."""
        while self._running:
            try:
                self._send_heartbeat()
                self._try_become_leader()
            except Exception:
                pass  # Ignore errors in background thread
            time.sleep(self._heartbeat_interval)

    def _serialize_instance(self, info: InstanceInfo) -> str:
        """Serialize instance info to JSON."""
        import json
        return json.dumps({
            "instance_id": info.instance_id,
            "hostname": info.hostname,
            "port": info.port,
            "started_at": info.started_at,
            "last_heartbeat": info.last_heartbeat,
            "metadata": info.metadata,
            "is_leader": info.is_leader,
        })

    def _deserialize_instance(self, data: bytes | str) -> InstanceInfo:
        """Deserialize instance info from JSON."""
        import json
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        d = json.loads(data)
        return InstanceInfo(
            instance_id=d["instance_id"],
            hostname=d["hostname"],
            port=d["port"],
            started_at=d["started_at"],
            last_heartbeat=d["last_heartbeat"],
            metadata=d.get("metadata", {}),
            is_leader=d.get("is_leader", False),
        )

    def get_instances(self) -> list[InstanceInfo]:
        """
        Get all active instances.

        Returns:
            List of active instance information
        """
        if not self._redis:
            # Single instance mode
            return [InstanceInfo(
                instance_id=self._instance_id,
                hostname=self._hostname,
                port=self._port,
                started_at=self._started_at,
                last_heartbeat=time.time(),
                metadata=self._metadata,
                is_leader=True,
            )]

        instances = []
        pattern = f"{self._key_prefix}*"

        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                data = self._redis.get(key)
                if data:
                    try:
                        info = self._deserialize_instance(data)
                        if info.is_healthy(self._instance_timeout):
                            instances.append(info)
                    except Exception:
                        pass
            if cursor == 0:
                break

        return instances

    def get_instance_count(self) -> int:
        """Get number of active instances."""
        return len(self.get_instances())

    def is_leader(self) -> bool:
        """
        Check if this instance is the leader.

        In single-instance mode, always returns True.
        In multi-instance mode, uses Redis for leader election.
        """
        if not self._redis:
            return True

        leader = self._redis.get(self._leader_key)
        if leader:
            return leader.decode('utf-8') == self._instance_id
        return False

    def _try_become_leader(self) -> bool:
        """Try to become the leader."""
        if not self._redis:
            return True

        # Try to set leader key if not exists
        ttl = int(self._instance_timeout)
        result = self._redis.set(
            self._leader_key,
            self._instance_id,
            nx=True,
            ex=ttl,
        )

        if result:
            return True

        # If we're already leader, extend TTL
        leader = self._redis.get(self._leader_key)
        if leader and leader.decode('utf-8') == self._instance_id:
            self._redis.expire(self._leader_key, ttl)
            return True

        return False

    def _release_leadership(self) -> None:
        """Release leadership if we hold it."""
        if not self._redis:
            return

        # Only delete if we are the leader (atomic check-and-delete)
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        end
        return 0
        """
        self._redis.eval(script, 1, self._leader_key, self._instance_id)

    def get_leader(self) -> InstanceInfo | None:
        """Get information about the current leader."""
        if not self._redis:
            return InstanceInfo(
                instance_id=self._instance_id,
                hostname=self._hostname,
                port=self._port,
                started_at=self._started_at,
                last_heartbeat=time.time(),
                metadata=self._metadata,
                is_leader=True,
            )

        leader_id = self._redis.get(self._leader_key)
        if not leader_id:
            return None

        leader_id = leader_id.decode('utf-8')
        key = f"{self._key_prefix}{leader_id}"
        data = self._redis.get(key)

        if data:
            try:
                return self._deserialize_instance(data)
            except Exception:
                pass

        return None

    def run_on_leader(self, func: Callable, *args, **kwargs) -> Any | None:
        """
        Run a function only if this instance is the leader.

        Args:
            func: Function to run
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result if leader, None otherwise
        """
        if self.is_leader():
            return func(*args, **kwargs)
        return None

    def get_info(self) -> dict[str, Any]:
        """Get coordinator status information."""
        return {
            "instance_id": self._instance_id,
            "hostname": self._hostname,
            "port": self._port,
            "started_at": self._started_at,
            "uptime_seconds": time.time() - self._started_at,
            "is_leader": self.is_leader(),
            "redis_connected": self._redis is not None,
            "instance_count": self.get_instance_count(),
            "metadata": self._metadata,
        }

    def close(self) -> None:
        """Stop the coordinator and unregister."""
        self.unregister()
        if self._redis:
            self._redis.close()
