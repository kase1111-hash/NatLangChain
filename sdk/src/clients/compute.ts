/**
 * Compute-to-Data Client
 *
 * Privacy-preserving computation on data inspired by Ocean Protocol.
 * Enables running algorithms on private data without exposing the underlying content.
 */

import { HttpClient } from '../utils/client';

// ============================================================================
// Types
// ============================================================================

/** Types of data assets */
export type DataAssetType =
  | 'contract'
  | 'entry'
  | 'entry_set'
  | 'dispute'
  | 'settlement'
  | 'custom';

/** Types of compute algorithms */
export type ComputeAlgorithmType =
  | 'statistical'
  | 'classification'
  | 'matching'
  | 'verification'
  | 'extraction'
  | 'analysis'
  | 'custom';

/** Access levels for data assets */
export type AccessLevel =
  | 'none'
  | 'metadata_only'
  | 'aggregate_only'
  | 'compute_only'
  | 'full_compute'
  | 'full_access';

/** Status of compute jobs */
export type JobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'timeout';

/** Privacy levels for results */
export type PrivacyLevel = 'raw' | 'anonymized' | 'aggregated' | 'differential';

/** Types of compute events */
export type ComputeEventType =
  | 'asset_registered'
  | 'asset_updated'
  | 'asset_revoked'
  | 'algorithm_registered'
  | 'access_granted'
  | 'access_revoked'
  | 'job_submitted'
  | 'job_started'
  | 'job_completed'
  | 'job_failed'
  | 'result_retrieved';

/** A registered data asset */
export interface DataAsset {
  asset_id: string;
  asset_type: DataAssetType;
  owner: string;
  name: string;
  description?: string;
  content_hash?: string;
  entry_count: number;
  allowed_algorithms: string[];
  allowed_compute_providers: string[];
  privacy_level: PrivacyLevel;
  min_aggregation_size: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

/** A registered compute algorithm */
export interface ComputeAlgorithm {
  algorithm_id: string;
  algorithm_type: ComputeAlgorithmType;
  name: string;
  description?: string;
  author?: string;
  code_hash?: string;
  version: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  privacy_preserving: boolean;
  supports_differential_privacy: boolean;
  min_input_size: number;
  audited: boolean;
  created_at: string;
  is_active: boolean;
}

/** An access token for compute operations */
export interface AccessToken {
  token_id: string;
  asset_id: string;
  grantee: string;
  access_level: AccessLevel;
  allowed_algorithms: string[];
  max_uses: number;
  uses_remaining: number;
  expires_at: string;
  created_at: string;
  revoked: boolean;
  valid: boolean;
}

/** A compute job */
export interface ComputeJob {
  job_id: string;
  asset_id: string;
  algorithm_id: string;
  requester: string;
  access_token_id: string;
  parameters: Record<string, unknown>;
  privacy_level: PrivacyLevel;
  status: JobStatus;
  started_at?: string;
  completed_at?: string;
  result_hash?: string;
  error_message?: string;
  created_at: string;
  compute_time_ms?: number;
}

/** Result from a compute job */
export interface ComputeResult {
  result_id: string;
  job_id: string;
  asset_id: string;
  algorithm_id: string;
  requester: string;
  data: Record<string, unknown>;
  privacy_level: PrivacyLevel;
  record_count: number;
  result_hash: string;
  created_at: string;
  expires_at?: string;
}

/** A compute event */
export interface ComputeEvent {
  event_id: string;
  event_type: ComputeEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

/** Request to register a data asset */
export interface RegisterAssetRequest {
  asset_type: DataAssetType;
  owner: string;
  name: string;
  data: Record<string, unknown>[];
  description?: string;
  entry_refs?: Array<{ block_index: number; entry_index: number }>;
  allowed_algorithms?: string[];
  allowed_compute_providers?: string[];
  privacy_level?: PrivacyLevel;
  min_aggregation_size?: number;
  metadata?: Record<string, unknown>;
}

/** Request to update a data asset */
export interface UpdateAssetRequest {
  owner: string;
  allowed_algorithms?: string[];
  allowed_compute_providers?: string[];
  privacy_level?: PrivacyLevel;
  min_aggregation_size?: number;
  metadata?: Record<string, unknown>;
}

/** Request to grant access */
export interface GrantAccessRequest {
  asset_id: string;
  owner: string;
  grantee: string;
  access_level: AccessLevel;
  allowed_algorithms?: string[];
  max_uses?: number;
  expires_in_hours?: number;
}

/** Request to register an algorithm */
export interface RegisterAlgorithmRequest {
  algorithm_type: ComputeAlgorithmType;
  name: string;
  code_hash: string;
  author?: string;
  description?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  privacy_preserving?: boolean;
}

/** Request to submit a compute job */
export interface SubmitJobRequest {
  asset_id: string;
  algorithm_id: string;
  access_token_id: string;
  requester: string;
  parameters?: Record<string, unknown>;
  privacy_level?: PrivacyLevel;
}

/** Response listing assets */
export interface AssetsResponse {
  count: number;
  assets: DataAsset[];
}

/** Response listing algorithms */
export interface AlgorithmsResponse {
  count: number;
  algorithms: ComputeAlgorithm[];
}

/** Response listing access tokens */
export interface AccessTokensResponse {
  count: number;
  tokens: AccessToken[];
}

/** Response listing jobs */
export interface JobsResponse {
  count: number;
  jobs: ComputeJob[];
}

/** Response listing events */
export interface ComputeEventsResponse {
  count: number;
  events: ComputeEvent[];
}

/** Compute service statistics */
export interface ComputeStatistics {
  assets: {
    total: number;
    active: number;
    by_type: Record<string, number>;
  };
  algorithms: {
    total: number;
    builtin: number;
    custom: number;
    by_type: Record<string, number>;
  };
  access_tokens: {
    total: number;
    valid: number;
  };
  jobs: {
    total: number;
    by_status: Record<string, number>;
    avg_compute_time_ms: number;
  };
  results: {
    total: number;
  };
  events: {
    total: number;
  };
}

// ============================================================================
// Client
// ============================================================================

/**
 * Client for compute-to-data operations
 *
 * @example
 * ```ts
 * // Register a data asset
 * const asset = await client.compute.registerAsset({
 *   asset_type: 'contract',
 *   owner: 'did:nlc:z6Mk...',
 *   name: 'My Contracts',
 *   data: contractData,
 *   privacy_level: 'aggregated'
 * });
 *
 * // Grant access to a compute provider
 * const token = await client.compute.grantAccess({
 *   asset_id: asset.asset_id,
 *   owner: 'did:nlc:z6Mk...',
 *   grantee: 'did:nlc:z6Mj...',
 *   access_level: 'compute_only'
 * });
 *
 * // Submit a compute job
 * const job = await client.compute.submitJob({
 *   asset_id: asset.asset_id,
 *   algorithm_id: 'builtin_count',
 *   access_token_id: token.token_id,
 *   requester: 'did:nlc:z6Mj...',
 *   parameters: { field: 'status', value: 'active' }
 * });
 *
 * // Get the result
 * const result = await client.compute.getJobResult(job.job_id, 'did:nlc:z6Mj...');
 * ```
 */
export class ComputeClient {
  constructor(private readonly http: HttpClient) {}

  // ===========================================================================
  // Data Asset Management
  // ===========================================================================

  /**
   * Register a new data asset for compute
   *
   * @param request - Asset registration options
   * @returns Registered asset info
   */
  async registerAsset(request: RegisterAssetRequest): Promise<DataAsset> {
    return this.http.post<DataAsset>('/compute/assets', request);
  }

  /**
   * Get a data asset by ID
   *
   * @param assetId - The asset ID
   * @returns Asset info (excludes actual data)
   */
  async getAsset(assetId: string): Promise<DataAsset> {
    return this.http.get<DataAsset>(`/compute/assets/${encodeURIComponent(assetId)}`);
  }

  /**
   * Update a data asset's configuration
   *
   * @param assetId - The asset ID
   * @param request - Update options
   * @returns Updated asset info
   */
  async updateAsset(assetId: string, request: UpdateAssetRequest): Promise<DataAsset> {
    return this.http.patch<DataAsset>(
      `/compute/assets/${encodeURIComponent(assetId)}`,
      request
    );
  }

  /**
   * Revoke a data asset
   *
   * @param assetId - The asset ID
   * @param owner - Asset owner (for authorization)
   * @returns Revocation result
   */
  async revokeAsset(
    assetId: string,
    owner: string
  ): Promise<{ asset_id: string; revoked: boolean }> {
    return this.http.post<{ asset_id: string; revoked: boolean }>(
      `/compute/assets/${encodeURIComponent(assetId)}/revoke`,
      { owner }
    );
  }

  /**
   * List data assets
   *
   * @param options - Filter options
   * @returns List of assets
   */
  async listAssets(options?: {
    owner?: string;
    asset_type?: DataAssetType;
    active_only?: boolean;
  }): Promise<AssetsResponse> {
    const params = new URLSearchParams();
    if (options?.owner) {
      params.set('owner', options.owner);
    }
    if (options?.asset_type) {
      params.set('asset_type', options.asset_type);
    }
    if (options?.active_only !== undefined) {
      params.set('active_only', String(options.active_only));
    }
    const query = params.toString();
    return this.http.get<AssetsResponse>(`/compute/assets${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Access Control
  // ===========================================================================

  /**
   * Grant access to a data asset
   *
   * @param request - Access grant options
   * @returns Access token info
   */
  async grantAccess(request: GrantAccessRequest): Promise<AccessToken> {
    return this.http.post<AccessToken>('/compute/access/grant', request);
  }

  /**
   * Revoke an access token
   *
   * @param tokenId - The token ID
   * @param owner - Asset owner (for authorization)
   * @returns Revocation result
   */
  async revokeAccess(
    tokenId: string,
    owner: string
  ): Promise<{ token_id: string; revoked: boolean }> {
    return this.http.post<{ token_id: string; revoked: boolean }>(
      `/compute/access/${encodeURIComponent(tokenId)}/revoke`,
      { owner }
    );
  }

  /**
   * List access tokens
   *
   * @param options - Filter options
   * @returns List of access tokens
   */
  async listAccessTokens(options?: {
    asset_id?: string;
    grantee?: string;
  }): Promise<AccessTokensResponse> {
    const params = new URLSearchParams();
    if (options?.asset_id) {
      params.set('asset_id', options.asset_id);
    }
    if (options?.grantee) {
      params.set('grantee', options.grantee);
    }
    const query = params.toString();
    return this.http.get<AccessTokensResponse>(`/compute/access${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Algorithm Management
  // ===========================================================================

  /**
   * Register a custom algorithm
   *
   * @param request - Algorithm registration options
   * @returns Registered algorithm info
   */
  async registerAlgorithm(request: RegisterAlgorithmRequest): Promise<ComputeAlgorithm> {
    return this.http.post<ComputeAlgorithm>('/compute/algorithms', request);
  }

  /**
   * Get an algorithm by ID
   *
   * @param algorithmId - The algorithm ID
   * @returns Algorithm info
   */
  async getAlgorithm(algorithmId: string): Promise<ComputeAlgorithm> {
    return this.http.get<ComputeAlgorithm>(
      `/compute/algorithms/${encodeURIComponent(algorithmId)}`
    );
  }

  /**
   * List available algorithms
   *
   * @param options - Filter options
   * @returns List of algorithms
   */
  async listAlgorithms(options?: {
    algorithm_type?: ComputeAlgorithmType;
    privacy_preserving_only?: boolean;
    audited_only?: boolean;
  }): Promise<AlgorithmsResponse> {
    const params = new URLSearchParams();
    if (options?.algorithm_type) {
      params.set('algorithm_type', options.algorithm_type);
    }
    if (options?.privacy_preserving_only !== undefined) {
      params.set('privacy_preserving_only', String(options.privacy_preserving_only));
    }
    if (options?.audited_only !== undefined) {
      params.set('audited_only', String(options.audited_only));
    }
    const query = params.toString();
    return this.http.get<AlgorithmsResponse>(`/compute/algorithms${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Compute Job Execution
  // ===========================================================================

  /**
   * Submit a compute job
   *
   * @param request - Job submission options
   * @returns Job info with status
   */
  async submitJob(request: SubmitJobRequest): Promise<ComputeJob> {
    return this.http.post<ComputeJob>('/compute/jobs', request);
  }

  /**
   * Get a compute job by ID
   *
   * @param jobId - The job ID
   * @returns Job info with status
   */
  async getJob(jobId: string): Promise<ComputeJob> {
    return this.http.get<ComputeJob>(`/compute/jobs/${encodeURIComponent(jobId)}`);
  }

  /**
   * Get the result of a completed compute job
   *
   * @param jobId - The job ID
   * @param requester - Requester DID (for authorization)
   * @returns Privacy-filtered result
   */
  async getJobResult(jobId: string, requester: string): Promise<ComputeResult> {
    return this.http.get<ComputeResult>(
      `/compute/jobs/${encodeURIComponent(jobId)}/result?requester=${encodeURIComponent(requester)}`
    );
  }

  /**
   * List compute jobs
   *
   * @param options - Filter options
   * @returns List of jobs
   */
  async listJobs(options?: {
    requester?: string;
    asset_id?: string;
    status?: JobStatus;
  }): Promise<JobsResponse> {
    const params = new URLSearchParams();
    if (options?.requester) {
      params.set('requester', options.requester);
    }
    if (options?.asset_id) {
      params.set('asset_id', options.asset_id);
    }
    if (options?.status) {
      params.set('status', options.status);
    }
    const query = params.toString();
    return this.http.get<JobsResponse>(`/compute/jobs${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Statistics and Events
  // ===========================================================================

  /**
   * Get compute service statistics
   *
   * @returns Comprehensive statistics
   */
  async getStatistics(): Promise<ComputeStatistics> {
    return this.http.get<ComputeStatistics>('/compute/statistics');
  }

  /**
   * Get compute event log
   *
   * @param options - Filter options
   * @returns List of events
   */
  async getEvents(options?: {
    limit?: number;
    event_type?: ComputeEventType;
  }): Promise<ComputeEventsResponse> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    if (options?.event_type) {
      params.set('event_type', options.event_type);
    }
    const query = params.toString();
    return this.http.get<ComputeEventsResponse>(`/compute/events${query ? `?${query}` : ''}`);
  }

  // ===========================================================================
  // Supported Types
  // ===========================================================================

  /**
   * Get supported data asset types
   *
   * @returns List of supported asset types
   */
  async getAssetTypes(): Promise<{ types: DataAssetType[] }> {
    return this.http.get<{ types: DataAssetType[] }>('/compute/types/assets');
  }

  /**
   * Get supported algorithm types
   *
   * @returns List of supported algorithm types
   */
  async getAlgorithmTypes(): Promise<{ types: ComputeAlgorithmType[] }> {
    return this.http.get<{ types: ComputeAlgorithmType[] }>('/compute/types/algorithms');
  }

  /**
   * Get supported access levels
   *
   * @returns List of supported access levels
   */
  async getAccessLevels(): Promise<{ levels: AccessLevel[] }> {
    return this.http.get<{ levels: AccessLevel[] }>('/compute/types/access_levels');
  }

  /**
   * Get supported privacy levels
   *
   * @returns List of supported privacy levels
   */
  async getPrivacyLevels(): Promise<{ levels: PrivacyLevel[] }> {
    return this.http.get<{ levels: PrivacyLevel[] }>('/compute/types/privacy_levels');
  }

  /**
   * Get supported job statuses
   *
   * @returns List of supported job statuses
   */
  async getJobStatuses(): Promise<{ statuses: JobStatus[] }> {
    return this.http.get<{ statuses: JobStatus[] }>('/compute/types/job_statuses');
  }
}
