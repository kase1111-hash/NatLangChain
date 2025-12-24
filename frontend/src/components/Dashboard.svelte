<script>
  import { onMount } from 'svelte';
  import { getChainInfo, validateChain, getPendingEntries } from '../lib/api.js';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  let chainInfo = null;
  let isValid = null;
  let pendingCount = 0;
  let loading = true;
  let error = null;

  onMount(async () => {
    await loadDashboard();
  });

  async function loadDashboard() {
    loading = true;
    error = null;
    try {
      const [chain, validation, pending] = await Promise.all([
        getChainInfo(),
        validateChain().catch(() => ({ valid: null })),
        getPendingEntries().catch(() => ({ entries: [] })),
      ]);
      chainInfo = chain;
      isValid = validation.valid;
      pendingCount = pending.entries?.length || 0;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="dashboard">
  <h2>Dashboard</h2>

  {#if loading}
    <div class="loading">Loading chain data...</div>
  {:else if error}
    <div class="error">
      <p>Error loading data: {error}</p>
      <button on:click={loadDashboard}>Retry</button>
    </div>
  {:else if chainInfo}
    <div class="stats-grid">
      <Tooltip text="Blocks form the immutable chain. Each block contains one or more entries and links to the previous block." ncipRef="NCIP-001" position="bottom">
        <div class="stat-card">
          <div class="stat-icon">🔗</div>
          <div class="stat-content">
            <div class="stat-value">{chainInfo.length || 0}</div>
            <div class="stat-label">Total Blocks</div>
          </div>
        </div>
      </Tooltip>

      <Tooltip text={ncipDefinitions.entry.text} ncipRef={ncipDefinitions.entry.ncipRef} position="bottom">
        <div class="stat-card">
          <div class="stat-icon">📝</div>
          <div class="stat-content">
            <div class="stat-value">{chainInfo.total_entries || 0}</div>
            <div class="stat-label">Total Entries</div>
          </div>
        </div>
      </Tooltip>

      <Tooltip text={ncipDefinitions.pendingEntries.text} ncipRef={ncipDefinitions.pendingEntries.ncipRef} position="bottom">
        <div class="stat-card">
          <div class="stat-icon">⏳</div>
          <div class="stat-content">
            <div class="stat-value">{pendingCount}</div>
            <div class="stat-label">Pending Entries</div>
          </div>
        </div>
      </Tooltip>

      <Tooltip text={isValid === true ? ncipDefinitions.chainValid.text : isValid === false ? ncipDefinitions.chainInvalid.text : 'Chain validation status is pending.'} ncipRef={isValid === true ? ncipDefinitions.chainValid.ncipRef : ncipDefinitions.chainInvalid.ncipRef} position="bottom">
        <div class="stat-card" class:valid={isValid === true} class:invalid={isValid === false}>
          <div class="stat-icon">{isValid === true ? '✅' : isValid === false ? '❌' : '❓'}</div>
          <div class="stat-content">
            <div class="stat-value">{isValid === true ? 'Valid' : isValid === false ? 'Invalid' : 'Unknown'}</div>
            <div class="stat-label">Chain Status</div>
          </div>
        </div>
      </Tooltip>
    </div>

    {#if chainInfo.latest_block}
      <div class="latest-block">
        <h3>Latest Block</h3>
        <div class="block-info">
          <div class="info-row">
            <span class="info-label">Index:</span>
            <span class="info-value">{chainInfo.latest_block.index}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Hash:</span>
            <span class="info-value hash">{chainInfo.latest_block.hash?.slice(0, 16)}...</span>
          </div>
          <div class="info-row">
            <span class="info-label">Timestamp:</span>
            <span class="info-value">{new Date(chainInfo.latest_block.timestamp).toLocaleString()}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Entries:</span>
            <span class="info-value">{chainInfo.latest_block.entries?.length || 0}</span>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .dashboard {
    max-width: 1000px;
    margin: 0 auto;
  }

  h2 {
    font-size: 1.5rem;
    margin-bottom: 24px;
    color: #e4e4e7;
  }

  .loading {
    text-align: center;
    padding: 40px;
    color: #a1a1aa;
  }

  .error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 20px;
    text-align: center;
  }

  .error button {
    margin-top: 12px;
    padding: 8px 16px;
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    transition: transform 0.2s ease;
  }

  .stat-card:hover {
    transform: translateY(-2px);
  }

  .stat-card.valid {
    border-color: rgba(34, 197, 94, 0.3);
    background: rgba(34, 197, 94, 0.1);
  }

  .stat-card.invalid {
    border-color: rgba(239, 68, 68, 0.3);
    background: rgba(239, 68, 68, 0.1);
  }

  .stat-icon {
    font-size: 2rem;
  }

  .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #e4e4e7;
  }

  .stat-label {
    color: #a1a1aa;
    font-size: 0.875rem;
  }

  .latest-block {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 24px;
  }

  .latest-block h3 {
    margin-bottom: 16px;
    color: #e4e4e7;
    font-size: 1.125rem;
  }

  .block-info {
    display: grid;
    gap: 12px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .info-label {
    color: #a1a1aa;
  }

  .info-value {
    color: #e4e4e7;
    font-family: monospace;
  }

  .info-value.hash {
    color: #667eea;
  }
</style>
