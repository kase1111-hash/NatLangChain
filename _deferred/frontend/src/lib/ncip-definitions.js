/**
 * NCIP Definitions for GUI Tooltips
 *
 * These definitions are derived from the NatLangChain Improvement Proposals (NCIPs)
 * and provide contextual help throughout the application.
 *
 * References:
 * - NCIP-000: Terminology & Semantics Governance
 * - NCIP-001: Canonical Term Registry
 * - NCIP-002: Semantic Drift Thresholds & Validator Responses
 * - NCIP-003: Multilingual Semantic Alignment & Drift
 * - NCIP-004: Proof of Understanding (PoU) Generation & Verification
 * - NCIP-005: Dispute Escalation, Cooling Periods & Semantic Locking
 */

export const ncipDefinitions = {
  // Navigation Items
  dashboard: {
    text: 'Overview of chain statistics, validation status, and recent activity. Shows total blocks, entries, and chain integrity.',
    ncipRef: 'NCIP-000',
  },
  chainExplorer: {
    text: 'Browse the blockchain and inspect individual blocks and their entries. Each entry contains prose, metadata, and timestamps.',
    ncipRef: 'NCIP-001',
  },
  submitEntry: {
    text: 'Create a new Entry - a discrete, timestamped record containing prose, metadata, and signatures within the NatLangChain system.',
    ncipRef: 'NCIP-001',
  },
  contracts: {
    text: 'Manage Agreements - mutually ratified Intents establishing shared understanding and obligations between parties.',
    ncipRef: 'NCIP-001',
  },
  search: {
    text: 'Search entries using basic keyword matching or semantic search powered by AI understanding of meaning.',
    ncipRef: 'NCIP-002',
  },

  // Core Terms (from NCIP-001)
  entry: {
    text: 'A discrete, timestamped record containing prose, metadata, and signatures. Entries form the canonical audit trail.',
    ncipRef: 'NCIP-001',
  },
  intent: {
    text: 'A human-authored expression of desired outcome or commitment, recorded as prose and treated as the primary semantic input.',
    ncipRef: 'NCIP-001',
  },
  agreement: {
    text: 'A mutually ratified Intent or set of Intents establishing shared understanding and obligations between parties.',
    ncipRef: 'NCIP-001',
  },
  ratification: {
    text: 'An explicit act of consent confirming understanding and acceptance of an Intent or Agreement.',
    ncipRef: 'NCIP-001',
  },

  // Validation & Drift (from NCIP-002)
  validation: {
    text: 'Checks entries against semantic drift thresholds (D0-D4). D0 is stable, D4 is a semantic break requiring dispute resolution.',
    ncipRef: 'NCIP-002',
  },
  semanticDrift: {
    text: 'The divergence between original intended meaning and subsequent interpretation. Measured as a score from 0.0 (identical) to 1.0 (contradictory).',
    ncipRef: 'NCIP-002',
  },
  driftThresholds: {
    text: 'D0 (Stable): 0-10%, D1 (Soft Drift): 10-25%, D2 (Ambiguous): 25-45%, D3 (Hard Drift): 45-70%, D4 (Break): 70-100%.',
    ncipRef: 'NCIP-002',
  },

  // Proof of Understanding (from NCIP-004)
  proofOfUnderstanding: {
    text: 'Evidence that a party has demonstrably comprehended the meaning and implications of an Intent or Agreement. Semantic, not just cryptographic.',
    ncipRef: 'NCIP-004',
  },

  // Disputes (from NCIP-005)
  dispute: {
    text: 'A formally raised challenge asserting misinterpretation, non-compliance, or unresolved ambiguity in an Agreement.',
    ncipRef: 'NCIP-005',
  },
  semanticLock: {
    text: 'A binding freeze of interpretive meaning at a specific time, against which all dispute evaluation occurs.',
    ncipRef: 'NCIP-005',
  },
  coolingPeriod: {
    text: 'A mandatory delay (24-72 hours) preventing immediate escalation, allowing clarification or settlement without adversarial processes.',
    ncipRef: 'NCIP-005',
  },
  settlement: {
    text: 'The resolution of an Agreement or Dispute resulting in final obligations, compensation, or closure.',
    ncipRef: 'NCIP-001',
  },

  // Other Core Terms
  temporalFixity: {
    text: 'The binding of meaning to a specific point in time (T0), ensuring interpretations are evaluated against contemporaneous context.',
    ncipRef: 'NCIP-001',
  },
  mediator: {
    text: 'A human or authorized entity responsible for interpretation, dispute resolution, or enforcement within defined bounds.',
    ncipRef: 'NCIP-001',
  },

  // Form & Action Terms
  author: {
    text: 'The party creating this entry. Authors are bound by their entries and must provide Proof of Understanding for agreements.',
    ncipRef: 'NCIP-004',
  },
  content: {
    text: 'Natural language prose is the canonical substrate. Meaning is expressed in human language, not code.',
    ncipRef: 'NCIP-000',
  },
  validateFirst: {
    text: 'Check entry content against semantic drift thresholds before submission. Helps identify ambiguous or problematic entries.',
    ncipRef: 'NCIP-002',
  },
  mining: {
    text: 'Creates a new block containing pending entries. Blocks form the immutable chain of entries.',
    ncipRef: 'NCIP-001',
  },

  // Contract Types
  contractOffer: {
    text: 'An offer entry proposes terms that another party may accept to form an Agreement.',
    ncipRef: 'NCIP-001',
  },
  contractSeek: {
    text: 'A seek entry expresses a need or request that may be matched with compatible offers.',
    ncipRef: 'NCIP-001',
  },
  contractMatching: {
    text: 'Finds semantically compatible offers and seeks based on intent alignment and term compatibility.',
    ncipRef: 'NCIP-002',
  },

  // Search Types
  basicSearch: {
    text: 'Matches exact words and phrases in entry content. Use quotes for exact phrase matching.',
    ncipRef: 'NCIP-001',
  },
  semanticSearch: {
    text: "Uses AI to find entries with similar meaning. Works best with natural language queries describing what you're looking for.",
    ncipRef: 'NCIP-002',
  },

  // Chain Status
  chainValid: {
    text: 'The chain has passed integrity validation. All blocks are correctly linked and entries are unmodified.',
    ncipRef: 'NCIP-001',
  },
  chainInvalid: {
    text: 'Chain integrity check failed. This may indicate tampering or corruption. Dispute resolution may be required.',
    ncipRef: 'NCIP-005',
  },
  pendingEntries: {
    text: 'Entries awaiting inclusion in a block. These become permanent once mined into the chain.',
    ncipRef: 'NCIP-001',
  },

  // Block Details
  blockHash: {
    text: 'Cryptographic fingerprint of the block. Changes if any content is modified.',
    ncipRef: 'NCIP-001',
  },
  previousHash: {
    text: 'Links this block to its predecessor, forming the immutable chain.',
    ncipRef: 'NCIP-001',
  },
  nonce: {
    text: "Proof of work value that validates the block's creation.",
    ncipRef: 'NCIP-001',
  },

  // Parse Results
  contractParse: {
    text: 'Analyzes natural language contract text to extract parties, obligations, conditions, and timeline.',
    ncipRef: 'NCIP-004',
  },
  parties: {
    text: 'Identified participants in the agreement who have obligations or rights.',
    ncipRef: 'NCIP-001',
  },
  obligations: {
    text: 'Actions or commitments that parties must fulfill under the agreement.',
    ncipRef: 'NCIP-004',
  },
  conditions: {
    text: 'Requirements or circumstances that affect when obligations apply.',
    ncipRef: 'NCIP-004',
  },
};

export default ncipDefinitions;
