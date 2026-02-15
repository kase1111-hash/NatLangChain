# NatLangChain

A prose-first, intent-native blockchain protocol that uses natural language as the primary substrate for immutable entries. Records human intent in readable prose with LLM-powered validation and semantic consensus.

## Quick Reference

```bash
# Run API server
python run_server.py                    # Starts at http://localhost:5000

# Run tests
pytest tests/ -v                        # All tests
pytest tests/ --cov=src --cov-report=html  # With coverage

# Code quality
ruff check src/ --fix                   # Lint and fix
ruff format src/                        # Format
mypy --config-file=pyproject.toml src/  # Type check
```

## Tech Stack

**Backend:** Python 3.9+, Flask 3.0+, Anthropic Claude API, sentence-transformers, cryptography (AES-256)

**Infrastructure:** Docker, PostgreSQL (optional), Redis (optional)

## Project Structure

```
src/                    # Core Python application
├── api/                # Modular API blueprints (9 files)
│   ├── __init__.py     # create_app() factory
│   ├── core.py         # Entry, block, chain, validation endpoints
│   ├── search.py       # Semantic search endpoints
│   ├── contracts.py    # Live contract management
│   ├── derivatives.py  # Derivative tracking endpoints
│   ├── monitoring.py   # Health checks and metrics
│   ├── state.py        # Shared blockchain state
│   ├── utils.py        # Auth, rate limiting, schema validation
│   └── ssrf_protection.py
├── storage/            # Pluggable persistence (json, postgresql, memory)
├── monitoring/         # Metrics and structured logging
├── scaling/            # Distributed caching, coordination, locking
├── blockchain.py       # Core blockchain logic
├── validator.py        # LLM validation engine (Proof of Understanding)
├── contract_parser.py  # Natural language contract parsing
├── contract_matcher.py # Contract matching and proposal generation
├── semantic_search.py  # Embedding-based semantic search
├── encryption.py       # AES-256-GCM data encryption at rest
├── entry_quality.py    # Entry quality analysis
├── pou_scoring.py      # Proof of Understanding scoring dimensions
├── llm_providers.py    # Multi-provider LLM abstraction
├── intent_classifier.py # Transfer intent detection
├── rate_limiter.py     # Distributed rate limiting
└── retry.py            # Exponential backoff with circuit breaker

tests/                  # Test suite (20 test files)
examples/               # Usage examples (quickstart.py)
data/                   # Blockchain persistence (chain.json)
_deferred/              # Deferred features (frontend, SDK, additional docs)
```

## Key Files

- `run_server.py` - Server launcher
- `src/api/__init__.py` - Flask app factory (create_app)
- `src/blockchain.py` - Core blockchain implementation
- `src/validator.py` - LLM validation logic
- `data/chain.json` - Blockchain ledger persistence
- `pyproject.toml` - Python config, tool settings
- `.env` - Environment variables (copy from `.env.example`)

## Code Conventions

**Python:**
- Ruff for linting/formatting (line length: 100)
- Type hints (stricter in `src/api/` modules)
- snake_case for functions, PascalCase for classes
- Private methods with `_prefix`

**Testing:**
- Files: `test_*.py`, classes: `Test*`, methods: `test_*`
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Fixtures in `tests/conftest.py`

## Environment Variables

```bash
ANTHROPIC_API_KEY=your_key          # Optional - for LLM validation
NATLANGCHAIN_REQUIRE_AUTH=false     # Authentication requirement
PORT=5000                           # Server port
STORAGE_BACKEND=json                # json, postgresql, or memory
CHAIN_DATA_FILE=chain_data.json     # Persistence file
```

## API Endpoints

- Health check: `GET /health`
- Create entry: `POST /entry`
- Validate entry: `POST /entry/validate`
- Mine block: `POST /mine`
- View chain: `GET /chain`
- Semantic search: `POST /search/semantic`

See `API_REFERENCE.md` for complete endpoint documentation.

## Documentation

- `README.md` - Project overview and getting started
- `API_REFERENCE.md` - REST API reference
- `SPEC.md` - Technical specification
- `EVALUATION.md` - Project evaluation report
- `REFOCUS_PLAN.md` - Code refactoring roadmap
- `DEPENDENCY_MAP.md` - Dependency analysis
