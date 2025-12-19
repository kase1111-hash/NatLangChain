# Agent OS ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Agent OS is the locally-controlled, constitutionally-governed AI infrastructure that serves as the root of trust for the NatLangChain ecosystem. This specification defines how Agent OS integrates with NatLangChain to enable autonomous intent posting and alignment reception.

## Purpose

Enable Agent OS instances to:
1. Post standing intents on behalf of users
2. Receive alignment proposals from Mediator Nodes
3. Auto-accept/counter based on Learning Contract constraints
4. Record agent actions for audit and compliance

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Agent OS                       │
│  ┌─────────────────────────────────────────┐    │
│  │        Learning Contract Enforcer        │    │
│  │  (Validates all actions against rules)   │    │
│  └──────────────────┬──────────────────────┘    │
│                     │                            │
│  ┌──────────────────▼──────────────────────┐    │
│  │         NatLangChain Client              │    │
│  │  - Post intents                          │    │
│  │  - Receive alignments                    │    │
│  │  - Auto-negotiate                        │    │
│  └──────────────────┬──────────────────────┘    │
└─────────────────────┼───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              NatLangChain API                   │
│  POST /entry (with agent metadata)              │
│  POST /contract/post                            │
│  POST /contract/respond                         │
└─────────────────────────────────────────────────┘
```

## API Contract

### 1. Agent Registration

Before posting intents, Agent OS must register with NatLangChain:

```python
POST /agent/register
{
    "agent_id": "agent_os_instance_1",
    "owner": "alice",
    "learning_contract_hash": "SHA256...",
    "capabilities": ["code_review", "web_development"],
    "callback_url": "https://agent.alice.com/callback",
    "public_key": "-----BEGIN PUBLIC KEY-----..."
}

Response:
{
    "status": "registered",
    "agent_id": "agent_os_instance_1",
    "registration_block": 42,
    "expiry": "2026-12-19T00:00:00Z"
}
```

### 2. Posting Standing Intents

Agent OS posts standing intents that persist until fulfilled or revoked:

```python
POST /entry
{
    "content": "Agent offering code review services for Python/JavaScript projects. Available 24/7.",
    "author": "agent_os_instance_1",
    "intent": "Offer code review",
    "metadata": {
        "source": "agent_os",
        "agent_id": "agent_os_instance_1",
        "owner": "alice",
        "learning_contract_ref": "LC-001",
        "standing_intent": true,
        "auto_accept_threshold": 85,
        "max_commitments": 5,
        "rate_limit": {
            "max_per_day": 10,
            "cooldown_hours": 24
        },
        "constraints": {
            "min_value": 100,
            "max_value": 10000,
            "currency": "USD",
            "allowed_counterparty_types": ["individual", "business"]
        }
    }
}
```

### 3. Receiving Alignment Callbacks

NatLangChain calls back to Agent OS when alignments are proposed:

```python
# NatLangChain → Agent OS Callback
POST {callback_url}/alignment
{
    "alignment_id": "ALIGN-123",
    "proposal_block": 50,
    "proposal_hash": "000abc...",
    "match_score": 92,
    "counterparty": {
        "id": "bob",
        "type": "individual",
        "reputation_score": 0.95
    },
    "proposed_terms": {
        "scope": "Review 500 lines of Python code",
        "value": 250,
        "currency": "USD",
        "deadline": "2025-12-22T00:00:00Z",
        "facilitation_fee": "2%"
    },
    "mediator_id": "mediator_node_alpha",
    "requires_response_by": "2025-12-20T12:00:00Z"
}

# Agent OS → NatLangChain Response
POST /contract/respond
{
    "to_block": 50,
    "to_entry": 0,
    "response_content": "Agent accepts proposal with confirmed availability",
    "author": "agent_os_instance_1",
    "response_type": "accept",
    "signature": "..."
}
```

### 4. Auto-Accept Logic

Agent OS implements decision logic based on Learning Contract:

```python
class AgentOSIntentHandler:
    def evaluate_proposal(self, proposal: dict) -> str:
        """
        Returns: "accept", "counter", "reject", or "escalate_to_human"
        """
        # Check Learning Contract constraints
        if not self.learning_contract.allows_action(proposal):
            return "reject"

        # Check match score threshold
        if proposal["match_score"] >= self.config.auto_accept_threshold:
            return "accept"

        # Check if within negotiable range
        if proposal["match_score"] >= self.config.counter_threshold:
            return "counter"

        # Below thresholds - escalate to human
        return "escalate_to_human"

    def generate_counter(self, proposal: dict) -> dict:
        """Generate counter-proposal within Learning Contract bounds"""
        return {
            "response_type": "counter",
            "counter_terms": {
                "value": proposal["proposed_terms"]["value"] * 1.1,
                "deadline": self.extend_deadline(proposal, days=2)
            }
        }
```

## Learning Contract Verification

Before any autonomous action, Agent OS must verify against Learning Contract:

```python
# Learning Contract Interface
class LearningContractVerifier:
    def allows_action(self, action: dict) -> bool:
        """Check if action is within Learning Contract bounds"""

    def max_autonomous_value(self) -> float:
        """Maximum value agent can commit without human approval"""

    def allowed_counterparty_types(self) -> List[str]:
        """Types of counterparties agent can engage with"""

    def requires_human_approval(self, action: dict) -> bool:
        """Check if action needs human sign-off"""
```

## Security Requirements

### Authentication
- All Agent OS requests must be signed with agent's private key
- NatLangChain verifies signature against registered public key
- Callbacks from NatLangChain are signed with chain's key

### Rate Limiting
- Max intents per agent per day: Configurable (default: 100)
- Max responses per agent per hour: Configurable (default: 50)
- Cooldown after rejection: 1 hour

### Audit Trail
- All agent actions recorded on-chain
- Learning Contract violations flagged
- Human override capability always available

## Implementation Tasks

### Agent OS Side
- [ ] Implement NatLangChain client library
- [ ] Add Learning Contract verification layer
- [ ] Implement callback webhook handler
- [ ] Add auto-accept/counter decision engine
- [ ] Implement rate limiting and cooldowns
- [ ] Add human escalation interface

### NatLangChain Side
- [ ] Add `/agent/register` endpoint
- [ ] Add agent metadata validation
- [ ] Implement callback webhook system
- [ ] Add agent-specific rate limiting
- [ ] Implement signature verification
- [ ] Add agent activity auditing

## Error Handling

| Error Code | Description | Agent Action |
|------------|-------------|--------------|
| `LEARNING_CONTRACT_VIOLATION` | Action exceeds LC bounds | Reject and log |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Back off and retry |
| `SIGNATURE_INVALID` | Authentication failed | Re-register |
| `ALIGNMENT_EXPIRED` | Response too late | Log and skip |
| `COUNTERPARTY_BLOCKED` | Owner blocked counterparty | Reject |

## Testing Requirements

1. **Unit Tests**
   - Learning Contract verification
   - Auto-accept logic
   - Counter-proposal generation

2. **Integration Tests**
   - End-to-end intent posting
   - Callback handling
   - Signature verification

3. **Security Tests**
   - Signature forgery attempts
   - Rate limit bypass attempts
   - Learning Contract bypass attempts

## Dependencies

- **Learning Contracts**: For action validation
- **Boundary Daemon**: For trust boundary enforcement
- **IntentLog**: For reasoning context

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
