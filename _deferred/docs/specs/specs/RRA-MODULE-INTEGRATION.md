# RRA-Module ↔ NatLangChain Integration Specification

## Version: 1.0
## Date: January 1, 2026
## Status: Draft

---

## Overview

RRA-Module (Repository Resurrection Agent) is an extension for NatLangChain designed to resurrect dormant or unmanaged GitHub repositories, converting them into self-sustaining, autonomous agents capable of generating revenue through on-chain negotiations and licensing.

## Purpose

Enable RRA-Module to:
1. Scan and analyze dormant repositories
2. Generate value propositions from code
3. Auto-post OFFER contracts on NatLangChain
4. Negotiate licensing terms autonomously
5. Track and distribute earnings to repo owners

## Core Principle

> "Your work sells itself at the door. You no longer have to knock."

RRA-Module transforms passive code into active, self-marketing assets.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       RRA-Module                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Repository Scanner                            │  │
│  │  - GitHub API integration                                  │  │
│  │  - Activity analysis                                       │  │
│  │  - Tech stack detection                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Value Proposition Generator                   │  │
│  │  - LLM-powered code analysis                               │  │
│  │  - Feature extraction                                      │  │
│  │  - Use case identification                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Contract Generator                            │  │
│  │  - OFFER contract creation                                 │  │
│  │  - Pricing strategy                                        │  │
│  │  - License terms                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │              Negotiation Agent                             │  │
│  │  - Auto-respond to proposals                               │  │
│  │  - Counter-offer logic                                     │  │
│  │  - Closure handling                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NatLangChain API                             │
│  POST /contract/post (OFFER)                                    │
│  POST /contract/respond                                         │
│  GET  /contract/list                                            │
└─────────────────────────────────────────────────────────────────┘
```

## API Contract

### 1. Repository Registration

```python
POST /rra/register
{
    "owner": "alice",
    "repos": [
        {
            "url": "github.com/alice/fluid-dynamics-rust",
            "access_token": "ghp_...",
            "auto_post": true,
            "min_price": 100,
            "max_price": 10000,
            "license_types": ["perpetual_commercial", "subscription", "open_source_free"],
            "facilitation_fee": "2%"
        }
    ],
    "notification_preferences": {
        "email": "alice@example.com",
        "webhook": "https://alice.com/rra-notifications"
    },
    "earnings_wallet": "0xAAA..."
}

Response:
{
    "registration_id": "RRA-REG-001",
    "repos_registered": 1,
    "initial_scan_scheduled": "2025-12-19T10:00:00Z"
}
```

### 2. Repository Analysis

```python
# Internal RRA analysis
POST /rra/analyze
{
    "repo_url": "github.com/alice/fluid-dynamics-rust",
    "analysis_depth": "comprehensive"
}

Response:
{
    "repo_id": "RRA-REPO-001",
    "analysis": {
        "tech_stack": ["Rust", "SIMD", "GPU compute"],
        "complexity_score": 0.85,
        "documentation_quality": 0.7,
        "test_coverage": 0.65,

        "features": [
            {
                "name": "Asynchronous fluid simulation",
                "uniqueness": 0.9,
                "market_demand": "high",
                "description": "GPU-accelerated fluid dynamics with async computation"
            },
            {
                "name": "SIMD optimization",
                "uniqueness": 0.7,
                "market_demand": "medium"
            }
        ],

        "use_cases": [
            "Climate modeling",
            "Game development",
            "Engineering simulation",
            "Visual effects"
        ],

        "comparable_projects": [
            {"name": "PhysX", "license": "proprietary"},
            {"name": "OpenFOAM", "license": "GPL"}
        ],

        "suggested_pricing": {
            "perpetual_commercial": "$500-2000",
            "annual_subscription": "$100-300/year",
            "open_source_discount": "free for climate research"
        },

        "effort_estimate": {
            "commits": 847,
            "contributors": 1,
            "estimated_hours": 400
        }
    }
}
```

### 3. Auto-Post OFFER Contract

```python
# RRA-Module → NatLangChain
POST /contract/post
{
    "content": "[CONTRACT: OFFER] Async Fluid Dynamics library in Rust.\n\nHigh-performance GPU-accelerated fluid simulation with:\n- Asynchronous computation pipeline\n- SIMD optimization for CPU fallback\n- 400+ hours of optimization work\n- 847 commits, comprehensive tests\n\nIdeal for: Climate modeling, game development, engineering simulation.\n\nLicensing options:\n- Perpetual commercial: $500 (single project) to $2000 (enterprise)\n- Annual subscription: $150/year\n- FREE for open-source climate research projects\n\n[TERMS: facilitation=2%, escrow=USDC]",

    "author": "rra_module_alice_fluid",
    "intent": "Offer library licensing",
    "contract_type": "offer",

    "terms": {
        "license_options": [
            {
                "type": "perpetual_commercial_single",
                "price": 500,
                "scope": "Single project"
            },
            {
                "type": "perpetual_commercial_enterprise",
                "price": 2000,
                "scope": "Unlimited projects"
            },
            {
                "type": "annual_subscription",
                "price": 150,
                "period": "year"
            },
            {
                "type": "open_source_climate",
                "price": 0,
                "conditions": "Must be open-source climate research"
            }
        ],
        "facilitation": "2%",
        "escrow": "USDC"
    },

    "metadata": {
        "source": "rra_module",
        "rra_registration": "RRA-REG-001",
        "repo_url": "github.com/alice/fluid-dynamics-rust",
        "repo_analysis_hash": "SHA256:...",
        "owner": "alice",
        "owner_wallet": "0xAAA...",
        "auto_negotiate": true,
        "auto_accept_threshold": 90,
        "last_updated": "2025-12-19",
        "refresh_frequency": "weekly"
    }
}
```

### 4. Auto-Negotiation

When a SEEK matches the OFFER:

```python
# NatLangChain → RRA-Module callback
POST {rra_webhook}/proposal
{
    "proposal_id": "PROP-123",
    "offer_ref": {"block": 200, "entry": 0},
    "seek_ref": {"block": 205, "entry": 1},
    "counterparty": "green_horizon_lab",
    "proposed_terms": {
        "license_type": "perpetual_commercial_single",
        "price": 400,
        "use_case": "Ocean current simulation for climate research"
    },
    "match_score": 92,
    "mediator": "mediator_node_alpha"
}

# RRA-Module evaluates and responds
POST /contract/respond
{
    "to_block": 210,
    "to_entry": 0,
    "response_content": "Counter-proposal: Given the climate research use case, we offer a discounted rate of $250 (50% off) with attribution requirement. Alternatively, if project is fully open-source, license is free.",
    "author": "rra_module_alice_fluid",
    "response_type": "counter",
    "counter_terms": {
        "option_1": {
            "type": "discounted_climate",
            "price": 250,
            "conditions": "Attribution required"
        },
        "option_2": {
            "type": "open_source_free",
            "price": 0,
            "conditions": "Project must be fully open-source"
        }
    }
}
```

### 5. Earnings Distribution

```python
# After successful closure
POST /rra/earnings/distribute
{
    "closure_ref": {"block": 220, "entry": 0},
    "settlement_id": "SETTLE-456",
    "gross_amount": 250,
    "breakdown": {
        "owner_share": 245,
        "facilitation_fee": 5
    },
    "owner": "alice",
    "owner_wallet": "0xAAA...",
    "payment_rail": "USDC"
}

Response:
{
    "distribution_id": "DIST-001",
    "status": "queued",
    "estimated_payout": "2025-12-22T00:00:00Z"
}
```

## Daily Work Automation

RRA-Module can also auto-post daily work outputs:

```python
# Git hook integration
POST /rra/daily-output
{
    "repo": "github.com/alice/project",
    "date": "2025-12-19",
    "commits": [
        {
            "hash": "abc123",
            "message": "Implement OAuth 2.0 authentication",
            "files_changed": 12,
            "lines_added": 450,
            "lines_removed": 30
        }
    ],
    "summary": "Added OAuth 2.0 authentication with Google and GitHub providers"
}

# Generates daily OFFER
POST /contract/post
{
    "content": "[CONTRACT: OFFER] Daily work output - OAuth 2.0 Implementation\n\nCompleted today:\n- Full OAuth 2.0 authentication system\n- Google and GitHub providers\n- 450 lines of production code with tests\n\nAvailable for licensing or consultation on similar implementations.\n\n[TERMS: consultation=$150/hr, code_license=$200, facilitation=2%]",

    "author": "rra_module_alice_daily",
    "intent": "Offer daily work",
    "contract_type": "offer",
    "metadata": {
        "source": "rra_daily_output",
        "date": "2025-12-19",
        "banking_enabled": true,
        "bank_after_days": 7,
        "escalator": "5%_weekly"
    }
}
```

## Banking & Bundling

Unsold daily outputs can be banked and bundled:

```python
# After 7 days, bundle unsold work
POST /rra/bundle
{
    "outputs": ["OFFER-001", "OFFER-002", "OFFER-003"],
    "bundle_type": "weekly",
    "bundle_price": 800,
    "escalator": "10%_monthly"
}

# Creates bundled OFFER
POST /contract/post
{
    "content": "[CONTRACT: OFFER] Weekly Bundle - Authentication & API Work\n\nThis week's work includes:\n- OAuth 2.0 implementation\n- Rate limiting middleware\n- API documentation\n\nBundle price: $800 (20% discount vs individual)\nPrice increases 10% monthly.\n\n[TERMS: bundle=true, escalator=10%_monthly]",

    "author": "rra_module_alice_bundle",
    "metadata": {
        "bundle_refs": ["OFFER-001", "OFFER-002", "OFFER-003"],
        "original_value": 1000,
        "bundle_discount": "20%"
    }
}
```

## Implementation Tasks

### RRA-Module Side
- [ ] Implement GitHub API integration
- [ ] Build repository analyzer (LLM-powered)
- [ ] Create value proposition generator
- [ ] Implement contract generator
- [ ] Build negotiation agent
- [ ] Add daily work automation (git hooks)
- [ ] Implement banking and bundling
- [ ] Add earnings distribution

### NatLangChain Side
- [ ] Support RRA metadata fields
- [ ] Add auto-refresh for stale offers
- [ ] Implement bundle contract type
- [ ] Add escalator pricing support

## Dependencies

- **Memory Vault**: For effort tracking
- **IntentLog**: For pricing reasoning
- **Value Ledger**: For earnings distribution
- **Agent OS**: For autonomous negotiation

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specification |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
