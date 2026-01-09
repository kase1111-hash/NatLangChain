/**
 * Settlements Client - Settlement and Mediation Operations
 *
 * Handles settlement lifecycle through the mediator-node protocol:
 * - Proposing settlements
 * - Accepting settlements
 * - Tracking settlement status
 * - Claiming payouts
 */

import { HttpClient } from '../utils/client';
import type {
  SettlementProposeRequest,
  SettlementProposeResponse,
  SettlementAcceptRequest,
  SettlementStatusResponse,
  Settlement,
} from '../types';

/** Reputation response */
export interface ReputationResponse {
  mediator_id: string;
  reputation_score: number;
  successful_settlements: number;
  total_settlements: number;
  average_time_to_settlement: number;
  disputes_escalated: number;
}

/** Delegation response */
export interface DelegationResponse {
  mediator_id: string;
  delegations: Array<{
    delegator: string;
    amount: number;
    delegated_at: string;
  }>;
  total_delegated: number;
}

/** Stake response */
export interface StakeResponse {
  status: 'success';
  transaction_id: string;
  amount: number;
  action: 'bond' | 'unbond';
}

/**
 * Settlements client for mediator-node protocol operations
 */
export class SettlementsClient {
  constructor(private readonly http: HttpClient) {}

  // ==========================================================================
  // Settlement Operations
  // ==========================================================================

  /**
   * Propose a settlement between two parties
   *
   * Creates a settlement proposal that both parties must accept
   * to finalize.
   *
   * @param request - Settlement proposal details
   * @returns Created settlement
   *
   * @example
   * ```ts
   * const settlement = await client.settlements.propose({
   *   intent_a: 'Alice wants to sell 100 widgets',
   *   intent_b: 'Bob wants to buy widgets at $10 each',
   *   terms: 'Alice sells 100 widgets to Bob for $1000. Delivery in 14 days.',
   *   fee: 10 // Optional mediator fee
   * });
   *
   * console.log(`Settlement proposed: ${settlement.settlement.id}`);
   * ```
   */
  async propose(request: SettlementProposeRequest): Promise<SettlementProposeResponse> {
    return this.http.post<SettlementProposeResponse>('/api/v1/settlements', request);
  }

  /**
   * Get settlement status
   *
   * @param settlementId - Settlement identifier
   * @returns Current settlement status
   *
   * @example
   * ```ts
   * const status = await client.settlements.getStatus('stl_123abc');
   *
   * console.log(`Status: ${status.settlement.status}`);
   * console.log(`Accepted by: ${status.accepted_by.join(', ')}`);
   * ```
   */
  async getStatus(settlementId: string): Promise<SettlementStatusResponse> {
    return this.http.get<SettlementStatusResponse>(
      `/api/v1/settlements/${encodeURIComponent(settlementId)}/status`
    );
  }

  /**
   * Accept a settlement as one of the parties
   *
   * Both parties must accept for the settlement to be finalized.
   *
   * @param settlementId - Settlement identifier
   * @param request - Acceptance details
   * @returns Updated settlement
   *
   * @example
   * ```ts
   * // Alice accepts
   * await client.settlements.accept('stl_123abc', {
   *   party: 'A',
   *   party_id: 'alice@example.com'
   * });
   *
   * // Bob accepts
   * await client.settlements.accept('stl_123abc', {
   *   party: 'B',
   *   party_id: 'bob@example.com'
   * });
   *
   * // Check if finalized
   * const status = await client.settlements.getStatus('stl_123abc');
   * console.log(status.settlement.status); // 'finalized'
   * ```
   */
  async accept(settlementId: string, request: SettlementAcceptRequest): Promise<Settlement> {
    return this.http.post<Settlement>(
      `/api/v1/settlements/${encodeURIComponent(settlementId)}/accept`,
      request
    );
  }

  /**
   * Claim payout from a finalized settlement
   *
   * @param settlementId - Settlement identifier
   * @returns Payout transaction details
   *
   * @example
   * ```ts
   * const payout = await client.settlements.claimPayout('stl_123abc');
   * console.log(`Payout claimed: ${payout.amount}`);
   * ```
   */
  async claimPayout(settlementId: string): Promise<{ status: string; amount: number }> {
    return this.http.post<{ status: string; amount: number }>(
      `/api/v1/settlements/${encodeURIComponent(settlementId)}/claim`,
      {}
    );
  }

  // ==========================================================================
  // Reputation Operations
  // ==========================================================================

  /**
   * Get mediator reputation
   *
   * @param mediatorId - Mediator identifier
   * @returns Reputation details
   *
   * @example
   * ```ts
   * const rep = await client.settlements.getReputation('mediator_123');
   * console.log(`Score: ${rep.reputation_score}`);
   * console.log(`Success rate: ${rep.successful_settlements}/${rep.total_settlements}`);
   * ```
   */
  async getReputation(mediatorId: string): Promise<ReputationResponse> {
    return this.http.get<ReputationResponse>(
      `/api/v1/reputation/${encodeURIComponent(mediatorId)}`
    );
  }

  /**
   * Update mediator reputation (typically called by the protocol)
   *
   * @param mediatorId - Mediator identifier
   * @param reputation - New reputation data
   */
  async updateReputation(
    mediatorId: string,
    reputation: Partial<ReputationResponse>
  ): Promise<ReputationResponse> {
    return this.http.post<ReputationResponse>('/api/v1/reputation', {
      mediator_id: mediatorId,
      ...reputation,
    });
  }

  // ==========================================================================
  // Delegation Operations
  // ==========================================================================

  /**
   * Get delegations for a mediator
   *
   * @param mediatorId - Mediator identifier
   * @returns Delegation details
   *
   * @example
   * ```ts
   * const delegations = await client.settlements.getDelegations('mediator_123');
   * console.log(`Total delegated: ${delegations.total_delegated}`);
   * ```
   */
  async getDelegations(mediatorId: string): Promise<DelegationResponse> {
    return this.http.get<DelegationResponse>(
      `/api/v1/delegations/${encodeURIComponent(mediatorId)}`
    );
  }

  // ==========================================================================
  // Staking Operations
  // ==========================================================================

  /**
   * Bond stake as a mediator
   *
   * @param amount - Amount to stake
   * @returns Stake transaction details
   *
   * @example
   * ```ts
   * const stake = await client.settlements.bondStake(1000);
   * console.log(`Staked ${stake.amount} - tx: ${stake.transaction_id}`);
   * ```
   */
  async bondStake(amount: number): Promise<StakeResponse> {
    return this.http.post<StakeResponse>('/api/v1/stake/bond', { amount });
  }

  /**
   * Unbond stake as a mediator
   *
   * @returns Unstake transaction details
   *
   * @example
   * ```ts
   * const unstake = await client.settlements.unbondStake();
   * console.log(`Unbonded ${unstake.amount}`);
   * ```
   */
  async unbondStake(): Promise<StakeResponse> {
    return this.http.post<StakeResponse>('/api/v1/stake/unbond', {});
  }
}
