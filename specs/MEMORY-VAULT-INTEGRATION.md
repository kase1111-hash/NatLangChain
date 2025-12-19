# Memory Vault ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Memory Vault is the secure, offline-capable, owner-sovereign storage subsystem for work artifacts. This specification defines how Memory Vault integrates with NatLangChain to provide Proof-of-Effort receipts (MP-02).

## Purpose

Enable Memory Vault to:
1. Store raw work signals (code, text, audio transcripts)
2. Generate cryptographic hashes for NatLangChain references
3. Provide verification without exposing raw content
4. Support WORM archival for legal compliance

## Core Principle

> "Effort that cannot be shown is effort that cannot be valued."

Memory Vault stores the evidence; NatLangChain records the receipts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Vault                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Signal Capture Layer                          │  │
│  │  - Code commits (git hooks)                                │  │
│  │  - Text edits (editor plugins)                             │  │
│  │  - Voice transcripts (optional)                            │  │
│  │  - Command history                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Encrypted Storage                             │  │
│  │  - Owner-controlled encryption keys                        │  │
│  │  - Air-gapped capability                                   │  │
│  │  - Append-only structure                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Hash & Receipt Generator                      │  │
│  │  - SHA-256 of signals                                      │  │
│  │  - Time-stamped receipts                                   │  │
│  │  - NatLangChain submission                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NatLangChain API                             │
│  POST /entry (effort receipt)                                   │
│  GET  /receipt/verify                                           │
└─────────────────────────────────────────────────────────────────┘
```

## API Contract

### 1. Signal Storage

Memory Vault captures work signals:

```python
# Internal Memory Vault API
POST /signal/store
{
    "signal_type": "code_commit",
    "source": "git",
    "timestamp": "2025-12-19T10:30:00Z",
    "content": "def calculate_alignment(...)...",
    "metadata": {
        "repo": "natlangchain",
        "branch": "main",
        "commit_hash": "abc123...",
        "files_changed": ["src/alignment.py"],
        "lines_added": 150,
        "lines_removed": 20
    }
}

Response:
{
    "signal_id": "SIG-001",
    "content_hash": "SHA256:abc123...",
    "stored_at": "2025-12-19T10:30:01Z",
    "encrypted": true
}
```

### 2. Effort Segmentation

Group signals into effort segments:

```python
POST /effort/segment
{
    "segment_id": "SEG-001",
    "time_bounds": {
        "start": "2025-12-19T09:00:00Z",
        "end": "2025-12-19T17:00:00Z"
    },
    "signals": ["SIG-001", "SIG-002", "SIG-003", ...],
    "segmentation_rule": "daily_work_session",
    "summary": "Implemented alignment algorithm and tests"
}

Response:
{
    "segment_id": "SEG-001",
    "signal_count": 47,
    "aggregate_hash": "SHA256:xyz789...",
    "ready_for_receipt": true
}
```

### 3. Receipt Generation for NatLangChain

```python
# Memory Vault → NatLangChain
POST /entry
{
    "content": "Effort receipt for alignment algorithm implementation. 8 hours of focused development including 47 tracked signals.",
    "author": "alice",
    "intent": "Record proof of effort",
    "metadata": {
        "is_effort_receipt": true,
        "mp02_compliant": true,

        "vault_segment_ref": "SEG-001",
        "vault_instance": "vault.alice.local",

        "time_bounds": {
            "start": "2025-12-19T09:00:00Z",
            "end": "2025-12-19T17:00:00Z"
        },

        "signal_summary": {
            "total_signals": 47,
            "signal_types": {
                "code_commit": 12,
                "text_edit": 30,
                "command": 5
            }
        },

        "signal_hashes": [
            "SHA256:abc123...",
            "SHA256:def456...",
            "SHA256:ghi789..."
        ],

        "aggregate_hash": "SHA256:xyz789...",

        "validation_metadata": {
            "coherence_score": 0.92,
            "progression_detected": true,
            "continuity_verified": true,
            "validator_model": "claude-3-sonnet",
            "validator_version": "2025-12"
        },

        "observer_id": "vault.alice.local",
        "prior_receipts": ["R-100"]
    }
}

Response:
{
    "status": "success",
    "receipt_id": "R-101",
    "block": 200,
    "entry_index": 3
}
```

### 4. Third-Party Verification

External parties can verify receipts without accessing raw content:

```python
# Verify effort receipt
POST /receipt/verify
{
    "receipt_id": "R-101",
    "vault_segment_ref": "SEG-001",
    "vault_instance": "vault.alice.local",
    "challenge": {
        "signal_index": 5,
        "expected_hash": "SHA256:abc123..."
    }
}

Response:
{
    "verified": true,
    "hash_match": true,
    "timestamp_valid": true,
    "chain_integrity": true,
    "verifier_notes": "All 47 signals hash-verified against ledger"
}
```

## Signal Types

| Signal Type | Capture Method | Hash Content |
|-------------|---------------|--------------|
| `code_commit` | Git post-commit hook | Diff + metadata |
| `text_edit` | Editor plugin | Content delta |
| `voice_transcript` | Audio processing | Transcript text |
| `command_history` | Shell hook | Command + output |
| `research_note` | Manual entry | Note content |

## Validation Rules (MP-02)

### Validators MAY assess:
- Linguistic coherence
- Conceptual progression
- Internal consistency
- Indicators of synthesis vs duplication

### Validators MUST:
- Produce deterministic summaries
- Disclose model identity and version
- Preserve dissent and uncertainty

### Validators MUST NOT:
- Declare effort as valuable
- Assert originality or ownership
- Collapse ambiguous signals into certainty

## Privacy & Sovereignty

### Owner Control
- All encryption keys held by owner
- Air-gapped operation supported
- No cloud dependency required

### Selective Disclosure
- Hash verification without content exposure
- Proof of effort without revealing work
- Auditor access with explicit consent

### Revocation
- Future observation can be revoked
- Past receipts remain immutable
- Right to be forgotten for raw signals (not hashes)

## Implementation Tasks

### Memory Vault Side
- [ ] Implement signal capture hooks (git, editor, shell)
- [ ] Build encrypted storage layer
- [ ] Create effort segmentation engine
- [ ] Add hash generation pipeline
- [ ] Implement NatLangChain submission client
- [ ] Build verification API

### NatLangChain Side
- [ ] Add effort receipt entry type
- [ ] Implement `/receipt/verify` endpoint
- [ ] Add MP-02 validation rules
- [ ] Support vault reference fields
- [ ] Build receipt chain linking

## Dependencies

- **IntentLog**: For reasoning context
- **NatLangChain**: For receipt recording
- **Common**: For schema definitions
- **Boundary Daemon**: For privacy enforcement

## WORM Archival

Memory Vault supports WORM (Write Once Read Many) export:

```python
POST /archive/export
{
    "segments": ["SEG-001", "SEG-002"],
    "format": "WORM_LTO",
    "include_raw_signals": false,
    "include_hashes": true,
    "legal_certificate": true
}

Response:
{
    "archive_id": "ARCH-001",
    "export_path": "/mnt/lto/vault_export_2025-12-19.tar.gz.enc",
    "size_bytes": 1048576,
    "integrity_hash": "SHA256:...",
    "legal_certificate_included": true
}
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
