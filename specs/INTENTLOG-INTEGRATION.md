# IntentLog ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

IntentLog is version control for human reasoning—tracking "why" not just "what." This specification defines how IntentLog integrates with NatLangChain to provide reasoning context for intents.

## Purpose

Enable IntentLog to:
1. Capture reasoning ("why") before intents are posted
2. Track decision paths and rejected alternatives
3. Provide context for dispute resolution
4. Support post-hoc analysis of decision quality

## Core Principle

> "What if Git tracked why, not just what?"

IntentLog preserves the reasoning process; NatLangChain records the outcome.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       IntentLog                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Reasoning Capture                             │  │
│  │  - Why am I doing this?                                    │  │
│  │  - What alternatives did I consider?                       │  │
│  │  - What factors influenced my decision?                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Decision Tree                                 │  │
│  │  - Branch points                                           │  │
│  │  - Rejected paths                                          │  │
│  │  - Chosen path                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Intent Summarizer                             │  │
│  │  - Condense reasoning for NatLangChain                     │  │
│  │  - Preserve key decision factors                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NatLangChain API                             │
│  POST /entry (with intentlog_ref)                               │
└─────────────────────────────────────────────────────────────────┘
```

## API Contract

### 1. Logging Reasoning

```python
# IntentLog internal API
POST /reasoning/log
{
    "session_id": "SESSION-001",
    "author": "alice",

    "context": "Deciding on pricing strategy for web development services",

    "considerations": [
        {
            "factor": "Market rates",
            "weight": 0.3,
            "notes": "Competitors charge $80-150/hour"
        },
        {
            "factor": "Experience level",
            "weight": 0.25,
            "notes": "5 years React, 3 years Node"
        },
        {
            "factor": "Target clients",
            "weight": 0.25,
            "notes": "Startups and small businesses"
        },
        {
            "factor": "Work-life balance",
            "weight": 0.2,
            "notes": "Prefer fewer, higher-paying clients"
        }
    ],

    "alternatives_considered": [
        {
            "option": "$80/hour - Volume strategy",
            "pros": ["More clients", "Faster portfolio growth"],
            "cons": ["Burnout risk", "Lower quality work"],
            "rejected_because": "Conflicts with work-life balance priority"
        },
        {
            "option": "$150/hour - Premium positioning",
            "pros": ["Higher income", "Better clients"],
            "cons": ["Fewer opportunities", "May price out startups"],
            "rejected_because": "May exclude target client segment"
        },
        {
            "option": "$100/hour - Balanced approach",
            "pros": ["Competitive yet premium", "Sustainable workload"],
            "cons": ["Middle of market"],
            "chosen_because": "Best balance of all factors"
        }
    ],

    "final_decision": "$100/hour for web development services",

    "confidence_level": 0.85,

    "revisit_triggers": [
        "If demand exceeds capacity for 2+ months",
        "If market rates shift significantly",
        "Annual review"
    ]
}

Response:
{
    "intent_id": "INTENT-456",
    "reasoning_hash": "SHA256:reasoning...",
    "ready_for_natlangchain": true
}
```

### 2. Posting to NatLangChain with Context

```python
# IntentLog → NatLangChain
POST /entry
{
    "content": "I offer web development services at $100/hour. Specializing in React and Node.js for startups and small businesses.",
    "author": "alice",
    "intent": "Offer web development services",

    "metadata": {
        "intentlog_ref": "INTENT-456",
        "intentlog_instance": "intentlog.alice.local",

        "reasoning_summary": "Balanced rate considering market ($80-150), 5 years experience, and work-life priorities. Chose middle ground to serve target market (startups) while maintaining sustainable workload.",

        "decision_factors": [
            {"factor": "Market rates", "influence": "high"},
            {"factor": "Experience level", "influence": "medium"},
            {"factor": "Target clients", "influence": "high"},
            {"factor": "Work-life balance", "influence": "medium"}
        ],

        "alternatives_rejected": 2,

        "confidence_level": 0.85,

        "reasoning_hash": "SHA256:reasoning...",

        "full_reasoning_available": true,
        "reasoning_access": "on_request"
    }
}
```

### 3. Retrieving Reasoning for Disputes

When a dispute arises (MP-03), IntentLog can provide context:

```python
# Request reasoning context
GET /reasoning/{intent_id}?requester=arbitrator&purpose=dispute_resolution

Response (if access granted):
{
    "intent_id": "INTENT-456",
    "author": "alice",

    "reasoning_context": {
        "original_considerations": [...],
        "alternatives_considered": [...],
        "decision_rationale": "..."
    },

    "state_at_decision": {
        "timestamp": "2025-12-19T09:00:00Z",
        "information_available": ["Market research report", "Client feedback"],
        "constraints": ["Budget limitations", "Time availability"]
    },

    "access_granted_for": "dispute_resolution",
    "access_expires": "2025-12-26T00:00:00Z"
}
```

## Decision Tree Format

```python
{
    "tree_id": "TREE-001",
    "root": {
        "question": "What pricing strategy?",
        "branches": [
            {
                "option": "Volume ($80/hr)",
                "evaluation": 0.6,
                "terminal": true,
                "outcome": "rejected"
            },
            {
                "option": "Premium ($150/hr)",
                "evaluation": 0.7,
                "terminal": true,
                "outcome": "rejected"
            },
            {
                "option": "Balanced ($100/hr)",
                "evaluation": 0.85,
                "terminal": true,
                "outcome": "chosen"
            }
        ]
    },
    "chosen_path": ["root", "Balanced ($100/hr)"],
    "path_confidence": 0.85
}
```

## Use Cases

### 1. Intent Posting with Context
- Alice logs reasoning about pricing
- Posts offer to NatLangChain with reasoning summary
- Counterparties can request reasoning context

### 2. Dispute Resolution
- Bob claims Alice misrepresented experience
- Arbitrator requests IntentLog reasoning
- Alice's original considerations show honest self-assessment

### 3. Decision Quality Review
- Periodically review past decisions
- Compare outcomes to predictions
- Improve future reasoning

### 4. Learning from Rejected Paths
- Track alternatives not chosen
- If market changes, revisit rejected options
- Preserve institutional memory

## Privacy Controls

### Access Levels
- **Private**: Only author can access
- **On Request**: Available with author approval
- **Summary Only**: Only summary shared, not full reasoning
- **Public**: Full reasoning visible

### Time-Limited Access
- Dispute access can be time-bounded
- Historical reasoning may be sealed after period
- Right to revoke future access (not past disclosures)

## Implementation Tasks

### IntentLog Side
- [ ] Implement reasoning capture UI/API
- [ ] Build decision tree data structure
- [ ] Create intent summarizer
- [ ] Add NatLangChain submission client
- [ ] Implement access control system
- [ ] Build reasoning retrieval API

### NatLangChain Side
- [ ] Add `intentlog_ref` field to entries
- [ ] Support reasoning summary in metadata
- [ ] Implement reasoning retrieval for disputes
- [ ] Add access verification

## Dependencies

- **Agent OS**: For local reasoning capture
- **NatLangChain**: For intent recording
- **Common**: For schema definitions
- **Boundary Daemon**: For access control

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
