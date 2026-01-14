"""
NatLangChain - Compute-to-Data Layer

Privacy-preserving contract analysis system inspired by Ocean Protocol.
Enables computation on private data without exposing the underlying content.

Key Concepts:
- Data stays with the owner, computation moves to the data
- Algorithms run in sandboxed environments
- Only aggregated/anonymized results are returned
- Access control through cryptographic permissions

Use Cases:
- Analyze private contracts without revealing content
- Statistical queries across confidential entries
- Third-party verification without data exposure
- Privacy-preserving contract matching

Architecture:
1. Data owners register assets with access policies
2. Compute providers submit approved algorithms
3. Jobs execute in isolated environments
4. Results are filtered/aggregated before return
"""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Compute configuration
MAX_COMPUTE_TIME_SECONDS = 300  # 5 minute max per job
MAX_RESULT_SIZE_BYTES = 1024 * 1024  # 1MB max result
DEFAULT_PRIVACY_THRESHOLD = 5  # Min records for aggregation

# Access token configuration
ACCESS_TOKEN_EXPIRY_HOURS = 24
MAX_COMPUTE_USES_PER_TOKEN = 100


# =============================================================================
# Enums
# =============================================================================


class DataAssetType(Enum):
    """Types of data assets."""

    CONTRACT = "contract"
    ENTRY = "entry"
    ENTRY_SET = "entry_set"
    DISPUTE = "dispute"
    SETTLEMENT = "settlement"
    CUSTOM = "custom"


class ComputeAlgorithmType(Enum):
    """Types of compute algorithms."""

    STATISTICAL = "statistical"  # Aggregations, counts, averages
    CLASSIFICATION = "classification"  # Categorization
    MATCHING = "matching"  # Find compatible items
    VERIFICATION = "verification"  # Validate claims
    EXTRACTION = "extraction"  # Extract specific fields
    ANALYSIS = "analysis"  # General analysis
    CUSTOM = "custom"


class AccessLevel(Enum):
    """Access levels for data assets."""

    NONE = "none"
    METADATA_ONLY = "metadata_only"  # Can see metadata, not content
    AGGREGATE_ONLY = "aggregate_only"  # Can run aggregations only
    COMPUTE_ONLY = "compute_only"  # Can run approved algorithms
    FULL_COMPUTE = "full_compute"  # Can run any algorithm
    FULL_ACCESS = "full_access"  # Can access raw data


class JobStatus(Enum):
    """Status of compute jobs."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class PrivacyLevel(Enum):
    """Privacy levels for results."""

    RAW = "raw"  # No privacy filtering
    ANONYMIZED = "anonymized"  # Personal info removed
    AGGREGATED = "aggregated"  # Only aggregated results
    DIFFERENTIAL = "differential"  # Differential privacy applied


class ComputeEventType(Enum):
    """Types of compute events."""

    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_REVOKED = "asset_revoked"
    ALGORITHM_REGISTERED = "algorithm_registered"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REVOKED = "access_revoked"
    JOB_SUBMITTED = "job_submitted"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    RESULT_RETRIEVED = "result_retrieved"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DataAsset:
    """A registered data asset for compute operations."""

    asset_id: str
    asset_type: DataAssetType
    owner: str  # DID of owner
    name: str
    description: str | None = None
    # Content reference (not the actual content)
    content_hash: str | None = None
    entry_refs: list[dict[str, int]] | None = None  # [{block_index, entry_index}]
    # Access control
    allowed_algorithms: list[str] = field(default_factory=list)  # Algorithm IDs
    allowed_compute_providers: list[str] = field(default_factory=list)  # DIDs
    privacy_level: PrivacyLevel = PrivacyLevel.AGGREGATED
    min_aggregation_size: int = DEFAULT_PRIVACY_THRESHOLD
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding sensitive content)."""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "owner": self.owner,
            "name": self.name,
            "description": self.description,
            "content_hash": self.content_hash,
            "entry_count": len(self.entry_refs) if self.entry_refs else 0,
            "allowed_algorithms": self.allowed_algorithms,
            "allowed_compute_providers": self.allowed_compute_providers,
            "privacy_level": self.privacy_level.value,
            "min_aggregation_size": self.min_aggregation_size,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }


@dataclass
class ComputeAlgorithm:
    """A registered compute algorithm."""

    algorithm_id: str
    algorithm_type: ComputeAlgorithmType
    name: str
    description: str | None = None
    author: str | None = None  # DID of author
    # Code/logic reference
    code_hash: str | None = None
    version: str = "1.0"
    # Input/output schema
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    # Privacy guarantees
    privacy_preserving: bool = True
    supports_differential_privacy: bool = False
    min_input_size: int = 1
    # Audit trail
    audited: bool = False
    audit_report: str | None = None
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "algorithm_id": self.algorithm_id,
            "algorithm_type": self.algorithm_type.value,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "code_hash": self.code_hash,
            "version": self.version,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "privacy_preserving": self.privacy_preserving,
            "supports_differential_privacy": self.supports_differential_privacy,
            "min_input_size": self.min_input_size,
            "audited": self.audited,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


@dataclass
class AccessToken:
    """Access token for compute operations."""

    token_id: str
    asset_id: str
    grantee: str  # DID granted access
    access_level: AccessLevel
    allowed_algorithms: list[str] = field(default_factory=list)
    max_uses: int = MAX_COMPUTE_USES_PER_TOKEN
    uses_remaining: int = MAX_COMPUTE_USES_PER_TOKEN
    expires_at: str = field(
        default_factory=lambda: (datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS)).isoformat()
    )
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    revoked: bool = False

    def is_valid(self) -> bool:
        """Check if token is valid."""
        if self.revoked:
            return False
        if self.uses_remaining <= 0:
            return False
        if datetime.fromisoformat(self.expires_at) < datetime.utcnow():
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "token_id": self.token_id,
            "asset_id": self.asset_id,
            "grantee": self.grantee,
            "access_level": self.access_level.value,
            "allowed_algorithms": self.allowed_algorithms,
            "max_uses": self.max_uses,
            "uses_remaining": self.uses_remaining,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "revoked": self.revoked,
            "valid": self.is_valid(),
        }


@dataclass
class ComputeJob:
    """A compute job to be executed."""

    job_id: str
    asset_id: str
    algorithm_id: str
    requester: str  # DID of requester
    access_token_id: str
    # Job configuration
    parameters: dict[str, Any] = field(default_factory=dict)
    privacy_level: PrivacyLevel = PrivacyLevel.AGGREGATED
    # Status tracking
    status: JobStatus = JobStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    # Results
    result: dict[str, Any] | None = None
    result_hash: str | None = None
    error_message: str | None = None
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    compute_time_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "asset_id": self.asset_id,
            "algorithm_id": self.algorithm_id,
            "requester": self.requester,
            "access_token_id": self.access_token_id,
            "parameters": self.parameters,
            "privacy_level": self.privacy_level.value,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_hash": self.result_hash,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "compute_time_ms": self.compute_time_ms,
        }


@dataclass
class ComputeResult:
    """Result from a compute job."""

    result_id: str
    job_id: str
    asset_id: str
    algorithm_id: str
    requester: str
    # Result data
    data: dict[str, Any]
    privacy_level: PrivacyLevel
    record_count: int  # Number of records processed
    # Verification
    result_hash: str
    signature: str | None = None
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result_id": self.result_id,
            "job_id": self.job_id,
            "asset_id": self.asset_id,
            "algorithm_id": self.algorithm_id,
            "requester": self.requester,
            "data": self.data,
            "privacy_level": self.privacy_level.value,
            "record_count": self.record_count,
            "result_hash": self.result_hash,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class ComputeEvent:
    """Event in compute system."""

    event_id: str
    event_type: ComputeEventType
    timestamp: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }


# =============================================================================
# Built-in Algorithms
# =============================================================================


class BuiltInAlgorithms:
    """Collection of built-in privacy-preserving algorithms."""

    @staticmethod
    def count(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Count records matching criteria."""
        field_name = params.get("field")
        value = params.get("value")

        if field_name and value is not None:
            count = sum(1 for d in data if d.get(field_name) == value)
        else:
            count = len(data)

        return {"count": count, "algorithm": "count"}

    @staticmethod
    def aggregate(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Aggregate numeric field."""
        field_name = params.get("field")
        operation = params.get("operation", "sum")

        if not field_name:
            return {"error": "field parameter required"}

        values = [d.get(field_name) for d in data if isinstance(d.get(field_name), int | float)]

        if not values:
            return {"result": None, "count": 0}

        if operation == "sum":
            result = sum(values)
        elif operation == "avg":
            result = sum(values) / len(values)
        elif operation == "min":
            result = min(values)
        elif operation == "max":
            result = max(values)
        elif operation == "median":
            sorted_vals = sorted(values)
            mid = len(sorted_vals) // 2
            result = sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        else:
            return {"error": f"Unknown operation: {operation}"}

        return {"result": result, "operation": operation, "count": len(values)}

    @staticmethod
    def distribution(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Get distribution of field values."""
        field_name = params.get("field")
        if not field_name:
            return {"error": "field parameter required"}

        distribution: dict[Any, int] = {}
        for record in data:
            value = record.get(field_name)
            if value is not None:
                key = str(value)
                distribution[key] = distribution.get(key, 0) + 1

        return {"distribution": distribution, "total": len(data), "unique_values": len(distribution)}

    @staticmethod
    def exists(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Check if records matching criteria exist (without revealing count)."""
        field_name = params.get("field")
        value = params.get("value")

        if field_name and value is not None:
            exists = any(d.get(field_name) == value for d in data)
        else:
            exists = len(data) > 0

        return {"exists": exists}

    @staticmethod
    def schema_analysis(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Analyze data schema without revealing content."""
        if not data:
            return {"fields": [], "record_count": 0}

        # Get all unique fields
        all_fields: set[str] = set()
        for record in data:
            all_fields.update(record.keys())

        # Analyze each field
        field_info = {}
        for field_name in all_fields:
            values = [r.get(field_name) for r in data if field_name in r]
            types = set(type(v).__name__ for v in values if v is not None)

            field_info[field_name] = {
                "present_count": len(values),
                "null_count": sum(1 for v in values if v is None),
                "types": list(types),
            }

        return {
            "fields": list(all_fields),
            "field_info": field_info,
            "record_count": len(data),
        }

    @staticmethod
    def keyword_presence(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Check presence of keywords without revealing content."""
        keywords = params.get("keywords", [])
        field_name = params.get("field", "content")

        if not keywords:
            return {"error": "keywords parameter required"}

        results = {}
        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = sum(1 for d in data if keyword_lower in str(d.get(field_name, "")).lower())
            results[keyword] = {"present": count > 0, "approximate_count": "few" if count < 5 else "some" if count < 20 else "many"}

        return {"keyword_analysis": results, "total_records": len(data)}

    @staticmethod
    def similarity_buckets(data: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
        """Group records into similarity buckets without revealing specifics."""
        field_name = params.get("field", "content")
        bucket_count = params.get("buckets", 5)

        # Simple length-based bucketing as proxy for similarity
        lengths = [len(str(d.get(field_name, ""))) for d in data]

        if not lengths:
            return {"buckets": [], "total": 0}

        min_len = min(lengths)
        max_len = max(lengths)
        bucket_size = (max_len - min_len + 1) / bucket_count if max_len > min_len else 1

        buckets = [0] * bucket_count
        for length in lengths:
            bucket_idx = min(int((length - min_len) / bucket_size), bucket_count - 1)
            buckets[bucket_idx] += 1

        return {
            "bucket_counts": buckets,
            "bucket_count": bucket_count,
            "total": len(data),
            "note": "Buckets represent content length distribution",
        }


# =============================================================================
# Privacy Filter
# =============================================================================


class PrivacyFilter:
    """Filters results based on privacy requirements."""

    def __init__(self, min_aggregation_size: int = DEFAULT_PRIVACY_THRESHOLD):
        self.min_aggregation_size = min_aggregation_size

    def apply(
        self,
        result: dict[str, Any],
        privacy_level: PrivacyLevel,
        record_count: int,
    ) -> dict[str, Any]:
        """
        Apply privacy filtering to result.

        Args:
            result: Raw result data
            privacy_level: Required privacy level
            record_count: Number of records processed

        Returns:
            Filtered result
        """
        if privacy_level == PrivacyLevel.RAW:
            return result

        filtered = dict(result)

        # Check aggregation threshold
        if record_count < self.min_aggregation_size:
            return {
                "error": "insufficient_data",
                "message": f"Minimum {self.min_aggregation_size} records required for privacy protection",
                "record_count": record_count,
            }

        if privacy_level == PrivacyLevel.ANONYMIZED:
            filtered = self._anonymize(filtered)

        elif privacy_level == PrivacyLevel.AGGREGATED:
            filtered = self._aggregate_only(filtered)

        elif privacy_level == PrivacyLevel.DIFFERENTIAL:
            filtered = self._add_differential_privacy(filtered, record_count)

        return filtered

    def _anonymize(self, result: dict[str, Any]) -> dict[str, Any]:
        """Remove potentially identifying information."""
        sensitive_fields = ["author", "party", "name", "email", "address", "id", "did"]
        return self._remove_fields(result, sensitive_fields)

    def _aggregate_only(self, result: dict[str, Any]) -> dict[str, Any]:
        """Keep only aggregate values."""
        aggregate_keys = ["count", "sum", "avg", "min", "max", "median", "total", "distribution", "buckets", "exists", "present"]
        return {k: v for k, v in result.items() if any(agg in k.lower() for agg in aggregate_keys) or k in ["error", "message", "algorithm", "operation"]}

    def _add_differential_privacy(self, result: dict[str, Any], record_count: int) -> dict[str, Any]:
        """Add noise for differential privacy."""
        import random

        noised = dict(result)

        # Add Laplacian noise to numeric values
        epsilon = 0.1  # Privacy parameter
        sensitivity = 1.0

        for key, value in noised.items():
            if isinstance(value, int | float):
                noise = random.gauss(0, sensitivity / epsilon)
                noised[key] = round(value + noise, 2)

        noised["differential_privacy"] = {
            "epsilon": epsilon,
            "noise_added": True,
        }

        return noised

    def _remove_fields(self, data: Any, fields: list[str]) -> Any:
        """Recursively remove sensitive fields."""
        if isinstance(data, dict):
            return {k: self._remove_fields(v, fields) for k, v in data.items() if not any(f in k.lower() for f in fields)}
        elif isinstance(data, list):
            return [self._remove_fields(item, fields) for item in data]
        return data


# =============================================================================
# Compute Environment
# =============================================================================


class ComputeEnvironment:
    """
    Sandboxed environment for executing compute jobs.

    In production, this would use containerization or secure enclaves.
    This is a simplified implementation for demonstration.
    """

    def __init__(self):
        self.algorithms: dict[str, Callable] = {}
        self._register_builtin_algorithms()

    def _register_builtin_algorithms(self) -> None:
        """Register built-in algorithms."""
        self.algorithms["builtin_count"] = BuiltInAlgorithms.count
        self.algorithms["builtin_aggregate"] = BuiltInAlgorithms.aggregate
        self.algorithms["builtin_distribution"] = BuiltInAlgorithms.distribution
        self.algorithms["builtin_exists"] = BuiltInAlgorithms.exists
        self.algorithms["builtin_schema_analysis"] = BuiltInAlgorithms.schema_analysis
        self.algorithms["builtin_keyword_presence"] = BuiltInAlgorithms.keyword_presence
        self.algorithms["builtin_similarity_buckets"] = BuiltInAlgorithms.similarity_buckets

    def execute(
        self,
        algorithm_id: str,
        data: list[dict[str, Any]],
        parameters: dict[str, Any],
        timeout_seconds: int = MAX_COMPUTE_TIME_SECONDS,
    ) -> tuple[bool, dict[str, Any], int]:
        """
        Execute an algorithm on data.

        Args:
            algorithm_id: Algorithm to execute
            data: Input data
            parameters: Algorithm parameters
            timeout_seconds: Execution timeout

        Returns:
            Tuple of (success, result, compute_time_ms)
        """
        import time

        start_time = time.time()

        # Input validation
        if not algorithm_id:
            return False, {"error": "Algorithm ID is required"}, 0

        if data is None:
            return False, {"error": "Data cannot be None"}, 0

        if not isinstance(data, list):
            return False, {"error": "Data must be a list"}, 0

        if parameters is None:
            parameters = {}

        try:
            if algorithm_id not in self.algorithms:
                return False, {"error": f"Algorithm {algorithm_id} not found"}, 0

            algorithm = self.algorithms[algorithm_id]

            # Validate algorithm is callable
            if not callable(algorithm):
                return False, {"error": f"Algorithm {algorithm_id} is not callable"}, 0

            result = algorithm(data, parameters)

            # Validate result is a dictionary
            if result is None:
                return False, {"error": "Algorithm returned None"}, int((time.time() - start_time) * 1000)

            if not isinstance(result, dict):
                return False, {"error": "Algorithm must return a dictionary"}, int((time.time() - start_time) * 1000)

            compute_time = int((time.time() - start_time) * 1000)
            return True, result, compute_time

        except TimeoutError:
            return False, {"error": "Computation timeout", "timeout_seconds": timeout_seconds}, int(timeout_seconds * 1000)
        except MemoryError:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": "Out of memory during computation"}, compute_time
        except RecursionError:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": "Maximum recursion depth exceeded"}, compute_time
        except TypeError as e:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": f"Type error in algorithm: {str(e)}"}, compute_time
        except KeyError as e:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": f"Missing required key: {str(e)}"}, compute_time
        except ValueError as e:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": f"Invalid value: {str(e)}"}, compute_time
        except Exception as e:
            compute_time = int((time.time() - start_time) * 1000)
            return False, {"error": f"Unexpected error: {str(e)}", "error_type": type(e).__name__}, compute_time


# =============================================================================
# Compute-to-Data Service
# =============================================================================


class ComputeToDataService:
    """
    Service for privacy-preserving computation on data.

    Allows running algorithms on private data without exposing
    the underlying content.
    """

    def __init__(self):
        self.assets: dict[str, DataAsset] = {}
        self.algorithms: dict[str, ComputeAlgorithm] = {}
        self.access_tokens: dict[str, AccessToken] = {}
        self.jobs: dict[str, ComputeJob] = {}
        self.results: dict[str, ComputeResult] = {}
        self.events: list[ComputeEvent] = []

        self.compute_env = ComputeEnvironment()
        self.privacy_filter = PrivacyFilter()

        # Data store (in production, this would be secure storage)
        self._data_store: dict[str, list[dict[str, Any]]] = {}

        # Register built-in algorithms
        self._register_builtin_algorithms()

    def _register_builtin_algorithms(self) -> None:
        """Register built-in algorithms."""
        builtins = [
            ("builtin_count", "Count", ComputeAlgorithmType.STATISTICAL, "Count records matching criteria"),
            ("builtin_aggregate", "Aggregate", ComputeAlgorithmType.STATISTICAL, "Aggregate numeric fields (sum, avg, min, max, median)"),
            ("builtin_distribution", "Distribution", ComputeAlgorithmType.STATISTICAL, "Get distribution of field values"),
            ("builtin_exists", "Exists", ComputeAlgorithmType.VERIFICATION, "Check if matching records exist"),
            ("builtin_schema_analysis", "Schema Analysis", ComputeAlgorithmType.ANALYSIS, "Analyze data schema without revealing content"),
            ("builtin_keyword_presence", "Keyword Presence", ComputeAlgorithmType.ANALYSIS, "Check keyword presence without revealing content"),
            ("builtin_similarity_buckets", "Similarity Buckets", ComputeAlgorithmType.ANALYSIS, "Group records by similarity buckets"),
        ]

        for alg_id, name, alg_type, description in builtins:
            self.algorithms[alg_id] = ComputeAlgorithm(
                algorithm_id=alg_id,
                algorithm_type=alg_type,
                name=name,
                description=description,
                author="system",
                privacy_preserving=True,
                audited=True,
            )

    # =========================================================================
    # Data Asset Management
    # =========================================================================

    def register_asset(
        self,
        asset_type: DataAssetType,
        owner: str,
        name: str,
        data: list[dict[str, Any]],
        description: str | None = None,
        entry_refs: list[dict[str, int]] | None = None,
        allowed_algorithms: list[str] | None = None,
        allowed_compute_providers: list[str] | None = None,
        privacy_level: PrivacyLevel = PrivacyLevel.AGGREGATED,
        min_aggregation_size: int = DEFAULT_PRIVACY_THRESHOLD,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Register a new data asset.

        Args:
            asset_type: Type of asset
            owner: Owner DID
            name: Asset name
            data: The actual data (stored securely)
            description: Optional description
            entry_refs: Optional entry references
            allowed_algorithms: Algorithms allowed on this data
            allowed_compute_providers: DIDs allowed to compute
            privacy_level: Minimum privacy level for results
            min_aggregation_size: Minimum records for aggregation
            metadata: Optional metadata

        Returns:
            Tuple of (success, asset_info)
        """
        asset_id = f"asset_{secrets.token_hex(12)}"

        # Hash the content
        content_str = str(data)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Default to all built-in algorithms if none specified
        if allowed_algorithms is None:
            allowed_algorithms = list(self.algorithms.keys())

        asset = DataAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            owner=owner,
            name=name,
            description=description,
            content_hash=content_hash,
            entry_refs=entry_refs,
            allowed_algorithms=allowed_algorithms,
            allowed_compute_providers=allowed_compute_providers or [],
            privacy_level=privacy_level,
            min_aggregation_size=min_aggregation_size,
            metadata=metadata or {},
        )

        self.assets[asset_id] = asset

        # Store data securely
        self._data_store[asset_id] = data

        # Emit event
        self._emit_event(
            ComputeEventType.ASSET_REGISTERED,
            {"asset_id": asset_id, "owner": owner, "record_count": len(data)},
        )

        return True, asset.to_dict()

    def get_asset(self, asset_id: str) -> DataAsset | None:
        """Get asset by ID."""
        return self.assets.get(asset_id)

    def update_asset(
        self,
        asset_id: str,
        owner: str,
        updates: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """Update an asset's configuration."""
        asset = self.assets.get(asset_id)
        if not asset:
            return False, {"error": "Asset not found"}

        if asset.owner != owner:
            return False, {"error": "Not authorized to update asset"}

        # Apply updates
        if "allowed_algorithms" in updates:
            asset.allowed_algorithms = updates["allowed_algorithms"]
        if "allowed_compute_providers" in updates:
            asset.allowed_compute_providers = updates["allowed_compute_providers"]
        if "privacy_level" in updates:
            asset.privacy_level = PrivacyLevel(updates["privacy_level"])
        if "min_aggregation_size" in updates:
            asset.min_aggregation_size = updates["min_aggregation_size"]
        if "metadata" in updates:
            asset.metadata = updates["metadata"]

        asset.updated_at = datetime.utcnow().isoformat()

        # Emit event
        self._emit_event(
            ComputeEventType.ASSET_UPDATED,
            {"asset_id": asset_id, "updates": list(updates.keys())},
        )

        return True, asset.to_dict()

    def revoke_asset(self, asset_id: str, owner: str) -> tuple[bool, dict[str, Any]]:
        """Revoke a data asset."""
        asset = self.assets.get(asset_id)
        if not asset:
            return False, {"error": "Asset not found"}

        if asset.owner != owner:
            return False, {"error": "Not authorized to revoke asset"}

        asset.is_active = False
        asset.updated_at = datetime.utcnow().isoformat()

        # Revoke all access tokens
        for token in self.access_tokens.values():
            if token.asset_id == asset_id:
                token.revoked = True

        # Emit event
        self._emit_event(ComputeEventType.ASSET_REVOKED, {"asset_id": asset_id})

        return True, {"asset_id": asset_id, "revoked": True}

    def list_assets(
        self,
        owner: str | None = None,
        asset_type: DataAssetType | None = None,
        active_only: bool = True,
    ) -> list[DataAsset]:
        """List assets with optional filters."""
        results = []
        for asset in self.assets.values():
            if active_only and not asset.is_active:
                continue
            if owner and asset.owner != owner:
                continue
            if asset_type and asset.asset_type != asset_type:
                continue
            results.append(asset)
        return results

    # =========================================================================
    # Access Control
    # =========================================================================

    def grant_access(
        self,
        asset_id: str,
        owner: str,
        grantee: str,
        access_level: AccessLevel,
        allowed_algorithms: list[str] | None = None,
        max_uses: int = MAX_COMPUTE_USES_PER_TOKEN,
        expires_in_hours: int = ACCESS_TOKEN_EXPIRY_HOURS,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Grant access to a data asset.

        Args:
            asset_id: Asset to grant access to
            owner: Asset owner (must match)
            grantee: DID to grant access to
            access_level: Level of access
            allowed_algorithms: Specific algorithms allowed
            max_uses: Maximum compute uses
            expires_in_hours: Token expiry

        Returns:
            Tuple of (success, token_info)
        """
        asset = self.assets.get(asset_id)
        if not asset:
            return False, {"error": "Asset not found"}

        if asset.owner != owner:
            return False, {"error": "Not authorized to grant access"}

        if not asset.is_active:
            return False, {"error": "Asset is not active"}

        # Generate access token
        token_id = f"token_{secrets.token_hex(16)}"
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()

        # If no algorithms specified, use asset's allowed algorithms
        if allowed_algorithms is None:
            allowed_algorithms = asset.allowed_algorithms

        token = AccessToken(
            token_id=token_id,
            asset_id=asset_id,
            grantee=grantee,
            access_level=access_level,
            allowed_algorithms=allowed_algorithms,
            max_uses=max_uses,
            uses_remaining=max_uses,
            expires_at=expires_at,
        )

        self.access_tokens[token_id] = token

        # Add grantee to allowed compute providers
        if grantee not in asset.allowed_compute_providers:
            asset.allowed_compute_providers.append(grantee)

        # Emit event
        self._emit_event(
            ComputeEventType.ACCESS_GRANTED,
            {"token_id": token_id, "asset_id": asset_id, "grantee": grantee, "access_level": access_level.value},
        )

        return True, token.to_dict()

    def revoke_access(self, token_id: str, owner: str) -> tuple[bool, dict[str, Any]]:
        """Revoke an access token."""
        token = self.access_tokens.get(token_id)
        if not token:
            return False, {"error": "Token not found"}

        asset = self.assets.get(token.asset_id)
        if not asset or asset.owner != owner:
            return False, {"error": "Not authorized to revoke token"}

        token.revoked = True

        # Emit event
        self._emit_event(
            ComputeEventType.ACCESS_REVOKED,
            {"token_id": token_id, "asset_id": token.asset_id},
        )

        return True, {"token_id": token_id, "revoked": True}

    def get_access_tokens(self, asset_id: str | None = None, grantee: str | None = None) -> list[AccessToken]:
        """Get access tokens with optional filters."""
        results = []
        for token in self.access_tokens.values():
            if asset_id and token.asset_id != asset_id:
                continue
            if grantee and token.grantee != grantee:
                continue
            results.append(token)
        return results

    # =========================================================================
    # Algorithm Management
    # =========================================================================

    def register_algorithm(
        self,
        algorithm_type: ComputeAlgorithmType,
        name: str,
        code_hash: str,
        author: str | None = None,
        description: str | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        privacy_preserving: bool = True,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Register a custom algorithm.

        Note: Custom algorithms would need security review in production.
        """
        algorithm_id = f"alg_{secrets.token_hex(8)}"

        algorithm = ComputeAlgorithm(
            algorithm_id=algorithm_id,
            algorithm_type=algorithm_type,
            name=name,
            description=description,
            author=author,
            code_hash=code_hash,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            privacy_preserving=privacy_preserving,
            audited=False,  # Custom algorithms start unaudited
        )

        self.algorithms[algorithm_id] = algorithm

        # Emit event
        self._emit_event(
            ComputeEventType.ALGORITHM_REGISTERED,
            {"algorithm_id": algorithm_id, "name": name, "author": author},
        )

        return True, algorithm.to_dict()

    def get_algorithm(self, algorithm_id: str) -> ComputeAlgorithm | None:
        """Get algorithm by ID."""
        return self.algorithms.get(algorithm_id)

    def list_algorithms(
        self,
        algorithm_type: ComputeAlgorithmType | None = None,
        privacy_preserving_only: bool = False,
        audited_only: bool = False,
    ) -> list[ComputeAlgorithm]:
        """List algorithms with optional filters."""
        results = []
        for algorithm in self.algorithms.values():
            if not algorithm.is_active:
                continue
            if algorithm_type and algorithm.algorithm_type != algorithm_type:
                continue
            if privacy_preserving_only and not algorithm.privacy_preserving:
                continue
            if audited_only and not algorithm.audited:
                continue
            results.append(algorithm)
        return results

    # =========================================================================
    # Compute Job Execution
    # =========================================================================

    def submit_job(
        self,
        asset_id: str,
        algorithm_id: str,
        access_token_id: str,
        requester: str,
        parameters: dict[str, Any] | None = None,
        privacy_level: PrivacyLevel | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Submit a compute job.

        Args:
            asset_id: Data asset to compute on
            algorithm_id: Algorithm to run
            access_token_id: Access token
            requester: Requester DID
            parameters: Algorithm parameters
            privacy_level: Override privacy level

        Returns:
            Tuple of (success, job_info)
        """
        # Validate asset
        asset = self.assets.get(asset_id)
        if not asset:
            return False, {"error": "Asset not found"}
        if not asset.is_active:
            return False, {"error": "Asset is not active"}

        # Validate algorithm
        algorithm = self.algorithms.get(algorithm_id)
        if not algorithm:
            return False, {"error": "Algorithm not found"}
        if not algorithm.is_active:
            return False, {"error": "Algorithm is not active"}

        # Validate access token
        token = self.access_tokens.get(access_token_id)
        if not token:
            return False, {"error": "Access token not found"}
        if not token.is_valid():
            return False, {"error": "Access token is invalid or expired"}
        if token.asset_id != asset_id:
            return False, {"error": "Token is for different asset"}
        if token.grantee != requester:
            return False, {"error": "Token is for different requester"}

        # Check algorithm authorization
        if algorithm_id not in asset.allowed_algorithms:
            return False, {"error": "Algorithm not allowed for this asset"}
        if token.allowed_algorithms and algorithm_id not in token.allowed_algorithms:
            return False, {"error": "Algorithm not allowed by access token"}

        # Check access level
        if token.access_level == AccessLevel.METADATA_ONLY:
            return False, {"error": "Access level does not allow compute"}

        # Determine privacy level
        job_privacy = privacy_level or asset.privacy_level
        if job_privacy.value < asset.privacy_level.value:  # More permissive than allowed
            job_privacy = asset.privacy_level

        # Create job
        job_id = f"job_{secrets.token_hex(12)}"
        job = ComputeJob(
            job_id=job_id,
            asset_id=asset_id,
            algorithm_id=algorithm_id,
            requester=requester,
            access_token_id=access_token_id,
            parameters=parameters or {},
            privacy_level=job_privacy,
        )

        self.jobs[job_id] = job

        # Decrement token uses
        token.uses_remaining -= 1

        # Emit event
        self._emit_event(
            ComputeEventType.JOB_SUBMITTED,
            {"job_id": job_id, "asset_id": asset_id, "algorithm_id": algorithm_id},
        )

        # Execute job (in production, this would be async/queued)
        self._execute_job(job)

        return True, job.to_dict()

    def _execute_job(self, job: ComputeJob) -> None:
        """Execute a compute job."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow().isoformat()

        # Emit event
        self._emit_event(ComputeEventType.JOB_STARTED, {"job_id": job.job_id})

        try:
            # Get data
            data = self._data_store.get(job.asset_id, [])
            asset = self.assets[job.asset_id]

            # Execute algorithm
            success, raw_result, compute_time = self.compute_env.execute(
                job.algorithm_id,
                data,
                job.parameters,
            )

            job.compute_time_ms = compute_time

            if not success:
                job.status = JobStatus.FAILED
                job.error_message = raw_result.get("error", "Unknown error")
                job.completed_at = datetime.utcnow().isoformat()

                self._emit_event(
                    ComputeEventType.JOB_FAILED,
                    {"job_id": job.job_id, "error": job.error_message},
                )
                return

            # Apply privacy filter
            self.privacy_filter.min_aggregation_size = asset.min_aggregation_size
            filtered_result = self.privacy_filter.apply(raw_result, job.privacy_level, len(data))

            # Check for privacy filter errors
            if "error" in filtered_result and filtered_result.get("error") == "insufficient_data":
                job.status = JobStatus.FAILED
                job.error_message = filtered_result.get("message", "Insufficient data for privacy protection")
                job.completed_at = datetime.utcnow().isoformat()

                self._emit_event(
                    ComputeEventType.JOB_FAILED,
                    {"job_id": job.job_id, "error": job.error_message},
                )
                return

            # Create result
            result_id = f"result_{secrets.token_hex(12)}"
            result_hash = hashlib.sha256(str(filtered_result).encode()).hexdigest()

            result = ComputeResult(
                result_id=result_id,
                job_id=job.job_id,
                asset_id=job.asset_id,
                algorithm_id=job.algorithm_id,
                requester=job.requester,
                data=filtered_result,
                privacy_level=job.privacy_level,
                record_count=len(data),
                result_hash=result_hash,
            )

            self.results[result_id] = result

            # Update job
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            job.result = filtered_result
            job.result_hash = result_hash

            # Emit event
            self._emit_event(
                ComputeEventType.JOB_COMPLETED,
                {"job_id": job.job_id, "result_id": result_id},
            )

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow().isoformat()

            self._emit_event(
                ComputeEventType.JOB_FAILED,
                {"job_id": job.job_id, "error": str(e)},
            )

    def get_job(self, job_id: str) -> ComputeJob | None:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def get_job_result(self, job_id: str, requester: str) -> tuple[bool, dict[str, Any]]:
        """
        Get result for a completed job.

        Args:
            job_id: Job ID
            requester: Requester DID (must match job)

        Returns:
            Tuple of (success, result_data)
        """
        job = self.jobs.get(job_id)
        if not job:
            return False, {"error": "Job not found"}

        if job.requester != requester:
            return False, {"error": "Not authorized to access result"}

        if job.status != JobStatus.COMPLETED:
            return False, {"error": f"Job status is {job.status.value}"}

        # Find result
        for result in self.results.values():
            if result.job_id == job_id:
                self._emit_event(
                    ComputeEventType.RESULT_RETRIEVED,
                    {"result_id": result.result_id, "job_id": job_id},
                )
                return True, result.to_dict()

        return False, {"error": "Result not found"}

    def list_jobs(
        self,
        requester: str | None = None,
        asset_id: str | None = None,
        status: JobStatus | None = None,
    ) -> list[ComputeJob]:
        """List jobs with optional filters."""
        results = []
        for job in self.jobs.values():
            if requester and job.requester != requester:
                continue
            if asset_id and job.asset_id != asset_id:
                continue
            if status and job.status != status:
                continue
            results.append(job)
        return results

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get compute service statistics."""
        asset_type_counts: dict[str, int] = {}
        for asset in self.assets.values():
            at = asset.asset_type.value
            asset_type_counts[at] = asset_type_counts.get(at, 0) + 1

        job_status_counts: dict[str, int] = {}
        for job in self.jobs.values():
            js = job.status.value
            job_status_counts[js] = job_status_counts.get(js, 0) + 1

        algorithm_type_counts: dict[str, int] = {}
        for algorithm in self.algorithms.values():
            at = algorithm.algorithm_type.value
            algorithm_type_counts[at] = algorithm_type_counts.get(at, 0) + 1

        total_compute_time = sum(j.compute_time_ms or 0 for j in self.jobs.values())
        avg_compute_time = total_compute_time / len(self.jobs) if self.jobs else 0

        return {
            "assets": {
                "total": len(self.assets),
                "active": sum(1 for a in self.assets.values() if a.is_active),
                "by_type": asset_type_counts,
            },
            "algorithms": {
                "total": len(self.algorithms),
                "builtin": sum(1 for a in self.algorithms.values() if a.algorithm_id.startswith("builtin_")),
                "custom": sum(1 for a in self.algorithms.values() if not a.algorithm_id.startswith("builtin_")),
                "by_type": algorithm_type_counts,
            },
            "access_tokens": {
                "total": len(self.access_tokens),
                "valid": sum(1 for t in self.access_tokens.values() if t.is_valid()),
            },
            "jobs": {
                "total": len(self.jobs),
                "by_status": job_status_counts,
                "avg_compute_time_ms": round(avg_compute_time, 2),
            },
            "results": {
                "total": len(self.results),
            },
            "events": {
                "total": len(self.events),
            },
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _emit_event(self, event_type: ComputeEventType, data: dict[str, Any]) -> None:
        """Emit a compute event."""
        event = ComputeEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
        )
        self.events.append(event)
