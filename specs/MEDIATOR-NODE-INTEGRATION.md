# Mediator Node ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

> **Currency-Agnostic Design:** NatLangChain does not have its own native cryptocurrency. All stake amounts and fees are denominated in the configured staking currency (e.g., ETH, USDC, DAI) for each deployment.

---

## Overview

Mediator Node is a lightweight, dedicated node that discovers, negotiates, and proposes alignments between explicit intents on the NatLangChain protocol. This specification defines the "mediation mining" process where Mediator Nodes compete to create successful alignments and earn facilitation fees.

## Purpose

Enable Mediator Nodes to:
1. Subscribe to open contracts on NatLangChain
2. Propose alignments between compatible intents
3. Compete with other Mediator Nodes for best proposals
4. Earn facilitation fees for successful matches
5. Build reputation through successful mediations

## Core Principle

> "LLMs may propose; humans must decide."

Mediator Nodes generate proposals but never finalize agreements. All settlements require explicit human ratification.

## LLM Model Selection

**Important:** The Mediator Node only uses LLM models that are loaded or selected by the user. This ensures:
1. **User control** - Operators choose which models to use
2. **Transparency** - No hidden or external model dependencies
3. **Sovereignty** - Users maintain control over AI components

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Mediator Node                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  LLM Alignment Engine                      │  │
│  │  - Semantic matching                                       │  │
│  │  - Term negotiation                                        │  │
│  │  - Proposal generation                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              NatLangChain Subscriber                       │  │
│  │  - WebSocket connection to /contracts/stream               │  │
│  │  - Polls /contract/list for open contracts                 │  │
│  └──────────────────────────┬────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NatLangChain API                             │
│  GET  /contract/list?status=open                                │
│  POST /contract/propose                                         │
│  POST /mediator/register                                        │
│  GET  /mediator/<id>/stats                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Mediator Protocol (MP-01)

### The Alignment Cycle

1. **Ingestion**: Monitor the Pending Intent Pool
2. **Mapping**: Generate semantic vectors to identify high-dimensional overlaps
3. **Negotiation**: Simulate internal dialogues to find "Middle Ground"
4. **Submission**: Publish Proposed Settlement (PS) to the ledger

### Proof-of-Alignment (Consensus)

- **Mutual Acceptance**: Finality when both parties sign the PS
- **Challenge Window**: Other nodes may audit a PS
- **Procedural Integrity**: EXIT and mark as "Opaque" if clarity requirements fail

## API Contract

### 1. Mediator Registration

```python
POST /mediator/register
{
    "mediator_id": "mediator_node_alpha",
    "operator": "charlie",
    "llm_models": ["claude-3-sonnet", "gpt-4"],
    "stake_amount": 1000,
    "stake_currency": "USDC",  // Configurable: ETH, USDC, DAI, etc.
    "specializations": ["tech", "finance", "legal"],
    "max_concurrent_mediations": 50,
    "webhook_url": "https://mediator.charlie.com/updates"
}

Response:
{
    "status": "registered",
    "mediator_id": "mediator_node_alpha",
    "registration_block": 100,
    "stake_locked": true,
    "reputation_score": 0.0,
    "active_until": "2026-12-19T00:00:00Z"
}
```

### 2. Subscribing to Open Contracts

```python
# WebSocket subscription (preferred)
ws://natlangchain.api/contracts/stream

# Message format
{
    "type": "new_contract",
    "contract": {
        "block_index": 105,
        "entry_index": 2,
        "content": "[CONTRACT: SEEK] Need web developer...",
        "author": "bob",
        "contract_type": "seek",
        "terms": {...},
        "posted_at": "2025-12-19T10:00:00Z"
    }
}

# Polling fallback
GET /contract/list?status=open&since_block=100

Response:
{
    "count": 15,
    "contracts": [
        {
            "block_index": 105,
            "entry": {...}
        }
    ]
}
```

### 3. Proposing Alignments

```python
POST /contract/propose
{
    "offer_ref": {
        "block": 100,
        "entry": 0,
        "hash": "000abc..."
    },
    "seek_ref": {
        "block": 105,
        "entry": 2,
        "hash": "000def..."
    },
    "proposal_content": "[PROPOSAL: Match 87%] Contract proposal between alice and bob.\n\nAlice's web development expertise aligns with Bob's e-commerce project needs...",
    "match_score": 87,
    "match_reasoning": "Skills match (React, Node.js), budget within range, timeline compatible",
    "proposed_terms": {
        "scope": "E-commerce site development with payment integration",
        "value": 5000,
        "currency": "USD",
        "timeline": "3 weeks",
        "milestones": [
            {"name": "Design approval", "value": 1000},
            {"name": "Frontend complete", "value": 2000},
            {"name": "Full delivery", "value": 2000}
        ],
        "facilitation_fee": "2%"
    },
    "mediator_id": "mediator_node_alpha",
    "llm_model_used": "claude-3-sonnet",
    "signature": "..."
}

Response:
{
    "status": "proposal_accepted",
    "proposal_id": "PROP-789",
    "proposal_block": 110,
    "competing_proposals": 3,
    "response_deadline": "2025-12-21T10:00:00Z"
}
```

### 4. Fee Collection

When a proposal leads to successful closure:

```python
POST /mediator/claim-fee
{
    "mediator_id": "mediator_node_alpha",
    "closure_ref": {
        "block": 150,
        "entry": 0
    },
    "proposal_ref": "PROP-789",
    "fee_amount": 100,
    "fee_currency": "USD",
    "wallet_address": "0xABC..."
}

Response:
{
    "status": "fee_recorded",
    "payout_entry_block": 151,
    "payout_status": "pending_external_settlement"
}
```

## Alignment Algorithm

### Semantic Matching

```python
class AlignmentEngine:
    def find_matches(self, contracts: List[Contract]) -> List[Match]:
        """
        Find compatible OFFER/SEEK pairs
        """
        offers = [c for c in contracts if c.type == "offer"]
        seeks = [c for c in contracts if c.type == "seek"]

        matches = []
        for offer in offers:
            for seek in seeks:
                score = self.compute_match_score(offer, seek)
                if score >= self.threshold:
                    matches.append(Match(offer, seek, score))

        return sorted(matches, key=lambda m: m.score, reverse=True)

    def compute_match_score(self, offer: Contract, seek: Contract) -> float:
        """
        Multi-factor scoring:
        - Semantic similarity (embeddings)
        - Term compatibility (price, timeline, scope)
        - Historical success patterns
        """
        semantic_score = self.llm.evaluate_compatibility(offer, seek)
        term_score = self.evaluate_terms(offer.terms, seek.terms)

        return 0.7 * semantic_score + 0.3 * term_score
```

### Proposal Generation

```python
def generate_proposal(self, offer: Contract, seek: Contract, score: float) -> str:
    """
    Use LLM to generate natural language proposal
    """
    prompt = f"""
    Generate a contract proposal between:

    OFFER: {offer.content}
    Terms: {offer.terms}

    SEEK: {seek.content}
    Terms: {seek.terms}

    Match Score: {score}%

    Create a balanced proposal that:
    1. Identifies points of alignment
    2. Proposes fair middle ground on terms
    3. Specifies clear deliverables and timeline
    4. Includes facilitation fee
    """

    return self.llm.generate(prompt)
```

## Escalation Fork (Optional)

When standard mediation fails to achieve resolution, either party can trigger an **Escalation Fork**. This mechanism forks the mediation fee pool to incentivize alternative solvers while preserving the original mediator's stake.

### Trigger Conditions
- Failed ratification of mediation proposal
- Refusal to mediate by either party
- Mediation timeout

### Fork Mechanics
- **50% retained** by original mediator (for initial effort)
- **50% becomes Resolution Bounty Pool** (available to solvers)

### Resolution
- Any qualified participant can submit a proposal during the 7-day solver window
- Both parties must ratify for resolution
- Bounty distributed based on effort metrics (word count, iterations, alignment score)
- On timeout: 90% refunded to parties, 10% burned

**Full specification:** See [Escalation-Protocol.md](../docs/Escalation-Protocol.md)

---

## Competitive Mediation

When multiple Mediator Nodes propose for the same pair:

1. All proposals recorded on-chain
2. Multi-model consensus evaluates proposals
3. Highest-scoring proposal becomes canonical
4. Winning mediator earns facilitation fee
5. Losing mediators receive no fee but build experience

### Proposal Scoring Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Match accuracy | 30% | How well proposal reflects both intents |
| Term fairness | 25% | Balance of proposed terms |
| Clarity | 20% | Unambiguous language |
| Completeness | 15% | All necessary terms specified |
| Speed | 10% | Time to proposal submission |

## Reputation System

```python
# Reputation calculation
reputation_score = (
    0.4 * successful_closures / total_proposals +
    0.3 * average_party_satisfaction +
    0.2 * (1 - challenge_rate) +
    0.1 * tenure_bonus
)

# Reputation effects
- Higher reputation → Priority in tie-breakers
- Lower reputation → Higher stake requirements
- Zero reputation → Registration revoked
```

## Stake & Slashing

### Stake Requirements
- Minimum stake: 100 units (in configured staking currency)
- Higher stakes unlock higher-value mediations
- Stake locked during active mediations

### Slashing Conditions
- Proposal violates original intent: 10% slash
- Fraudulent matching: 50% slash
- Repeated low-quality proposals: 5% slash per incident

## Security

### Sybil Resistance
- Stake requirements deter mass registration
- Reputation decay for inactive nodes
- Challenge mechanism for suspicious patterns

### Collusion Prevention
- Multi-model consensus reduces single-model manipulation
- Random assignment for proposal evaluation
- Transparent on-chain records

## Implementation Tasks

### Mediator Node Side
- [ ] Implement WebSocket subscriber
- [ ] Build LLM alignment engine
- [ ] Add proposal generation
- [ ] Implement fee tracking
- [ ] Build reputation tracker
- [ ] Add multi-model support

### NatLangChain Side
- [ ] Add `/mediator/register` endpoint
- [ ] Implement `/contracts/stream` WebSocket
- [ ] Add `/contract/propose` endpoint
- [ ] Implement competitive proposal evaluation
- [ ] Add `/mediator/claim-fee` endpoint
- [ ] Build reputation scoring system

## Dependencies

- **Multi-Model Consensus**: For proposal evaluation
- **Value Ledger**: For fee distribution
- **Common**: For schema definitions

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
