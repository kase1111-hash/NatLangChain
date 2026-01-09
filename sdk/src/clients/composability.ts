/**
 * Data Composability Client
 *
 * Cross-application data sharing and composability system inspired by
 * Ceramic Network. Enables contracts and entries to be shared, linked,
 * and composed across different applications.
 */

import { HttpClient } from '../utils/client';

// ============================================================================
// Types
// ============================================================================

/** Stream types */
export type StreamType =
  | 'tile'
  | 'model'
  | 'model_instance'
  | 'caip10_link'
  | 'contract_stream'
  | 'entry_stream';

/** Commit types */
export type CommitType = 'genesis' | 'signed' | 'anchor' | 'time';

/** Stream states */
export type StreamState = 'pending' | 'anchored' | 'published' | 'archived';

/** Schema types */
export type SchemaType = 'json-schema' | 'graphql' | 'protobuf' | 'natlangchain';

/** Link types */
export type LinkType = 'reference' | 'embed' | 'derive' | 'respond' | 'extend';

/** Stream metadata */
export interface StreamMetadata {
  controllers: string[];
  family?: string;
  tags: string[];
  schema_id?: string;
  model_id?: string;
  application_id?: string;
  unique?: string;
}

/** Stream commit */
export interface StreamCommit {
  commit_id: string;
  stream_id: string;
  commit_type: CommitType;
  data: Record<string, unknown>;
  prev_commit_id?: string;
  controller: string;
  timestamp: string;
  signature?: string;
  anchor_proof?: Record<string, unknown>;
}

/** Stream */
export interface Stream {
  stream_id: string;
  stream_type: StreamType;
  content: Record<string, unknown>;
  metadata: StreamMetadata;
  state: StreamState;
  tip: string;
  commit_count: number;
  created_at: string;
  updated_at: string;
  anchored_at?: string;
}

/** Cross-application link */
export interface CrossAppLink {
  link_id: string;
  source_stream_id: string;
  target_stream_id: string;
  link_type: LinkType;
  source_app_id: string;
  target_app_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
  created_by?: string;
}

/** Schema */
export interface Schema {
  schema_id: string;
  name: string;
  version: string;
  schema_type: SchemaType;
  definition: Record<string, unknown>;
  description?: string;
  author?: string;
  created_at: string;
  dependencies: string[];
}

/** Application */
export interface Application {
  app_id: string;
  name: string;
  description?: string;
  controllers: string[];
  schemas: string[];
  models: string[];
  endpoints: Record<string, string>;
  created_at: string;
  stream_count: number;
}

/** Request to create a stream */
export interface CreateStreamRequest {
  stream_type: StreamType;
  content: Record<string, unknown>;
  controller: string;
  schema_id?: string;
  app_id?: string;
  tags?: string[];
  family?: string;
}

/** Response from creating a stream */
export interface CreateStreamResponse {
  stream_id: string;
  commit_id: string;
  stream: Stream;
}

/** Request to update a stream */
export interface UpdateStreamRequest {
  content: Record<string, unknown>;
  controller: string;
  merge?: boolean;
}

/** Response from updating a stream */
export interface UpdateStreamResponse {
  stream_id: string;
  commit_id: string;
  content: Record<string, unknown>;
}

/** Request to anchor a stream */
export interface AnchorStreamRequest {
  anchor_proof: Record<string, unknown>;
}

/** Request to register a schema */
export interface RegisterSchemaRequest {
  name: string;
  version: string;
  schema_type: SchemaType;
  definition: Record<string, unknown>;
  description?: string;
  author?: string;
  dependencies?: string[];
}

/** Request to register an application */
export interface RegisterAppRequest {
  name: string;
  controllers: string[];
  description?: string;
  endpoints?: Record<string, string>;
}

/** Request to create a link */
export interface CreateLinkRequest {
  source_stream_id: string;
  target_stream_id: string;
  link_type: LinkType;
  created_by?: string;
  metadata?: Record<string, unknown>;
}

/** Request to create a contract stream */
export interface CreateContractStreamRequest {
  entry_hash: string;
  block_index: number;
  entry_index: number;
  content: string;
  intent: string;
  author: string;
  parties: string[];
  terms?: Record<string, unknown>;
  controller?: string;
  app_id?: string;
}

/** Export request */
export interface ExportRequest {
  stream_ids: string[];
  include_schemas?: boolean;
  include_links?: boolean;
  exported_by?: string;
}

/** Export package */
export interface ExportPackage {
  package_id: string;
  stream_count: number;
  schema_count: number;
  link_count: number;
  source_app_id: string;
  exported_at: string;
  exported_by?: string;
  format_version: string;
  streams: Array<Record<string, unknown>>;
  schemas: Array<Record<string, unknown>>;
  links: Array<Record<string, unknown>>;
}

/** Import request */
export interface ImportRequest {
  package: ExportPackage;
  target_app_id?: string;
  controller?: string;
  remap_ids?: boolean;
}

/** Import result */
export interface ImportResult {
  streams_imported: string[];
  schemas_imported: string[];
  links_imported: string[];
  id_mapping: Record<string, string>;
}

/** Query streams options */
export interface QueryStreamsOptions {
  stream_type?: StreamType;
  app_id?: string;
  schema_id?: string;
  controller?: string;
  tags?: string[];
  family?: string;
  limit?: number;
}

/** Streams query response */
export interface StreamsResponse {
  count: number;
  streams: Stream[];
}

/** Schemas response */
export interface SchemasResponse {
  count: number;
  schemas: Schema[];
}

/** Applications response */
export interface ApplicationsResponse {
  count: number;
  applications: Application[];
}

/** Links response */
export interface LinksResponse {
  count: number;
  links: CrossAppLink[];
}

/** Linked streams response */
export interface LinkedStreamsResponse {
  stream_id: string;
  direction: string;
  count: number;
  linked_streams: Stream[];
}

/** Stream history response */
export interface StreamHistoryResponse {
  stream_id: string;
  commits: StreamCommit[];
}

/** Composability statistics */
export interface ComposabilityStatistics {
  streams: {
    total: number;
    by_type: Record<StreamType, number>;
    by_state: Record<StreamState, number>;
  };
  schemas: {
    total: number;
  };
  applications: {
    total: number;
  };
  links: {
    total: number;
    by_type: Record<LinkType, number>;
  };
  events: {
    total: number;
  };
}

/** Composability event */
export interface ComposabilityEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

/** Events response */
export interface ComposabilityEventsResponse {
  count: number;
  events: ComposabilityEvent[];
}

// ============================================================================
// Client
// ============================================================================

/**
 * Client for data composability operations
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
 * const link = await client.composability.createLink({
 *   source_stream_id: stream.stream_id,
 *   target_stream_id: 'kjzl_...',
 *   link_type: 'reference'
 * });
 *
 * // Export for sharing
 * const pkg = await client.composability.export({
 *   stream_ids: [stream.stream_id],
 *   include_schemas: true
 * });
 *
 * // Import from another app
 * const result = await client.composability.import({
 *   package: pkg,
 *   target_app_id: 'app_...'
 * });
 * ```
 */
export class ComposabilityClient {
  constructor(private readonly http: HttpClient) {}

  // ===========================================================================
  // Stream Management
  // ===========================================================================

  /**
   * Create a new composable stream
   *
   * @param request - Stream creation options
   * @returns Created stream info
   */
  async createStream(request: CreateStreamRequest): Promise<CreateStreamResponse> {
    return this.http.post<CreateStreamResponse>('/composability/streams', request);
  }

  /**
   * Get a stream by ID
   *
   * @param streamId - The stream ID
   * @returns Stream data
   */
  async getStream(streamId: string): Promise<Stream> {
    return this.http.get<Stream>(`/composability/streams/${encodeURIComponent(streamId)}`);
  }

  /**
   * Update a stream's content
   *
   * @param streamId - The stream ID
   * @param request - Update options
   * @returns Update result
   */
  async updateStream(
    streamId: string,
    request: UpdateStreamRequest
  ): Promise<UpdateStreamResponse> {
    return this.http.patch<UpdateStreamResponse>(
      `/composability/streams/${encodeURIComponent(streamId)}`,
      request
    );
  }

  /**
   * Get commit history for a stream
   *
   * @param streamId - The stream ID
   * @returns Commit history
   */
  async getStreamHistory(streamId: string): Promise<StreamHistoryResponse> {
    return this.http.get<StreamHistoryResponse>(
      `/composability/streams/${encodeURIComponent(streamId)}/history`
    );
  }

  /**
   * Get stream content at a specific commit
   *
   * @param streamId - The stream ID
   * @param commitId - The commit ID
   * @returns Stream content at commit
   */
  async getStreamAtCommit(
    streamId: string,
    commitId: string
  ): Promise<{ stream_id: string; commit_id: string; content: Record<string, unknown> }> {
    return this.http.get(
      `/composability/streams/${encodeURIComponent(streamId)}/at/${encodeURIComponent(commitId)}`
    );
  }

  /**
   * Anchor a stream to external blockchain
   *
   * @param streamId - The stream ID
   * @param request - Anchor options
   * @returns Anchor result
   */
  async anchorStream(
    streamId: string,
    request: AnchorStreamRequest
  ): Promise<{ stream_id: string; state: string; commit_id: string }> {
    return this.http.post(
      `/composability/streams/${encodeURIComponent(streamId)}/anchor`,
      request
    );
  }

  /**
   * Make a stream publicly accessible
   *
   * @param streamId - The stream ID
   * @returns Publish result
   */
  async publishStream(
    streamId: string
  ): Promise<{ stream_id: string; state: string }> {
    return this.http.post(
      `/composability/streams/${encodeURIComponent(streamId)}/publish`,
      {}
    );
  }

  /**
   * Query streams with filters
   *
   * @param options - Query options
   * @returns Matching streams
   */
  async queryStreams(options?: QueryStreamsOptions): Promise<StreamsResponse> {
    const params = new URLSearchParams();
    if (options?.stream_type) params.set('stream_type', options.stream_type);
    if (options?.app_id) params.set('app_id', options.app_id);
    if (options?.schema_id) params.set('schema_id', options.schema_id);
    if (options?.controller) params.set('controller', options.controller);
    if (options?.tags) params.set('tags', options.tags.join(','));
    if (options?.family) params.set('family', options.family);
    if (options?.limit !== undefined) params.set('limit', String(options.limit));
    const query = params.toString();
    return this.http.get<StreamsResponse>(
      `/composability/streams${query ? `?${query}` : ''}`
    );
  }

  // ===========================================================================
  // Schema Management
  // ===========================================================================

  /**
   * Register a new schema
   *
   * @param request - Schema registration options
   * @returns Registered schema
   */
  async registerSchema(request: RegisterSchemaRequest): Promise<Schema> {
    return this.http.post<Schema>('/composability/schemas', request);
  }

  /**
   * Get a schema by ID
   *
   * @param schemaId - The schema ID
   * @returns Schema data
   */
  async getSchema(schemaId: string): Promise<Schema> {
    return this.http.get<Schema>(
      `/composability/schemas/${encodeURIComponent(schemaId)}`
    );
  }

  /**
   * List schemas with optional filters
   *
   * @param options - Filter options
   * @returns List of schemas
   */
  async listSchemas(options?: {
    schema_type?: SchemaType;
    name?: string;
  }): Promise<SchemasResponse> {
    const params = new URLSearchParams();
    if (options?.schema_type) params.set('schema_type', options.schema_type);
    if (options?.name) params.set('name', options.name);
    const query = params.toString();
    return this.http.get<SchemasResponse>(
      `/composability/schemas${query ? `?${query}` : ''}`
    );
  }

  // ===========================================================================
  // Application Management
  // ===========================================================================

  /**
   * Register a new application
   *
   * @param request - Application registration options
   * @returns Registered application
   */
  async registerApp(request: RegisterAppRequest): Promise<Application> {
    return this.http.post<Application>('/composability/apps', request);
  }

  /**
   * Get an application by ID
   *
   * @param appId - The application ID
   * @returns Application data
   */
  async getApp(appId: string): Promise<Application> {
    return this.http.get<Application>(
      `/composability/apps/${encodeURIComponent(appId)}`
    );
  }

  /**
   * List all registered applications
   *
   * @returns List of applications
   */
  async listApps(): Promise<ApplicationsResponse> {
    return this.http.get<ApplicationsResponse>('/composability/apps');
  }

  // ===========================================================================
  // Cross-Application Linking
  // ===========================================================================

  /**
   * Create a link between streams
   *
   * @param request - Link creation options
   * @returns Created link
   */
  async createLink(request: CreateLinkRequest): Promise<CrossAppLink> {
    return this.http.post<CrossAppLink>('/composability/links', request);
  }

  /**
   * Get links with optional filters
   *
   * @param options - Filter options
   * @returns List of links
   */
  async getLinks(options?: {
    stream_id?: string;
    link_type?: LinkType;
    app_id?: string;
  }): Promise<LinksResponse> {
    const params = new URLSearchParams();
    if (options?.stream_id) params.set('stream_id', options.stream_id);
    if (options?.link_type) params.set('link_type', options.link_type);
    if (options?.app_id) params.set('app_id', options.app_id);
    const query = params.toString();
    return this.http.get<LinksResponse>(
      `/composability/links${query ? `?${query}` : ''}`
    );
  }

  /**
   * Get streams linked to a given stream
   *
   * @param streamId - The stream ID
   * @param direction - Link direction (outgoing, incoming, both)
   * @returns Linked streams
   */
  async getLinkedStreams(
    streamId: string,
    direction: 'outgoing' | 'incoming' | 'both' = 'both'
  ): Promise<LinkedStreamsResponse> {
    return this.http.get<LinkedStreamsResponse>(
      `/composability/streams/${encodeURIComponent(streamId)}/linked?direction=${direction}`
    );
  }

  // ===========================================================================
  // Import/Export
  // ===========================================================================

  /**
   * Export streams as a package
   *
   * @param request - Export options
   * @returns Export package
   */
  async export(request: ExportRequest): Promise<ExportPackage> {
    return this.http.post<ExportPackage>('/composability/export', request);
  }

  /**
   * Import streams from a package
   *
   * @param request - Import options
   * @returns Import result
   */
  async import(request: ImportRequest): Promise<ImportResult> {
    return this.http.post<ImportResult>('/composability/import', request);
  }

  // ===========================================================================
  // Contract Streams
  // ===========================================================================

  /**
   * Create a composable stream from a contract entry
   *
   * @param request - Contract stream options
   * @returns Created stream info
   */
  async createContractStream(
    request: CreateContractStreamRequest
  ): Promise<CreateStreamResponse> {
    return this.http.post<CreateStreamResponse>(
      '/composability/streams/contract',
      request
    );
  }

  // ===========================================================================
  // Statistics and Types
  // ===========================================================================

  /**
   * Get composability service statistics
   *
   * @returns Comprehensive statistics
   */
  async getStatistics(): Promise<ComposabilityStatistics> {
    return this.http.get<ComposabilityStatistics>('/composability/statistics');
  }

  /**
   * Get composability event log
   *
   * @param options - Filter options
   * @returns List of events
   */
  async getEvents(options?: {
    limit?: number;
    event_type?: string;
  }): Promise<ComposabilityEventsResponse> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) params.set('limit', String(options.limit));
    if (options?.event_type) params.set('event_type', options.event_type);
    const query = params.toString();
    return this.http.get<ComposabilityEventsResponse>(
      `/composability/events${query ? `?${query}` : ''}`
    );
  }

  /**
   * Get supported stream types
   *
   * @returns List of stream types
   */
  async getStreamTypes(): Promise<{ types: StreamType[] }> {
    return this.http.get<{ types: StreamType[] }>('/composability/types/streams');
  }

  /**
   * Get supported link types
   *
   * @returns List of link types
   */
  async getLinkTypes(): Promise<{ types: LinkType[] }> {
    return this.http.get<{ types: LinkType[] }>('/composability/types/links');
  }

  /**
   * Get supported schema types
   *
   * @returns List of schema types
   */
  async getSchemaTypes(): Promise<{ types: SchemaType[] }> {
    return this.http.get<{ types: SchemaType[] }>('/composability/types/schemas');
  }
}
