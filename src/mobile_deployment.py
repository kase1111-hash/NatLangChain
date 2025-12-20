"""
NatLangChain - Mobile Deployment
Portable system architecture for edge AI and mobile wallet integration.

"The best interface is no interface.
 The best device is the one you have with you."

This module implements:
- Edge AI optimization for on-device inference
- Mobile wallet integration (WalletConnect, native)
- Portable system architecture (NatLangChain, ILRM, RRA)
- Offline-first capability with sync
"""

import json
import hashlib
import secrets
import base64
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import os
import threading
import queue
import time


# ============================================================
# Enums and Constants
# ============================================================

class DeviceType(Enum):
    """Mobile device types."""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    DESKTOP = "desktop"
    EMBEDDED = "embedded"


class WalletType(Enum):
    """Wallet types for mobile integration."""
    WALLETCONNECT = "walletconnect"
    WALLET_CONNECT = "wallet_connect"  # Alias
    METAMASK = "metamask"
    COINBASE = "coinbase"
    TRUST = "trust"
    LEDGER = "ledger"
    TREZOR = "trezor"
    NATIVE = "native"
    HARDWARE = "hardware"


class SyncStatus(Enum):
    """Sync operation status."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


class ConnectionState(Enum):
    """Connection state for mobile devices."""
    ONLINE = "online"
    CONNECTED = "connected"
    OFFLINE = "offline"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    SYNCING = "syncing"


class ModelSize(Enum):
    """AI model sizes for edge deployment."""
    NANO = "nano"       # < 50MB, fastest
    MICRO = "micro"     # 50-100MB
    SMALL = "small"     # 100-500MB
    MEDIUM = "medium"   # 500MB-1GB
    LARGE = "large"     # > 1GB, full capability


# ============================================================
# Data Classes
# ============================================================

@dataclass
class DeviceProfile:
    """Mobile device profile."""
    device_id: str
    device_type: DeviceType
    device_name: str = "Unknown Device"
    os_version: str = "1.0"
    app_version: str = "1.0"
    platform_version: str = "1.0"
    capabilities: Dict[str, Any] = field(default_factory=dict)
    memory_mb: int = 2048
    storage_mb: int = 1024
    cpu_cores: int = 4
    has_gpu: bool = False
    has_npu: bool = False  # Neural Processing Unit
    battery_optimization: bool = True
    is_active: bool = True
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_sync: Optional[datetime] = None
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WalletConnection:
    """Mobile wallet connection."""
    connection_id: str
    wallet_type: WalletType
    wallet_address: str
    chain_id: int = 1
    connected_at: Optional[datetime] = None
    state: ConnectionState = ConnectionState.ONLINE
    device_id: Optional[str] = None
    session_topic: Optional[str] = None  # WalletConnect session
    is_hardware: bool = False
    permissions: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    signature_count: int = 0


@dataclass
class SyncOperation:
    """Sync operation for offline-first."""
    operation_id: str
    operation_type: str
    data: Dict[str, Any]
    status: SyncStatus
    created_at: str
    synced_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    conflict_resolution: Optional[str] = None


@dataclass
class LocalState:
    """Local state for offline operation."""
    state_id: str
    entity_type: str
    entity_id: str
    data: Dict[str, Any]
    version: int
    last_modified: str
    is_dirty: bool = False
    sync_status: SyncStatus = SyncStatus.SYNCED


@dataclass
class SyncConflict:
    """Sync conflict record."""
    conflict_id: str
    resource_type: str
    resource_id: str
    local_data: Dict[str, Any]
    remote_data: Dict[str, Any]
    conflict_type: str
    detected_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class LoadedModel:
    """Loaded AI model configuration."""
    model_id: str
    model_type: str
    model_path: Optional[str] = None
    model_size: ModelSize = ModelSize.SMALL
    is_quantized: bool = False
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    inference_count: int = 0
    memory_mb: int = 100
    optimizations: List[str] = field(default_factory=list)


@dataclass
class ResourceLimits:
    """Edge AI resource limits."""
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    max_battery_drain_percent: float = 10.0
    prefer_wifi: bool = True


# ============================================================
# Edge AI Runtime
# ============================================================

class EdgeAIRuntime:
    """
    Edge AI runtime for on-device inference.

    Features:
    - Model optimization and quantization
    - Resource-aware inference
    - Battery-efficient operation
    - Fallback to cloud when needed
    """

    # Model configurations by size
    MODEL_CONFIGS = {
        ModelSize.NANO: {
            "max_tokens": 128,
            "context_window": 512,
            "quantization": "int4",
            "memory_mb": 50,
            "latency_ms": 50
        },
        ModelSize.MICRO: {
            "max_tokens": 256,
            "context_window": 1024,
            "quantization": "int8",
            "memory_mb": 100,
            "latency_ms": 100
        },
        ModelSize.SMALL: {
            "max_tokens": 512,
            "context_window": 2048,
            "quantization": "fp16",
            "memory_mb": 300,
            "latency_ms": 200
        },
        ModelSize.MEDIUM: {
            "max_tokens": 1024,
            "context_window": 4096,
            "quantization": "fp16",
            "memory_mb": 700,
            "latency_ms": 500
        },
        ModelSize.LARGE: {
            "max_tokens": 2048,
            "context_window": 8192,
            "quantization": "fp32",
            "memory_mb": 1500,
            "latency_ms": 1000
        }
    }

    def __init__(self):
        """Initialize edge AI runtime."""
        self.loaded_models: Dict[str, LoadedModel] = {}
        self.inference_cache: Dict[str, Any] = {}
        self.resource_usage: Dict[str, float] = {
            "memory_mb": 0,
            "cpu_percent": 0,
            "battery_impact": 0
        }
        self.resource_limits = ResourceLimits()
        self.inference_count = 0
        self.cache_hits = 0
        self.fallback_count = 0

    def get_optimal_model_size(self, device: DeviceProfile) -> ModelSize:
        """
        Determine optimal model size for device.

        Args:
            device: Device profile

        Returns:
            Optimal model size
        """
        available_memory = device.memory_mb * 0.3  # Use max 30% of memory

        if device.has_npu:
            # NPU devices can handle larger models
            available_memory *= 1.5

        if device.battery_optimization:
            # Prefer smaller models for battery
            available_memory *= 0.7

        # Find largest model that fits
        for size in [ModelSize.LARGE, ModelSize.MEDIUM, ModelSize.SMALL, ModelSize.MICRO, ModelSize.NANO]:
            config = self.MODEL_CONFIGS[size]
            if config["memory_mb"] <= available_memory:
                return size

        return ModelSize.NANO

    def load_model(
        self,
        model_id: str,
        size: ModelSize,
        device: DeviceProfile,
        model_type: str = "generic",
        model_path: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Load a model for on-device inference.

        Args:
            model_id: Model identifier
            size: Model size
            device: Device profile
            model_type: Type of model
            model_path: Path to model file

        Returns:
            Tuple of (success, model info)
        """
        config = self.MODEL_CONFIGS[size]

        # Check memory
        if self.resource_usage["memory_mb"] + config["memory_mb"] > device.memory_mb * 0.5:
            # Unload least recently used model
            self._unload_lru_model()

        # Create LoadedModel instance
        is_quantized = config["quantization"] in ["int4", "int8"]
        optimizations = self._get_optimizations(device, size)

        loaded_model = LoadedModel(
            model_id=model_id,
            model_type=model_type,
            model_path=model_path,
            model_size=size,
            is_quantized=is_quantized,
            loaded_at=datetime.utcnow(),
            inference_count=0,
            memory_mb=config["memory_mb"],
            optimizations=optimizations
        )

        self.loaded_models[model_id] = loaded_model
        self.resource_usage["memory_mb"] += config["memory_mb"]

        return True, {
            "model_id": model_id,
            "size": size.value,
            "config": config,
            "loaded_at": loaded_model.loaded_at.isoformat(),
            "device_id": device.device_id,
            "optimizations": optimizations
        }

    def _get_optimizations(self, device: DeviceProfile, size: ModelSize) -> List[str]:
        """Get applicable optimizations for device."""
        optimizations = []

        if device.has_npu:
            optimizations.append("npu_acceleration")
        if device.has_gpu:
            optimizations.append("gpu_acceleration")
        if device.cpu_cores >= 4:
            optimizations.append("multi_thread")
        if size in [ModelSize.NANO, ModelSize.MICRO]:
            optimizations.append("quantized_weights")
        if device.battery_optimization:
            optimizations.append("power_efficient_mode")

        return optimizations

    def _unload_lru_model(self):
        """Unload least recently used model."""
        if not self.loaded_models:
            return

        # Find oldest model
        oldest = min(
            self.loaded_models.items(),
            key=lambda x: x[1].loaded_at
        )

        model_id, model = oldest
        self.resource_usage["memory_mb"] -= model.memory_mb
        del self.loaded_models[model_id]

    def run_inference(
        self,
        model_id: str,
        input_text: str,
        max_tokens: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Run on-device inference.

        Args:
            model_id: Model to use
            input_text: Input text
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (success, result)
        """
        if model_id not in self.loaded_models:
            return False, {"error": "Model not loaded"}

        model = self.loaded_models[model_id]
        config = self.MODEL_CONFIGS[model.model_size]

        # Check cache (using SHA-256 for consistency with security standards)
        cache_key = hashlib.sha256(f"{model_id}:{input_text}".encode()).hexdigest()[:32]
        if cache_key in self.inference_cache:
            self.cache_hits += 1
            model.inference_count += 1
            return True, {
                "cached": True,
                "result": self.inference_cache[cache_key]
            }

        # Simulate inference
        effective_max = min(max_tokens or config["max_tokens"], config["max_tokens"])

        # Simulated output (in production, would run actual model)
        result = {
            "model_id": model_id,
            "input_length": len(input_text),
            "output": f"[Edge AI Response for: {input_text[:50]}...]",
            "tokens_generated": effective_max,
            "latency_ms": config["latency_ms"],
            "on_device": True
        }

        # Cache result
        self.inference_cache[cache_key] = result
        self.inference_count += 1
        model.inference_count += 1

        # Limit cache size
        if len(self.inference_cache) > 100:
            # Remove oldest entries
            oldest_keys = list(self.inference_cache.keys())[:20]
            for key in oldest_keys:
                del self.inference_cache[key]

        return True, result

    def should_fallback_to_cloud(
        self,
        input_text: str,
        device: DeviceProfile,
        connection: ConnectionState
    ) -> Tuple[bool, str]:
        """
        Determine if should fallback to cloud inference.

        Args:
            input_text: Input to process
            device: Device profile
            connection: Current connection state

        Returns:
            Tuple of (should_fallback, reason)
        """
        # Offline - must use edge
        if connection == ConnectionState.OFFLINE:
            return False, "offline_mode"

        # Check input complexity
        if len(input_text) > 2000:
            return True, "input_too_long"

        # Check battery
        if device.battery_optimization and self.resource_usage["battery_impact"] > 0.5:
            return True, "battery_preservation"

        # Check memory pressure
        if self.resource_usage["memory_mb"] > device.memory_mb * 0.4:
            return True, "memory_pressure"

        return False, "edge_capable"

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        return {
            "memory_mb": self.resource_usage["memory_mb"],
            "loaded_models": len(self.loaded_models),
            "inference_count": self.inference_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.inference_count, 1),
            "fallback_count": self.fallback_count
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get edge AI statistics."""
        return {
            "models_loaded": len(self.loaded_models),
            "total_inferences": self.inference_count,
            "memory_mb": self.resource_usage["memory_mb"],
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.inference_count, 1),
            "fallback_count": self.fallback_count
        }


# ============================================================
# Mobile Wallet Integration
# ============================================================

class MobileWalletManager:
    """
    Mobile wallet integration manager.

    Supports:
    - WalletConnect protocol
    - Native wallet APIs
    - Hardware wallet via mobile
    - Transaction signing
    """

    # Supported chains
    SUPPORTED_CHAINS = {
        1: "Ethereum Mainnet",
        137: "Polygon",
        42161: "Arbitrum One",
        10: "Optimism",
        8453: "Base",
        43114: "Avalanche"
    }

    def __init__(self):
        """Initialize wallet manager."""
        self.connections: Dict[str, WalletConnection] = {}
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.transaction_history: List[Dict[str, Any]] = []
        self.session_topics: Dict[str, str] = {}  # topic -> connection_id

    def initiate_wallet_connect(
        self,
        device_id: str,
        required_chains: List[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Initiate WalletConnect session.

        Args:
            device_id: Device initiating connection
            required_chains: Required chain IDs

        Returns:
            Tuple of (success, connection request)
        """
        session_topic = f"wc:{secrets.token_hex(16)}"
        connection_id = f"WALLET-{secrets.token_hex(8).upper()}"

        chains = required_chains or [1]  # Default to Ethereum

        # Generate WalletConnect URI (simulated)
        wc_uri = f"wc:{session_topic}@2?relay-protocol=irn&symKey={secrets.token_hex(32)}"

        request = {
            "connection_id": connection_id,
            "session_topic": session_topic,
            "uri": wc_uri,
            "required_chains": chains,
            "required_methods": [
                "eth_sendTransaction",
                "eth_signTypedData_v4",
                "personal_sign"
            ],
            "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            "status": "awaiting_approval"
        }

        self.pending_requests[connection_id] = request
        self.session_topics[session_topic] = connection_id

        return True, request

    def complete_wallet_connect(
        self,
        connection_id: str,
        wallet_address: str,
        chain_id: int,
        wallet_type: WalletType = WalletType.WALLET_CONNECT
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete WalletConnect handshake.

        Args:
            connection_id: Connection to complete
            wallet_address: Connected wallet address
            chain_id: Connected chain
            wallet_type: Type of wallet

        Returns:
            Tuple of (success, connection info)
        """
        if connection_id not in self.pending_requests:
            return False, {"error": "Connection request not found"}

        request = self.pending_requests[connection_id]

        # Validate chain
        if chain_id not in self.SUPPORTED_CHAINS:
            return False, {"error": f"Chain {chain_id} not supported"}

        connection = WalletConnection(
            connection_id=connection_id,
            wallet_type=wallet_type,
            wallet_address=wallet_address,
            chain_id=chain_id,
            connected_at=datetime.utcnow().isoformat(),
            session_topic=request.get("session_topic"),
            permissions=request.get("required_methods", []),
            expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat()
        )

        self.connections[connection_id] = connection
        del self.pending_requests[connection_id]

        return True, {
            "connection_id": connection_id,
            "wallet_address": wallet_address,
            "chain": self.SUPPORTED_CHAINS.get(chain_id, f"Chain {chain_id}"),
            "chain_id": chain_id,
            "expires_at": connection.expires_at
        }

    def connect_native_wallet(
        self,
        wallet_type: WalletType,
        wallet_address: str,
        chain_id: int,
        is_hardware: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Connect native mobile wallet.

        Args:
            wallet_type: Type of wallet
            wallet_address: Wallet address
            chain_id: Chain ID
            is_hardware: Whether connected via hardware wallet

        Returns:
            Tuple of (success, connection info)
        """
        connection_id = f"WALLET-{secrets.token_hex(8).upper()}"

        connection = WalletConnection(
            connection_id=connection_id,
            wallet_type=wallet_type,
            wallet_address=wallet_address,
            chain_id=chain_id,
            connected_at=datetime.utcnow().isoformat(),
            is_hardware=is_hardware,
            permissions=["eth_sendTransaction", "personal_sign"],
            expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat()
        )

        self.connections[connection_id] = connection

        return True, {
            "connection_id": connection_id,
            "wallet_type": wallet_type.value,
            "wallet_address": wallet_address,
            "chain_id": chain_id,
            "is_hardware": is_hardware
        }

    def request_signature(
        self,
        connection_id: str,
        message: str,
        signature_type: str = "personal_sign"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Request signature from connected wallet.

        Args:
            connection_id: Wallet connection
            message: Message to sign
            signature_type: Type of signature

        Returns:
            Tuple of (success, signature request)
        """
        if connection_id not in self.connections:
            return False, {"error": "Wallet not connected"}

        connection = self.connections[connection_id]

        if signature_type not in connection.permissions:
            return False, {"error": f"Permission not granted for {signature_type}"}

        request_id = f"SIG-{secrets.token_hex(6).upper()}"

        # In production, this would trigger wallet popup
        request = {
            "request_id": request_id,
            "connection_id": connection_id,
            "wallet_address": connection.wallet_address,
            "message": message,
            "signature_type": signature_type,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        self.pending_requests[request_id] = request

        return True, request

    def submit_signature(
        self,
        request_id: str,
        signature: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit signature response.

        Args:
            request_id: Signature request ID
            signature: The signature

        Returns:
            Tuple of (success, result)
        """
        if request_id not in self.pending_requests:
            return False, {"error": "Request not found"}

        request = self.pending_requests[request_id]

        # Validate signature format (basic check)
        if not signature.startswith("0x") or len(signature) < 130:
            return False, {"error": "Invalid signature format"}

        result = {
            "request_id": request_id,
            "signature": signature,
            "signer": request["wallet_address"],
            "message": request["message"],
            "signed_at": datetime.utcnow().isoformat()
        }

        del self.pending_requests[request_id]

        return True, result

    def request_transaction(
        self,
        connection_id: str,
        to_address: str,
        value: str,
        data: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Request transaction signing.

        Args:
            connection_id: Wallet connection
            to_address: Recipient address
            value: Transaction value (wei)
            data: Transaction data (optional)

        Returns:
            Tuple of (success, transaction request)
        """
        if connection_id not in self.connections:
            return False, {"error": "Wallet not connected"}

        connection = self.connections[connection_id]

        request_id = f"TX-{secrets.token_hex(6).upper()}"

        request = {
            "request_id": request_id,
            "connection_id": connection_id,
            "from": connection.wallet_address,
            "to": to_address,
            "value": value,
            "data": data or "0x",
            "chain_id": connection.chain_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        self.pending_requests[request_id] = request

        return True, request

    def submit_transaction(
        self,
        request_id: str,
        tx_hash: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit transaction hash after signing.

        Args:
            request_id: Transaction request ID
            tx_hash: Transaction hash

        Returns:
            Tuple of (success, result)
        """
        if request_id not in self.pending_requests:
            return False, {"error": "Request not found"}

        request = self.pending_requests[request_id]

        result = {
            "request_id": request_id,
            "tx_hash": tx_hash,
            "from": request["from"],
            "to": request["to"],
            "value": request["value"],
            "chain_id": request["chain_id"],
            "submitted_at": datetime.utcnow().isoformat()
        }

        self.transaction_history.append(result)
        del self.pending_requests[request_id]

        return True, result

    def disconnect_wallet(self, connection_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Disconnect a wallet."""
        if connection_id not in self.connections:
            return False, {"error": "Connection not found"}

        connection = self.connections[connection_id]
        del self.connections[connection_id]

        # Clean up session topic
        if connection.session_topic and connection.session_topic in self.session_topics:
            del self.session_topics[connection.session_topic]

        return True, {
            "disconnected": True,
            "connection_id": connection_id,
            "wallet_address": connection.wallet_address
        }

    def get_connected_wallets(self) -> List[Dict[str, Any]]:
        """Get all connected wallets."""
        return [
            {
                "connection_id": c.connection_id,
                "wallet_type": c.wallet_type.value,
                "wallet_address": c.wallet_address,
                "chain_id": c.chain_id,
                "is_hardware": c.is_hardware,
                "connected_at": c.connected_at
            }
            for c in self.connections.values()
        ]


# ============================================================
# Offline-First System
# ============================================================

class OfflineFirstManager:
    """
    Offline-first data management.

    Features:
    - Local state persistence
    - Sync queue management
    - Conflict resolution
    - Background sync
    """

    def __init__(self):
        """Initialize offline-first manager."""
        self.local_state: Dict[str, LocalState] = {}
        self.local_states: Dict[str, Dict[str, Any]] = {}  # Per-device states
        self.sync_queue: Dict[str, List[SyncOperation]] = {}  # Per-device queues
        self.conflicts: Dict[str, List[SyncConflict]] = {}  # Per-device conflicts
        self.connection_state = ConnectionState.ONLINE
        self.last_sync: Optional[str] = None
        self.conflict_handlers: Dict[str, Callable] = {}
        self.sync_in_progress = False

    def set_connection_state(self, state: ConnectionState):
        """Update connection state."""
        old_state = self.connection_state
        self.connection_state = state

        # Trigger sync when coming online
        if old_state == ConnectionState.OFFLINE and state == ConnectionState.ONLINE:
            self._trigger_sync()

    def save_local(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Save data locally.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            data: Data to save

        Returns:
            Tuple of (success, state info)
        """
        state_id = f"{entity_type}:{entity_id}"

        # Get existing state
        existing = self.local_state.get(state_id)
        version = (existing.version + 1) if existing else 1

        state = LocalState(
            state_id=state_id,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data,
            version=version,
            last_modified=datetime.utcnow().isoformat(),
            is_dirty=True,
            sync_status=SyncStatus.PENDING
        )

        self.local_state[state_id] = state

        # Queue sync operation
        self._queue_sync_operation(
            operation_type="save",
            data={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "data": data,
                "version": version
            }
        )

        return True, {
            "state_id": state_id,
            "version": version,
            "is_dirty": True,
            "sync_status": state.sync_status.value
        }

    def get_local(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get data from local storage.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier

        Returns:
            Local data or None
        """
        state_id = f"{entity_type}:{entity_id}"
        state = self.local_state.get(state_id)

        if not state:
            return None

        return {
            "entity_type": state.entity_type,
            "entity_id": state.entity_id,
            "data": state.data,
            "version": state.version,
            "last_modified": state.last_modified,
            "is_dirty": state.is_dirty,
            "sync_status": state.sync_status.value
        }

    def delete_local(
        self,
        entity_type: str,
        entity_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete data locally.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier

        Returns:
            Tuple of (success, result)
        """
        state_id = f"{entity_type}:{entity_id}"

        if state_id not in self.local_state:
            return False, {"error": "Entity not found"}

        del self.local_state[state_id]

        # Queue sync operation
        self._queue_sync_operation(
            operation_type="delete",
            data={
                "entity_type": entity_type,
                "entity_id": entity_id
            }
        )

        return True, {"deleted": state_id}

    def _queue_sync_operation(
        self,
        operation_type: str,
        data: Dict[str, Any]
    ):
        """Queue a sync operation."""
        operation = SyncOperation(
            operation_id=f"SYNC-{secrets.token_hex(6).upper()}",
            operation_type=operation_type,
            data=data,
            status=SyncStatus.PENDING,
            created_at=datetime.utcnow().isoformat()
        )

        self.sync_queue.append(operation)

        # Try to sync if online
        if self.connection_state == ConnectionState.ONLINE:
            self._trigger_sync()

    def _trigger_sync(self):
        """Trigger sync process."""
        if self.sync_in_progress:
            return

        if not self.sync_queue:
            return

        self.sync_in_progress = True
        self.connection_state = ConnectionState.SYNCING

        # Process sync queue
        synced = []
        for operation in self.sync_queue:
            if operation.status == SyncStatus.PENDING:
                # Simulate sync
                operation.status = SyncStatus.SYNCED
                operation.synced_at = datetime.utcnow().isoformat()
                synced.append(operation)

                # Update local state
                if operation.operation_type == "save":
                    state_id = f"{operation.data['entity_type']}:{operation.data['entity_id']}"
                    if state_id in self.local_state:
                        self.local_state[state_id].is_dirty = False
                        self.local_state[state_id].sync_status = SyncStatus.SYNCED

        # Remove synced operations
        self.sync_queue = [op for op in self.sync_queue if op.status != SyncStatus.SYNCED]

        self.last_sync = datetime.utcnow().isoformat()
        self.sync_in_progress = False
        self.connection_state = ConnectionState.ONLINE

    def resolve_conflict(
        self,
        state_id: str,
        resolution: str,
        merged_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Resolve a sync conflict.

        Args:
            state_id: State with conflict
            resolution: "local", "remote", or "merge"
            merged_data: Data if resolution is "merge"

        Returns:
            Tuple of (success, result)
        """
        if state_id not in self.local_state:
            return False, {"error": "State not found"}

        state = self.local_state[state_id]

        if state.sync_status != SyncStatus.CONFLICT:
            return False, {"error": "No conflict to resolve"}

        if resolution == "local":
            # Keep local data, re-queue sync
            state.sync_status = SyncStatus.PENDING
            self._queue_sync_operation(
                operation_type="save",
                data={
                    "entity_type": state.entity_type,
                    "entity_id": state.entity_id,
                    "data": state.data,
                    "version": state.version,
                    "force": True
                }
            )
        elif resolution == "remote":
            # Accept remote data (would fetch from server)
            state.sync_status = SyncStatus.SYNCED
            state.is_dirty = False
        elif resolution == "merge" and merged_data:
            state.data = merged_data
            state.version += 1
            state.sync_status = SyncStatus.PENDING
            self._queue_sync_operation(
                operation_type="save",
                data={
                    "entity_type": state.entity_type,
                    "entity_id": state.entity_id,
                    "data": merged_data,
                    "version": state.version
                }
            )
        else:
            return False, {"error": "Invalid resolution"}

        return True, {
            "state_id": state_id,
            "resolution": resolution,
            "new_status": state.sync_status.value
        }

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        pending = sum(1 for op in self.sync_queue if op.status == SyncStatus.PENDING)
        conflicts = sum(1 for s in self.local_state.values() if s.sync_status == SyncStatus.CONFLICT)
        dirty = sum(1 for s in self.local_state.values() if s.is_dirty)

        return {
            "connection_state": self.connection_state.value,
            "last_sync": self.last_sync,
            "sync_in_progress": self.sync_in_progress,
            "pending_operations": pending,
            "conflicts": conflicts,
            "dirty_entities": dirty,
            "total_local_entities": len(self.local_state)
        }

    def get_pending_operations(self) -> List[Dict[str, Any]]:
        """Get pending sync operations."""
        return [
            {
                "operation_id": op.operation_id,
                "operation_type": op.operation_type,
                "status": op.status.value,
                "created_at": op.created_at,
                "retry_count": op.retry_count
            }
            for op in self.sync_queue
            if op.status == SyncStatus.PENDING
        ]


# ============================================================
# Portable System Architecture
# ============================================================

class PortableArchitecture:
    """
    Portable system architecture for cross-platform deployment.

    Features:
    - Lightweight API client
    - State management
    - Cross-platform compatibility
    - Resource optimization
    """

    def __init__(self):
        """Initialize portable architecture."""
        self.registered_devices: Dict[str, DeviceProfile] = {}
        self.device_states: Dict[str, Dict[str, Any]] = {}
        self.api_endpoints: Dict[str, str] = {}
        self.feature_flags: Dict[str, bool] = {
            "edge_ai": True,
            "wallet_connect": True,
            "offline_mode": True,
            "background_sync": True,
            "push_notifications": True,
            "biometric_auth": True
        }

    @property
    def devices(self) -> Dict[str, DeviceProfile]:
        """Alias for registered_devices."""
        return self.registered_devices

    def register_device(
        self,
        device_type: DeviceType,
        device_name: str = "Unknown Device",
        capabilities: Optional[Dict[str, Any]] = None,
        os_version: str = "1.0",
        app_version: str = "1.0",
        memory_mb: int = 2048,
        storage_mb: int = 1024,
        cpu_cores: int = 4,
        has_gpu: bool = False,
        has_npu: bool = False
    ) -> str:
        """
        Register a mobile device.

        Args:
            device_type: Type of device
            device_name: User-friendly device name
            capabilities: Device capabilities
            os_version: OS version
            app_version: App version
            memory_mb: Available memory
            storage_mb: Available storage
            cpu_cores: CPU cores
            has_gpu: GPU availability
            has_npu: NPU availability

        Returns:
            Device ID
        """
        device_id = f"DEVICE-{secrets.token_hex(8).upper()}"

        device = DeviceProfile(
            device_id=device_id,
            device_type=device_type,
            device_name=device_name,
            os_version=os_version,
            app_version=app_version,
            capabilities=capabilities or {},
            memory_mb=memory_mb,
            storage_mb=storage_mb,
            cpu_cores=cpu_cores,
            has_gpu=has_gpu,
            has_npu=has_npu
        )

        self.registered_devices[device_id] = device

        return device_id

    def register_device_full(
        self,
        device_type: DeviceType,
        os_version: str,
        app_version: str,
        capabilities: Dict[str, bool],
        memory_mb: int = 2048,
        storage_mb: int = 1024,
        cpu_cores: int = 4,
        has_gpu: bool = False,
        has_npu: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Register a mobile device with full response.

        Returns:
            Tuple of (success, device info)
        """
        device_id = self.register_device(
            device_type=device_type,
            capabilities=capabilities,
            os_version=os_version,
            app_version=app_version,
            memory_mb=memory_mb,
            storage_mb=storage_mb,
            cpu_cores=cpu_cores,
            has_gpu=has_gpu,
            has_npu=has_npu
        )

        device = self.registered_devices[device_id]

        # Determine available features
        available_features = self._get_available_features(device)

        return True, {
            "device_id": device_id,
            "device_type": device_type.value,
            "registered_at": device.registered_at.isoformat(),
            "available_features": available_features,
            "recommended_model_size": self._get_recommended_model_size(device)
        }

    def _get_available_features(self, device: DeviceProfile) -> List[str]:
        """Get available features for device."""
        features = []

        if self.feature_flags.get("edge_ai") and device.memory_mb >= 1024:
            features.append("edge_ai")

        if self.feature_flags.get("wallet_connect"):
            features.append("wallet_connect")

        if self.feature_flags.get("offline_mode"):
            features.append("offline_mode")

        if self.feature_flags.get("background_sync") and device.capabilities.get("background_tasks"):
            features.append("background_sync")

        if self.feature_flags.get("push_notifications") and device.capabilities.get("push"):
            features.append("push_notifications")

        if self.feature_flags.get("biometric_auth") and device.capabilities.get("biometric"):
            features.append("biometric_auth")

        return features

    def _get_recommended_model_size(self, device: DeviceProfile) -> str:
        """Get recommended model size for device."""
        if device.has_npu and device.memory_mb >= 4096:
            return ModelSize.MEDIUM.value
        elif device.memory_mb >= 2048:
            return ModelSize.SMALL.value
        elif device.memory_mb >= 1024:
            return ModelSize.MICRO.value
        else:
            return ModelSize.NANO.value

    def update_device_state(
        self,
        device_id: str,
        state: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Update device state."""
        if device_id not in self.registered_devices:
            return False, {"error": "Device not registered"}

        self.device_states[device_id] = {
            **state,
            "updated_at": datetime.utcnow().isoformat()
        }

        # Update last seen
        self.registered_devices[device_id].last_seen = datetime.utcnow().isoformat()

        return True, {"device_id": device_id, "state_updated": True}

    def get_device_config(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for device."""
        if device_id not in self.registered_devices:
            return None

        device = self.registered_devices[device_id]

        return {
            "device_id": device_id,
            "device_type": device.device_type.value,
            "features": self._get_available_features(device),
            "model_size": self._get_recommended_model_size(device),
            "api_endpoints": self.api_endpoints,
            "feature_flags": self.feature_flags,
            "sync_interval_seconds": 30 if device.battery_optimization else 10,
            "cache_size_mb": min(device.storage_mb // 10, 100)
        }

    def set_api_endpoints(self, endpoints: Dict[str, str]):
        """Set API endpoints for mobile clients."""
        self.api_endpoints = endpoints

    def set_feature_flag(self, flag: str, enabled: bool):
        """Set a feature flag."""
        self.feature_flags[flag] = enabled

    def get_registered_devices(self) -> List[Dict[str, Any]]:
        """Get all registered devices."""
        return [
            {
                "device_id": d.device_id,
                "device_type": d.device_type.value,
                "os_version": d.os_version,
                "app_version": d.app_version,
                "last_seen": d.last_seen
            }
            for d in self.registered_devices.values()
        ]


# ============================================================
# Main Mobile Deployment Manager
# ============================================================

class MobileDeploymentManager:
    """
    Main manager for mobile deployment.

    Coordinates edge AI, wallet, offline, and portable components.
    """

    def __init__(self):
        """Initialize mobile deployment manager."""
        self.edge_ai = EdgeAIRuntime()
        self.wallet_manager = MobileWalletManager()
        self.offline_manager = OfflineFirstManager()
        self.portable = PortableArchitecture()

        self.audit_trail: List[Dict[str, Any]] = []

    # ===== Device Management =====

    def register_device(
        self,
        device_type: DeviceType,
        device_name: str = "Unknown Device",
        capabilities: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a mobile device.

        Args:
            device_type: Type of device
            device_name: User-friendly device name
            capabilities: Device capabilities

        Returns:
            Device ID
        """
        device_id = self.portable.register_device(
            device_type=device_type,
            device_name=device_name,
            capabilities=capabilities
        )

        self._log_audit("device_registered", {
            "device_id": device_id,
            "device_type": device_type.value,
            "device_name": device_name
        })

        return device_id

    def get_device_features(self, device_id: str) -> Optional[Dict[str, bool]]:
        """Get feature flags for a device."""
        if device_id not in self.portable.devices:
            return None

        device = self.portable.devices[device_id]
        features = dict(self.portable.feature_flags)

        # Adjust based on device capabilities
        if device.device_type == DeviceType.WEB:
            features["biometric_auth"] = False

        features["edge_ai_enabled"] = device.has_npu or device.has_gpu or device.memory_mb >= 2048

        return features

    def get_device_config(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device configuration."""
        return self.portable.get_device_config(device_id)

    # ===== Edge AI =====

    def load_edge_model(
        self,
        model_id: str,
        model_type: str = "generic",
        model_path: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> bool:
        """
        Load an edge AI model.

        Args:
            model_id: Unique model identifier
            model_type: Type of model
            model_path: Path to model file
            device_id: Device to load on

        Returns:
            True if loaded successfully
        """
        # Get device or use default profile
        if device_id and device_id in self.portable.devices:
            device = self.portable.devices[device_id]
        else:
            device = DeviceProfile(
                device_id="default",
                device_type=DeviceType.WEB,
                memory_mb=2048
            )

        model_size = self.edge_ai.get_optimal_model_size(device)

        success, _ = self.edge_ai.load_model(
            model_id=model_id,
            size=model_size,
            device=device,
            model_type=model_type,
            model_path=model_path
        )

        if success:
            self._log_audit("model_loaded", {
                "model_id": model_id,
                "model_type": model_type,
                "device_id": device_id
            })

        return success

    def run_inference(
        self,
        model_id: str,
        input_data: Any,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run inference on a loaded model.

        Args:
            model_id: Model to use
            input_data: Input data (can be dict with 'text' key or string)
            device_id: Device to run on

        Returns:
            Inference result
        """
        # Extract text from input
        if isinstance(input_data, dict):
            input_text = input_data.get("text", str(input_data))
        else:
            input_text = str(input_data)

        success, result = self.edge_ai.run_inference(model_id, input_text)

        if success:
            return {
                "success": True,
                "result": {
                    "output": result.get("output", ""),
                    "confidence": 0.85,  # Simulated
                    "latency_ms": result.get("latency_ms", 100),
                    "on_device": result.get("on_device", True)
                }
            }
        else:
            return {"success": False, "error": result.get("error", "Inference failed")}

    def run_edge_inference(
        self,
        model_id: str,
        input_text: str,
        max_tokens: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Run edge AI inference (legacy method)."""
        return self.edge_ai.run_inference(model_id, input_text, max_tokens)

    def get_edge_resource_usage(self) -> Dict[str, Any]:
        """Get edge AI resource usage."""
        return self.edge_ai.get_resource_usage()

    # ===== Wallet (Convenience Methods) =====

    def connect_wallet(
        self,
        wallet_type: WalletType,
        device_id: Optional[str] = None,
        wallet_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Connect a mobile wallet.

        Args:
            wallet_type: Type of wallet
            device_id: Device connecting
            wallet_address: Wallet address

        Returns:
            Connection ID or None on failure
        """
        connection_id = secrets.token_hex(16)

        connection = WalletConnection(
            connection_id=connection_id,
            wallet_type=wallet_type,
            wallet_address=wallet_address or f"0x{secrets.token_hex(20)}",
            chain_id=1,
            connected_at=datetime.utcnow(),
            state=ConnectionState.CONNECTED,
            device_id=device_id,
            is_hardware=wallet_type == WalletType.HARDWARE
        )

        self.wallet_manager.connections[connection_id] = connection

        self._log_audit("wallet_connected", {
            "connection_id": connection_id,
            "wallet_type": wallet_type.value,
            "device_id": device_id
        })

        return connection_id

    def disconnect_wallet(self, connection_id: str) -> bool:
        """Disconnect a wallet."""
        if connection_id not in self.wallet_manager.connections:
            return False

        conn = self.wallet_manager.connections[connection_id]
        conn.state = ConnectionState.DISCONNECTED

        self._log_audit("wallet_disconnected", {
            "connection_id": connection_id
        })

        return True

    def sign_message(
        self,
        connection_id: str,
        message: str,
        sign_type: str = "personal"
    ) -> Dict[str, Any]:
        """
        Sign a message with connected wallet.

        Args:
            connection_id: Wallet connection ID
            message: Message to sign
            sign_type: Type of signature

        Returns:
            Signature result
        """
        if connection_id not in self.wallet_manager.connections:
            return {"success": False, "error": "Connection not found"}

        conn = self.wallet_manager.connections[connection_id]

        # Simulate signature
        signature = "0x" + hashlib.sha256(
            f"{message}:{conn.wallet_address}:{sign_type}".encode()
        ).hexdigest()

        conn.signature_count += 1

        self._log_audit("message_signed", {
            "connection_id": connection_id,
            "sign_type": sign_type
        })

        return {
            "success": True,
            "signature": signature,
            "sign_type": sign_type,
            "wallet_address": conn.wallet_address
        }

    def initiate_wallet_connect(
        self,
        device_id: str,
        chains: Optional[List[int]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Initiate WalletConnect session."""
        return self.wallet_manager.initiate_wallet_connect(device_id, chains)

    def complete_wallet_connect(
        self,
        connection_id: str,
        wallet_address: str,
        chain_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Complete WalletConnect handshake."""
        success, result = self.wallet_manager.complete_wallet_connect(
            connection_id, wallet_address, chain_id
        )

        if success:
            self._log_audit("wallet_connected", {
                "connection_id": connection_id,
                "wallet_address": wallet_address
            })

        return success, result

    def connect_native_wallet(
        self,
        wallet_type: str,
        wallet_address: str,
        chain_id: int,
        is_hardware: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Connect native wallet."""
        try:
            wt = WalletType(wallet_type)
        except ValueError:
            wt = WalletType.NATIVE

        return self.wallet_manager.connect_native_wallet(
            wt, wallet_address, chain_id, is_hardware
        )

    def request_signature(
        self,
        connection_id: str,
        message: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Request signature from wallet."""
        return self.wallet_manager.request_signature(connection_id, message)

    def request_transaction(
        self,
        connection_id: str,
        to_address: str,
        value: str,
        data: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Request transaction signing."""
        return self.wallet_manager.request_transaction(
            connection_id, to_address, value, data
        )

    def get_connected_wallets(self) -> List[Dict[str, Any]]:
        """Get connected wallets."""
        return self.wallet_manager.get_connected_wallets()

    # ===== Offline (Convenience Methods) =====

    def save_offline_state(
        self,
        device_id: str,
        state_type: str,
        state_data: Dict[str, Any]
    ) -> str:
        """
        Save state for offline access.

        Args:
            device_id: Device to save for
            state_type: Type of state
            state_data: State data

        Returns:
            State ID
        """
        state_id = f"STATE-{secrets.token_hex(8)}"

        # Store in offline manager
        if device_id not in self.offline_manager.local_states:
            self.offline_manager.local_states[device_id] = {}

        self.offline_manager.local_states[device_id][state_type] = {
            "state_id": state_id,
            "data": state_data,
            "saved_at": datetime.utcnow().isoformat()
        }

        self._log_audit("offline_state_saved", {
            "device_id": device_id,
            "state_type": state_type,
            "state_id": state_id
        })

        return state_id

    def get_offline_state(
        self,
        device_id: str,
        state_type: Optional[str] = None
    ) -> Any:
        """
        Get offline state for a device.

        Args:
            device_id: Device ID
            state_type: Optional specific state type

        Returns:
            State data or all states
        """
        if device_id not in self.offline_manager.local_states:
            return None if state_type else {}

        states = self.offline_manager.local_states[device_id]

        if state_type:
            return states.get(state_type)
        return states

    def queue_offline_operation(
        self,
        device_id: str,
        operation_type: str,
        resource_type: str,
        resource_data: Dict[str, Any]
    ) -> str:
        """
        Add an operation to the offline sync queue.

        Args:
            device_id: Device adding the operation
            operation_type: Type of operation
            resource_type: Type of resource
            resource_data: Operation data

        Returns:
            Operation ID
        """
        operation_id = f"OP-{secrets.token_hex(8)}"

        operation = SyncOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            data={
                "device_id": device_id,
                "resource_type": resource_type,
                "resource_data": resource_data
            },
            status=SyncStatus.PENDING,
            created_at=datetime.utcnow().isoformat()
        )

        if device_id not in self.offline_manager.sync_queue:
            self.offline_manager.sync_queue[device_id] = []

        self.offline_manager.sync_queue[device_id].append(operation)

        return operation_id

    def sync_device(
        self,
        device_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize device with server.

        Args:
            device_id: Device to sync
            force: Force sync even with conflicts

        Returns:
            Sync result
        """
        queue = self.offline_manager.sync_queue.get(device_id, [])
        synced_count = len(queue)

        # Clear queue (simulate sync)
        self.offline_manager.sync_queue[device_id] = []

        # Update device last sync
        if device_id in self.portable.devices:
            self.portable.devices[device_id].last_sync = datetime.utcnow()

        self._log_audit("device_synced", {
            "device_id": device_id,
            "synced_count": synced_count,
            "forced": force
        })

        return {
            "success": True,
            "synced_count": synced_count,
            "conflicts": 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_sync_queue(self, device_id: str) -> List[Dict[str, Any]]:
        """Get pending sync operations for a device."""
        queue = self.offline_manager.sync_queue.get(device_id, [])
        return [
            {
                "operation_id": op.operation_id,
                "operation_type": op.operation_type,
                "status": op.status.value,
                "created_at": op.created_at
            }
            for op in queue
        ]

    def get_conflicts(self, device_id: str) -> List[Dict[str, Any]]:
        """Get sync conflicts for a device."""
        conflicts = self.offline_manager.conflicts.get(device_id, [])
        return [
            {
                "conflict_id": c.conflict_id,
                "resource_type": c.resource_type,
                "resource_id": c.resource_id,
                "conflict_type": c.conflict_type,
                "detected_at": c.detected_at.isoformat()
            }
            for c in conflicts if not c.resolved
        ]

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        merged_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Resolve a sync conflict.

        Args:
            conflict_id: Conflict to resolve
            resolution: Resolution strategy
            merged_data: Merged data if using merge

        Returns:
            True if resolved
        """
        for device_id, conflicts in self.offline_manager.conflicts.items():
            for conflict in conflicts:
                if conflict.conflict_id == conflict_id:
                    conflict.resolved = True
                    conflict.resolution = resolution
                    self._log_audit("conflict_resolved", {
                        "conflict_id": conflict_id,
                        "resolution": resolution
                    })
                    return True
        return False

    def set_connection_state(self, state: str):
        """Set connection state."""
        try:
            cs = ConnectionState(state)
        except ValueError:
            cs = ConnectionState.ONLINE

        self.offline_manager.set_connection_state(cs)

    def save_offline(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Save data for offline use."""
        return self.offline_manager.save_local(entity_type, entity_id, data)

    def get_offline(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get offline data."""
        return self.offline_manager.get_local(entity_type, entity_id)

    def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status."""
        return self.offline_manager.get_sync_status()

    def resolve_sync_conflict(
        self,
        state_id: str,
        resolution: str,
        merged_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Resolve sync conflict."""
        return self.offline_manager.resolve_conflict(state_id, resolution, merged_data)

    # ===== Statistics =====

    def get_statistics(self) -> Dict[str, Any]:
        """Get mobile deployment statistics."""
        total_synced = sum(
            len(self.offline_manager.sync_queue.get(d, []))
            for d in self.portable.devices
        )

        return {
            "devices": {
                "total": len(self.portable.registered_devices),
                "by_type": {}
            },
            "edge_ai": self.edge_ai.get_statistics(),
            "wallets": {
                "total_connections": len(self.wallet_manager.connections),
                "active": sum(1 for c in self.wallet_manager.connections.values()
                             if c.state == ConnectionState.ONLINE)
            },
            "offline": {
                "pending_operations": total_synced,
                "operations_synced": len(self.audit_trail)
            },
            "feature_flags": self.portable.feature_flags
        }

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail."""
        return self.audit_trail[-limit:]

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
