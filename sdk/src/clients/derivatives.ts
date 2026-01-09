/**
 * Derivatives Client - Intent Evolution Tracking
 *
 * Handles derivative/lineage operations:
 * - Get derivatives of an entry
 * - Get lineage/ancestry of an entry
 * - Get complete derivation tree
 * - Validate derivative references
 */

import { HttpClient } from '../utils/client';
import type { Entry } from '../types';

/** Valid derivative types */
export type DerivativeType =
  | 'amendment'
  | 'extension'
  | 'response'
  | 'revision'
  | 'reference'
  | 'fulfillment';

/** Parent reference for derivative entries */
export interface ParentRef {
  block_index: number;
  entry_index: number;
  relationship?: string;
}

/** Derivative entry reference */
export interface DerivativeRef {
  block_index: number;
  entry_index: number;
  derivative_type: DerivativeType;
  relationship: string;
  registered_at: number;
  depth?: number;
  entry?: Entry;
}

/** Lineage/ancestor reference */
export interface LineageRef {
  block_index: number;
  entry_index: number;
  relationship: string;
  depth?: number;
  entry?: Entry;
}

/** Derivatives response */
export interface DerivativesResponse {
  parent: {
    block_index: number;
    entry_index: number;
  };
  derivative_count: number;
  recursive: boolean;
  derivatives: DerivativeRef[];
}

/** Lineage response */
export interface LineageResponse {
  entry: {
    block_index: number;
    entry_index: number;
  };
  ancestor_count: number;
  lineage: LineageRef[];
  roots: Array<{
    block_index: number;
    entry_index: number;
    entry?: Entry;
  }>;
}

/** Derivation tree response */
export interface DerivationTreeResponse {
  entry: {
    block_index: number;
    entry_index: number;
    data?: Entry;
  };
  parents: LineageRef[];
  lineage: LineageRef[];
  roots: Array<{
    block_index: number;
    entry_index: number;
    entry?: Entry;
  }>;
  derivatives: DerivativeRef[];
  all_descendants: DerivativeRef[];
}

/** Derivative status response */
export interface DerivativeStatusResponse {
  block_index: number;
  entry_index: number;
  is_derivative: boolean;
  has_derivatives: boolean;
  derivative_type: DerivativeType | null;
  parent_count: number;
  parent_refs?: ParentRef[];
}

/** Derivative types response */
export interface DerivativeTypesResponse {
  types: DerivativeType[];
  descriptions: Record<DerivativeType, string>;
}

/** Validate derivative refs request */
export interface ValidateDerivativeRefsRequest {
  parent_refs: ParentRef[];
  derivative_type: DerivativeType;
}

/** Validate derivative refs response */
export interface ValidateDerivativeRefsResponse {
  valid: boolean;
  derivative_type: DerivativeType;
  total_refs: number;
  valid_refs: Array<{
    block_index: number;
    entry_index: number;
    author: string;
    intent: string;
  }>;
  issues: Array<{
    ref_index: number;
    error: string;
    block_index?: number;
    entry_index?: number;
  }>;
}

/** Options for getting derivatives */
export interface GetDerivativesOptions {
  /** If true, get all descendants recursively */
  recursive?: boolean;
  /** Maximum recursion depth (default: 10, max: 50) */
  maxDepth?: number;
  /** If true, include full entry data */
  includeEntries?: boolean;
}

/** Options for getting lineage */
export interface GetLineageOptions {
  /** Maximum traversal depth (default: 10, max: 50) */
  maxDepth?: number;
  /** If true, include full entry data */
  includeEntries?: boolean;
}

/**
 * Derivatives client for intent evolution tracking
 */
export class DerivativesClient {
  constructor(private readonly http: HttpClient) {}

  /**
   * Get all valid derivative types and their descriptions
   *
   * @returns List of valid derivative types
   *
   * @example
   * ```ts
   * const types = await client.derivatives.getTypes();
   * console.log(types.types); // ['amendment', 'extension', ...]
   * console.log(types.descriptions.amendment); // 'Modifies terms of parent entry'
   * ```
   */
  async getTypes(): Promise<DerivativeTypesResponse> {
    return this.http.get<DerivativeTypesResponse>('/derivatives/types');
  }

  /**
   * Get all derivatives of a specific entry
   *
   * @param blockIndex - Block containing the parent entry
   * @param entryIndex - Index of the parent entry within the block
   * @param options - Query options
   * @returns List of derivative entry references
   *
   * @example
   * ```ts
   * // Get direct derivatives only
   * const derivatives = await client.derivatives.getDerivatives(1, 0);
   *
   * // Get all descendants recursively with full entry data
   * const allDescendants = await client.derivatives.getDerivatives(1, 0, {
   *   recursive: true,
   *   maxDepth: 5,
   *   includeEntries: true
   * });
   *
   * for (const deriv of allDescendants.derivatives) {
   *   console.log(`${deriv.derivative_type} at depth ${deriv.depth}`);
   * }
   * ```
   */
  async getDerivatives(
    blockIndex: number,
    entryIndex: number,
    options?: GetDerivativesOptions
  ): Promise<DerivativesResponse> {
    const params: Record<string, string | number> = {};

    if (options?.recursive) params.recursive = 'true';
    if (options?.maxDepth) params.max_depth = options.maxDepth;
    if (options?.includeEntries) params.include_entries = 'true';

    return this.http.get<DerivativesResponse>(
      `/derivatives/${blockIndex}/${entryIndex}`,
      params
    );
  }

  /**
   * Get the full ancestry/lineage of an entry
   *
   * Traces back through all parent relationships to find
   * the original root entries.
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Index of the entry within the block
   * @param options - Query options
   * @returns Lineage information including ancestors and roots
   *
   * @example
   * ```ts
   * const lineage = await client.derivatives.getLineage(5, 2, {
   *   includeEntries: true
   * });
   *
   * console.log(`Entry has ${lineage.ancestor_count} ancestors`);
   * console.log('Root entries:', lineage.roots);
   *
   * for (const ancestor of lineage.lineage) {
   *   console.log(`Ancestor at depth ${ancestor.depth}: ${ancestor.entry?.intent}`);
   * }
   * ```
   */
  async getLineage(
    blockIndex: number,
    entryIndex: number,
    options?: GetLineageOptions
  ): Promise<LineageResponse> {
    const params: Record<string, string | number> = {};

    if (options?.maxDepth) params.max_depth = options.maxDepth;
    if (options?.includeEntries) params.include_entries = 'true';

    return this.http.get<LineageResponse>(
      `/derivatives/${blockIndex}/${entryIndex}/lineage`,
      params
    );
  }

  /**
   * Get the complete derivation tree for an entry
   *
   * Returns both ancestors and descendants in a tree structure.
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Index of the entry within the block
   * @param options - Query options
   * @returns Complete derivation tree
   *
   * @example
   * ```ts
   * const tree = await client.derivatives.getTree(3, 1, {
   *   maxDepth: 10,
   *   includeEntries: true
   * });
   *
   * console.log('Parents:', tree.parents.length);
   * console.log('Full lineage:', tree.lineage.length);
   * console.log('Roots:', tree.roots.length);
   * console.log('Direct derivatives:', tree.derivatives.length);
   * console.log('All descendants:', tree.all_descendants.length);
   * ```
   */
  async getTree(
    blockIndex: number,
    entryIndex: number,
    options?: GetLineageOptions
  ): Promise<DerivationTreeResponse> {
    const params: Record<string, string | number> = {};

    if (options?.maxDepth) params.max_depth = options.maxDepth;
    if (options?.includeEntries) params.include_entries = 'true';

    return this.http.get<DerivationTreeResponse>(
      `/derivatives/${blockIndex}/${entryIndex}/tree`,
      params
    );
  }

  /**
   * Get derivative status for an entry
   *
   * Returns whether the entry is a derivative and/or has derivatives.
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Index of the entry within the block
   * @returns Derivative status information
   *
   * @example
   * ```ts
   * const status = await client.derivatives.getStatus(2, 0);
   *
   * if (status.is_derivative) {
   *   console.log(`This is a ${status.derivative_type} of ${status.parent_count} parent(s)`);
   * }
   *
   * if (status.has_derivatives) {
   *   console.log('This entry has been derived from');
   * }
   * ```
   */
  async getStatus(
    blockIndex: number,
    entryIndex: number
  ): Promise<DerivativeStatusResponse> {
    return this.http.get<DerivativeStatusResponse>(
      `/derivatives/${blockIndex}/${entryIndex}/status`
    );
  }

  /**
   * Validate parent references before creating a derivative entry
   *
   * Use this to check that parent references are valid before
   * submitting a derivative entry.
   *
   * @param request - Validation request with parent refs and derivative type
   * @returns Validation result with any issues found
   *
   * @example
   * ```ts
   * const validation = await client.derivatives.validateRefs({
   *   parent_refs: [
   *     { block_index: 1, entry_index: 0 },
   *     { block_index: 2, entry_index: 1 }
   *   ],
   *   derivative_type: 'amendment'
   * });
   *
   * if (validation.valid) {
   *   // Safe to create derivative entry
   *   await client.core.createEntry({
   *     content: 'Amending the terms from Block 1, Entry 0...',
   *     author: 'user@example.com',
   *     intent: 'Amendment to original agreement',
   *     metadata: {
   *       parent_refs: validation.valid_refs,
   *       derivative_type: 'amendment'
   *     }
   *   });
   * } else {
   *   console.error('Invalid parent refs:', validation.issues);
   * }
   * ```
   */
  async validateRefs(
    request: ValidateDerivativeRefsRequest
  ): Promise<ValidateDerivativeRefsResponse> {
    return this.http.post<ValidateDerivativeRefsResponse>(
      '/derivatives/validate',
      request
    );
  }

  /**
   * Check if an entry is a derivative (has parents)
   *
   * Convenience method that wraps getStatus.
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Index of the entry within the block
   * @returns True if the entry is a derivative
   */
  async isDerivative(blockIndex: number, entryIndex: number): Promise<boolean> {
    const status = await this.getStatus(blockIndex, entryIndex);
    return status.is_derivative;
  }

  /**
   * Check if an entry has derivatives (has children)
   *
   * Convenience method that wraps getStatus.
   *
   * @param blockIndex - Block containing the entry
   * @param entryIndex - Index of the entry within the block
   * @returns True if the entry has derivatives
   */
  async hasDerivatives(blockIndex: number, entryIndex: number): Promise<boolean> {
    const status = await this.getStatus(blockIndex, entryIndex);
    return status.has_derivatives;
  }
}
