# Boundary Daemon ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: January 1, 2026
## Status: Draft

---

## Overview

Boundary Daemon is the hard enforcement layer that prevents unauthorized data flow and ensures trust boundaries are maintained across the ecosystem. This specification defines how Boundary Daemon integrates with NatLangChain for policy enforcement.

## Purpose

Enable Boundary Daemon to:
1. Enforce Learning Contract boundaries
2. Block unauthorized data exfiltration
3. Audit all cross-system communications
4. Provide cryptographic proof of enforcement

## Core Principle

> "What cannot be leaked cannot be exploited."

Boundary Daemon is the last line of defense for data sovereignty.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trust Boundary                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Agent OS                                │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Protected Data                          │  │  │
│  │  │  - Private communications                            │  │  │
│  │  │  - Financial data                                    │  │  │
│  │  │  - Proprietary code                                  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ All outbound requests            │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Boundary Daemon                           │  │
│  │  ┌─────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │ Policy      │  │ Data Flow  │  │ Audit              │  │  │
│  │  │ Engine      │  │ Inspector  │  │ Logger             │  │  │
│  │  └─────────────┘  └────────────┘  └────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Approved requests only
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      External World                              │
│  NatLangChain  │  Mediator Node  │  Value Ledger  │  Internet   │
└─────────────────────────────────────────────────────────────────┘
```

## Policy Schema

```python
{
    "policy_id": "POLICY-001",
    "owner": "alice",
    "agent_id": "agent_os_instance_1",
    "created_at": "2025-12-19T09:00:00Z",
    "status": "active",

    # Data classification
    "data_classifications": [
        {
            "class": "public",
            "allowed_destinations": ["*"],
            "examples": ["Public code repositories", "Published articles"]
        },
        {
            "class": "internal",
            "allowed_destinations": ["natlangchain", "value_ledger"],
            "examples": ["Contract details", "Pricing information"]
        },
        {
            "class": "confidential",
            "allowed_destinations": ["memory_vault"],
            "examples": ["Trade secrets", "Unpublished code"]
        },
        {
            "class": "restricted",
            "allowed_destinations": [],
            "examples": ["Private keys", "Credentials", "Medical records"]
        }
    ],

    # Outbound rules
    "outbound_rules": [
        {
            "rule_id": "OUT-001",
            "source": "agent_os",
            "destination": "natlangchain",
            "allowed_data_classes": ["public", "internal"],
            "blocked_patterns": [
                "password", "api_key", "secret", "private_key"
            ],
            "max_payload_size": "1MB"
        },
        {
            "rule_id": "OUT-002",
            "source": "agent_os",
            "destination": "external_api",
            "allowed_data_classes": ["public"],
            "requires_approval": true
        }
    ],

    # Inbound rules
    "inbound_rules": [
        {
            "rule_id": "IN-001",
            "source": "natlangchain",
            "destination": "agent_os",
            "allowed": true,
            "sanitization": ["strip_external_links"]
        }
    ],

    # Enforcement settings
    "enforcement": {
        "mode": "strict",  # strict | permissive | audit_only
        "on_violation": "block_and_alert",
        "escalation": "owner"
    }
}
```

## API Contract

### 1. Request Authorization

```python
# Agent OS → Boundary Daemon → External
POST /boundary/authorize
{
    "request_id": "REQ-001",
    "source": "agent_os_instance_1",
    "destination": "natlangchain",
    "endpoint": "/entry",
    "method": "POST",

    "payload": {
        "content": "I offer web development services...",
        "author": "agent_os_instance_1",
        "metadata": {...}
    },

    "data_classification": "internal",
    "learning_contract_ref": "LC-001"
}

Response (Allowed):
{
    "authorized": true,
    "request_id": "REQ-001",
    "authorization_id": "AUTH-001",
    "rules_applied": ["OUT-001"],
    "modifications": [],
    "proceed": true
}

Response (Blocked):
{
    "authorized": false,
    "request_id": "REQ-001",
    "violation": {
        "type": "blocked_pattern_detected",
        "pattern": "api_key",
        "location": "payload.content",
        "rule": "OUT-001"
    },
    "action_taken": "blocked",
    "owner_notified": true
}
```

### 2. Data Flow Inspection

```python
POST /boundary/inspect
{
    "flow_id": "FLOW-001",
    "data": "Base64EncodedPayload...",
    "context": {
        "source": "agent_os",
        "destination": "natlangchain",
        "operation": "post_entry"
    }
}

Response:
{
    "inspection_id": "INSP-001",
    "risk_score": 0.15,

    "detected_patterns": [
        {
            "type": "email_address",
            "count": 1,
            "risk": "low",
            "recommendation": "redact_optional"
        }
    ],

    "classification_suggested": "internal",
    "policy_compliance": true
}
```

### 3. Audit Logging

```python
POST /boundary/audit
{
    "event_type": "data_flow",
    "timestamp": "2025-12-19T10:00:00Z",

    "source": "agent_os_instance_1",
    "destination": "natlangchain",

    "request": {
        "endpoint": "/entry",
        "method": "POST",
        "payload_hash": "SHA256:...",
        "payload_size": 1024
    },

    "authorization": {
        "authorized": true,
        "authorization_id": "AUTH-001",
        "rules_applied": ["OUT-001"]
    },

    "result": {
        "status": "success",
        "response_code": 200
    }
}

Response:
{
    "audit_id": "AUDIT-001",
    "recorded": true,
    "chain_block": 400,
    "audit_hash": "SHA256:..."
}
```

### 4. Policy Violation Alert

```python
POST /boundary/violation
{
    "violation_id": "VIOL-001",
    "timestamp": "2025-12-19T10:30:00Z",
    "severity": "high",

    "violation_type": "data_exfiltration_attempt",

    "details": {
        "source": "agent_os_instance_1",
        "destination": "external_api",
        "blocked_data_class": "confidential",
        "payload_sample": "REDACTED",
        "rule_violated": "OUT-002"
    },

    "action_taken": "blocked",
    "owner_notification": {
        "sent": true,
        "channels": ["email", "webhook"]
    }
}

Response:
{
    "violation_recorded": true,
    "incident_id": "INC-001",
    "investigation_required": true,
    "agent_suspended": true
}
```

### 5. Recording on NatLangChain

Critical boundary events are recorded on-chain:

```python
POST /entry
{
    "content": "Boundary Daemon Audit: Policy violation detected and blocked. Agent agent_os_instance_1 attempted to send confidential data to external_api. Action: Blocked. Owner notified.",

    "author": "boundary_daemon",
    "intent": "Record security event",

    "metadata": {
        "is_boundary_event": true,
        "event_type": "policy_violation",
        "violation_id": "VIOL-001",
        "incident_id": "INC-001",
        "agent_id": "agent_os_instance_1",
        "owner": "alice",
        "severity": "high",
        "action_taken": "blocked"
    }
}
```

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **strict** | Block all violations, no exceptions | Production |
| **permissive** | Block critical, warn on minor | Development |
| **audit_only** | Log only, no blocking | Testing/analysis |

## Pattern Detection

Built-in blocked patterns:
- `api_key`, `api-key`, `apikey`
- `password`, `passwd`, `pwd`
- `secret`, `token`
- `private_key`, `privatekey`
- `ssh_key`, `ssh-key`
- Credit card patterns
- Social security patterns

Custom patterns can be added:
```python
POST /boundary/patterns/add
{
    "pattern_id": "CUSTOM-001",
    "regex": "internal-project-\\d+",
    "description": "Internal project identifiers",
    "action": "block",
    "data_class": "confidential"
}
```

## Implementation Tasks

### Boundary Daemon Side
- [ ] Implement policy engine
- [ ] Build data flow inspector
- [ ] Create pattern detection
- [ ] Add audit logging
- [ ] Implement violation alerting
- [ ] Build owner notification system

### NatLangChain Side
- [ ] Add boundary event entry type
- [ ] Support audit record ingestion
- [ ] Implement violation queries
- [ ] Add policy reference fields

### Agent OS Side
- [ ] Route all outbound through Boundary Daemon
- [ ] Implement classification tagging
- [ ] Add policy compliance checker

## Dependencies

- **Agent OS**: Source of requests
- **Learning Contracts**: Policy source
- **NatLangChain**: Audit record storage
- **Memory Vault**: Confidential data source

## External System Integration

NatLangChain implements full integration with external Boundary Daemon and Boundary SIEM systems.

### Configuration

Set environment variables to enable external integration:

```bash
# External Boundary Daemon
export BOUNDARY_ENABLE_EXTERNAL_DAEMON=true
export BOUNDARY_DAEMON_SOCKET=/var/run/boundary-daemon/boundary.sock
export BOUNDARY_DAEMON_URL=http://localhost:8080/api/v1
export BOUNDARY_DAEMON_API_KEY=your-api-key
export BOUNDARY_DAEMON_TIMEOUT=5.0
export BOUNDARY_DAEMON_FAIL_OPEN=false  # Fail-closed by default
export BOUNDARY_SYNC_MODE_WITH_DAEMON=true

# External Boundary SIEM
export BOUNDARY_USE_ENHANCED_SIEM=true
export BOUNDARY_SIEM_URL=https://siem.example.com/api/v1
export BOUNDARY_SIEM_API_KEY=your-siem-key
export BOUNDARY_SIEM_AUTH_METHOD=oauth2  # bearer_token, oauth2, mtls
export BOUNDARY_SIEM_KAFKA_BROKERS=kafka1:9092,kafka2:9092
export BOUNDARY_SIEM_KAFKA_TOPIC=boundary-siem-events
```

### Python Usage

```python
from boundary_protection import BoundaryProtection, ProtectionConfig

# Create config with external integration
config = ProtectionConfig.from_env()

# Or manually configure
config = ProtectionConfig(
    enable_external_daemon=True,
    external_daemon_socket="/var/run/boundary-daemon/boundary.sock",
    sync_mode_with_daemon=True,
    use_enhanced_siem=True,
    siem_url="https://siem.example.com/api/v1"
)

# Initialize protection
protection = BoundaryProtection(config)
protection.start()

# Check ToolGate with external daemon
result = protection.check_external_tool_gate(
    tool_name="file_read",
    parameters={"path": "/etc/passwd"},
    requester="my_agent"
)

if not result.allowed:
    print(f"Blocked: {result.details['reasoning']}")

# Forward events to external daemon
protection.forward_event_to_daemon(
    event_type="policy_decision",
    event_data={"action": "block", "tool": "shell_execute"},
    severity=7
)

# Query SIEM via GraphQL (requires enhanced SIEM)
events = protection.graphql_query('''
    query {
        events(limit: 100) {
            id
            timestamp
            action
            severity
        }
    }
''')

# Cleanup
protection.stop()
```

### RecallGate Integration

Query the external daemon for memory access decisions:

```python
# Check memory access
result = protection.check_external_recall_gate(
    memory_class=3,  # CONFIDENTIAL
    purpose="Research project analysis",
    requester="researcher_agent"
)

if result.allowed:
    # Proceed with memory access
    pass
else:
    # Access denied by daemon
    print(f"Memory access denied: {result.details['reasoning']}")
```

### Human Override Ceremony

Coordinate ceremonies with external daemon:

```python
# Request ceremony
ceremony = protection.request_external_ceremony(
    ceremony_type="mode_change",
    reason="Maintenance window required",
    target="open",
    requester="admin"
)

if ceremony["success"]:
    print(f"Ceremony ID: {ceremony['ceremony_id']}")
    print(f"Steps required: {ceremony['steps']}")

    # Complete ceremony with confirmation code
    result = protection.confirm_external_ceremony(
        ceremony_id=ceremony["ceremony_id"],
        confirmation_code="ABC123",
        confirmed_by="security_admin"
    )
```

### SIEM Detection Rules

Create custom detection rules in Boundary SIEM:

```python
# Get existing rules
rules = protection.get_siem_detection_rules()

# Create custom rule
protection.create_custom_detection_rule(
    name="NatLangChain Prompt Injection",
    query="event.category:ai_agent AND event.action:prompt_injection",
    severity=8,
    description="Detects prompt injection attempts in NatLangChain",
    tags=["ai-security", "injection"]
)
```

### Bulk Event Ingestion

Efficiently send multiple events:

```python
from boundary_siem import SIEMEvent, SIEMEventCategory, SIEMSeverity

events = [
    SIEMEvent(
        category=SIEMEventCategory.CHAIN_ENTRY_CREATED,
        action="create",
        outcome="success",
        severity=SIEMSeverity.INFORMATIONAL,
        message=f"Entry created: {entry_id}"
    )
    for entry_id in recent_entries
]

result = protection.send_events_bulk(events, sync=True)
print(f"Sent {result['success']} events")
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |
| 1.1 | 2026-01-02 | Added external system integration (Boundary-SIEM, Boundary-Daemon) |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
