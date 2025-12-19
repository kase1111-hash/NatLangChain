# Learning Contracts ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Learning Contracts are human-ratified agreements that govern what AI agents may learn, how they may generalize, and when they must forget. This specification defines how Learning Contracts are recorded on NatLangChain and enforced by Agent OS.

## Purpose

Enable Learning Contracts to:
1. Define AI learning boundaries
2. Record learning permissions on-chain
3. Enable revocation of learning rights
4. Provide audit trails for AI behavior

## Core Principle

> "AI may observe and learn, but only within explicit, revocable human consent."

Learning Contracts put humans in control of AI training.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Human Owner                              │
│  "I consent to my agent learning from my code style,             │
│   but not from private communications."                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Learning Contract                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Learning Scope                                │  │
│  │  - What may be observed                                    │  │
│  │  - How learning may be generalized                         │  │
│  │  - Retention policies                                      │  │
│  │  - Revocation rules                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
┌─────────────────────────┐    ┌──────────────────────────────────┐
│     NatLangChain        │    │          Agent OS                │
│  (Records contract)     │    │  (Enforces contract)             │
└─────────────────────────┘    └──────────────────────────────────┘
```

## Learning Contract Schema

```python
{
    "contract_id": "LC-001",
    "version": 1,
    "owner": "alice",
    "agent_id": "agent_os_instance_1",
    "created_at": "2025-12-19T09:00:00Z",
    "status": "active",

    # What the agent may observe
    "observation_scope": {
        "allowed": [
            {
                "type": "code_style",
                "sources": ["github.com/alice/*"],
                "description": "May observe coding patterns and style preferences"
            },
            {
                "type": "scheduling_preferences",
                "sources": ["calendar"],
                "description": "May learn scheduling preferences"
            }
        ],
        "prohibited": [
            {
                "type": "private_communications",
                "sources": ["email", "messages"],
                "description": "Must not access or learn from private messages"
            },
            {
                "type": "financial_data",
                "sources": ["bank_accounts", "transactions"],
                "description": "Must not access financial information"
            }
        ]
    },

    # How learning may be generalized
    "generalization_rules": {
        "allowed": [
            {
                "from": "code_style",
                "to": "code_suggestions",
                "constraint": "Only for owner's projects"
            }
        ],
        "prohibited": [
            {
                "from": "any_observation",
                "to": "external_training",
                "description": "May not contribute to external model training"
            }
        ]
    },

    # Retention policies
    "retention": {
        "default_retention": "session_only",
        "persistent_allowed": ["code_style"],
        "persistent_duration": "1_year",
        "right_to_forget": true,
        "forget_on_revocation": true
    },

    # Revocation rules
    "revocation": {
        "revocable": true,
        "revocation_notice": "immediate",
        "revocation_effects": [
            "Stop all observation",
            "Delete all learned patterns",
            "Report deletion confirmation"
        ]
    },

    # Signatures
    "signatures": {
        "owner": {
            "signer": "alice",
            "timestamp": "2025-12-19T09:00:00Z",
            "signature": "..."
        }
    }
}
```

## API Contract

### 1. Recording Learning Contract on NatLangChain

```python
POST /entry
{
    "content": "Learning Contract LC-001: I, Alice, grant my AI agent permission to observe and learn from my coding style in my GitHub repositories. The agent may generalize this to provide code suggestions for my projects only. The agent may NOT access private communications or financial data. This consent is revocable at any time with immediate effect.",

    "author": "alice",
    "intent": "Establish AI learning boundaries",

    "metadata": {
        "is_learning_contract": true,
        "learning_contract_id": "LC-001",
        "learning_contract_version": 1,
        "agent_id": "agent_os_instance_1",

        "observation_scope": {
            "allowed": ["code_style"],
            "prohibited": ["private_communications", "financial_data"]
        },

        "generalization_scope": "code_suggestions_for_owner_only",

        "retention_policy": {
            "default": "session_only",
            "persistent": ["code_style"],
            "duration": "1_year"
        },

        "revocation": {
            "revocable": true,
            "notice": "immediate"
        }
    }
}

Response:
{
    "status": "success",
    "learning_contract_id": "LC-001",
    "block": 300,
    "entry_index": 0,
    "hash": "000lc..."
}
```

### 2. Updating Learning Contract

```python
POST /entry
{
    "content": "Learning Contract LC-001 Amendment: I extend observation scope to include my calendar for scheduling preferences. All other terms remain unchanged.",

    "author": "alice",
    "intent": "Amend learning contract",

    "metadata": {
        "is_learning_contract": true,
        "learning_contract_id": "LC-001",
        "learning_contract_version": 2,
        "amends_version": 1,
        "amendment_type": "scope_extension",

        "changes": {
            "observation_scope": {
                "added": ["scheduling_preferences"]
            }
        }
    }
}
```

### 3. Revoking Learning Contract

```python
POST /entry
{
    "content": "Learning Contract LC-001 Revocation: I hereby revoke all learning permissions granted under LC-001. Agent must immediately cease observation and delete all learned patterns.",

    "author": "alice",
    "intent": "Revoke learning contract",

    "metadata": {
        "is_learning_contract": true,
        "learning_contract_id": "LC-001",
        "learning_contract_version": 3,
        "revocation": true,
        "revocation_effective": "immediate",

        "required_actions": [
            "cease_observation",
            "delete_learned_patterns",
            "confirm_deletion"
        ]
    }
}

Response:
{
    "status": "success",
    "learning_contract_id": "LC-001",
    "revocation_recorded": true,
    "block": 350,
    "agent_notification_sent": true
}
```

### 4. Agent Compliance Verification

```python
POST /learning-contract/verify-compliance
{
    "agent_id": "agent_os_instance_1",
    "learning_contract_id": "LC-001",

    "action_to_verify": {
        "type": "observation",
        "source": "email",
        "timestamp": "2025-12-19T10:00:00Z"
    }
}

Response:
{
    "compliant": false,
    "violation": {
        "type": "prohibited_observation",
        "source": "email",
        "prohibition": "private_communications",
        "learning_contract_ref": {"block": 300, "entry": 0}
    },
    "action": "BLOCK_AND_REPORT"
}
```

### 5. Learning Audit

```python
GET /learning-contract/{lc_id}/audit

Response:
{
    "learning_contract_id": "LC-001",
    "owner": "alice",
    "agent_id": "agent_os_instance_1",

    "history": [
        {
            "version": 1,
            "timestamp": "2025-12-19T09:00:00Z",
            "action": "created",
            "block": 300
        },
        {
            "version": 2,
            "timestamp": "2025-12-19T12:00:00Z",
            "action": "amended",
            "block": 320
        }
    ],

    "compliance_record": {
        "total_observations": 1500,
        "compliant_observations": 1500,
        "violations": 0
    },

    "learned_patterns": {
        "code_style": {
            "patterns_learned": 45,
            "last_updated": "2025-12-19T15:00:00Z"
        }
    }
}
```

## Enforcement Flow

```
┌──────────────────────────────────────────────────────────────┐
│                   Agent Action Request                        │
│  "Observe user's email to learn communication style"          │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                Learning Contract Checker                      │
│  1. Retrieve active Learning Contract                         │
│  2. Check if action is in allowed scope                       │
│  3. Check if action is in prohibited scope                    │
└───────────────────────────────┬──────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
┌───────────────────────────┐      ┌───────────────────────────┐
│        ALLOWED            │      │       PROHIBITED          │
│  Action proceeds          │      │  Action blocked           │
│  Learning recorded        │      │  Violation logged         │
│  Audit trail updated      │      │  Owner notified           │
└───────────────────────────┘      └───────────────────────────┘
```

## Right to Be Forgotten

When revocation occurs:

```python
POST /learning-contract/forget
{
    "learning_contract_id": "LC-001",
    "agent_id": "agent_os_instance_1",
    "forget_scope": "all_learned_patterns",

    "verification": {
        "owner_signature": "...",
        "revocation_block": 350
    }
}

Response:
{
    "forget_request_id": "FORGET-001",
    "status": "processing",

    "patterns_to_delete": [
        {"type": "code_style", "count": 45},
        {"type": "scheduling_preferences", "count": 12}
    ],

    "deletion_confirmation": {
        "completed_at": "2025-12-19T16:00:00Z",
        "patterns_deleted": 57,
        "verification_hash": "SHA256:...",
        "recorded_on_chain": true,
        "block": 351
    }
}
```

## Implementation Tasks

### Learning Contracts Side
- [ ] Define Learning Contract schema
- [ ] Implement scope validation
- [ ] Build revocation system
- [ ] Create audit trail

### NatLangChain Side
- [ ] Add learning contract entry type
- [ ] Implement verification endpoint
- [ ] Add revocation recording
- [ ] Build audit API

### Agent OS Side
- [ ] Implement Learning Contract enforcer
- [ ] Add pattern deletion capability
- [ ] Create compliance reporter
- [ ] Integrate with Boundary Daemon

## Dependencies

- **Agent OS**: Enforcement layer
- **Boundary Daemon**: Hard enforcement
- **NatLangChain**: Immutable record

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
