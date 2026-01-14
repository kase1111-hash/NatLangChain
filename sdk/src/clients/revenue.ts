/**
 * Revenue Sharing Client
 *
 * Programmable royalties for derivative intent chains.
 * Enables automatic revenue distribution through derivative relationships.
 * Inspired by Story Protocol's IP royalty system.
 */

import { HttpClient } from '../utils/client';

// ============================================================================
// Types
// ============================================================================

/** Types of royalty configurations */
export type RoyaltyType = 'fixed' | 'tiered' | 'split' | 'none';

/** Types of revenue-generating events */
export type RevenueEventType =
  | 'derivative_created'
  | 'contract_executed'
  | 'license_purchased'
  | 'tip'
  | 'bounty'
  | 'marketplace_sale'
  | 'custom';

/** Status of royalty payments */
export type PaymentStatus =
  | 'pending'
  | 'distributed'
  | 'claimed'
  | 'expired'
  | 'failed';

/** Status of revenue claims */
export type ClaimStatus = 'available' | 'claimed' | 'expired' | 'pending';

/** Entry reference */
export interface EntryRef {
  block_index: number;
  entry_index: number;
}

/** Royalty configuration for an entry/contract */
export interface RoyaltyConfig {
  config_id: string;
  entry_ref: EntryRef;
  owner: string;
  royalty_type: RoyaltyType;
  base_rate: string;
  tiered_rates: Record<string, string>;
  split_recipients: Record<string, string>;
  chain_propagation: boolean;
  max_depth: number;
  depth_decay: string;
  min_payment: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

/** A revenue-generating event */
export interface RevenueEvent {
  event_id: string;
  event_type: RevenueEventType;
  source_entry_ref: EntryRef;
  amount: string;
  currency: string;
  payer?: string;
  metadata: Record<string, unknown>;
  derivative_type?: string;
  created_at: string;
  processed_at?: string;
}

/** A calculated royalty payment */
export interface RoyaltyPayment {
  payment_id: string;
  event_id: string;
  recipient: string;
  entry_ref: EntryRef;
  amount: string;
  currency: string;
  rate_applied: string;
  depth: number;
  chain_path: EntryRef[];
  status: PaymentStatus;
  created_at: string;
  distributed_at?: string;
  claimed_at?: string;
  expires_at: string;
}

/** Revenue pool for a recipient */
export interface RevenuePool {
  pool_id: string;
  recipient: string;
  balances: Record<string, string>;
  total_earned: Record<string, string>;
  total_claimed: Record<string, string>;
  pending_payment_count: number;
  created_at: string;
  last_claim_at?: string;
}

/** A claim request */
export interface Claim {
  claim_id: string;
  recipient: string;
  amount: string;
  currency: string;
  status: ClaimStatus;
  destination_address?: string;
  created_at: string;
  processed_at?: string;
  tx_ref?: string;
}

/** Royalty distribution estimate */
export interface RoyaltyDistribution {
  entry_ref: EntryRef;
  recipient: string;
  rate: string;
  depth: number;
  estimated_amount: string;
}

/** Revenue event with royalty info */
export interface RevenueEventWithRoyalties extends RevenueEvent {
  royalties: {
    payment_count: number;
    total_distributed: string;
    remaining: string;
    payments: RoyaltyPayment[];
  };
}

/** Request to configure royalties */
export interface ConfigureRoyaltiesRequest {
  block_index: number;
  entry_index: number;
  owner: string;
  royalty_type?: RoyaltyType;
  base_rate?: string;
  tiered_rates?: Record<string, string>;
  split_recipients?: Record<string, string>;
  chain_propagation?: boolean;
  max_depth?: number;
  depth_decay?: string;
  min_payment?: string;
  metadata?: Record<string, unknown>;
}

/** Request to update royalty config */
export interface UpdateRoyaltyConfigRequest {
  owner: string;
  base_rate?: string;
  tiered_rates?: Record<string, string>;
  split_recipients?: Record<string, string>;
  chain_propagation?: boolean;
  max_depth?: number;
  is_active?: boolean;
}

/** Request to record a revenue event */
export interface RecordRevenueEventRequest {
  block_index: number;
  entry_index: number;
  event_type: RevenueEventType;
  amount: string;
  currency?: string;
  payer?: string;
  derivative_type?: string;
  metadata?: Record<string, unknown>;
}

/** Request to claim revenue */
export interface ClaimRevenueRequest {
  recipient: string;
  amount?: string;
  currency?: string;
  destination_address?: string;
}

/** Request to estimate royalties */
export interface EstimateRoyaltiesRequest {
  block_index: number;
  entry_index: number;
  amount: string;
  derivative_type?: string;
}

/** Response listing revenue events */
export interface RevenueEventsResponse {
  count: number;
  events: RevenueEvent[];
}

/** Response listing payments */
export interface PaymentsResponse {
  count: number;
  payments: RoyaltyPayment[];
}

/** Response listing claims */
export interface ClaimsResponse {
  count: number;
  claims: Claim[];
}

/** Balance response */
export interface BalanceResponse {
  recipient: string;
  currency: string;
  available_balance: string;
}

/** Entry earnings response */
export interface EntryEarningsResponse {
  entry_ref: EntryRef;
  earnings: Record<string, string>;
  payment_count: number;
}

/** Chain revenue response */
export interface ChainRevenueResponse {
  entry_ref: EntryRef;
  total_revenue: Record<string, string>;
  direct_revenue: Record<string, string>;
  derivative_revenue: Record<string, string>;
}

/** Royalty estimate response */
export interface RoyaltyEstimateResponse {
  input_amount: string;
  total_royalties: string;
  remaining_after_royalties: string;
  distribution_count: number;
  distributions: RoyaltyDistribution[];
}

/** Revenue sharing statistics */
export interface RevenueStatistics {
  royalty_configs: {
    total: number;
    active: number;
  };
  revenue_events: {
    total: number;
    by_type: Record<string, number>;
  };
  payments: {
    total: number;
    by_status: Record<string, number>;
    total_distributed: Record<string, string>;
  };
  pools: {
    total: number;
    total_balances: Record<string, string>;
  };
  claims: {
    total: number;
    claimed: number;
  };
}

/** Audit event */
export interface AuditEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

/** Audit events response */
export interface AuditEventsResponse {
  count: number;
  events: AuditEvent[];
}

// ============================================================================
// Client
// ============================================================================

/**
 * Client for revenue sharing operations
 *
 * @example
 * ```ts
 * // Configure royalties for an entry
 * const config = await client.revenue.configureRoyalties({
 *   block_index: 1,
 *   entry_index: 0,
 *   owner: 'did:nlc:author...',
 *   royalty_type: 'fixed',
 *   base_rate: '5.0',  // 5%
 *   chain_propagation: true
 * });
 *
 * // Record a revenue event (e.g., derivative created)
 * const event = await client.revenue.recordRevenueEvent({
 *   block_index: 2,
 *   entry_index: 0,
 *   event_type: 'derivative_created',
 *   amount: '100.00',
 *   derivative_type: 'amendment'
 * });
 * // Royalties are automatically calculated and distributed!
 *
 * // Check your earnings
 * const balance = await client.revenue.getBalance('did:nlc:author...');
 *
 * // Claim accumulated revenue
 * const claim = await client.revenue.claimRevenue({
 *   recipient: 'did:nlc:author...',
 *   amount: '50.00'
 * });
 * ```
 */
export class RevenueClient {
  constructor(private readonly http: HttpClient) {}

  // ===========================================================================
  // Royalty Configuration
  // ===========================================================================

  /**
   * Configure royalties for an entry/contract
   *
   * @param request - Configuration options
   * @returns Royalty configuration
   */
  async configureRoyalties(request: ConfigureRoyaltiesRequest): Promise<RoyaltyConfig> {
    return this.http.post<RoyaltyConfig>('/revenue/royalties', request);
  }

  /**
   * Get royalty configuration for an entry
   *
   * @param blockIndex - Block index
   * @param entryIndex - Entry index
   * @returns Royalty configuration if exists
   */
  async getRoyaltyConfig(blockIndex: number, entryIndex: number): Promise<RoyaltyConfig> {
    return this.http.get<RoyaltyConfig>(`/revenue/royalties/${blockIndex}/${entryIndex}`);
  }

  /**
   * Update royalty configuration
   *
   * @param blockIndex - Block index
   * @param entryIndex - Entry index
   * @param request - Update options
   * @returns Updated configuration
   */
  async updateRoyaltyConfig(
    blockIndex: number,
    entryIndex: number,
    request: UpdateRoyaltyConfigRequest
  ): Promise<RoyaltyConfig> {
    return this.http.patch<RoyaltyConfig>(
      `/revenue/royalties/${blockIndex}/${entryIndex}`,
      request
    );
  }

  /**
   * Disable royalties for an entry
   *
   * @param blockIndex - Block index
   * @param entryIndex - Entry index
   * @param owner - Owner DID for authorization
   * @returns Disable result
   */
  async disableRoyalties(
    blockIndex: number,
    entryIndex: number,
    owner: string
  ): Promise<{ config_id: string; disabled: boolean }> {
    return this.http.post<{ config_id: string; disabled: boolean }>(
      `/revenue/royalties/${blockIndex}/${entryIndex}/disable`,
      { owner }
    );
  }

  // ===========================================================================
  // Revenue Events
  // ===========================================================================

  /**
   * Record a revenue-generating event
   *
   * @param request - Event details
   * @returns Event info with calculated royalties
   */
  async recordRevenueEvent(
    request: RecordRevenueEventRequest
  ): Promise<RevenueEventWithRoyalties> {
    return this.http.post<RevenueEventWithRoyalties>('/revenue/events', request);
  }

  /**
   * Get a revenue event by ID
   *
   * @param eventId - The event ID
   * @returns Event info
   */
  async getRevenueEvent(eventId: string): Promise<RevenueEvent> {
    return this.http.get<RevenueEvent>(`/revenue/events/${encodeURIComponent(eventId)}`);
  }

  /**
   * List revenue events
   *
   * @param options - Filter options
   * @returns List of events
   */
  async listRevenueEvents(options?: {
    block_index?: number;
    entry_index?: number;
    event_type?: RevenueEventType;
    limit?: number;
  }): Promise<RevenueEventsResponse> {
    const params = new URLSearchParams();
    if (options?.block_index !== undefined) {
      params.set('block_index', String(options.block_index));
    }
    if (options?.entry_index !== undefined) {
      params.set('entry_index', String(options.entry_index));
    }
    if (options?.event_type) {
      params.set('event_type', options.event_type);
    }
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    const query = params.toString();
    return this.http.get<RevenueEventsResponse>(`/revenue/events${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Revenue Pool & Claims
  // ===========================================================================

  /**
   * Get revenue pool for a recipient
   *
   * @param recipient - Recipient DID
   * @returns Pool info with balances
   */
  async getPool(recipient: string): Promise<RevenuePool> {
    return this.http.get<RevenuePool>(`/revenue/pools/${encodeURIComponent(recipient)}`);
  }

  /**
   * Get available balance for a recipient
   *
   * @param recipient - Recipient DID
   * @param currency - Currency type (default: NLC)
   * @returns Available balance
   */
  async getBalance(recipient: string, currency: string = 'NLC'): Promise<BalanceResponse> {
    return this.http.get<BalanceResponse>(
      `/revenue/balance/${encodeURIComponent(recipient)}?currency=${encodeURIComponent(currency)}`
    );
  }

  /**
   * Claim accumulated revenue
   *
   * @param request - Claim options
   * @returns Claim info
   */
  async claimRevenue(request: ClaimRevenueRequest): Promise<Claim> {
    return this.http.post<Claim>('/revenue/claims', request);
  }

  /**
   * Get a claim by ID
   *
   * @param claimId - The claim ID
   * @returns Claim info
   */
  async getClaim(claimId: string): Promise<Claim> {
    return this.http.get<Claim>(`/revenue/claims/${encodeURIComponent(claimId)}`);
  }

  /**
   * List claims
   *
   * @param options - Filter options
   * @returns List of claims
   */
  async listClaims(options?: {
    recipient?: string;
    status?: ClaimStatus;
    limit?: number;
  }): Promise<ClaimsResponse> {
    const params = new URLSearchParams();
    if (options?.recipient) {
      params.set('recipient', options.recipient);
    }
    if (options?.status) {
      params.set('status', options.status);
    }
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    const query = params.toString();
    return this.http.get<ClaimsResponse>(`/revenue/claims${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Payments
  // ===========================================================================

  /**
   * Get a payment by ID
   *
   * @param paymentId - The payment ID
   * @returns Payment info
   */
  async getPayment(paymentId: string): Promise<RoyaltyPayment> {
    return this.http.get<RoyaltyPayment>(
      `/revenue/payments/${encodeURIComponent(paymentId)}`
    );
  }

  /**
   * List payments
   *
   * @param options - Filter options
   * @returns List of payments
   */
  async listPayments(options?: {
    recipient?: string;
    event_id?: string;
    status?: PaymentStatus;
    limit?: number;
  }): Promise<PaymentsResponse> {
    const params = new URLSearchParams();
    if (options?.recipient) {
      params.set('recipient', options.recipient);
    }
    if (options?.event_id) {
      params.set('event_id', options.event_id);
    }
    if (options?.status) {
      params.set('status', options.status);
    }
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    const query = params.toString();
    return this.http.get<PaymentsResponse>(`/revenue/payments${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Analytics
  // ===========================================================================

  /**
   * Get total earnings for an entry
   *
   * @param blockIndex - Block index
   * @param entryIndex - Entry index
   * @returns Entry earnings summary
   */
  async getEntryEarnings(blockIndex: number, entryIndex: number): Promise<EntryEarningsResponse> {
    return this.http.get<EntryEarningsResponse>(`/revenue/earnings/${blockIndex}/${entryIndex}`);
  }

  /**
   * Get total revenue generated by an entry and its derivatives
   *
   * @param blockIndex - Block index
   * @param entryIndex - Entry index
   * @returns Chain revenue breakdown
   */
  async getChainRevenue(blockIndex: number, entryIndex: number): Promise<ChainRevenueResponse> {
    return this.http.get<ChainRevenueResponse>(`/revenue/chain/${blockIndex}/${entryIndex}`);
  }

  /**
   * Estimate royalty distribution for a potential revenue event
   *
   * @param request - Estimation parameters
   * @returns Estimated distribution breakdown
   */
  async estimateRoyalties(request: EstimateRoyaltiesRequest): Promise<RoyaltyEstimateResponse> {
    return this.http.post<RoyaltyEstimateResponse>('/revenue/estimate', request);
  }

  // ===========================================================================
  // Statistics
  // ===========================================================================

  /**
   * Get revenue sharing statistics
   *
   * @returns Comprehensive statistics
   */
  async getStatistics(): Promise<RevenueStatistics> {
    return this.http.get<RevenueStatistics>('/revenue/statistics');
  }

  /**
   * Get audit trail events
   *
   * @param options - Filter options
   * @returns List of audit events
   */
  async getAuditEvents(options?: {
    limit?: number;
    event_type?: string;
  }): Promise<AuditEventsResponse> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    if (options?.event_type) {
      params.set('event_type', options.event_type);
    }
    const query = params.toString();
    return this.http.get<AuditEventsResponse>(`/revenue/audit${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Supported Types
  // ===========================================================================

  /**
   * Get supported royalty types
   *
   * @returns List of supported royalty types
   */
  async getRoyaltyTypes(): Promise<{ types: RoyaltyType[] }> {
    return this.http.get<{ types: RoyaltyType[] }>('/revenue/types/royalty');
  }

  /**
   * Get supported revenue event types
   *
   * @returns List of supported event types
   */
  async getEventTypes(): Promise<{ types: RevenueEventType[] }> {
    return this.http.get<{ types: RevenueEventType[] }>('/revenue/types/events');
  }

  /**
   * Get supported payment statuses
   *
   * @returns List of supported payment statuses
   */
  async getPaymentStatuses(): Promise<{ statuses: PaymentStatus[] }> {
    return this.http.get<{ statuses: PaymentStatus[] }>('/revenue/types/payment_status');
  }

  /**
   * Get supported claim statuses
   *
   * @returns List of supported claim statuses
   */
  async getClaimStatuses(): Promise<{ statuses: ClaimStatus[] }> {
    return this.http.get<{ statuses: ClaimStatus[] }>('/revenue/types/claim_status');
  }
}
