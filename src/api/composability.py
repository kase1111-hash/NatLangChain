"""
NatLangChain - Composability API Blueprint

REST API endpoints for cross-application data composability.
Provides access to:
- Stream management (create, update, query)
- Schema registry
- Application management
- Cross-application linking
- Import/export operations
"""

from flask import Blueprint, jsonify, request

from .state import managers

composability_bp = Blueprint("composability", __name__)


# =============================================================================
# Stream Management Endpoints
# =============================================================================


@composability_bp.route("/composability/streams", methods=["POST"])
def create_stream():
    """
    Create a new composable stream.

    Request body:
        {
            "stream_type": "tile",              // tile, model, contract_stream, etc.
            "content": {...},                   // Stream content
            "controller": "did:nlc:...",        // DID controlling stream
            "schema_id": "schema_...",          // Optional schema
            "app_id": "app_...",                // Optional application
            "tags": ["contract", "offer"],      // Optional tags
            "family": "contracts"               // Optional family grouping
        }

    Returns:
        Created stream info
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    required = ["stream_type", "content", "controller"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from data_composability import StreamType

    try:
        stream_type = StreamType(data["stream_type"])
    except ValueError:
        return jsonify({"error": f"Invalid stream_type: {data['stream_type']}"}), 400

    success, result = managers.composability_service.create_stream(
        stream_type=stream_type,
        content=data["content"],
        controller=data["controller"],
        schema_id=data.get("schema_id"),
        app_id=data.get("app_id"),
        tags=data.get("tags"),
        family=data.get("family"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/streams/<stream_id>", methods=["GET"])
def get_stream(stream_id):
    """
    Get a stream by ID.

    Path params:
        stream_id: The stream ID

    Returns:
        Stream data
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    stream = managers.composability_service.get_stream(stream_id)
    if not stream:
        return jsonify({"error": "Stream not found"}), 404

    return jsonify(stream.to_dict())


@composability_bp.route("/composability/streams/<stream_id>", methods=["PATCH"])
def update_stream(stream_id):
    """
    Update a stream's content.

    Path params:
        stream_id: The stream ID

    Request body:
        {
            "content": {...},                // New content
            "controller": "did:nlc:...",     // DID making update
            "merge": true                    // Merge vs replace (default: true)
        }

    Returns:
        Update result
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    if "content" not in data or "controller" not in data:
        return jsonify({"error": "content and controller are required"}), 400

    success, result = managers.composability_service.update_stream(
        stream_id=stream_id,
        content=data["content"],
        controller=data["controller"],
        merge=data.get("merge", True),
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/streams/<stream_id>/history", methods=["GET"])
def get_stream_history(stream_id):
    """
    Get commit history for a stream.

    Path params:
        stream_id: The stream ID

    Returns:
        Commit history
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    history = managers.composability_service.get_stream_history(stream_id)
    if not history:
        stream = managers.composability_service.get_stream(stream_id)
        if not stream:
            return jsonify({"error": "Stream not found"}), 404

    return jsonify({"stream_id": stream_id, "commits": history})


@composability_bp.route("/composability/streams/<stream_id>/at/<commit_id>", methods=["GET"])
def get_stream_at_commit(stream_id, commit_id):
    """
    Get stream content at a specific commit.

    Path params:
        stream_id: The stream ID
        commit_id: The commit ID

    Returns:
        Stream content at commit
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    result = managers.composability_service.get_stream_at_commit(stream_id, commit_id)
    if not result:
        return jsonify({"error": "Stream or commit not found"}), 404

    return jsonify(result)


@composability_bp.route("/composability/streams/<stream_id>/anchor", methods=["POST"])
def anchor_stream(stream_id):
    """
    Anchor a stream to external blockchain.

    Path params:
        stream_id: The stream ID

    Request body:
        {
            "anchor_proof": {...}   // Proof from external anchoring
        }

    Returns:
        Anchor result
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    if "anchor_proof" not in data:
        return jsonify({"error": "anchor_proof is required"}), 400

    success, result = managers.composability_service.anchor_stream(stream_id, data["anchor_proof"])

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/streams/<stream_id>/publish", methods=["POST"])
def publish_stream(stream_id):
    """
    Make a stream publicly accessible.

    Path params:
        stream_id: The stream ID

    Returns:
        Publish result
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    success, result = managers.composability_service.publish_stream(stream_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/streams", methods=["GET"])
def query_streams():
    """
    Query streams with filters.

    Query params:
        stream_type: Filter by type
        app_id: Filter by application
        schema_id: Filter by schema
        controller: Filter by controller
        tags: Filter by tags (comma-separated)
        family: Filter by family
        limit: Max results (default: 100)

    Returns:
        List of matching streams
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    from data_composability import StreamType

    stream_type = None
    if request.args.get("stream_type"):
        try:
            stream_type = StreamType(request.args.get("stream_type"))
        except ValueError:
            return jsonify({"error": f"Invalid stream_type: {request.args.get('stream_type')}"}), 400

    tags = None
    if request.args.get("tags"):
        tags = request.args.get("tags").split(",")

    results = managers.composability_service.query_streams(
        stream_type=stream_type,
        app_id=request.args.get("app_id"),
        schema_id=request.args.get("schema_id"),
        controller=request.args.get("controller"),
        tags=tags,
        family=request.args.get("family"),
        limit=request.args.get("limit", 100, type=int),
    )

    return jsonify({"count": len(results), "streams": [s.to_dict() for s in results]})


# =============================================================================
# Schema Management Endpoints
# =============================================================================


@composability_bp.route("/composability/schemas", methods=["POST"])
def register_schema():
    """
    Register a new schema.

    Request body:
        {
            "name": "MyContract",
            "version": "1.0",
            "schema_type": "json-schema",       // json-schema, graphql, natlangchain
            "definition": {...},                // Schema definition
            "description": "...",               // Optional
            "author": "did:nlc:...",            // Optional author DID
            "dependencies": ["schema_..."]      // Optional schema dependencies
        }

    Returns:
        Registered schema info
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    required = ["name", "version", "schema_type", "definition"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from data_composability import SchemaType

    try:
        schema_type = SchemaType(data["schema_type"])
    except ValueError:
        return jsonify({"error": f"Invalid schema_type: {data['schema_type']}"}), 400

    success, result = managers.composability_service.register_schema(
        name=data["name"],
        version=data["version"],
        schema_type=schema_type,
        definition=data["definition"],
        description=data.get("description"),
        author=data.get("author"),
        dependencies=data.get("dependencies"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/schemas/<schema_id>", methods=["GET"])
def get_schema(schema_id):
    """
    Get a schema by ID.

    Path params:
        schema_id: The schema ID

    Returns:
        Schema data
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    schema = managers.composability_service.get_schema(schema_id)
    if not schema:
        return jsonify({"error": "Schema not found"}), 404

    return jsonify(schema.to_dict())


@composability_bp.route("/composability/schemas", methods=["GET"])
def list_schemas():
    """
    List schemas with optional filters.

    Query params:
        schema_type: Filter by type
        name: Filter by name

    Returns:
        List of schemas
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    from data_composability import SchemaType

    schema_type = None
    if request.args.get("schema_type"):
        try:
            schema_type = SchemaType(request.args.get("schema_type"))
        except ValueError:
            return jsonify({"error": f"Invalid schema_type: {request.args.get('schema_type')}"}), 400

    results = managers.composability_service.list_schemas(
        schema_type=schema_type,
        name=request.args.get("name"),
    )

    return jsonify({"count": len(results), "schemas": [s.to_dict() for s in results]})


# =============================================================================
# Application Management Endpoints
# =============================================================================


@composability_bp.route("/composability/apps", methods=["POST"])
def register_application():
    """
    Register a new application.

    Request body:
        {
            "name": "MyApp",
            "controllers": ["did:nlc:..."],     // Admin DIDs
            "description": "...",               // Optional
            "endpoints": {                      // Optional API endpoints
                "api": "https://api.myapp.com"
            }
        }

    Returns:
        Registered application info
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    if "name" not in data or "controllers" not in data:
        return jsonify({"error": "name and controllers are required"}), 400

    success, result = managers.composability_service.register_application(
        name=data["name"],
        controllers=data["controllers"],
        description=data.get("description"),
        endpoints=data.get("endpoints"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/apps/<app_id>", methods=["GET"])
def get_application(app_id):
    """
    Get an application by ID.

    Path params:
        app_id: The application ID

    Returns:
        Application data
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    app = managers.composability_service.get_application(app_id)
    if not app:
        return jsonify({"error": "Application not found"}), 404

    return jsonify(app.to_dict())


@composability_bp.route("/composability/apps", methods=["GET"])
def list_applications():
    """
    List all registered applications.

    Returns:
        List of applications
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    apps = managers.composability_service.list_applications()

    return jsonify({"count": len(apps), "applications": [a.to_dict() for a in apps]})


# =============================================================================
# Cross-Application Linking Endpoints
# =============================================================================


@composability_bp.route("/composability/links", methods=["POST"])
def create_link():
    """
    Create a link between streams.

    Request body:
        {
            "source_stream_id": "kjzl_...",
            "target_stream_id": "kjzl_...",
            "link_type": "reference",           // reference, embed, derive, respond, extend
            "created_by": "did:nlc:...",        // Optional
            "metadata": {...}                   // Optional
        }

    Returns:
        Created link info
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    required = ["source_stream_id", "target_stream_id", "link_type"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    from data_composability import LinkType

    try:
        link_type = LinkType(data["link_type"])
    except ValueError:
        return jsonify({"error": f"Invalid link_type: {data['link_type']}"}), 400

    success, result = managers.composability_service.create_link(
        source_stream_id=data["source_stream_id"],
        target_stream_id=data["target_stream_id"],
        link_type=link_type,
        created_by=data.get("created_by"),
        metadata=data.get("metadata"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/links", methods=["GET"])
def get_links():
    """
    Get links with optional filters.

    Query params:
        stream_id: Filter by stream (source or target)
        link_type: Filter by link type
        app_id: Filter by application

    Returns:
        List of links
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    from data_composability import LinkType

    link_type = None
    if request.args.get("link_type"):
        try:
            link_type = LinkType(request.args.get("link_type"))
        except ValueError:
            return jsonify({"error": f"Invalid link_type: {request.args.get('link_type')}"}), 400

    results = managers.composability_service.get_links(
        stream_id=request.args.get("stream_id"),
        link_type=link_type,
        app_id=request.args.get("app_id"),
    )

    return jsonify({"count": len(results), "links": [link.to_dict() for link in results]})


@composability_bp.route("/composability/streams/<stream_id>/linked", methods=["GET"])
def get_linked_streams(stream_id):
    """
    Get streams linked to a given stream.

    Path params:
        stream_id: The stream ID

    Query params:
        direction: "outgoing", "incoming", or "both" (default)

    Returns:
        List of linked streams
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    direction = request.args.get("direction", "both")
    if direction not in ["outgoing", "incoming", "both"]:
        return jsonify({"error": "direction must be outgoing, incoming, or both"}), 400

    results = managers.composability_service.get_linked_streams(stream_id, direction)

    return jsonify({"stream_id": stream_id, "direction": direction, "count": len(results), "linked_streams": [s.to_dict() for s in results]})


# =============================================================================
# Import/Export Endpoints
# =============================================================================


MAX_STREAM_IDS = 100  # Maximum number of stream IDs per export request


@composability_bp.route("/composability/export", methods=["POST"])
def export_streams():
    """
    Export streams as a package.

    Request body:
        {
            "stream_ids": ["kjzl_...", ...],  // Max 100 stream IDs
            "include_schemas": true,         // Default: true
            "include_links": true,           // Default: true
            "exported_by": "did:nlc:..."     // Optional
        }

    Returns:
        Export package
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    if "stream_ids" not in data or not data["stream_ids"]:
        return jsonify({"error": "stream_ids is required and must not be empty"}), 400

    # Validate list size to prevent resource exhaustion
    if len(data["stream_ids"]) > MAX_STREAM_IDS:
        return jsonify({"error": f"stream_ids exceeds maximum limit of {MAX_STREAM_IDS}"}), 400

    success, result = managers.composability_service.export_streams(
        stream_ids=data["stream_ids"],
        include_schemas=data.get("include_schemas", True),
        include_links=data.get("include_links", True),
        exported_by=data.get("exported_by"),
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@composability_bp.route("/composability/import", methods=["POST"])
def import_streams():
    """
    Import streams from a package.

    Request body:
        {
            "package": {...},                // Export package
            "target_app_id": "app_...",      // Optional target application
            "controller": "did:nlc:...",     // Optional controller for imported streams
            "remap_ids": true                // Whether to generate new IDs (default: true)
        }

    Returns:
        Import result
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    if "package" not in data:
        return jsonify({"error": "package is required"}), 400

    success, result = managers.composability_service.import_streams(
        package=data["package"],
        target_app_id=data.get("target_app_id"),
        controller=data.get("controller"),
        remap_ids=data.get("remap_ids", True),
    )

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


# =============================================================================
# Contract Stream Helpers
# =============================================================================


@composability_bp.route("/composability/streams/contract", methods=["POST"])
def create_contract_stream():
    """
    Create a composable stream from a contract entry.

    Request body:
        {
            "entry_hash": "abc123...",
            "block_index": 5,
            "entry_index": 2,
            "content": "Alice agrees to...",
            "intent": "Service agreement",
            "author": "alice@example.com",
            "parties": ["alice", "bob"],
            "terms": {...},                    // Optional parsed terms
            "controller": "did:nlc:...",       // Optional controller DID
            "app_id": "app_..."                // Optional application
        }

    Returns:
        Created contract stream info
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    data = request.get_json() or {}

    required = ["entry_hash", "block_index", "entry_index", "content", "intent", "author", "parties"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    success, result = managers.composability_service.create_contract_stream(
        entry_hash=data["entry_hash"],
        block_index=data["block_index"],
        entry_index=data["entry_index"],
        content=data["content"],
        intent=data["intent"],
        author=data["author"],
        parties=data["parties"],
        terms=data.get("terms"),
        controller=data.get("controller"),
        app_id=data.get("app_id"),
    )

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


# =============================================================================
# Statistics and Types
# =============================================================================


@composability_bp.route("/composability/statistics", methods=["GET"])
def get_statistics():
    """
    Get composability service statistics.

    Returns:
        Comprehensive statistics
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    return jsonify(managers.composability_service.get_statistics())


@composability_bp.route("/composability/events", methods=["GET"])
def get_events():
    """
    Get composability event log.

    Query params:
        limit: Maximum events to return (default: 100)
        event_type: Filter by event type (optional)

    Returns:
        List of events
    """
    if not managers.composability_service:
        return jsonify({"error": "Composability service not initialized"}), 503

    limit = request.args.get("limit", 100, type=int)
    event_type = request.args.get("event_type")

    events = managers.composability_service.events

    if event_type:
        events = [e for e in events if e.event_type.value == event_type]

    events = events[-limit:]

    return jsonify({"count": len(events), "events": [e.to_dict() for e in reversed(events)]})


@composability_bp.route("/composability/types/streams", methods=["GET"])
def get_stream_types():
    """
    Get supported stream types.

    Returns:
        List of stream types
    """
    from data_composability import StreamType

    return jsonify({"types": [t.value for t in StreamType]})


@composability_bp.route("/composability/types/links", methods=["GET"])
def get_link_types():
    """
    Get supported link types.

    Returns:
        List of link types
    """
    from data_composability import LinkType

    return jsonify({"types": [t.value for t in LinkType]})


@composability_bp.route("/composability/types/schemas", methods=["GET"])
def get_schema_types():
    """
    Get supported schema types.

    Returns:
        List of schema types
    """
    from data_composability import SchemaType

    return jsonify({"types": [t.value for t in SchemaType]})
