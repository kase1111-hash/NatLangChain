# Common ↔ All Repositories Integration Specification

## Version: 1.0
## Date: December 19, 2025
## Status: Draft

---

## Overview

Common is the shared library providing schemas, cryptographic primitives, receipt formats, and provenance standards used across all 11 repositories in the NatLangChain ecosystem.

## Purpose

Enable Common to provide:
1. Shared data schemas
2. Cryptographic primitives
3. Receipt formats
4. Provenance standards
5. Inter-repo communication protocols

## Core Principle

> "Consistency across the ecosystem enables trust between components."

Common ensures all repos speak the same language.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Common                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    Schemas      │  │     Crypto      │  │    Formats      │  │
│  │  - Entry        │  │  - Hashing      │  │  - Receipts     │  │
│  │  - Contract     │  │  - Signing      │  │  - Certificates │  │
│  │  - Receipt      │  │  - Verification │  │  - Exports      │  │
│  │  - License      │  │  - Keys         │  │  - Provenance   │  │
│  │  - Settlement   │  │                 │  │                 │  │
│  │  - Dispute      │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────────────┐
│   NatLangChain    │ │   Agent OS    │ │  All Other Repos      │
│   Value Ledger    │ │   IntentLog   │ │  Memory Vault         │
│   Mediator Node   │ │               │ │  Boundary Daemon      │
│                   │ │               │ │  RRA-Module           │
│                   │ │               │ │  Finite-Intent-Exec   │
│                   │ │               │ │  Learning Contracts   │
└───────────────────┘ └───────────────┘ └───────────────────────┘
```

## Shared Schemas

### 1. Entry Schema

The fundamental unit of NatLangChain:

```python
# common/schemas/entry.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

@dataclass
class EntryMetadata:
    validation_status: str  # "valid" | "pending" | "invalid"
    validation_mode: Optional[str] = None
    paraphrase: Optional[str] = None

    # Entry type flags
    is_contract: bool = False
    contract_type: Optional[str] = None  # "offer" | "seek" | "proposal" | "response" | "closure"
    is_effort_receipt: bool = False
    is_license: bool = False
    is_settlement: bool = False
    is_dispute: bool = False
    is_learning_contract: bool = False
    is_delayed_intent: bool = False
    is_boundary_event: bool = False

    # Temporal fixity
    temporal_fixity_enabled: bool = False
    t0_snapshot: Optional[Dict] = None

    # References
    intentlog_ref: Optional[str] = None
    vault_refs: Optional[List[str]] = None
    learning_contract_ref: Optional[str] = None

    # Additional metadata
    extra: Optional[Dict[str, Any]] = None

@dataclass
class NaturalLanguageEntry:
    content: str
    author: str
    intent: str
    timestamp: datetime
    metadata: EntryMetadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "author": self.author,
            "intent": self.intent,
            "timestamp": self.timestamp.isoformat(),
            "metadata": asdict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "NaturalLanguageEntry":
        return cls(
            content=data["content"],
            author=data["author"],
            intent=data["intent"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=EntryMetadata(**data["metadata"])
        )
```

### 2. Contract Schema

```python
# common/schemas/contract.py

@dataclass
class ContractTerms:
    license_type: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    duration: Optional[str] = None
    scope: Optional[str] = None
    facilitation_fee: str = "2%"
    escrow_required: bool = False
    escrow_type: Optional[str] = None

@dataclass
class Contract:
    contract_type: str  # "offer" | "seek" | "proposal" | "response" | "closure"
    terms: ContractTerms
    entry_ref: Dict[str, Any]  # {"block": int, "entry": int}
    author: str
    counterparty: Optional[str] = None
    status: str = "open"  # "open" | "negotiating" | "matched" | "closed" | "expired"
    match_refs: Optional[List[Dict]] = None
```

### 3. Receipt Schema (MP-02)

```python
# common/schemas/receipt.py

@dataclass
class ValidationMetadata:
    coherence_score: float
    progression_detected: bool
    validator_id: str
    model_version: str
    dissent: Optional[str] = None

@dataclass
class EffortReceipt:
    receipt_id: str
    time_bounds: Dict[str, str]  # {"start": ISO, "end": ISO}
    signal_hashes: List[str]
    effort_summary: str
    validation_metadata: ValidationMetadata
    observer_id: str
    prior_receipts: List[str]

    def compute_hash(self) -> str:
        """Compute deterministic hash of receipt"""
        from common.crypto import hash_dict
        return hash_dict(self.to_dict())
```

### 4. License Schema (MP-04)

```python
# common/schemas/license.py

@dataclass
class License:
    license_id: str
    subject: str          # What is licensed
    purpose: str          # Allowed use cases
    limits: str           # Prohibited actions
    duration: str         # Time-bounded or perpetual
    transferability: str  # Sublicensing rules
    grantor: str
    grantee: str
    agreement_ref: Dict[str, Any]
    receipt_refs: List[str]
    status: str = "active"  # "active" | "expired" | "revoked"
```

### 5. Settlement Schema (MP-05)

```python
# common/schemas/settlement.py

@dataclass
class ValueDescription:
    amount: float
    currency: str
    formula: Optional[str] = None  # For complex calculations

@dataclass
class Settlement:
    settlement_id: str
    agreement_refs: List[Dict]
    receipt_refs: List[str]
    value_description: ValueDescription
    conditions: Optional[str] = None  # Vesting rules
    parties: List[str]
    declarations: List[Dict]  # Each party's declaration
    capitalization_interface: Optional[Dict] = None
    status: str = "pending"  # "pending" | "funded" | "released" | "disputed"
```

### 6. Dispute Schema (MP-03)

```python
# common/schemas/dispute.py

@dataclass
class Dispute:
    dispute_id: str
    claimant: str
    respondent: str
    contested_refs: List[Dict]  # Receipts/agreements contested
    description: str
    escalation_path: str
    evidence_frozen: bool = False
    status: str = "open"  # "open" | "clarifying" | "escalated" | "resolved"
    resolution: Optional[str] = None
```

### 7. Learning Contract Schema

```python
# common/schemas/learning_contract.py

@dataclass
class ObservationScope:
    allowed: List[Dict]
    prohibited: List[Dict]

@dataclass
class GeneralizationRules:
    allowed: List[Dict]
    prohibited: List[Dict]

@dataclass
class RetentionPolicy:
    default_retention: str
    persistent_allowed: List[str]
    persistent_duration: str
    right_to_forget: bool

@dataclass
class LearningContract:
    contract_id: str
    version: int
    owner: str
    agent_id: str
    observation_scope: ObservationScope
    generalization_rules: GeneralizationRules
    retention: RetentionPolicy
    revocable: bool
    status: str = "active"
```

## Cryptographic Primitives

```python
# common/crypto/__init__.py

import hashlib
import json
from typing import Dict, Any

def hash_content(content: str) -> str:
    """SHA-256 hash of string content"""
    return hashlib.sha256(content.encode()).hexdigest()

def hash_dict(data: Dict[str, Any]) -> str:
    """Deterministic hash of dictionary"""
    # Sort keys for determinism
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hash_content(canonical)

def verify_hash(content: str, expected_hash: str) -> bool:
    """Verify content matches expected hash"""
    return hash_content(content) == expected_hash

# Signature primitives
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

def generate_keypair():
    """Generate RSA key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    return private_key, private_key.public_key()

def sign(message: bytes, private_key) -> bytes:
    """Sign message with private key"""
    return private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

def verify_signature(message: bytes, signature: bytes, public_key) -> bool:
    """Verify signature with public key"""
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False
```

## Receipt Formats

```python
# common/formats/receipt.py

def format_receipt_for_chain(receipt: EffortReceipt) -> str:
    """Format receipt for NatLangChain entry"""
    return f"""Effort Receipt {receipt.receipt_id}

Time: {receipt.time_bounds['start']} to {receipt.time_bounds['end']}

Summary: {receipt.effort_summary}

Signal Count: {len(receipt.signal_hashes)}
Aggregate Hash: {receipt.compute_hash()}

Validation:
- Coherence: {receipt.validation_metadata.coherence_score}
- Progression: {receipt.validation_metadata.progression_detected}
- Validator: {receipt.validation_metadata.validator_id}

Prior Receipts: {', '.join(receipt.prior_receipts) if receipt.prior_receipts else 'None (first receipt)'}
"""

def format_receipt_for_worm(receipt: EffortReceipt) -> Dict:
    """Format receipt for WORM archival"""
    return {
        "format_version": "1.0",
        "format_type": "WORM_RECEIPT",
        "receipt": receipt.to_dict(),
        "integrity_hash": receipt.compute_hash(),
        "archival_timestamp": datetime.utcnow().isoformat()
    }
```

## Provenance Standards

```python
# common/provenance/__init__.py

@dataclass
class ProvenanceRecord:
    """Track origin and transformations of data"""
    origin_type: str  # "human" | "model" | "system"
    origin_id: str
    origin_timestamp: datetime
    transformations: List[Dict]  # Each transformation applied
    current_hash: str
    chain_of_custody: List[str]  # IDs of handlers

def create_provenance(content: str, author: str, origin_type: str = "human") -> ProvenanceRecord:
    """Create provenance record for new content"""
    return ProvenanceRecord(
        origin_type=origin_type,
        origin_id=author,
        origin_timestamp=datetime.utcnow(),
        transformations=[],
        current_hash=hash_content(content),
        chain_of_custody=[author]
    )

def add_transformation(provenance: ProvenanceRecord, transform_type: str, actor: str, new_hash: str) -> ProvenanceRecord:
    """Record a transformation of the content"""
    provenance.transformations.append({
        "type": transform_type,
        "actor": actor,
        "timestamp": datetime.utcnow().isoformat(),
        "previous_hash": provenance.current_hash,
        "new_hash": new_hash
    })
    provenance.current_hash = new_hash
    provenance.chain_of_custody.append(actor)
    return provenance
```

## Inter-Repo Communication Protocol

```python
# common/protocol/__init__.py

from enum import Enum

class MessageType(Enum):
    ENTRY_CREATED = "entry_created"
    CONTRACT_POSTED = "contract_posted"
    CONTRACT_MATCHED = "contract_matched"
    SETTLEMENT_DECLARED = "settlement_declared"
    DISPUTE_FILED = "dispute_filed"
    LEARNING_CONTRACT_UPDATED = "learning_contract_updated"
    BOUNDARY_VIOLATION = "boundary_violation"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"

@dataclass
class InterRepoMessage:
    message_type: MessageType
    source_repo: str
    target_repo: str
    payload: Dict[str, Any]
    timestamp: datetime
    signature: str

    def validate(self) -> bool:
        """Validate message integrity"""
        # Verify signature, check timestamp freshness
        pass

# Webhook format
def format_webhook_payload(message: InterRepoMessage) -> Dict:
    return {
        "version": "1.0",
        "type": message.message_type.value,
        "source": message.source_repo,
        "target": message.target_repo,
        "payload": message.payload,
        "timestamp": message.timestamp.isoformat(),
        "signature": message.signature
    }
```

## Implementation Tasks

### Common Side
- [ ] Implement all schema dataclasses
- [ ] Add cryptographic primitives
- [ ] Create receipt format utilities
- [ ] Build provenance tracking
- [ ] Define inter-repo protocol
- [ ] Add validation utilities
- [ ] Create serialization helpers

### All Repos Side
- [ ] Import common as dependency
- [ ] Use common schemas
- [ ] Follow provenance standards
- [ ] Implement inter-repo messaging

## Package Structure

```
common/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── entry.py
│   ├── contract.py
│   ├── receipt.py
│   ├── license.py
│   ├── settlement.py
│   ├── dispute.py
│   └── learning_contract.py
├── crypto/
│   ├── __init__.py
│   ├── hashing.py
│   └── signing.py
├── formats/
│   ├── __init__.py
│   ├── receipt.py
│   ├── certificate.py
│   └── worm.py
├── provenance/
│   ├── __init__.py
│   └── tracking.py
├── protocol/
│   ├── __init__.py
│   ├── messages.py
│   └── webhooks.py
└── utils/
    ├── __init__.py
    ├── validation.py
    └── serialization.py
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
