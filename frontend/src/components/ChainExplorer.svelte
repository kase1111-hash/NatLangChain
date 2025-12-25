<script>
  import { onMount } from 'svelte';
  import { fly, fade, scale } from 'svelte/transition';
  import { getChainInfo, getBlock } from '../lib/api.js';

  let blocks = [];
  let selectedBlock = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    await loadChain();
  });

  async function loadChain() {
    loading = true;
    error = null;
    try {
      const info = await getChainInfo();
      blocks = Array.isArray(info.chain) ? info.chain : [];
    } catch (e) {
      error = e.message || 'Failed to load chain';
      blocks = [];
    } finally {
      loading = false;
    }
  }

  async function selectBlock(index) {
    try {
      const block = await getBlock(index);
      selectedBlock = block;
    } catch (e) {
      console.error('Failed to load block:', e);
    }
  }

  function formatHash(hash) {
    if (!hash) return 'N/A';
    return hash.slice(0, 8) + '...' + hash.slice(-8);
  }

  function formatTimestamp(ts) {
    if (!ts) return 'N/A';
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  const icons = {
    refresh: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
    block: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
    hash: 'M7 20l4-16m2 16l4-16M6 9h14M4 15h14',
    clock: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    document: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    link: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1'
  };
</script>

<div class="explorer" in:fly={{ y: 20, duration: 400 }}>
  <div class="explorer-header">
    <div class="header-content">
      <div class="header-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d={icons.block} />
        </svg>
      </div>
      <div class="header-text">
        <h2>Chain Explorer</h2>
        <p class="subtitle">Browse and inspect blockchain blocks</p>
      </div>
    </div>
    <button class="refresh-btn" on:click={loadChain}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
      <p>Loading blockchain...</p>
    </div>
  {:else if error}
    <div class="error-container" in:fly={{ y: 20, duration: 300 }}>
      <div class="error-card">
        <div class="error-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p>Error: {error}</p>
        <button class="retry-btn" on:click={loadChain}>Retry</button>
      </div>
    </div>
  {:else}
    <div class="explorer-layout">
      <div class="blocks-panel" in:fly={{ x: -20, duration: 400, delay: 100 }}>
        <div class="panel-header">
          <h3>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d={icons.link} />
            </svg>
            Blocks
          </h3>
          <span class="block-count">{blocks.length}</span>
        </div>
        <div class="blocks-scroll">
          {#each blocks.slice().reverse() as block, i}
            <button
              class="block-item"
              class:selected={selectedBlock?.index === block.index}
              on:click={() => selectBlock(block.index)}
              in:fly={{ x: -10, duration: 200, delay: i * 30 }}
            >
              <div class="block-header">
                <span class="block-index">
                  <span class="index-hash">#</span>{block.index}
                </span>
                <span class="block-entries">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d={icons.document} />
                  </svg>
                  {block.entries?.length || 0}
                </span>
              </div>
              <div class="block-hash">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d={icons.hash} />
                </svg>
                {formatHash(block.hash)}
              </div>
              <div class="block-time">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d={icons.clock} />
                </svg>
                {formatTimestamp(block.timestamp)}
              </div>
              {#if selectedBlock?.index === block.index}
                <div class="selected-indicator"></div>
              {/if}
            </button>
          {/each}
        </div>
      </div>

      <div class="details-panel" in:fly={{ x: 20, duration: 400, delay: 200 }}>
        {#if selectedBlock}
          <div class="block-details" in:fade={{ duration: 200 }}>
            <div class="details-header">
              <div class="details-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d={icons.block} />
                </svg>
                <h3>Block #{selectedBlock.index}</h3>
              </div>
              <span class="block-badge">
                {selectedBlock.entries?.length || 0} entries
              </span>
            </div>

            <div class="detail-section">
              <div class="detail-grid">
                <div class="detail-item">
                  <div class="detail-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d={icons.hash} />
                    </svg>
                  </div>
                  <div class="detail-content">
                    <span class="detail-label">Hash</span>
                    <span class="detail-value mono">{selectedBlock.hash || 'N/A'}</span>
                  </div>
                  <button class="copy-btn" on:click={() => navigator.clipboard.writeText(selectedBlock.hash)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                    </svg>
                  </button>
                </div>

                <div class="detail-item">
                  <div class="detail-icon prev">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d={icons.link} />
                    </svg>
                  </div>
                  <div class="detail-content">
                    <span class="detail-label">Previous Hash</span>
                    <span class="detail-value mono prev">{selectedBlock.previous_hash || 'Genesis Block'}</span>
                  </div>
                </div>

                <div class="detail-item">
                  <div class="detail-icon time">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d={icons.clock} />
                    </svg>
                  </div>
                  <div class="detail-content">
                    <span class="detail-label">Timestamp</span>
                    <span class="detail-value">{formatTimestamp(selectedBlock.timestamp)}</span>
                  </div>
                </div>

                <div class="detail-item">
                  <div class="detail-icon nonce">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M12 2v4m0 12v4m10-10h-4M6 12H2m15.364-6.364l-2.828 2.828M9.464 14.536l-2.828 2.828m0-11.314l2.828 2.828m5.656 5.656l2.828 2.828" />
                    </svg>
                  </div>
                  <div class="detail-content">
                    <span class="detail-label">Nonce</span>
                    <span class="detail-value">{selectedBlock.nonce ?? 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="entries-section">
              <div class="entries-header">
                <h4>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d={icons.document} />
                  </svg>
                  Entries
                </h4>
                <span class="entries-count">{selectedBlock.entries?.length || 0}</span>
              </div>

              {#each selectedBlock.entries || [] as entry, i}
                <div class="entry-card" in:fly={{ y: 10, duration: 200, delay: i * 50 }}>
                  <div class="entry-header">
                    <div class="entry-author">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d={icons.user} />
                      </svg>
                      {entry.author}
                    </div>
                    <span class="entry-time">{formatTimestamp(entry.timestamp)}</span>
                  </div>
                  <div class="entry-intent">
                    <span class="intent-label">Intent</span>
                    <span class="intent-value">{entry.intent}</span>
                  </div>
                  <div class="entry-content">{entry.content}</div>
                  {#if entry.metadata && Object.keys(entry.metadata).length > 0}
                    <div class="entry-metadata">
                      <details>
                        <summary>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="9 18 15 12 9 6" />
                          </svg>
                          Metadata
                        </summary>
                        <pre>{JSON.stringify(entry.metadata, null, 2)}</pre>
                      </details>
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <div class="no-selection">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d={icons.block} />
              </svg>
            </div>
            <p>Select a block to view details</p>
            <span class="hint">Click on any block in the list</span>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .explorer {
    height: calc(100vh - 300px);
    min-height: 500px;
    display: flex;
    flex-direction: column;
  }

  .explorer-header {
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
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
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
  }

  /* Error */
  .error-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .error-card {
    text-align: center;
    padding: 40px;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 20px;
  }

  .error-icon {
    width: 48px;
    height: 48px;
    margin: 0 auto 16px;
    color: #ef4444;
  }

  .error-card p {
    color: #ef4444;
    margin-bottom: 20px;
  }

  .retry-btn {
    padding: 10px 20px;
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .retry-btn:hover {
    background: #dc2626;
  }

  /* Layout */
  .explorer-layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 24px;
    flex: 1;
    min-height: 0;
  }

  /* Blocks Panel */
  .blocks-panel {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .panel-header h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e4e4e7;
    font-size: 1rem;
    font-weight: 600;
  }

  .panel-header svg {
    width: 18px;
    height: 18px;
    color: #667eea;
  }

  .block-count {
    padding: 4px 12px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .blocks-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .block-item {
    position: relative;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 14px;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    width: 100%;
    overflow: hidden;
  }

  .block-item:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateX(4px);
  }

  .block-item.selected {
    background: rgba(102, 126, 234, 0.15);
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

  .block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .block-index {
    font-weight: 700;
    font-size: 1.1rem;
    color: #e4e4e7;
  }

  .index-hash {
    color: #667eea;
  }

  .block-entries {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.8rem;
    color: #71717a;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
  }

  .block-entries svg {
    width: 12px;
    height: 12px;
  }

  .block-hash, .block-time {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    color: #71717a;
    margin-bottom: 6px;
  }

  .block-hash svg, .block-time svg {
    width: 12px;
    height: 12px;
    color: #52525b;
  }

  /* Details Panel */
  .details-panel {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .block-details {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .details-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .details-title {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .details-title svg {
    width: 28px;
    height: 28px;
    color: #667eea;
  }

  .details-title h3 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #e4e4e7;
  }

  .block-badge {
    padding: 8px 16px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .detail-section {
    margin-bottom: 28px;
  }

  .detail-grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .detail-item {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 14px;
    transition: background 0.2s ease;
  }

  .detail-item:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .detail-icon {
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

  .detail-icon.prev {
    background: rgba(168, 85, 247, 0.1);
    color: #a855f7;
  }

  .detail-icon.time {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }

  .detail-icon.nonce {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }

  .detail-icon svg {
    width: 20px;
    height: 20px;
  }

  .detail-content {
    flex: 1;
    min-width: 0;
  }

  .detail-label {
    display: block;
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }

  .detail-value {
    color: #e4e4e7;
    font-size: 0.9rem;
    word-break: break-all;
  }

  .detail-value.mono {
    font-family: 'Monaco', 'Menlo', monospace;
    color: #a5b4fc;
    font-size: 0.8rem;
  }

  .detail-value.prev {
    color: #c4b5fd;
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
    flex-shrink: 0;
    margin-top: 4px;
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

  /* Entries Section */
  .entries-section {
    margin-top: 24px;
  }

  .entries-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }

  .entries-header h4 {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e4e4e7;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .entries-header svg {
    width: 20px;
    height: 20px;
    color: #667eea;
  }

  .entries-count {
    padding: 4px 12px;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 12px;
    color: #a5b4fc;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .entry-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
  }

  .entry-card:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .entry-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }

  .entry-author {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    color: #667eea;
  }

  .entry-author svg {
    width: 16px;
    height: 16px;
  }

  .entry-time {
    font-size: 0.75rem;
    color: #52525b;
  }

  .entry-intent {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    padding: 10px 14px;
    background: rgba(102, 126, 234, 0.05);
    border-radius: 10px;
  }

  .intent-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: #71717a;
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  .intent-value {
    color: #a5b4fc;
    font-size: 0.9rem;
  }

  .entry-content {
    color: #d4d4d8;
    line-height: 1.7;
    white-space: pre-wrap;
    font-size: 0.95rem;
  }

  .entry-metadata {
    margin-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding-top: 14px;
  }

  .entry-metadata summary {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    color: #71717a;
    font-size: 0.85rem;
    transition: color 0.2s;
  }

  .entry-metadata summary:hover {
    color: #a1a1aa;
  }

  .entry-metadata summary svg {
    width: 14px;
    height: 14px;
    transition: transform 0.2s;
  }

  .entry-metadata details[open] summary svg {
    transform: rotate(90deg);
  }

  .entry-metadata pre {
    margin-top: 12px;
    padding: 14px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 10px;
    font-size: 0.75rem;
    overflow-x: auto;
    color: #a1a1aa;
    font-family: 'Monaco', 'Menlo', monospace;
  }

  /* No Selection */
  .no-selection {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #52525b;
    text-align: center;
    padding: 40px;
  }

  .empty-icon {
    width: 80px;
    height: 80px;
    margin-bottom: 20px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 20px;
    color: #3f3f46;
  }

  .empty-icon svg {
    width: 100%;
    height: 100%;
  }

  .no-selection p {
    font-size: 1.1rem;
    color: #71717a;
    margin-bottom: 8px;
  }

  .hint {
    font-size: 0.85rem;
    color: #52525b;
  }

  /* Responsive */
  @media (max-width: 900px) {
    .explorer-layout {
      grid-template-columns: 1fr;
    }

    .blocks-panel {
      max-height: 250px;
    }

    .details-panel {
      min-height: 400px;
    }

    .header-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }
  }

  @media (max-width: 640px) {
    .explorer-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }

    .refresh-btn {
      width: 100%;
      justify-content: center;
    }

    .detail-item {
      flex-wrap: wrap;
    }

    .copy-btn {
      margin-left: 56px;
    }
  }
</style>
