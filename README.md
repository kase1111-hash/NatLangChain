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

- Python 3.9+
- An Anthropic API key (optional — server runs without it, but validation is disabled)

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
├── llm_providers.py     # Multi-provider LLM support
├── retry.py             # Exponential backoff with circuit breaker
├── rate_limiter.py      # Entry rate limiting
├── pou_scoring.py       # Proof of Understanding scoring
└── api/                 # Flask REST API (app factory pattern)
    ├── __init__.py      # create_app() factory
    ├── state.py         # Shared blockchain state
    ├── core.py          # Chain, entry, mining, block endpoints
    ├── search.py        # Semantic search endpoints
    ├── contracts.py     # Contract endpoints
    ├── validation.py    # Validation endpoints
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
| `STORAGE_BACKEND` | `json` | `json`, `postgresql`, or `memory` |
| `NATLANGCHAIN_REQUIRE_AUTH` | `true` | Require API key for mutations |
| `NATLANGCHAIN_API_KEY` | _(none)_ | API key for authentication |

## License

Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

[![CC BY-SA 4.0](https://licensebuttons.net/l/by-sa/4.0/88x31.png)](http://creativecommons.org/licenses/by-sa/4.0/)
