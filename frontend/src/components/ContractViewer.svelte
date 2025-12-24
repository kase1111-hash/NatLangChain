<script>
  import { onMount } from 'svelte';
  import { getOpenContracts, parseContract, findContractMatches, getPendingEntries } from '../lib/api.js';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  let contracts = [];
  let pendingEntries = [];
  let loading = true;
  let error = null;
  let selectedContract = null;
  let parseInput = '';
  let parseResult = null;
  let parsing = false;
  let matching = false;
  let matchResults = null;

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    loading = true;
    error = null;
    try {
      const [contractsData, pendingData] = await Promise.all([
        getOpenContracts().catch(() => ({ contracts: [] })),
        getPendingEntries().catch(() => ({ entries: [] }))
      ]);
      contracts = contractsData.contracts || [];
      pendingEntries = pendingData.entries || [];
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function handleParse() {
    if (!parseInput.trim()) return;

    parsing = true;
    parseResult = null;
    error = null;

    try {
      parseResult = await parseContract(parseInput);
    } catch (e) {
      error = 'Failed to parse contract: ' + e.message;
    } finally {
      parsing = false;
    }
  }

  async function handleFindMatches() {
    matching = true;
    matchResults = null;
    error = null;

    try {
      matchResults = await findContractMatches(pendingEntries, 'web-matcher');
    } catch (e) {
      error = 'Failed to find matches: ' + e.message;
    } finally {
      matching = false;
    }
  }

  function formatTimestamp(ts) {
    if (!ts) return 'N/A';
    return new Date(ts).toLocaleString();
  }

  function getContractTypeColor(type) {
    const colors = {
      offer: '#22c55e',
      seek: '#3b82f6',
      proposal: '#a855f7',
      response: '#f59e0b'
    };
    return colors[type] || '#71717a';
  }
</script>

<div class="contracts">
  <div class="contracts-header">
    <h2>Contract Manager</h2>
    <button class="refresh-btn" on:click={loadData}>Refresh</button>
  </div>

  {#if loading}
    <div class="loading">Loading contracts...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else}
    <div class="contracts-grid">
      <!-- Contract Parser -->
      <div class="panel parse-panel">
        <Tooltip text={ncipDefinitions.contractParse.text} ncipRef={ncipDefinitions.contractParse.ncipRef} position="right">
          <h3>Parse Contract</h3>
        </Tooltip>
        <p class="panel-desc">Analyze natural language contract text</p>

        <textarea
          bind:value={parseInput}
          placeholder="Enter contract text to parse...

Example: 'I, Alice, agree to deliver 100 widgets to Bob by January 15, 2025, in exchange for $500 payment upon delivery.'"
          rows="6"
        ></textarea>

        <Tooltip text={ncipDefinitions.contractParse.text} ncipRef={ncipDefinitions.contractParse.ncipRef} position="top">
          <button
            class="btn-primary"
            on:click={handleParse}
            disabled={parsing || !parseInput.trim()}
          >
            {parsing ? 'Parsing...' : 'Parse Contract'}
          </button>
        </Tooltip>

        {#if parseResult}
          <div class="parse-result">
            <h4>Parse Result</h4>
            {#if parseResult.terms}
              <div class="terms-list">
                <div class="term-item">
                  <Tooltip text={ncipDefinitions.parties.text} ncipRef={ncipDefinitions.parties.ncipRef} position="right">
                    <span class="term-label">Parties:</span>
                  </Tooltip>
                  <span class="term-value">{parseResult.terms.parties?.join(', ') || 'None identified'}</span>
                </div>
                <div class="term-item">
                  <Tooltip text={ncipDefinitions.obligations.text} ncipRef={ncipDefinitions.obligations.ncipRef} position="right">
                    <span class="term-label">Obligations:</span>
                  </Tooltip>
                  <ul>
                    {#each parseResult.terms.obligations || [] as obligation}
                      <li>{obligation}</li>
                    {/each}
                  </ul>
                </div>
                <div class="term-item">
                  <Tooltip text={ncipDefinitions.conditions.text} ncipRef={ncipDefinitions.conditions.ncipRef} position="right">
                    <span class="term-label">Conditions:</span>
                  </Tooltip>
                  <ul>
                    {#each parseResult.terms.conditions || [] as condition}
                      <li>{condition}</li>
                    {/each}
                  </ul>
                </div>
                {#if parseResult.terms.timeline}
                  <div class="term-item">
                    <span class="term-label">Timeline:</span>
                    <span class="term-value">{parseResult.terms.timeline}</span>
                  </div>
                {/if}
              </div>
            {:else}
              <pre>{JSON.stringify(parseResult, null, 2)}</pre>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Open Contracts -->
      <div class="panel contracts-list-panel">
        <Tooltip text={ncipDefinitions.agreement.text} ncipRef={ncipDefinitions.agreement.ncipRef} position="right">
          <h3>Open Contracts ({contracts.length})</h3>
        </Tooltip>
        <p class="panel-desc">Contracts awaiting fulfillment or response</p>

        {#if contracts.length === 0}
          <div class="empty-state">
            <p>No open contracts found</p>
            <p class="hint">Submit contract entries to see them here</p>
          </div>
        {:else}
          <div class="contracts-scroll">
            {#each contracts as contract}
              <button
                class="contract-card"
                class:selected={selectedContract === contract}
                on:click={() => selectedContract = contract}
              >
                <div class="contract-header">
                  <span
                    class="contract-type"
                    style="background-color: {getContractTypeColor(contract.type)}20; color: {getContractTypeColor(contract.type)}"
                  >
                    {contract.type || 'unknown'}
                  </span>
                  <span class="contract-time">{formatTimestamp(contract.timestamp)}</span>
                </div>
                <div class="contract-author">{contract.author}</div>
                <div class="contract-preview">{contract.content?.slice(0, 100)}...</div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Contract Matching -->
      <div class="panel matching-panel">
        <Tooltip text={ncipDefinitions.contractMatching.text} ncipRef={ncipDefinitions.contractMatching.ncipRef} position="right">
          <h3>Contract Matching</h3>
        </Tooltip>
        <p class="panel-desc">Find matching offers and seeks</p>

        <Tooltip text={ncipDefinitions.pendingEntries.text} ncipRef={ncipDefinitions.pendingEntries.ncipRef} position="right">
          <div class="pending-info">
            <span class="pending-count">{pendingEntries.length}</span>
            <span>pending entries to match</span>
          </div>
        </Tooltip>

        <Tooltip text={ncipDefinitions.contractMatching.text} ncipRef={ncipDefinitions.contractMatching.ncipRef} position="top">
          <button
            class="btn-primary"
            on:click={handleFindMatches}
            disabled={matching || pendingEntries.length === 0}
          >
            {matching ? 'Finding Matches...' : 'Find Matches'}
          </button>
        </Tooltip>

        {#if matchResults}
          <div class="match-results">
            <h4>Match Results</h4>
            {#if matchResults.matches && matchResults.matches.length > 0}
              {#each matchResults.matches as match}
                <div class="match-item">
                  <div class="match-score">
                    Match Score: {(match.score * 100).toFixed(1)}%
                  </div>
                  <div class="match-entries">
                    <div class="match-entry offer">
                      <strong>Offer:</strong> {match.offer?.content?.slice(0, 80)}...
                    </div>
                    <div class="match-entry seek">
                      <strong>Seek:</strong> {match.seek?.content?.slice(0, 80)}...
                    </div>
                  </div>
                </div>
              {/each}
            {:else}
              <p class="no-matches">No matches found</p>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Selected Contract Details -->
      {#if selectedContract}
        <div class="panel detail-panel">
          <h3>Contract Details</h3>
          <button class="close-btn" on:click={() => selectedContract = null}>Close</button>

          <div class="detail-content">
            <div class="detail-row">
              <span class="detail-label">Author:</span>
              <span class="detail-value">{selectedContract.author}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Type:</span>
              <span
                class="contract-type-badge"
                style="background-color: {getContractTypeColor(selectedContract.type)}20; color: {getContractTypeColor(selectedContract.type)}"
              >
                {selectedContract.type || 'unknown'}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Intent:</span>
              <span class="detail-value">{selectedContract.intent}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Created:</span>
              <span class="detail-value">{formatTimestamp(selectedContract.timestamp)}</span>
            </div>
            <div class="detail-row full-width">
              <span class="detail-label">Content:</span>
              <div class="detail-content-text">{selectedContract.content}</div>
            </div>
            {#if selectedContract.metadata}
              <div class="detail-row full-width">
                <span class="detail-label">Metadata:</span>
                <pre class="metadata-pre">{JSON.stringify(selectedContract.metadata, null, 2)}</pre>
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .contracts {
    height: calc(100vh - 300px);
    min-height: 500px;
  }

  .contracts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  h2 {
    font-size: 1.5rem;
    color: #e4e4e7;
  }

  .refresh-btn {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: #e4e4e7;
    cursor: pointer;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .loading, .error {
    text-align: center;
    padding: 40px;
    color: #a1a1aa;
  }

  .error {
    color: #ef4444;
  }

  .contracts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .panel {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
  }

  .panel h3 {
    color: #e4e4e7;
    margin-bottom: 8px;
  }

  .panel-desc {
    color: #71717a;
    font-size: 0.875rem;
    margin-bottom: 16px;
  }

  textarea {
    width: 100%;
    padding: 12px;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #e4e4e7;
    font-family: inherit;
    font-size: 0.875rem;
    resize: vertical;
    margin-bottom: 12px;
  }

  textarea:focus {
    outline: none;
    border-color: #667eea;
  }

  .btn-primary {
    padding: 10px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 8px;
    color: white;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .parse-result {
    margin-top: 16px;
    padding: 16px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
  }

  .parse-result h4 {
    color: #e4e4e7;
    margin-bottom: 12px;
  }

  .terms-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .term-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .term-label {
    color: #a1a1aa;
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  .term-value {
    color: #e4e4e7;
  }

  .term-item ul {
    margin: 0;
    padding-left: 20px;
    color: #e4e4e7;
  }

  .term-item li {
    margin-bottom: 4px;
  }

  .parse-result pre {
    color: #a1a1aa;
    font-size: 0.75rem;
    overflow-x: auto;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #71717a;
  }

  .hint {
    font-size: 0.875rem;
    margin-top: 8px;
  }

  .contracts-scroll {
    max-height: 300px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .contract-card {
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
  }

  .contract-card:hover {
    border-color: rgba(255, 255, 255, 0.2);
  }

  .contract-card.selected {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.1);
  }

  .contract-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .contract-type {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .contract-time {
    font-size: 0.75rem;
    color: #71717a;
  }

  .contract-author {
    font-weight: 600;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .contract-preview {
    font-size: 0.875rem;
    color: #a1a1aa;
    line-height: 1.4;
  }

  .pending-info {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    color: #a1a1aa;
  }

  .pending-count {
    font-size: 1.5rem;
    font-weight: 700;
    color: #667eea;
  }

  .match-results {
    margin-top: 16px;
  }

  .match-results h4 {
    color: #e4e4e7;
    margin-bottom: 12px;
  }

  .match-item {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
  }

  .match-score {
    font-weight: 600;
    color: #22c55e;
    margin-bottom: 8px;
  }

  .match-entries {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .match-entry {
    font-size: 0.875rem;
    color: #a1a1aa;
  }

  .match-entry strong {
    color: #e4e4e7;
  }

  .no-matches {
    color: #71717a;
    text-align: center;
    padding: 20px;
  }

  .detail-panel {
    grid-column: span 2;
    position: relative;
  }

  .close-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    padding: 4px 12px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    color: #a1a1aa;
    cursor: pointer;
    font-size: 0.75rem;
  }

  .close-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #e4e4e7;
  }

  .detail-content {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-top: 16px;
  }

  .detail-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .detail-row.full-width {
    grid-column: span 2;
  }

  .detail-label {
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  .detail-value {
    color: #e4e4e7;
  }

  .contract-type-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .detail-content-text {
    color: #e4e4e7;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  .metadata-pre {
    background: rgba(0, 0, 0, 0.3);
    padding: 12px;
    border-radius: 6px;
    color: #a1a1aa;
    font-size: 0.75rem;
    overflow-x: auto;
  }

  @media (max-width: 768px) {
    .contracts-grid {
      grid-template-columns: 1fr;
    }

    .detail-panel {
      grid-column: span 1;
    }

    .detail-content {
      grid-template-columns: 1fr;
    }

    .detail-row.full-width {
      grid-column: span 1;
    }
  }
</style>
