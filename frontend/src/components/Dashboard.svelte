<script>
  import { onMount } from 'svelte';
  import { fly, fade } from 'svelte/transition';
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

  const statIcons = {
    blocks: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
    entries: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    pending: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    valid: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    invalid: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
    unknown: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  };
</script>

<div class="dashboard" in:fly={{ y: 20, duration: 400 }}>
  <div class="dashboard-header">
    <h2>Dashboard</h2>
    <p class="subtitle">Real-time blockchain overview</p>
  </div>

  {#if loading}
    <div class="loading-container" in:fade>
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <p>Loading chain data...</p>
    </div>
  {:else if error}
    <div class="error-container" in:fly={{ y: 20, duration: 300 }}>
      <div class="error-card">
        <div class="error-icon-wrapper">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </div>
        <h3>Backend Not Connected</h3>
        {#if error.includes('<!DOCTYPE') || error.includes('Unexpected token')}
          <p class="error-message">The NatLangChain API server is not running.</p>
          <div class="error-instructions">
            <p class="instruction-title">To start the backend:</p>
            <ol>
              <li><span class="step-number">1</span> Open a terminal in the NatLangChain directory</li>
              <li><span class="step-number">2</span> Run: <code>python src/api.py</code></li>
              <li><span class="step-number">3</span> Wait for "Running on http://localhost:5000"</li>
              <li><span class="step-number">4</span> Click Retry below</li>
            </ol>
          </div>
        {:else}
          <p class="error-message">{error}</p>
        {/if}
        <button class="retry-button" on:click={loadDashboard}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
          </svg>
          Retry Connection
        </button>
      </div>
    </div>
  {:else if chainInfo}
    <div class="stats-grid">
      {#each [
        { key: 'blocks', icon: statIcons.blocks, value: chainInfo.length || 0, label: 'Total Blocks', tooltip: { text: 'Blocks form the immutable chain. Each block contains one or more entries and links to the previous block.', ncipRef: 'NCIP-001' }, color: 'blue' },
        { key: 'entries', icon: statIcons.entries, value: chainInfo.total_entries || 0, label: 'Total Entries', tooltip: ncipDefinitions.entry, color: 'purple' },
        { key: 'pending', icon: statIcons.pending, value: pendingCount, label: 'Pending Entries', tooltip: ncipDefinitions.pendingEntries, color: 'amber' },
        { key: 'status', icon: isValid === true ? statIcons.valid : isValid === false ? statIcons.invalid : statIcons.unknown, value: isValid === true ? 'Valid' : isValid === false ? 'Invalid' : 'Unknown', label: 'Chain Status', tooltip: { text: isValid === true ? ncipDefinitions.chainValid.text : isValid === false ? ncipDefinitions.chainInvalid.text : 'Chain validation status is pending.', ncipRef: isValid === true ? ncipDefinitions.chainValid.ncipRef : ncipDefinitions.chainInvalid.ncipRef }, color: isValid === true ? 'green' : isValid === false ? 'red' : 'gray', isStatus: true }
      ] as stat, i}
        <div
          class="stat-card {stat.color}"
          class:valid={stat.key === 'status' && isValid === true}
          class:invalid={stat.key === 'status' && isValid === false}
          in:fly={{ y: 20, duration: 400, delay: i * 100 }}
        >
          <Tooltip text={stat.tooltip.text} ncipRef={stat.tooltip.ncipRef} position="bottom">
            <div class="stat-inner">
              <div class="stat-icon-wrapper {stat.color}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d={stat.icon} />
                </svg>
              </div>
              <div class="stat-content">
                <div class="stat-value">{stat.value}</div>
                <div class="stat-label">{stat.label}</div>
              </div>
              <div class="stat-glow {stat.color}"></div>
            </div>
          </Tooltip>
        </div>
      {/each}
    </div>

    {#if chainInfo.latest_block}
      <div class="latest-block" in:fly={{ y: 20, duration: 400, delay: 400 }}>
        <div class="block-header">
          <div class="block-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            <h3>Latest Block</h3>
          </div>
          <span class="block-badge">Block #{chainInfo.latest_block.index}</span>
        </div>
        <div class="block-info">
          <div class="info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="4" y1="9" x2="20" y2="9" />
                <line x1="4" y1="15" x2="20" y2="15" />
                <line x1="10" y1="3" x2="8" y2="21" />
                <line x1="16" y1="3" x2="14" y2="21" />
              </svg>
            </div>
            <div class="info-content">
              <span class="info-label">Hash</span>
              <span class="info-value hash">{chainInfo.latest_block.hash?.slice(0, 24)}...</span>
            </div>
            <button class="copy-btn" on:click={() => navigator.clipboard.writeText(chainInfo.latest_block.hash)} title="Copy full hash">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
              </svg>
            </button>
          </div>
          <div class="info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <div class="info-content">
              <span class="info-label">Timestamp</span>
              <span class="info-value">{new Date(chainInfo.latest_block.timestamp).toLocaleString()}</span>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </div>
            <div class="info-content">
              <span class="info-label">Entries in Block</span>
              <span class="info-value">{chainInfo.latest_block.entries?.length || 0}</span>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <div class="quick-actions" in:fly={{ y: 20, duration: 400, delay: 500 }}>
      <h3>Quick Actions</h3>
      <div class="actions-grid">
        <button class="action-card" on:click={loadDashboard}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
          </svg>
          <span>Refresh Data</span>
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .dashboard {
    max-width: 1200px;
    margin: 0 auto;
  }

  .dashboard-header {
    margin-bottom: 32px;
  }

  .dashboard-header h2 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #667eea 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }

  .subtitle {
    color: #71717a;
    font-size: 1rem;
  }

  /* Loading State */
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
    to { transform: rotate(360deg); }
  }

  .loading-container p {
    color: #a1a1aa;
    font-size: 1rem;
  }

  /* Error State */
  .error-container {
    display: flex;
    justify-content: center;
    padding: 40px 20px;
  }

  .error-card {
    max-width: 500px;
    background: rgba(239, 68, 68, 0.05);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 20px;
    padding: 40px;
    text-align: center;
  }

  .error-icon-wrapper {
    width: 64px;
    height: 64px;
    margin: 0 auto 20px;
    padding: 16px;
    background: rgba(239, 68, 68, 0.1);
    border-radius: 16px;
    color: #ef4444;
  }

  .error-icon-wrapper svg {
    width: 100%;
    height: 100%;
  }

  .error-card h3 {
    color: #ef4444;
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .error-message {
    color: #a1a1aa;
    margin-bottom: 20px;
  }

  .error-instructions {
    text-align: left;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }

  .instruction-title {
    color: #e4e4e7;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .error-instructions ol {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .error-instructions li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin: 10px 0;
    color: #d4d4d8;
    line-height: 1.6;
  }

  .step-number {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(102, 126, 234, 0.2);
    color: #667eea;
    border-radius: 50%;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .error-instructions code {
    background: rgba(102, 126, 234, 0.2);
    color: #667eea;
    padding: 4px 8px;
    border-radius: 6px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.875rem;
  }

  .retry-button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .retry-button svg {
    width: 18px;
    height: 18px;
  }

  .retry-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(239, 68, 68, 0.3);
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .stat-card:hover {
    transform: translateY(-4px);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
  }

  .stat-inner {
    position: relative;
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .stat-icon-wrapper {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    flex-shrink: 0;
  }

  .stat-icon-wrapper.blue {
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
  }

  .stat-icon-wrapper.purple {
    background: rgba(168, 85, 247, 0.15);
    color: #a855f7;
  }

  .stat-icon-wrapper.amber {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
  }

  .stat-icon-wrapper.green {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .stat-icon-wrapper.red {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .stat-icon-wrapper.gray {
    background: rgba(113, 113, 122, 0.15);
    color: #71717a;
  }

  .stat-icon-wrapper svg {
    width: 28px;
    height: 28px;
  }

  .stat-content {
    flex: 1;
    min-width: 0;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #e4e4e7;
    line-height: 1.2;
  }

  .stat-label {
    color: #71717a;
    font-size: 0.875rem;
    margin-top: 4px;
  }

  .stat-glow {
    position: absolute;
    top: -50%;
    right: -50%;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    filter: blur(60px);
    opacity: 0.15;
    pointer-events: none;
  }

  .stat-glow.blue { background: #667eea; }
  .stat-glow.purple { background: #a855f7; }
  .stat-glow.amber { background: #f59e0b; }
  .stat-glow.green { background: #22c55e; }
  .stat-glow.red { background: #ef4444; }
  .stat-glow.gray { background: #71717a; }

  .stat-card.valid {
    border-color: rgba(34, 197, 94, 0.3);
  }

  .stat-card.invalid {
    border-color: rgba(239, 68, 68, 0.3);
  }

  /* Latest Block */
  .latest-block {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 24px;
  }

  .block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .block-title {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #e4e4e7;
  }

  .block-title svg {
    width: 24px;
    height: 24px;
    color: #667eea;
  }

  .block-title h3 {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .block-badge {
    padding: 6px 14px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .block-info {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .info-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    transition: background 0.2s ease;
  }

  .info-item:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .info-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 10px;
    color: #667eea;
    flex-shrink: 0;
  }

  .info-icon svg {
    width: 20px;
    height: 20px;
  }

  .info-content {
    flex: 1;
    min-width: 0;
  }

  .info-label {
    display: block;
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }

  .info-value {
    color: #e4e4e7;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9rem;
    word-break: break-all;
  }

  .info-value.hash {
    color: #a5b4fc;
  }

  .copy-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .copy-btn:hover {
    background: rgba(102, 126, 234, 0.2);
    border-color: rgba(102, 126, 234, 0.3);
    color: #667eea;
  }

  .copy-btn svg {
    width: 16px;
    height: 16px;
  }

  /* Quick Actions */
  .quick-actions {
    margin-top: 8px;
  }

  .quick-actions h3 {
    color: #a1a1aa;
    font-size: 0.875rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
  }

  .actions-grid {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .action-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 20px;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    color: #a1a1aa;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .action-card:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
    color: #e4e4e7;
    transform: translateY(-2px);
  }

  .action-card svg {
    width: 18px;
    height: 18px;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .dashboard-header h2 {
      font-size: 1.5rem;
    }

    .stats-grid {
      grid-template-columns: 1fr;
    }

    .stat-inner {
      padding: 20px;
    }

    .stat-value {
      font-size: 1.5rem;
    }

    .block-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .info-item {
      flex-wrap: wrap;
    }
  }
</style>
