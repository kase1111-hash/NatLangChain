/**
 * Disputes Client - Dispute Resolution Management
 *
 * Handles dispute lifecycle operations:
 * - Filing disputes
 * - Evidence submission
 * - Escalation
 * - Resolution
 */

import { HttpClient } from '../utils/client';
import type {
  DisputeFileRequest,
  DisputeFileResponse,
  DisputeListResponse,
  DisputeEvidenceRequest,
  Dispute,
} from '../types';

/** Dispute list filter options */
export interface DisputeListOptions {
  /** Filter by status */
  status?: 'open' | 'evidence_collection' | 'escalated' | 'resolved';
  /** Filter by complainant */
  complainant?: string;
  /** Filter by respondent */
  respondent?: string;
}

/** Dispute resolution request */
export interface DisputeResolveRequest {
  outcome: string;
  resolved_by: string;
  notes?: string;
}

/** Dispute analysis response */
export interface DisputeAnalysisResponse {
  dispute_id: string;
  analysis: {
    summary: string;
    key_issues: string[];
    evidence_assessment: {
      complainant_evidence: string;
      respondent_evidence: string;
    };
    recommended_outcome: string;
    confidence: number;
  };
}

/** Dispute package response (complete dispute bundle) */
export interface DisputePackageResponse {
  dispute: Dispute;
  related_entries: Array<{
    block: number;
    entry: number;
    content: string;
  }>;
  timeline: Array<{
    timestamp: string;
    event: string;
    actor: string;
  }>;
}

/**
 * Disputes client for dispute resolution operations
 */
export class DisputesClient {
  constructor(private readonly http: HttpClient) {}

  /**
   * File a new dispute
   *
   * @param request - Dispute details
   * @returns Created dispute
   *
   * @example
   * ```ts
   * const dispute = await client.disputes.file({
   *   complainant: 'alice@example.com',
   *   respondent: 'bob@example.com',
   *   description: 'Bob failed to deliver widgets as agreed in Block 5, Entry 2',
   *   related_entries: [{ block: 5, entry: 2 }],
   *   evidence: {
   *     delivery_tracking: 'No shipment recorded',
   *     communication_log: 'Multiple unanswered follow-ups'
   *   }
   * });
   *
   * console.log(`Dispute filed: ${dispute.dispute.id}`);
   * ```
   */
  async file(request: DisputeFileRequest): Promise<DisputeFileResponse> {
    return this.http.post<DisputeFileResponse>('/dispute/file', request);
  }

  /**
   * List all disputes with optional filters
   *
   * @param options - Filter options
   * @returns Filtered list of disputes
   *
   * @example
   * ```ts
   * // Get all open disputes
   * const openDisputes = await client.disputes.list({ status: 'open' });
   *
   * // Get disputes where I'm the complainant
   * const myDisputes = await client.disputes.list({
   *   complainant: 'me@example.com'
   * });
   * ```
   */
  async list(options?: DisputeListOptions): Promise<DisputeListResponse> {
    const params: Record<string, string> = {};

    if (options?.status) params.status = options.status;
    if (options?.complainant) params.complainant = options.complainant;
    if (options?.respondent) params.respondent = options.respondent;

    return this.http.get<DisputeListResponse>('/dispute/list', params);
  }

  /**
   * Get a specific dispute by ID
   *
   * @param disputeId - Dispute identifier
   * @returns Dispute details
   *
   * @example
   * ```ts
   * const dispute = await client.disputes.get('disp_123abc');
   * console.log(`Status: ${dispute.status}`);
   * console.log(`Evidence items: ${dispute.evidence.length}`);
   * ```
   */
  async get(disputeId: string): Promise<Dispute> {
    return this.http.get<Dispute>(`/dispute/${encodeURIComponent(disputeId)}`);
  }

  /**
   * Submit evidence for a dispute
   *
   * @param disputeId - Dispute identifier
   * @param request - Evidence details
   * @returns Updated dispute
   *
   * @example
   * ```ts
   * await client.disputes.submitEvidence('disp_123abc', {
   *   submitter: 'alice@example.com',
   *   evidence_type: 'communication',
   *   content: 'Email thread showing delivery was promised by March 15',
   *   metadata: {
   *     email_date: '2025-03-10',
   *     participants: ['alice', 'bob']
   *   }
   * });
   * ```
   */
  async submitEvidence(disputeId: string, request: DisputeEvidenceRequest): Promise<Dispute> {
    return this.http.post<Dispute>(
      `/dispute/${encodeURIComponent(disputeId)}/evidence`,
      request
    );
  }

  /**
   * Escalate a dispute to higher authority
   *
   * @param disputeId - Dispute identifier
   * @param reason - Reason for escalation
   * @returns Updated dispute
   *
   * @example
   * ```ts
   * await client.disputes.escalate('disp_123abc', {
   *   reason: 'Parties unable to reach agreement after 3 mediation rounds'
   * });
   * ```
   */
  async escalate(disputeId: string, reason: string): Promise<Dispute> {
    return this.http.post<Dispute>(
      `/dispute/${encodeURIComponent(disputeId)}/escalate`,
      { reason }
    );
  }

  /**
   * Resolve a dispute
   *
   * @param disputeId - Dispute identifier
   * @param request - Resolution details
   * @returns Resolved dispute
   *
   * @example
   * ```ts
   * await client.disputes.resolve('disp_123abc', {
   *   outcome: 'Bob to deliver remaining 5 widgets within 7 days or refund $50',
   *   resolved_by: 'mediator@natlangchain.org',
   *   notes: 'Both parties agreed to partial fulfillment'
   * });
   * ```
   */
  async resolve(disputeId: string, request: DisputeResolveRequest): Promise<Dispute> {
    return this.http.post<Dispute>(
      `/dispute/${encodeURIComponent(disputeId)}/resolve`,
      request
    );
  }

  /**
   * Get complete dispute package
   *
   * Retrieves the full dispute bundle including related entries
   * and timeline of events.
   *
   * @param disputeId - Dispute identifier
   * @returns Complete dispute package
   *
   * @example
   * ```ts
   * const pkg = await client.disputes.getPackage('disp_123abc');
   *
   * console.log('Related entries:');
   * for (const entry of pkg.related_entries) {
   *   console.log(`  Block ${entry.block}, Entry ${entry.entry}: ${entry.content}`);
   * }
   *
   * console.log('Timeline:');
   * for (const event of pkg.timeline) {
   *   console.log(`  ${event.timestamp}: ${event.event} by ${event.actor}`);
   * }
   * ```
   */
  async getPackage(disputeId: string): Promise<DisputePackageResponse> {
    return this.http.get<DisputePackageResponse>(
      `/dispute/${encodeURIComponent(disputeId)}/package`
    );
  }

  /**
   * Get AI-powered dispute analysis
   *
   * Uses LLM to analyze the dispute and provide recommendations.
   *
   * @param disputeId - Dispute identifier
   * @returns AI analysis of the dispute
   *
   * @example
   * ```ts
   * const analysis = await client.disputes.analyze('disp_123abc');
   *
   * console.log('Key issues:', analysis.analysis.key_issues);
   * console.log('Recommended outcome:', analysis.analysis.recommended_outcome);
   * console.log(`Confidence: ${analysis.analysis.confidence}%`);
   * ```
   */
  async analyze(disputeId: string): Promise<DisputeAnalysisResponse> {
    return this.http.get<DisputeAnalysisResponse>(
      `/dispute/${encodeURIComponent(disputeId)}/analyze`
    );
  }
}
