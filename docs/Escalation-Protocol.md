# Escalation Fork Protocol

## Overview

The Escalation Fork is an optional mechanism that activates when standard mediation fails to achieve resolution. Rather than simply pausing the process, it **forks the mediation fee pool** to incentivize alternative solvers while preserving the original mediator's stake.

> **Core Principle**: When negotiation hits a wall, the system doesn't stall—it opens the floor to anyone who can solve the deadlock.

## Trigger Conditions

The Escalation Fork can be triggered by either party under these conditions:

1. **Failed Ratification**: The mediation proposal was rejected by one or both parties
2. **Refusal to Mediate**: A party explicitly refuses to continue the mediation process
3. **Mediation Timeout**: The mediator fails to produce a proposal within the agreed timeframe
4. **Mutual Request**: Both parties agree to escalate to community solving

### Observance Burn Requirement

Before an Escalation Fork can be triggered, the requesting party must perform an **Observance Burn** of 5% of the original mediation stake. This ensures escalations are serious commitments, not tactical delays.

> "To escalate, you must perform an Observance Burn of 5% of the mediation stake. This amount is permanently removed from circulation and redistributed proportionally to all remaining holders. Do you wish to proceed with the burn?"

See [Observance-Burn.md](./Observance-Burn.md) for the full burn protocol specification.

### Trigger Syntax

```python
# Step 1: Perform Observance Burn (required)
POST /burn/observance
{
    "amount": "5000000000000000000",  # 5% of mediation stake
    "reason": "EscalationCommitment",
    "intentHash": "0x...",  # Hash of the mediation being escalated
    "epitaph": "Burned to fairly escalate and preserve ledger integrity"
}

# Step 2: Trigger the fork
POST /dispute/{dispute_id}/escalate-fork
{
    "trigger_reason": "failed_ratification",  # or "refusal_to_mediate", "timeout", "mutual_request"
    "triggering_party": "alice",
    "original_mediator": "mediator_node_1",
    "burn_tx_hash": "0x...",  # Proof of Observance Burn
    "evidence_of_failure": {
        "failed_proposals": ["PROP-001", "PROP-002"],
        "rejection_reasons": ["Terms unacceptable", "Missing key provisions"]
    }
}

Response:
{
    "fork_id": "FORK-001",
    "status": "active",
    "original_pool": 100.0,
    "mediator_retained": 50.0,
    "bounty_pool": 50.0,
    "observance_burn_verified": true,
    "solver_window_ends": "2025-12-26T00:00:00Z"
}
```

## Fork Mechanics

### Fee Pool Division

When an Escalation Fork is triggered:

| Allocation | Percentage | Purpose |
|------------|------------|---------|
| Original Mediator | 50% | Retained for initial effort |
| Resolution Bounty Pool | 50% | Distributed to successful solver(s) |

```
┌─────────────────────────────────────────────────────────────────┐
│                    Original Mediation Fee Pool                   │
│                           100 tokens                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                        ESCALATION FORK
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   Original Mediator     │       │   Resolution Bounty     │
│        50 tokens        │       │      Pool: 50 tokens    │
│                         │       │                         │
│  Retained for initial   │       │  Available to solvers   │
│  effort regardless of   │       │  who achieve ratified   │
│  final outcome          │       │  resolution             │
└─────────────────────────┘       └─────────────────────────┘
```

### Solver Participation

Any qualified participant can submit a resolution proposal during the solver window:

```python
POST /fork/{fork_id}/submit-proposal
{
    "solver": "community_solver_1",
    "proposal": {
        "content": "Proposed resolution: The contract shall be amended to reflect a $90/hour rate...",
        "word_count": 850,
        "addresses_concerns": ["rate_dispute", "timeline_concerns"],
        "supporting_evidence": ["EMAIL-001", "CONTRACT-DRAFT-002"]
    },
    "iteration": 1  # Proposal version number
}
```

## Solver Incentives

### Effort-Based Allocation Formula

Solver rewards are distributed based on measurable contribution to resolution:

```
Solver's Share = (Solver Effort / Total Resolution Effort) × Bounty Pool
```

### Effort Metrics

| Metric | Weight | Description |
|--------|--------|-------------|
| Word Count | 30% | Total words in accepted proposal |
| Proposal Iterations | 40% | Number of refinement cycles |
| Alignment Score | 30% | Party satisfaction rating (0-100) |

### Effort Calculation

```python
def calculate_solver_effort(solver_data):
    """Calculate a solver's effort score."""
    word_score = normalize(solver_data["word_count"], min=500, max=5000) * 0.30
    iteration_score = normalize(solver_data["iterations"], min=1, max=10) * 0.40
    alignment_score = (solver_data["party_a_rating"] + solver_data["party_b_rating"]) / 200 * 0.30

    return word_score + iteration_score + alignment_score

def distribute_bounty(solvers, bounty_pool):
    """Distribute bounty proportionally to effort."""
    total_effort = sum(calculate_solver_effort(s) for s in solvers)

    distribution = {}
    for solver in solvers:
        effort = calculate_solver_effort(solver)
        distribution[solver["id"]] = (effort / total_effort) * bounty_pool

    return distribution
```

### Example Distribution

Given a bounty pool of 50 tokens and three contributing solvers:

| Solver | Word Count | Iterations | Alignment | Effort Score | Share |
|--------|------------|------------|-----------|--------------|-------|
| Solver A | 1200 | 3 | 85 | 0.42 | 21 tokens |
| Solver B | 800 | 2 | 70 | 0.31 | 15.5 tokens |
| Solver C | 600 | 2 | 60 | 0.27 | 13.5 tokens |

## Resolution Criteria

For a solver's proposal to be accepted:

1. **Dual Ratification**: Both parties must explicitly ratify the proposal
2. **Minimum Completeness**: Proposal must address all contested points
3. **Implementation Path**: Must include clear execution steps

```python
POST /fork/{fork_id}/ratify
{
    "proposal_id": "PROP-SOLVER-001",
    "ratifying_party": "alice",
    "ratification": {
        "accepted": true,
        "satisfaction_rating": 85,
        "comments": "This proposal adequately addresses my concerns."
    }
}

# Both parties must ratify for resolution
Response (after both ratify):
{
    "fork_id": "FORK-001",
    "status": "resolved",
    "winning_proposal": "PROP-SOLVER-001",
    "solver": "community_solver_1",
    "bounty_distributed": true,
    "distribution": {
        "community_solver_1": 50.0
    }
}
```

## Timeout and Refund

### 7-Day Solver Window

If no ratified resolution is achieved within the solver window:

```
┌─────────────────────────────────────────────────────────────────┐
│                         TIMEOUT (7 Days)                         │
│                                                                  │
│  Bounty Pool: 50 tokens                                          │
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │   Refund to Parties │    │   Observance Burn   │             │
│  │      90% (45)       │    │     10% (5)         │             │
│  │                     │    │                     │             │
│  │  Split equally:     │    │  Burned via the     │             │
│  │  - Party A: 22.5    │    │  Observance Burn    │             │
│  │  - Party B: 22.5    │    │  protocol           │             │
│  └─────────────────────┘    └─────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Timeout Handling

```python
# Automatic execution after 7 days without resolution
{
    "fork_id": "FORK-001",
    "status": "timeout",
    "bounty_pool": 50.0,
    "distribution": {
        "party_a_refund": 22.5,
        "party_b_refund": 22.5,
        "burn_fee": 5.0
    },
    "timeout_reason": "No ratified proposal within solver window"
}
```

## Anti-Abuse Guards

### 1. Minimum Proposal Requirements

- **500 word minimum**: Proposals must demonstrate substantive effort
- **Address all contested points**: Incomplete proposals are rejected
- **Evidence-backed**: Claims must reference on-chain evidence

```python
def validate_proposal(proposal):
    """Validate proposal meets minimum requirements."""
    if proposal["word_count"] < 500:
        return False, "Proposal must be at least 500 words"

    if not all(point in proposal["addressed_points"] for point in dispute["contested_points"]):
        return False, "Proposal must address all contested points"

    return True, "Valid"
```

### 2. Veto Rights

Either party can veto a proposal with documented reasoning:

```python
POST /fork/{fork_id}/veto
{
    "proposal_id": "PROP-SOLVER-001",
    "vetoing_party": "bob",
    "veto_reason": "Proposal ignores key evidence from email chain",
    "evidence_refs": ["EVIDENCE-003", "EVIDENCE-007"]
}
```

Veto abuse prevention:
- Maximum 3 vetoes per party per fork
- Vetoes must include substantive reasoning (100+ words)
- Pattern of bad-faith vetoes can result in party losing veto rights

### 3. On-Chain Auditability

All fork actions are recorded immutably:

```python
# Fork audit trail entry
{
    "audit_type": "fork_action",
    "fork_id": "FORK-001",
    "action": "proposal_submitted",
    "actor": "community_solver_1",
    "timestamp": "2025-12-20T14:30:00Z",
    "action_hash": "SHA256:...",
    "previous_action_hash": "SHA256:..."
}
```

### 4. Solver Reputation

Solvers build reputation over time:

| Metric | Impact |
|--------|--------|
| Successful resolutions | +10 reputation |
| High satisfaction ratings | +1-5 reputation |
| Timeout/failed proposals | -2 reputation |
| Vetoed proposals | -1 reputation |

Minimum reputation threshold may be required for high-value disputes.

## Integration with MP-01 Alignment Cycle

The Escalation Fork extends the standard Mediator Protocol (MP-01) with an optional branch:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MP-01 Alignment Cycle                         │
│                                                                  │
│  1. Intent Submission ──► 2. Mediator Assignment                │
│                                    │                             │
│                                    ▼                             │
│                          3. Proposal Generation                  │
│                                    │                             │
│                                    ▼                             │
│                          4. Party Review                         │
│                                    │                             │
│                    ┌───────────────┴───────────────┐            │
│                    │                               │            │
│                    ▼                               ▼            │
│            [RATIFIED]                      [NOT RATIFIED]       │
│                    │                               │            │
│                    ▼                               ▼            │
│            5. Execute                    ┌─────────────────┐    │
│               Agreement                  │ ESCALATION FORK │    │
│                                          │   (Optional)    │    │
│                                          └────────┬────────┘    │
│                                                   │             │
│                                                   ▼             │
│                                          6. Solver Window       │
│                                                   │             │
│                                    ┌──────────────┴──────────┐  │
│                                    │                         │  │
│                                    ▼                         ▼  │
│                            [RESOLVED]               [TIMEOUT]   │
│                                    │                         │  │
│                                    ▼                         ▼  │
│                            Execute                    Refund    │
│                            Agreement                  Parties   │
└─────────────────────────────────────────────────────────────────┘
```

## API Reference

### Fork Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dispute/{id}/escalate-fork` | POST | Trigger escalation fork |
| `/fork/{id}` | GET | Get fork status |
| `/fork/{id}/submit-proposal` | POST | Submit solver proposal |
| `/fork/{id}/proposals` | GET | List all proposals |
| `/fork/{id}/ratify` | POST | Ratify a proposal |
| `/fork/{id}/veto` | POST | Veto a proposal |
| `/fork/{id}/distribution` | GET | Get bounty distribution |
| `/fork/{id}/audit` | GET | Get fork audit trail |

## Configuration

```python
ESCALATION_FORK_CONFIG = {
    "fee_split": {
        "mediator_retained": 0.50,
        "bounty_pool": 0.50
    },
    "solver_window_days": 7,
    "timeout_distribution": {
        "party_refund": 0.90,
        "burn_fee": 0.10
    },
    "effort_weights": {
        "word_count": 0.30,
        "iterations": 0.40,
        "alignment": 0.30
    },
    "minimum_requirements": {
        "proposal_word_count": 500,
        "veto_reason_word_count": 100,
        "max_vetoes_per_party": 3
    }
}
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Related Documents:**
- [SPEC.md](../SPEC.md) - MP-01 Alignment Cycle
- [Observance-Burn.md](./Observance-Burn.md) - Observance Burn protocol
- [MEDIATOR-NODE-INTEGRATION.md](../specs/MEDIATOR-NODE-INTEGRATION.md) - Mediator Node integration
- [Dispute Protocol](./dispute-protocol.md) - MP-03 Dispute Protocol

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
