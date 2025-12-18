# NatLangChain API Documentation

## Overview

The NatLangChain API provides RESTful endpoints for Agent OS (and other systems) to interact with the natural language blockchain. This API enables:

- **Pushing** natural language entries to the blockchain
- **Pulling** entries, blocks, and narratives from the blockchain
- **Validating** entries using LLM-powered "Proof of Understanding"
- **Mining** blocks from pending entries
- **Querying** the blockchain by author, intent, or other criteria

Base URL: `http://localhost:5000` (configurable via PORT environment variable)

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the server
python run_server.py
```

### 2. Basic Usage

```bash
# Check server health
curl http://localhost:5000/health

# Add an entry
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Alice transfers ownership of the vintage 1967 Mustang to Bob for $25,000.",
    "author": "alice",
    "intent": "Transfer vehicle ownership",
    "auto_mine": true
  }'

# Get the narrative
curl http://localhost:5000/chain/narrative
```

## API Endpoints

### Health & Status

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "NatLangChain API",
  "llm_validation_available": true,
  "blocks": 1,
  "pending_entries": 0
}
```

#### `GET /stats`

Get blockchain statistics.

**Response:**
```json
{
  "total_blocks": 5,
  "total_entries": 12,
  "pending_entries": 2,
  "unique_authors": 4,
  "validated_entries": 10,
  "chain_valid": true,
  "latest_block_hash": "000abc123...",
  "llm_validation_enabled": true
}
```

---

### Writing to the Blockchain (Push)

#### `POST /entry`

Add a new natural language entry to the blockchain.

**Request Body:**
```json
{
  "content": "Natural language description of the transaction/event",
  "author": "identifier of the creator",
  "intent": "brief summary of purpose",
  "metadata": {},
  "validate": true,
  "auto_mine": false,
  "multi_validator": false
}
```

**Fields:**
- `content` (required): The natural language prose describing the transaction/event
- `author` (required): Identifier of the entry creator
- `intent` (required): Brief summary of the entry's purpose
- `metadata` (optional): Additional structured data
- `validate` (optional, default true): Whether to validate the entry
- `auto_mine` (optional, default false): Whether to immediately mine a block
- `multi_validator` (optional, default false): Use multi-validator consensus

**Response:**
```json
{
  "status": "success",
  "entry": {
    "status": "pending",
    "message": "Entry added to pending queue",
    "entry": {
      "content": "...",
      "author": "alice",
      "intent": "...",
      "timestamp": "2024-01-15T10:30:00",
      "validation_status": "valid",
      "validation_paraphrases": ["..."]
    }
  },
  "validation": {
    "symbolic_validation": {
      "valid": true,
      "issues": []
    },
    "llm_validation": {
      "status": "success",
      "validation": {
        "paraphrase": "...",
        "intent_match": true,
        "ambiguities": [],
        "adversarial_indicators": [],
        "decision": "VALID",
        "reasoning": "..."
      }
    },
    "overall_decision": "VALID"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{
    "content": "The board of directors voted unanimously to approve the merger with TechCorp, effective Q2 2024.",
    "author": "board_secretary",
    "intent": "Record board decision",
    "metadata": {
      "meeting_id": "BD-2024-001",
      "vote": "unanimous"
    },
    "validate": true,
    "auto_mine": true
  }'
```

#### `POST /entry/validate`

Validate an entry without adding it to the blockchain (dry run).

**Request Body:**
```json
{
  "content": "content to validate",
  "author": "author identifier",
  "intent": "intent description",
  "multi_validator": false
}
```

**Response:**
```json
{
  "symbolic_validation": {
    "valid": true,
    "issues": []
  },
  "llm_validation": {
    "status": "success",
    "validation": {
      "paraphrase": "The validator's understanding of the content",
      "intent_match": true,
      "ambiguities": [],
      "adversarial_indicators": [],
      "decision": "VALID",
      "reasoning": "Clear and unambiguous entry"
    }
  },
  "overall_decision": "VALID"
}
```

#### `POST /mine`

Mine pending entries into a new block.

**Request Body (optional):**
```json
{
  "difficulty": 2
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Block mined successfully",
  "block": {
    "index": 1,
    "timestamp": 1705320000.0,
    "entries": [...],
    "previous_hash": "abc123...",
    "nonce": 42,
    "hash": "000def456..."
  }
}
```

---

### Reading from the Blockchain (Pull)

#### `GET /chain`

Get the entire blockchain.

**Response:**
```json
{
  "length": 5,
  "chain": {
    "chain": [...],
    "pending_entries": [...]
  },
  "valid": true
}
```

#### `GET /chain/narrative`

Get the full narrative history as human-readable text.

**This is a key feature:** Returns the entire ledger as readable prose.

**Response:** Plain text narrative

```
=== NatLangChain Narrative History ===

--- Block 0 ---
Hash: abc123...
Timestamp: 2024-01-15T10:00:00
Previous Hash: 0

Entry 1:
  Author: system
  Intent: Initialize the NatLangChain
  Time: 2024-01-15T10:00:00
  Status: validated
  Content:
    This is the genesis block of the NatLangChain...

--- Block 1 ---
...
```

#### `GET /block/<index>`

Get a specific block by index.

**Parameters:**
- `index`: Block index (integer)

**Response:**
```json
{
  "index": 1,
  "timestamp": 1705320000.0,
  "entries": [...],
  "previous_hash": "abc123...",
  "nonce": 42,
  "hash": "000def456..."
}
```

#### `GET /entries/author/<author>`

Get all entries by a specific author.

**Parameters:**
- `author`: Author identifier (string)

**Response:**
```json
{
  "author": "alice",
  "count": 3,
  "entries": [
    {
      "block_index": 1,
      "block_hash": "000abc...",
      "entry": {
        "content": "...",
        "author": "alice",
        "intent": "...",
        "timestamp": "...",
        "validation_status": "valid"
      }
    }
  ]
}
```

#### `GET /entries/search?intent=<keyword>`

Search for entries by intent keyword.

**Query Parameters:**
- `intent`: Keyword to search for in intent field

**Response:**
```json
{
  "keyword": "transfer",
  "count": 2,
  "entries": [...]
}
```

#### `GET /pending`

Get all pending entries awaiting mining.

**Response:**
```json
{
  "count": 2,
  "entries": [
    {
      "content": "...",
      "author": "...",
      "intent": "...",
      "timestamp": "...",
      "validation_status": "pending"
    }
  ]
}
```

#### `GET /validate/chain`

Validate the entire blockchain for integrity.

**Response:**
```json
{
  "valid": true,
  "blocks": 5,
  "message": "Blockchain is valid"
}
```

---

## Agent OS Integration Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:5000"

# Push information to the blockchain
def push_to_chain(content, author, intent, metadata=None):
    response = requests.post(
        f"{BASE_URL}/entry",
        json={
            "content": content,
            "author": author,
            "intent": intent,
            "metadata": metadata or {},
            "validate": True,
            "auto_mine": True
        }
    )
    return response.json()

# Pull information from the blockchain
def pull_from_chain(author=None):
    if author:
        response = requests.get(f"{BASE_URL}/entries/author/{author}")
    else:
        response = requests.get(f"{BASE_URL}/chain")
    return response.json()

# Example usage
result = push_to_chain(
    content="Agent OS completed task #1234 successfully at 10:30 AM.",
    author="agent_os",
    intent="Record task completion",
    metadata={"task_id": 1234, "status": "completed"}
)

print(f"Entry added: {result['status']}")

# Retrieve all Agent OS entries
entries = pull_from_chain(author="agent_os")
print(f"Found {entries['count']} entries from Agent OS")
```

### JavaScript Example

```javascript
const BASE_URL = 'http://localhost:5000';

// Push information to the blockchain
async function pushToChain(content, author, intent, metadata = {}) {
  const response = await fetch(`${BASE_URL}/entry`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content,
      author,
      intent,
      metadata,
      validate: true,
      auto_mine: true
    })
  });
  return await response.json();
}

// Pull information from the blockchain
async function pullFromChain(author = null) {
  const url = author
    ? `${BASE_URL}/entries/author/${author}`
    : `${BASE_URL}/chain`;

  const response = await fetch(url);
  return await response.json();
}

// Example usage
const result = await pushToChain(
  'Agent OS completed task #1234 successfully at 10:30 AM.',
  'agent_os',
  'Record task completion',
  { task_id: 1234, status: 'completed' }
);

console.log(`Entry added: ${result.status}`);
```

### cURL Example

```bash
# Push to blockchain
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Agent OS initialized successfully with 8 active modules.",
    "author": "agent_os",
    "intent": "System initialization log",
    "metadata": {"modules": 8},
    "auto_mine": true
  }'

# Pull from blockchain
curl http://localhost:5000/entries/author/agent_os

# Get narrative
curl http://localhost:5000/chain/narrative
```

---

## Validation: Proof of Understanding

The NatLangChain uses LLM-powered validation to ensure entries are understood correctly.

### Validation Decisions

- `VALID`: Entry is clear and matches stated intent
- `NEEDS_CLARIFICATION`: Entry has ambiguities that need resolution
- `INVALID`: Entry fails validation (suspicious patterns, mismatched intent)
- `ERROR`: Validation error occurred

### Multi-Validator Consensus

For critical entries, use multi-validator consensus:

```json
{
  "content": "...",
  "author": "...",
  "intent": "...",
  "multi_validator": true
}
```

This simulates multiple validator nodes achieving consensus through "Proof of Understanding."

---

## Error Handling

### Common Error Responses

**400 Bad Request**
```json
{
  "error": "Missing required fields",
  "required": ["content", "author", "intent"]
}
```

**404 Not Found**
```json
{
  "error": "Block not found",
  "valid_range": "0-4"
}
```

**503 Service Unavailable**
```json
{
  "error": "LLM validation not available",
  "reason": "ANTHROPIC_API_KEY not configured"
}
```

---

## Configuration

### Environment Variables

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key_here
PORT=5000
HOST=0.0.0.0
CHAIN_DATA_FILE=chain_data.json
```

### Running in Production

For production deployment:

1. Use a production-grade WSGI server (e.g., Gunicorn)
2. Set up proper authentication/authorization
3. Configure HTTPS
4. Implement rate limiting
5. Set up monitoring and logging

Example with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 src.api:app
```

---

## Persistence

The blockchain is automatically saved to `chain_data.json` (configurable) after:
- Mining a new block
- Any modification to the chain

On startup, the API loads the existing blockchain from this file.

---

## Testing

Run the test suite:

```bash
python tests/test_blockchain.py
```

---

## Key Concepts

### Natural Language as Substrate

Unlike traditional blockchains where transactions are opaque bytecode, NatLangChain entries are human-readable prose:

```
"Alice transfers ownership of the vintage 1967 Mustang to Bob for $25,000."
```

vs. traditional:

```
0x7b226f776e6572223a22416c696365222c22616d6f756e74223a32353030307d
```

### Proof of Understanding

Validators don't just verify cryptographic signatures—they demonstrate comprehension by paraphrasing entries and detecting ambiguities.

### Auditability

The entire blockchain can be read as a narrative (`/chain/narrative`), making it auditable by non-technical stakeholders.

---

## Limitations & Future Work

**Current Implementation:**
- Single-node (not distributed)
- Simple proof-of-work (demonstration only)
- Synchronous LLM validation
- File-based persistence

**Future Enhancements:**
- P2P networking for distributed nodes
- Advanced consensus algorithms
- Asynchronous validation pipeline
- Database backend (PostgreSQL, etc.)
- Multi-language support
- Hybrid symbolic-linguistic validation
- Smart contracts in natural language

---

## Support

For issues and feature requests, see the main README.md and project documentation.
