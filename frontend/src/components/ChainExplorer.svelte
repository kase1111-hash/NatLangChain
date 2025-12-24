<script>
  import { onMount } from 'svelte';
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
      // Ensure blocks is always an array
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
</script>

<div class="explorer">
  <div class="explorer-header">
    <h2>Chain Explorer</h2>
    <button class="refresh-btn" on:click={loadChain}>↻ Refresh</button>
  </div>

  {#if loading}
    <div class="loading">Loading blockchain...</div>
  {:else if error}
    <div class="error">Error: {error}</div>
  {:else}
    <div class="explorer-layout">
      <div class="blocks-list">
        <h3>Blocks ({blocks.length})</h3>
        <div class="blocks-scroll">
          {#each blocks.slice().reverse() as block}
            <button
              class="block-item"
              class:selected={selectedBlock?.index === block.index}
              on:click={() => selectBlock(block.index)}
            >
              <div class="block-header">
                <span class="block-index">#{block.index}</span>
                <span class="block-entries">{block.entries?.length || 0} entries</span>
              </div>
              <div class="block-hash">{formatHash(block.hash)}</div>
              <div class="block-time">{formatTimestamp(block.timestamp)}</div>
            </button>
          {/each}
        </div>
      </div>

      <div class="block-details">
        {#if selectedBlock}
          <h3>Block #{selectedBlock.index}</h3>

          <div class="detail-section">
            <div class="detail-row">
              <span class="detail-label">Hash:</span>
              <span class="detail-value mono">{selectedBlock.hash || 'N/A'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Previous Hash:</span>
              <span class="detail-value mono">{selectedBlock.previous_hash || 'N/A'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Timestamp:</span>
              <span class="detail-value">{formatTimestamp(selectedBlock.timestamp)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Nonce:</span>
              <span class="detail-value">{selectedBlock.nonce ?? 'N/A'}</span>
            </div>
          </div>

          <div class="entries-section">
            <h4>Entries ({selectedBlock.entries?.length || 0})</h4>
            {#each selectedBlock.entries || [] as entry, i}
              <div class="entry-card">
                <div class="entry-header">
                  <span class="entry-author">{entry.author}</span>
                  <span class="entry-time">{formatTimestamp(entry.timestamp)}</span>
                </div>
                <div class="entry-intent">
                  <strong>Intent:</strong> {entry.intent}
                </div>
                <div class="entry-content">{entry.content}</div>
                {#if entry.metadata && Object.keys(entry.metadata).length > 0}
                  <div class="entry-metadata">
                    <details>
                      <summary>Metadata</summary>
                      <pre>{JSON.stringify(entry.metadata, null, 2)}</pre>
                    </details>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else}
          <div class="no-selection">
            <p>Select a block to view details</p>
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
  }

  .explorer-header {
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

  .explorer-layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 20px;
    height: 100%;
  }

  .blocks-list {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
  }

  .blocks-list h3 {
    margin-bottom: 12px;
    color: #e4e4e7;
    font-size: 1rem;
  }

  .blocks-scroll {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .block-item {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
  }

  .block-item:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.15);
  }

  .block-item.selected {
    background: rgba(102, 126, 234, 0.2);
    border-color: #667eea;
  }

  .block-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .block-index {
    font-weight: 600;
    color: #667eea;
  }

  .block-entries {
    font-size: 0.75rem;
    color: #a1a1aa;
  }

  .block-hash {
    font-family: monospace;
    font-size: 0.75rem;
    color: #71717a;
    margin-bottom: 4px;
  }

  .block-time {
    font-size: 0.75rem;
    color: #a1a1aa;
  }

  .block-details {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    overflow-y: auto;
  }

  .block-details h3 {
    margin-bottom: 16px;
    color: #e4e4e7;
  }

  .no-selection {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #71717a;
  }

  .detail-section {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;
  }

  .detail-row {
    display: flex;
    margin-bottom: 8px;
    gap: 12px;
  }

  .detail-label {
    color: #a1a1aa;
    min-width: 120px;
  }

  .detail-value {
    color: #e4e4e7;
    word-break: break-all;
  }

  .detail-value.mono {
    font-family: monospace;
    font-size: 0.85rem;
    color: #667eea;
  }

  .entries-section h4 {
    margin-bottom: 12px;
    color: #e4e4e7;
  }

  .entry-card {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
  }

  .entry-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .entry-author {
    font-weight: 600;
    color: #667eea;
  }

  .entry-time {
    font-size: 0.75rem;
    color: #71717a;
  }

  .entry-intent {
    font-size: 0.875rem;
    color: #a1a1aa;
    margin-bottom: 8px;
  }

  .entry-content {
    color: #e4e4e7;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .entry-metadata {
    margin-top: 12px;
  }

  .entry-metadata summary {
    cursor: pointer;
    color: #a1a1aa;
    font-size: 0.875rem;
  }

  .entry-metadata pre {
    margin-top: 8px;
    padding: 12px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 6px;
    font-size: 0.75rem;
    overflow-x: auto;
    color: #a1a1aa;
  }

  @media (max-width: 768px) {
    .explorer-layout {
      grid-template-columns: 1fr;
    }

    .blocks-list {
      max-height: 200px;
    }
  }
</style>
