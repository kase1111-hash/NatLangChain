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

# Frontend (Svelte + Tauri)
cd frontend && npm run dev              # Web dev server
cd frontend && npm run tauri:dev        # Desktop app
```

## Tech Stack

**Backend:** Python 3.11+, Flask 3.0+, Anthropic Claude API, sentence-transformers, cryptography (AES-256)

**Frontend:** Svelte 5, Vite 6, Tauri 1.6 (desktop), ESLint 9, Prettier 3

**Infrastructure:** Docker, Kubernetes/Helm, ArgoCD, PostgreSQL (optional), Redis (optional), Prometheus/Grafana

## Project Structure

```
src/                    # Core Python application
├── api/                # Modular API blueprints (18 files)
│   ├── core.py         # Entry, block, chain operations
│   ├── search.py       # Semantic search, drift detection
│   ├── contracts.py    # Live contract management
│   ├── disputes.py     # Dispute resolution
│   └── ...
├── api.py              # Main API server (being modularized into api/)
├── blockchain.py       # Core blockchain logic
├── validator.py        # LLM validation engine
├── p2p_network.py      # P2P networking
├── negotiation_engine.py  # Automated negotiation
└── ...                 # 78+ modules total

sdk/                    # TypeScript SDK (type-safe client)
frontend/               # Svelte + Tauri desktop app
tests/                  # Test suite (64+ test files)
docs/                   # NCIP specs, user manual, threat model
specs/                  # Integration specifications
charts/                 # Helm charts
k8s/                    # Kubernetes manifests
argocd/                 # GitOps configuration
```

## Key Files

- `run_server.py` - Server launcher
- `src/api.py` - Main API server (212+ endpoints)
- `src/blockchain.py` - Core blockchain implementation
- `src/validator.py` - LLM validation logic
- `config/canonical_terms.yaml` - Governance terms registry
- `data/chain_data.json` - Blockchain ledger persistence
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

**Frontend:**
- ESLint with single quotes, semicolons
- Prettier for formatting
- `const` preferred over `let`

## Environment Variables

```bash
ANTHROPIC_API_KEY=your_key          # Optional - for LLM validation
NATLANGCHAIN_REQUIRE_AUTH=false     # Authentication requirement
PORT=5000                           # Server port
CHAIN_DATA_FILE=chain_data.json     # Persistence file
VALIDATION_MODE=hybrid              # llm, hybrid, or multi
```

## API Endpoints

- Swagger UI: `http://localhost:5000/docs`
- Health check: `GET /health`
- Create entry: `POST /entry`
- Mine block: `POST /mine`
- View chain: `GET /chain`
- Semantic search: `POST /search`

See `API.md` for complete reference (212+ endpoints).

## Documentation

- `README.md` - Project overview
- `ARCHITECTURE.md` - System design
- `API.md` - REST API reference
- `SPEC.md` - Technical specification
- `INSTALLATION.md` - Setup guide
- `docs/NCIP-*.md` - Protocol governance specs
- `docs/user-manual.md` - End-user guide
