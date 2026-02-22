# Vibe-Check Audit v2.0 - Remediation Plan

## Overview

Address all actionable findings from `VIBE_CHECK_AUDIT.md` across 8 phases, ordered by priority and dependency. Total: ~22 discrete changes across ~15 files.

---

## Phase 1: Dead Code & Broken References [HIGH]

### 1.1 Move orphaned `src/llm_providers.py` to `_deferred/src/`
- **Issue:** 1,298 lines implementing multi-provider LLM abstraction — never imported anywhere
- **Action:** `git mv src/llm_providers.py _deferred/src/llm_providers.py`
- **Note:** The `requests` dependency is still used by `api/ssrf_protection.py`, so it stays in pyproject.toml

### 1.2 Move orphaned `src/rate_limiter.py` to `_deferred/src/`
- **Issue:** 530 lines implementing distributed rate limiter — never imported (blockchain.py has its own `EntryRateLimiter`)
- **Action:** `git mv src/rate_limiter.py _deferred/src/rate_limiter.py`

### 1.3 Fix broken entry point in `pyproject.toml`
- **Issue:** `[project.scripts] natlangchain = "src.cli:main"` references `src/cli.py` which was moved to `_deferred/`
- **Action:** Comment out the `[project.scripts]` section with a note that CLI is deferred, or remove it entirely

---

## Phase 2: Configuration Hygiene [HIGH]

### 2.1 Remove/fix ghost config vars in `.env.example`
- **`HOST`** — truly unused, remove it
- **`PORT`** — IS used (`scaling/coordinator.py:86`) — keep but add clarifying comment
- **`FLASK_DEBUG`** — IS read (`api/monitoring.py:182`) for status reporting — keep but clarify it doesn't enable Flask debug mode
- **`CHAIN_DATA_FILE`** — IS used (`storage/__init__.py:60`) — keep, it's correct

### 2.2 Document all undocumented env vars in `.env.example`
Add sections for the following env vars that are consumed by active code but not documented:

**Retry tuning:**
- `RETRY_EXPONENTIAL_BASE` (default: 2.0)
- `RETRY_JITTER` (default: 0.1)

**Secret scanning:**
- `NATLANGCHAIN_SECRET_SCANNING` (default: true)
- `NATLANGCHAIN_SECRET_SCAN_MODE` (default: redact)

**Semantic search:**
- `SENTENCE_TRANSFORMERS_HOME` (default: system cache)

**Cryptographic identity:**
- `NATLANGCHAIN_IDENTITY_ENABLED` (default: false)
- `NATLANGCHAIN_IDENTITY_REQUIRE_SIGNATURES` (default: false)
- `NATLANGCHAIN_IDENTITY_KEYSTORE` (path)
- `NATLANGCHAIN_IDENTITY_PASSPHRASE` (secret)

**API pagination:**
- `NATLANGCHAIN_DEFAULT_PAGE_LIMIT` (default: 100)
- `NATLANGCHAIN_MAX_PAGE_LIMIT` (default: 1000)
- `NATLANGCHAIN_DEFAULT_HISTORY_LIMIT` (default: 50)

**LLM rate limiting:**
- `LLM_RATE_LIMIT_REQUESTS` (default: 10)
- `LLM_RATE_LIMIT_WINDOW` (default: 60)

**CORS & security:**
- `CORS_ALLOWED_ORIGINS` (comma-separated)
- `NATLANGCHAIN_ENABLE_HSTS` (default: false)
- `NATLANGCHAIN_TRUSTED_PROXIES` (comma-separated IPs)

**Infrastructure:**
- `DATABASE_URL` (PostgreSQL connection string)
- `REDIS_URL` (for scaling features)
- `STORAGE_BACKEND` (already documented, but add to appropriate section)

**Module manifests:**
- `NATLANGCHAIN_MANIFEST_DIR` (default: manifests/)
- `NATLANGCHAIN_MANIFEST_ENFORCE` (default: false)

---

## Phase 3: Error Handling Tightening [MEDIUM]

### 3.1 Replace broad `except Exception` with typed exceptions
76 broad catches across 22 files. Prioritize by file (highest count first):

| File | Count | Approach |
|------|-------|----------|
| `api/monitoring.py` | 6 | Catch `KeyError`, `OSError`, `RuntimeError` per context |
| `validator.py` | 6 | Catch `anthropic.APIError`, `json.JSONDecodeError`, `KeyError` |
| `semantic_search.py` | 5 | Catch `ModelLoadError`, `EncodingError`, `RuntimeError` |
| `storage/postgresql.py` | 5 | Catch `psycopg2.Error`, `ConnectionError` |
| `api/state.py` | 4 | Catch `StorageError`, `OSError` |
| `api/contracts.py` | 3 | Catch `anthropic.APIError`, `ValueError` |
| `api/__init__.py` | 3 | Catch `ImportError`, `ValueError` |
| `scaling/coordinator.py` | 3 | Catch `ConnectionError`, `redis.RedisError` |
| `storage/json_file.py` | 3 | Catch `OSError`, `json.JSONDecodeError` |
| Remaining 13 files | 1-2 each | Case-by-case typed replacement |

**Scope note:** Some `except Exception` catches are legitimate top-level safety nets (e.g., API error handlers). Those should get a `# broad catch intentional: last-resort handler` comment rather than being replaced.

### 3.2 Replace `print()` with `logging` in `state.py`
- **Lines 204, 208-209, 212-213, 228-229** — replace all `print()` calls with `logger.info()` / `logger.warning()`
- Add `logger = logging.getLogger(__name__)` at module top

---

## Phase 4: Fix Broken Entry Point & API Consistency [MEDIUM]

### 4.1 Standardize API query parameter naming
- **Issue:** `/entries/search` uses `q` (`core.py:397`) while `/search/semantic` uses `query` (`search.py:48`)
- **Action:** Rename `q` → `query` in `/entries/search` for consistency. Update error message at line 404 accordingly.
- **Backward compat:** Add deprecation support — accept both `query` and `q`, log a deprecation warning for `q`

### 4.2 Standardize API success response shapes
- **Issue:** Some endpoints return `{"status": "success", ...}`, others return direct objects
- **Action:** Audit all endpoints and document the two patterns. For new/modified endpoints, prefer the `{"status": "success", "data": {...}}` envelope. Do not break existing clients by changing stable endpoints.

---

## Phase 5: Test Quality Improvements [MEDIUM]

### 5.1 Fix trivial assertions
- **`test_e2e_blockchain_pipelines.py:176`** — `assert True` inside an if-block is a no-op. Replace with an actual check on the response data, e.g., assert the block/mined_block key has expected structure.
- **`test_pou_scoring.py:495`** — `assert False, "Should have raised"` is a manual pytest.raises. Replace with `with pytest.raises(ValueError, match="non-verified"):`.

### 5.2 Add `@pytest.mark.parametrize` to key test areas
Add parametrized tests to cover boundary conditions in 3-4 high-value areas:
- **Blockchain entry validation** — parametrize content length limits, missing fields, special characters
- **Rate limiting** — parametrize request counts at/near threshold
- **Encryption** — parametrize key lengths, empty data, large data
- **Semantic search** — parametrize query edge cases (empty, very long, special chars)

Target: ~10-15 new parametrized test cases across 3-4 test files.

---

## Phase 6: Thread Safety & Resource Management [LOW]

### 6.1 Add lock around mining operation
- **Issue:** `mine_pending_entries()` clears `pending_entries` after block creation, leaving a race window
- **Action:** Add a `threading.Lock` (`_mining_lock`) to `NatLangChain` class, acquired around the mine operation

### 6.2 Add lock to rate limit store
- **Issue:** `_rate_limit_store` in `api/utils.py` is a plain dict with no lock
- **Action:** Add `threading.Lock` around rate limit store reads/writes

### 6.3 Add sentence-transformers model cleanup
- **Issue:** No explicit cleanup when app shuts down
- **Action:** Add model cleanup to the existing graceful shutdown hook in `state.py`

---

## Phase 7: Error UX Improvements [LOW]

### 7.1 Add consistent `Retry-After` to all 503 responses
- Audit all 503 responses and add `Retry-After` header where missing (especially LLM-unavailable paths)

### 7.2 Add machine-readable error codes
- Define error code enum/constants (e.g., `VALIDATION_FAILED`, `RATE_LIMITED`, `LLM_UNAVAILABLE`, `NOT_FOUND`)
- Add `"code"` field to error JSON responses: `{"error": "message", "code": "RATE_LIMITED"}`
- Start with API boundary errors; internal errors can be added incrementally

---

## Phase 8: Authenticity & Comment Quality [LOW]

### 8.1 Add WHY comments to complex logic
Replace ~10-15 of the most opaque WHAT comments with WHY comments in:
- `blockchain.py` — hash computation choices, mining difficulty logic
- `validator.py` — prompt construction rationale, scoring thresholds
- `encryption.py` — algorithm/parameter choices (why AES-256-GCM, why 1M PBKDF2 iterations)
- `api/__init__.py` — security header choices

### 8.2 Add TODO/FIXME markers for known limitations
Add realistic TODO markers for documented gaps:
- `# TODO: parametrize rate limit per-endpoint (currently global)`
- `# TODO: add connection pooling for PostgreSQL storage`
- `# FIXME: mining is not atomic under concurrent writes (see Phase 6)`
- `# TODO: model warm-up on startup to avoid first-request latency`

---

## Dependency Graph

```
Phase 1 ← no dependencies (do first, removes 1,828 lines of noise)
  ↓
Phase 2 ← depends on Phase 1 (env vars from moved modules should NOT be documented)
  ↓
Phase 3 ← independent, can parallel with Phase 2
Phase 4 ← independent
Phase 5 ← independent
  ↓
Phase 6 ← can parallel with Phases 3-5
Phase 7 ← can parallel with Phase 6
Phase 8 ← do last (cosmetic, lowest risk)
```

---

## Files Modified Summary

| File | Changes | Phase |
|------|---------|-------|
| `src/llm_providers.py` | Move to `_deferred/` | 1 |
| `src/rate_limiter.py` | Move to `_deferred/` | 1 |
| `pyproject.toml` | Remove broken entry point | 1 |
| `.env.example` | Remove HOST, add ~20 env vars | 2 |
| `src/api/state.py` | print→logging, typed exceptions | 3 |
| `src/api/monitoring.py` | Typed exceptions | 3 |
| `src/validator.py` | Typed exceptions | 3 |
| `src/semantic_search.py` | Typed exceptions | 3 |
| `src/storage/postgresql.py` | Typed exceptions | 3 |
| ~13 other src/ files | Typed exceptions (1-3 each) | 3 |
| `src/api/core.py` | `q`→`query`, response consistency | 4 |
| `tests/test_e2e_blockchain_pipelines.py` | Fix `assert True` | 5 |
| `tests/test_pou_scoring.py` | Fix `assert False` | 5 |
| 3-4 test files | Add parametrize | 5 |
| `src/blockchain.py` | Mining lock, WHY comments, TODOs | 6, 8 |
| `src/api/utils.py` | Rate limit lock | 6 |
| Multiple API files | Retry-After, error codes | 7 |

**Total:** ~2 moved files, ~20-25 modified files

---

## Testing Strategy

After each phase:
1. Run `python -m pytest tests/` — verify zero regressions
2. Phase 1: Verify no import errors after moving dead modules
3. Phase 3: Verify error handling still works (existing tests cover this)
4. Phase 4: Verify both `q` and `query` work on `/entries/search`
5. Phase 5: Run new parametrized tests pass
6. Phase 6: Stress test mining under concurrent requests (manual or load test)
