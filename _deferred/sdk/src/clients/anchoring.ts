/**
 * External Anchoring Client
 *
 * Provides external blockchain anchoring for NatLangChain entries.
 * Supports Ethereum mainnet/testnets and Arweave for permanent anchoring.
 */

import { HttpClient } from '../utils/client';

// ============================================================================
// Types
// ============================================================================

/** Supported anchor chains */
export type AnchorChain =
  | 'ethereum_mainnet'
  | 'ethereum_sepolia'
  | 'ethereum_goerli'
  | 'polygon_mainnet'
  | 'polygon_mumbai'
  | 'arbitrum_one'
  | 'arbitrum_sepolia'
  | 'optimism_mainnet'
  | 'optimism_sepolia'
  | 'base_mainnet'
  | 'base_sepolia'
  | 'arweave_mainnet';

/** Anchor batch status */
export type AnchorBatchStatus =
  | 'pending'
  | 'submitted'
  | 'confirming'
  | 'confirmed'
  | 'failed';

/** Request to queue an entry for anchoring */
export interface QueueEntryRequest {
  entry_hash: string;
  block_index?: number;
  entry_index?: number;
  priority?: number;
  metadata?: Record<string, unknown>;
}

/** Request to queue a block for anchoring */
export interface QueueBlockRequest {
  block_hash: string;
  block_index: number;
  entry_count: number;
}

/** Request to create an anchor */
export interface CreateAnchorRequest {
  chain?: AnchorChain;
  max_entries?: number;
}

/** Request to verify a proof */
export interface VerifyProofRequest {
  chain?: AnchorChain;
}

/** Queue result */
export interface QueueResult {
  status: 'queued' | 'already_queued';
  entry_hash: string;
  position?: number;
  queued_at?: string;
}

/** Queue status */
export interface QueueStatus {
  pending_entries: number;
  pending_blocks: number;
  total_queued: number;
  oldest_entry?: string;
  next_batch_estimated?: string;
}

/** Merkle proof for an entry */
export interface MerkleProof {
  entry_hash: string;
  merkle_root: string;
  proof_path: string[];
  proof_indices: number[];
  batch_id: string;
  chain: AnchorChain;
  tx_hash: string;
  block_number?: number;
  confirmed_at?: string;
}

/** Anchor batch details */
export interface AnchorBatch {
  batch_id: string;
  merkle_root: string;
  entry_count: number;
  chains: AnchorChain[];
  status: AnchorBatchStatus;
  created_at: string;
  submitted_at?: string;
  confirmed_at?: string;
  transactions: Record<AnchorChain, {
    tx_hash: string;
    block_number?: number;
    confirmations?: number;
    gas_used?: number;
  }>;
}

/** Anchor creation result */
export interface AnchorResult {
  batch_id: string;
  merkle_root: string;
  entry_count: number;
  chains: AnchorChain[];
  transactions: Record<AnchorChain, string>;
  status: AnchorBatchStatus;
}

/** Proof verification result */
export interface VerifyProofResult {
  verified: boolean;
  entry_hash: string;
  verifications: Array<{
    chain: AnchorChain;
    verified: boolean;
    merkle_root: string;
    tx_hash: string;
    block_number?: number;
    confirmations?: number;
    error?: string;
  }>;
  overall_confidence: 'high' | 'medium' | 'low' | 'none';
}

/** Legal proof document */
export interface LegalProof {
  entry_hash: string;
  generated_at: string;
  document_version: string;
  summary: {
    entry_exists: boolean;
    externally_anchored: boolean;
    anchor_count: number;
    oldest_anchor?: string;
    strongest_chain?: AnchorChain;
  };
  entry_details?: {
    block_index: number;
    entry_index: number;
    timestamp: string;
    author: string;
    content_hash: string;
  };
  anchor_proofs: MerkleProof[];
  verification_instructions: string;
  legal_notice: string;
}

/** Cost estimate per chain */
export interface ChainCostEstimate {
  chain: AnchorChain;
  estimated_cost_usd: number;
  estimated_cost_native: number;
  native_token: string;
  gas_price_gwei?: number;
  confirmations_expected: number;
  time_to_confirmation: string;
}

/** Cost estimation result */
export interface CostEstimation {
  entry_count: number;
  estimates: ChainCostEstimate[];
  recommended_chain: AnchorChain;
  total_minimum_cost_usd: number;
}

/** Anchoring statistics */
export interface AnchoringStatistics {
  total_anchored: number;
  total_batches: number;
  batches_by_status: Record<AnchorBatchStatus, number>;
  entries_by_chain: Record<AnchorChain, number>;
  total_gas_spent: Record<AnchorChain, number>;
  average_confirmation_time: Record<AnchorChain, number>;
  last_anchor_at?: string;
  queue: QueueStatus;
}

/** Anchor provider info */
export interface AnchorProvider {
  chain: AnchorChain;
  name: string;
  enabled: boolean;
  rpc_endpoint?: string;
  contract_address?: string;
  last_anchor?: string;
  total_anchored: number;
}

/** Anchoring event */
export interface AnchoringEvent {
  event_type: 'queued' | 'batched' | 'submitted' | 'confirmed' | 'failed';
  timestamp: string;
  batch_id?: string;
  entry_hash?: string;
  chain?: AnchorChain;
  tx_hash?: string;
  details?: Record<string, unknown>;
}

/** Events response */
export interface EventsResponse {
  count: number;
  events: AnchoringEvent[];
}

// ============================================================================
// Client
// ============================================================================

/**
 * Client for external blockchain anchoring operations
 *
 * @example
 * ```ts
 * // Queue an entry for anchoring
 * await client.anchoring.queueEntry({
 *   entry_hash: 'abc123...',
 *   priority: 1
 * });
 *
 * // Create anchor batch
 * const anchor = await client.anchoring.createAnchor({
 *   chain: 'ethereum_mainnet'
 * });
 *
 * // Get proof for an entry
 * const proof = await client.anchoring.getProof('abc123...');
 *
 * // Verify the proof
 * const verification = await client.anchoring.verifyProof('abc123...');
 *
 * // Generate legal proof document
 * const legalProof = await client.anchoring.getLegalProof('abc123...');
 * ```
 */
export class AnchoringClient {
  constructor(private readonly http: HttpClient) {}

  // ===========================================================================
  // Queue Management
  // ===========================================================================

  /**
   * Queue an entry for external anchoring
   *
   * @param request - Queue entry request
   * @returns Queue result with position
   */
  async queueEntry(request: QueueEntryRequest): Promise<QueueResult> {
    return this.http.post<QueueResult>('/anchoring/queue', request);
  }

  /**
   * Queue an entire block for anchoring
   *
   * @param request - Queue block request
   * @returns Queue result
   */
  async queueBlock(request: QueueBlockRequest): Promise<QueueResult> {
    return this.http.post<QueueResult>('/anchoring/queue/block', request);
  }

  /**
   * Get current anchor queue status
   *
   * @returns Queue status with pending entries
   */
  async getQueueStatus(): Promise<QueueStatus> {
    return this.http.get<QueueStatus>('/anchoring/queue/status');
  }

  // ===========================================================================
  // Anchor Operations
  // ===========================================================================

  /**
   * Create and submit an anchor batch
   *
   * @param request - Optional anchor configuration
   * @returns Anchor result with batch details
   */
  async createAnchor(request?: CreateAnchorRequest): Promise<AnchorResult> {
    return this.http.post<AnchorResult>('/anchoring/anchor', request || {});
  }

  /**
   * Confirm an anchor batch is confirmed on-chain
   *
   * @param batchId - The batch ID to confirm
   * @returns Confirmation result
   */
  async confirmAnchor(batchId: string): Promise<AnchorBatch> {
    return this.http.post<AnchorBatch>(`/anchoring/batch/${batchId}/confirm`, {});
  }

  /**
   * Get anchor batch details
   *
   * @param batchId - The batch ID
   * @returns Batch details
   */
  async getBatch(batchId: string): Promise<AnchorBatch> {
    return this.http.get<AnchorBatch>(`/anchoring/batch/${batchId}`);
  }

  // ===========================================================================
  // Proof Operations
  // ===========================================================================

  /**
   * Get anchor proofs for an entry
   *
   * @param entryHash - The entry hash
   * @returns Proofs for the entry
   */
  async getProof(entryHash: string): Promise<{ entry_hash: string; proofs: MerkleProof[] }> {
    return this.http.get<{ entry_hash: string; proofs: MerkleProof[] }>(
      `/anchoring/proof/${entryHash}`
    );
  }

  /**
   * Verify anchor proofs for an entry
   *
   * @param entryHash - The entry hash
   * @param request - Optional verification options
   * @returns Verification result
   */
  async verifyProof(
    entryHash: string,
    request?: VerifyProofRequest
  ): Promise<VerifyProofResult> {
    return this.http.post<VerifyProofResult>(
      `/anchoring/proof/${entryHash}/verify`,
      request || {}
    );
  }

  /**
   * Generate legal proof document for an entry
   *
   * @param entryHash - The entry hash
   * @returns Comprehensive legal proof document
   */
  async getLegalProof(entryHash: string): Promise<LegalProof> {
    return this.http.get<LegalProof>(`/anchoring/proof/${entryHash}/legal`);
  }

  // ===========================================================================
  // Cost Estimation
  // ===========================================================================

  /**
   * Estimate anchoring costs
   *
   * @param entryCount - Number of entries (uses pending count if omitted)
   * @returns Cost estimates per provider
   */
  async estimateCosts(entryCount?: number): Promise<CostEstimation> {
    const params = entryCount !== undefined ? `?entries=${entryCount}` : '';
    return this.http.get<CostEstimation>(`/anchoring/estimate${params}`);
  }

  // ===========================================================================
  // Statistics and Configuration
  // ===========================================================================

  /**
   * Get anchoring statistics
   *
   * @returns Comprehensive statistics
   */
  async getStatistics(): Promise<AnchoringStatistics> {
    return this.http.get<AnchoringStatistics>('/anchoring/statistics');
  }

  /**
   * Get configured anchor providers
   *
   * @returns List of providers
   */
  async getProviders(): Promise<{ providers: AnchorProvider[] }> {
    return this.http.get<{ providers: AnchorProvider[] }>('/anchoring/providers');
  }

  /**
   * Get all supported anchor chains
   *
   * @returns List of supported chains
   */
  async getSupportedChains(): Promise<{ chains: AnchorChain[] }> {
    return this.http.get<{ chains: AnchorChain[] }>('/anchoring/chains');
  }

  // ===========================================================================
  // Events
  // ===========================================================================

  /**
   * Get anchoring event log
   *
   * @param options - Optional filter options
   * @returns List of events
   */
  async getEvents(options?: {
    limit?: number;
    event_type?: AnchoringEvent['event_type'];
  }): Promise<EventsResponse> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    if (options?.event_type) {
      params.set('event_type', options.event_type);
    }
    const query = params.toString();
    return this.http.get<EventsResponse>(`/anchoring/events${query ? `?${query}` : ''}`);
  }
}
