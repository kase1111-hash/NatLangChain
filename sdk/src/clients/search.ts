/**
 * Search Client - Semantic Search and Drift Detection
 *
 * Handles semantic analysis operations:
 * - Vector-based semantic search
 * - Similar entry finding
 * - Intent-execution drift detection
 * - Dialectic consensus validation
 * - Oracle verification
 */

import { HttpClient } from '../utils/client';
import type {
  SemanticSearchRequest,
  SemanticSearchResponse,
  FindSimilarRequest,
  FindSimilarResponse,
  DriftCheckRequest,
  DriftCheckResponse,
  EntryDriftResponse,
  DialecticValidateRequest,
  DialecticResult,
  OracleVerifyRequest,
  OracleVerifyResponse,
} from '../types';

/**
 * Search client for semantic analysis operations
 */
export class SearchClient {
  constructor(private readonly http: HttpClient) {}

  // ==========================================================================
  // Semantic Search
  // ==========================================================================

  /**
   * Perform semantic search across blockchain entries
   *
   * Uses vector embeddings to find semantically similar entries,
   * even if they don't share exact keywords.
   *
   * @param request - Search parameters
   * @returns Semantically similar entries with scores
   *
   * @example
   * ```ts
   * const results = await client.search.semantic({
   *   query: 'agreement to deliver goods',
   *   top_k: 10,
   *   min_score: 0.7,
   *   field: 'content'
   * });
   *
   * for (const result of results.results) {
   *   console.log(`Score: ${result.score} - ${result.entry.intent}`);
   * }
   * ```
   */
  async semantic(request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    return this.http.post<SemanticSearchResponse>('/search/semantic', request);
  }

  /**
   * Find entries similar to given content
   *
   * @param request - Content to find similar entries for
   * @returns Similar entries with similarity scores
   *
   * @example
   * ```ts
   * const similar = await client.search.findSimilar({
   *   content: 'Party A will provide consulting services to Party B',
   *   top_k: 5,
   *   exclude_exact: true
   * });
   * ```
   */
  async findSimilar(request: FindSimilarRequest): Promise<FindSimilarResponse> {
    return this.http.post<FindSimilarResponse>('/search/similar', request);
  }

  // ==========================================================================
  // Drift Detection
  // ==========================================================================

  /**
   * Check semantic drift between intent and execution
   *
   * Compares the original on-chain intent with actual execution logs
   * to detect if actions have drifted from stated purpose.
   *
   * @param request - Intent and execution to compare
   * @returns Drift analysis with score and recommendations
   *
   * @example
   * ```ts
   * const drift = await client.search.checkDrift({
   *   on_chain_intent: 'Deliver 100 widgets by March 15',
   *   execution_log: 'Shipped 95 widgets on March 20'
   * });
   *
   * if (!drift.aligned) {
   *   console.warn(`Drift detected: ${drift.drift_score}`);
   *   console.log('Recommendations:', drift.recommendations);
   * }
   * ```
   */
  async checkDrift(request: DriftCheckRequest): Promise<DriftCheckResponse> {
    return this.http.post<DriftCheckResponse>('/drift/check', request);
  }

  /**
   * Check drift for a specific blockchain entry
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Entry index within the block
   * @param executionLog - Actual execution log to compare
   * @returns Drift analysis for the specific entry
   *
   * @example
   * ```ts
   * const drift = await client.search.checkEntryDrift(5, 2, {
   *   execution_log: 'Payment processed via wire transfer'
   * });
   *
   * console.log(`Entry by ${drift.entry_info.author}: ${drift.aligned ? 'aligned' : 'drifted'}`);
   * ```
   */
  async checkEntryDrift(
    blockIndex: number,
    entryIndex: number,
    executionLog: string
  ): Promise<EntryDriftResponse> {
    return this.http.post<EntryDriftResponse>(
      `/drift/entry/${blockIndex}/${entryIndex}`,
      { execution_log: executionLog }
    );
  }

  // ==========================================================================
  // Dialectic Consensus
  // ==========================================================================

  /**
   * Validate an entry using dialectic consensus (Skeptic/Facilitator debate)
   *
   * This validation mode uses two AI personas:
   * - Skeptic: Challenges the entry and identifies risks
   * - Facilitator: Defends the entry and identifies merits
   *
   * The synthesis of both perspectives determines the final decision.
   *
   * @param request - Entry to validate
   * @returns Dialectic validation result with both perspectives
   *
   * @example
   * ```ts
   * const result = await client.search.validateDialectic({
   *   content: 'Transfer all assets to external wallet',
   *   author: 'treasury@company.com',
   *   intent: 'Asset consolidation'
   * });
   *
   * console.log('Skeptic concerns:', result.skeptic_analysis.concerns);
   * console.log('Facilitator merits:', result.facilitator_analysis.merits);
   * console.log('Final decision:', result.decision);
   * ```
   */
  async validateDialectic(request: DialecticValidateRequest): Promise<DialecticResult> {
    return this.http.post<DialecticResult>('/validate/dialectic', request);
  }

  // ==========================================================================
  // Oracle Verification
  // ==========================================================================

  /**
   * Verify an external event using semantic oracles
   *
   * Uses AI to evaluate whether claimed external events actually occurred,
   * based on provided evidence and context.
   *
   * @param request - Event to verify
   * @returns Oracle verification results
   *
   * @example
   * ```ts
   * const verification = await client.search.verifyOracle({
   *   event_description: 'Weather conditions in NYC on Jan 15, 2025',
   *   claimed_outcome: 'It was sunny with temperatures above 50F',
   *   evidence: {
   *     weather_api_response: { temp: 52, conditions: 'clear' }
   *   }
   * });
   *
   * if (verification.verified) {
   *   console.log(`Verified with ${verification.confidence}% confidence`);
   * }
   * ```
   */
  async verifyOracle(request: OracleVerifyRequest): Promise<OracleVerifyResponse> {
    return this.http.post<OracleVerifyResponse>('/oracle/verify', request);
  }
}
