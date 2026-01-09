/**
 * Contracts Client - Natural Language Contract Management
 *
 * Handles contract lifecycle operations:
 * - Contract parsing and term extraction
 * - Contract posting (offers and seeks)
 * - Contract matching
 * - Contract responses and counter-offers
 */

import { HttpClient } from '../utils/client';
import type {
  ContractParseRequest,
  ContractParseResponse,
  ContractPostRequest,
  ContractPostResponse,
  ContractMatchRequest,
  ContractMatchResponse,
  ContractListResponse,
  ContractRespondRequest,
  ContractRespondResponse,
} from '../types';

/** Contract list filter options */
export interface ContractListOptions {
  /** Filter by status */
  status?: 'open' | 'matched' | 'negotiating' | 'closed' | 'cancelled';
  /** Filter by type */
  type?: 'offer' | 'seek' | 'proposal';
  /** Filter by author */
  author?: string;
}

/**
 * Contracts client for natural language contract operations
 */
export class ContractsClient {
  constructor(private readonly http: HttpClient) {}

  /**
   * Parse natural language contract content and extract structured terms
   *
   * Uses LLM to analyze prose contracts and extract:
   * - Contract type (offer, seek, proposal)
   * - Terms and conditions
   * - Parties involved
   * - Key conditions
   *
   * @param content - Natural language contract text
   * @returns Parsed contract with extracted structure
   *
   * @example
   * ```ts
   * const parsed = await client.contracts.parse({
   *   content: `I, Alice, offer to sell 100 widgets to any buyer
   *             at $10 per widget. Delivery within 30 days of payment.
   *             Buyer pays shipping.`
   * });
   *
   * console.log(parsed.parsed.contract_type); // 'offer'
   * console.log(parsed.parsed.terms); // { price: '$10/widget', quantity: 100, ... }
   * ```
   */
  async parse(request: ContractParseRequest): Promise<ContractParseResponse> {
    return this.http.post<ContractParseResponse>('/contract/parse', request);
  }

  /**
   * Post a new live contract (offer or seek)
   *
   * Creates a contract entry on the blockchain that can be matched
   * with compatible counterparties.
   *
   * @param request - Contract details
   * @returns Posted contract with validation results
   *
   * @example
   * ```ts
   * // Post an offer
   * const offer = await client.contracts.post({
   *   content: 'Offering 500 hours of Python development at $150/hour',
   *   author: 'dev@example.com',
   *   intent: 'Seeking development contract',
   *   contract_type: 'offer',
   *   terms: {
   *     hourly_rate: 150,
   *     total_hours: 500,
   *     skills: ['Python', 'Django', 'PostgreSQL']
   *   }
   * });
   *
   * // Post a seek
   * const seek = await client.contracts.post({
   *   content: 'Looking for Python developer, 500 hours, budget $100-175/hour',
   *   author: 'startup@example.com',
   *   intent: 'Hiring developer',
   *   contract_type: 'seek'
   * });
   * ```
   */
  async post(request: ContractPostRequest): Promise<ContractPostResponse> {
    return this.http.post<ContractPostResponse>('/contract/post', request);
  }

  /**
   * Find matching contracts for pending entries
   *
   * Analyzes pending entries and existing contracts to find
   * compatible matches (offers matching seeks, etc.)
   *
   * @param request - Match parameters
   * @returns List of matched contract proposals
   *
   * @example
   * ```ts
   * const matches = await client.contracts.match({
   *   miner_id: 'matcher-node-1'
   * });
   *
   * for (const match of matches.matches) {
   *   console.log(`Match found: ${match.compatibility_score}% compatible`);
   *   console.log('Offer:', match.offer.intent);
   *   console.log('Seek:', match.seek.intent);
   * }
   * ```
   */
  async match(request?: ContractMatchRequest): Promise<ContractMatchResponse> {
    return this.http.post<ContractMatchResponse>('/contract/match', request ?? {});
  }

  /**
   * List all contracts with optional filters
   *
   * @param options - Filter options
   * @returns Filtered list of contracts
   *
   * @example
   * ```ts
   * // Get all open offers
   * const openOffers = await client.contracts.list({
   *   status: 'open',
   *   type: 'offer'
   * });
   *
   * // Get all contracts by specific author
   * const myContracts = await client.contracts.list({
   *   author: 'me@example.com'
   * });
   * ```
   */
  async list(options?: ContractListOptions): Promise<ContractListResponse> {
    const params: Record<string, string> = {};

    if (options?.status) params.status = options.status;
    if (options?.type) params.type = options.type;
    if (options?.author) params.author = options.author;

    return this.http.get<ContractListResponse>('/contract/list', params);
  }

  /**
   * Respond to a contract proposal
   *
   * Allows accepting, rejecting, or counter-offering a contract.
   * Counter-offers trigger mediation for negotiation support.
   *
   * @param request - Response details
   * @returns Response entry with optional mediation
   *
   * @example
   * ```ts
   * // Accept a contract
   * await client.contracts.respond({
   *   to_block: 5,
   *   to_entry: 2,
   *   response_content: 'I accept these terms and will begin work Monday',
   *   author: 'contractor@example.com',
   *   response_type: 'accept'
   * });
   *
   * // Counter-offer
   * const counter = await client.contracts.respond({
   *   to_block: 5,
   *   to_entry: 2,
   *   response_content: 'I propose $175/hour instead of $150',
   *   author: 'contractor@example.com',
   *   response_type: 'counter',
   *   counter_terms: {
   *     hourly_rate: 175
   *   }
   * });
   *
   * if (counter.mediation) {
   *   console.log('Mediator suggests:', counter.mediation.suggested_compromise);
   * }
   * ```
   */
  async respond(request: ContractRespondRequest): Promise<ContractRespondResponse> {
    return this.http.post<ContractRespondResponse>('/contract/respond', request);
  }
}
