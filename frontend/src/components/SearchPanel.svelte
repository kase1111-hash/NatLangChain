<script>
  import { searchEntries, semanticSearch } from '../lib/api.js';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  let query = '';
  let searchType = 'basic';
  let limit = 10;
  let searching = false;
  let results = null;
  let error = null;

  async function handleSearch() {
    if (!query.trim()) return;

    searching = true;
    results = null;
    error = null;

    try {
      if (searchType === 'semantic') {
        results = await semanticSearch(query, limit);
      } else {
        results = await searchEntries(query, limit);
      }
    } catch (e) {
      error = 'Search failed: ' + e.message;
    } finally {
      searching = false;
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  function formatTimestamp(ts) {
    if (!ts) return 'N/A';
    return new Date(ts).toLocaleString();
  }

  function highlightQuery(text, searchQuery) {
    if (!text || !searchQuery) return text;
    const regex = new RegExp(`(${escapeRegex(searchQuery)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function clearSearch() {
    query = '';
    results = null;
    error = null;
  }
</script>

<div class="search-panel">
  <h2>Search Entries</h2>

  <div class="search-container">
    <div class="search-box">
      <input
        type="text"
        bind:value={query}
        on:keydown={handleKeydown}
        placeholder="Search for entries..."
        class="search-input"
      />
      <button
        class="search-btn"
        on:click={handleSearch}
        disabled={searching || !query.trim()}
      >
        {searching ? 'Searching...' : 'Search'}
      </button>
      {#if query}
        <button class="clear-btn" on:click={clearSearch}>Clear</button>
      {/if}
    </div>

    <div class="search-options">
      <div class="option-group">
        <Tooltip text={ncipDefinitions.basicSearch.text} ncipRef={ncipDefinitions.basicSearch.ncipRef} position="bottom">
          <label class="radio-label">
            <input type="radio" bind:group={searchType} value="basic" />
            <span>Basic Search</span>
          </label>
        </Tooltip>
        <Tooltip text={ncipDefinitions.semanticSearch.text} ncipRef={ncipDefinitions.semanticSearch.ncipRef} position="bottom">
          <label class="radio-label">
            <input type="radio" bind:group={searchType} value="semantic" />
            <span>Semantic Search</span>
          </label>
        </Tooltip>
      </div>

      <div class="limit-group">
        <label for="limit">Results:</label>
        <select id="limit" bind:value={limit}>
          <option value={5}>5</option>
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
    </div>
  </div>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if results}
    <div class="results-section">
      <div class="results-header">
        <h3>Results ({results.results?.length || 0})</h3>
        {#if results.search_type}
          <span class="search-type-badge">
            {results.search_type === 'semantic' ? 'Semantic' : 'Basic'} Search
          </span>
        {/if}
      </div>

      {#if results.results && results.results.length > 0}
        <div class="results-list">
          {#each results.results as result, i}
            <div class="result-card">
              <div class="result-header">
                <span class="result-number">#{i + 1}</span>
                {#if result.score !== undefined}
                  <span class="result-score">
                    Score: {(result.score * 100).toFixed(1)}%
                  </span>
                {/if}
                <span class="result-block">Block #{result.block_index}</span>
              </div>

              <div class="result-meta">
                <span class="result-author">{result.author}</span>
                <span class="result-time">{formatTimestamp(result.timestamp)}</span>
              </div>

              <div class="result-intent">
                <strong>Intent:</strong> {result.intent}
              </div>

              <div class="result-content">
                {#if searchType === 'basic'}
                  {@html highlightQuery(result.content, query)}
                {:else}
                  {result.content}
                {/if}
              </div>

              {#if result.metadata && Object.keys(result.metadata).length > 0}
                <details class="result-metadata">
                  <summary>Metadata</summary>
                  <pre>{JSON.stringify(result.metadata, null, 2)}</pre>
                </details>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <div class="no-results">
          <p>No results found for "{query}"</p>
          <p class="hint">Try different keywords or switch to semantic search</p>
        </div>
      {/if}
    </div>
  {:else}
    <div class="search-tips">
      <h3>Search Tips</h3>
      <ul>
        <li><strong>Basic Search:</strong> Matches exact words and phrases in entry content</li>
        <li><strong>Semantic Search:</strong> Finds entries with similar meaning using AI understanding</li>
        <li>Use quotes for exact phrase matching in basic search</li>
        <li>Semantic search works best with natural language queries</li>
      </ul>

      <div class="example-queries">
        <h4>Example Queries</h4>
        <button class="example-btn" on:click={() => query = 'payment terms'}>
          payment terms
        </button>
        <button class="example-btn" on:click={() => query = 'delivery agreement'}>
          delivery agreement
        </button>
        <button class="example-btn" on:click={() => query = 'contract offer'}>
          contract offer
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  .search-panel {
    max-width: 900px;
    margin: 0 auto;
  }

  h2 {
    font-size: 1.5rem;
    color: #e4e4e7;
    margin-bottom: 24px;
  }

  .search-container {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }

  .search-box {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }

  .search-input {
    flex: 1;
    padding: 12px 16px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    color: #e4e4e7;
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    outline: none;
    border-color: #667eea;
  }

  .search-input::placeholder {
    color: #71717a;
  }

  .search-btn {
    padding: 12px 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .search-btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .clear-btn {
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    color: #a1a1aa;
    cursor: pointer;
    transition: all 0.2s;
  }

  .clear-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #e4e4e7;
  }

  .search-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }

  .option-group {
    display: flex;
    gap: 20px;
  }

  .radio-label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a1a1aa;
    cursor: pointer;
    transition: color 0.2s;
  }

  .radio-label:hover {
    color: #e4e4e7;
  }

  .radio-label input[type="radio"] {
    cursor: pointer;
  }

  .limit-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .limit-group label {
    color: #a1a1aa;
    font-size: 0.875rem;
  }

  .limit-group select {
    padding: 6px 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: #e4e4e7;
    cursor: pointer;
  }

  .error-message {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
  }

  .results-section {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .results-header h3 {
    color: #e4e4e7;
  }

  .search-type-badge {
    padding: 4px 12px;
    background: rgba(102, 126, 234, 0.2);
    color: #667eea;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .result-card {
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 16px;
    transition: border-color 0.2s;
  }

  .result-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .result-number {
    font-weight: 600;
    color: #667eea;
  }

  .result-score {
    padding: 2px 8px;
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
    border-radius: 4px;
    font-size: 0.75rem;
  }

  .result-block {
    margin-left: auto;
    font-size: 0.75rem;
    color: #71717a;
  }

  .result-meta {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .result-author {
    font-weight: 600;
    color: #e4e4e7;
  }

  .result-time {
    font-size: 0.75rem;
    color: #71717a;
  }

  .result-intent {
    font-size: 0.875rem;
    color: #a1a1aa;
    margin-bottom: 8px;
  }

  .result-intent strong {
    color: #71717a;
  }

  .result-content {
    color: #e4e4e7;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .result-content :global(mark) {
    background: rgba(245, 158, 11, 0.3);
    color: #f59e0b;
    padding: 0 2px;
    border-radius: 2px;
  }

  .result-metadata {
    margin-top: 12px;
  }

  .result-metadata summary {
    cursor: pointer;
    color: #71717a;
    font-size: 0.875rem;
  }

  .result-metadata pre {
    margin-top: 8px;
    padding: 12px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 6px;
    font-size: 0.75rem;
    color: #a1a1aa;
    overflow-x: auto;
  }

  .no-results {
    text-align: center;
    padding: 40px;
    color: #71717a;
  }

  .no-results .hint {
    font-size: 0.875rem;
    margin-top: 8px;
  }

  .search-tips {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 24px;
  }

  .search-tips h3 {
    color: #e4e4e7;
    margin-bottom: 16px;
  }

  .search-tips ul {
    list-style: none;
    padding: 0;
    margin: 0 0 24px 0;
  }

  .search-tips li {
    color: #a1a1aa;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .search-tips li:last-child {
    border-bottom: none;
  }

  .search-tips strong {
    color: #e4e4e7;
  }

  .example-queries h4 {
    color: #a1a1aa;
    font-size: 0.875rem;
    margin-bottom: 12px;
  }

  .example-btn {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #667eea;
    cursor: pointer;
    margin-right: 8px;
    margin-bottom: 8px;
    transition: all 0.2s;
  }

  .example-btn:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: #667eea;
  }

  @media (max-width: 768px) {
    .search-box {
      flex-direction: column;
    }

    .search-options {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
