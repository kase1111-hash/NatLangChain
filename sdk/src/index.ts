/**
 * NatLangChain TypeScript SDK
 *
 * The official SDK for NatLangChain - the prose-first, intent-native blockchain.
 *
 * @example
 * ```ts
 * import { NatLangChain } from '@natlangchain/sdk';
 *
 * const client = new NatLangChain({
 *   endpoint: 'https://api.natlangchain.org',
 *   apiKey: 'your-api-key'
 * });
 *
 * // Create an entry
 * const entry = await client.core.createEntry({
 *   content: 'Alice agrees to deliver 100 widgets to Bob',
 *   author: 'alice@example.com',
 *   intent: 'Widget delivery agreement'
 * });
 *
 * // Search semantically
 * const results = await client.search.semantic({
 *   query: 'widget delivery',
 *   top_k: 5
 * });
 *
 * // Post a contract
 * const contract = await client.contracts.post({
 *   content: 'Offering consulting services at $200/hour',
 *   author: 'consultant@example.com',
 *   intent: 'Service offering',
 *   contract_type: 'offer'
 * });
 * ```
 *
 * @packageDocumentation
 */

import { HttpClient } from './utils/client';
import { CoreClient } from './clients/core';
import { SearchClient } from './clients/search';
import { ContractsClient } from './clients/contracts';
import { DisputesClient } from './clients/disputes';
import { SettlementsClient } from './clients/settlements';
import { DerivativesClient } from './clients/derivatives';
import type { NatLangChainConfig } from './types';

// Re-export all types
export * from './types';

// Re-export error classes
export { NatLangChainError, NetworkError } from './utils/client';

// Re-export client-specific types
export type { ContractListOptions } from './clients/contracts';
export type {
  DisputeListOptions,
  DisputeResolveRequest,
  DisputeAnalysisResponse,
  DisputePackageResponse,
} from './clients/disputes';
export type {
  ReputationResponse,
  DelegationResponse,
  StakeResponse,
} from './clients/settlements';
export type {
  DerivativeType,
  ParentRef,
  DerivativeRef,
  LineageRef,
  DerivativesResponse,
  LineageResponse,
  DerivationTreeResponse,
  DerivativeStatusResponse,
  DerivativeTypesResponse,
  ValidateDerivativeRefsRequest,
  ValidateDerivativeRefsResponse,
  GetDerivativesOptions,
  GetLineageOptions,
} from './clients/derivatives';

/**
 * NatLangChain SDK Client
 *
 * The main entry point for interacting with NatLangChain.
 * Provides access to all API modules through a unified interface.
 *
 * @example
 * ```ts
 * const client = new NatLangChain({
 *   endpoint: 'http://localhost:5000',
 *   apiKey: 'optional-api-key',
 *   timeout: 30000,
 *   retry: {
 *     attempts: 3,
 *     delay: 1000
 *   }
 * });
 * ```
 */
export class NatLangChain {
  private readonly http: HttpClient;

  /**
   * Core operations: entries, blocks, chain management
   *
   * @example
   * ```ts
   * // Create entry
   * await client.core.createEntry({ ... });
   *
   * // Get stats
   * const stats = await client.core.stats();
   *
   * // Mine pending entries
   * await client.core.mine();
   * ```
   */
  public readonly core: CoreClient;

  /**
   * Search operations: semantic search, drift detection, oracles
   *
   * @example
   * ```ts
   * // Semantic search
   * await client.search.semantic({ query: 'delivery agreement' });
   *
   * // Check drift
   * await client.search.checkDrift({ ... });
   *
   * // Dialectic validation
   * await client.search.validateDialectic({ ... });
   * ```
   */
  public readonly search: SearchClient;

  /**
   * Contract operations: parse, post, match, respond
   *
   * @example
   * ```ts
   * // Parse contract
   * await client.contracts.parse({ content: '...' });
   *
   * // Post offer
   * await client.contracts.post({ ..., contract_type: 'offer' });
   *
   * // Find matches
   * await client.contracts.match();
   * ```
   */
  public readonly contracts: ContractsClient;

  /**
   * Dispute operations: file, evidence, escalate, resolve
   *
   * @example
   * ```ts
   * // File dispute
   * await client.disputes.file({ ... });
   *
   * // Submit evidence
   * await client.disputes.submitEvidence(id, { ... });
   *
   * // Get AI analysis
   * await client.disputes.analyze(id);
   * ```
   */
  public readonly disputes: DisputesClient;

  /**
   * Settlement operations: propose, accept, claim payouts
   *
   * @example
   * ```ts
   * // Propose settlement
   * await client.settlements.propose({ ... });
   *
   * // Accept as party
   * await client.settlements.accept(id, { party: 'A', party_id: '...' });
   *
   * // Get reputation
   * await client.settlements.getReputation(mediatorId);
   * ```
   */
  public readonly settlements: SettlementsClient;

  /**
   * Derivative operations: lineage tracking, derivation trees
   *
   * @example
   * ```ts
   * // Get derivatives of an entry
   * await client.derivatives.getDerivatives(1, 0, { recursive: true });
   *
   * // Get lineage/ancestry
   * await client.derivatives.getLineage(5, 2);
   *
   * // Get full derivation tree
   * await client.derivatives.getTree(3, 1);
   *
   * // Check derivative status
   * await client.derivatives.getStatus(2, 0);
   * ```
   */
  public readonly derivatives: DerivativesClient;

  /**
   * Create a new NatLangChain client
   *
   * @param config - Client configuration
   */
  constructor(config: NatLangChainConfig) {
    this.http = new HttpClient(config);

    this.core = new CoreClient(this.http);
    this.search = new SearchClient(this.http);
    this.contracts = new ContractsClient(this.http);
    this.disputes = new DisputesClient(this.http);
    this.settlements = new SettlementsClient(this.http);
    this.derivatives = new DerivativesClient(this.http);
  }

  /**
   * Create a client with default local development settings
   *
   * @param apiKey - Optional API key
   * @returns Configured client for local development
   *
   * @example
   * ```ts
   * const client = NatLangChain.local();
   * // or with API key
   * const client = NatLangChain.local('my-dev-key');
   * ```
   */
  static local(apiKey?: string): NatLangChain {
    return new NatLangChain({
      endpoint: 'http://localhost:5000',
      apiKey,
    });
  }

  /**
   * Create a client for the testnet
   *
   * @param apiKey - API key for testnet
   * @returns Configured client for testnet
   *
   * @example
   * ```ts
   * const client = NatLangChain.testnet('your-testnet-key');
   * ```
   */
  static testnet(apiKey: string): NatLangChain {
    return new NatLangChain({
      endpoint: 'https://testnet.natlangchain.org',
      apiKey,
    });
  }

  /**
   * Create a client for mainnet
   *
   * @param apiKey - API key for mainnet
   * @returns Configured client for mainnet
   *
   * @example
   * ```ts
   * const client = NatLangChain.mainnet('your-mainnet-key');
   * ```
   */
  static mainnet(apiKey: string): NatLangChain {
    return new NatLangChain({
      endpoint: 'https://api.natlangchain.org',
      apiKey,
    });
  }
}

// Default export
export default NatLangChain;
