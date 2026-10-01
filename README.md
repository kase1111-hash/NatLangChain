# NatLangChain

A **natural language blockchain** — a prose-first ledger and intent-native protocol for recording human intent in readable prose.

> "Post intent. Let the system find alignment."

## What It Does

NatLangChain is a blockchain where **entries are ordinary, readable prose** — stories, offers, requests, agreements, or daily work outputs. Large language models serve as neutral validators using **Proof of Understanding** consensus: they paraphrase entries to demonstrate comprehension before accepting them into the chain.

Every step is immutably recorded as legible text, creating permanent, auditable receipts.

## Core Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Your Intent    │────▶│   REST API      │────▶│   Blockchain    │
│  (Natural Lang) │     │  (Flask)        │     │   (Immutable)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │  LLM Validator  │
                        │  (Anthropic)    │
                        │  Proof of       │
                        │  Understanding  │
                        └─────────────────┘
```

**Key components:**
- **Blockchain engine** — natural language entries, block mining, chain validation
- **Proof of Understanding** — LLM-powered semantic validation (Anthropic Claude)
- **Contract system** — parse and match natural language contracts
- **Semantic search** — find entries by meaning, not just keywords
- **REST API** — Flask-based API for all operations

## Getting Started

### Prerequisites

- Python 3.10+
- An Anthropic API key (optional — without it the server runs and entries are accepted without Proof of Understanding validation; semantic validation, contract parsing and intent classification need the key)

### Install

```bash
git clone https://github.com/kase1111-hash/NatLangChain.git
cd NatLangChain
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (optional)
# Set NATLANGCHAIN_REQUIRE_AUTH=false for local development
```

Authentication is on by default. Either set `NATLANGCHAIN_REQUIRE_AUTH=false` for local
development, or generate a key and send it in the `X-API-Key` header:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"   # -> NATLANGCHAIN_API_KEY
```

### Run

```bash
python run_server.py
```

### Try the Core Loop

```bash
# Check health
curl http://localhost:5000/health

# Add an entry (with auth disabled)
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Alice agrees to deliver 100 widgets to Bob by March 15th for $5,000.",
    "author": "alice",
    "intent": "Widget delivery agreement"
  }'

# Mine pending entries into a block
curl -X POST http://localhost:5000/mine

# View the chain
curl http://localhost:5000/chain

# Read the full narrative
curl http://localhost:5000/chain/narrative
```

### Docker

```bash
docker build -t natlangchain .
docker run -p 5000:5000 -e NATLANGCHAIN_REQUIRE_AUTH=false natlangchain
```

Chain data lives in `/app/data` inside the container; mount a volume there (see
`docker-compose.yml`) so the ledger survives container recreation.

### Production

`python run_server.py` uses Flask's development server. For a real deployment run the
app under gunicorn via `wsgi.py` (this is what the Docker image does):

```bash
pip install ".[production]"
gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:5000 wsgi:app
```

Run **exactly one worker process**: the ledger, pending queue and rate-limit state are held in
process memory, so multiple workers would each serve a different chain. Use threads for
concurrency, put TLS termination in front of it, set `NATLANGCHAIN_API_KEY`, and keep
`NATLANGCHAIN_REQUIRE_AUTH=true`.

## Project Structure

```
src/
├── blockchain.py        # Core chain: entries, blocks, mining, validation pipeline
├── validator.py         # Proof of Understanding (LLM semantic validation)
├── intent_classifier.py # LLM-based transfer intent detection
├── contract_parser.py   # Natural language contract parsing
├── contract_matcher.py  # Contract matching and proposal generation
├── semantic_search.py   # Embedding-based semantic search
├── encryption.py        # Data encryption at rest
├── entry_quality.py     # Entry quality analysis
├── llm_config.py        # Model selection and response parsing shared by all LLM callers
├── retry.py             # Exponential backoff with circuit breaker
├── rate_limiter.py      # Entry rate limiting
├── pou_scoring.py       # Proof of Understanding scoring
└── api/                 # Flask REST API (app factory pattern)
    ├── __init__.py      # create_app() factory
    ├── state.py         # Shared blockchain state
    ├── core.py          # Chain, entry, mining, validation endpoints
    ├── search.py        # Semantic search endpoints
    ├── contracts.py     # Contract endpoints
    ├── derivatives.py   # Derivative tracking endpoints
    ├── monitoring.py    # Health checks and metrics
    ├── utils.py         # Auth, rate limiting, schema validation
    └── ssrf_protection.py
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src
```

## Configuration

See [`.env.example`](.env.example) for all configuration options. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | _(none)_ | Enables LLM validation |
| `NATLANGCHAIN_LLM_MODEL` | `claude-sonnet-5-5` | Anthropic model used for all LLM features |
| `STORAGE_BACKEND` | `json` | `json`, `postgresql`, or `memory` |
| `NATLANGCHAIN_REQUIRE_AUTH` | `true` | Require API key for mutations |
| `NATLANGCHAIN_API_KEY` | _(none)_ | API key for authentication |

## Security model

Read this before relying on the chain for anything adversarial.

- **Proof of Understanding** (LLM paraphrase validation) checks that an entry is
  comprehensible and consistent with its stated intent. It is not a signature and does not
  prove who wrote the entry. Enable `NATLANGCHAIN_IDENTITY_ENABLED` for Ed25519 signing.
- **Hash linkage** gives tamper *detection*: editing a mined entry breaks its block hash and
  every later block. `GET /validate/chain` reports this.
- **Proof of work is not tamper *resistance*.** There is no peer network or fork-choice rule in
  the core engine, and at the default difficulty of 2 re-mining a year of history takes seconds
  (see `simulations/FINDINGS.md`, finding 6). Whoever controls the node's storage can rewrite
  it. Treat the chain as an auditable ledger of record kept by a trusted operator, not as a
  trustless blockchain. `NATLANGCHAIN_MINING_DIFFICULTY` raises the cost of rewriting but every
  extra digit also makes legitimate mining ~16x slower; publishing block hashes to an external
  timestamping service is the practical way to make history rewrites detectable.
- **Authentication** is a shared API key (`X-API-Key`). Rate limiting is per IP and per author.

## Deployment model

The ledger is held in process memory and persisted through the storage backend (JSON file by
default, PostgreSQL with `STORAGE_BACKEND=postgresql` and `DATABASE_URL`). That means:

- Run **one** application process. `gunicorn.conf.py` enforces a single worker and uses threads
  for concurrency. Scale vertically.
- The PostgreSQL backend makes storage durable and shareable with other tools, but it does not
  make the API horizontally scalable: two processes would each hold their own copy of the chain.
- Back up `CHAIN_DATA_FILE` (or the database) like any other ledger.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

Contributions are accepted under the same license.
