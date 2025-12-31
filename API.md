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

---

## Advanced Features

The NatLangChain API now includes three integrated advanced features for enhanced validation, search, and security.

### Semantic Search

Semantic search uses embeddings to find entries by meaning, not just keywords.

#### `POST /search/semantic`

Perform semantic search across all blockchain entries.

**Request Body:**
```json
{
  "query": "natural language search query",
  "top_k": 5,
  "min_score": 0.0,
  "field": "content" | "intent" | "both"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vehicle ownership transfers",
    "top_k": 5,
    "field": "both"
  }'
```

**Response:**
```json
{
  "query": "vehicle ownership transfers",
  "field": "both",
  "count": 2,
  "results": [
    {
      "score": 0.8234,
      "entry": {
        "content": "Alice transfers ownership of the vintage car...",
        "author": "alice",
        "intent": "Transfer vehicle ownership",
        "block_index": 1,
        "block_hash": "000abc..."
      }
    }
  ]
}
```

**Key Feature:** Semantic search finds "car sales" even when the text says "automobile transfers" because it understands meaning, not just words.

#### `POST /search/similar`

Find entries similar to given content (useful for detecting duplicates).

**Request Body:**
```json
{
  "content": "content to find similar entries for",
  "top_k": 5,
  "exclude_exact": true
}
```

### Semantic Drift Detection

Detect when agent execution drifts from stated on-chain intent. This is a security feature that implements a "semantic firewall" for agent systems.

#### `POST /drift/check`

Check semantic drift between canonical intent and execution log.

**Request Body:**
```json
{
  "on_chain_intent": "Maintain a neutral delta on S&P 500 via low-risk options",
  "execution_log": "Purchasing leveraged 3x call options on volatile AI startups"
}
```

**Response:**
```json
{
  "status": "success",
  "drift_analysis": {
    "score": 0.89,
    "is_violating": true,
    "reason": "Execution significantly diverges from stated low-risk strategy",
    "recommended_action": "BLOCK"
  },
  "threshold": 0.7,
  "alert": true
}
```

**Use Cases:**
- Monitor AI agents to ensure they follow their stated intentions
- Audit trails for regulatory compliance
- Circuit breakers for autonomous systems

#### `POST /drift/entry/<block_index>/<entry_index>`

Check drift for a specific blockchain entry against an execution log.

**Example:**
```bash
curl -X POST http://localhost:5000/drift/entry/1/0 \
  -H "Content-Type: application/json" \
  -d '{
    "execution_log": "Agent performed action X"
  }'
```

### Dialectic Consensus Validation

Advanced validation using debate between Skeptic and Facilitator roles. Particularly useful for financial or legal entries requiring precision.

#### `POST /validate/dialectic`

Validate entry through dialectic debate (requires ANTHROPIC_API_KEY).

**Request Body:**
```json
{
  "content": "I'll hedge some oil soon if things get crazy in the Middle East",
  "author": "trader",
  "intent": "Risk management strategy"
}
```

**Response:**
```json
{
  "status": "success",
  "method": "dialectic_consensus",
  "skeptic_perspective": {
    "concerns": ["'some oil' is vague", "'soon' lacks timeline", "'crazy' is undefined"],
    "severity": "CRITICAL",
    "recommendation": "REJECT",
    "reasoning": "Multiple ambiguous terms make entry unenforceable"
  },
  "facilitator_perspective": {
    "canonical_intent": "Trader wants to hedge oil exposure during geopolitical instability",
    "key_commitments": ["Hedge oil positions", "Respond to Middle East events"],
    "clarity_score": 0.4
  },
  "final_decision": {
    "status": "REJECT",
    "reasoning": "Skeptic's concerns are critical - vague terms make entry semantically null",
    "required_clarifications": ["Specify oil quantity", "Define timeline", "Clarify trigger conditions"]
  },
  "decision": "INVALID"
}
```

**How It Works:**
1. **Skeptic** examines for ambiguities, loopholes, and vague terms
2. **Facilitator** extracts core intent and spirit
3. **Consensus Engine** reconciles perspectives to make final decision

**Use in Entry Creation:**

You can use dialectic validation when adding entries:

```bash
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your entry content",
    "author": "author_id",
    "intent": "Entry intent",
    "validation_mode": "dialectic",
    "auto_mine": true
  }'
```

**Validation Modes:**
- `"standard"` - Default hybrid validation (symbolic + LLM)
- `"multi"` - Multi-validator consensus (3 validators)
- `"dialectic"` - Skeptic/Facilitator debate

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

**Note:** Semantic search works without an API key. Drift detection and dialectic consensus require `ANTHROPIC_API_KEY`.

---

## Complete API Reference

This section provides a comprehensive reference for all 167 API endpoints organized by category.

### Table of Contents

1. [Core Blockchain](#core-blockchain-endpoints)
2. [Semantic Search](#semantic-search-endpoints)
3. [Drift Detection](#drift-detection-endpoints)
4. [Dialectic Validation](#dialectic-validation-endpoints)
5. [Semantic Oracle](#semantic-oracle-endpoints)
6. [Live Contracts](#live-contract-endpoints)
7. [Dispute Resolution](#dispute-resolution-endpoints)
8. [Escalation Forks](#escalation-fork-endpoints)
9. [Observance Burn](#observance-burn-endpoints)
10. [Anti-Harassment](#anti-harassment-endpoints)
11. [Treasury](#treasury-endpoints)
12. [FIDO2 Authentication](#fido2-authentication-endpoints)
13. [ZK Privacy](#zk-privacy-endpoints)
14. [Negotiation Engine](#negotiation-engine-endpoints)
15. [Market Pricing](#market-pricing-endpoints)
16. [Mobile Deployment](#mobile-deployment-endpoints)

---

### Core Blockchain Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check and service status |
| GET | `/chain` | Get entire blockchain |
| GET | `/chain/narrative` | Get blockchain as human-readable narrative |
| POST | `/entry` | Submit new entry to blockchain |
| POST | `/entry/validate` | Validate entry without submitting (dry run) |
| POST | `/mine` | Mine pending entries into new block |
| GET | `/block/<index>` | Get block by index |
| GET | `/block/latest` | Get most recent block |
| GET | `/entries/author/<author>` | Get all entries by author |
| GET | `/entries/search?intent=<keyword>` | Search entries by intent keyword |
| GET | `/validate/chain` | Validate blockchain integrity |
| GET | `/pending` | Get pending entries awaiting mining |
| GET | `/stats` | Get blockchain statistics |
| GET | `/entry/frozen/<block_index>/<entry_index>` | Get frozen entry state at T0 |

---

### Semantic Search Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/search/semantic` | Semantic search across entries by meaning |
| POST | `/search/similar` | Find entries similar to given content |

---

### Drift Detection Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/drift/check` | Check semantic drift between intent and execution |
| POST | `/drift/entry/<block_index>/<entry_index>` | Check drift for specific entry |

---

### Dialectic Validation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/validate/dialectic` | Validate entry via Skeptic/Facilitator debate |

---

### Semantic Oracle Endpoints

Semantic oracles verify external events against contract intent using LLM reasoning.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/oracle/verify` | Verify if external event triggers contract condition |

**Request Body:**
```json
{
  "contract_condition": "if geopolitical instability in Middle East",
  "contract_intent": "hedge against oil price volatility",
  "event_description": "Major conflict erupts in region",
  "event_data": {}
}
```

---

### Live Contract Endpoints

Self-seeking live contracts with AI-mediated matching.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/contract/parse` | Parse natural language contract |
| POST | `/contract/match` | Find matching contracts for pending entries |
| POST | `/contract/post` | Post new contract (offer or seek) |
| GET | `/contract/list` | List all contracts with optional filters |
| POST | `/contract/respond` | Respond to contract (accept/counter/reject) |

**Contract Types:** `offer`, `seek`, `proposal`, `response`, `closure`

**Contract Statuses:** `open`, `matched`, `negotiating`, `closed`, `cancelled`

---

### Dispute Resolution Endpoints

Full dispute resolution protocol with evidence, escalation, and resolution.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/dispute/file` | File a new dispute |
| GET | `/dispute/list` | List all disputes |
| GET | `/dispute/<dispute_id>` | Get dispute details |
| POST | `/dispute/<dispute_id>/evidence` | Submit evidence to dispute |
| POST | `/dispute/<dispute_id>/escalate` | Escalate dispute to higher authority |
| POST | `/dispute/<dispute_id>/resolve` | Resolve a dispute |
| GET | `/dispute/<dispute_id>/package` | Get complete dispute package |
| GET | `/dispute/<dispute_id>/analyze` | Analyze dispute with AI |

---

### Escalation Fork Endpoints

Protocol amendment and fork escalation system.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fork/trigger` | Trigger an escalation fork |
| GET | `/fork/<fork_id>` | Get fork details |
| POST | `/fork/<fork_id>/submit-proposal` | Submit proposal to fork |
| GET | `/fork/<fork_id>/proposals` | List fork proposals |
| POST | `/fork/<fork_id>/ratify` | Ratify a fork proposal |
| POST | `/fork/<fork_id>/veto` | Veto a fork proposal |
| GET | `/fork/<fork_id>/distribution` | Get fork voting distribution |
| GET | `/fork/<fork_id>/audit` | Get fork audit trail |
| GET | `/fork/active` | List active forks |

---

### Observance Burn Endpoints

Token burn protocol for stake, penalties, and observance.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/burn/observance` | Burn tokens for observance |
| POST | `/burn/voluntary` | Voluntary token burn |
| GET | `/burn/history` | Get burn history |
| GET | `/burn/stats` | Get burn statistics |
| GET | `/burn/<tx_hash>` | Get burn transaction by hash |
| GET | `/burn/address/<address>` | Get burns for address |
| GET | `/burn/ledger` | Get full burn ledger |
| GET | `/burn/calculate-escalation` | Calculate escalation burn amount |

---

### Anti-Harassment Endpoints

Stake-based anti-harassment system with escrow and resolution.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/harassment/breach-dispute` | File harassment breach dispute |
| POST | `/harassment/match-stake` | Match harassment stake |
| POST | `/harassment/decline-stake` | Decline stake matching |
| POST | `/harassment/voluntary-request` | Request voluntary resolution |
| POST | `/harassment/respond-request` | Respond to resolution request |
| POST | `/harassment/counter-proposal` | Submit counter-proposal |
| GET | `/harassment/counter-status/<dispute_ref>/<party>` | Get counter status |
| GET | `/harassment/score/<address>` | Get harassment score |
| GET | `/harassment/escrow/<escrow_id>` | Get escrow details |
| POST | `/harassment/resolve` | Resolve harassment dispute |
| POST | `/harassment/check-timeouts` | Check for timeouts |
| GET | `/harassment/stats` | Get harassment statistics |
| GET | `/harassment/audit` | Get harassment audit trail |

---

### Treasury Endpoints

Subsidy and treasury management system.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/treasury/balance` | Get treasury balance |
| POST | `/treasury/deposit` | Deposit to treasury |
| POST | `/treasury/deposit/timeout-burn` | Deposit timeout burn |
| POST | `/treasury/deposit/counter-fee` | Deposit counter-offer fee |
| GET | `/treasury/inflows` | Get treasury inflows |
| POST | `/treasury/subsidy/request` | Request subsidy |
| POST | `/treasury/subsidy/disburse` | Disburse subsidy |
| GET | `/treasury/subsidy/<request_id>` | Get subsidy request |
| POST | `/treasury/subsidy/simulate` | Simulate subsidy |
| GET | `/treasury/participant/<address>` | Get participant info |
| GET | `/treasury/dispute/<dispute_id>/subsidized` | Check if dispute subsidized |
| GET | `/treasury/stats` | Get treasury statistics |
| GET | `/treasury/audit` | Get treasury audit trail |
| POST | `/treasury/cleanup` | Clean up expired entries |

---

### FIDO2 Authentication Endpoints

WebAuthn/FIDO2 hardware key authentication and delegation.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fido2/register/begin` | Begin FIDO2 registration |
| POST | `/fido2/register/complete` | Complete FIDO2 registration |
| POST | `/fido2/authenticate/begin` | Begin authentication |
| POST | `/fido2/authenticate/verify` | Verify authentication |
| POST | `/fido2/sign/proposal` | Sign proposal with FIDO2 |
| POST | `/fido2/sign/contract` | Sign contract with FIDO2 |
| POST | `/fido2/delegation/begin` | Begin delegation |
| POST | `/fido2/delegation/complete` | Complete delegation |
| GET | `/fido2/delegation/<delegation_id>` | Get delegation details |
| POST | `/fido2/delegation/<delegation_id>/revoke` | Revoke delegation |
| GET | `/fido2/delegation/user/<user_id>` | Get user delegations |
| POST | `/fido2/delegation/verify` | Verify delegation |
| GET | `/fido2/credentials/<user_id>` | Get user credentials |
| DELETE | `/fido2/credentials/<user_id>/<credential_id>` | Delete credential |
| GET | `/fido2/signatures/<user_id>` | Get user signatures |
| GET | `/fido2/stats` | Get FIDO2 statistics |
| GET | `/fido2/audit` | Get FIDO2 audit trail |

---

### ZK Privacy Endpoints

Zero-knowledge proof infrastructure for privacy-preserving operations.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/zk/identity/commitment` | Create identity commitment |
| POST | `/zk/identity/proof` | Generate identity proof |
| POST | `/zk/identity/verify` | Verify identity proof |
| GET | `/zk/identity/proof/<proof_id>` | Get proof details |
| POST | `/zk/viewing-key/create` | Create viewing key |
| POST | `/zk/viewing-key/share` | Share viewing key |
| POST | `/zk/viewing-key/reconstruct` | Reconstruct viewing key |
| GET | `/zk/viewing-key/<key_id>` | Get viewing key |
| POST | `/zk/batch/submit` | Submit ZK batch |
| POST | `/zk/batch/advance` | Advance batch processing |
| GET | `/zk/batch/<batch_id>` | Get batch details |
| POST | `/zk/dummy/generate` | Generate dummy proofs |
| GET | `/zk/dummy/stats` | Get dummy proof stats |
| POST | `/zk/compliance/request` | Request compliance check |
| POST | `/zk/compliance/vote` | Vote on compliance request |
| GET | `/zk/compliance/<request_id>` | Get compliance request |
| POST | `/zk/compliance/threshold-sign` | Threshold sign compliance |
| GET | `/zk/compliance/council` | Get compliance council |
| GET | `/zk/stats` | Get ZK statistics |
| GET | `/zk/audit` | Get ZK audit trail |

---

### Negotiation Engine Endpoints

Multi-party contract negotiation with clause management.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/negotiation/session` | Create negotiation session |
| POST | `/negotiation/session/<session_id>/join` | Join session |
| GET | `/negotiation/session/<session_id>` | Get session details |
| POST | `/negotiation/session/<session_id>/advance` | Advance session phase |
| POST | `/negotiation/session/<session_id>/clause` | Add clause to session |
| POST | `/negotiation/session/<session_id>/clause/<clause_id>/respond` | Respond to clause |
| GET | `/negotiation/session/<session_id>/clauses` | Get session clauses |
| POST | `/negotiation/session/<session_id>/offer` | Make offer |
| POST | `/negotiation/session/<session_id>/offer/<offer_id>/respond` | Respond to offer |
| GET | `/negotiation/session/<session_id>/offers` | Get session offers |
| POST | `/negotiation/session/<session_id>/auto-counter` | Generate auto counter-offer |
| GET | `/negotiation/session/<session_id>/strategies` | Get negotiation strategies |
| POST | `/negotiation/session/<session_id>/finalize` | Finalize negotiation |
| GET | `/negotiation/stats` | Get negotiation statistics |
| GET | `/negotiation/audit` | Get negotiation audit trail |
| GET | `/negotiation/clause-types` | Get available clause types |

---

### Market Pricing Endpoints

Fair market pricing with AI analysis and benchmarks.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/market/price/<asset>` | Get asset price |
| POST | `/market/prices` | Get multiple asset prices |
| GET | `/market/analyze/<asset>` | Analyze asset pricing |
| POST | `/market/summary` | Get market summary |
| POST | `/market/suggest-price` | Get AI price suggestion |
| POST | `/market/adjust-price` | Adjust price with factors |
| POST | `/market/counteroffer` | Generate counteroffer |
| GET | `/market/history/<asset>` | Get price history |
| GET | `/market/benchmark/<asset>` | Get price benchmark |
| POST | `/market/similar-prices` | Find similar prices |
| POST | `/market/asset` | Register new asset |
| GET | `/market/assets` | List all assets |
| GET | `/market/strategies` | Get pricing strategies |
| GET | `/market/conditions` | Get market conditions |
| GET | `/market/stats` | Get market statistics |
| GET | `/market/audit` | Get market audit trail |

---

### Mobile Deployment Endpoints

Mobile device support with edge inference and offline sync.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mobile/device/register` | Register mobile device |
| GET | `/mobile/device/<device_id>` | Get device info |
| GET | `/mobile/device/<device_id>/features` | Get device features |
| POST | `/mobile/edge/model/load` | Load edge ML model |
| POST | `/mobile/edge/inference` | Run edge inference |
| GET | `/mobile/edge/models` | List edge models |
| GET | `/mobile/edge/resources` | Get edge resources |
| POST | `/mobile/wallet/connect` | Connect mobile wallet |
| GET | `/mobile/wallet/<connection_id>` | Get wallet connection |
| POST | `/mobile/wallet/<connection_id>/disconnect` | Disconnect wallet |
| POST | `/mobile/wallet/<connection_id>/sign` | Sign with wallet |
| GET | `/mobile/wallet/list` | List wallet connections |
| POST | `/mobile/offline/state/save` | Save offline state |
| GET | `/mobile/offline/state/<device_id>` | Get offline state |
| POST | `/mobile/offline/queue/add` | Add to offline queue |
| POST | `/mobile/offline/sync` | Sync offline changes |
| GET | `/mobile/offline/queue/<device_id>` | Get offline queue |
| GET | `/mobile/offline/conflicts/<device_id>` | Get sync conflicts |
| POST | `/mobile/offline/conflict/resolve` | Resolve conflict |
| GET | `/mobile/stats` | Get mobile statistics |
| GET | `/mobile/audit` | Get mobile audit trail |

---

### Monitoring & Metrics

Production monitoring endpoints for observability and health checking.

#### `GET /metrics`

Prometheus-compatible metrics endpoint.

**Response:** (text/plain)
```
# TYPE natlangchain_http_requests_total counter
natlangchain_http_requests_total{method="GET",path="/health",status="200"} 42

# TYPE natlangchain_http_request_duration_ms histogram
natlangchain_http_request_duration_ms_bucket{le="50"} 100
natlangchain_http_request_duration_ms_sum 1234.56
natlangchain_http_request_duration_ms_count 150

# TYPE natlangchain_blockchain_blocks_total gauge
natlangchain_blockchain_blocks_total 5
```

#### `GET /metrics/json`

JSON format metrics.

**Response:**
```json
{
  "uptime_seconds": 3600.5,
  "counters": {
    "http_requests_total": 1000
  },
  "gauges": {
    "blockchain_blocks_total": 5,
    "blockchain_pending_entries": 2
  },
  "histograms": {
    "http_request_duration_ms": {
      "_total": {
        "count": 1000,
        "sum": 5000.0,
        "avg": 5.0
      }
    }
  }
}
```

#### `GET /health/live`

Kubernetes liveness probe. Returns 200 if the application is running.

**Response:**
```json
{
  "status": "alive"
}
```

#### `GET /health/ready`

Kubernetes readiness probe. Returns 200 if ready to accept traffic, 503 if not.

**Response (ready):**
```json
{
  "status": "ready"
}
```

**Response (not ready):**
```json
{
  "status": "not_ready",
  "issues": ["storage: not available"]
}
```

#### `GET /health/detailed`

Comprehensive system diagnostics.

**Response:**
```json
{
  "status": "healthy",
  "service": "NatLangChain API",
  "version": "0.1.0",
  "uptime_seconds": 3600.5,
  "system": {
    "python_version": "3.11.0",
    "platform": "Linux-5.15.0-x86_64",
    "hostname": "api-server-1"
  },
  "blockchain": {
    "blocks": 5,
    "pending_entries": 2,
    "difficulty": 2,
    "valid": true
  },
  "storage": {
    "backend_type": "JSONFileStorage",
    "available": true
  },
  "features": {
    "llm_validator": true,
    "search_engine": true,
    "drift_detector": true
  }
}
```

---

### Cluster Management

Endpoints for multi-instance deployments and horizontal scaling.

#### `GET /cluster/instances`

List all active API instances in the cluster.

**Response:**
```json
{
  "instance_count": 3,
  "instances": [
    {
      "instance_id": "api-server-abc123",
      "hostname": "api-1.example.com",
      "port": 5000,
      "started_at": 1704067200.0,
      "last_heartbeat": 1704070800.0,
      "is_leader": true,
      "healthy": true
    },
    {
      "instance_id": "api-server-def456",
      "hostname": "api-2.example.com",
      "port": 5000,
      "started_at": 1704067210.0,
      "last_heartbeat": 1704070800.0,
      "is_leader": false,
      "healthy": true
    }
  ]
}
```

#### `GET /cluster/info`

Get cluster coordination information.

**Response:**
```json
{
  "instance": {
    "instance_id": "api-server-abc123",
    "hostname": "api-1.example.com",
    "port": 5000,
    "is_leader": true,
    "uptime_seconds": 3600.0,
    "instance_count": 3
  },
  "leader": {
    "is_leader": true,
    "leader_info": {
      "instance_id": "api-server-abc123",
      "hostname": "api-1.example.com"
    }
  },
  "lock_manager": {
    "type": "RedisLockManager"
  },
  "cache": {
    "type": "RedisCache",
    "hits": 1000,
    "misses": 50
  },
  "scaling_config": {
    "redis_url": true,
    "storage_backend": "postgresql"
  }
}
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/metrics` | Prometheus format metrics |
| GET | `/metrics/json` | JSON format metrics |
| GET | `/health/live` | Kubernetes liveness probe |
| GET | `/health/ready` | Kubernetes readiness probe |
| GET | `/health/detailed` | Full system diagnostics |
| GET | `/cluster/instances` | List cluster instances |
| GET | `/cluster/info` | Cluster coordination info |

---

## Feature Requirements

Many advanced endpoints require specific configuration:

| Feature | Requirement |
|---------|-------------|
| LLM Validation | `ANTHROPIC_API_KEY` |
| Semantic Search | None (works offline) |
| Drift Detection | `ANTHROPIC_API_KEY` |
| Dialectic Validation | `ANTHROPIC_API_KEY` |
| Semantic Oracle | `ANTHROPIC_API_KEY` |
| Contract Parsing | `ANTHROPIC_API_KEY` |
| Contract Matching | `ANTHROPIC_API_KEY` |
| PostgreSQL Storage | `DATABASE_URL`, `pip install natlangchain[postgres]` |
| Distributed Locking | `REDIS_URL`, `pip install natlangchain[redis]` |
| Distributed Caching | `REDIS_URL`, `pip install natlangchain[redis]` |
| Cluster Coordination | `REDIS_URL`, `pip install natlangchain[redis]` |

Endpoints return `503 Service Unavailable` with descriptive error when requirements not met.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | API server port |
| `HOST` | `0.0.0.0` | API server host |
| `ANTHROPIC_API_KEY` | - | Required for LLM features |
| `STORAGE_BACKEND` | `json` | Storage backend: `json`, `postgresql`, `memory` |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string for scaling |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `console` | Log format: `console`, `json` |
| `WORKERS` | `4` | Gunicorn workers (production mode) |

---

## Support

For issues and feature requests, see the main README.md and project documentation.
