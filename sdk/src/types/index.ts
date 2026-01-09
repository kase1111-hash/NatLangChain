/**
 * NatLangChain SDK Type Definitions
 *
 * Complete TypeScript types for all API responses and request payloads.
 */

// ============================================================================
// Core Types
// ============================================================================

/** Parent reference for derivative entries */
export interface EntryParentRef {
  block_index: number;
  entry_index: number;
  relationship?: string;
}

/** Natural language entry - the fundamental unit of NatLangChain */
export interface Entry {
  content: string;
  author: string;
  intent: string;
  timestamp: string;
  metadata: Record<string, unknown>;
  validation_status: ValidationStatus;
  validation_paraphrases: string[];
  /** Parent references if this is a derivative entry */
  parent_refs?: EntryParentRef[];
  /** Type of derivation if this is a derivative entry */
  derivative_type?: 'amendment' | 'extension' | 'response' | 'revision' | 'reference' | 'fulfillment';
}

/** Block containing entries */
export interface Block {
  index: number;
  timestamp: string;
  entries: Entry[];
  previous_hash: string;
  nonce: number;
  hash: string;
}

/** Validation status for entries */
export type ValidationStatus =
  | 'pending'
  | 'valid'
  | 'invalid'
  | 'accepted'
  | 'rejected'
  | 'needs_revision';

/** Validation mode options */
export type ValidationMode = 'standard' | 'dialectic' | 'multi' | 'none';

// ============================================================================
// Request Types
// ============================================================================

/** Request to create a new entry */
export interface CreateEntryRequest {
  content: string;
  author: string;
  intent: string;
  metadata?: Record<string, unknown>;
  validate?: boolean;
  auto_mine?: boolean;
  validation_mode?: ValidationMode;
  multi_validator?: boolean;
  /** Parent references if creating a derivative entry */
  parent_refs?: EntryParentRef[];
  /** Type of derivation if creating a derivative entry */
  derivative_type?: 'amendment' | 'extension' | 'response' | 'revision' | 'reference' | 'fulfillment';
}

/** Request to validate an entry without submitting */
export interface ValidateEntryRequest {
  content: string;
  author: string;
  intent: string;
  multi_validator?: boolean;
}

/** Request to mine pending entries */
export interface MineRequest {
  difficulty?: number;
}

/** Semantic search request */
export interface SemanticSearchRequest {
  query: string;
  top_k?: number;
  min_score?: number;
  field?: 'content' | 'intent' | 'both';
}

/** Find similar entries request */
export interface FindSimilarRequest {
  content: string;
  top_k?: number;
  exclude_exact?: boolean;
}

/** Drift check request */
export interface DriftCheckRequest {
  on_chain_intent: string;
  execution_log: string;
}

/** Dialectic validation request */
export interface DialecticValidateRequest {
  content: string;
  author: string;
  intent: string;
}

/** Oracle verification request */
export interface OracleVerifyRequest {
  event_description: string;
  claimed_outcome: string;
  evidence?: Record<string, unknown>;
  validators?: string[];
}

/** Contract parse request */
export interface ContractParseRequest {
  content: string;
}

/** Contract post request */
export interface ContractPostRequest {
  content: string;
  author: string;
  intent: string;
  contract_type?: 'offer' | 'seek';
  terms?: Record<string, unknown>;
  auto_mine?: boolean;
}

/** Contract match request */
export interface ContractMatchRequest {
  pending_entries?: Entry[];
  miner_id?: string;
}

/** Contract respond request */
export interface ContractRespondRequest {
  to_block: number;
  to_entry: number;
  response_content: string;
  author: string;
  response_type?: 'accept' | 'counter' | 'reject';
  counter_terms?: Record<string, unknown>;
}

/** Dispute file request */
export interface DisputeFileRequest {
  complainant: string;
  respondent: string;
  description: string;
  related_entries?: Array<{ block: number; entry: number }>;
  evidence?: Record<string, unknown>;
}

/** Dispute evidence request */
export interface DisputeEvidenceRequest {
  submitter: string;
  evidence_type: string;
  content: string;
  metadata?: Record<string, unknown>;
}

/** Settlement propose request */
export interface SettlementProposeRequest {
  intent_a: string;
  intent_b: string;
  terms: string;
  fee?: number;
}

/** Settlement accept request */
export interface SettlementAcceptRequest {
  party: 'A' | 'B';
  party_id: string;
}

// ============================================================================
// Response Types
// ============================================================================

/** Health check response */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  service: string;
  llm_validation_available: boolean;
  blocks: number;
  pending_entries: number;
}

/** Chain response */
export interface ChainResponse {
  length: number;
  chain: Block[];
  valid: boolean;
}

/** Entry creation response */
export interface CreateEntryResponse {
  status: 'success';
  entry: Entry;
  validation: ValidationResult | null;
  mined_block?: {
    index: number;
    hash: string;
  };
}

/** Validation result */
export interface ValidationResult {
  validation_mode: ValidationMode;
  overall_decision: string;
  llm_validation?: {
    validation?: {
      paraphrase?: string;
      is_valid?: boolean;
      confidence?: number;
    };
    validations?: Array<{
      model?: string;
      is_valid?: boolean;
      confidence?: number;
    }>;
    paraphrases?: string[];
  };
  dialectic_validation?: DialecticResult;
  note?: string;
}

/** Dialectic validation result */
export interface DialecticResult {
  decision: string;
  skeptic_analysis: {
    concerns: string[];
    risk_level: string;
  };
  facilitator_analysis: {
    merits: string[];
    recommendation: string;
  };
  synthesis: string;
}

/** Mine response */
export interface MineResponse {
  status: 'success';
  block: {
    index: number;
    timestamp: string;
    entries_count: number;
    hash: string;
    previous_hash: string;
  };
}

/** Block response */
export interface BlockResponse extends Block {}

/** Latest block response */
export interface LatestBlockResponse {
  block: Block;
  chain_length: number;
  pending_entries: number;
}

/** Entries by author response */
export interface EntriesByAuthorResponse {
  author: string;
  count: number;
  entries: Entry[];
}

/** Search entries response */
export interface SearchEntriesResponse {
  query: string;
  count: number;
  entries: Entry[];
}

/** Pending entries response */
export interface PendingEntriesResponse {
  count: number;
  entries: Entry[];
}

/** Stats response */
export interface StatsResponse {
  blocks: number;
  pending_entries: number;
  total_entries: number;
  unique_authors: number;
  chain_valid: boolean;
  features: {
    llm_validation: boolean;
    semantic_search: boolean;
    drift_detection: boolean;
    dialectic_consensus: boolean;
    multi_model_consensus: boolean;
    contract_management: boolean;
    dispute_management: boolean;
    temporal_fixity: boolean;
    semantic_oracles: boolean;
    escalation_forks: boolean;
    observance_burns: boolean;
    anti_harassment: boolean;
    treasury: boolean;
    fido2_auth: boolean;
    zk_privacy: boolean;
    negotiation: boolean;
    market_pricing: boolean;
    mobile_deployment: boolean;
  };
}

/** Chain validation response */
export interface ValidateChainResponse {
  valid: boolean;
  blocks: number;
  pending_entries: number;
}

/** Semantic search response */
export interface SemanticSearchResponse {
  query: string;
  field: string;
  count: number;
  results: Array<{
    entry: Entry;
    score: number;
    block_index: number;
    entry_index: number;
  }>;
}

/** Find similar response */
export interface FindSimilarResponse {
  content: string;
  count: number;
  similar_entries: Array<{
    entry: Entry;
    score: number;
    block_index: number;
    entry_index: number;
  }>;
}

/** Drift check response */
export interface DriftCheckResponse {
  aligned: boolean;
  drift_score: number;
  analysis: string;
  recommendations: string[];
}

/** Entry drift response */
export interface EntryDriftResponse extends DriftCheckResponse {
  entry_info: {
    block_index: number;
    entry_index: number;
    author: string;
    intent: string;
  };
}

/** Oracle verify response */
export interface OracleVerifyResponse {
  verified: boolean;
  confidence: number;
  analysis: string;
  evidence_assessment: Record<string, unknown>;
}

/** Contract parse response */
export interface ContractParseResponse {
  status: 'success';
  parsed: {
    contract_type: string;
    terms: Record<string, unknown>;
    parties: string[];
    conditions: string[];
    is_contract: boolean;
  };
}

/** Contract match response */
export interface ContractMatchResponse {
  status: 'success';
  matches: Array<{
    offer: Entry;
    seek: Entry;
    compatibility_score: number;
    proposed_terms: Record<string, unknown>;
  }>;
  count: number;
}

/** Contract post response */
export interface ContractPostResponse {
  status: 'success';
  entry: Entry;
  contract_metadata: Record<string, unknown>;
  mined_block?: {
    index: number;
    hash: string;
  };
}

/** Contract list response */
export interface ContractListResponse {
  count: number;
  contracts: Array<{
    block_index: number;
    block_hash: string;
    entry: Entry;
  }>;
}

/** Contract respond response */
export interface ContractRespondResponse {
  status: 'success';
  response: Entry;
  mediation: {
    recommendation: string;
    suggested_compromise: Record<string, unknown>;
    negotiation_round: number;
  } | null;
}

/** Dispute response */
export interface Dispute {
  id: string;
  complainant: string;
  respondent: string;
  description: string;
  status: 'open' | 'evidence_collection' | 'escalated' | 'resolved';
  created_at: string;
  evidence: Array<{
    submitter: string;
    type: string;
    content: string;
    timestamp: string;
  }>;
  related_entries: Array<{ block: number; entry: number }>;
  resolution?: {
    outcome: string;
    resolved_by: string;
    resolved_at: string;
  };
}

/** Dispute file response */
export interface DisputeFileResponse {
  status: 'success';
  dispute: Dispute;
}

/** Dispute list response */
export interface DisputeListResponse {
  count: number;
  disputes: Dispute[];
}

/** Settlement response */
export interface Settlement {
  id: string;
  intent_a: string;
  intent_b: string;
  terms: string;
  status: 'proposed' | 'party_a_accepted' | 'party_b_accepted' | 'both_accepted' | 'finalized' | 'rejected';
  created_at: string;
  fee: number;
}

/** Settlement propose response */
export interface SettlementProposeResponse {
  status: 'success';
  settlement: Settlement;
}

/** Settlement status response */
export interface SettlementStatusResponse {
  settlement: Settlement;
  accepted_by: string[];
}

// ============================================================================
// Permanence Endowment Types (Arweave-inspired)
// ============================================================================

/** Storage cost projection over time */
export interface StorageCostProjection {
  entry_size_bytes: number;
  current_annual_cost: number;
  total_lifetime_cost: number;
  required_endowment: number;
  years_projected: number;
  cost_by_decade: Record<number, number>;
}

/** Fee calculation result for permanence */
export interface PermanenceFeeCalculation {
  entry_size_bytes: number;
  total_fee: number;
  fee_breakdown: {
    endowment_allocation: number;
    immediate_storage: number;
  };
  storage_projection: StorageCostProjection;
  yield_assumptions: {
    current_rate: number;
    strategy: string;
  };
  sustainability: {
    projected_years: number;
    safety_multiplier: number;
  };
}

/** Permanence guarantee for an entry */
export interface PermanenceGuarantee {
  guarantee_id: string;
  entry_hash: string;
  entry_size_bytes: number;
  fee_paid: number;
  endowment_allocated: number;
  immediate_storage_paid: number;
  status: 'pending' | 'guaranteed' | 'partial' | 'expired' | 'revoked';
  created_at: string;
  expires_at: string | null;
  yield_strategy: string;
  projected_sustainability_years: number;
  guarantee_hash: string;
}

/** Endowment pool status */
export interface EndowmentPoolStatus {
  principal: number;
  accrued_yield: number;
  total_funds: number;
  total_deposits: number;
  total_payouts: number;
  total_yield_generated: number;
  entries_guaranteed: number;
  bytes_guaranteed: number;
  yield_rate: number;
  annual_yield_projection: number;
  annual_storage_cost: number;
  sustainability_ratio: number;
  health_status: 'excellent' | 'healthy' | 'stable' | 'warning' | 'critical';
  last_yield_accrual: string | null;
  last_storage_payout: string | null;
}

/** Endowment statistics */
export interface EndowmentStatistics {
  pool: EndowmentPoolStatus;
  guarantees: {
    total: number;
    by_status: Record<string, number>;
    total_entries: number;
    total_bytes: number;
    average_entry_size: number;
  };
  yield_history: {
    total_accruals: number;
    total_generated: number;
    average_rate: number;
  };
  payouts: {
    total_count: number;
    total_amount: number;
    from_yield: number;
    from_principal: number;
  };
  events_count: number;
}

/** Year projection for sustainability report */
export interface YearProjection {
  year: number;
  projected_principal: number;
  annual_yield: number;
  annual_cost: number;
  net_position: number;
  sustainable: boolean;
}

/** Sustainability report */
export interface SustainabilityReport {
  current_status: EndowmentPoolStatus;
  yield_assumptions: {
    current_rate: number;
    strategy: string;
    min_assumed: number;
  };
  cost_assumptions: {
    current_cost_per_gb: number;
    annual_decline_rate: number;
    cost_floor: number;
  };
  ten_year_projection: YearProjection[];
  sustainability_summary: {
    years_projected_sustainable: number;
    is_perpetually_sustainable: boolean;
    confidence: 'high' | 'medium' | 'low';
  };
  recommendations: string[];
}

/** Yield accrual result */
export interface YieldAccrualResult {
  status: string;
  accrual_id?: string;
  days_elapsed?: number;
  yield_amount?: number;
  yield_rate?: number;
  new_principal?: number;
  total_yield_generated?: number;
}

/** Storage payout result */
export interface StoragePayoutResult {
  status: string;
  payout_id: string;
  amount: number;
  storage_provider: string;
  entries_covered: number;
  bytes_stored: number;
  funded_from: 'yield' | 'principal';
  remaining_yield: number;
  remaining_principal: number;
}

// ============================================================================
// SDK Configuration
// ============================================================================

/** SDK client configuration */
export interface NatLangChainConfig {
  /** Base URL of the NatLangChain API */
  endpoint: string;
  /** API key for authenticated requests */
  apiKey?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Custom headers to include with every request */
  headers?: Record<string, string>;
  /** Retry configuration */
  retry?: {
    /** Number of retry attempts (default: 3) */
    attempts?: number;
    /** Base delay between retries in ms (default: 1000) */
    delay?: number;
    /** Maximum delay between retries in ms (default: 10000) */
    maxDelay?: number;
  };
}

/** API error response */
export interface ApiError {
  error: string;
  reason?: string;
  details?: string;
  required?: string[];
  valid_range?: string;
}
