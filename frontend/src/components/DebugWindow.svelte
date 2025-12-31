<script>
  import { onMount, onDestroy } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { settings, debugLogs, clearDebugLogs, debug } from '../lib/stores.js';

  let windowEl;
  let isDragging = false;
  let isResizing = false;
  let dragOffset = { x: 0, y: 0 };
  let position = { x: 20, y: 20 };
  let size = { width: 500, height: 400 };
  let isMinimized = false;
  let autoScroll = true;
  let filterLevel = 'all';
  let filterCategory = 'all';
  let searchQuery = '';
  let logsContainer;

  // Get unique categories from logs
  $: categories = [...new Set($debugLogs.map((log) => log.category))];

  // Filter logs based on level, category, and search
  $: filteredLogs = $debugLogs.filter((log) => {
    if (filterLevel !== 'all' && log.level !== filterLevel) return false;
    if (filterCategory !== 'all' && log.category !== filterCategory) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        log.message.toLowerCase().includes(query) ||
        log.category.toLowerCase().includes(query) ||
        (log.data && JSON.stringify(log.data).toLowerCase().includes(query))
      );
    }
    return true;
  });

  // Load saved position/size from settings
  const unsubscribe = settings.subscribe((s) => {
    if (s.debugWindowPosition) position = s.debugWindowPosition;
    if (s.debugWindowSize) size = s.debugWindowSize;
  });

  onMount(() => {
    debug.info('Debug', 'Debug window opened');
  });

  onDestroy(() => {
    unsubscribe();
  });

  // Auto-scroll to bottom when new logs arrive
  $: if (autoScroll && logsContainer && filteredLogs.length) {
    setTimeout(() => {
      if (logsContainer) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
      }
    }, 10);
  }

  function startDrag(e) {
    if (
      e.target.closest('.resize-handle') ||
      e.target.closest('button') ||
      e.target.closest('input') ||
      e.target.closest('select')
    )
      return;
    isDragging = true;
    dragOffset = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
    e.preventDefault();
  }

  function startResize(e) {
    isResizing = true;
    e.preventDefault();
    e.stopPropagation();
  }

  function handleMouseMove(e) {
    if (isDragging) {
      position = {
        x: Math.max(0, Math.min(window.innerWidth - size.width, e.clientX - dragOffset.x)),
        y: Math.max(0, Math.min(window.innerHeight - size.height, e.clientY - dragOffset.y)),
      };
    } else if (isResizing) {
      size = {
        width: Math.max(300, Math.min(window.innerWidth - position.x, e.clientX - position.x)),
        height: Math.max(200, Math.min(window.innerHeight - position.y, e.clientY - position.y)),
      };
    }
  }

  function handleMouseUp() {
    if (isDragging || isResizing) {
      // Save position/size to settings
      settings.update((s) => ({
        ...s,
        debugWindowPosition: position,
        debugWindowSize: size,
      }));
    }
    isDragging = false;
    isResizing = false;
  }

  function toggleMinimize() {
    isMinimized = !isMinimized;
  }

  function closeWindow() {
    settings.update((s) => ({ ...s, debugWindowEnabled: false }));
  }

  function getLevelColor(level) {
    switch (level) {
      case 'debug':
        return '#8b8b8b';
      case 'info':
        return '#60a5fa';
      case 'warn':
        return '#fbbf24';
      case 'error':
        return '#f87171';
      default:
        return '#a1a1aa';
    }
  }

  function getLevelIcon(level) {
    switch (level) {
      case 'debug':
        return 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4';
      case 'info':
        return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
      case 'warn':
        return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
      case 'error':
        return 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z';
      default:
        return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    }
  }

  function formatTimestamp(iso) {
    const date = new Date(iso);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  }

  function formatData(data) {
    if (!data) return null;
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }

  function copyLogs() {
    const text = filteredLogs
      .map(
        (log) =>
          `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.category}] ${log.message}${log.data ? `\n${formatData(log.data)}` : ''}`
      )
      .join('\n');
    navigator.clipboard.writeText(text);
    debug.info('Debug', 'Logs copied to clipboard');
  }
</script>

<svelte:window on:mousemove={handleMouseMove} on:mouseup={handleMouseUp} />

<div
  class="debug-window"
  class:minimized={isMinimized}
  bind:this={windowEl}
  style="left: {position.x}px; top: {position.y}px; width: {size.width}px; height: {isMinimized
    ? 'auto'
    : `${size.height}px`};"
  in:fly={{ y: 20, duration: 300 }}
  out:fade={{ duration: 150 }}
>
  <!-- Title bar -->
  <div
    class="title-bar"
    role="button"
    tabindex="0"
    on:mousedown={startDrag}
    on:keydown={(e) => e.key === 'Enter' && startDrag(e)}
  >
    <div class="title">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
      <span>Debug Console</span>
      <span class="log-count">{filteredLogs.length} / {$debugLogs.length}</span>
    </div>
    <div class="window-controls">
      <button
        class="control-btn"
        on:click={toggleMinimize}
        title={isMinimized ? 'Expand' : 'Minimize'}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          {#if isMinimized}
            <path
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          {:else}
            <path d="M20 12H4" />
          {/if}
        </svg>
      </button>
      <button class="control-btn close" on:click={closeWindow} title="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>

  {#if !isMinimized}
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="filters">
        <select bind:value={filterLevel} class="filter-select">
          <option value="all">All Levels</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warn">Warning</option>
          <option value="error">Error</option>
        </select>
        <select bind:value={filterCategory} class="filter-select">
          <option value="all">All Categories</option>
          {#each categories as cat}
            <option value={cat}>{cat}</option>
          {/each}
        </select>
        <input
          type="text"
          class="search-input"
          placeholder="Search logs..."
          bind:value={searchQuery}
        />
      </div>
      <div class="toolbar-actions">
        <label class="auto-scroll-toggle">
          <input type="checkbox" bind:checked={autoScroll} />
          <span>Auto-scroll</span>
        </label>
        <button class="toolbar-btn" on:click={copyLogs} title="Copy logs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path
              d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
            />
          </svg>
        </button>
        <button class="toolbar-btn" on:click={clearDebugLogs} title="Clear logs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Logs container -->
    <div class="logs-container" bind:this={logsContainer}>
      {#if filteredLogs.length === 0}
        <div class="no-logs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <span>No logs to display</span>
        </div>
      {:else}
        {#each filteredLogs as log (log.id)}
          <div class="log-entry" style="--level-color: {getLevelColor(log.level)}">
            <div class="log-header">
              <svg
                class="level-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke={getLevelColor(log.level)}
                stroke-width="2"
              >
                <path d={getLevelIcon(log.level)} />
              </svg>
              <span class="log-time">{formatTimestamp(log.timestamp)}</span>
              <span class="log-category">[{log.category}]</span>
              <span class="log-message">{log.message}</span>
            </div>
            {#if log.data}
              <pre class="log-data">{formatData(log.data)}</pre>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <!-- Resize handle -->
    <div
      class="resize-handle"
      role="button"
      tabindex="0"
      on:mousedown={startResize}
      on:keydown={(e) => e.key === 'Enter' && startResize(e)}
    >
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path
          d="M22 22H20V20H22V22ZM22 18H20V16H22V18ZM18 22H16V20H18V22ZM22 14H20V12H22V14ZM18 18H16V16H18V18ZM14 22H12V20H14V22Z"
        />
      </svg>
    </div>
  {/if}
</div>

<style>
  .debug-window {
    position: fixed;
    z-index: 9999;
    background: rgba(15, 15, 20, 0.95);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    box-shadow:
      0 20px 40px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.05) inset;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
  }

  .debug-window.minimized {
    height: auto !important;
  }

  .title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    cursor: move;
    user-select: none;
  }

  .title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a1a1aa;
    font-weight: 500;
  }

  .title svg {
    width: 16px;
    height: 16px;
    color: #667eea;
  }

  .log-count {
    font-size: 10px;
    padding: 2px 6px;
    background: rgba(102, 126, 234, 0.2);
    border-radius: 4px;
    color: #667eea;
  }

  .window-controls {
    display: flex;
    gap: 6px;
  }

  .control-btn {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 6px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .control-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
  }

  .control-btn.close:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }

  .control-btn svg {
    width: 14px;
    height: 14px;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    gap: 12px;
    flex-wrap: wrap;
  }

  .filters {
    display: flex;
    gap: 8px;
    flex: 1;
    min-width: 200px;
  }

  .filter-select,
  .search-input {
    padding: 6px 10px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #e4e4e7;
    font-size: 11px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s ease;
  }

  .filter-select:focus,
  .search-input:focus {
    border-color: rgba(102, 126, 234, 0.5);
  }

  .filter-select {
    min-width: 100px;
  }

  .search-input {
    flex: 1;
    min-width: 120px;
  }

  .search-input::placeholder {
    color: #52525b;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .auto-scroll-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #71717a;
    cursor: pointer;
  }

  .auto-scroll-toggle input {
    accent-color: #667eea;
  }

  .toolbar-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 6px;
    color: #71717a;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .toolbar-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
  }

  .toolbar-btn svg {
    width: 14px;
    height: 14px;
  }

  .logs-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 8px;
  }

  .no-logs {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #52525b;
    gap: 12px;
  }

  .no-logs svg {
    width: 48px;
    height: 48px;
    opacity: 0.5;
  }

  .log-entry {
    padding: 8px 10px;
    margin-bottom: 4px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 6px;
    border-left: 3px solid var(--level-color);
    transition: background 0.15s ease;
  }

  .log-entry:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .log-header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .level-icon {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
  }

  .log-time {
    color: #52525b;
    font-size: 10px;
    flex-shrink: 0;
  }

  .log-category {
    color: #667eea;
    font-size: 11px;
    flex-shrink: 0;
  }

  .log-message {
    color: #d4d4d8;
    word-break: break-word;
  }

  .log-data {
    margin-top: 6px;
    padding: 8px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    color: #a1a1aa;
    font-size: 10px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .resize-handle {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 20px;
    height: 20px;
    cursor: se-resize;
    color: #3f3f46;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .resize-handle:hover {
    color: #667eea;
  }

  .resize-handle svg {
    width: 12px;
    height: 12px;
  }

  /* Scrollbar styling */
  .logs-container::-webkit-scrollbar {
    width: 6px;
  }

  .logs-container::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 3px;
  }

  .logs-container::-webkit-scrollbar-thumb {
    background: rgba(102, 126, 234, 0.3);
    border-radius: 3px;
  }

  .logs-container::-webkit-scrollbar-thumb:hover {
    background: rgba(102, 126, 234, 0.5);
  }
</style>
