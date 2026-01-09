# @natlangchain/sdk

The official TypeScript SDK for **NatLangChain** - the prose-first, intent-native blockchain.

## Installation

```bash
npm install @natlangchain/sdk
# or
yarn add @natlangchain/sdk
# or
pnpm add @natlangchain/sdk
```

## Quick Start

```typescript
import { NatLangChain } from '@natlangchain/sdk';

// Create a client
const client = new NatLangChain({
  endpoint: 'http://localhost:5000',
  apiKey: 'your-api-key' // optional for some endpoints
});

// Or use convenience methods
const local = NatLangChain.local();
const testnet = NatLangChain.testnet('your-key');
const mainnet = NatLangChain.mainnet('your-key');
```

## Modules

The SDK is organized into five modules:

### Core - Entries, Blocks & Chain

```typescript
// Create an entry
const entry = await client.core.createEntry({
  content: 'Alice agrees to deliver 100 widgets to Bob by March 15th',
  author: 'alice@example.com',
  intent: 'Widget delivery agreement',
  validate: true,
  auto_mine: false
});

// Validate without submitting
const validation = await client.core.validateEntry({
  content: 'Transfer all assets...',
  author: 'user',
  intent: 'Asset transfer'
});

// Mine pending entries
const block = await client.core.mine({ difficulty: 2 });

// Get chain stats
const stats = await client.core.stats();
console.log(`${stats.total_entries} entries across ${stats.blocks} blocks`);

// Get narrative (human-readable chain history)
const narrative = await client.core.getNarrative();
```

### Search - Semantic Analysis & Drift Detection

```typescript
// Semantic search
const results = await client.search.semantic({
  query: 'delivery agreements for widgets',
  top_k: 10,
  min_score: 0.7,
  field: 'content'
});

// Find similar entries
const similar = await client.search.findSimilar({
  content: 'Party A will provide services to Party B',
  top_k: 5
});

// Check drift between intent and execution
const drift = await client.search.checkDrift({
  on_chain_intent: 'Deliver 100 widgets by March 15',
  execution_log: 'Shipped 95 widgets on March 20'
});

if (!drift.aligned) {
  console.warn(`Drift detected: ${drift.drift_score}`);
}

// Dialectic validation (Skeptic/Facilitator debate)
const dialectic = await client.search.validateDialectic({
  content: 'Transfer ownership to external wallet',
  author: 'treasury',
  intent: 'Asset consolidation'
});

// Oracle verification
const oracle = await client.search.verifyOracle({
  event_description: 'Weather in NYC on Jan 15',
  claimed_outcome: 'Sunny, above 50F',
  evidence: { weather_api: { temp: 52 } }
});
```

### Contracts - Natural Language Agreements

```typescript
// Parse a contract
const parsed = await client.contracts.parse({
  content: 'I offer to sell 100 widgets at $10 each, delivery in 30 days'
});

// Post an offer
const offer = await client.contracts.post({
  content: 'Offering Python development at $150/hour',
  author: 'dev@example.com',
  intent: 'Service offering',
  contract_type: 'offer',
  terms: { hourly_rate: 150, skills: ['Python'] }
});

// Post a seek
const seek = await client.contracts.post({
  content: 'Looking for Python developer',
  author: 'startup@example.com',
  intent: 'Hiring',
  contract_type: 'seek'
});

// Find matches
const matches = await client.contracts.match({ miner_id: 'matcher-1' });

// List contracts
const openOffers = await client.contracts.list({
  status: 'open',
  type: 'offer'
});

// Respond to a contract
await client.contracts.respond({
  to_block: 5,
  to_entry: 2,
  response_content: 'I accept these terms',
  author: 'buyer@example.com',
  response_type: 'accept'
});

// Counter-offer (triggers mediation)
const counter = await client.contracts.respond({
  to_block: 5,
  to_entry: 2,
  response_content: 'I propose $175/hour instead',
  author: 'contractor@example.com',
  response_type: 'counter',
  counter_terms: { hourly_rate: 175 }
});
```

### Disputes - Resolution Pipeline

```typescript
// File a dispute
const dispute = await client.disputes.file({
  complainant: 'alice@example.com',
  respondent: 'bob@example.com',
  description: 'Failed to deliver as agreed',
  related_entries: [{ block: 5, entry: 2 }],
  evidence: { tracking: 'No shipment recorded' }
});

// Submit evidence
await client.disputes.submitEvidence(dispute.dispute.id, {
  submitter: 'alice@example.com',
  evidence_type: 'communication',
  content: 'Email showing promised delivery date'
});

// Get AI analysis
const analysis = await client.disputes.analyze(dispute.dispute.id);
console.log('Recommended:', analysis.analysis.recommended_outcome);

// Escalate
await client.disputes.escalate(dispute.dispute.id, 'Unable to reach agreement');

// Resolve
await client.disputes.resolve(dispute.dispute.id, {
  outcome: 'Bob to refund $50',
  resolved_by: 'mediator@natlangchain.org'
});
```

### Settlements - Mediator Protocol

```typescript
// Propose settlement
const settlement = await client.settlements.propose({
  intent_a: 'Alice wants to sell widgets',
  intent_b: 'Bob wants to buy widgets',
  terms: 'Alice sells 100 widgets to Bob for $1000',
  fee: 10
});

// Both parties accept
await client.settlements.accept(settlement.settlement.id, {
  party: 'A',
  party_id: 'alice@example.com'
});

await client.settlements.accept(settlement.settlement.id, {
  party: 'B',
  party_id: 'bob@example.com'
});

// Check status
const status = await client.settlements.getStatus(settlement.settlement.id);

// Claim payout
await client.settlements.claimPayout(settlement.settlement.id);

// Mediator operations
await client.settlements.bondStake(1000);
const rep = await client.settlements.getReputation('mediator_123');
```

## Error Handling

```typescript
import { NatLangChain, NatLangChainError, NetworkError } from '@natlangchain/sdk';

try {
  await client.core.createEntry({ ... });
} catch (error) {
  if (error instanceof NatLangChainError) {
    // API returned an error
    console.error(`API Error ${error.status}: ${error.message}`);
    console.error('Details:', error.apiError);
  } else if (error instanceof NetworkError) {
    // Network/timeout error
    console.error('Network error:', error.message);
  }
}
```

## Configuration

```typescript
const client = new NatLangChain({
  // Required: API endpoint
  endpoint: 'https://api.natlangchain.org',

  // Optional: API key for authenticated endpoints
  apiKey: 'your-api-key',

  // Optional: Request timeout (default: 30000ms)
  timeout: 60000,

  // Optional: Custom headers
  headers: {
    'X-Custom-Header': 'value'
  },

  // Optional: Retry configuration
  retry: {
    attempts: 3,      // Number of retries (default: 3)
    delay: 1000,      // Base delay in ms (default: 1000)
    maxDelay: 10000   // Max delay in ms (default: 10000)
  }
});
```

## TypeScript Support

Full TypeScript support with exported types:

```typescript
import type {
  Entry,
  Block,
  ValidationResult,
  CreateEntryRequest,
  SemanticSearchResponse,
  Dispute,
  Settlement,
  NatLangChainConfig
} from '@natlangchain/sdk';
```

## License

MIT
