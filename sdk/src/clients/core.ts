/**
 * Core Client - Entries, Blocks, and Chain Operations
 *
 * Handles fundamental blockchain operations:
 * - Entry creation and validation
 * - Block retrieval and mining
 * - Chain management and stats
 */

import { HttpClient } from '../utils/client';
import type {
  CreateEntryRequest,
  CreateEntryResponse,
  ValidateEntryRequest,
  ValidationResult,
  MineRequest,
  MineResponse,
  Block,
  BlockResponse,
  LatestBlockResponse,
  EntriesByAuthorResponse,
  SearchEntriesResponse,
  PendingEntriesResponse,
  ChainResponse,
  HealthResponse,
  StatsResponse,
  ValidateChainResponse,
  Entry,
} from '../types';

/**
 * Core client for fundamental NatLangChain operations
 */
export class CoreClient {
  constructor(private readonly http: HttpClient) {}

  // ==========================================================================
  // Health & Status
  // ==========================================================================

  /**
   * Check API health status
   *
   * @example
   * ```ts
   * const health = await client.core.health();
   * console.log(health.status); // 'healthy'
   * console.log(health.llm_validation_available);
   * ```
   */
  async health(): Promise<HealthResponse> {
    return this.http.get<HealthResponse>('/health');
  }

  /**
   * Get comprehensive blockchain statistics
   *
   * @example
   * ```ts
   * const stats = await client.core.stats();
   * console.log(`${stats.total_entries} entries across ${stats.blocks} blocks`);
   * console.log('Features:', stats.features);
   * ```
   */
  async stats(): Promise<StatsResponse> {
    return this.http.get<StatsResponse>('/stats');
  }

  // ==========================================================================
  // Entry Operations
  // ==========================================================================

  /**
   * Create a new natural language entry on the blockchain
   *
   * @param request - Entry creation parameters
   * @returns Created entry with validation results
   *
   * @example
   * ```ts
   * const result = await client.core.createEntry({
   *   content: 'Alice agrees to deliver 100 widgets to Bob by March 15th',
   *   author: 'alice@example.com',
   *   intent: 'Delivery agreement for widget order #1234',
   *   validate: true,
   *   auto_mine: false
   * });
   *
   * console.log(result.validation?.overall_decision);
   * ```
   */
  async createEntry(request: CreateEntryRequest): Promise<CreateEntryResponse> {
    return this.http.post<CreateEntryResponse>('/entry', request);
  }

  /**
   * Validate an entry without adding it to the blockchain
   *
   * Useful for pre-flight validation before committing.
   *
   * @param request - Entry to validate
   * @returns Validation results
   *
   * @example
   * ```ts
   * const validation = await client.core.validateEntry({
   *   content: 'Transfer ownership of asset X to Bob',
   *   author: 'alice',
   *   intent: 'Asset transfer'
   * });
   *
   * if (validation.overall_decision === 'ACCEPTED') {
   *   // Safe to create the actual entry
   * }
   * ```
   */
  async validateEntry(request: ValidateEntryRequest): Promise<ValidationResult> {
    return this.http.post<ValidationResult>('/entry/validate', request);
  }

  /**
   * Get all entries by a specific author
   *
   * @param author - Author identifier
   * @returns List of entries by the author
   *
   * @example
   * ```ts
   * const result = await client.core.getEntriesByAuthor('alice@example.com');
   * console.log(`Found ${result.count} entries by ${result.author}`);
   * ```
   */
  async getEntriesByAuthor(author: string): Promise<EntriesByAuthorResponse> {
    return this.http.get<EntriesByAuthorResponse>(`/entries/author/${encodeURIComponent(author)}`);
  }

  /**
   * Search entries by keyword
   *
   * @param query - Search query
   * @param limit - Maximum results (default: 10)
   * @returns Matching entries
   *
   * @example
   * ```ts
   * const results = await client.core.searchEntries('widget delivery', 20);
   * ```
   */
  async searchEntries(query: string, limit?: number): Promise<SearchEntriesResponse> {
    return this.http.get<SearchEntriesResponse>('/entries/search', {
      q: query,
      ...(limit && { limit }),
    });
  }

  /**
   * Get all pending (unmined) entries
   *
   * @returns List of pending entries
   *
   * @example
   * ```ts
   * const pending = await client.core.getPendingEntries();
   * if (pending.count > 0) {
   *   await client.core.mine();
   * }
   * ```
   */
  async getPendingEntries(): Promise<PendingEntriesResponse> {
    return this.http.get<PendingEntriesResponse>('/pending');
  }

  /**
   * Get a frozen (immutable) entry state at T0
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Entry index within the block
   * @returns Frozen entry state
   */
  async getFrozenEntry(blockIndex: number, entryIndex: number): Promise<Entry> {
    return this.http.get<Entry>(`/entry/frozen/${blockIndex}/${entryIndex}`);
  }

  // ==========================================================================
  // Block Operations
  // ==========================================================================

  /**
   * Mine pending entries into a new block
   *
   * @param request - Optional mining parameters
   * @returns Mined block details
   *
   * @example
   * ```ts
   * const block = await client.core.mine({ difficulty: 3 });
   * console.log(`Mined block ${block.block.index} with hash ${block.block.hash}`);
   * ```
   */
  async mine(request?: MineRequest): Promise<MineResponse> {
    return this.http.post<MineResponse>('/mine', request ?? {});
  }

  /**
   * Get a specific block by index
   *
   * @param index - Block index (0 = genesis block)
   * @returns Block data
   *
   * @example
   * ```ts
   * const genesis = await client.core.getBlock(0);
   * const latest = await client.core.getBlock(await client.core.stats().then(s => s.blocks - 1));
   * ```
   */
  async getBlock(index: number): Promise<BlockResponse> {
    return this.http.get<BlockResponse>(`/block/${index}`);
  }

  /**
   * Get the most recent block
   *
   * @returns Latest block with chain metadata
   *
   * @example
   * ```ts
   * const latest = await client.core.getLatestBlock();
   * console.log(`Chain has ${latest.chain_length} blocks`);
   * ```
   */
  async getLatestBlock(): Promise<LatestBlockResponse> {
    return this.http.get<LatestBlockResponse>('/block/latest');
  }

  // ==========================================================================
  // Chain Operations
  // ==========================================================================

  /**
   * Get the entire blockchain
   *
   * @returns Full blockchain data
   *
   * @example
   * ```ts
   * const chain = await client.core.getChain();
   * console.log(`Chain valid: ${chain.valid}`);
   * ```
   */
  async getChain(): Promise<ChainResponse> {
    return this.http.get<ChainResponse>('/chain');
  }

  /**
   * Get the full narrative history as human-readable text
   *
   * This is a key NatLangChain feature: the entire ledger as readable prose.
   *
   * @returns Complete narrative of all entries
   *
   * @example
   * ```ts
   * const narrative = await client.core.getNarrative();
   * console.log(narrative); // Human-readable transaction history
   * ```
   */
  async getNarrative(): Promise<string> {
    return this.http.get<string>('/chain/narrative');
  }

  /**
   * Validate the entire blockchain integrity
   *
   * @returns Validation status
   *
   * @example
   * ```ts
   * const validation = await client.core.validateChain();
   * if (!validation.valid) {
   *   console.error('Blockchain integrity compromised!');
   * }
   * ```
   */
  async validateChain(): Promise<ValidateChainResponse> {
    return this.http.get<ValidateChainResponse>('/validate/chain');
  }
}
