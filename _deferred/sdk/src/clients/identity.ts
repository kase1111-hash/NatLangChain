/**
 * DID Identity Client
 *
 * W3C-compliant Decentralized Identifier (DID) management for NatLangChain.
 * Provides identity creation, resolution, key management, and verification.
 */

import { HttpClient } from '../utils/client';

// ============================================================================
// Types
// ============================================================================

/** Supported verification method types */
export type VerificationMethodType =
  | 'Ed25519VerificationKey2020'
  | 'EcdsaSecp256k1VerificationKey2019'
  | 'X25519KeyAgreementKey2020'
  | 'JsonWebKey2020';

/** Verification relationships */
export type VerificationRelationship =
  | 'authentication'
  | 'assertionMethod'
  | 'keyAgreement'
  | 'capabilityInvocation'
  | 'capabilityDelegation';

/** Common service endpoint types */
export type ServiceType =
  | 'NatLangChainProfile'
  | 'NatLangChainMessaging'
  | 'LinkedDomains'
  | 'DIDCommMessaging'
  | 'CredentialRegistry';

/** DID document status */
export type DIDStatus = 'active' | 'deactivated' | 'suspended';

/** Verification method in a DID document */
export interface VerificationMethod {
  id: string;
  type: VerificationMethodType;
  controller: string;
  publicKeyMultibase?: string;
  publicKeyJwk?: Record<string, unknown>;
}

/** Service endpoint in a DID document */
export interface ServiceEndpoint {
  id: string;
  type: string;
  serviceEndpoint: string | string[] | Record<string, unknown>;
  description?: string;
}

/** W3C DID Document */
export interface DIDDocument {
  '@context': string[];
  id: string;
  controller?: string | string[];
  alsoKnownAs?: string[];
  verificationMethod?: VerificationMethod[];
  authentication?: string[];
  assertionMethod?: string[];
  keyAgreement?: string[];
  capabilityInvocation?: string[];
  capabilityDelegation?: string[];
  service?: ServiceEndpoint[];
}

/** DID Resolution metadata */
export interface DIDDocumentMetadata {
  created?: string;
  updated?: string;
  deactivated?: boolean;
  versionId?: number;
}

/** DID Resolution result */
export interface DIDResolutionResult {
  didDocument: DIDDocument | null;
  didDocumentMetadata: DIDDocumentMetadata;
  didResolutionMetadata: {
    contentType?: string;
    error?: string;
    message?: string;
  };
}

/** Request to create a DID */
export interface CreateDIDRequest {
  display_name?: string;
  email?: string;
  profile_data?: Record<string, unknown>;
  also_known_as?: string[];
  services?: Array<{
    type: string;
    endpoint: string;
    description?: string;
  }>;
}

/** Response from creating a DID */
export interface CreateDIDResponse {
  did: string;
  document: DIDDocument;
  private_keys: Record<string, string>;
  warning: string;
}

/** Request to update a DID */
export interface UpdateDIDRequest {
  also_known_as?: string[];
  controller?: string | string[];
  authorized_by?: string;
}

/** Response from updating a DID */
export interface UpdateDIDResponse {
  did: string;
  updated: string;
  changes: string[];
}

/** Request to add a key */
export interface AddKeyRequest {
  type?: VerificationMethodType;
  relationships?: VerificationRelationship[];
  expires_in_days?: number;
}

/** Response from adding a key */
export interface AddKeyResponse {
  key_id: string;
  type: VerificationMethodType;
  public_key: string;
  private_key: string;
  relationships: VerificationRelationship[];
  expires_at?: string;
  warning: string;
}

/** Response from revoking a key */
export interface RevokeKeyResponse {
  key_id: string;
  revoked_at: string;
}

/** Request to rotate a key */
export interface RotateKeyRequest {
  reason?: string;
  grace_period_days?: number;
}

/** Response from rotating a key */
export interface RotateKeyResponse {
  rotation_id: string;
  old_key: {
    id: string;
    expires_at: string;
  };
  new_key: AddKeyResponse;
  grace_period_days: number;
}

/** Request to add a service */
export interface AddServiceRequest {
  type: string;
  endpoint: string | string[] | Record<string, unknown>;
  description?: string;
}

/** Response from adding a service */
export interface AddServiceResponse {
  service_id: string;
  service: ServiceEndpoint;
}

/** Delegation between DIDs */
export interface Delegation {
  id: string;
  delegator: string;
  delegate: string;
  capabilities: string[];
  constraints: Record<string, unknown>;
  created_at: string;
  expires_at?: string;
  revoked_at?: string;
  valid: boolean;
}

/** Request to grant delegation */
export interface GrantDelegationRequest {
  delegator: string;
  delegate: string;
  capabilities: string[];
  constraints?: Record<string, unknown>;
  expires_in_days?: number;
}

/** Response from listing delegations */
export interface DelegationsResponse {
  did: string;
  count: number;
  delegations: Delegation[];
}

/** Request to link an author */
export interface LinkAuthorRequest {
  author: string;
  did: string;
}

/** Response from resolving an author */
export interface ResolveAuthorResponse {
  author: string;
  did: string;
}

/** Request to verify authorship */
export interface VerifyAuthorshipRequest {
  entry_hash: string;
  claimed_author: string;
  signature?: string;
}

/** Response from verifying authorship */
export interface VerifyAuthorshipResponse {
  verified: boolean;
  did?: string;
  verification_method?: string;
  entry_hash?: string;
  reason?: string;
  note?: string;
}

/** Request to verify authentication */
export interface VerifyAuthenticationRequest {
  did: string;
  key_id: string;
}

/** Response from verifying authentication */
export interface VerifyAuthenticationResponse {
  valid: boolean;
  reason: string;
  did: string;
  key_id: string;
}

/** Identity service statistics */
export interface IdentityStatistics {
  registry: {
    total_dids: number;
    status_distribution: Record<DIDStatus, number>;
    total_verification_methods: number;
    total_services: number;
    delegations: {
      total: number;
      valid: number;
      revoked: number;
    };
    total_events: number;
    rotation_history_count: number;
  };
  author_mappings: number;
}

/** DID event */
export interface DIDEvent {
  event_id: string;
  event_type: string;
  did: string;
  timestamp: string;
  data: Record<string, unknown>;
  signature?: string;
}

/** Key rotation record */
export interface KeyRotationRecord {
  rotation_id: string;
  did: string;
  old_key_id: string;
  new_key_id: string;
  rotated_at: string;
  reason?: string;
  grace_period_ends?: string;
}

/** DID history response */
export interface DIDHistoryResponse {
  did: string;
  events: DIDEvent[];
  key_rotations: KeyRotationRecord[];
}

/** Events response */
export interface IdentityEventsResponse {
  count: number;
  events: DIDEvent[];
}

/** Deactivation response */
export interface DeactivateResponse {
  did: string;
  status: 'deactivated';
  deactivated_at: string;
}

// ============================================================================
// Client
// ============================================================================

/**
 * Client for DID identity operations
 *
 * @example
 * ```ts
 * // Create a new identity
 * const identity = await client.identity.createDID({
 *   display_name: 'Alice',
 *   email: 'alice@example.com'
 * });
 * console.log('Created DID:', identity.did);
 * // IMPORTANT: Store private_keys securely!
 *
 * // Resolve a DID
 * const resolved = await client.identity.resolve(identity.did);
 *
 * // Add a new key
 * const key = await client.identity.addKey(identity.did, {
 *   type: 'Ed25519VerificationKey2020',
 *   relationships: ['authentication']
 * });
 *
 * // Rotate a key
 * const rotation = await client.identity.rotateKey(identity.did, 'key-1', {
 *   reason: 'Scheduled rotation'
 * });
 *
 * // Verify authorship
 * const verification = await client.identity.verifyAuthorship({
 *   entry_hash: 'abc123...',
 *   claimed_author: 'alice@example.com'
 * });
 * ```
 */
export class IdentityClient {
  constructor(private readonly http: HttpClient) {}

  // ===========================================================================
  // DID Management
  // ===========================================================================

  /**
   * Create a new DID with document
   *
   * @param request - DID creation options
   * @returns Created DID, document, and private keys
   *
   * @warning Store the returned private_keys securely! They cannot be recovered.
   */
  async createDID(request?: CreateDIDRequest): Promise<CreateDIDResponse> {
    return this.http.post<CreateDIDResponse>('/identity/did', request || {});
  }

  /**
   * Resolve a DID to its document
   *
   * @param did - The DID to resolve
   * @returns DID Resolution result
   */
  async resolve(did: string): Promise<DIDResolutionResult> {
    return this.http.get<DIDResolutionResult>(`/identity/did/${encodeURIComponent(did)}`);
  }

  /**
   * Update a DID document
   *
   * @param did - The DID to update
   * @param request - Update options
   * @returns Update result
   */
  async updateDID(did: string, request: UpdateDIDRequest): Promise<UpdateDIDResponse> {
    return this.http.patch<UpdateDIDResponse>(
      `/identity/did/${encodeURIComponent(did)}`,
      request
    );
  }

  /**
   * Deactivate a DID (permanent)
   *
   * @param did - The DID to deactivate
   * @returns Deactivation result
   */
  async deactivate(did: string): Promise<DeactivateResponse> {
    return this.http.post<DeactivateResponse>(
      `/identity/did/${encodeURIComponent(did)}/deactivate`,
      {}
    );
  }

  // ===========================================================================
  // Key Management
  // ===========================================================================

  /**
   * Add a new verification method (key) to a DID
   *
   * @param did - The DID
   * @param request - Key options
   * @returns New key info including private key
   *
   * @warning Store the returned private_key securely!
   */
  async addKey(did: string, request?: AddKeyRequest): Promise<AddKeyResponse> {
    return this.http.post<AddKeyResponse>(
      `/identity/did/${encodeURIComponent(did)}/keys`,
      request || {}
    );
  }

  /**
   * Revoke a verification method (key)
   *
   * @param did - The DID
   * @param keyId - The key ID (e.g., "key-1")
   * @returns Revocation result
   */
  async revokeKey(did: string, keyId: string): Promise<RevokeKeyResponse> {
    return this.http.post<RevokeKeyResponse>(
      `/identity/did/${encodeURIComponent(did)}/keys/${encodeURIComponent(keyId)}/revoke`,
      {}
    );
  }

  /**
   * Rotate a key - create new key and schedule old for revocation
   *
   * @param did - The DID
   * @param keyId - The key ID to rotate
   * @param request - Rotation options
   * @returns Rotation result with new key info
   */
  async rotateKey(
    did: string,
    keyId: string,
    request?: RotateKeyRequest
  ): Promise<RotateKeyResponse> {
    return this.http.post<RotateKeyResponse>(
      `/identity/did/${encodeURIComponent(did)}/keys/${encodeURIComponent(keyId)}/rotate`,
      request || {}
    );
  }

  // ===========================================================================
  // Service Management
  // ===========================================================================

  /**
   * Add a service endpoint to a DID
   *
   * @param did - The DID
   * @param request - Service options
   * @returns Service info
   */
  async addService(did: string, request: AddServiceRequest): Promise<AddServiceResponse> {
    return this.http.post<AddServiceResponse>(
      `/identity/did/${encodeURIComponent(did)}/services`,
      request
    );
  }

  /**
   * Remove a service endpoint from a DID
   *
   * @param did - The DID
   * @param serviceId - The service ID
   * @returns Removal result
   */
  async removeService(
    did: string,
    serviceId: string
  ): Promise<{ service_id: string; removed: boolean }> {
    return this.http.delete<{ service_id: string; removed: boolean }>(
      `/identity/did/${encodeURIComponent(did)}/services/${encodeURIComponent(serviceId)}`
    );
  }

  // ===========================================================================
  // Delegations
  // ===========================================================================

  /**
   * Grant delegation from one DID to another
   *
   * @param request - Delegation options
   * @returns Delegation info
   */
  async grantDelegation(request: GrantDelegationRequest): Promise<Delegation> {
    return this.http.post<Delegation>('/identity/delegations', request);
  }

  /**
   * Revoke a delegation
   *
   * @param delegationId - The delegation ID
   * @returns Revocation result
   */
  async revokeDelegation(
    delegationId: string
  ): Promise<{ delegation_id: string; revoked_at: string }> {
    return this.http.post<{ delegation_id: string; revoked_at: string }>(
      `/identity/delegations/${encodeURIComponent(delegationId)}/revoke`,
      {}
    );
  }

  /**
   * Get delegations for a DID
   *
   * @param did - The DID
   * @param options - Filter options
   * @returns List of delegations
   */
  async getDelegations(
    did: string,
    options?: {
      as_delegator?: boolean;
      as_delegate?: boolean;
      valid_only?: boolean;
    }
  ): Promise<DelegationsResponse> {
    const params = new URLSearchParams();
    if (options?.as_delegator !== undefined) {
      params.set('as_delegator', String(options.as_delegator));
    }
    if (options?.as_delegate !== undefined) {
      params.set('as_delegate', String(options.as_delegate));
    }
    if (options?.valid_only !== undefined) {
      params.set('valid_only', String(options.valid_only));
    }
    const query = params.toString();
    return this.http.get<DelegationsResponse>(
      `/identity/did/${encodeURIComponent(did)}/delegations${query ? `?${query}` : ''}`
    );
  }

  // ===========================================================================
  // Author Linking and Verification
  // ===========================================================================

  /**
   * Link an author identifier to a DID
   *
   * @param request - Link options
   * @returns Link result
   */
  async linkAuthor(request: LinkAuthorRequest): Promise<{ author: string; did: string }> {
    return this.http.post<{ author: string; did: string }>('/identity/link', request);
  }

  /**
   * Resolve an author identifier to a DID
   *
   * @param author - Author identifier
   * @returns DID if found
   */
  async resolveAuthor(author: string): Promise<ResolveAuthorResponse> {
    return this.http.get<ResolveAuthorResponse>(
      `/identity/resolve/${encodeURIComponent(author)}`
    );
  }

  /**
   * Verify entry authorship
   *
   * @param request - Verification options
   * @returns Verification result
   */
  async verifyAuthorship(request: VerifyAuthorshipRequest): Promise<VerifyAuthorshipResponse> {
    return this.http.post<VerifyAuthorshipResponse>('/identity/verify', request);
  }

  /**
   * Verify that a key can authenticate for a DID
   *
   * @param request - Verification options
   * @returns Authentication verification result
   */
  async verifyAuthentication(
    request: VerifyAuthenticationRequest
  ): Promise<VerifyAuthenticationResponse> {
    return this.http.post<VerifyAuthenticationResponse>('/identity/authenticate', request);
  }

  // ===========================================================================
  // Statistics and History
  // ===========================================================================

  /**
   * Get identity service statistics
   *
   * @returns Comprehensive statistics
   */
  async getStatistics(): Promise<IdentityStatistics> {
    return this.http.get<IdentityStatistics>('/identity/statistics');
  }

  /**
   * Get DID event log
   *
   * @param options - Filter options
   * @returns List of events
   */
  async getEvents(options?: {
    limit?: number;
    did?: string;
    event_type?: string;
  }): Promise<IdentityEventsResponse> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) {
      params.set('limit', String(options.limit));
    }
    if (options?.did) {
      params.set('did', options.did);
    }
    if (options?.event_type) {
      params.set('event_type', options.event_type);
    }
    const query = params.toString();
    return this.http.get<IdentityEventsResponse>(
      `/identity/events${query ? `?${query}` : ''}`
    );
  }

  /**
   * Get event history for a specific DID
   *
   * @param did - The DID
   * @returns Event history
   */
  async getHistory(did: string): Promise<DIDHistoryResponse> {
    return this.http.get<DIDHistoryResponse>(
      `/identity/did/${encodeURIComponent(did)}/history`
    );
  }

  // ===========================================================================
  // Supported Types
  // ===========================================================================

  /**
   * Get supported verification method types
   *
   * @returns List of supported key types
   */
  async getKeyTypes(): Promise<{ types: VerificationMethodType[] }> {
    return this.http.get<{ types: VerificationMethodType[] }>('/identity/types/keys');
  }

  /**
   * Get supported verification relationships
   *
   * @returns List of supported relationships
   */
  async getRelationshipTypes(): Promise<{ relationships: VerificationRelationship[] }> {
    return this.http.get<{ relationships: VerificationRelationship[] }>(
      '/identity/types/relationships'
    );
  }

  /**
   * Get common service endpoint types
   *
   * @returns List of common service types
   */
  async getServiceTypes(): Promise<{ types: ServiceType[] }> {
    return this.http.get<{ types: ServiceType[] }>('/identity/types/services');
  }
}
