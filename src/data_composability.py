"""
NatLangChain - Data Composability Layer

Cross-application data sharing and composability system inspired by
Ceramic Network. Enables contracts and entries to be shared, linked,
and composed across different applications.

Features:
- Stream-based data model for versioned, updateable content
- Schema registry for interoperability between applications
- Cross-application linking and references
- Composable data objects that can be combined
- Import/export for data portability
- Application namespace isolation with controlled sharing

Stream Types:
- TileDocument: Mutable documents controlled by a DID
- CAIP10Link: Links blockchain accounts to DIDs
- Model: Reusable data schemas
- ModelInstanceDocument: Instances of models

Architecture:
1. Streams are identified by unique StreamIDs
2. Commits represent changes to streams
3. Tips are the current state of a stream
4. Anchors provide immutable timestamps via blockchain
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

STREAM_ID_PREFIX = "kjzl"  # Ceramic-style stream ID prefix
COMMIT_ID_PREFIX = "bagc"  # Commit ID prefix
MODEL_ID_PREFIX = "kh4q"  # Model ID prefix

# Schema versioning
SCHEMA_VERSION = "1.0"
MAX_STREAM_SIZE_BYTES = 1024 * 1024  # 1MB max per stream


# =============================================================================
# Enums
# =============================================================================


class StreamType(Enum):
    """Types of streams."""

    TILE_DOCUMENT = "tile"
    MODEL = "model"
    MODEL_INSTANCE = "model_instance"
    CAIP10_LINK = "caip10_link"
    CONTRACT_STREAM = "contract_stream"
    ENTRY_STREAM = "entry_stream"


class CommitType(Enum):
    """Types of commits to a stream."""

    GENESIS = "genesis"  # Initial creation
    SIGNED = "signed"  # Signed update
    ANCHOR = "anchor"  # Blockchain anchor
    TIME = "time"  # Time-based update


class StreamState(Enum):
    """Stream lifecycle states."""

    PENDING = "pending"
    ANCHORED = "anchored"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SchemaType(Enum):
    """Types of schemas."""

    JSON_SCHEMA = "json-schema"
    GRAPHQL = "graphql"
    PROTOBUF = "protobuf"
    NATLANGCHAIN = "natlangchain"


class LinkType(Enum):
    """Types of cross-application links."""

    REFERENCE = "reference"  # Simple reference to another stream
    EMBED = "embed"  # Embedded content
    DERIVE = "derive"  # Derived from another stream
    RESPOND = "respond"  # Response to another stream
    EXTEND = "extend"  # Extension of another stream


class ComposabilityEventType(Enum):
    """Types of composability events."""

    STREAM_CREATED = "stream_created"
    STREAM_UPDATED = "stream_updated"
    STREAM_ANCHORED = "stream_anchored"
    STREAM_PUBLISHED = "stream_published"
    LINK_CREATED = "link_created"
    SCHEMA_REGISTERED = "schema_registered"
    APP_REGISTERED = "app_registered"
    IMPORT_COMPLETED = "import_completed"
    EXPORT_COMPLETED = "export_completed"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StreamCommit:
    """A commit (change) to a stream."""

    commit_id: str
    stream_id: str
    commit_type: CommitType
    data: dict[str, Any]
    prev_commit_id: str | None  # Previous commit (forms chain)
    controller: str  # DID controlling this commit
    timestamp: str
    signature: str | None = None
    anchor_proof: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "commit_id": self.commit_id,
            "stream_id": self.stream_id,
            "commit_type": self.commit_type.value,
            "data": self.data,
            "prev_commit_id": self.prev_commit_id,
            "controller": self.controller,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "anchor_proof": self.anchor_proof,
        }


@dataclass
class StreamMetadata:
    """Metadata for a stream."""

    controllers: list[str]  # DIDs that can update the stream
    family: str | None = None  # Optional family grouping
    tags: list[str] = field(default_factory=list)
    schema_id: str | None = None  # Schema this stream conforms to
    model_id: str | None = None  # Model ID for model instances
    application_id: str | None = None  # Application that created this
    unique: str | None = None  # Unique constraint field

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "controllers": self.controllers,
            "family": self.family,
            "tags": self.tags,
            "schema_id": self.schema_id,
            "model_id": self.model_id,
            "application_id": self.application_id,
            "unique": self.unique,
        }


@dataclass
class Stream:
    """A composable data stream."""

    stream_id: str
    stream_type: StreamType
    content: dict[str, Any]
    metadata: StreamMetadata
    state: StreamState
    tip: str  # Current commit ID
    commits: list[StreamCommit] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    anchored_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type.value,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "state": self.state.value,
            "tip": self.tip,
            "commit_count": len(self.commits),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "anchored_at": self.anchored_at,
        }


@dataclass
class CrossAppLink:
    """Link between streams across applications."""

    link_id: str
    source_stream_id: str
    target_stream_id: str
    link_type: LinkType
    source_app_id: str
    target_app_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str | None = None  # DID that created the link

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "link_id": self.link_id,
            "source_stream_id": self.source_stream_id,
            "target_stream_id": self.target_stream_id,
            "link_type": self.link_type.value,
            "source_app_id": self.source_app_id,
            "target_app_id": self.target_app_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }


@dataclass
class Schema:
    """Reusable data schema."""

    schema_id: str
    name: str
    version: str
    schema_type: SchemaType
    definition: dict[str, Any]  # The actual schema definition
    description: str | None = None
    author: str | None = None  # DID of schema author
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dependencies: list[str] = field(default_factory=list)  # Other schema IDs

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_id": self.schema_id,
            "name": self.name,
            "version": self.version,
            "schema_type": self.schema_type.value,
            "definition": self.definition,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "dependencies": self.dependencies,
        }


@dataclass
class Application:
    """Registered application for composability."""

    app_id: str
    name: str
    description: str | None = None
    controllers: list[str] = field(default_factory=list)  # Admin DIDs
    schemas: list[str] = field(default_factory=list)  # Schema IDs used
    models: list[str] = field(default_factory=list)  # Model IDs defined
    endpoints: dict[str, str] = field(default_factory=dict)  # API endpoints
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    stream_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "app_id": self.app_id,
            "name": self.name,
            "description": self.description,
            "controllers": self.controllers,
            "schemas": self.schemas,
            "models": self.models,
            "endpoints": self.endpoints,
            "created_at": self.created_at,
            "stream_count": self.stream_count,
        }


@dataclass
class ComposableContract:
    """A contract represented as a composable stream."""

    stream_id: str
    original_entry_hash: str
    block_index: int
    entry_index: int
    contract_content: str
    parsed_terms: dict[str, Any]
    parties: list[str]  # DIDs or identifiers
    linked_streams: list[str] = field(default_factory=list)
    responses: list[str] = field(default_factory=list)  # Response stream IDs

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stream_id": self.stream_id,
            "original_entry_hash": self.original_entry_hash,
            "block_index": self.block_index,
            "entry_index": self.entry_index,
            "contract_content": self.contract_content,
            "parsed_terms": self.parsed_terms,
            "parties": self.parties,
            "linked_streams": self.linked_streams,
            "responses": self.responses,
        }


@dataclass
class ExportPackage:
    """Package for exporting streams."""

    package_id: str
    streams: list[dict[str, Any]]
    schemas: list[dict[str, Any]]
    links: list[dict[str, Any]]
    source_app_id: str
    exported_at: str
    exported_by: str | None = None
    format_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package_id": self.package_id,
            "stream_count": len(self.streams),
            "schema_count": len(self.schemas),
            "link_count": len(self.links),
            "source_app_id": self.source_app_id,
            "exported_at": self.exported_at,
            "exported_by": self.exported_by,
            "format_version": self.format_version,
            "streams": self.streams,
            "schemas": self.schemas,
            "links": self.links,
        }


@dataclass
class ComposabilityEvent:
    """Event in composability system."""

    event_id: str
    event_type: ComposabilityEventType
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
# ID Generation
# =============================================================================


class IDGenerator:
    """Utilities for generating IDs."""

    @staticmethod
    def generate_stream_id() -> str:
        """Generate a unique stream ID."""
        random_bytes = secrets.token_bytes(24)
        encoded = hashlib.sha256(random_bytes).hexdigest()[:32]
        return f"{STREAM_ID_PREFIX}_{encoded}"

    @staticmethod
    def generate_commit_id() -> str:
        """Generate a unique commit ID."""
        random_bytes = secrets.token_bytes(16)
        encoded = hashlib.sha256(random_bytes).hexdigest()[:24]
        return f"{COMMIT_ID_PREFIX}_{encoded}"

    @staticmethod
    def generate_schema_id(name: str, version: str) -> str:
        """Generate a schema ID from name and version."""
        content = f"{name}:{version}:{secrets.token_hex(8)}"
        encoded = hashlib.sha256(content.encode()).hexdigest()[:24]
        return f"schema_{encoded}"

    @staticmethod
    def generate_model_id() -> str:
        """Generate a model ID."""
        random_bytes = secrets.token_bytes(16)
        encoded = hashlib.sha256(random_bytes).hexdigest()[:24]
        return f"{MODEL_ID_PREFIX}_{encoded}"

    @staticmethod
    def generate_link_id() -> str:
        """Generate a link ID."""
        return f"link_{secrets.token_hex(12)}"

    @staticmethod
    def generate_app_id(name: str) -> str:
        """Generate an application ID."""
        content = f"{name}:{secrets.token_hex(8)}"
        encoded = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"app_{encoded}"


# =============================================================================
# Schema Validator
# =============================================================================


class SchemaValidator:
    """Validates content against schemas."""

    def __init__(self, schemas: dict[str, Schema] | None = None):
        self.schemas = schemas or {}

    def validate(self, content: dict[str, Any], schema_id: str) -> tuple[bool, list[str]]:
        """
        Validate content against a schema.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if schema_id not in self.schemas:
            return False, [f"Schema {schema_id} not found"]

        schema = self.schemas[schema_id]

        if schema.schema_type == SchemaType.JSON_SCHEMA:
            return self._validate_json_schema(content, schema.definition)
        elif schema.schema_type == SchemaType.NATLANGCHAIN:
            return self._validate_natlangchain_schema(content, schema.definition)
        else:
            return True, []  # Unknown schema types pass by default

    def _validate_json_schema(
        self, content: dict[str, Any], definition: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate against JSON Schema (simplified)."""
        errors = []

        # Check required fields
        required = definition.get("required", [])
        for field_name in required:
            if field_name not in content:
                errors.append(f"Missing required field: {field_name}")

        # Check property types
        properties = definition.get("properties", {})
        for field_name, field_def in properties.items():
            if field_name in content:
                expected_type = field_def.get("type")
                value = content[field_name]

                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field_name} must be a string")
                elif expected_type == "number" and not isinstance(value, int | float):
                    errors.append(f"Field {field_name} must be a number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {field_name} must be a boolean")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Field {field_name} must be an array")
                elif expected_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field {field_name} must be an object")

        return len(errors) == 0, errors

    def _validate_natlangchain_schema(
        self, content: dict[str, Any], definition: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate against NatLangChain schema."""
        errors = []

        # Check intent field for contracts
        if definition.get("requires_intent") and "intent" not in content:
            errors.append("Missing required intent field")

        # Check parties for contracts
        if definition.get("requires_parties"):
            if "parties" not in content or not content["parties"]:
                errors.append("Missing required parties field")

        # Check content field
        if definition.get("requires_content") and "content" not in content:
            errors.append("Missing required content field")

        return len(errors) == 0, errors


# =============================================================================
# Composability Service
# =============================================================================


class ComposabilityService:
    """
    Service for managing cross-application data composability.

    Enables streams (entries/contracts) to be shared, linked, and
    composed across different applications.
    """

    def __init__(self):
        self.streams: dict[str, Stream] = {}
        self.schemas: dict[str, Schema] = {}
        self.applications: dict[str, Application] = {}
        self.links: dict[str, CrossAppLink] = {}
        self.events: list[ComposabilityEvent] = []
        self.validator = SchemaValidator()

        # Initialize default schemas
        self._register_default_schemas()

    def _register_default_schemas(self) -> None:
        """Register default NatLangChain schemas."""
        # Entry schema
        self.register_schema(
            name="NatLangChainEntry",
            version="1.0",
            schema_type=SchemaType.NATLANGCHAIN,
            definition={
                "type": "object",
                "requires_content": True,
                "requires_intent": True,
                "properties": {
                    "content": {"type": "string"},
                    "intent": {"type": "string"},
                    "author": {"type": "string"},
                    "metadata": {"type": "object"},
                },
            },
            description="Standard NatLangChain entry schema",
        )

        # Contract schema
        self.register_schema(
            name="NatLangChainContract",
            version="1.0",
            schema_type=SchemaType.NATLANGCHAIN,
            definition={
                "type": "object",
                "requires_content": True,
                "requires_intent": True,
                "requires_parties": True,
                "properties": {
                    "content": {"type": "string"},
                    "intent": {"type": "string"},
                    "parties": {"type": "array"},
                    "terms": {"type": "object"},
                    "contract_type": {"type": "string"},
                },
            },
            description="Standard NatLangChain contract schema",
        )

    # =========================================================================
    # Stream Management
    # =========================================================================

    def create_stream(
        self,
        stream_type: StreamType,
        content: dict[str, Any],
        controller: str,
        schema_id: str | None = None,
        app_id: str | None = None,
        tags: list[str] | None = None,
        family: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a new stream.

        Args:
            stream_type: Type of stream
            content: Initial content
            controller: DID controlling the stream
            schema_id: Optional schema to validate against
            app_id: Optional application ID
            tags: Optional tags
            family: Optional family grouping

        Returns:
            Tuple of (success, stream_info)
        """
        # Validate against schema if provided
        if schema_id:
            self.validator.schemas = self.schemas
            is_valid, errors = self.validator.validate(content, schema_id)
            if not is_valid:
                return False, {"error": "Schema validation failed", "errors": errors}

        # Generate IDs
        stream_id = IDGenerator.generate_stream_id()
        commit_id = IDGenerator.generate_commit_id()

        # Create genesis commit
        genesis_commit = StreamCommit(
            commit_id=commit_id,
            stream_id=stream_id,
            commit_type=CommitType.GENESIS,
            data=content,
            prev_commit_id=None,
            controller=controller,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Create metadata
        metadata = StreamMetadata(
            controllers=[controller],
            schema_id=schema_id,
            application_id=app_id,
            tags=tags or [],
            family=family,
        )

        # Create stream
        stream = Stream(
            stream_id=stream_id,
            stream_type=stream_type,
            content=content,
            metadata=metadata,
            state=StreamState.PENDING,
            tip=commit_id,
            commits=[genesis_commit],
        )

        self.streams[stream_id] = stream

        # Update application stream count
        if app_id and app_id in self.applications:
            self.applications[app_id].stream_count += 1

        # Emit event
        self._emit_event(
            ComposabilityEventType.STREAM_CREATED,
            {"stream_id": stream_id, "stream_type": stream_type.value, "controller": controller},
        )

        return True, {
            "stream_id": stream_id,
            "commit_id": commit_id,
            "stream": stream.to_dict(),
        }

    def update_stream(
        self,
        stream_id: str,
        content: dict[str, Any],
        controller: str,
        merge: bool = True,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Update a stream's content.

        Args:
            stream_id: Stream to update
            content: New content
            controller: DID making the update
            merge: Whether to merge with existing content (True) or replace (False)

        Returns:
            Tuple of (success, result)
        """
        if stream_id not in self.streams:
            return False, {"error": "Stream not found"}

        stream = self.streams[stream_id]

        # Check authorization
        if controller not in stream.metadata.controllers:
            return False, {"error": "Not authorized to update stream"}

        # Validate against schema if present
        if stream.metadata.schema_id:
            new_content = {**stream.content, **content} if merge else content
            self.validator.schemas = self.schemas
            is_valid, errors = self.validator.validate(new_content, stream.metadata.schema_id)
            if not is_valid:
                return False, {"error": "Schema validation failed", "errors": errors}

        # Create new commit
        commit_id = IDGenerator.generate_commit_id()
        commit = StreamCommit(
            commit_id=commit_id,
            stream_id=stream_id,
            commit_type=CommitType.SIGNED,
            data=content,
            prev_commit_id=stream.tip,
            controller=controller,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Update stream
        if merge:
            stream.content = {**stream.content, **content}
        else:
            stream.content = content

        stream.commits.append(commit)
        stream.tip = commit_id
        stream.updated_at = datetime.utcnow().isoformat()

        # Emit event
        self._emit_event(
            ComposabilityEventType.STREAM_UPDATED,
            {"stream_id": stream_id, "commit_id": commit_id},
        )

        return True, {
            "stream_id": stream_id,
            "commit_id": commit_id,
            "content": stream.content,
        }

    def get_stream(self, stream_id: str) -> Stream | None:
        """Get a stream by ID."""
        return self.streams.get(stream_id)

    def get_stream_at_commit(self, stream_id: str, commit_id: str) -> dict[str, Any] | None:
        """Get stream content at a specific commit."""
        stream = self.streams.get(stream_id)
        if not stream:
            return None

        # Reconstruct content up to commit
        content: dict[str, Any] = {}
        for commit in stream.commits:
            if commit.commit_type in [CommitType.GENESIS, CommitType.SIGNED]:
                content = {**content, **commit.data}
            if commit.commit_id == commit_id:
                break

        return {"stream_id": stream_id, "commit_id": commit_id, "content": content}

    def get_stream_history(self, stream_id: str) -> list[dict[str, Any]]:
        """Get commit history for a stream."""
        stream = self.streams.get(stream_id)
        if not stream:
            return []

        return [c.to_dict() for c in stream.commits]

    def anchor_stream(self, stream_id: str, anchor_proof: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """
        Anchor a stream to external blockchain.

        Args:
            stream_id: Stream to anchor
            anchor_proof: Proof from external anchoring

        Returns:
            Tuple of (success, result)
        """
        if stream_id not in self.streams:
            return False, {"error": "Stream not found"}

        stream = self.streams[stream_id]

        # Create anchor commit
        commit_id = IDGenerator.generate_commit_id()
        commit = StreamCommit(
            commit_id=commit_id,
            stream_id=stream_id,
            commit_type=CommitType.ANCHOR,
            data={},
            prev_commit_id=stream.tip,
            controller=stream.metadata.controllers[0],
            timestamp=datetime.utcnow().isoformat(),
            anchor_proof=anchor_proof,
        )

        stream.commits.append(commit)
        stream.tip = commit_id
        stream.state = StreamState.ANCHORED
        stream.anchored_at = datetime.utcnow().isoformat()

        # Emit event
        self._emit_event(
            ComposabilityEventType.STREAM_ANCHORED,
            {"stream_id": stream_id, "anchor_proof": anchor_proof},
        )

        return True, {"stream_id": stream_id, "state": "anchored", "commit_id": commit_id}

    def publish_stream(self, stream_id: str) -> tuple[bool, dict[str, Any]]:
        """Make a stream publicly accessible."""
        if stream_id not in self.streams:
            return False, {"error": "Stream not found"}

        stream = self.streams[stream_id]
        stream.state = StreamState.PUBLISHED

        # Emit event
        self._emit_event(
            ComposabilityEventType.STREAM_PUBLISHED,
            {"stream_id": stream_id},
        )

        return True, {"stream_id": stream_id, "state": "published"}

    def query_streams(
        self,
        stream_type: StreamType | None = None,
        app_id: str | None = None,
        schema_id: str | None = None,
        controller: str | None = None,
        tags: list[str] | None = None,
        family: str | None = None,
        limit: int = 100,
    ) -> list[Stream]:
        """
        Query streams with filters.

        Args:
            stream_type: Filter by stream type
            app_id: Filter by application
            schema_id: Filter by schema
            controller: Filter by controller
            tags: Filter by tags (any match)
            family: Filter by family
            limit: Maximum results

        Returns:
            List of matching streams
        """
        results = []

        for stream in self.streams.values():
            if stream_type and stream.stream_type != stream_type:
                continue
            if app_id and stream.metadata.application_id != app_id:
                continue
            if schema_id and stream.metadata.schema_id != schema_id:
                continue
            if controller and controller not in stream.metadata.controllers:
                continue
            if tags and not any(t in stream.metadata.tags for t in tags):
                continue
            if family and stream.metadata.family != family:
                continue

            results.append(stream)

            if len(results) >= limit:
                break

        return results

    # =========================================================================
    # Schema Management
    # =========================================================================

    def register_schema(
        self,
        name: str,
        version: str,
        schema_type: SchemaType,
        definition: dict[str, Any],
        description: str | None = None,
        author: str | None = None,
        dependencies: list[str] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Register a new schema.

        Args:
            name: Schema name
            version: Schema version
            schema_type: Type of schema
            definition: Schema definition
            description: Optional description
            author: Optional author DID
            dependencies: Optional schema dependencies

        Returns:
            Tuple of (success, schema_info)
        """
        schema_id = IDGenerator.generate_schema_id(name, version)

        # Check for duplicate name+version
        for existing in self.schemas.values():
            if existing.name == name and existing.version == version:
                return False, {"error": f"Schema {name}:{version} already exists"}

        schema = Schema(
            schema_id=schema_id,
            name=name,
            version=version,
            schema_type=schema_type,
            definition=definition,
            description=description,
            author=author,
            dependencies=dependencies or [],
        )

        self.schemas[schema_id] = schema

        # Emit event
        self._emit_event(
            ComposabilityEventType.SCHEMA_REGISTERED,
            {"schema_id": schema_id, "name": name, "version": version},
        )

        return True, schema.to_dict()

    def get_schema(self, schema_id: str) -> Schema | None:
        """Get a schema by ID."""
        return self.schemas.get(schema_id)

    def list_schemas(
        self,
        schema_type: SchemaType | None = None,
        name: str | None = None,
    ) -> list[Schema]:
        """List schemas with optional filters."""
        results = []
        for schema in self.schemas.values():
            if schema_type and schema.schema_type != schema_type:
                continue
            if name and schema.name != name:
                continue
            results.append(schema)
        return results

    # =========================================================================
    # Application Management
    # =========================================================================

    def register_application(
        self,
        name: str,
        controllers: list[str],
        description: str | None = None,
        endpoints: dict[str, str] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Register a new application.

        Args:
            name: Application name
            controllers: Admin DIDs
            description: Optional description
            endpoints: Optional API endpoints

        Returns:
            Tuple of (success, app_info)
        """
        app_id = IDGenerator.generate_app_id(name)

        app = Application(
            app_id=app_id,
            name=name,
            description=description,
            controllers=controllers,
            endpoints=endpoints or {},
        )

        self.applications[app_id] = app

        # Emit event
        self._emit_event(
            ComposabilityEventType.APP_REGISTERED,
            {"app_id": app_id, "name": name},
        )

        return True, app.to_dict()

    def get_application(self, app_id: str) -> Application | None:
        """Get an application by ID."""
        return self.applications.get(app_id)

    def list_applications(self) -> list[Application]:
        """List all registered applications."""
        return list(self.applications.values())

    # =========================================================================
    # Cross-Application Linking
    # =========================================================================

    def create_link(
        self,
        source_stream_id: str,
        target_stream_id: str,
        link_type: LinkType,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a link between streams.

        Args:
            source_stream_id: Source stream
            target_stream_id: Target stream
            link_type: Type of link
            created_by: Optional DID creating the link
            metadata: Optional link metadata

        Returns:
            Tuple of (success, link_info)
        """
        # Validate streams exist
        source = self.streams.get(source_stream_id)
        target = self.streams.get(target_stream_id)

        if not source:
            return False, {"error": "Source stream not found"}
        if not target:
            return False, {"error": "Target stream not found"}

        link_id = IDGenerator.generate_link_id()

        link = CrossAppLink(
            link_id=link_id,
            source_stream_id=source_stream_id,
            target_stream_id=target_stream_id,
            link_type=link_type,
            source_app_id=source.metadata.application_id or "",
            target_app_id=target.metadata.application_id or "",
            metadata=metadata or {},
            created_by=created_by,
        )

        self.links[link_id] = link

        # Emit event
        self._emit_event(
            ComposabilityEventType.LINK_CREATED,
            {
                "link_id": link_id,
                "source": source_stream_id,
                "target": target_stream_id,
                "link_type": link_type.value,
            },
        )

        return True, link.to_dict()

    def get_links(
        self,
        stream_id: str | None = None,
        link_type: LinkType | None = None,
        app_id: str | None = None,
    ) -> list[CrossAppLink]:
        """
        Get links with optional filters.

        Args:
            stream_id: Filter by stream (source or target)
            link_type: Filter by link type
            app_id: Filter by application

        Returns:
            List of matching links
        """
        results = []
        for link in self.links.values():
            if stream_id and stream_id not in [link.source_stream_id, link.target_stream_id]:
                continue
            if link_type and link.link_type != link_type:
                continue
            if app_id and app_id not in [link.source_app_id, link.target_app_id]:
                continue
            results.append(link)
        return results

    def get_linked_streams(self, stream_id: str, direction: str = "both") -> list[Stream]:
        """
        Get streams linked to a given stream.

        Args:
            stream_id: Stream to find links for
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of linked streams
        """
        linked_ids: set[str] = set()

        for link in self.links.values():
            if direction in ["outgoing", "both"] and link.source_stream_id == stream_id:
                linked_ids.add(link.target_stream_id)
            if direction in ["incoming", "both"] and link.target_stream_id == stream_id:
                linked_ids.add(link.source_stream_id)

        return [self.streams[sid] for sid in linked_ids if sid in self.streams]

    # =========================================================================
    # Import/Export
    # =========================================================================

    def export_streams(
        self,
        stream_ids: list[str],
        include_schemas: bool = True,
        include_links: bool = True,
        exported_by: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Export streams as a package.

        Args:
            stream_ids: Streams to export
            include_schemas: Include referenced schemas
            include_links: Include links between streams
            exported_by: DID exporting the data

        Returns:
            Tuple of (success, export_package)
        """
        streams_data = []
        schema_ids: set[str] = set()
        links_data = []

        for stream_id in stream_ids:
            stream = self.streams.get(stream_id)
            if not stream:
                continue

            streams_data.append({
                **stream.to_dict(),
                "commits": [c.to_dict() for c in stream.commits],
            })

            if include_schemas and stream.metadata.schema_id:
                schema_ids.add(stream.metadata.schema_id)

        # Get schemas
        schemas_data = []
        if include_schemas:
            for schema_id in schema_ids:
                schema = self.schemas.get(schema_id)
                if schema:
                    schemas_data.append(schema.to_dict())

        # Get links
        if include_links:
            exported_set = set(stream_ids)
            for link in self.links.values():
                if link.source_stream_id in exported_set or link.target_stream_id in exported_set:
                    links_data.append(link.to_dict())

        package = ExportPackage(
            package_id=f"pkg_{secrets.token_hex(8)}",
            streams=streams_data,
            schemas=schemas_data,
            links=links_data,
            source_app_id="natlangchain",
            exported_at=datetime.utcnow().isoformat(),
            exported_by=exported_by,
        )

        # Emit event
        self._emit_event(
            ComposabilityEventType.EXPORT_COMPLETED,
            {"package_id": package.package_id, "stream_count": len(streams_data)},
        )

        return True, package.to_dict()

    def import_streams(
        self,
        package: dict[str, Any],
        target_app_id: str | None = None,
        controller: str | None = None,
        remap_ids: bool = True,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Import streams from a package.

        Args:
            package: Export package data
            target_app_id: Application to import into
            controller: Controller for imported streams
            remap_ids: Whether to generate new IDs

        Returns:
            Tuple of (success, import_result)
        """
        id_mapping: dict[str, str] = {}
        imported_streams = []
        imported_schemas = []

        # Import schemas first
        for schema_data in package.get("schemas", []):
            if remap_ids:
                old_id = schema_data["schema_id"]
                # Skip if schema with same name+version exists
                existing = [
                    s for s in self.schemas.values()
                    if s.name == schema_data["name"] and s.version == schema_data["version"]
                ]
                if existing:
                    id_mapping[old_id] = existing[0].schema_id
                    continue

                success, result = self.register_schema(
                    name=schema_data["name"],
                    version=schema_data["version"],
                    schema_type=SchemaType(schema_data["schema_type"]),
                    definition=schema_data["definition"],
                    description=schema_data.get("description"),
                )
                if success:
                    id_mapping[old_id] = result["schema_id"]
                    imported_schemas.append(result["schema_id"])

        # Import streams
        for stream_data in package.get("streams", []):
            old_stream_id = stream_data["stream_id"]

            # Remap schema ID if needed
            schema_id = stream_data.get("metadata", {}).get("schema_id")
            if schema_id and schema_id in id_mapping:
                schema_id = id_mapping[schema_id]

            success, result = self.create_stream(
                stream_type=StreamType(stream_data["stream_type"]),
                content=stream_data["content"],
                controller=controller or stream_data.get("metadata", {}).get("controllers", ["unknown"])[0],
                schema_id=schema_id,
                app_id=target_app_id,
                tags=stream_data.get("metadata", {}).get("tags", []),
            )

            if success:
                new_id = result["stream_id"]
                id_mapping[old_stream_id] = new_id
                imported_streams.append(new_id)

        # Import links with remapped IDs
        imported_links = []
        for link_data in package.get("links", []):
            source = id_mapping.get(link_data["source_stream_id"], link_data["source_stream_id"])
            target = id_mapping.get(link_data["target_stream_id"], link_data["target_stream_id"])

            if source in self.streams and target in self.streams:
                success, result = self.create_link(
                    source_stream_id=source,
                    target_stream_id=target,
                    link_type=LinkType(link_data["link_type"]),
                    metadata=link_data.get("metadata", {}),
                )
                if success:
                    imported_links.append(result["link_id"])

        # Emit event
        self._emit_event(
            ComposabilityEventType.IMPORT_COMPLETED,
            {
                "streams_imported": len(imported_streams),
                "schemas_imported": len(imported_schemas),
                "links_imported": len(imported_links),
            },
        )

        return True, {
            "streams_imported": imported_streams,
            "schemas_imported": imported_schemas,
            "links_imported": imported_links,
            "id_mapping": id_mapping,
        }

    # =========================================================================
    # Contract Stream Helpers
    # =========================================================================

    def create_contract_stream(
        self,
        entry_hash: str,
        block_index: int,
        entry_index: int,
        content: str,
        intent: str,
        author: str,
        parties: list[str],
        terms: dict[str, Any] | None = None,
        controller: str | None = None,
        app_id: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create a composable stream from a contract entry.

        Args:
            entry_hash: Original entry hash
            block_index: Block containing entry
            entry_index: Index within block
            content: Contract content
            intent: Contract intent
            author: Contract author
            parties: Contract parties
            terms: Parsed contract terms
            controller: Optional controller DID
            app_id: Optional application ID

        Returns:
            Tuple of (success, stream_info)
        """
        stream_content = {
            "original_entry_hash": entry_hash,
            "block_index": block_index,
            "entry_index": entry_index,
            "content": content,
            "intent": intent,
            "author": author,
            "parties": parties,
            "terms": terms or {},
        }

        # Find contract schema
        contract_schema = None
        for schema in self.schemas.values():
            if schema.name == "NatLangChainContract":
                contract_schema = schema
                break

        return self.create_stream(
            stream_type=StreamType.CONTRACT_STREAM,
            content=stream_content,
            controller=controller or author,
            schema_id=contract_schema.schema_id if contract_schema else None,
            app_id=app_id,
            tags=["contract"],
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get composability service statistics."""
        stream_type_counts: dict[str, int] = {}
        for stream in self.streams.values():
            st = stream.stream_type.value
            stream_type_counts[st] = stream_type_counts.get(st, 0) + 1

        state_counts: dict[str, int] = {}
        for stream in self.streams.values():
            state = stream.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        link_type_counts: dict[str, int] = {}
        for link in self.links.values():
            lt = link.link_type.value
            link_type_counts[lt] = link_type_counts.get(lt, 0) + 1

        return {
            "streams": {
                "total": len(self.streams),
                "by_type": stream_type_counts,
                "by_state": state_counts,
            },
            "schemas": {
                "total": len(self.schemas),
            },
            "applications": {
                "total": len(self.applications),
            },
            "links": {
                "total": len(self.links),
                "by_type": link_type_counts,
            },
            "events": {
                "total": len(self.events),
            },
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _emit_event(self, event_type: ComposabilityEventType, data: dict[str, Any]) -> None:
        """Emit a composability event."""
        event = ComposabilityEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
        )
        self.events.append(event)
