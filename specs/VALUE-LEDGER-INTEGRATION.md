# Value Ledger ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Value Ledger serves as the dedicated accounting layer for the NatLangChain ecosystem, tracking meta-value derived from cognitive processes without storing sensitive content. This specification defines how settlements from NatLangChain (MP-05) are transformed into capitalization interfaces.

## Purpose

Enable Value Ledger to:
1. Receive settlement records from NatLangChain
2. Generate capitalization interfaces for external systems
3. Track facilitation fees owed to Mediator Nodes
4. Interface with payment rails (USDC, BTC, traditional banking)
5. Maintain audit trails for compliance

## Core Principle

> "Value is downstream of meaning, not the reverse."

Value Ledger records the financial implications of agreements but does not determine their validity. All value originates from human-ratified NatLangChain settlements.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NatLangChain                                │
│  Settlement Declaration (MP-05)                                 │
│  "I declare receipts R-101 to R-149 satisfy Agreement A-12"     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Value Ledger                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Settlement Ingester                          │  │
│  │  - Validates settlement references                         │  │
│  │  - Extracts value description                              │  │
│  │  - Records capitalization event                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │           Capitalization Interface Generator               │  │
│  │  - Generates payment instructions                          │  │
│  │  - Creates escrow references                               │  │
│  │  - Produces accounting entries                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Payment Rails Adapter                         │  │
│  │  - USDC/ETH smart contracts                                │  │
│  │  - BTC Lightning                                           │  │
│  │  - Traditional ACH/Wire                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## API Contract

### 1. Receiving Settlement Records

NatLangChain pushes settlements to Value Ledger:

```python
POST /capitalization/ingest
{
    "settlement_id": "SETTLE-789",
    "source_chain": "natlangchain_mainnet",
    "settlement_block": 150,
    "settlement_hash": "000xyz...",

    "agreement_refs": [
        {"block": 100, "entry": 0, "hash": "000abc..."}
    ],
    "receipt_refs": [
        {"id": "R-101", "hash": "..."},
        {"id": "R-149", "hash": "..."}
    ],

    "parties": [
        {"id": "alice", "role": "provider", "wallet": "0xAAA..."},
        {"id": "bob", "role": "receiver", "wallet": "0xBBB..."}
    ],

    "value_description": {
        "total_amount": 5000,
        "currency": "USD",
        "breakdown": [
            {"description": "Service fee", "amount": 4900},
            {"description": "Facilitation fee (2%)", "amount": 100}
        ]
    },

    "facilitation": {
        "mediator_id": "mediator_node_alpha",
        "fee_percentage": 2,
        "fee_amount": 100,
        "mediator_wallet": "0xCCC..."
    },

    "payment_preferences": {
        "preferred_rail": "USDC",
        "chain": "Ethereum",
        "escrow_required": true
    },

    "declarations": [
        {
            "party": "alice",
            "content": "I declare receipts R-101 to R-149 satisfy Agreement A-12",
            "timestamp": "2025-12-19T15:00:00Z",
            "signature": "..."
        },
        {
            "party": "bob",
            "content": "I confirm delivery is complete",
            "timestamp": "2025-12-19T15:30:00Z",
            "signature": "..."
        }
    ]
}

Response:
{
    "status": "ingested",
    "capitalization_id": "CAP-456",
    "capitalization_interface": {...},
    "escrow_address": "0xESCROW...",
    "next_steps": [
        "Await escrow funding from bob",
        "Release to alice upon confirmation"
    ]
}
```

### 2. Generating Capitalization Interface

```python
GET /capitalization/{cap_id}/interface

Response:
{
    "capitalization_id": "CAP-456",
    "settlement_ref": "SETTLE-789",

    "payment_instructions": {
        "rail": "USDC",
        "chain": "Ethereum",
        "escrow_contract": "0xESCROW...",
        "escrow_abi": "...",

        "funding": {
            "payer": "bob",
            "amount": 5000,
            "token": "USDC",
            "deadline": "2025-12-22T00:00:00Z"
        },

        "release_conditions": [
            {
                "recipient": "alice",
                "amount": 4900,
                "condition": "Mutual settlement confirmed on-chain"
            },
            {
                "recipient": "mediator_node_alpha",
                "amount": 100,
                "condition": "Automatic on settlement"
            }
        ]
    },

    "accounting_entries": [
        {
            "date": "2025-12-19",
            "account": "Accounts Receivable - alice",
            "debit": 4900,
            "credit": 0,
            "memo": "Service fee per Agreement A-12"
        },
        {
            "date": "2025-12-19",
            "account": "Accounts Payable - bob",
            "debit": 0,
            "credit": 5000,
            "memo": "Payment due per Agreement A-12"
        }
    ],

    "tax_implications": {
        "jurisdiction": "US",
        "alice_income": 4900,
        "alice_form": "1099-NEC",
        "mediator_income": 100,
        "mediator_form": "1099-NEC"
    },

    "compliance": {
        "sec_17a4_compliant": true,
        "audit_trail_available": true,
        "worm_export_ready": true
    }
}
```

### 3. Escrow Operations

```python
# Create escrow
POST /escrow/create
{
    "capitalization_id": "CAP-456",
    "escrow_type": "USDC_ETH",
    "amount": 5000,
    "parties": ["alice", "bob"],
    "release_conditions": "mutual_settlement",
    "timeout_days": 30,
    "timeout_action": "refund_to_payer"
}

Response:
{
    "escrow_id": "ESC-123",
    "contract_address": "0xESCROW...",
    "funding_deadline": "2025-12-22T00:00:00Z",
    "status": "awaiting_funding"
}

# Fund escrow (triggered by on-chain event)
POST /escrow/{escrow_id}/funded
{
    "tx_hash": "0xTX...",
    "amount_received": 5000,
    "funded_by": "bob",
    "timestamp": "2025-12-20T10:00:00Z"
}

# Release escrow
POST /escrow/{escrow_id}/release
{
    "settlement_confirmation": {
        "block": 151,
        "hash": "000final..."
    },
    "release_to": [
        {"recipient": "alice", "amount": 4900},
        {"recipient": "mediator_node_alpha", "amount": 100}
    ]
}
```

### 4. Fee Distribution

```python
# Query pending fees
GET /fees/pending?mediator_id=mediator_node_alpha

Response:
{
    "mediator_id": "mediator_node_alpha",
    "pending_fees": [
        {
            "settlement_ref": "SETTLE-789",
            "amount": 100,
            "currency": "USD",
            "status": "awaiting_escrow_release"
        }
    ],
    "total_pending": 100,
    "total_earned_all_time": 5000
}

# Claim fee (after escrow release)
POST /fees/claim
{
    "mediator_id": "mediator_node_alpha",
    "settlement_ref": "SETTLE-789",
    "claim_signature": "..."
}
```

## Data Schemas

### Capitalization Record

```python
{
    "capitalization_id": str,
    "settlement_ref": str,
    "created_at": datetime,
    "status": "pending" | "funded" | "released" | "disputed" | "refunded",

    "value": {
        "gross_amount": float,
        "net_to_provider": float,
        "facilitation_fee": float,
        "currency": str
    },

    "escrow": {
        "type": str,
        "address": str,
        "chain": str,
        "status": str
    },

    "parties": [
        {
            "id": str,
            "role": str,
            "wallet": str,
            "amount_due": float
        }
    ],

    "audit_trail": [
        {
            "action": str,
            "timestamp": datetime,
            "actor": str,
            "details": dict
        }
    ]
}
```

## Payment Rails

### Supported Rails

| Rail | Status | Description |
|------|--------|-------------|
| USDC (Ethereum) | Planned | ERC-20 stablecoin escrow |
| USDC (Polygon) | Planned | Lower gas fees |
| BTC (Lightning) | Planned | Fast micropayments |
| ACH | Future | US bank transfers |
| SEPA | Future | EU bank transfers |

### Escrow Contract Interface

```solidity
interface INatLangChainEscrow {
    function deposit(bytes32 settlementId, address recipient) external payable;
    function release(bytes32 settlementId, address[] recipients, uint256[] amounts) external;
    function refund(bytes32 settlementId) external;
    function dispute(bytes32 settlementId, string reason) external;
}
```

## Compliance Features

### SEC 17a-4 Compliance
- All records are append-only
- WORM export capability
- Tamper-evident audit trails

### Tax Reporting
- Automatic 1099 generation for US
- Jurisdiction detection
- Export to accounting software

### Audit Trail
- Every state change recorded
- Cryptographic proof of each step
- External auditor access API

## Implementation Tasks

### Value Ledger Side
- [ ] Implement settlement ingester
- [ ] Build capitalization interface generator
- [ ] Create escrow smart contracts (USDC)
- [ ] Add fee distribution system
- [ ] Implement compliance exports
- [ ] Build accounting entry generator

### NatLangChain Side
- [ ] Add settlement push to Value Ledger
- [ ] Implement MP-05 settlement declaration
- [ ] Add capitalization status tracking
- [ ] Integrate escrow status callbacks

## Dependencies

- **NatLangChain**: Settlement source
- **Mediator Node**: Fee recipients
- **Common**: Schema definitions
- **External**: Ethereum, Oracle networks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
