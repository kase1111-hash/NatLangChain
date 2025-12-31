<script>
  import { onMount } from 'svelte';
  import { fly, fade, scale } from 'svelte/transition';
  import {
    getOpenContracts,
    parseContract,
    findContractMatches,
    getPendingEntries,
  } from '../lib/api.js';
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
        getPendingEntries().catch(() => ({ entries: [] })),
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
      error = `Failed to parse contract: ${e.message}`;
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
      error = `Failed to find matches: ${e.message}`;
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
      offer: { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', border: 'rgba(34, 197, 94, 0.3)' },
      seek: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', border: 'rgba(59, 130, 246, 0.3)' },
      proposal: {
        bg: 'rgba(168, 85, 247, 0.15)',
        text: '#a855f7',
        border: 'rgba(168, 85, 247, 0.3)',
      },
      response: {
        bg: 'rgba(245, 158, 11, 0.15)',
        text: '#f59e0b',
        border: 'rgba(245, 158, 11, 0.3)',
      },
    };
    return (
      colors[type] || {
        bg: 'rgba(113, 113, 122, 0.15)',
        text: '#71717a',
        border: 'rgba(113, 113, 122, 0.3)',
      }
    );
  }

  const icons = {
    contract:
      'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    parse:
      'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
    refresh:
      'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
    match:
      'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
    user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    users:
      'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    clock: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    close: 'M6 18L18 6M6 6l12 12',
    check: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    list: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
    target:
      'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  };
</script>

<div class="contracts" in:fly={{ y: 20, duration: 400 }}>
  <div class="contracts-header">
    <div class="header-content">
      <div class="header-icon">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d={icons.contract} />
        </svg>
      </div>
      <div class="header-text">
        <h2>Contract Manager</h2>
        <p class="subtitle">Parse, view, and match contracts</p>
      </div>
    </div>
    <button class="refresh-btn" on:click={loadData}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d={icons.refresh} />
      </svg>
      <span>Refresh</span>
    </button>
  </div>

  {#if loading}
    <div class="loading-container" in:fade>
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <p>Loading contracts...</p>
    </div>
  {:else if error}
    <div class="error-message" in:scale={{ duration: 200 }}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {error}
    </div>
  {:else}
    <div class="contracts-grid">
      <!-- Contract Parser -->
      <div class="panel parse-panel" in:fly={{ y: 10, duration: 300, delay: 100 }}>
        <div class="panel-header">
          <Tooltip
            text={ncipDefinitions.contractParse.text}
            ncipRef={ncipDefinitions.contractParse.ncipRef}
            position="right"
          >
            <h3>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.parse} />
              </svg>
              Parse Contract
            </h3>
          </Tooltip>
        </div>
        <p class="panel-desc">Analyze natural language contract text</p>

        <textarea
          bind:value={parseInput}
          placeholder="Enter contract text to parse...

Example: 'I, Alice, agree to deliver 100 widgets to Bob by January 15, 2025, in exchange for $500 payment upon delivery.'"
          rows="6"
        ></textarea>

        <Tooltip
          text={ncipDefinitions.contractParse.text}
          ncipRef={ncipDefinitions.contractParse.ncipRef}
          position="top"
        >
          <button
            class="btn btn-primary"
            on:click={handleParse}
            disabled={parsing || !parseInput.trim()}
          >
            {#if parsing}
              <div class="btn-spinner"></div>
            {:else}
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.parse} />
              </svg>
            {/if}
            <span>{parsing ? 'Parsing...' : 'Parse Contract'}</span>
          </button>
        </Tooltip>

        {#if parseResult}
          <div class="parse-result" in:fly={{ y: 10, duration: 200 }}>
            <div class="result-header">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.check} />
              </svg>
              <h4>Parse Result</h4>
            </div>
            {#if parseResult.terms}
              <div class="terms-list">
                <div class="term-item">
                  <Tooltip
                    text={ncipDefinitions.parties.text}
                    ncipRef={ncipDefinitions.parties.ncipRef}
                    position="right"
                  >
                    <span class="term-label">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d={icons.users} />
                      </svg>
                      Parties
                    </span>
                  </Tooltip>
                  <span class="term-value"
                    >{parseResult.terms.parties?.join(', ') || 'None identified'}</span
                  >
                </div>
                <div class="term-item">
                  <Tooltip
                    text={ncipDefinitions.obligations.text}
                    ncipRef={ncipDefinitions.obligations.ncipRef}
                    position="right"
                  >
                    <span class="term-label">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d={icons.list} />
                      </svg>
                      Obligations
                    </span>
                  </Tooltip>
                  <ul>
                    {#each parseResult.terms.obligations || [] as obligation}
                      <li>{obligation}</li>
                    {/each}
                  </ul>
                </div>
                <div class="term-item">
                  <Tooltip
                    text={ncipDefinitions.conditions.text}
                    ncipRef={ncipDefinitions.conditions.ncipRef}
                    position="right"
                  >
                    <span class="term-label">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d={icons.target} />
                      </svg>
                      Conditions
                    </span>
                  </Tooltip>
                  <ul>
                    {#each parseResult.terms.conditions || [] as condition}
                      <li>{condition}</li>
                    {/each}
                  </ul>
                </div>
                {#if parseResult.terms.timeline}
                  <div class="term-item">
                    <span class="term-label">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d={icons.clock} />
                      </svg>
                      Timeline
                    </span>
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
      <div class="panel contracts-list-panel" in:fly={{ y: 10, duration: 300, delay: 150 }}>
        <div class="panel-header">
          <Tooltip
            text={ncipDefinitions.agreement.text}
            ncipRef={ncipDefinitions.agreement.ncipRef}
            position="right"
          >
            <h3>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.contract} />
              </svg>
              Open Contracts
            </h3>
          </Tooltip>
          <span class="count-badge">{contracts.length}</span>
        </div>
        <p class="panel-desc">Contracts awaiting fulfillment or response</p>

        {#if contracts.length === 0}
          <div class="empty-state">
            <div class="empty-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.contract} />
              </svg>
            </div>
            <p>No open contracts found</p>
            <span class="hint">Submit contract entries to see them here</span>
          </div>
        {:else}
          <div class="contracts-scroll">
            {#each contracts as contract, i}
              <button
                class="contract-card"
                class:selected={selectedContract === contract}
                on:click={() => (selectedContract = contract)}
                in:fly={{ x: -10, duration: 200, delay: i * 30 }}
              >
                <div class="contract-header">
                  <span
                    class="contract-type"
                    style="background: {getContractTypeColor(contract.type)
                      .bg}; color: {getContractTypeColor(contract.type)
                      .text}; border-color: {getContractTypeColor(contract.type).border}"
                  >
                    {contract.type || 'unknown'}
                  </span>
                  <span class="contract-time">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d={icons.clock} />
                    </svg>
                    {formatTimestamp(contract.timestamp)}
                  </span>
                </div>
                <div class="contract-author">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d={icons.user} />
                  </svg>
                  {contract.author}
                </div>
                <div class="contract-preview">{contract.content?.slice(0, 100)}...</div>
                {#if selectedContract === contract}
                  <div class="selected-indicator"></div>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Contract Matching -->
      <div class="panel matching-panel" in:fly={{ y: 10, duration: 300, delay: 200 }}>
        <div class="panel-header">
          <Tooltip
            text={ncipDefinitions.contractMatching.text}
            ncipRef={ncipDefinitions.contractMatching.ncipRef}
            position="right"
          >
            <h3>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.match} />
              </svg>
              Contract Matching
            </h3>
          </Tooltip>
        </div>
        <p class="panel-desc">Find matching offers and seeks</p>

        <Tooltip
          text={ncipDefinitions.pendingEntries.text}
          ncipRef={ncipDefinitions.pendingEntries.ncipRef}
          position="right"
        >
          <div class="pending-info">
            <span class="pending-count">{pendingEntries.length}</span>
            <span>pending entries to match</span>
          </div>
        </Tooltip>

        <Tooltip
          text={ncipDefinitions.contractMatching.text}
          ncipRef={ncipDefinitions.contractMatching.ncipRef}
          position="top"
        >
          <button
            class="btn btn-primary"
            on:click={handleFindMatches}
            disabled={matching || pendingEntries.length === 0}
          >
            {#if matching}
              <div class="btn-spinner"></div>
            {:else}
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.match} />
              </svg>
            {/if}
            <span>{matching ? 'Finding Matches...' : 'Find Matches'}</span>
          </button>
        </Tooltip>

        {#if matchResults}
          <div class="match-results" in:fly={{ y: 10, duration: 200 }}>
            <div class="result-header">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.match} />
              </svg>
              <h4>Match Results</h4>
            </div>
            {#if matchResults.matches && matchResults.matches.length > 0}
              {#each matchResults.matches as match, i}
                <div class="match-item" in:fly={{ y: 10, duration: 200, delay: i * 50 }}>
                  <div class="match-score">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <path d={icons.target} />
                    </svg>
                    Match Score: {(match.score * 100).toFixed(1)}%
                  </div>
                  <div class="match-entries">
                    <div class="match-entry offer">
                      <span class="entry-type">Offer</span>
                      <p>{match.offer?.content?.slice(0, 80)}...</p>
                    </div>
                    <div class="match-connector">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d={icons.match} />
                      </svg>
                    </div>
                    <div class="match-entry seek">
                      <span class="entry-type">Seek</span>
                      <p>{match.seek?.content?.slice(0, 80)}...</p>
                    </div>
                  </div>
                </div>
              {/each}
            {:else}
              <div class="no-matches">
                <p>No matches found</p>
              </div>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Selected Contract Details -->
      {#if selectedContract}
        <div class="panel detail-panel" in:fly={{ y: 20, duration: 300 }}>
          <div class="detail-header">
            <h3>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.contract} />
              </svg>
              Contract Details
            </h3>
            <button class="close-btn" on:click={() => (selectedContract = null)}>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.close} />
              </svg>
            </button>
          </div>

          <div class="detail-content">
            <div class="detail-row">
              <span class="detail-label">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d={icons.user} />
                </svg>
                Author
              </span>
              <span class="detail-value">{selectedContract.author}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Type</span>
              <span
                class="contract-type-badge"
                style="background: {getContractTypeColor(selectedContract.type)
                  .bg}; color: {getContractTypeColor(selectedContract.type)
                  .text}; border-color: {getContractTypeColor(selectedContract.type).border}"
              >
                {selectedContract.type || 'unknown'}
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d={icons.target} />
                </svg>
                Intent
              </span>
              <span class="detail-value">{selectedContract.intent}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d={icons.clock} />
                </svg>
                Created
              </span>
              <span class="detail-value">{formatTimestamp(selectedContract.timestamp)}</span>
            </div>
            <div class="detail-row full-width">
              <span class="detail-label">Content</span>
              <div class="detail-content-text">{selectedContract.content}</div>
            </div>
            {#if selectedContract.metadata}
              <div class="detail-row full-width">
                <span class="detail-label">Metadata</span>
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
    min-height: 500px;
  }

  .contracts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .header-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 16px;
    color: #667eea;
  }

  .header-icon svg {
    width: 28px;
    height: 28px;
  }

  .header-text h2 {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #667eea 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
  }

  .subtitle {
    color: #71717a;
    font-size: 0.9rem;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    color: #e4e4e7;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .refresh-btn svg {
    width: 18px;
    height: 18px;
  }

  .refresh-btn:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
    transform: translateY(-2px);
  }

  /* Loading */
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px;
    gap: 24px;
  }

  .loading-spinner {
    position: relative;
    width: 60px;
    height: 60px;
  }

  .spinner-ring {
    position: absolute;
    inset: 0;
    border: 3px solid transparent;
    border-radius: 50%;
  }

  .spinner-ring:nth-child(1) {
    border-top-color: #667eea;
    animation: spin 1s linear infinite;
  }

  .spinner-ring:nth-child(2) {
    inset: 6px;
    border-right-color: #a855f7;
    animation: spin 1.5s linear infinite reverse;
  }

  .spinner-ring:nth-child(3) {
    inset: 12px;
    border-bottom-color: #764ba2;
    animation: spin 2s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .loading-container p {
    color: #a1a1aa;
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 14px 18px;
    border-radius: 14px;
    margin-bottom: 20px;
  }

  .error-message svg {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  .contracts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .panel {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .panel-header h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e4e4e7;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .panel-header svg {
    width: 20px;
    height: 20px;
    color: #667eea;
  }

  .count-badge {
    padding: 4px 12px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .panel-desc {
    color: #71717a;
    font-size: 0.875rem;
    margin-bottom: 20px;
  }

  textarea {
    width: 100%;
    padding: 14px 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    color: #e4e4e7;
    font-family: inherit;
    font-size: 0.9rem;
    resize: vertical;
    margin-bottom: 16px;
    line-height: 1.6;
    min-height: 140px;
    transition: all 0.3s ease;
  }

  textarea:focus {
    outline: none;
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  textarea::placeholder {
    color: #52525b;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 12px 24px;
    border-radius: 12px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    border: none;
  }

  .btn svg {
    width: 18px;
    height: 18px;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  .btn-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid transparent;
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .parse-result,
  .match-results {
    margin-top: 20px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .result-header svg {
    width: 20px;
    height: 20px;
    color: #22c55e;
  }

  .result-header h4 {
    color: #e4e4e7;
    font-size: 1rem;
    font-weight: 600;
  }

  .terms-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .term-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .term-label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .term-label svg {
    width: 16px;
    height: 16px;
    color: #667eea;
  }

  .term-value {
    color: #e4e4e7;
    font-size: 0.9rem;
  }

  .term-item ul {
    margin: 0;
    padding-left: 24px;
    color: #e4e4e7;
    font-size: 0.9rem;
  }

  .term-item li {
    margin-bottom: 6px;
    line-height: 1.5;
  }

  .parse-result pre {
    color: #a1a1aa;
    font-size: 0.75rem;
    overflow-x: auto;
    font-family: 'Monaco', 'Menlo', monospace;
  }

  /* Contracts List */
  .empty-state {
    text-align: center;
    padding: 40px 20px;
  }

  .empty-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 16px;
    color: #3f3f46;
  }

  .empty-icon svg {
    width: 100%;
    height: 100%;
  }

  .empty-state p {
    color: #71717a;
    margin-bottom: 8px;
  }

  .hint {
    font-size: 0.85rem;
    color: #52525b;
  }

  .contracts-scroll {
    max-height: 350px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .contract-card {
    position: relative;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.3s ease;
    width: 100%;
    overflow: hidden;
  }

  .contract-card:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateX(4px);
  }

  .contract-card.selected {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.4);
  }

  .selected-indicator {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, #667eea, #764ba2);
    border-radius: 0 4px 4px 0;
  }

  .contract-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .contract-type {
    padding: 4px 12px;
    border: 1px solid;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .contract-time {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #52525b;
  }

  .contract-time svg {
    width: 12px;
    height: 12px;
  }

  .contract-author {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #e4e4e7;
    margin-bottom: 8px;
  }

  .contract-author svg {
    width: 16px;
    height: 16px;
    color: #667eea;
  }

  .contract-preview {
    font-size: 0.85rem;
    color: #71717a;
    line-height: 1.5;
  }

  /* Matching Panel */
  .pending-info {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    color: #a1a1aa;
  }

  .pending-count {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .match-item {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
  }

  .match-score {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #22c55e;
    margin-bottom: 14px;
  }

  .match-score svg {
    width: 18px;
    height: 18px;
  }

  .match-entries {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .match-entry {
    padding: 12px 14px;
    border-radius: 10px;
  }

  .match-entry.offer {
    background: rgba(34, 197, 94, 0.1);
    border-left: 3px solid #22c55e;
  }

  .match-entry.seek {
    background: rgba(59, 130, 246, 0.1);
    border-left: 3px solid #3b82f6;
  }

  .entry-type {
    font-size: 0.7rem;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
    display: block;
  }

  .match-entry.offer .entry-type {
    color: #22c55e;
  }

  .match-entry.seek .entry-type {
    color: #3b82f6;
  }

  .match-entry p {
    color: #a1a1aa;
    font-size: 0.85rem;
    line-height: 1.5;
    margin: 0;
  }

  .match-connector {
    display: flex;
    justify-content: center;
    color: #52525b;
  }

  .match-connector svg {
    width: 20px;
    height: 20px;
    transform: rotate(90deg);
  }

  .no-matches {
    text-align: center;
    padding: 20px;
    color: #71717a;
  }

  /* Detail Panel */
  .detail-panel {
    grid-column: span 2;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .detail-header h3 {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #e4e4e7;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .detail-header svg {
    width: 24px;
    height: 24px;
    color: #667eea;
  }

  .close-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
    color: #ef4444;
  }

  .close-btn svg {
    width: 18px;
    height: 18px;
  }

  .detail-content {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .detail-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .detail-row.full-width {
    grid-column: span 2;
  }

  .detail-label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .detail-label svg {
    width: 16px;
    height: 16px;
    color: #667eea;
  }

  .detail-value {
    color: #e4e4e7;
    font-size: 0.95rem;
  }

  .contract-type-badge {
    display: inline-block;
    padding: 6px 16px;
    border: 1px solid;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .detail-content-text {
    color: #d4d4d8;
    line-height: 1.7;
    white-space: pre-wrap;
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
  }

  .metadata-pre {
    background: rgba(0, 0, 0, 0.3);
    padding: 16px;
    border-radius: 12px;
    color: #a1a1aa;
    font-size: 0.8rem;
    overflow-x: auto;
    font-family: 'Monaco', 'Menlo', monospace;
  }

  @media (max-width: 900px) {
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

  @media (max-width: 640px) {
    .contracts-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }

    .refresh-btn {
      width: 100%;
      justify-content: center;
    }

    .header-content {
      flex-direction: column;
      text-align: center;
      width: 100%;
    }
  }
</style>
