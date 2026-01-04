# NatLangChain Security Documentation

**Last Updated:** January 2026
**Status:** All HIGH and MEDIUM severity issues resolved

This document consolidates all security audits, findings, and configuration for NatLangChain.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Security Configuration](#security-configuration)
3. [Codebase Security Audit](#codebase-security-audit)
4. [Security Sweep Results](#security-sweep-results)
5. [Boundary Integration Security](#boundary-integration-security)
6. [Security Controls Reference](#security-controls-reference)
7. [Production Checklist](#production-checklist)

---

## Executive Summary

### Overall Security Posture: EXCELLENT

The NatLangChain codebase has undergone comprehensive security audits with all critical and high-severity issues resolved:

| Audit Area | Status | Issues Found | Issues Fixed |
|------------|--------|--------------|--------------|
| Codebase Security | PATCHED | 9 | 9 |
| Backdoor Sweep | ALL CLEAR | 0 | N/A |
| Command Injection | FIXED | 1 CRITICAL | 1 |
| SSRF Protection | IMPLEMENTED | 1 HIGH | 1 |
| Input Validation | IMPLEMENTED | 1 HIGH | 1 |

### Key Security Features

- API key authentication (opt-in)
- Rate limiting (100 req/60s default)
- Request size limits (16MB)
- Security headers on all responses
- CORS configuration
- SHA-256 for all hashing
- SSRF protection on P2P endpoints
- Input validation for firewall commands

---

## Security Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_DEBUG` | `false` | Enable debug mode (development only) |
| `NATLANGCHAIN_API_KEY` | None | API key for authentication |
| `NATLANGCHAIN_REQUIRE_AUTH` | `false` | Require API key for all requests |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per rate limit window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `CORS_ALLOWED_ORIGINS` | `*` | Allowed CORS origins |
| `NATLANGCHAIN_TRUSTED_PROXIES` | None | Comma-separated trusted proxy IPs |

### Production Configuration

```bash
# Required for production
export FLASK_DEBUG=false
export NATLANGCHAIN_API_KEY=$(openssl rand -hex 32)
export NATLANGCHAIN_REQUIRE_AUTH=true
export CORS_ALLOWED_ORIGINS=https://your-domain.com

# Optional tuning
export RATE_LIMIT_REQUESTS=50
export RATE_LIMIT_WINDOW=60
export NATLANGCHAIN_TRUSTED_PROXIES=10.0.0.1,10.0.0.2
```

---

## Codebase Security Audit

**Date:** January 1, 2026
**Scope:** Full codebase security review (40+ Python files)

### Patched Issues

#### HIGH SEVERITY (All Fixed)

| Issue | Location | Fix |
|-------|----------|-----|
| API Authentication | `src/api.py` | Added `require_api_key` decorator |
| Debug Mode | `src/api.py` | Environment variable controlled, defaults to `false` |
| Rate Limiting | `src/api.py` | IP-based rate limiting with configurable limits |
| Request Size | `src/api.py` | 16MB limit via `MAX_CONTENT_LENGTH` |

#### MEDIUM SEVERITY (All Fixed)

| Issue | Location | Fix |
|-------|----------|-----|
| Unbounded Loops | `src/validator.py` | `MAX_VALIDATORS = 10` |
| CORS Configuration | `src/api.py` | Configurable origins via env var |
| MD5 for Caching | `src/mobile_deployment.py` | Replaced with SHA-256 |

#### LOW SEVERITY

| Issue | Status |
|-------|--------|
| Input Validation | Schema validation recommended for future |
| Security Headers | PATCHED - All standard headers added |

### Positive Findings (No Issues)

| Area | Status |
|------|--------|
| Hardcoded Secrets | PASS - Uses `secrets.token_hex()` |
| Command Injection | PASS - No dangerous `eval()`/`exec()` |
| Path Traversal | PASS - No user-controlled paths |
| SQL Injection | PASS - No SQL database |
| Insecure Deserialization | PASS - Only `json.loads()` |
| SSL/TLS Verification | PASS - No `verify=False` |
| Cryptographic Algorithms | PASS - SHA-256, ECDSA, proper FIDO2 |

---

## Security Sweep Results

**Date:** January 1, 2026
**Scope:** Full codebase backdoor and exploit sweep

### Summary: ALL CLEAR

| Category | Status |
|----------|--------|
| Hardcoded Secrets | PASS (test files only) |
| eval/exec Usage | PASS (proper usage only) |
| pickle Deserialization | PASS (not used) |
| shell=True Usage | PASS (refactored to list-based) |
| Backdoor Patterns | PASS (none found) |
| Hidden Endpoints | PASS (none found) |
| SQL Injection | PASS |
| Path Traversal | PASS |
| Open Redirects | PASS |
| YAML Deserialization | PASS (uses safe_load) |
| Crypto Randomness | PASS (uses secrets module) |
| SSL Verification | PASS |
| Debug Mode | PASS |
| Bypass Flags | PASS (properly blocked) |

### Security Controls Present

**Input Validation:**
```python
def validate_ip_address(ip: str) -> tuple[bool, str | None]:
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '{', '}', ...]
    # Validates and blocks injection attempts
```

**SSRF Protection:**
```python
BLOCKED_IP_RANGES = [
    "10.0.0.0/8",       # Private
    "172.16.0.0/12",    # Private
    "192.168.0.0/16",   # Private
    "169.254.0.0/16",   # AWS metadata
    "127.0.0.0/8",      # Localhost
]
```

**Forbidden Metadata Fields:**
```python
FORBIDDEN_METADATA_KEYS = {
    "__override__", "__bypass__", "__admin__", "__system__",
    "skip_validation", "bypass_validation", "force_accept",
}
```

---

## Boundary Integration Security

### Understanding Boundary Daemon Limitations

The Boundary Daemon (external repository) provides **detection and monitoring** but not enforcement. NatLangChain includes `src/security_enforcement.py` to add actual prevention:

| Capability | Boundary Daemon | NatLangChain Enforcement |
|------------|-----------------|-------------------------|
| Network Blocking | Detection only | iptables/nftables rules |
| USB Blocking | Detection only | udev rules |
| Process Sandboxing | Not provided | firejail/seccomp |
| Daemon Watchdog | Not provided | Self-healing watchdog |
| Audit Logs | Basic | Hash-chained, append-only |

### Enforcement API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/security/enforcement/status` | GET | Get enforcement capabilities |
| `/security/enforcement/mode` | POST | Enforce a boundary mode |
| `/security/enforcement/network/block` | POST | Block all network |
| `/security/enforcement/usb/block` | POST | Block USB storage |
| `/security/enforcement/sandbox/run` | POST | Run sandboxed command |
| `/security/enforcement/audit/verify` | GET | Verify audit log integrity |

### Requirements for Enforcement

- **Root/sudo privileges** for network and USB enforcement
- **Linux** for seccomp, namespaces, udev
- **iptables or nftables** for network blocking
- **firejail, unshare, or bubblewrap** for sandboxing

---

## Security Controls Reference

### Input Validation Functions

Located in `src/security_enforcement.py`:

```python
validate_ip_address(ip)      # Validates IP format, blocks injection chars
validate_port(port)          # Validates port range (1-65535)
validate_interface_name(if)  # Validates interface name pattern
sanitize_log_prefix(prefix)  # Sanitizes to alphanumeric only
```

### SSRF Protection

Located in `src/api/ssrf_protection.py`:

- 18 blocked IP ranges (private networks, localhost, metadata services)
- 11 blocked hosts (cloud metadata endpoints)
- URL validation before any outbound requests

### X-Forwarded-For Protection

- NOT trusted by default (secure default)
- Must configure `NATLANGCHAIN_TRUSTED_PROXIES`
- Uses rightmost untrusted IP (harder to spoof)

---

## Production Checklist

### Required Before Production

- [ ] Set `FLASK_DEBUG=false`
- [ ] Generate and set `NATLANGCHAIN_API_KEY`
- [ ] Set `NATLANGCHAIN_REQUIRE_AUTH=true`
- [ ] Configure `CORS_ALLOWED_ORIGINS` to specific domains
- [ ] Configure `NATLANGCHAIN_TRUSTED_PROXIES` if behind proxy

### Recommended Configuration

- [ ] Set up PostgreSQL for persistent storage
- [ ] Enable Redis for distributed rate limiting
- [ ] Configure TLS via cert-manager or reverse proxy
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerting (Slack/PagerDuty)
- [ ] Enable RBAC (`ENABLE_RBAC=true`)
- [ ] Review and apply network policies

### Verification Commands

```bash
# Verify debug mode is configurable
grep "FLASK_DEBUG" src/api.py

# Verify rate limiting is active
grep "check_rate_limit" src/api.py

# Verify security headers
grep "X-Content-Type-Options" src/api.py

# Verify input validation
grep "validate_ip_address\|validate_port" src/security_enforcement.py

# Verify SHA-256 usage
grep "sha256" src/mobile_deployment.py
```

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security concerns to the repository maintainer
3. Include detailed reproduction steps
4. Allow reasonable time for a fix before disclosure

---

## Audit History

| Date | Audit Type | Findings |
|------|------------|----------|
| 2026-01-01 | Codebase Security | 9 issues found, all patched |
| 2026-01-01 | Backdoor Sweep | All clear |
| 2026-01-01 | Command Injection | 1 critical fixed |
| 2026-01-01 | SSRF Protection | Implemented |
| 2026-01-01 | Boundary Integration | Enforcement added |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
