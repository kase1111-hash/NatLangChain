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
import { EndowmentClient } from './clients/endowment';
import { AnchoringClient } from './clients/anchoring';
import { IdentityClient } from './clients/identity';
import { ComposabilityClient } from './clients/composability';
import { ComputeClient } from './clients/compute';
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
export type {
  AnchorChain,
  AnchorBatchStatus,
  QueueEntryRequest,
  QueueBlockRequest,
  CreateAnchorRequest,
  VerifyProofRequest,
  QueueResult,
  QueueStatus,
  MerkleProof,
  AnchorBatch,
  AnchorResult,
  VerifyProofResult,
  LegalProof,
  ChainCostEstimate,
  CostEstimation,
  AnchoringStatistics,
  AnchorProvider,
  AnchoringEvent,
  EventsResponse,
} from './clients/anchoring';
export type {
  VerificationMethodType,
  VerificationRelationship,
  ServiceType,
  DIDStatus,
  VerificationMethod,
  ServiceEndpoint,
  DIDDocument,
  DIDDocumentMetadata,
  DIDResolutionResult,
  CreateDIDRequest,
  CreateDIDResponse,
  UpdateDIDRequest,
  UpdateDIDResponse,
  AddKeyRequest,
  AddKeyResponse,
  RevokeKeyResponse,
  RotateKeyRequest,
  RotateKeyResponse,
  AddServiceRequest,
  AddServiceResponse,
  Delegation,
  GrantDelegationRequest,
  DelegationsResponse,
  LinkAuthorRequest,
  ResolveAuthorResponse,
  VerifyAuthorshipRequest,
  VerifyAuthorshipResponse,
  VerifyAuthenticationRequest,
  VerifyAuthenticationResponse,
  IdentityStatistics,
  DIDEvent,
  KeyRotationRecord,
  DIDHistoryResponse,
  IdentityEventsResponse,
  DeactivateResponse,
} from './clients/identity';
export type {
  StreamType,
  CommitType,
  StreamState,
  SchemaType,
  LinkType,
  StreamMetadata,
  StreamCommit,
  Stream,
  CrossAppLink,
  Schema,
  Application,
  CreateStreamRequest,
  CreateStreamResponse,
  UpdateStreamRequest,
  UpdateStreamResponse,
  AnchorStreamRequest,
  RegisterSchemaRequest,
  RegisterAppRequest,
  CreateLinkRequest,
  CreateContractStreamRequest,
  ExportRequest,
  ExportPackage,
  ImportRequest,
  ImportResult,
  QueryStreamsOptions,
  StreamsResponse,
  SchemasResponse,
  ApplicationsResponse,
  LinksResponse,
  LinkedStreamsResponse,
  StreamHistoryResponse,
  ComposabilityStatistics,
  ComposabilityEvent,
  ComposabilityEventsResponse,
} from './clients/composability';
export type {
  DataAssetType,
  ComputeAlgorithmType,
  AccessLevel,
  JobStatus,
  PrivacyLevel,
  ComputeEventType,
  DataAsset,
  ComputeAlgorithm,
  AccessToken,
  ComputeJob,
  ComputeResult,
  ComputeEvent,
  RegisterAssetRequest,
  UpdateAssetRequest,
  GrantAccessRequest,
  RegisterAlgorithmRequest,
  SubmitJobRequest,
  AssetsResponse,
  AlgorithmsResponse,
  AccessTokensResponse,
  JobsResponse,
  ComputeEventsResponse,
  ComputeStatistics,
} from './clients/compute';

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
   * Endowment operations: permanence guarantees, yield management
   *
   * Pay-once-store-forever system inspired by Arweave.
   *
   * @example
   * ```ts
   * // Calculate permanence fee
   * const fee = await client.endowment.calculateFee(2048);
   *
   * // Create permanence guarantee
   * await client.endowment.createGuarantee(entryHash, 2048, fee.total_fee, 'alice');
   *
   * // Get pool status
   * const status = await client.endowment.getPoolStatus();
   *
   * // Get sustainability report
   * const report = await client.endowment.getSustainabilityReport();
   * ```
   */
  public readonly endowment: EndowmentClient;

  /**
   * Anchoring operations: external blockchain anchoring
   *
   * Anchor NatLangChain entries to external blockchains (Ethereum, Arweave)
   * for independent verification and legal proof generation.
   *
   * @example
   * ```ts
   * // Queue entry for anchoring
   * await client.anchoring.queueEntry({ entry_hash: 'abc123...' });
   *
   * // Create anchor batch
   * const anchor = await client.anchoring.createAnchor({ chain: 'ethereum_mainnet' });
   *
   * // Get proof for entry
   * const proof = await client.anchoring.getProof('abc123...');
   *
   * // Generate legal proof document
   * const legal = await client.anchoring.getLegalProof('abc123...');
   * ```
   */
  public readonly anchoring: AnchoringClient;

  /**
   * Identity operations: DID management, key rotation, verification
   *
   * W3C-compliant Decentralized Identifier (DID) system for NatLangChain.
   *
   * @example
   * ```ts
   * // Create a new identity
   * const identity = await client.identity.createDID({
   *   display_name: 'Alice',
   *   email: 'alice@example.com'
   * });
   *
   * // Resolve a DID
   * const resolved = await client.identity.resolve(identity.did);
   *
   * // Rotate a key
   * await client.identity.rotateKey(identity.did, 'key-1');
   *
   * // Verify authorship
   * await client.identity.verifyAuthorship({
   *   entry_hash: 'abc123...',
   *   claimed_author: 'alice@example.com'
   * });
   * ```
   */
  public readonly identity: IdentityClient;

  /**
   * Composability operations: cross-application data sharing
   *
   * Stream-based data model for versioned, composable content across applications.
   * Inspired by Ceramic Network.
   *
   * @example
   * ```ts
   * // Create a composable stream
   * const stream = await client.composability.createStream({
   *   stream_type: 'contract_stream',
   *   content: { terms: '...' },
   *   controller: 'did:nlc:...'
   * });
   *
   * // Link streams across applications
   * await client.composability.createLink({
   *   source_stream_id: stream.stream_id,
   *   target_stream_id: 'kjzl_...',
   *   link_type: 'reference'
   * });
   *
   * // Export for sharing
   * const pkg = await client.composability.export({
   *   stream_ids: [stream.stream_id]
   * });
   * ```
   */
  public readonly composability: ComposabilityClient;

  /**
   * Compute operations: privacy-preserving computation on data
   *
   * Run algorithms on private data without exposing the underlying content.
   * Inspired by Ocean Protocol's compute-to-data paradigm.
   *
   * @example
   * ```ts
   * // Register a data asset
   * const asset = await client.compute.registerAsset({
   *   asset_type: 'contract',
   *   owner: 'did:nlc:...',
   *   name: 'Private Contracts',
   *   data: contractData,
   *   privacy_level: 'aggregated'
   * });
   *
   * // Grant compute access
   * const token = await client.compute.grantAccess({
   *   asset_id: asset.asset_id,
   *   owner: 'did:nlc:...',
   *   grantee: 'did:nlc:analyst...',
   *   access_level: 'compute_only'
   * });
   *
   * // Submit a compute job
   * const job = await client.compute.submitJob({
   *   asset_id: asset.asset_id,
   *   algorithm_id: 'builtin_count',
   *   access_token_id: token.token_id,
   *   requester: 'did:nlc:analyst...',
   *   parameters: { field: 'status', value: 'active' }
   * });
   *
   * // Get privacy-filtered result
   * const result = await client.compute.getJobResult(job.job_id, 'did:nlc:analyst...');
   * ```
   */
  public readonly compute: ComputeClient;

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
    this.endowment = new EndowmentClient(this.http);
    this.anchoring = new AnchoringClient(this.http);
    this.identity = new IdentityClient(this.http);
    this.composability = new ComposabilityClient(this.http);
    this.compute = new ComputeClient(this.http);
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
