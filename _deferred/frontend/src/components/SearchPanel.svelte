<script>
  import { fly, scale } from 'svelte/transition';
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
      error = `Search failed: ${e.message}`;
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

  const icons = {
    search: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
    brain:
      'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    text: 'M4 6h16M4 12h16m-7 6h7',
    clear: 'M6 18L18 6M6 6l12 12',
    block: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
    user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    clock: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
    target:
      'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    lightbulb:
      'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  };
</script>

<div class="search-panel" in:fly={{ y: 20, duration: 400 }}>
  <div class="search-header">
    <div class="header-icon">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d={icons.search} />
      </svg>
    </div>
    <div class="header-text">
      <h2>Search Entries</h2>
      <p class="subtitle">Find content across the blockchain</p>
    </div>
  </div>

  <div class="search-container" in:fly={{ y: 10, duration: 300, delay: 100 }}>
    <div class="search-box">
      <div class="search-input-wrapper">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d={icons.search} />
        </svg>
        <input
          type="text"
          bind:value={query}
          on:keydown={handleKeydown}
          placeholder="Search for entries..."
          class="search-input"
        />
        {#if query}
          <button class="clear-input-btn" on:click={clearSearch}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d={icons.clear} />
            </svg>
          </button>
        {/if}
      </div>
      <button class="search-btn" on:click={handleSearch} disabled={searching || !query.trim()}>
        {#if searching}
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
            <path d={icons.search} />
          </svg>
        {/if}
        <span>{searching ? 'Searching...' : 'Search'}</span>
      </button>
    </div>

    <div class="search-options">
      <div class="option-group">
        <Tooltip
          text={ncipDefinitions.basicSearch.text}
          ncipRef={ncipDefinitions.basicSearch.ncipRef}
          position="bottom"
        >
          <label class="radio-option" class:selected={searchType === 'basic'}>
            <input type="radio" bind:group={searchType} value="basic" />
            <div class="radio-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.text} />
              </svg>
            </div>
            <span>Basic Search</span>
          </label>
        </Tooltip>
        <Tooltip
          text={ncipDefinitions.semanticSearch.text}
          ncipRef={ncipDefinitions.semanticSearch.ncipRef}
          position="bottom"
        >
          <label class="radio-option" class:selected={searchType === 'semantic'}>
            <input type="radio" bind:group={searchType} value="semantic" />
            <div class="radio-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d={icons.brain} />
              </svg>
            </div>
            <span>Semantic Search</span>
          </label>
        </Tooltip>
      </div>

      <div class="limit-group">
        <label for="limit">Results:</label>
        <div class="select-wrapper">
          <select id="limit" bind:value={limit}>
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </div>
    </div>
  </div>

  {#if error}
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
  {/if}

  {#if results}
    <div class="results-section" in:fly={{ y: 20, duration: 300 }}>
      <div class="results-header">
        <h3>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Results
        </h3>
        <div class="results-meta">
          <span class="results-count">{results.results?.length || 0} found</span>
          {#if results.search_type}
            <span class="search-type-badge" class:semantic={results.search_type === 'semantic'}>
              {results.search_type === 'semantic' ? 'Semantic' : 'Basic'}
            </span>
          {/if}
        </div>
      </div>

      {#if results.results && results.results.length > 0}
        <div class="results-list">
          {#each results.results as result, i}
            <div class="result-card" in:fly={{ y: 10, duration: 200, delay: i * 50 }}>
              <div class="result-header">
                <span class="result-number">#{i + 1}</span>
                {#if result.score !== undefined}
                  <span class="result-score">
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
                    {(result.score * 100).toFixed(1)}%
                  </span>
                {/if}
                <span class="result-block">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <path d={icons.block} />
                  </svg>
                  Block #{result.block_index}
                </span>
              </div>

              <div class="result-meta">
                <span class="result-author">
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
                  {result.author}
                </span>
                <span class="result-time">
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
                  {formatTimestamp(result.timestamp)}
                </span>
              </div>

              <div class="result-intent">
                <span class="intent-label">Intent</span>
                <span class="intent-value">{result.intent}</span>
              </div>

              <div class="result-content">
                {#if searchType === 'basic'}
                  <!-- eslint-disable-next-line svelte/no-at-html-tags -- Safe: highlightQuery only wraps text in <mark> tags -->
                  {@html highlightQuery(result.content, query)}
                {:else}
                  {result.content}
                {/if}
              </div>

              {#if result.metadata && Object.keys(result.metadata).length > 0}
                <details class="result-metadata">
                  <summary>
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <polyline points="9 18 15 12 9 6" />
                    </svg>
                    Metadata
                  </summary>
                  <pre>{JSON.stringify(result.metadata, null, 2)}</pre>
                </details>
              {/if}
            </div>
          {/each}
        </div>
      {:else}
        <div class="no-results">
          <div class="no-results-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d={icons.search} />
            </svg>
          </div>
          <p>No results found for "{query}"</p>
          <span class="hint">Try different keywords or switch to semantic search</span>
        </div>
      {/if}
    </div>
  {:else}
    <div class="search-tips" in:fly={{ y: 10, duration: 300, delay: 200 }}>
      <div class="tips-header">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d={icons.lightbulb} />
        </svg>
        <h3>Search Tips</h3>
      </div>
      <ul>
        <li>
          <strong>Basic Search</strong>
          <span>Matches exact words and phrases in entry content</span>
        </li>
        <li>
          <strong>Semantic Search</strong>
          <span>Finds entries with similar meaning using AI</span>
        </li>
        <li>
          <strong>Exact Phrases</strong>
          <span>Use quotes for exact phrase matching in basic search</span>
        </li>
        <li>
          <strong>Natural Language</strong>
          <span>Semantic search works best with conversational queries</span>
        </li>
      </ul>

      <div class="example-queries">
        <h4>Try these examples:</h4>
        <div class="example-btns">
          <button class="example-btn" on:click={() => (query = 'payment terms')}>
            payment terms
          </button>
          <button class="example-btn" on:click={() => (query = 'delivery agreement')}>
            delivery agreement
          </button>
          <button class="example-btn" on:click={() => (query = 'contract offer')}>
            contract offer
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .search-panel {
    max-width: 900px;
    margin: 0 auto;
  }

  .search-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
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

  .search-container {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
  }

  .search-box {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }

  .search-input-wrapper {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-input-wrapper > svg {
    position: absolute;
    left: 16px;
    width: 20px;
    height: 20px;
    color: #52525b;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 14px 48px 14px 48px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    color: #e4e4e7;
    font-size: 1rem;
    transition: all 0.3s ease;
  }

  .search-input:focus {
    outline: none;
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .search-input::placeholder {
    color: #52525b;
  }

  .clear-input-btn {
    position: absolute;
    right: 12px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    border-radius: 6px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.2s;
  }

  .clear-input-btn:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  .clear-input-btn svg {
    width: 14px;
    height: 14px;
  }

  .search-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 28px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 14px;
    color: white;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  }

  .search-btn svg {
    width: 18px;
    height: 18px;
  }

  .search-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  }

  .search-btn:disabled {
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

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
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
    gap: 12px;
  }

  .radio-option {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .radio-option:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.15);
  }

  .radio-option.selected {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.4);
    color: #e4e4e7;
  }

  .radio-option input {
    display: none;
  }

  .radio-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .radio-icon svg {
    width: 16px;
    height: 16px;
  }

  .radio-option.selected .radio-icon {
    color: #667eea;
  }

  .limit-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .limit-group label {
    color: #71717a;
    font-size: 0.875rem;
  }

  .select-wrapper {
    position: relative;
  }

  .select-wrapper select {
    appearance: none;
    padding: 10px 36px 10px 14px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #e4e4e7;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .select-wrapper select:focus {
    outline: none;
    border-color: #667eea;
  }

  .select-wrapper svg {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    color: #71717a;
    pointer-events: none;
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

  .results-section {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    overflow: hidden;
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .results-header h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e4e4e7;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .results-header h3 svg {
    width: 20px;
    height: 20px;
    color: #667eea;
  }

  .results-meta {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .results-count {
    color: #71717a;
    font-size: 0.9rem;
  }

  .search-type-badge {
    padding: 6px 14px;
    background: rgba(102, 126, 234, 0.1);
    border: 1px solid rgba(102, 126, 234, 0.3);
    color: #667eea;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .search-type-badge.semantic {
    background: rgba(168, 85, 247, 0.1);
    border-color: rgba(168, 85, 247, 0.3);
    color: #a855f7;
  }

  .results-list {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .result-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    transition: all 0.2s ease;
  }

  .result-card:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.12);
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
  }

  .result-number {
    font-weight: 700;
    font-size: 1rem;
    color: #667eea;
  }

  .result-score {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    color: #22c55e;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .result-score svg {
    width: 14px;
    height: 14px;
  }

  .result-block {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    font-size: 0.8rem;
    color: #71717a;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
  }

  .result-block svg {
    width: 14px;
    height: 14px;
  }

  .result-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .result-author,
  .result-time {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
  }

  .result-author {
    font-weight: 600;
    color: #e4e4e7;
  }

  .result-author svg {
    width: 16px;
    height: 16px;
    color: #667eea;
  }

  .result-time {
    color: #52525b;
  }

  .result-time svg {
    width: 14px;
    height: 14px;
  }

  .result-intent {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
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

  .result-content {
    color: #d4d4d8;
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .result-content :global(mark) {
    background: rgba(245, 158, 11, 0.3);
    color: #f59e0b;
    padding: 2px 4px;
    border-radius: 4px;
  }

  .result-metadata {
    margin-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding-top: 14px;
  }

  .result-metadata summary {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    color: #71717a;
    font-size: 0.85rem;
    transition: color 0.2s;
  }

  .result-metadata summary:hover {
    color: #a1a1aa;
  }

  .result-metadata summary svg {
    width: 14px;
    height: 14px;
    transition: transform 0.2s;
  }

  .result-metadata details[open] summary svg {
    transform: rotate(90deg);
  }

  .result-metadata pre {
    margin-top: 12px;
    padding: 14px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 10px;
    font-size: 0.75rem;
    overflow-x: auto;
    color: #a1a1aa;
    font-family: 'Monaco', 'Menlo', monospace;
  }

  .no-results {
    text-align: center;
    padding: 60px 20px;
  }

  .no-results-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 20px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 16px;
    color: #3f3f46;
  }

  .no-results-icon svg {
    width: 100%;
    height: 100%;
  }

  .no-results p {
    color: #71717a;
    font-size: 1.1rem;
    margin-bottom: 8px;
  }

  .hint {
    font-size: 0.9rem;
    color: #52525b;
  }

  .search-tips {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 28px;
  }

  .tips-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .tips-header svg {
    width: 24px;
    height: 24px;
    color: #f59e0b;
  }

  .tips-header h3 {
    color: #e4e4e7;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .search-tips ul {
    list-style: none;
    padding: 0;
    margin: 0 0 28px 0;
  }

  .search-tips li {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  .search-tips li:last-child {
    border-bottom: none;
  }

  .search-tips li strong {
    color: #e4e4e7;
    font-size: 0.9rem;
  }

  .search-tips li span {
    color: #71717a;
    font-size: 0.85rem;
  }

  .example-queries h4 {
    color: #71717a;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 14px;
  }

  .example-btns {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .example-btn {
    padding: 10px 18px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #667eea;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s ease;
  }

  .example-btn:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
    transform: translateY(-2px);
  }

  @media (max-width: 768px) {
    .search-header {
      flex-direction: column;
      text-align: center;
    }

    .search-box {
      flex-direction: column;
    }

    .search-btn {
      width: 100%;
      justify-content: center;
    }

    .search-options {
      flex-direction: column;
      align-items: stretch;
    }

    .option-group {
      flex-direction: column;
    }

    .result-meta {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
