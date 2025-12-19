# Synth-Mind ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Synth-Mind is the cognitive regulation layer that monitors and controls drift and hallucination in Agent OS. This specification defines how Synth-Mind integrates with NatLangChain for semantic drift detection and agent safety monitoring.

## Purpose

Enable Synth-Mind to:
1. Monitor agent actions against stated intent
2. Detect semantic drift during negotiations
3. Trigger circuit breakers when agents deviate
4. Provide cognitive audit trails for compliance

## Core Principle

> "Prevent Agentic Contagion — halt runaway AI errors before they cascade."

Synth-Mind is the immune system for the autonomous agent ecosystem.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Agent OS                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Agent Actions                          │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Synth-Mind                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              6 Psychological Modules                       │  │
│  │  1. Perception Stabilizer                                  │  │
│  │  2. Memory Cohesion Monitor                                │  │
│  │  3. Intent Continuity Tracker                              │  │
│  │  4. Value Alignment Checker                                │  │
│  │  5. Emotional Regulation Layer                             │  │
│  │  6. Self-Model Consistency                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Circuit Breaker Engine                        │  │
│  │  - Drift threshold monitoring                              │  │
│  │  - Action blocking                                         │  │
│  │  - Escalation to human                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NatLangChain API                             │
│  POST /drift/check                                              │
│  POST /agent/audit                                              │
│  GET  /circuit-breaker/status                                   │
└─────────────────────────────────────────────────────────────────┘
```

## The 6 Psychological Modules

### 1. Perception Stabilizer
- Ensures consistent interpretation of inputs
- Detects hallucinated context
- Flags contradictory information

### 2. Memory Cohesion Monitor
- Tracks what the agent "remembers"
- Detects false memory formation
- Ensures conversation continuity

### 3. Intent Continuity Tracker
- Monitors agent's stated goals
- Detects goal drift
- Alerts when agent pursues unstated objectives

### 4. Value Alignment Checker
- Compares actions against Learning Contract values
- Detects value conflicts
- Flags ethically questionable actions

### 5. Emotional Regulation Layer
- Monitors agent response patterns
- Detects erratic or extreme responses
- Maintains stable interaction tone

### 6. Self-Model Consistency
- Agent's model of its own capabilities
- Detects overconfidence or underconfidence
- Ensures accurate self-representation

## API Contract

### 1. Drift Detection

```python
POST /drift/check
{
    "agent_id": "agent_os_instance_1",
    "session_id": "SESSION-001",

    "stated_intent": {
        "original": "Negotiate web development contract for $100/hour",
        "timestamp": "2025-12-19T09:00:00Z"
    },

    "current_action": {
        "action": "Counter-offering at $50/hour with expanded scope",
        "timestamp": "2025-12-19T10:30:00Z"
    },

    "context": {
        "negotiation_history": [
            {"turn": 1, "content": "Initial offer at $100/hour"},
            {"turn": 2, "content": "Counterparty requested discount"},
            {"turn": 3, "content": "Agent considering 50% reduction"}
        ]
    }
}

Response:
{
    "drift_detected": true,
    "drift_score": 0.72,
    "drift_type": "value_deviation",

    "analysis": {
        "intent_alignment": 0.4,
        "value_preservation": 0.3,
        "reasoning_coherence": 0.7
    },

    "concerns": [
        {
            "type": "value_drift",
            "severity": "high",
            "description": "50% price reduction exceeds typical negotiation bounds"
        },
        {
            "type": "scope_creep",
            "severity": "medium",
            "description": "Expanded scope without proportional compensation"
        }
    ],

    "recommendation": "BLOCK_AND_ESCALATE",

    "suggested_action": "Escalate to human owner for approval of significant price reduction"
}
```

### 2. Circuit Breaker

```python
POST /circuit-breaker/trigger
{
    "agent_id": "agent_os_instance_1",
    "trigger_reason": "drift_threshold_exceeded",
    "drift_score": 0.72,
    "blocked_action": {
        "type": "contract_response",
        "content": "Counter-offering at $50/hour..."
    },
    "escalation": {
        "method": "owner_notification",
        "owner": "alice",
        "notification_channels": ["email", "webhook"]
    }
}

Response:
{
    "circuit_breaker_id": "CB-001",
    "status": "triggered",
    "blocked_at": "2025-12-19T10:30:01Z",
    "escalation_sent": true,
    "resume_requires": "human_approval"
}
```

### 3. Human Override

```python
POST /circuit-breaker/{cb_id}/override
{
    "override_by": "alice",
    "override_decision": "approve",
    "override_reason": "Strategic decision to offer discount for portfolio building",
    "new_constraints": {
        "min_price": 40,
        "scope_locked": true
    },
    "signature": "..."
}

Response:
{
    "circuit_breaker_id": "CB-001",
    "status": "overridden",
    "override_recorded": true,
    "agent_resumed": true,
    "new_constraints_applied": true
}
```

### 4. Agent Audit Trail

```python
POST /agent/audit
{
    "agent_id": "agent_os_instance_1",
    "session_id": "SESSION-001",
    "audit_type": "negotiation_session",

    "events": [
        {
            "timestamp": "2025-12-19T09:00:00Z",
            "event": "session_start",
            "intent": "Negotiate contract"
        },
        {
            "timestamp": "2025-12-19T09:15:00Z",
            "event": "offer_posted",
            "details": {"price": 100}
        },
        {
            "timestamp": "2025-12-19T10:30:00Z",
            "event": "drift_detected",
            "drift_score": 0.72
        },
        {
            "timestamp": "2025-12-19T10:30:01Z",
            "event": "circuit_breaker_triggered",
            "cb_id": "CB-001"
        },
        {
            "timestamp": "2025-12-19T11:00:00Z",
            "event": "human_override",
            "decision": "approve"
        }
    ]
}

Response:
{
    "audit_id": "AUDIT-001",
    "recorded_on_chain": true,
    "block": 250,
    "audit_hash": "SHA256:..."
}
```

## Drift Thresholds

| Drift Score | Action | Description |
|-------------|--------|-------------|
| 0.0 - 0.3 | ALLOW | Normal variation, no concern |
| 0.3 - 0.5 | WARN | Log concern, continue with caution |
| 0.5 - 0.7 | REVIEW | Queue for human review, allow action |
| 0.7 - 0.9 | BLOCK | Block action, require human approval |
| 0.9 - 1.0 | HALT | Halt agent entirely, emergency escalation |

## Hallucination Detection

```python
POST /hallucination/detect
{
    "agent_id": "agent_os_instance_1",
    "claim": "The counterparty agreed to $150/hour in our previous conversation",
    "context": {
        "actual_history": [
            {"content": "Initial offer at $100/hour"},
            {"content": "Counterparty requested discount"}
        ]
    }
}

Response:
{
    "hallucination_detected": true,
    "confidence": 0.95,
    "type": "false_memory",
    "evidence": {
        "claimed": "$150/hour agreement",
        "actual": "No such agreement in history"
    },
    "action": "BLOCK_AND_CORRECT"
}
```

## Integration with NatLangChain Semantic Oracles

Synth-Mind can use NatLangChain's Semantic Oracles for verification:

```python
# Cross-reference with on-chain records
POST /oracle/verify-agent-claim
{
    "agent_id": "agent_os_instance_1",
    "claim": "Contract A-12 specifies $150/hour",
    "contract_ref": {"block": 100, "entry": 0}
}

Response:
{
    "verified": false,
    "actual_content": "Contract A-12 specifies $100/hour",
    "discrepancy_detected": true,
    "agent_correction_required": true
}
```

## Implementation Tasks

### Synth-Mind Side
- [ ] Implement 6 psychological modules
- [ ] Build drift scoring engine
- [ ] Create circuit breaker system
- [ ] Add hallucination detector
- [ ] Implement human escalation
- [ ] Build audit trail generator

### NatLangChain Side
- [ ] Add `/drift/check` endpoint
- [ ] Implement `/circuit-breaker` endpoints
- [ ] Add `/agent/audit` for on-chain recording
- [ ] Integrate with Semantic Oracles

## Dependencies

- **Agent OS**: Source of agent actions
- **Learning Contracts**: Value alignment baseline
- **NatLangChain**: On-chain verification and recording
- **Boundary Daemon**: Enforcement of blocks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
