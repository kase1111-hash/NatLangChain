# Observance Burn Protocol

## Overview

The Observance Burn is a ceremonial token destruction mechanism that serves both economic and signaling purposes within the NatLangChain ecosystem. Rather than treating burns as mere technical operations, the protocol elevates them to meaningful acts that consecrate system boundaries and demonstrate commitment.

> **Core Philosophy:**
> "Models propose the possible.
> Humans ratify the actual.
> Burns consecrate the boundary."

## Purpose

1. **Economic Deflation**: Permanently removes tokens from circulation
2. **Redistribution**: Proportionally benefits remaining holders
3. **Signaling**: Provides credible, costly proof of commitment
4. **Anti-Abuse**: Discourages system gaming through meaningful cost
5. **Ceremony**: Elevates protocol actions to meaningful observances

---

## Event Schema

### Solidity Event Definition

```solidity
event ObservanceBurn(
    address indexed burner,
    uint256 amount,
    BurnReason reason,
    bytes32 indexed intentHash,  // Links to mediation/contract (0x0 if voluntary)
    string epitaph               // Optional message from burner
);
```

### Burn Reason Enum

```solidity
enum BurnReason {
    VoluntarySignal,        // Pure belief in the system
    EscalationCommitment,   // Triggering an escalation fork
    RateLimitExcess,        // Exceeding daily contract creation threshold
    ProtocolViolation,      // Enforced burns for rule violations
    CommunityDirective      // Governance-initiated burns
}
```

### Indexed Parameters

| Parameter | Type | Indexed | Purpose |
|-----------|------|---------|---------|
| `burner` | address | Yes | Wallet/address performing the burn |
| `amount` | uint256 | No | Amount of tokens destroyed |
| `reason` | uint8 | No | BurnReason enum value |
| `intentHash` | bytes32 | Yes | Keccak256 hash of related mediation/contract |
| `epitaph` | string | No | Optional free-form message |

---

## JSON Schema

For off-chain indexing, explorers, and APIs:

```json
{
  "name": "ObservanceBurn",
  "type": "event",
  "anonymous": false,
  "inputs": [
    {
      "name": "burner",
      "type": "address",
      "indexed": true
    },
    {
      "name": "amount",
      "type": "uint256",
      "indexed": false
    },
    {
      "name": "reason",
      "type": "uint8",
      "indexed": false,
      "enum": [
        "VoluntarySignal",
        "EscalationCommitment",
        "RateLimitExcess",
        "ProtocolViolation",
        "CommunityDirective"
      ]
    },
    {
      "name": "intentHash",
      "type": "bytes32",
      "indexed": true
    },
    {
      "name": "epitaph",
      "type": "string",
      "indexed": false
    }
  ],
  "emittedAt": "uint256",
  "txHash": "bytes32",
  "blockNumber": "uint256"
}
```

---

## Burn Reason Definitions

### 1. VoluntarySignal

**Purpose:** Pure belief signaling with no required context.

Anyone can perform a zero-reason Observance Burn at any time. This becomes a credible, costly signal of belief in the system—akin to proof-of-sacrifice in early tokenomics (like BNB's quarterly burns).

**Use Cases:**
- Long-term holders demonstrating skin in the game
- Periodic "faith burns" by committed participants
- Community health contributions

**Requirements:**
- No minimum amount
- No intent reference required (`intentHash = 0x0`)
- Epitaph optional but encouraged

### 2. EscalationCommitment

**Purpose:** Required burn when triggering an Escalation Fork.

To prevent abuse of the escalation mechanism, parties must sacrifice a percentage of the mediation stake. This ensures escalations are serious commitments, not tactical delays.

**Requirements:**
- **Burn Amount:** 5% of the original mediation stake
- **Intent Reference:** Must link to the mediation being escalated
- **Timing:** Must occur before escalation fork is activated

**Protocol Ceremony Language:**
> "To escalate, you must perform an Observance Burn of 5% of the mediation stake. This amount is permanently removed from circulation and redistributed proportionally to all remaining holders. Do you wish to proceed with the burn?"

### 3. RateLimitExcess

**Purpose:** Cost for exceeding daily contract creation thresholds.

Power users who exceed daily limits can continue by burning tokens, preventing spam while allowing legitimate high-volume users to proceed.

**Requirements:**
- Amount scales with excess (e.g., 0.1 token per excess contract)
- Links to the contract(s) triggering the limit
- Auto-calculated by protocol

### 4. ProtocolViolation

**Purpose:** Enforced burns for rule violations.

Future-proof mechanism for protocol-enforced penalties.

**Examples:**
- Submitting fraudulent evidence
- Repeated bad-faith vetoes
- Gaming reputation systems

### 5. CommunityDirective

**Purpose:** Governance-initiated burns.

Reserved for future governance mechanisms where community consensus triggers burns (e.g., treasury cleanup, inflation control).

---

## Example Emissions

### Escalation Burn

```json
{
  "burner": "0xAlice...",
  "amount": "5000000000000000000",
  "reason": "EscalationCommitment",
  "intentHash": "0xabc123...def456",
  "epitaph": "Burned to fairly escalate and preserve ledger integrity"
}
```

### Voluntary Signal Burn

```json
{
  "burner": "0xBeliever...",
  "amount": "100000000000000000",
  "reason": "VoluntarySignal",
  "intentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "epitaph": "For the long-term health of NatLangChain"
}
```

### Rate Limit Burn

```json
{
  "burner": "0xPowerUser...",
  "amount": "2000000000000000000",
  "reason": "RateLimitExcess",
  "intentHash": "0x789def...abc123",
  "epitaph": ""
}
```

---

## Economic Mechanics

### Redistribution Model

When tokens are burned, the effect is **proportional redistribution** to all remaining holders:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVANCE BURN                               │
│                                                                  │
│  Burn Amount: 100 tokens                                         │
│  Total Supply Before: 1,000,000 tokens                          │
│  Total Supply After: 999,900 tokens                             │
│                                                                  │
│  Effect: Each remaining token is now worth                      │
│          (1,000,000 / 999,900) = 1.0001x its previous value     │
│                                                                  │
│  Holder with 10,000 tokens:                                      │
│    Before: 10,000 / 1,000,000 = 1.0% of supply                  │
│    After:  10,000 / 999,900 = 1.0001% of supply                 │
│    Value gain: 0.0001% increase in ownership                    │
└─────────────────────────────────────────────────────────────────┘
```

### Burn Rate Limits

| Burn Type | Minimum | Maximum | Frequency Limit |
|-----------|---------|---------|-----------------|
| VoluntarySignal | None | None | None |
| EscalationCommitment | 5% of stake | 5% of stake | Per escalation |
| RateLimitExcess | 0.1 token | None | Per excess action |
| ProtocolViolation | Set by protocol | Set by protocol | Per violation |
| CommunityDirective | Set by governance | Set by governance | Per directive |

---

## Integration with Escalation Fork

The Observance Burn integrates with the [Escalation Fork Protocol](./Escalation-Protocol.md) as follows:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESCALATION TRIGGER                            │
│                                                                  │
│  1. Party requests escalation                                    │
│                     │                                            │
│                     ▼                                            │
│  2. OBSERVANCE BURN required (5% of stake)                      │
│     ┌─────────────────────────────────────┐                     │
│     │ ObservanceBurn Event Emitted        │                     │
│     │ - reason: EscalationCommitment      │                     │
│     │ - amount: 5% of mediation stake     │                     │
│     │ - intentHash: mediation ID          │                     │
│     │ - epitaph: (optional)               │                     │
│     └─────────────────────────────────────┘                     │
│                     │                                            │
│                     ▼                                            │
│  3. Fee pool forks (50/50)                                       │
│                     │                                            │
│                     ▼                                            │
│  4. Solver window opens                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Explorer / Dashboard Presentation

### Dedicated "Observance Ledger" Tab

Display burns prominently in public ledger explorers:

```
┌─────────────────────────────────────────────────────────────────┐
│  🔥 OBSERVANCE LEDGER                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Total Supply Reduction: 15,847.32 NLC                          │
│  Total Burns: 1,247                                              │
│  Last 24h: 23.5 NLC burned                                       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  RECENT OBSERVANCES                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔥 5.0 NLC sacrificed — Escalation Commitment                  │
│     "Burned to fairly escalate and preserve ledger integrity"   │
│     0xAlice... • Block 1,234,567 • 2 hours ago                  │
│     → Redistributed to all holders                               │
│                                                                  │
│  🔥 0.1 NLC sacrificed — Voluntary Signal                       │
│     "For the long-term health of NatLangChain"                  │
│     0xBeliever... • Block 1,234,560 • 5 hours ago               │
│     → Redistributed to all holders                               │
│                                                                  │
│  🔥 2.0 NLC sacrificed — Rate Limit Excess                      │
│     (no epitaph)                                                 │
│     0xPowerUser... • Block 1,234,555 • 8 hours ago              │
│     → Redistributed to all holders                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### UI Elements

| Element | Description |
|---------|-------------|
| Icon | Subtle, dignified flame or urn glyph |
| Title | "Observance Burn" |
| Subtitle | `{amount} tokens sacrificed — {reasonLabel}` |
| Body | `{epitaph}` (if present) |
| Footer | "Redistributed proportionally to all remaining holders" |

### Burn Confirmation Dialog

```
┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVANCE BURN                               │
│                                                                  │
│  🔥 You are about to perform an Observance Burn                 │
│                                                                  │
│  Amount: 5.0 NLC                                                 │
│  Reason: Escalation Commitment                                   │
│  Linked Intent: MEDIATION-789                                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Epitaph (optional):                                         │ │
│  │ ____________________________________________________        │ │
│  │                                                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  This amount will be permanently removed from circulation        │
│  and redistributed proportionally to all remaining holders.      │
│                                                                  │
│  [ Cancel ]                              [ Proceed with Burn ]   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/burn/observance` | POST | Perform an Observance Burn |
| `/burn/history` | GET | List all burns (paginated) |
| `/burn/stats` | GET | Get burn statistics |
| `/burn/{txHash}` | GET | Get specific burn details |
| `/burn/address/{address}` | GET | Get burns by address |

### Perform Burn

```python
POST /burn/observance
{
    "amount": "5000000000000000000",
    "reason": "EscalationCommitment",
    "intentHash": "0xabc123...def456",
    "epitaph": "Burned to fairly escalate and preserve ledger integrity",
    "signature": "0x..."
}

Response:
{
    "status": "burned",
    "txHash": "0x...",
    "blockNumber": 1234567,
    "amount": "5000000000000000000",
    "reason": "EscalationCommitment",
    "newTotalSupply": "999995000000000000000000",
    "redistributionEffect": "0.0005%"
}
```

### Get Statistics

```python
GET /burn/stats

Response:
{
    "totalBurned": "15847320000000000000000",
    "totalBurns": 1247,
    "burnsByReason": {
        "VoluntarySignal": 892,
        "EscalationCommitment": 234,
        "RateLimitExcess": 98,
        "ProtocolViolation": 18,
        "CommunityDirective": 5
    },
    "last24Hours": "23500000000000000000",
    "last7Days": "156200000000000000000",
    "largestBurn": {
        "amount": "100000000000000000000",
        "burner": "0x...",
        "epitaph": "In memory of the old protocol",
        "timestamp": "2025-12-01T00:00:00Z"
    }
}
```

---

## Configuration

```python
OBSERVANCE_BURN_CONFIG = {
    "escalation_burn_percentage": 0.05,  # 5% of mediation stake
    "rate_limit_burn_per_excess": "100000000000000000",  # 0.1 tokens
    "minimum_epitaph_length": 0,
    "maximum_epitaph_length": 280,  # Twitter-length
    "voluntary_minimum": "0",
    "voluntary_maximum": None,  # No limit
    "enable_epitaphs": True,
    "enable_voluntary_burns": True
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Related Documents:**
- [SPEC.md](../SPEC.md) - Protocol overview
- [Escalation-Protocol.md](./Escalation-Protocol.md) - Escalation Fork specification
- [VALUE-LEDGER-INTEGRATION.md](../specs/VALUE-LEDGER-INTEGRATION.md) - Value Ledger integration

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
