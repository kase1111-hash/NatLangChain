# Agentic Security Audit v3.0 — NatLangChain

```
AUDIT METADATA
  Project:       NatLangChain
  Date:          2026-03-10
  Auditor:       claude-opus-4-6
  Commit:        4f82afe7bde71518324c859c7e7054ebedc34574
  Strictness:    STANDARD
  Context:       PROTOTYPE (alpha, single-node, no production users confirmed)

PROVENANCE ASSESSMENT
  Vibe-Code Confidence:   65%
  Human Review Evidence:  MINIMAL

LAYER VERDICTS
  L1 Provenance:       WARN
  L2 Credentials:      WARN
  L3 Agent Boundaries: WARN
  L4 Supply Chain:     WARN
  L5 Infrastructure:   PASS
```

---

## L1: PROVENANCE & TRUST ORIGIN

### 1.1 Vibe-Code Detection

| Indicator | Status | Evidence |
|-----------|--------|----------|
| No tests | **PASS** | 20+ test files exist, pytest configured in pyproject.toml, CI markers for slow/integration/e2e |
| No security config | **PASS** | `.env.example` present with full documentation, auth middleware exists, encryption module exists |
| AI boilerplate | **WARN** | 93 of 146 commits (64%) attributed to "Claude". Uniform formatting. TODO comments read like prompts (e.g., `# TODO: add language detection to reject gibberish inputs early`). However, commits show iterative refinement across 7 refocus phases — not a single-shot dump |
| Rapid commit history | **WARN** | Project started 2026-01-01, 146 commits in ~7 weeks. Many massive structural commits (`refocus: Phase 3 — Kill god file`). But clear iterative progression from Phase 1→7 |
| Polished README, hollow codebase | **PASS** | ~6,620 LOC across 35+ modules is substantive. 87KB SPEC.md is extensive but matches actual implementation. Multiple security review documents already exist |
| Bloated deps | **PASS** | 7 core dependencies for a project with blockchain, LLM validation, semantic search, and encryption. Proportionate to complexity |

**Verdict: WARN** — The codebase is predominantly AI-authored (64% Claude commits) with limited evidence of human security review. However, it shows genuine iterative refinement (7 refocus phases, security remediation commits), not a single vibe-coded dump. The risk is that security-critical code paths were generated without deep human understanding.

### 1.2 Human Review Evidence

| Check | Status | Evidence |
|-------|--------|----------|
| Security-focused commits | **PARTIAL** | Multiple security remediation commits exist (`Fix all 19 security findings`, `Implement cryptographic agent identity`), but these were also Claude-authored responding to Claude-authored audits — circular review |
| Security tooling in CI/CD | **FAIL** | No CI/CD configuration found (no `.github/workflows/`, no `Makefile` with security targets). Ruff includes bandit rules (`S` prefix) but no automated CI pipeline runs them |
| `.gitignore` excludes secrets | **PASS** | `.env` excluded. No `.pem`, `.key`, or credential files in gitignore but none appear in repo either |

### 1.3 The "Tech Preview" Trap

| Check | Status | Evidence |
|-------|--------|----------|
| Production traffic despite beta label | **LOW RISK** | Version `0.1.0-alpha` in pyproject.toml. No evidence of production deployment |
| Real credentials handled without review | **WARN** | System handles Anthropic API keys, encryption keys, and user API keys. `.env.example` documents them properly but no rotation mechanism exists |
| Disclaimers without protection | **PASS** | Alpha label is genuine — this is a prototype |

---

## L2: CREDENTIAL & SECRET HYGIENE

### 2.1 Secret Storage

| Check | Status | Evidence |
|-------|--------|----------|
| Plaintext creds in files | **PASS** | No hardcoded API keys found. `.env.example` uses placeholder `your_api_key_here` |
| API keys in client-side code | **N/A** | No frontend deployed (deferred to `_deferred/`) |
| Secrets in git history | **PASS** | No `.env` or credential files found in git history |
| `.env` committed | **PASS** | `.env` in `.gitignore` |

**One finding in deferred test code:**

```
[LOW] — Test Credential in Deferred Code
Layer:     2
Location:  _deferred/tests/test_nat_traversal.py:70
Evidence:  password="pass" in TURN server test
Risk:      Minimal — deferred test file, not production code
Fix:       Use fixture or env var for test credentials
```

### 2.2 Credential Scoping & Lifecycle

| Check | Status | Evidence |
|-------|--------|----------|
| Keys scoped to min permissions | **WARN** | Anthropic API key is passed as a single global key. No per-feature key scoping |
| Rotation mechanism | **FAIL** | No key rotation mechanism exists. Changing keys requires restart |
| Per-user credential isolation | **WARN** | Single API key authenticates all clients (via `NATLANGCHAIN_API_KEY`). No per-user keys |
| Credential delegation chain | **PASS** | Env var → memory only. Keys not logged or stored in chain data |

```
[MEDIUM] — No Credential Rotation Mechanism
Layer:     2
Location:  src/api/__init__.py:48, .env.example:40
Evidence:  NATLANGCHAIN_API_KEY is a single static key with no rotation path
Risk:      Compromised key requires manual intervention and service restart
Fix:       Implement key rotation endpoint or support multiple valid keys with expiry
```

### 2.3 Machine Credential Exposure

| Check | Status | Evidence |
|-------|--------|----------|
| OAuth tokens stored with rigor | **N/A** | No OAuth implementation |
| API key as sole identity boundary | **WARN** | Single `X-API-Key` header is the only identity mechanism |
| Credential aggregation risk | **LOW** | Single key, not per-user table |
| Key revocation path | **FAIL** | No revocation mechanism — must change env var and restart |
| Billing attack surface | **WARN** | Anthropic API key is used for validation. Rate limiting exists (10 req/60s for LLM endpoints) but no spend cap |

```
[MEDIUM] — LLM Billing Attack Surface
Layer:     2
Location:  src/api/utils.py:28 (rate limiter), src/validator.py
Evidence:  LLM rate limit is 10 requests per 60 seconds per IP, but rate limiter uses
           in-process dict that doesn't share across gunicorn workers (acknowledged FIXME)
Risk:      Attacker could bypass rate limits across workers and run up Anthropic API costs
Fix:       Enable Redis-backed rate limiting (already implemented in src/rate_limiter.py)
           for production deployments
```

---

## L3: AGENT BOUNDARY ENFORCEMENT

### 3.1 Agent Permission Model

| Check | Status | Evidence |
|-------|--------|----------|
| Default permissions | **PASS** | Auth required by default (`NATLANGCHAIN_REQUIRE_AUTH=true`) |
| Privilege escalation | **PASS** | No privilege levels exist — flat access model. API key either works or doesn't |
| File/network/exec boundaries | **PASS** | No file system access, no outbound network (except Anthropic API), no command execution |
| Least-privilege enforcement | **PASS** | Module manifest system (YAML files in `src/manifests/`) declares capabilities per module |
| Human-in-the-loop gates | **N/A** | No destructive operations in the API — ledger is append-only |

### 3.2 Prompt Injection Defense

| Check | Status | Evidence |
|-------|--------|----------|
| External inputs sanitized | **PASS** | `src/sanitization.py` applies Unicode NFKC normalization, truncation, and 11 regex patterns before LLM calls |
| Agent outputs validated | **PASS** | LLM responses validated against expected JSON schema (decision enum, intent_match boolean) in `src/validator.py` |
| System/user separation | **PASS** | Safe delimiters `[BEGIN CONTENT - N chars]...[END CONTENT]` separate untrusted input from system prompts |
| Multi-modal injection | **N/A** | No image/PDF/audio processing |
| Indirect injection via data | **WARN** | Chain entries from other users are included in LLM prompts during contract matching. A malicious entry could contain injection payloads that survive sanitization |

```
[MEDIUM] — Cross-Entry Prompt Injection in Contract Matching
Layer:     3
Location:  src/contract_matcher.py (match scoring prompts)
Evidence:  When matching contracts, entries from different users are included in the
           same LLM prompt. Sanitization runs on individual entries but coordinated
           multi-entry injection (split payload across entries) is not defended against
Risk:      Attacker could craft entries that, when combined in a matching prompt,
           form an injection payload that bypasses per-entry sanitization
Fix:       Add cross-entry sanitization check when composing multi-entry prompts;
           consider output validation specifically for match scoring responses
```

### 3.3 Memory Poisoning

| Check | Status | Evidence |
|-------|--------|----------|
| Long-term memory | **WARN** | The blockchain itself IS persistent memory. All entries are permanent and immutable |
| Source tracking | **PASS** | Each entry has `author` field and optional Ed25519 signature |
| Audit/purge capability | **FAIL** | Blockchain is append-only by design. Poisoned entries cannot be removed |
| Untrusted source isolation | **WARN** | All entries are treated equally in semantic search and contract matching regardless of author trust level |

```
[LOW] — No Trust-Level Differentiation for Chain Entries
Layer:     3
Location:  src/semantic_search.py, src/contract_matcher.py
Evidence:  Semantic search and contract matching return results from all authors equally.
           No trust score or reputation system exists
Risk:      Malicious entries rank alongside legitimate ones in search results
Fix:       Consider author reputation scoring or flagging unsigned entries in results
```

### 3.4 Agent-to-Agent Trust

| Check | Status | Evidence |
|-------|--------|----------|
| Agent identity verification | **PARTIAL** | Ed25519 identity system exists (`src/identity.py`) but disabled by default |
| Instructions from agents as untrusted | **N/A** | No agent-to-agent communication currently |
| Capability delegation logging | **N/A** | Single-node architecture |
| Cross-agent injection | **N/A** | No multi-agent system |
| ZombAI recruitment | **N/A** | Agents don't execute arbitrary instructions from entries |

---

## L4: SUPPLY CHAIN & DEPENDENCY TRUST

### 4.1 Plugin/Skill Supply Chain

| Check | Status |
|-------|--------|
| Plugin system | **N/A** — No plugin/skill system. All code is first-party |

### 4.2 MCP Server Trust

| Check | Status |
|-------|--------|
| MCP servers | **N/A** — No MCP integration |

### 4.3 Dependency Audit

| Check | Status | Evidence |
|-------|--------|----------|
| `pip audit` run | **FAIL** | `pip-audit` not installed. Could not verify vulnerability status |
| Stale dependencies | **WARN** | Versions use floor pins (`>=`) not ceiling pins. `cryptography>=41.0.0` — current installed is `41.0.7` while latest is 44.x |
| Versions pinned | **WARN** | All dependencies use `>=` minimum pins with no upper bound. Could pull in breaking changes |
| Transitive deps audited | **FAIL** | No lock file (`requirements.lock`, `poetry.lock`, or `pip-compile` output) |

```
[MEDIUM] — No Dependency Lock File
Layer:     4
Location:  requirements.txt, pyproject.toml
Evidence:  All dependencies use floor-only version pins (>=). No lock file pins
           exact transitive dependency versions
Risk:      Non-reproducible builds. A compromised or broken transitive dependency
           could be silently pulled in
Fix:       Add pip-compile (pip-tools) or poetry.lock to pin all transitive dependencies.
           Run pip-audit in CI
```

```
[LOW] — Outdated cryptography Library
Layer:     4
Location:  pyproject.toml:46
Evidence:  cryptography>=41.0.0 installed as 41.0.7; current release is 44.x
Risk:      Missing security patches from 3 major versions of updates
Fix:       Update to cryptography>=43.0.0 minimum; ideally pin to latest
```

---

## L5: INFRASTRUCTURE & RUNTIME

### 5.1 Database Security

| Check | Status | Evidence |
|-------|--------|----------|
| RLS enabled | **N/A** | Default storage is JSON file, not multi-tenant database |
| DB not publicly accessible | **PASS** | PostgreSQL backend requires explicit `DATABASE_URL` config |
| Connection string not in client code | **PASS** | Via env var only |
| Read/write separation | **N/A** | Single-user model |

### 5.2 BaaS Configuration

**N/A** — No BaaS (Supabase, Firebase, etc.) used.

### 5.3 Network & Hosting

| Check | Status | Evidence |
|-------|--------|----------|
| HTTPS everywhere | **WARN** | HSTS supported but disabled by default (`NATLANGCHAIN_ENABLE_HSTS=false`). No TLS termination built in |
| CORS restricted | **PASS** | Empty by default (blocks cross-origin). Wildcard `*` explicitly rejected with warning |
| Rate limiting | **PASS** | Per-IP rate limiting on all endpoints. Stricter limits on LLM endpoints (10/60s) |
| Error messages don't leak internals | **PASS** | Custom error handlers return generic messages. No stack traces exposed |
| Security event logging | **PASS** | Secret scanner logs warnings. Rate limit violations logged |

### 5.4 Deployment Pipeline

| Check | Status | Evidence |
|-------|--------|----------|
| CI/CD pipelines | **FAIL** | No CI/CD configuration found |
| Secrets injected at runtime | **PASS** | All secrets via env vars, not baked into code |
| Dev/staging/prod isolation | **N/A** | No deployment infrastructure |
| Rollback capability | **N/A** | No deployment infrastructure |

```
[MEDIUM] — No CI/CD Pipeline
Layer:     5
Location:  (missing .github/workflows/ or equivalent)
Evidence:  No automated CI/CD. Ruff (with bandit rules), pytest, and mypy are
           configured but never run automatically
Risk:      Security regressions can be introduced without automated gates
Fix:       Add GitHub Actions workflow running: ruff check, mypy, pytest, pip-audit
```

### 5.5 Regulatory Compliance

| Check | Status | Evidence |
|-------|--------|----------|
| EU CRA compliance | **N/A** | Alpha prototype, not commercially distributed |
| PII handling | **WARN** | Chain entries may contain PII in natural language. Encryption at rest is available but optional |
| AI-generated code review | **WARN** | 64% of code is AI-generated. Two prior security audits were also AI-generated (circular review) |

---

## FINDINGS SUMMARY

| # | Severity | Title | Layer |
|---|----------|-------|-------|
| 1 | **MEDIUM** | No Credential Rotation Mechanism | L2 |
| 2 | **MEDIUM** | LLM Billing Attack Surface (rate limiter worker isolation) | L2 |
| 3 | **MEDIUM** | Cross-Entry Prompt Injection in Contract Matching | L3 |
| 4 | **MEDIUM** | No Dependency Lock File | L4 |
| 5 | **MEDIUM** | No CI/CD Pipeline | L5 |
| 6 | **LOW** | No Trust-Level Differentiation for Chain Entries | L3 |
| 7 | **LOW** | Outdated cryptography Library | L4 |
| 8 | **LOW** | Test Credential in Deferred Code | L2 |

---

## STRENGTHS

The codebase demonstrates security awareness significantly above typical vibe-coded projects:

1. **Defense-in-depth for prompt injection** — Unicode normalization, truncation, pattern matching, safe delimiters, and output schema validation form a multi-layer defense
2. **Restrictive defaults** — Auth required, CORS blocked, wildcard `*` explicitly rejected, CSP set to `default-src 'none'`
3. **Outbound secret scanning** — Unusual and commendable. Responses are scanned for accidentally leaked credentials before leaving the server
4. **Security headers** — Comprehensive set including COOP, CORP, Permissions-Policy, Referrer-Policy
5. **Module manifest system** — Declares per-module capabilities (network, filesystem, shell) enabling least-privilege auditing
6. **Ed25519 identity system** — Proper cryptographic signing for entry authenticity (though disabled by default)
7. **AES-256-GCM encryption** — PBKDF2 with 1M iterations exceeds OWASP 2023 minimum. Proper random salt/IV per operation
8. **Debug mode lock** — Prevents running with debug=true AND auth=false simultaneously

---

## RECOMMENDATIONS (Priority Order)

### Immediate (this week)

1. **Add CI/CD pipeline** with `ruff check`, `pytest`, `pip-audit`, and `mypy` gates
2. **Generate a dependency lock file** using `pip-compile` or equivalent
3. **Update `cryptography`** to latest stable (44.x)

### Short-term (this month)

4. **Enable Redis-backed rate limiting** for any multi-worker deployment
5. **Add cross-entry sanitization** for contract matching prompts
6. **Implement API key rotation** supporting multiple valid keys with expiry
7. **Enable Ed25519 identity by default** — the code exists but is opt-in

### Medium-term

8. **Get human security review** — The circular AI-audits-AI-code pattern is a systemic risk. At least one human with security expertise should review the prompt injection defenses and cryptographic implementations
9. **Add PII detection and handling** — natural language entries are likely to contain personal data
10. **Implement author reputation/trust scoring** for search and matching results

---

## METHODOLOGY

This audit followed the [Agentic Security Audit v3.0](https://github.com/kase1111-hash/Claude-prompts/blob/main/vibe-check.md) framework, aligned with [OWASP Top 10 for Agentic Applications (2026)](https://owasp.org/www-project-top-10-for-agentic-applications/). All five layers were evaluated. No layers were skipped.

Tools used: static analysis (grep/ruff config review), git history analysis, dependency enumeration, code reading. No dynamic testing was performed (no running instance available).

---

*"Agent usefulness correlates with access level. Sandboxing solves security but cripples functionality." — This audit makes the tradeoffs visible so humans can decide.*
