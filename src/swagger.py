"""
OpenAPI/Swagger Documentation for NatLangChain API.

This module provides comprehensive API documentation using OpenAPI 3.0 specification.
Access the interactive documentation at /docs (Swagger UI) or /openapi.json (raw spec).
"""

import os
from flask import Blueprint, jsonify, current_app

# OpenAPI 3.0 Specification
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "NatLangChain API",
        "description": """
# NatLangChain - Natural Language Blockchain Platform

NatLangChain is a blockchain platform that uses natural language for entries,
semantic validation, and human-readable dispute resolution.

## Features

- **Natural Language Entries**: Store and validate natural language content on-chain
- **Semantic Search**: Find entries using semantic similarity
- **Dispute Resolution**: Built-in escalation and resolution mechanisms
- **FIDO2 Authentication**: Hardware security key support
- **Zero-Knowledge Proofs**: Privacy-preserving identity verification
- **Mobile Support**: Edge inference and offline sync capabilities

## Authentication

Most write endpoints require API key authentication via the `X-API-Key` header.

```
X-API-Key: your-api-key-here
```

Set the API key via the `NATLANGCHAIN_API_KEY` environment variable.

## Rate Limiting

- Default: 100 requests per 60 seconds per client IP
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW` env vars

## Error Responses

All errors follow this format:
```json
{
  "error": "Error description",
  "reason": "Additional context (optional)",
  "hint": "Suggestions for fixing (optional)"
}
```
        """,
        "version": "0.1.0-alpha",
        "contact": {
            "name": "NatLangChain",
            "url": "https://github.com/kase1111-hash/NatLangChain"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {
            "url": "/",
            "description": "Current server"
        },
        {
            "url": "https://api.natlangchain.io",
            "description": "Production server"
        },
        {
            "url": "https://staging.natlangchain.io",
            "description": "Staging server"
        }
    ],
    "tags": [
        {"name": "Health", "description": "Health checks and monitoring"},
        {"name": "Blockchain", "description": "Core blockchain operations"},
        {"name": "Entries", "description": "Entry management"},
        {"name": "Search", "description": "Semantic search and drift detection"},
        {"name": "Contracts", "description": "Contract parsing and matching"},
        {"name": "Disputes", "description": "Dispute filing and resolution"},
        {"name": "Forks", "description": "Escalation forks and proposals"},
        {"name": "Treasury", "description": "Treasury and subsidy management"},
        {"name": "Burn", "description": "Observance burn operations"},
        {"name": "Harassment", "description": "Anti-harassment mechanisms"},
        {"name": "FIDO2", "description": "FIDO2/WebAuthn authentication"},
        {"name": "Zero-Knowledge", "description": "ZK proofs and privacy"},
        {"name": "Negotiation", "description": "Negotiation sessions"},
        {"name": "Market", "description": "Market pricing and analysis"},
        {"name": "Mobile", "description": "Mobile device and edge computing"},
        {"name": "Chat", "description": "LLM chat interface"},
        {"name": "P2P", "description": "Peer-to-peer networking"},
        {"name": "Metrics", "description": "Prometheus metrics"},
        {"name": "Help", "description": "API documentation and NCIPs"}
    ],
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for authentication"
            }
        },
        "schemas": {
            # Common Response Schemas
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "data": {"type": "object"},
                    "timestamp": {"type": "integer", "example": 1704067200}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Invalid request"},
                    "reason": {"type": "string", "example": "Missing required field"},
                    "hint": {"type": "string", "example": "Include 'content' in request body"}
                },
                "required": ["error"]
            },
            "HealthStatus": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                    "chain_length": {"type": "integer"},
                    "chain_valid": {"type": "boolean"},
                    "pending_entries": {"type": "integer"},
                    "uptime_seconds": {"type": "number"}
                }
            },
            # Entry Schemas
            "Entry": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Natural language content",
                        "maxLength": 51200
                    },
                    "author": {
                        "type": "string",
                        "description": "Author identifier",
                        "maxLength": 500
                    },
                    "intent": {
                        "type": "string",
                        "description": "Brief summary of intent",
                        "maxLength": 2048
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata"
                    },
                    "timestamp": {"type": "number"},
                    "hash": {"type": "string"}
                },
                "required": ["content", "author"]
            },
            "EntryCreate": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Natural language content (max 50KB)",
                        "maxLength": 51200
                    },
                    "author": {
                        "type": "string",
                        "description": "Author identifier",
                        "maxLength": 500
                    },
                    "intent": {
                        "type": "string",
                        "description": "Brief summary",
                        "maxLength": 2048
                    },
                    "metadata": {"type": "object"},
                    "validate": {
                        "type": "boolean",
                        "default": True,
                        "description": "Validate entry before adding"
                    },
                    "auto_mine": {
                        "type": "boolean",
                        "default": False,
                        "description": "Automatically mine after adding"
                    }
                },
                "required": ["content", "author"]
            },
            # Block Schemas
            "Block": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "timestamp": {"type": "number"},
                    "entries": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Entry"}
                    },
                    "previous_hash": {"type": "string"},
                    "hash": {"type": "string"},
                    "nonce": {"type": "integer"}
                }
            },
            "Chain": {
                "type": "object",
                "properties": {
                    "chain": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Block"}
                    },
                    "length": {"type": "integer"},
                    "valid": {"type": "boolean"}
                }
            },
            # Search Schemas
            "SemanticSearchRequest": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of results to return"
                    },
                    "threshold": {
                        "type": "number",
                        "default": 0.5,
                        "description": "Minimum similarity threshold (0-1)"
                    }
                },
                "required": ["query"]
            },
            "SearchResult": {
                "type": "object",
                "properties": {
                    "entry": {"$ref": "#/components/schemas/Entry"},
                    "score": {"type": "number", "description": "Similarity score"},
                    "block_index": {"type": "integer"},
                    "entry_index": {"type": "integer"}
                }
            },
            # Contract Schemas
            "ContractParseRequest": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Contract text to parse"
                    }
                },
                "required": ["text"]
            },
            "Contract": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "parties": {"type": "array", "items": {"type": "string"}},
                    "terms": {"type": "array", "items": {"type": "object"}},
                    "status": {"type": "string", "enum": ["draft", "active", "completed", "disputed"]},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            },
            # Dispute Schemas
            "DisputeFileRequest": {
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string"},
                    "claimant": {"type": "string"},
                    "respondent": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["contract_id", "claimant", "description"]
            },
            "Dispute": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "contract_id": {"type": "string"},
                    "claimant": {"type": "string"},
                    "respondent": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["filed", "evidence", "escalated", "resolved"]
                    },
                    "resolution": {"type": "object"},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            },
            # FIDO2 Schemas
            "FIDO2RegisterBegin": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "user_name": {"type": "string"},
                    "display_name": {"type": "string"}
                },
                "required": ["user_id", "user_name"]
            },
            "FIDO2Credential": {
                "type": "object",
                "properties": {
                    "credential_id": {"type": "string"},
                    "public_key": {"type": "string"},
                    "sign_count": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            },
            # ZK Schemas
            "ZKIdentityCommitment": {
                "type": "object",
                "properties": {
                    "identity_secret": {"type": "string"},
                    "nullifier": {"type": "string"}
                },
                "required": ["identity_secret"]
            },
            "ZKProof": {
                "type": "object",
                "properties": {
                    "proof_id": {"type": "string"},
                    "commitment": {"type": "string"},
                    "nullifier_hash": {"type": "string"},
                    "verified": {"type": "boolean"}
                }
            },
            # Mobile Schemas
            "DeviceRegister": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string"},
                    "platform": {"type": "string", "enum": ["ios", "android", "web"]},
                    "capabilities": {"type": "object"}
                },
                "required": ["device_id", "platform"]
            },
            "EdgeInferenceRequest": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string"},
                    "input_data": {"type": "object"},
                    "options": {"type": "object"}
                },
                "required": ["model_id", "input_data"]
            },
            # Pagination
            "PaginationParams": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "maximum": 100
                    },
                    "offset": {
                        "type": "integer",
                        "default": 0,
                        "maximum": 100000
                    }
                }
            }
        },
        "responses": {
            "Unauthorized": {
                "description": "Missing or invalid API key",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {"error": "API key required"}
                    }
                }
            },
            "Forbidden": {
                "description": "Invalid API key",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {"error": "Invalid API key"}
                    }
                }
            },
            "NotFound": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {"error": "Resource not found"}
                    }
                }
            },
            "RateLimited": {
                "description": "Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Rate limit exceeded",
                            "hint": "Try again in 60 seconds"
                        }
                    }
                }
            },
            "ServiceUnavailable": {
                "description": "Feature not available",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {"error": "Feature not initialized"}
                    }
                }
            }
        }
    },
    "paths": {
        # =====================================================================
        # Health Endpoints
        # =====================================================================
        "/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Basic health check",
                "description": "Returns basic health status of the API",
                "operationId": "getHealth",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthStatus"}
                            }
                        }
                    }
                }
            }
        },
        "/health/live": {
            "get": {
                "tags": ["Health"],
                "summary": "Kubernetes liveness probe",
                "description": "Returns 200 if the service is alive",
                "operationId": "getLiveness",
                "responses": {
                    "200": {
                        "description": "Service is alive",
                        "content": {
                            "application/json": {
                                "example": {"status": "alive"}
                            }
                        }
                    }
                }
            }
        },
        "/health/ready": {
            "get": {
                "tags": ["Health"],
                "summary": "Kubernetes readiness probe",
                "description": "Returns 200 if the service is ready to accept traffic",
                "operationId": "getReadiness",
                "responses": {
                    "200": {
                        "description": "Service is ready",
                        "content": {
                            "application/json": {
                                "example": {"status": "ready", "checks": {}}
                            }
                        }
                    },
                    "503": {"$ref": "#/components/responses/ServiceUnavailable"}
                }
            }
        },
        "/health/detailed": {
            "get": {
                "tags": ["Health"],
                "summary": "Detailed health check",
                "description": "Returns detailed health information including all subsystems",
                "operationId": "getDetailedHealth",
                "responses": {
                    "200": {
                        "description": "Detailed health status",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "checks": {"type": "object"},
                                        "chain": {"type": "object"},
                                        "features": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Blockchain Endpoints
        # =====================================================================
        "/chain": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Get the full blockchain",
                "description": "Returns the entire blockchain including all blocks and entries",
                "operationId": "getChain",
                "responses": {
                    "200": {
                        "description": "Full blockchain",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Chain"}
                            }
                        }
                    }
                }
            }
        },
        "/chain/narrative": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Get chain as narrative text",
                "description": "Returns the blockchain content as human-readable narrative",
                "operationId": "getChainNarrative",
                "responses": {
                    "200": {
                        "description": "Narrative text",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"}
                            }
                        }
                    }
                }
            }
        },
        "/validate/chain": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Validate the blockchain",
                "description": "Validates the entire blockchain integrity",
                "operationId": "validateChain",
                "responses": {
                    "200": {
                        "description": "Validation result",
                        "content": {
                            "application/json": {
                                "example": {"valid": True, "blocks_checked": 10}
                            }
                        }
                    }
                }
            }
        },
        "/stats": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Get blockchain statistics",
                "description": "Returns statistics about the blockchain",
                "operationId": "getStats",
                "responses": {
                    "200": {
                        "description": "Blockchain statistics",
                        "content": {
                            "application/json": {
                                "example": {
                                    "total_blocks": 100,
                                    "total_entries": 500,
                                    "pending_entries": 5
                                }
                            }
                        }
                    }
                }
            }
        },
        "/block/{index}": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Get a specific block",
                "description": "Returns a block by its index",
                "operationId": "getBlock",
                "parameters": [
                    {
                        "name": "index",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Block index"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Block data",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Block"}
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFound"}
                }
            }
        },
        "/block/latest": {
            "get": {
                "tags": ["Blockchain"],
                "summary": "Get the latest block",
                "description": "Returns the most recently mined block",
                "operationId": "getLatestBlock",
                "responses": {
                    "200": {
                        "description": "Latest block",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Block"}
                            }
                        }
                    }
                }
            }
        },
        "/mine": {
            "post": {
                "tags": ["Blockchain"],
                "summary": "Mine pending entries",
                "description": "Mines all pending entries into a new block",
                "operationId": "mineBlock",
                "security": [{"ApiKeyAuth": []}],
                "responses": {
                    "200": {
                        "description": "Mining result",
                        "content": {
                            "application/json": {
                                "example": {
                                    "message": "Block mined successfully",
                                    "block_index": 101,
                                    "entries_mined": 5
                                }
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        # =====================================================================
        # Entry Endpoints
        # =====================================================================
        "/entry": {
            "post": {
                "tags": ["Entries"],
                "summary": "Add a new entry",
                "description": "Adds a new natural language entry to the pending queue",
                "operationId": "createEntry",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EntryCreate"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Entry created",
                        "content": {
                            "application/json": {
                                "example": {
                                    "message": "Entry added",
                                    "entry_hash": "abc123...",
                                    "pending_count": 5
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid entry",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/entry/validate": {
            "post": {
                "tags": ["Entries"],
                "summary": "Validate an entry without adding",
                "description": "Validates an entry against the chain without adding it",
                "operationId": "validateEntry",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EntryCreate"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Validation result",
                        "content": {
                            "application/json": {
                                "example": {
                                    "valid": True,
                                    "validation_details": {}
                                }
                            }
                        }
                    }
                }
            }
        },
        "/pending": {
            "get": {
                "tags": ["Entries"],
                "summary": "Get pending entries",
                "description": "Returns all entries waiting to be mined",
                "operationId": "getPendingEntries",
                "responses": {
                    "200": {
                        "description": "Pending entries",
                        "content": {
                            "application/json": {
                                "example": {
                                    "pending": [],
                                    "count": 0
                                }
                            }
                        }
                    }
                }
            }
        },
        "/entries/author/{author}": {
            "get": {
                "tags": ["Entries"],
                "summary": "Get entries by author",
                "description": "Returns all entries by a specific author",
                "operationId": "getEntriesByAuthor",
                "parameters": [
                    {
                        "name": "author",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Author identifier"
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20, "maximum": 100}
                    },
                    {
                        "name": "offset",
                        "in": "query",
                        "schema": {"type": "integer", "default": 0}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Author's entries",
                        "content": {
                            "application/json": {
                                "example": {"entries": [], "total": 0}
                            }
                        }
                    }
                }
            }
        },
        "/entries/search": {
            "get": {
                "tags": ["Entries"],
                "summary": "Search entries by keyword",
                "description": "Simple keyword search across entries",
                "operationId": "searchEntries",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Search query"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {
                                "example": {"results": [], "count": 0}
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Search Endpoints
        # =====================================================================
        "/search/semantic": {
            "post": {
                "tags": ["Search"],
                "summary": "Semantic search",
                "description": "Search entries using semantic similarity",
                "operationId": "semanticSearch",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SemanticSearchRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "results": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/SearchResult"}
                                        },
                                        "query": {"type": "string"},
                                        "count": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "503": {"$ref": "#/components/responses/ServiceUnavailable"}
                }
            }
        },
        "/search/similar": {
            "post": {
                "tags": ["Search"],
                "summary": "Find similar entries",
                "description": "Find entries similar to a given text",
                "operationId": "findSimilar",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "top_k": {"type": "integer", "default": 5}
                                },
                                "required": ["text"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Similar entries",
                        "content": {
                            "application/json": {
                                "example": {"similar": [], "count": 0}
                            }
                        }
                    }
                }
            }
        },
        "/drift/check": {
            "post": {
                "tags": ["Search"],
                "summary": "Check semantic drift",
                "description": "Analyze semantic drift across the chain",
                "operationId": "checkDrift",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "reference_text": {"type": "string"},
                                    "threshold": {"type": "number", "default": 0.3}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Drift analysis",
                        "content": {
                            "application/json": {
                                "example": {
                                    "drift_detected": False,
                                    "drift_score": 0.15,
                                    "analysis": {}
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Contract Endpoints
        # =====================================================================
        "/contract/parse": {
            "post": {
                "tags": ["Contracts"],
                "summary": "Parse contract text",
                "description": "Parse natural language contract into structured terms",
                "operationId": "parseContract",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContractParseRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Parsed contract",
                        "content": {
                            "application/json": {
                                "example": {
                                    "parties": [],
                                    "terms": [],
                                    "obligations": []
                                }
                            }
                        }
                    }
                }
            }
        },
        "/contract/list": {
            "get": {
                "tags": ["Contracts"],
                "summary": "List contracts",
                "description": "List all contracts with optional filtering",
                "operationId": "listContracts",
                "parameters": [
                    {"name": "status", "in": "query", "schema": {"type": "string"}},
                    {"name": "party", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}}
                ],
                "responses": {
                    "200": {
                        "description": "Contract list",
                        "content": {
                            "application/json": {
                                "example": {"contracts": [], "total": 0}
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Dispute Endpoints
        # =====================================================================
        "/dispute/file": {
            "post": {
                "tags": ["Disputes"],
                "summary": "File a dispute",
                "description": "File a new dispute against a contract",
                "operationId": "fileDispute",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DisputeFileRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Dispute filed",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Dispute"}
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        "/dispute/list": {
            "get": {
                "tags": ["Disputes"],
                "summary": "List disputes",
                "description": "List all disputes with optional filtering",
                "operationId": "listDisputes",
                "parameters": [
                    {"name": "status", "in": "query", "schema": {"type": "string"}},
                    {"name": "party", "in": "query", "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {
                        "description": "Dispute list",
                        "content": {
                            "application/json": {
                                "example": {"disputes": [], "total": 0}
                            }
                        }
                    }
                }
            }
        },
        "/dispute/{dispute_id}": {
            "get": {
                "tags": ["Disputes"],
                "summary": "Get dispute details",
                "description": "Get full details of a specific dispute",
                "operationId": "getDispute",
                "parameters": [
                    {
                        "name": "dispute_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Dispute details",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Dispute"}
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFound"}
                }
            }
        },
        "/dispute/{dispute_id}/resolve": {
            "post": {
                "tags": ["Disputes"],
                "summary": "Resolve a dispute",
                "description": "Submit a resolution for a dispute",
                "operationId": "resolveDispute",
                "security": [{"ApiKeyAuth": []}],
                "parameters": [
                    {
                        "name": "dispute_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "resolution": {"type": "string"},
                                    "ruling": {"type": "object"}
                                },
                                "required": ["resolution"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Dispute resolved",
                        "content": {
                            "application/json": {
                                "example": {"status": "resolved", "resolution": {}}
                            }
                        }
                    },
                    "401": {"$ref": "#/components/responses/Unauthorized"}
                }
            }
        },
        # =====================================================================
        # Metrics Endpoints
        # =====================================================================
        "/metrics": {
            "get": {
                "tags": ["Metrics"],
                "summary": "Prometheus metrics",
                "description": "Returns metrics in Prometheus text format",
                "operationId": "getMetrics",
                "responses": {
                    "200": {
                        "description": "Prometheus metrics",
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"},
                                "example": "# HELP http_requests_total Total HTTP requests\nhttp_requests_total{status=\"200\"} 1234"
                            }
                        }
                    }
                }
            }
        },
        "/metrics/json": {
            "get": {
                "tags": ["Metrics"],
                "summary": "JSON metrics",
                "description": "Returns metrics in JSON format",
                "operationId": "getMetricsJson",
                "responses": {
                    "200": {
                        "description": "JSON metrics",
                        "content": {
                            "application/json": {
                                "example": {
                                    "http_requests_total": 1234,
                                    "chain_blocks": 100
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Mobile Endpoints
        # =====================================================================
        "/mobile/device/register": {
            "post": {
                "tags": ["Mobile"],
                "summary": "Register mobile device",
                "description": "Register a mobile device for edge computing",
                "operationId": "registerDevice",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DeviceRegister"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Device registered",
                        "content": {
                            "application/json": {
                                "example": {
                                    "device_id": "abc123",
                                    "registered": True
                                }
                            }
                        }
                    }
                }
            }
        },
        "/mobile/edge/inference": {
            "post": {
                "tags": ["Mobile"],
                "summary": "Run edge inference",
                "description": "Run ML inference on edge device",
                "operationId": "edgeInference",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EdgeInferenceRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Inference result",
                        "content": {
                            "application/json": {
                                "example": {
                                    "result": {},
                                    "inference_time_ms": 50
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # FIDO2 Endpoints
        # =====================================================================
        "/fido2/register/begin": {
            "post": {
                "tags": ["FIDO2"],
                "summary": "Begin FIDO2 registration",
                "description": "Start the FIDO2 credential registration process",
                "operationId": "fido2RegisterBegin",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/FIDO2RegisterBegin"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Registration options",
                        "content": {
                            "application/json": {
                                "example": {
                                    "challenge": "base64...",
                                    "rp": {"name": "NatLangChain"},
                                    "user": {}
                                }
                            }
                        }
                    }
                }
            }
        },
        "/fido2/authenticate/begin": {
            "post": {
                "tags": ["FIDO2"],
                "summary": "Begin FIDO2 authentication",
                "description": "Start the FIDO2 authentication process",
                "operationId": "fido2AuthBegin",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"}
                                },
                                "required": ["user_id"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Authentication options",
                        "content": {
                            "application/json": {
                                "example": {
                                    "challenge": "base64...",
                                    "allowCredentials": []
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Zero-Knowledge Endpoints
        # =====================================================================
        "/zk/identity/commitment": {
            "post": {
                "tags": ["Zero-Knowledge"],
                "summary": "Create identity commitment",
                "description": "Create a ZK identity commitment",
                "operationId": "createIdentityCommitment",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ZKIdentityCommitment"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Commitment created",
                        "content": {
                            "application/json": {
                                "example": {
                                    "commitment": "0x...",
                                    "nullifier": "0x..."
                                }
                            }
                        }
                    }
                }
            }
        },
        "/zk/identity/verify": {
            "post": {
                "tags": ["Zero-Knowledge"],
                "summary": "Verify identity proof",
                "description": "Verify a ZK identity proof",
                "operationId": "verifyIdentityProof",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "proof_id": {"type": "string"},
                                    "proof_data": {"type": "object"}
                                },
                                "required": ["proof_id"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Verification result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ZKProof"}
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Chat Endpoints
        # =====================================================================
        "/chat/message": {
            "post": {
                "tags": ["Chat"],
                "summary": "Send chat message",
                "description": "Send a message to the LLM chat interface",
                "operationId": "sendChatMessage",
                "security": [{"ApiKeyAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"},
                                    "context": {"type": "object"}
                                },
                                "required": ["message"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Chat response",
                        "content": {
                            "application/json": {
                                "example": {
                                    "response": "Here's my answer...",
                                    "sources": []
                                }
                            }
                        }
                    }
                }
            }
        },
        "/chat/status": {
            "get": {
                "tags": ["Chat"],
                "summary": "Get chat status",
                "description": "Get the status of the chat system",
                "operationId": "getChatStatus",
                "responses": {
                    "200": {
                        "description": "Chat status",
                        "content": {
                            "application/json": {
                                "example": {
                                    "available": True,
                                    "model": "claude-3",
                                    "context_window": 100000
                                }
                            }
                        }
                    }
                }
            }
        },
        # =====================================================================
        # Help Endpoints
        # =====================================================================
        "/api/help/overview": {
            "get": {
                "tags": ["Help"],
                "summary": "API overview",
                "description": "Get an overview of the API capabilities",
                "operationId": "getApiOverview",
                "responses": {
                    "200": {
                        "description": "API overview",
                        "content": {
                            "application/json": {
                                "example": {
                                    "name": "NatLangChain API",
                                    "version": "1.0.0",
                                    "endpoints": 212
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/help/ncips": {
            "get": {
                "tags": ["Help"],
                "summary": "List NCIPs",
                "description": "List all NatLangChain Improvement Proposals",
                "operationId": "listNcips",
                "responses": {
                    "200": {
                        "description": "NCIP list",
                        "content": {
                            "application/json": {
                                "example": {"ncips": [], "total": 0}
                            }
                        }
                    }
                }
            }
        }
    }
}


def create_swagger_blueprint():
    """Create the Swagger UI blueprint."""
    swagger_bp = Blueprint('swagger', __name__)

    @swagger_bp.route('/openapi.json')
    def openapi_spec():
        """Return the OpenAPI specification."""
        return jsonify(OPENAPI_SPEC)

    @swagger_bp.route('/openapi.yaml')
    def openapi_yaml():
        """Return the OpenAPI specification as YAML."""
        import json
        try:
            import yaml
            return yaml.dump(OPENAPI_SPEC, default_flow_style=False), 200, {'Content-Type': 'text/yaml'}
        except ImportError:
            # Fallback to JSON if PyYAML not available
            return jsonify(OPENAPI_SPEC)

    return swagger_bp


def init_swagger(app):
    """Initialize Swagger UI for the Flask app."""
    try:
        from flask_swagger_ui import get_swaggerui_blueprint

        SWAGGER_URL = '/docs'
        API_URL = '/openapi.json'

        swaggerui_blueprint = get_swaggerui_blueprint(
            SWAGGER_URL,
            API_URL,
            config={
                'app_name': "NatLangChain API",
                'layout': 'BaseLayout',
                'deepLinking': True,
                'displayRequestDuration': True,
                'filter': True,
                'showExtensions': True,
                'showCommonExtensions': True,
                'tryItOutEnabled': True,
                'persistAuthorization': True,
                'defaultModelsExpandDepth': 2,
                'defaultModelExpandDepth': 2,
                'docExpansion': 'list',
                'syntaxHighlight.theme': 'monokai'
            }
        )

        # Register blueprints
        app.register_blueprint(create_swagger_blueprint())
        app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

        print(f"Swagger UI available at {SWAGGER_URL}")
        return True

    except ImportError as e:
        print(f"Warning: flask-swagger-ui not installed. Swagger UI disabled. ({e})")
        # Still register the OpenAPI spec endpoint
        app.register_blueprint(create_swagger_blueprint())
        return False


# Export for use in api.py
__all__ = ['init_swagger', 'OPENAPI_SPEC', 'create_swagger_blueprint']
