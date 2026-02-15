# NatLangChain API Reference

Base URL: `http://localhost:5000`

Authentication: Set `X-API-Key` header when `NATLANGCHAIN_REQUIRE_AUTH=true`.

---

## Core Endpoints

### POST /entry
Add a natural language entry to the blockchain.

```json
{
  "content": "Alice agrees to deliver 100 widgets to Bob.",
  "author": "alice",
  "intent": "Widget delivery agreement",
  "metadata": {},
  "validate": true,
  "auto_mine": false
}
```

**Response** `201`:
```json
{
  "status": "success",
  "entry": { "status": "pending", ... },
  "validation": { "validation_mode": "standard", "overall_decision": "ACCEPTED" }
}
```

### POST /entry/validate
Validate an entry without adding it to the chain. Requires `ANTHROPIC_API_KEY`.

```json
{ "content": "...", "author": "...", "intent": "..." }
```

### POST /mine
Mine pending entries into a new block.

```json
{ "difficulty": 2 }
```

**Response** `201`:
```json
{
  "status": "success",
  "block": { "index": 1, "hash": "00ab...", "entries_count": 3 }
}
```

### GET /chain
Get the entire blockchain.

### GET /chain/narrative
Get the full chain as human-readable prose. Returns `text/plain`.

### GET /block/{index}
Get a specific block by index (0 = genesis).

### GET /block/latest
Get the most recent block.

### GET /entries/author/{author}
Get all entries by a specific author.

### GET /entries/search?q={query}&limit={n}
Keyword search across all mined entries.

### GET /pending
Get all pending (unmined) entries.

### GET /validate/chain
Validate the entire chain's integrity.

### GET /stats
Get chain statistics (blocks, entries, authors, feature availability).

---

## Search Endpoints

### POST /search/semantic
Semantic search across blockchain entries. Requires sentence-transformers.

```json
{ "query": "widget delivery agreements", "top_k": 5, "min_score": 0.5 }
```

### POST /search/similar
Find entries similar to given content.

```json
{ "content": "Alice delivers widgets to Bob", "top_k": 5 }
```

---

## Contract Endpoints

All contract endpoints require `ANTHROPIC_API_KEY`.

### POST /contract/parse
Parse natural language content and extract structured contract terms.

```json
{ "content": "I offer Python tutoring at $50/hour, available weekday evenings." }
```

### POST /contract/match
Find matching contracts for pending entries.

```json
{ "miner_id": "miner-1" }
```

### POST /contract/post
Post a new live contract (offer or seek).

```json
{
  "content": "Offering character design for indie games, $500-1000 per character.",
  "author": "illustrator@example.com",
  "intent": "Offer design services",
  "contract_type": "offer",
  "auto_mine": true
}
```

### GET /contract/list?status={status}&type={type}&author={author}
List all contracts with optional filters.

### POST /contract/respond
Respond to a contract (accept, counter, reject).

```json
{
  "to_block": 1,
  "to_entry": 0,
  "response_content": "I accept the terms.",
  "author": "client@example.com",
  "response_type": "accept"
}
```

---

## Monitoring Endpoints

### GET /health
Basic health check. Returns `{ "status": "healthy" }`.

### GET /health/live
Kubernetes liveness probe.

### GET /health/ready
Kubernetes readiness probe.

### GET /health/detailed
Detailed health check with system information.

### GET /metrics
Prometheus-compatible metrics.

### GET /metrics/json
JSON format metrics.

### GET /cluster/instances
Get list of active API instances registered with the coordinator.

### GET /cluster/info
Get cluster coordination information (leader status, scaling config).

---

## Derivative Endpoints

### GET /derivatives/types
List all valid derivative types.

### GET /derivatives/{block_index}/{entry_index}
Get all derivatives of an entry.

### GET /derivatives/{block_index}/{entry_index}/lineage
Get full ancestry of an entry.

### GET /derivatives/{block_index}/{entry_index}/tree
Get complete derivation tree.

### GET /derivatives/{block_index}/{entry_index}/status
Get derivative status.

### POST /derivatives/validate
Validate parent references before creating a derivative.

---

## Error Responses

All errors return JSON with an `error` field:

```json
{ "error": "Missing required field: content" }
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 404 | Resource not found |
| 413 | Request body too large (>2MB) |
| 429 | Rate limited |
| 503 | Feature unavailable (no API key) or shutting down |
| 500 | Internal server error |
