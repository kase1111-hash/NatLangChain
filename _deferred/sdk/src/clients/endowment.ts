/**
 * NatLangChain SDK - Endowment Client
 *
 * Client for interacting with the Permanence Endowment system.
 * Implements Arweave-inspired "pay once, store forever" functionality.
 */

import { HttpClient } from '../utils/client';
import {
  PermanenceFeeCalculation,
  PermanenceGuarantee,
  EndowmentPoolStatus,
  EndowmentStatistics,
  SustainabilityReport,
  YieldAccrualResult,
  StoragePayoutResult,
} from '../types';

/**
 * Client for permanence endowment operations.
 *
 * The Permanence Endowment provides sustainable long-term storage funding:
 * - One-time fee for permanent storage
 * - Endowment generates yield to pay ongoing costs
 * - Storage costs decline over time (Moore's Law)
 * - Yield exceeds cost decline = sustainable permanence
 */
export class EndowmentClient {
  constructor(private client: HttpClient) {}

  // ===========================================================================
  // Fee Calculation
  // ===========================================================================

  /**
   * Calculate the permanence fee for an entry.
   *
   * @param entrySizeBytes - Size of entry in bytes
   * @returns Fee breakdown with endowment allocation and projections
   */
  async calculateFee(entrySizeBytes: number): Promise<PermanenceFeeCalculation> {
    return this.client.post<PermanenceFeeCalculation>('/endowment/calculate-fee', {
      entry_size_bytes: entrySizeBytes,
    });
  }

  /**
   * Quick fee estimate for common entry sizes.
   *
   * @param size - Entry size in bytes (default: 2048)
   * @returns Simplified fee estimate
   */
  async estimateFee(size: number = 2048): Promise<{
    entry_size_bytes: number;
    permanence_fee: number;
    currency: string;
    guarantee_years: number;
  }> {
    return this.client.get('/endowment/estimate', { size: size.toString() });
  }

  // ===========================================================================
  // Guarantee Management
  // ===========================================================================

  /**
   * Create a permanence guarantee for an entry.
   *
   * @param entryHash - Hash of the entry
   * @param entrySizeBytes - Size of entry in bytes
   * @param feeAmount - Amount paid for permanence
   * @param payer - Address/identifier of payer
   * @param metadata - Optional additional metadata
   * @returns Guarantee details
   */
  async createGuarantee(
    entryHash: string,
    entrySizeBytes: number,
    feeAmount: number,
    payer: string,
    metadata?: Record<string, unknown>
  ): Promise<{
    status: string;
    guarantee: PermanenceGuarantee;
    pool_status: EndowmentPoolStatus;
    message: string;
  }> {
    return this.client.post('/endowment/guarantee', {
      entry_hash: entryHash,
      entry_size_bytes: entrySizeBytes,
      fee_amount: feeAmount,
      payer,
      metadata,
    });
  }

  /**
   * Get permanence guarantee for an entry.
   *
   * @param entryHash - Hash of the entry
   * @returns Guarantee details or null if not found
   */
  async getGuarantee(entryHash: string): Promise<PermanenceGuarantee | null> {
    try {
      return await this.client.get<PermanenceGuarantee>(`/endowment/guarantee/${entryHash}`);
    } catch (error: unknown) {
      if (error instanceof Error && error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Verify a permanence guarantee cryptographically.
   *
   * @param entryHash - Hash of the entry
   * @param guaranteeHash - Claimed guarantee hash
   * @returns Verification result
   */
  async verifyGuarantee(
    entryHash: string,
    guaranteeHash: string
  ): Promise<{
    valid: boolean;
    guarantee?: PermanenceGuarantee;
    error?: string;
    verification_time?: string;
  }> {
    return this.client.post(`/endowment/guarantee/${entryHash}/verify`, {
      guarantee_hash: guaranteeHash,
    });
  }

  /**
   * Top up a partial permanence guarantee.
   *
   * @param entryHash - Hash of the entry
   * @param additionalFee - Additional fee to add
   * @param payer - Address/identifier of payer
   * @returns Updated guarantee details
   */
  async topUpGuarantee(
    entryHash: string,
    additionalFee: number,
    payer: string
  ): Promise<{
    status: string;
    guarantee: PermanenceGuarantee;
    upgrade_summary: {
      previous_status: string;
      new_status: string;
      additional_fee_paid: number;
      new_sustainability_years: number;
    };
  }> {
    return this.client.post(`/endowment/guarantee/${entryHash}/topup`, {
      additional_fee: additionalFee,
      payer,
    });
  }

  // ===========================================================================
  // Pool Status
  // ===========================================================================

  /**
   * Get current endowment pool status.
   *
   * @returns Pool status including principal, yield, sustainability
   */
  async getPoolStatus(): Promise<EndowmentPoolStatus> {
    return this.client.get<EndowmentPoolStatus>('/endowment/status');
  }

  /**
   * Get comprehensive endowment statistics.
   *
   * @returns Detailed statistics about pool, guarantees, yields, payouts
   */
  async getStatistics(): Promise<EndowmentStatistics> {
    return this.client.get<EndowmentStatistics>('/endowment/statistics');
  }

  /**
   * Get sustainability report with projections.
   *
   * @returns 10-year projection and sustainability analysis
   */
  async getSustainabilityReport(): Promise<SustainabilityReport> {
    return this.client.get<SustainabilityReport>('/endowment/sustainability');
  }

  /**
   * Quick health check for the endowment.
   *
   * @returns Simple health status
   */
  async getHealth(): Promise<{
    status: string;
    principal: number;
    sustainability_ratio: number;
    entries_guaranteed: number;
  }> {
    return this.client.get('/endowment/health');
  }

  // ===========================================================================
  // Yield Management
  // ===========================================================================

  /**
   * Trigger yield accrual on the endowment.
   *
   * @param daysElapsed - Override days (auto-calculated if omitted)
   * @returns Yield accrual result
   */
  async accrueYield(daysElapsed?: number): Promise<YieldAccrualResult> {
    return this.client.post<YieldAccrualResult>('/endowment/yield/accrue', {
      days_elapsed: daysElapsed,
    });
  }

  /**
   * Get yield accrual history.
   *
   * @param limit - Maximum records to return (default: 50)
   * @returns List of yield accruals
   */
  async getYieldHistory(limit: number = 50): Promise<{
    count: number;
    total_yield_generated: number;
    accruals: Array<{
      accrual_id: string;
      period_start: string;
      period_end: string;
      yield_amount: number;
      yield_rate: number;
      strategy: string;
    }>;
  }> {
    return this.client.get('/endowment/yield/history', { limit: limit.toString() });
  }

  // ===========================================================================
  // Storage Payouts
  // ===========================================================================

  /**
   * Process a storage payout to a provider.
   *
   * @param storageProvider - Provider identifier
   * @param entriesStored - Number of entries stored
   * @param bytesStored - Total bytes stored
   * @returns Payout result
   */
  async processStoragePayout(
    storageProvider: string,
    entriesStored: number,
    bytesStored: number
  ): Promise<StoragePayoutResult> {
    return this.client.post<StoragePayoutResult>('/endowment/payout', {
      storage_provider: storageProvider,
      entries_stored: entriesStored,
      bytes_stored: bytesStored,
    });
  }

  /**
   * Get storage payout history.
   *
   * @param limit - Maximum records to return (default: 50)
   * @returns List of storage payouts
   */
  async getPayoutHistory(limit: number = 50): Promise<{
    count: number;
    total_payouts: number;
    payouts: Array<{
      payout_id: string;
      period: string;
      storage_provider: string;
      entries_covered: number;
      bytes_stored: number;
      amount: number;
      funded_from: string;
    }>;
  }> {
    return this.client.get('/endowment/payouts', { limit: limit.toString() });
  }

  // ===========================================================================
  // Events
  // ===========================================================================

  /**
   * Get endowment event log.
   *
   * @param limit - Maximum events to return (default: 100)
   * @param eventType - Filter by event type (optional)
   * @returns List of events
   */
  async getEvents(
    limit: number = 100,
    eventType?: string
  ): Promise<{
    count: number;
    events: Array<{
      event_type: string;
      timestamp: string;
      data: Record<string, unknown>;
    }>;
  }> {
    const params: Record<string, string> = { limit: limit.toString() };
    if (eventType) {
      params.event_type = eventType;
    }
    return this.client.get('/endowment/events', params);
  }
}
