# Security Remediation Implementation Plan

## Overview

Fix all 19 distinct security findings (2 critical, 7 high, 6 medium, 4 low) identified in `SECURITY_REVIEW.md`. Changes span 14 files across 7 implementation phases, sequenced by dependencies.

---

## Phase 1 — Independent Quick Fixes (no dependencies, can be parallelized)

### Step 1: Fix docker-compose auth default [5.1 CRITICAL]
**File:** `docker-compose.yml` line 23
- Change `NATLANGCHAIN_REQUIRE_AUTH=${NATLANGCHAIN_REQUIRE_AUTH:-false}` → `:-true`
- Also remove `FLASK_DEBUG` from the production service environment block (relates to 6.3)

### Step 2: Secure subprocess execution [6.1 CRITICAL]
**File:** `src/llm_providers.py`
- Add `ALLOWED_CLI_PATHS` allowlist constant and `MAX_CLI_PROMPT_LENGTH = 100_000`
- Add `_validate_cli_path()` function that checks against the allowlist
- Apply validation in `LlamaCppProvider._complete_cli()` before `subprocess.run()`
- Apply validation in `LlamaCppProvider.is_available()` before the CLI version check

### Step 3: Add missing auth decorators [9.1 HIGH]
**Files:** `src/api/core.py`, `src/api/contracts.py`
- Add `@require_api_key` to `/validate/chain` endpoint (core.py:414)
- Add `@require_api_key` to `/stats` endpoint (core.py:449)
- Add `@require_api_key` to `/contract/parse` endpoint (contracts.py:46), placed before `@rate_limit_llm`

### Step 4: Add missing security headers [9.3 LOW]
**File:** `src/api/__init__.py` (in `add_security_headers`)
- Add `Referrer-Policy: no-referrer`
- Add `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
- Add `Cross-Origin-Opener-Policy: same-origin`
- Add `Cross-Origin-Resource-Policy: same-origin`

### Step 5: Remove API key config hint from error [5.2 LOW]
**File:** `src/api/utils.py` lines 369-375
- Replace the `"hint": "Set NATLANGCHAIN_API_KEY environment variable"` with a generic `"Authentication service unavailable"` message
- Log the configuration detail server-side only

### Step 6: Add repr protection to ProviderConfig [5.3 LOW]
**File:** `src/llm_providers.py` line 67
- Change `api_key: str | None = None` → `api_key: str | None = field(default=None, repr=False)`

### Step 7: Add Flask debug mode startup guard [6.3 HIGH]
**File:** `run_server.py`
- After the `debug` and `api_key_required` variables are computed, add a guard that refuses to start if both `FLASK_DEBUG=true` and `NATLANGCHAIN_REQUIRE_AUTH=false`
- Print a clear error explaining the security risk and `sys.exit(1)`

---

## Phase 2 — Create Standalone Sanitization Module (foundation for Phases 3-4)

### Step 8: Create `src/sanitization.py` [1.1 HIGH, 1.2 MEDIUM, 9.5 LOW]
**New file:** `src/sanitization.py`
- Extract `PROMPT_INJECTION_PATTERNS`, `sanitize_prompt_input()`, and `create_safe_prompt_section()` into a standalone module with **zero external dependencies** (no Flask, no anthropic, no validator imports)
- Add `unicodedata.normalize("NFKC", text)` before pattern matching [1.2]
- Change the injection detection `raise ValueError` to log the matched pattern server-side and raise a generic message: `"Input rejected for security reasons"` [9.5]
- Add `sanitize_output()` function that strips injection patterns from output text without raising errors (replaces matches with `[FILTERED]`)
- Add `validate_llm_response_field()` helper for schema enforcement

### Step 9: Update imports in contract_parser.py and contract_matcher.py [1.1]
**Files:** `src/contract_parser.py` lines 16-37, `src/contract_matcher.py` lines 17-41
- Change primary import to `from sanitization import ...`
- Keep `from validator import ...` as optional upgrade (try/except with pass)
- Delete the inline fallback functions entirely

### Step 10: Apply Unicode normalization in validator.py [1.2]
**File:** `src/validator.py` line 69
- Add `import unicodedata` at top
- Add `text = unicodedata.normalize("NFKC", text)` at the start of `sanitize_prompt_input()`

### Step 11: Fix injection error message in validator.py [9.5]
**File:** `src/validator.py` lines 79-82
- Log the matched pattern via `logger.warning()`
- Change the `ValueError` message to `"Input rejected for security reasons in field '{field_name}'."`

---

## Phase 3 — Memory Poisoning Fixes (depends on Phase 2)

### Step 12: Re-sanitize stored entries before LLM re-use [2.1 HIGH]
**File:** `src/contract_matcher.py`
- In `_get_open_contracts()`, wrap `entry.content`, `entry.author`, and `entry.intent` with `sanitize_prompt_input()` when building the open_contracts list
- This adds defense-in-depth on top of the existing sanitization in `_compute_match` and `_generate_proposal`

### Step 13: Sanitize narrative output [2.2 MEDIUM]
**File:** `src/api/core.py` lines 61-62
- After `state.blockchain.get_full_narrative()`, apply `sanitize_output()` from the sanitization module
- Add `Content-Disposition: inline` header to the response

---

## Phase 4 — Provider SSRF Hardening

### Step 14: Add SSRF validation to provider URLs [6.2 HIGH, 7.1 MEDIUM]
**File:** `src/llm_providers.py`
- Add `_validate_provider_url()` function that:
  - Imports `validate_url_for_ssrf` from `api.ssrf_protection`
  - Allows `localhost`/`127.0.0.1` when `NATLANGCHAIN_ALLOW_LOCAL_PROVIDERS=true` (default: true, since local providers are a core feature)
  - Blocks all other private/internal IPs
- Call this validation in `OllamaProvider.__init__()` and `LlamaCppProvider.__init__()`
- If validation fails, set `self.config.enabled = False` and log a warning
- Add optional `NATLANGCHAIN_ALLOWED_PROVIDER_HOSTS` environment variable for production allowlisting [7.1]

---

## Phase 5 — CORS and CSRF Hardening (do together)

### Step 15: Remove wildcard CORS support [9.2 MEDIUM]
**File:** `src/api/__init__.py` lines 154-155
- Replace the `if allowed_origins_str == "*":` branch with a warning log and no `Access-Control-Allow-Origin` header
- Keep the explicit origin list branch unchanged

### Step 16: Add CSRF Origin header validation [9.4 MEDIUM]
**File:** `src/api/__init__.py` (in `before_request_security`)
- For `POST`/`PUT`/`DELETE` requests, check the `Origin` header
- If `CORS_ALLOWED_ORIGINS` is configured and the request has an `Origin` header, verify it's in the allowed list
- Return 403 if origin is not allowed

---

## Phase 6 — LLM Response Schema Validation

### Step 17: Validate LLM response schemas [1.3 MEDIUM]
**Files:** `src/validator.py`, `src/contract_matcher.py`
- In `validator.py` after `json.loads(response_text)` (line 257):
  - Validate `decision` field is in `{"VALID", "NEEDS_CLARIFICATION", "INVALID"}`; default to `"INVALID"` if not
  - Validate `intent_match` is a boolean; default to `False` if not
- In `contract_matcher.py` after match score parsing:
  - Validate `score` is numeric in range [0, 100]; default to 0 if not
  - Validate `recommendation` is in `{"MATCH", "PARTIAL", "NO_MATCH"}`; default to `"NO_MATCH"` if not

---

## Phase 7 — Supply Chain Hardening (Docker changes)

### Step 18: Pin dependencies with hashes [3.1 HIGH]
**Files:** `requirements-lock.txt`, `Dockerfile`
- Regenerate `requirements-lock.txt` with hash annotations (using `pip-compile --generate-hashes` or equivalent)
- Update Dockerfile to: `pip install --no-cache-dir --require-hashes -r requirements-lock.txt`

### Step 19: Pre-download and pin ML model [3.2 HIGH]
**Files:** `Dockerfile`, `src/semantic_search.py`
- In Dockerfile builder stage, add `SENTENCE_TRANSFORMERS_HOME=/opt/models` and pre-download the `all-MiniLM-L6-v2` model
- Copy `/opt/models` from builder to runtime stage
- In `semantic_search.py`, pass `cache_folder` from env var to `SentenceTransformer()` so it uses the bundled model

---

## Dependency Graph

```
Phase 1: [5.1] [6.1] [9.1] [9.3] [5.2] [5.3] [6.3]  ← all independent
    ↓
Phase 2: [1.1] → creates src/sanitization.py
         [1.2] [9.5] → included in sanitization.py + validator.py
    ↓
Phase 3: [2.1] [2.2] ← depends on sanitization.py existing
    ↓ (parallel with Phase 3)
Phase 4: [6.2] [7.1] ← depends on ssrf_protection.py (already exists)
    ↓ (parallel with Phases 3-4)
Phase 5: [9.2] [9.4] ← do together for consistency
    ↓ (parallel with Phase 5)
Phase 6: [1.3] ← standalone
    ↓
Phase 7: [3.1] [3.2] ← Docker rebuild, do last since it requires generating lock file
```

---

## Files Modified Summary

| File | Findings | Phase |
|------|----------|-------|
| `docker-compose.yml` | 5.1, 6.3 | 1 |
| `src/llm_providers.py` | 6.1, 5.3, 6.2, 7.1 | 1, 4 |
| `src/api/core.py` | 9.1, 2.2 | 1, 3 |
| `src/api/contracts.py` | 9.1 | 1 |
| `src/api/__init__.py` | 9.3, 9.2, 9.4 | 1, 5 |
| `src/api/utils.py` | 5.2 | 1 |
| `run_server.py` | 6.3 | 1 |
| `src/sanitization.py` (NEW) | 1.1, 1.2, 2.2, 9.5 | 2 |
| `src/validator.py` | 1.2, 9.5, 1.3 | 2, 6 |
| `src/contract_parser.py` | 1.1 | 2 |
| `src/contract_matcher.py` | 1.1, 2.1, 1.3 | 2, 3, 6 |
| `src/semantic_search.py` | 3.2 | 7 |
| `Dockerfile` | 3.1, 3.2 | 7 |
| `requirements-lock.txt` | 3.1 | 7 |

**Total:** 1 new file, 13 modified files

---

## Testing Strategy

After each phase:
1. Run `python -m pytest tests/` to verify no regressions
2. For Phase 1 changes: verify auth is now required on previously-unprotected endpoints
3. For Phase 2-3: verify prompt injection detection works with Unicode confusables, verify narrative endpoint strips injection patterns
4. For Phase 4: verify SSRF validation on provider URLs (test with private IPs)
5. For Phase 5: verify wildcard CORS is rejected, verify Origin header validation
6. For Phase 7: verify Docker build succeeds with hash-pinned dependencies
