# Remediation Plan — Agentic Security Audit v3.0 Findings

## Updated Assessment

After deeper investigation, several findings are **partially addressed**:
- CI/CD pipeline exists (`.github/workflows/ci.yml`) but security checks use `continue-on-error: true`
- Lock file exists (`requirements-lock.txt`) with `cryptography==43.0.3` but isn't enforced in builds
- Redis-backed rate limiter exists in `_deferred/src/rate_limiter.py` but isn't integrated

This changes the plan from "build from scratch" to "tighten and integrate existing work."

---

## Fix 1: Update cryptography Version Floor [Finding #7 — LOW]

**Problem:** `cryptography>=41.0.0` allows installing a version 3 major releases behind.

**Files:** `pyproject.toml` (line 46), `requirements.txt` (line 22)

**Changes:**
- `cryptography>=41.0.0` → `cryptography>=43.0.0` in both files
- Lock file already has `cryptography==43.0.3` — no change needed there

---

## Fix 2: Remove Test Credential [Finding #8 — LOW]

**Problem:** Hardcoded `password="pass"` in deferred test file.

**File:** `_deferred/tests/test_nat_traversal.py`

**Changes:**
- Add test constants at top of file:
  ```python
  # Test-only credentials for TURN server mock — not real credentials
  TEST_TURN_USERNAME = "test_user"
  TEST_TURN_PASSWORD = "test_credential_placeholder"
  ```
- Replace hardcoded `username="user", password="pass"` with the constants throughout the file

---

## Fix 3: Enforce Lock File in CI Builds [Finding #4 — MEDIUM]

**Problem:** `requirements-lock.txt` exists with pinned versions but CI installs from `requirements.txt` (unpinned).

**File:** `.github/workflows/ci.yml`

**Changes:**
- In the `build` job (line 390): change `pip install -r requirements.txt` → `pip install -r requirements-lock.txt`
- In the `security` job (line 188): change `pip-audit -r requirements.txt` → `pip-audit -r requirements-lock.txt`
- In the `security` job (line 184): change `safety check -r requirements.txt` → `safety check -r requirements-lock.txt`
- Keep `requirements.txt` in `test` and `lint` jobs for development flexibility (floor pins are fine for test matrix)

---

## Fix 4: Harden CI Security Gates [Finding #5 — MEDIUM]

**Problem:** All security job steps use `continue-on-error: true` — they never block merges.

**File:** `.github/workflows/ci.yml`

**Changes:**
- **Remove** `continue-on-error: true` from `pip-audit` step (line 189) — known vulnerable deps must block
- **Remove** `continue-on-error: true` from Bandit step (line 181) — security lint violations must block
- **Keep** `continue-on-error: true` on Safety check (known for false positives on transitive deps)
- **Keep** `continue-on-error: true` on Trivy SARIF upload (external service, shouldn't block on upload failure)
- **Remove** `continue-on-error: true` from `mypy` in type-check job (line 90)
- **Remove** `continue-on-error: true` from `isort` in lint job (line 57)

---

## Fix 5: Cross-Entry Prompt Injection Defense [Finding #3 — MEDIUM]

**Problem:** When matching contracts, entries from different users are composed into one LLM prompt. A coordinated multi-entry injection (split across entries) could bypass per-entry sanitization.

**Files:** `src/sanitization.py`, `src/contract_matcher.py`

**Changes in `src/sanitization.py`:**
Add a new function `validate_composed_sections()`:
```python
def validate_composed_sections(
    sections: list[tuple[str, str]],
) -> None:
    """
    Validate that composed prompt sections don't contain cross-boundary
    injection attempts.

    Args:
        sections: List of (label, content) tuples that will be composed
                  into a single prompt.

    Raises:
        ValueError: If cross-entry injection is detected.
    """
    all_labels = {label for label, _ in sections}

    for label, content in sections:
        content_lower = content.lower()
        # Check if any entry references another entry's delimiters
        for other_label in all_labels:
            if other_label == label:
                continue
            if other_label.lower() in content_lower:
                raise ValueError(
                    f"Input rejected: cross-section reference detected in '{label}'"
                )

        # Check for delimiter forgery: [END ...] or [BEGIN ...] patterns
        if re.search(r"\[(BEGIN|END)\s+\w+", content, re.IGNORECASE):
            raise ValueError(
                f"Input rejected: delimiter pattern detected in '{label}'"
            )

    # Run injection detection on concatenated content
    combined = " ".join(content for _, content in sections)
    combined_lower = combined.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, combined_lower, re.IGNORECASE):
            raise ValueError(
                "Input rejected: injection pattern detected in composed prompt"
            )
```

**Changes in `src/contract_matcher.py` `_compute_match()`** (around line 218):
After individual sanitization (line 223), before building the prompt, add:
```python
from sanitization import validate_composed_sections

validate_composed_sections([
    ("CONTRACT_A_CONTENT", safe_content1),
    ("CONTRACT_A_INTENT", safe_intent1),
    ("CONTRACT_B_CONTENT", safe_content2),
    ("CONTRACT_B_INTENT", safe_intent2),
])
```

Wrap in try/except ValueError → return score 0 with "rejected by security check" reasoning.

Apply the same pattern to `_generate_proposal()` and `_mediate_negotiation()` if they also compose multi-entry prompts.

---

## Fix 6: Multi-Key Authentication with Expiry [Finding #1 — MEDIUM]

**Problem:** Single static `NATLANGCHAIN_API_KEY` with no rotation mechanism.

**File:** `src/api/utils.py`

**Changes:**
1. Add key parsing function above `require_api_key()`:
```python
def _parse_api_keys() -> list[tuple[str, str | None]]:
    """
    Parse API keys from environment.
    Supports NATLANGCHAIN_API_KEYS (comma-separated, optional expiry).
    Format: key1:2026-06-01,key2:2026-12-31,key3

    Returns list of (key, expiry_date_str_or_None).
    """
    keys_str = os.getenv("NATLANGCHAIN_API_KEYS", "")
    if keys_str:
        keys = []
        for entry in keys_str.split(","):
            entry = entry.strip()
            if ":" in entry:
                key, expiry = entry.rsplit(":", 1)
                keys.append((key, expiry))
            else:
                keys.append((entry, None))
        return keys

    # Fallback to single legacy key
    single = os.getenv("NATLANGCHAIN_API_KEY")
    if single:
        return [(single, None)]
    return []
```

2. Replace `API_KEY = os.getenv(...)` with:
```python
_API_KEYS = _parse_api_keys()
```

3. Update `require_api_key()` to iterate over `_API_KEYS`, checking each with `secrets.compare_digest()` and rejecting expired keys (compare `expiry` against `datetime.date.today()`).

4. Update `.env.example` to document the new `NATLANGCHAIN_API_KEYS` variable.

---

## Fix 7: Integrate Redis-Backed Rate Limiter [Finding #2 — MEDIUM]

**Problem:** In-process rate limiter doesn't share state across gunicorn workers.

**Files:** `_deferred/src/rate_limiter.py` → `src/rate_limiter.py`, `src/api/utils.py`

**Changes:**
1. Copy `_deferred/src/rate_limiter.py` → `src/rate_limiter.py` (replacing the existing simpler version that was already moved to deferred in a prior audit)
2. In `src/api/utils.py`:
   - Import `RateLimiter`, `RateLimitConfig` from `rate_limiter`
   - Replace the inline `rate_limit_store` dict, `_rate_limit_lock`, `check_rate_limit()` with:
     ```python
     _rate_limiter = RateLimiter(RateLimitConfig.from_env())

     def check_rate_limit() -> dict[str, Any] | None:
         client_ip = get_client_ip()
         result = _rate_limiter.check_limit(client_ip)
         if result.exceeded:
             return {
                 "error": "Rate limit exceeded",
                 "code": "RATE_LIMITED",
                 "retry_after": result.retry_after,
             }
         return None
     ```
   - Same pattern for LLM rate limiter (separate `RateLimiter` instance with stricter config)
   - Remove the FIXME comment
   - Function signatures remain the same — no downstream changes needed

---

## Fix 8: Trust-Level Annotations in Search Results [Finding #6 — LOW]

**Problem:** Search results return all entries equally with no trust indication.

**File:** `src/semantic_search.py`

**Changes in `search()` method** (around line 270):
Add trust indicators to each result:
```python
entry = self._entries_cache[idx]
results.append({
    "score": round(float(similarities[idx]), 4),
    "entry": entry,
    "trust_indicators": {
        "is_signed": bool(entry.get("metadata", {}).get("signature")),
        "validation_status": entry.get("validation_status", "unknown"),
    },
})
```

This is metadata enrichment only — no filtering or re-ranking. Consumers decide how to use it.

---

## Implementation Order

| Step | Fix | Finding | Risk | Effort |
|------|-----|---------|------|--------|
| 1 | Fix 1: Update cryptography version | #7 LOW | Low | ~2 lines |
| 2 | Fix 2: Remove test credential | #8 LOW | Low | ~5 lines |
| 3 | Fix 3: Enforce lock file in CI | #4 MEDIUM | Low | ~3 lines |
| 4 | Fix 4: Harden CI security gates | #5 MEDIUM | Low | ~5 lines removed |
| 5 | Fix 5: Cross-entry injection defense | #3 MEDIUM | Medium | ~40 lines added |
| 6 | Fix 6: Multi-key auth with expiry | #1 MEDIUM | Medium | ~50 lines added |
| 7 | Fix 7: Integrate Redis rate limiter | #2 MEDIUM | Medium | ~30 lines changed |
| 8 | Fix 8: Trust-level annotations | #6 LOW | Low | ~10 lines |

**Total:** ~8 files modified, ~140 lines added/changed.

---

## Testing Strategy

After all changes:
1. `python -m pytest tests/ -v` — verify zero regressions
2. Verify `require_api_key()` accepts valid keys, rejects expired keys (add unit test)
3. Verify `validate_composed_sections()` catches cross-entry injection (add unit test)
4. Verify rate limiter initializes with both memory and Redis backends
5. Verify search results include `trust_indicators` field
