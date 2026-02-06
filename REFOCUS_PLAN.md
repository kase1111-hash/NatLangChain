# NatLangChain Refocus: Phased Implementation Plan

**Based on:** [EVALUATION.md](./EVALUATION.md)
**Created:** 2026-02-06
**Target:** Cut ~45,000 lines, focus on 5 core modules, prove the intent matching loop

---

## Overview

The codebase is a 92,400-line Python monolith (74 source modules) for a 0.1.0-alpha release. The core value — LLM-mediated intent matching with immutable prose records — is buried under premature enterprise features, token economics, and distributed infrastructure.

This plan executes the evaluation's recommendation in 7 phases, each self-contained with clear entry/exit criteria.

### What Survives the Refocus

| Module | Lines | Role |
|--------|-------|------|
| `src/blockchain.py` | 2,467 | Chain data structures, entry pipeline |
| `src/validator.py` | 3,851 | Proof of Understanding (core differentiator) |
| `src/semantic_search.py` | 352 | Intent discovery via embeddings |
| `src/contract_parser.py` | 411 | Extract structured terms from prose |
| `src/contract_matcher.py` | 474 | Autonomous offer/seek matching |
| `src/llm_providers.py` | 1,180 | Multi-provider LLM abstraction |
| `src/entry_quality.py` | 654 | Chain bloat prevention |
| `src/rate_limiter.py` | 515 | Anti-flooding |
| `src/encryption.py` | 472 | Data-at-rest encryption |
| `src/pou_scoring.py` | 919 | PoU scoring dimensions |
| `src/storage/` | ~500 | Pluggable persistence backends |
| `src/api/core.py` | 485 | Core blockchain API |
| `src/api/contracts.py` | 348 | Contract endpoints |
| `src/api/search.py` | 334 | Semantic search endpoints |
| `src/api/state.py` | 192 | Shared state management |
| `src/api/utils.py` | 465 | Shared utilities, auth, rate limiting |
| `src/api/derivatives.py` | 339 | Derivative tracking endpoints |
| `src/api/monitoring.py` | 371 | Health/metrics endpoints |

**Total surviving source:** ~14,000 lines (~18% of current codebase)

### Estimated Lines Impact Per Phase

| Phase | Removed | Added | Net |
|-------|---------|-------|-----|
| Phase 0: Preparation | 0 | 0 | 0 |
| Phase 1: Cut Modules | ~25,000 | 0 | -25,000 |
| Phase 2: Defer Modules | ~15,000 | 0 | -15,000 |
| Phase 3: Kill God File | ~7,362 | ~500 | -6,862 |
| Phase 4: Harden Core | ~200 | ~800 | +600 |
| Phase 5: Test Overhaul | ~200 | ~2,000 | +1,800 |
| Phase 6: Config Cleanup | ~500 | ~300 | -200 |
| Phase 7: Prove the Loop | 0 | ~500 | +500 |
| **Total** | **~48,262** | **~4,100** | **~-44,162** |

---

## Phase 0: Preparation and Safety Net

**Duration:** 1-2 days
**Purpose:** Establish a baseline so every subsequent phase can be verified against known-good state.

### Entry Criteria
- Access to the repository
- Ability to run the existing test suite

### Tasks

#### 0.1 — Create a dedicated refocus branch
```bash
git checkout -b refocus/core-loop
```
All work happens on this branch. `main` stays untouched as a rollback target.

#### 0.2 — Record the current test baseline
Run the full test suite and record which tests pass/fail today:
```bash
python -m pytest tests/ --tb=short -q 2>&1 | tee test_baseline.txt
```

#### 0.3 — Inventory import dependencies for cut modules
Verify that no core module (`blockchain.py`, `validator.py`, `semantic_search.py`, `contract_parser.py`, `contract_matcher.py`) imports from any cut target. All references to cut modules should live only in:
- `src/api.py` (try/except import blocks)
- `src/api/__init__.py` (`init_managers`)
- Blueprint files for cut features
- Test files for cut features

This confirms removal is mechanically safe — no cascading breakage into core logic.

#### 0.4 — Tag the pre-refocus state
```bash
git tag v0.1.0-alpha-pre-refocus
```

### Exit Criteria
- Branch exists with tag
- Test baseline recorded
- Dependency map validated (no surprises in imports)

---

## Phase 1: Surgical Removal of "Cut Immediately" Modules

**Duration:** 2-3 days
**Purpose:** Remove dead code that adds cognitive load, CI noise, and false confidence. Target: eliminate ~25,000 lines.

### Entry Criteria
- Phase 0 complete
- On the `refocus/core-loop` branch

### Tasks

#### 1.1 — Delete source modules: Token Economics
Remove from `src/`:
| File | Lines | Reason |
|------|-------|--------|
| `market_pricing.py` | 1,246 | No market exists |
| `treasury.py` | 802 | No token exists |
| `observance_burn.py` | 432 | No token to burn |
| `revenue_sharing.py` | 1,134 | No revenue to share |
| `permanence_endowment.py` | 1,149 | No fund exists |

#### 1.2 — Delete source modules: Enterprise/Security Features
| File | Lines | Reason |
|------|-------|--------|
| `zk_privacy.py` | 1,571 | Simulated crypto, no security value |
| `boundary_siem.py` | 1,558 | Enterprise SIEM for pre-alpha |
| `fido2_auth.py` | 1,064 | Hardware keys for prototype |
| `jurisdictional.py` | 886 | No cross-jurisdictional users |

#### 1.3 — Delete source modules: Wrong Product
| File | Lines | Reason |
|------|-------|--------|
| `mobile_deployment.py` | 1,868 | Data structures only, no implementation |
| `compute_to_data.py` | 1,403 | Separate product (federated ML) |
| `data_composability.py` | 1,393 | Infrastructure without a use case |

#### 1.4 — Delete API blueprints for cut features
Remove from `src/api/`:
| File | Lines | Serves |
|------|-------|--------|
| `mobile.py` | 557 | `mobile_deployment.py` |
| `compute.py` | 738 | `compute_to_data.py` |
| `composability.py` | 812 | `data_composability.py` |
| `revenue.py` | 754 | `revenue_sharing.py` |
| `endowment.py` | 490 | `permanence_endowment.py` |
| `identity.py` | 834 | `did_identity.py` (deferred) |

#### 1.5 — Delete infrastructure for cut features
Remove directories:
- `charts/` (Kubernetes Helm charts)
- `argocd/` (GitOps configs)

Remove files:
- `docker-compose.production.yml`
- `docker-compose.security.yml`

Keep: `Dockerfile`, `docker-compose.yml` (basic deployment still useful).

#### 1.6 — Delete corresponding test files
Remove tests that exclusively test cut modules:
- `tests/test_zk_privacy.py`
- `tests/test_treasury.py`
- `tests/test_observance_burn.py`
- `tests/test_mobile_deployment.py`
- `tests/test_jurisdictional.py`
- `tests/test_market_pricing.py`
- `tests/test_fido2_auth.py`

Review and trim (may test integration paths touching core):
- `tests/test_boundary_protection.py`
- `tests/test_boundary_integration.py`
- `tests/test_integration_escalation.py`
- `tests/test_external_integration.py`

#### 1.7 — Clean up import references
**In `src/api.py`:** Remove the try/except import blocks (lines 129-256) for all deleted modules: `ObservanceBurnManager`, `AntiHarassmentManager`, `NatLangChainTreasury`, `FIDO2AuthManager`, `ZKPrivacyManager`, `MarketAwarePricingManager`, `MobileDeploymentManager`. Also remove all route definitions that reference these modules.

**In `src/api/__init__.py`:**
- Remove init blocks in `init_managers()` for deleted modules
- Remove deleted blueprints from `ALL_BLUEPRINTS` list
- Remove corresponding import statements

**In `src/api/utils.py`:** Remove fields from `ManagerRegistry` for deleted features and their `is_*_enabled()` convenience methods.

#### 1.8 — Clean up pyproject.toml
- Remove per-file-ignores for deleted modules (currently 38 entries, target <20)
- Remove mypy overrides for deleted modules
- Remove the `story-protocol` optional dependency group
- Remove `fido2` from the `all` group

#### 1.9 — Run tests and fix breakage
Expected outcomes:
- Core tests pass unchanged
- `test_api_endpoints.py` may break if it tests routes from deleted blueprints — remove those test cases
- `test_e2e.py` and `test_integration.py` may need adjustments

#### 1.10 — Commit
```
Remove 14 non-core modules, 6 API blueprints, K8s/ArgoCD infra, and associated tests
```

### Exit Criteria
- All cut modules deleted
- All import references cleaned
- Test suite passes (for remaining tests)
- No runtime import errors when starting the server

---

## Phase 2: Archive Deferred Modules

**Duration:** 1 day
**Purpose:** Get deferred code out of the active source tree without destroying it. Reduces cognitive load and makes the "core" set visually obvious.

### Entry Criteria
- Phase 1 complete and tests passing

### Tasks

#### 2.1 — Create `_deferred/` directory at project root
This is outside the Python path so nothing can accidentally import it.

#### 2.2 — Move deferred source modules
Move from `src/` to `_deferred/src/`:
| File | Lines | Reason to Defer |
|------|-------|-----------------|
| `p2p_network.py` | 2,392 | Real work, but centralized server needs to prove concept first |
| `gossip_protocol.py` | 1,234 | Depends on P2P |
| `nat_traversal.py` | 1,382 | Depends on P2P |
| `did_identity.py` | 1,331 | Not needed until multi-user identity is real |
| `negotiation_engine.py` | 1,861 | Complex; simplify to single-round matching first |
| `multi_model_consensus.py` | 584 | Single-LLM validation not proven yet |
| `dispute.py` | 1,237 | Dispute resolution premature without real disputes |
| `dialectic_consensus.py` | 284 | Skeptic/Facilitator debate is nice-to-have |
| `semantic_diff.py` | 346 | Drift detection is nice-to-have |
| `anti_harassment.py` | 907 | No user base to protect yet |
| `cognitive_load.py` | 889 | Agent load tracking premature |

#### 2.3 — Move deferred frontend and SDK
- `frontend/` → `_deferred/frontend/`
- `sdk/` → `_deferred/sdk/`

#### 2.4 — Clean deferred references
Remove try/except import blocks in `src/api.py` for: `SemanticDriftDetector`, `DialecticConsensus`, `DisputeManager`, `SemanticOracle`, `MultiModelConsensus`, `EscalationForkManager`, `AutomatedNegotiationEngine`, `P2PNetwork`.

Remove corresponding init blocks, route definitions, and `ManagerRegistry` fields.

#### 2.5 — Clean pyproject.toml
Remove per-file-ignores and mypy overrides for deferred modules.

#### 2.6 — Move deferred test files to `_deferred/tests/`
- `tests/test_p2p_network.py`
- `tests/test_gossip_protocol.py`
- `tests/test_nat_traversal.py`
- `tests/test_negotiation_engine.py`
- `tests/test_dispute.py`
- `tests/test_semantic_diff.py`
- `tests/test_cognitive_load.py`
- `tests/test_anti_harassment.py`
- `tests/test_multilingual.py`

#### 2.7 — Run tests, fix breakage, commit

### Exit Criteria
- `src/` contains only core modules (~15-20 files)
- `_deferred/` exists with preserved code
- Test suite passes
- Server starts cleanly with only core features

---

## Phase 3: Kill the God File (`src/api.py`)

**Duration:** 3-5 days
**Purpose:** Eliminate the 7,362-line monolith. After Phases 1 and 2, most route definitions are already dead code. Complete the migration to the blueprint architecture.

### Entry Criteria
- Phases 1 and 2 complete
- `src/api.py` significantly thinned from cut/deferred removals

### Tasks

#### 3.1 — Audit what remains in api.py
After removing cut and deferred imports/routes, identify:
- Route definitions still in the monolith (not yet in blueprints)
- `run_server()` function (line 7323)
- `load_chain()` / `save_chain()` functions
- Graceful shutdown handlers
- Duplicate utility functions (exist in both `api.py` and `api/utils.py`)

#### 3.2 — Extract remaining routes to existing blueprints
Move any remaining unique routes into the appropriate blueprint:
- Validation endpoints → `src/api/core.py` or new `src/api/validation.py`
- Mining endpoints → `src/api/core.py`
- Miscellaneous admin/debug → `src/api/monitoring.py`

#### 3.3 — Create a proper Flask app factory
Enhance `src/api/__init__.py` with a `create_app()` factory that:
1. Creates the Flask app
2. Configures security settings (`MAX_CONTENT_LENGTH`, etc.)
3. Calls `init_managers()`
4. Calls `register_blueprints()`
5. Registers error handlers
6. Returns the app

The building blocks already exist (`register_blueprints` at line 69, `init_managers` at line 91).

#### 3.4 — Move server startup to run_server.py
Move `run_server()` and graceful shutdown handlers from `api.py` into `run_server.py`. Change from `importlib` loading to importing `create_app` from the `api` package.

#### 3.5 — Delete src/api.py
Once all routes, utilities, and startup logic are extracted, delete the monolith. This is the keystone task of the entire refocus.

#### 3.6 — Update test configuration
Update `tests/conftest.py` to use the new app factory:
```python
from api import create_app
app = create_app(testing=True)
```

#### 3.7 — Update Dockerfile
Verify the entrypoint (`python run_server.py`) still works with the app factory.

#### 3.8 — Run full test suite, fix breakage, commit

### Exit Criteria
- **`src/api.py` is deleted**
- All routes live in blueprint files under `src/api/`
- `run_server.py` starts the app via the factory
- Test suite passes
- `docker build .` succeeds

---

## Phase 4: Core Loop Hardening

**Duration:** 5-7 days
**Purpose:** Fix fundamental technical problems in the core modules. This is where the "double down" investment happens.

### Entry Criteria
- Phases 1-3 complete
- Lean codebase with only core modules

### Tasks

#### 4.1 — Replace keyword-based intent detection with LLM classification
**The critical fix.** `TRANSFER_INTENT_KEYWORDS` in `src/blockchain.py:69-93` is a static set of 24 English verb conjugations used for double-spend prevention. This is the primary design contradiction in a "natural language first" blockchain.

**Implementation:**
- Create `src/intent_classifier.py` that calls the Anthropic API to classify transfer intent
- Return structured results: `{is_transfer: bool, asset_id: str|None, from: str|None, to: str|None, confidence: float}`
- Keep keyword list as a fast-path fallback when LLM is unavailable
- Use the same prompt injection protections from `validator.py:26-90`
- Wire into `_get_asset_transfer_rejection` in `blockchain.py`

#### 4.2 — Fix in-memory state persistence
**Problem:** These structures don't survive server restarts:
1. `AssetRegistry._ownership` and `._pending_transfers` (`blockchain.py:131-318`)
2. `DerivativeRegistry` (`blockchain.py`)
3. `rate_limit_store` in `src/api/utils.py`
4. `_entry_fingerprints` in the `NatLangChain` class

**Fix for 1, 2, 4:** Extend `NatLangChain.to_dict()` to include `asset_registry.to_dict()`, `derivative_registry.to_dict()`, and `_entry_fingerprints`. Extend `from_dict()` to restore them. Storage backends automatically persist this since they serialize `blockchain.to_dict()`.

**Fix for 3:** The `src/rate_limiter.py` already has `get_rate_limiter()` with Redis support. Wire it into `api/utils.py` properly. In-memory dict is acceptable for single-server as fallback.

#### 4.3 — Harden the entry validation pipeline
Strengthen the `add_entry` method in `blockchain.py`:
- Add explicit error handling for LLM API failures in validation
- Add timeout handling for LLM calls
- Add structured logging for each pipeline step (rejections logged with reason)
- Make pipeline steps configurable

#### 4.4 — Strengthen the PoU validator
After Phases 1-2, `src/validator.py` has dead imports (lines 115-219) for deferred modules. Clean them out. What remains:
- Ensure `validate_entry` has robust error handling for API timeouts, rate limits, malformed responses
- Add retry logic with exponential backoff (the existing `src/retry.py` module can be used)
- Ensure PoU scoring dimensions (Coverage, Fidelity, Consistency, Completeness) from `src/pou_scoring.py` are properly integrated and tested

#### 4.5 — Improve semantic search persistence
`src/semantic_search.py` (352 lines) keeps `_embeddings_cache` in memory. Add:
- Index persistence so embeddings survive restarts
- Batch encoding for efficiency as the chain grows
- Incremental indexing (only encode new entries, not full chain each time)

#### 4.6 — Harden contract matching
For `src/contract_parser.py` (411 lines) and `src/contract_matcher.py` (474 lines):
- Add error handling for LLM failures in `ContractParser.parse_contract()`
- Add configurable match confidence thresholds
- Add logging for match attempts (successful and failed)
- Consider caching parsed contract terms to avoid re-parsing

### Exit Criteria
- Keyword-based intent detection replaced with LLM classification (with keyword fallback)
- AssetRegistry, DerivativeRegistry, and entry fingerprints persisted through restarts
- Validator has retry logic and timeout handling
- Semantic search index persists
- All core module tests pass

---

## Phase 5: Test Suite Overhaul

**Duration:** 3-5 days
**Purpose:** Address bimodal test quality. Focus on making remaining tests comprehensive, especially for error paths.

### Entry Criteria
- Phase 4 complete
- Core modules hardened

### Tasks

#### 5.1 — Audit surviving test files
After Phases 1-2, key remaining files:
| File | Lines | Status |
|------|-------|--------|
| `test_blockchain.py` | 234 | Thin for 2,467-line module |
| `test_bad_actors.py` | 1,354 | Excellent — keep as-is |
| `test_e2e_blockchain_pipelines.py` | 1,353 | Excellent — keep as-is |
| `test_contract_parser.py` | 549 | Decent |
| `test_contract_matcher.py` | 564 | Decent |
| `test_semantic_search.py` | 222 | Thin |
| `test_api_endpoints.py` | 279 | Thin |
| `test_validator_critical.py` | 221 | Mostly stubs — rewrite |
| `test_storage.py` | 427 | OK |
| `test_pou_scoring.py` | - | Check coverage |

#### 5.2 — Expand test_blockchain.py
Currently 234 lines for a 2,467-line module. Add:
- Tests for the full `add_entry` pipeline with each rejection type (rate limit, timestamp, metadata, quality, duplicate, asset transfer, validation)
- `AssetRegistry` persistence roundtrip tests (`to_dict` / `from_dict`)
- `DerivativeRegistry` persistence roundtrip tests
- Tests for the new LLM-based intent classification (Phase 4.1)
- `NatLangChain.from_dict()` with corrupted data
- `mine_block` with edge cases (empty pending, already-mined)

#### 5.3 — Rewrite test_validator_critical.py
Currently mostly stubs checking constants exist. Replace with:
- Tests for `ProofOfUnderstanding.validate_entry()` with malformed LLM JSON responses
- API timeout handling tests
- Prompt injection detection tests (the sanitization at lines 26-90)
- PoU score edge cases (all zeros, all maximums, missing dimensions)

#### 5.4 — Add error path tests for contract modules
- Parsing with malformed/empty content
- Matching when LLM is unavailable
- Matching with no open contracts
- Matching same-type contracts (offer vs offer — should not match)

#### 5.5 — Expand API integration tests
Expand `test_api_endpoints.py` to cover:
- All surviving endpoints with valid and invalid inputs
- Rate limiting behavior
- Authentication enforcement
- Error responses (404, 500, 503)
- Full entry lifecycle: POST → GET pending → mine → GET chain

#### 5.6 — Expand storage backend tests
- JSON file storage with corrupted files and permission errors
- Memory storage thread safety
- PostgreSQL connection failures (mocked)

#### 5.7 — Eliminate remaining stub tests
Any test files that only check "class exists" or "constant is defined" — either delete or replace with behavioral tests.

### Exit Criteria
- Test coverage for core modules reaches 80%+ line coverage
- Every core module has explicit error path tests
- No stub-only test files remain
- `pytest` runs clean with no warnings about missing modules

---

## Phase 6: Configuration and Deployment Cleanup

**Duration:** 1-2 days
**Purpose:** Make the project runnable by someone other than the original author.

### Entry Criteria
- Phases 1-5 complete

### Tasks

#### 6.1 — Simplify requirements.txt
Focused core dependencies only:
```
flask>=3.0.0
anthropic>=0.34.2
python-dotenv>=1.0.0
sentence-transformers>=2.2.0
numpy>=1.20.0
cryptography>=41.0.0
requests>=2.28.0
```

#### 6.2 — Simplify pyproject.toml
Target: `per-file-ignores` reduced from 38 entries to <10. Mypy overrides for core modules should have `ignore_errors = false` (enable type checking).

#### 6.3 — Update .env.example
Minimal viable config:
```
ANTHROPIC_API_KEY=your_key_here
STORAGE_BACKEND=json
CHAIN_DATA_FILE=chain_data.json
NATLANGCHAIN_REQUIRE_AUTH=true
NATLANGCHAIN_API_KEY=your_api_key_here
```

#### 6.4 — Update Dockerfile
Remove `iptables`/`iproute2` packages from runtime stage (were for boundary/SIEM enforcement). Verify `config/` directory reference.

#### 6.5 — Update README.md
Reflect focused scope. Remove references to: ZK proofs, P2P networking, token economics, mobile wallets, enterprise SIEM/FIDO2, frontend/SDK. Add clear "Getting Started" walkthrough of the core loop.

#### 6.6 — Archive non-core documentation
Remove or move to `_deferred/docs/` any docs that describe cut/deferred features.

### Exit Criteria
- `docker build && docker run` works cleanly
- New user can follow README to run the core loop
- No references to cut features in user-facing docs

---

## Phase 7: Prove the Core Loop End-to-End

**Duration:** 3-5 days
**Purpose:** Demonstrate that the refocused product actually works. "Get 10 real users" preparation.

### Entry Criteria
- Phases 1-6 complete
- Clean, focused codebase

### Tasks

#### 7.1 — Create a scripted end-to-end demo
Write `demo.py` that:
1. Starts the API server
2. Submits an "offer" entry: *"I am a freelance illustrator offering character design services for indie games, $500-1000 per character sheet, 2-week turnaround"*
3. Waits for PoU validation
4. Submits a "seek" entry: *"Small indie studio looking for character artist for our RPG, budget $800 per character, need 5 characters over 3 months"*
5. Triggers contract matching
6. Verifies a proposal is generated
7. Shows the full chain narrative

This is the proof-of-life for the core loop.

#### 7.2 — Benchmark LLM costs
Instrument the validator and contract matcher to log:
- Number of LLM calls per entry
- Token usage per call
- Latency per validation
- Cost per entry lifecycle

Critical for understanding economic viability.

#### 7.3 — Stress test persistence
- Submit 100 entries, mine blocks, restart server, verify chain integrity
- Verify AssetRegistry state survives restart
- Test concurrent entry submissions (multiple clients)

#### 7.4 — Document the surviving API
Clean reference for surviving endpoints:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/entry` | POST | Submit an entry |
| `/chain` | GET | Get the blockchain |
| `/chain/narrative` | GET | Get readable narrative |
| `/search/semantic` | POST | Semantic search |
| `/contract/parse` | POST | Parse a contract |
| `/contract/match` | POST | Find matches |
| `/health` | GET | Health check |

#### 7.5 — Tag the release
```bash
git tag v0.2.0-alpha-focused
```

### Exit Criteria
- Demo script runs end-to-end successfully
- LLM cost per entry lifecycle documented
- Persistence verified across restarts
- API documented
- Tagged release

---

## Risk Registry

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing a module breaks an undetected dependency | Low | Medium | Phase 0 dependency mapping; try/except pattern means failures are silent |
| API consolidation (Phase 3) introduces route regressions | Medium | High | Record all existing routes before starting; test each endpoint after migration |
| LLM intent classifier (Phase 4.1) is too slow for entry pipeline | Medium | Medium | Keep keyword fallback as fast path; LLM classification as async background check |
| Test suite overhaul takes longer than estimated | Medium | Low | Prioritize blockchain.py and validator.py error paths first |
| Deferred modules bitrot in `_deferred/` | High | Low | Acceptable — re-integrate when needed; keeping them active is worse |

---

## Timeline Summary

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 0:** Preparation | 1-2 days | Branch, baseline, dependency map |
| **Phase 1:** Cut Modules | 2-3 days | Delete 14 modules, 6 blueprints, infra |
| **Phase 2:** Defer Modules | 1 day | Archive 11 modules, frontend, SDK |
| **Phase 3:** Kill God File | 3-5 days | Decompose api.py, create app factory |
| **Phase 4:** Harden Core | 5-7 days | LLM intent classifier, persistence, error handling |
| **Phase 5:** Test Overhaul | 3-5 days | Error paths, rewrite stubs, 80%+ coverage |
| **Phase 6:** Config Cleanup | 1-2 days | Simplify deployment, update docs |
| **Phase 7:** Prove the Loop | 3-5 days | E2E demo, benchmarks, tag release |
| **Total** | **~20-30 days** | **From 92K to ~35K lines, focused and proven** |
