<script>
  import { onMount, onDestroy } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { debug } from '../lib/stores.js';
  import {
    getBoundaryStatus,
    getBoundaryMode,
    setBoundaryMode,
    triggerLockdown,
    getModeHistory,
    getBoundaryViolations,
    getSiemAlerts,
    acknowledgeSiemAlert,
    checkInput,
    getEnforcementStatus,
  } from '../lib/api.js';

  // State
  let status = null;
  let modeInfo = null;
  let modeHistory = [];
  let violations = [];
  let alerts = [];
  let enforcement = null;
  let loading = true;
  let error = null;
  let refreshInterval;

  // Mode change form
  let selectedMode = '';
  let modeChangeReason = '';
  let modeChangeLoading = false;
  let modeChangeError = null;

  // Security check form
  let checkText = '';
  let checkContext = 'user_input';
  let checkResult = null;
  let checkLoading = false;

  // Tab state
  let activeTab = 'overview';

  const MODES = [
    { id: 'open', label: 'Open', color: '#22c55e', description: 'Full access, casual use' },
    { id: 'restricted', label: 'Restricted', color: '#3b82f6', description: 'Research mode' },
    { id: 'trusted', label: 'Trusted', color: '#8b5cf6', description: 'VPN only, no USB' },
    { id: 'airgap', label: 'Airgap', color: '#f59e0b', description: 'Offline only' },
    { id: 'coldroom', label: 'Coldroom', color: '#ef4444', description: 'Display only' },
    { id: 'lockdown', label: 'Lockdown', color: '#dc2626', description: 'Emergency block' },
  ];

  async function loadData() {
    try {
      const results = await Promise.allSettled([
        getBoundaryStatus(),
        getBoundaryMode(),
        getModeHistory(20),
        getBoundaryViolations(50),
        getSiemAlerts(null, 20),
        getEnforcementStatus(),
      ]);

      if (results[0].status === 'fulfilled') status = results[0].value;
      if (results[1].status === 'fulfilled') {
        modeInfo = results[1].value;
        selectedMode = modeInfo.current_mode;
      }
      if (results[2].status === 'fulfilled') modeHistory = results[2].value.transitions || [];
      if (results[3].status === 'fulfilled') violations = results[3].value.violations || [];
      if (results[4].status === 'fulfilled') alerts = results[4].value.alerts || [];
      if (results[5].status === 'fulfilled') enforcement = results[5].value;

      error = null;
      debug.info('Security', 'Data loaded successfully');
    } catch (e) {
      error = e.message;
      debug.error('Security', 'Failed to load data', e);
    } finally {
      loading = false;
    }
  }

  async function handleModeChange() {
    if (!selectedMode || !modeChangeReason) {
      modeChangeError = 'Please select a mode and provide a reason';
      return;
    }

    modeChangeLoading = true;
    modeChangeError = null;

    try {
      const result = await setBoundaryMode(selectedMode, modeChangeReason, 'web-ui');
      if (result.success) {
        debug.info('Security', `Mode changed to ${selectedMode}`);
        modeChangeReason = '';
        await loadData();
      } else {
        modeChangeError = result.error || 'Mode change failed';
        if (result.error?.includes('override')) {
          modeChangeError += '. Use the Override Ceremony for security relaxation.';
        }
      }
    } catch (e) {
      modeChangeError = e.message;
      debug.error('Security', 'Mode change failed', e);
    } finally {
      modeChangeLoading = false;
    }
  }

  async function handleLockdown() {
    if (!confirm('Are you sure you want to trigger LOCKDOWN? This will block all operations.')) {
      return;
    }

    try {
      await triggerLockdown('Manual lockdown from web UI');
      debug.warn('Security', 'LOCKDOWN triggered');
      await loadData();
    } catch (e) {
      error = e.message;
      debug.error('Security', 'Lockdown failed', e);
    }
  }

  async function handleSecurityCheck() {
    if (!checkText.trim()) return;

    checkLoading = true;
    checkResult = null;

    try {
      checkResult = await checkInput(checkText, checkContext);
      debug.info('Security', 'Input check completed', checkResult);
    } catch (e) {
      checkResult = { error: e.message };
      debug.error('Security', 'Input check failed', e);
    } finally {
      checkLoading = false;
    }
  }

  async function handleAcknowledgeAlert(alertId) {
    try {
      await acknowledgeSiemAlert(alertId, 'Acknowledged via web UI');
      await loadData();
      debug.info('Security', `Alert ${alertId} acknowledged`);
    } catch (e) {
      debug.error('Security', 'Failed to acknowledge alert', e);
    }
  }

  function getModeColor(mode) {
    const m = MODES.find((m) => m.id === mode);
    return m ? m.color : '#71717a';
  }

  function formatTimestamp(ts) {
    if (!ts) return 'N/A';
    return new Date(ts).toLocaleString();
  }

  onMount(() => {
    loadData();
    refreshInterval = setInterval(loadData, 30000); // Refresh every 30s
    debug.info('Security', 'Security panel mounted');
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });
</script>

<div class="security-container" in:fly={{ y: 20, duration: 300 }}>
  <div class="security-header">
    <div class="header-content">
      <h2>Security Center</h2>
      <p class="subtitle">Boundary Protection Management</p>
    </div>
    <button class="lockdown-btn" on:click={handleLockdown}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
      Emergency Lockdown
    </button>
  </div>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading security status...</p>
    </div>
  {:else if error}
    <div class="error-state">
      <p>Failed to load security data: {error}</p>
      <button on:click={loadData}>Retry</button>
    </div>
  {:else}
    <!-- Tab Navigation -->
    <div class="tabs">
      <button
        class="tab"
        class:active={activeTab === 'overview'}
        on:click={() => (activeTab = 'overview')}
      >
        Overview
      </button>
      <button
        class="tab"
        class:active={activeTab === 'violations'}
        on:click={() => (activeTab = 'violations')}
      >
        Violations ({violations.length})
      </button>
      <button
        class="tab"
        class:active={activeTab === 'alerts'}
        on:click={() => (activeTab = 'alerts')}
      >
        SIEM Alerts ({alerts.length})
      </button>
      <button
        class="tab"
        class:active={activeTab === 'check'}
        on:click={() => (activeTab = 'check')}
      >
        Security Check
      </button>
      <button
        class="tab"
        class:active={activeTab === 'history'}
        on:click={() => (activeTab = 'history')}
      >
        History
      </button>
    </div>

    <div class="tab-content">
      {#if activeTab === 'overview'}
        <div class="overview-grid" in:fade={{ duration: 200 }}>
          <!-- Current Mode Card -->
          <div class="card mode-card">
            <div class="card-header">
              <h3>Current Mode</h3>
            </div>
            <div class="mode-display">
              <div
                class="mode-badge large"
                style="background: {getModeColor(modeInfo?.current_mode)}20; border-color: {getModeColor(
                  modeInfo?.current_mode
                )}; color: {getModeColor(modeInfo?.current_mode)}"
              >
                {modeInfo?.current_mode?.toUpperCase() || 'UNKNOWN'}
              </div>
              <p class="mode-description">{modeInfo?.config?.description || ''}</p>
            </div>

            <div class="mode-properties">
              <div class="property">
                <span class="label">Network</span>
                <span class="value" class:allowed={modeInfo?.config?.network_allowed}>
                  {modeInfo?.config?.network_allowed ? 'Allowed' : 'Blocked'}
                </span>
              </div>
              <div class="property">
                <span class="label">VPN Required</span>
                <span class="value">{modeInfo?.config?.vpn_only ? 'Yes' : 'No'}</span>
              </div>
              <div class="property">
                <span class="label">USB</span>
                <span class="value" class:blocked={modeInfo?.config?.block_usb}>
                  {modeInfo?.config?.block_usb ? 'Blocked' : 'Allowed'}
                </span>
              </div>
              <div class="property">
                <span class="label">Display Only</span>
                <span class="value">{modeInfo?.config?.display_only ? 'Yes' : 'No'}</span>
              </div>
            </div>

            {#if modeInfo?.cooldown_remaining > 0}
              <div class="cooldown-notice">
                Cooldown: {Math.ceil(modeInfo.cooldown_remaining)}s remaining
              </div>
            {/if}
          </div>

          <!-- Mode Change Card -->
          <div class="card">
            <div class="card-header">
              <h3>Change Mode</h3>
            </div>
            <div class="mode-selector">
              {#each MODES as mode}
                <button
                  class="mode-option"
                  class:selected={selectedMode === mode.id}
                  style="--mode-color: {mode.color}"
                  on:click={() => (selectedMode = mode.id)}
                >
                  <span class="mode-name">{mode.label}</span>
                  <span class="mode-desc">{mode.description}</span>
                </button>
              {/each}
            </div>

            <div class="mode-change-form">
              <input
                type="text"
                placeholder="Reason for mode change..."
                bind:value={modeChangeReason}
              />
              <button
                class="btn-primary"
                on:click={handleModeChange}
                disabled={modeChangeLoading || !modeChangeReason}
              >
                {modeChangeLoading ? 'Changing...' : 'Apply Mode'}
              </button>
            </div>

            {#if modeChangeError}
              <div class="form-error">{modeChangeError}</div>
            {/if}
          </div>

          <!-- Stats Card -->
          <div class="card stats-card">
            <div class="card-header">
              <h3>Statistics</h3>
            </div>
            <div class="stats-grid">
              <div class="stat">
                <span class="stat-value">{status?.stats?.total_requests || 0}</span>
                <span class="stat-label">Total Requests</span>
              </div>
              <div class="stat">
                <span class="stat-value">{status?.stats?.blocked_requests || 0}</span>
                <span class="stat-label">Blocked</span>
              </div>
              <div class="stat">
                <span class="stat-value">{status?.stats?.threats_detected || 0}</span>
                <span class="stat-label">Threats</span>
              </div>
              <div class="stat">
                <span class="stat-value">{violations.length}</span>
                <span class="stat-label">Violations</span>
              </div>
            </div>
          </div>

          <!-- Enforcement Status -->
          <div class="card">
            <div class="card-header">
              <h3>Enforcement Status</h3>
            </div>
            <div class="enforcement-list">
              <div class="enforcement-item">
                <span class="enf-label">Network Enforcement</span>
                <span class="enf-status" class:active={enforcement?.network?.active}>
                  {enforcement?.network?.active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div class="enforcement-item">
                <span class="enf-label">USB Enforcement</span>
                <span class="enf-status" class:active={enforcement?.usb?.active}>
                  {enforcement?.usb?.active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div class="enforcement-item">
                <span class="enf-label">Process Sandbox</span>
                <span class="enf-status" class:active={enforcement?.process?.active}>
                  {enforcement?.process?.active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        </div>
      {:else if activeTab === 'violations'}
        <div class="violations-list" in:fade={{ duration: 200 }}>
          {#if violations.length === 0}
            <div class="empty-state">
              <p>No violations recorded</p>
            </div>
          {:else}
            {#each violations as violation}
              <div class="violation-item" class:critical={violation.severity === 'critical'}>
                <div class="violation-header">
                  <span class="violation-type">{violation.violation_type}</span>
                  <span class="violation-severity severity-{violation.severity}">
                    {violation.severity}
                  </span>
                </div>
                <p class="violation-details">{violation.details || 'No details'}</p>
                <div class="violation-meta">
                  <span>Source: {violation.source || 'unknown'}</span>
                  <span>{formatTimestamp(violation.timestamp)}</span>
                </div>
              </div>
            {/each}
          {/if}
        </div>
      {:else if activeTab === 'alerts'}
        <div class="alerts-list" in:fade={{ duration: 200 }}>
          {#if alerts.length === 0}
            <div class="empty-state">
              <p>No SIEM alerts</p>
            </div>
          {:else}
            {#each alerts as alert}
              <div class="alert-item" class:open={alert.status === 'open'}>
                <div class="alert-header">
                  <span class="alert-rule">{alert.rule_name}</span>
                  <span class="alert-severity severity-{alert.severity}">{alert.severity}</span>
                </div>
                <p class="alert-description">{alert.description}</p>
                <div class="alert-meta">
                  <span>Events: {alert.event_count}</span>
                  <span>{formatTimestamp(alert.created_at)}</span>
                  {#if alert.status === 'open'}
                    <button class="ack-btn" on:click={() => handleAcknowledgeAlert(alert.alert_id)}>
                      Acknowledge
                    </button>
                  {:else}
                    <span class="status-badge">{alert.status}</span>
                  {/if}
                </div>
              </div>
            {/each}
          {/if}
        </div>
      {:else if activeTab === 'check'}
        <div class="check-panel" in:fade={{ duration: 200 }}>
          <div class="card">
            <div class="card-header">
              <h3>Security Input Check</h3>
              <p>Test input for prompt injection, jailbreaks, and other threats</p>
            </div>

            <div class="check-form">
              <textarea bind:value={checkText} placeholder="Enter text to check for security threats..." rows="5"
              ></textarea>

              <div class="check-options">
                <label>
                  <span>Context:</span>
                  <select bind:value={checkContext}>
                    <option value="user_input">User Input</option>
                    <option value="document">Document</option>
                    <option value="tool_output">Tool Output</option>
                  </select>
                </label>
                <button class="btn-primary" on:click={handleSecurityCheck} disabled={checkLoading || !checkText.trim()}>
                  {checkLoading ? 'Checking...' : 'Check Input'}
                </button>
              </div>
            </div>

            {#if checkResult}
              <div
                class="check-result"
                class:threat={checkResult.blocked || checkResult.threat_detected}
                class:safe={!checkResult.blocked && !checkResult.threat_detected && !checkResult.error}
                class:error={checkResult.error}
              >
                {#if checkResult.error}
                  <h4>Error</h4>
                  <p>{checkResult.error}</p>
                {:else if checkResult.blocked || checkResult.threat_detected}
                  <h4>Threat Detected</h4>
                  <p>Risk Level: <strong>{checkResult.risk_level}</strong></p>
                  {#if checkResult.threat_category}
                    <p>Category: {checkResult.threat_category}</p>
                  {/if}
                  {#if checkResult.patterns_matched?.length > 0}
                    <p>Patterns: {checkResult.patterns_matched.join(', ')}</p>
                  {/if}
                {:else}
                  <h4>Input Safe</h4>
                  <p>No threats detected in this input.</p>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {:else if activeTab === 'history'}
        <div class="history-list" in:fade={{ duration: 200 }}>
          {#if modeHistory.length === 0}
            <div class="empty-state">
              <p>No mode transitions recorded</p>
            </div>
          {:else}
            {#each modeHistory as transition}
              <div class="history-item" class:success={transition.success} class:failed={!transition.success}>
                <div class="history-modes">
                  <span
                    class="mode-badge"
                    style="background: {getModeColor(transition.from_mode)}20; color: {getModeColor(
                      transition.from_mode
                    )}"
                  >
                    {transition.from_mode}
                  </span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="arrow">
                    <path d="M5 12h14m-7-7l7 7-7 7" />
                  </svg>
                  <span
                    class="mode-badge"
                    style="background: {getModeColor(transition.to_mode)}20; color: {getModeColor(
                      transition.to_mode
                    )}"
                  >
                    {transition.to_mode}
                  </span>
                </div>
                <p class="history-trigger">{transition.trigger}</p>
                <div class="history-meta">
                  <span>{transition.triggered_by || 'system'}</span>
                  <span>{formatTimestamp(transition.timestamp)}</span>
                  {#if !transition.success}
                    <span class="error-text">{transition.error}</span>
                  {/if}
                </div>
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .security-container {
    padding: 0;
  }

  .security-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
  }

  .header-content h2 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #ef4444 0%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }

  .subtitle {
    color: #71717a;
    font-size: 1rem;
  }

  .lockdown-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: linear-gradient(135deg, #dc2626, #991b1b);
    border: none;
    border-radius: 12px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .lockdown-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(220, 38, 38, 0.4);
  }

  .lockdown-btn svg {
    width: 20px;
    height: 20px;
  }

  /* Loading/Error States */
  .loading-state,
  .error-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: #71717a;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 24px;
    padding: 4px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
  }

  .tab {
    flex: 1;
    padding: 12px 16px;
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #71717a;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab:hover {
    color: #e4e4e7;
    background: rgba(255, 255, 255, 0.05);
  }

  .tab.active {
    color: white;
    background: linear-gradient(135deg, #667eea, #764ba2);
  }

  /* Cards */
  .card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
  }

  .card-header {
    margin-bottom: 16px;
  }

  .card-header h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .card-header p {
    font-size: 0.875rem;
    color: #71717a;
  }

  /* Overview Grid */
  .overview-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  @media (max-width: 900px) {
    .overview-grid {
      grid-template-columns: 1fr;
    }
  }

  /* Mode Display */
  .mode-display {
    text-align: center;
    margin-bottom: 20px;
  }

  .mode-badge {
    display: inline-block;
    padding: 6px 12px;
    border: 1px solid;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .mode-badge.large {
    padding: 12px 24px;
    font-size: 1.25rem;
    border-radius: 12px;
  }

  .mode-description {
    margin-top: 8px;
    color: #71717a;
    font-size: 0.875rem;
  }

  .mode-properties {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .property {
    display: flex;
    justify-content: space-between;
    padding: 10px 12px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
  }

  .property .label {
    color: #71717a;
    font-size: 0.875rem;
  }

  .property .value {
    font-weight: 500;
    color: #e4e4e7;
  }

  .property .value.allowed {
    color: #22c55e;
  }

  .property .value.blocked {
    color: #ef4444;
  }

  .cooldown-notice {
    margin-top: 16px;
    padding: 10px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    color: #f59e0b;
    text-align: center;
    font-size: 0.875rem;
  }

  /* Mode Selector */
  .mode-selector {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }

  .mode-option {
    padding: 12px;
    background: rgba(0, 0, 0, 0.2);
    border: 2px solid transparent;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .mode-option:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .mode-option.selected {
    border-color: var(--mode-color);
    background: color-mix(in srgb, var(--mode-color) 10%, transparent);
  }

  .mode-name {
    display: block;
    font-weight: 600;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .mode-desc {
    font-size: 0.75rem;
    color: #71717a;
  }

  .mode-change-form {
    display: flex;
    gap: 12px;
  }

  .mode-change-form input {
    flex: 1;
    padding: 12px 16px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #e4e4e7;
    font-size: 0.9rem;
  }

  .mode-change-form input:focus {
    outline: none;
    border-color: #667eea;
  }

  .btn-primary {
    padding: 12px 24px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border: none;
    border-radius: 10px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .form-error {
    margin-top: 12px;
    padding: 10px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    color: #f87171;
    font-size: 0.875rem;
  }

  /* Stats */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .stat {
    text-align: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 12px;
  }

  .stat-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: #e4e4e7;
  }

  .stat-label {
    font-size: 0.8rem;
    color: #71717a;
  }

  /* Enforcement */
  .enforcement-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .enforcement-item {
    display: flex;
    justify-content: space-between;
    padding: 12px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
  }

  .enf-label {
    color: #a1a1aa;
  }

  .enf-status {
    font-weight: 500;
    color: #71717a;
  }

  .enf-status.active {
    color: #22c55e;
  }

  /* Violations List */
  .violations-list,
  .alerts-list,
  .history-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .violation-item,
  .alert-item,
  .history-item {
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
  }

  .violation-item.critical {
    border-color: rgba(239, 68, 68, 0.3);
  }

  .violation-header,
  .alert-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .violation-type,
  .alert-rule {
    font-weight: 600;
    color: #e4e4e7;
  }

  .violation-severity,
  .alert-severity {
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .severity-low {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
  .severity-medium {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
  }
  .severity-high {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
  .severity-critical {
    background: rgba(220, 38, 38, 0.2);
    color: #dc2626;
  }

  .violation-details,
  .alert-description {
    color: #a1a1aa;
    font-size: 0.9rem;
    margin-bottom: 12px;
  }

  .violation-meta,
  .alert-meta,
  .history-meta {
    display: flex;
    gap: 16px;
    font-size: 0.8rem;
    color: #71717a;
  }

  .ack-btn {
    padding: 4px 10px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 6px;
    color: #22c55e;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .status-badge {
    padding: 4px 8px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
  }

  /* Security Check */
  .check-form textarea {
    width: 100%;
    padding: 16px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    color: #e4e4e7;
    font-size: 0.9rem;
    resize: vertical;
    font-family: inherit;
  }

  .check-form textarea:focus {
    outline: none;
    border-color: #667eea;
  }

  .check-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
  }

  .check-options label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a1a1aa;
  }

  .check-options select {
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #e4e4e7;
  }

  .check-result {
    margin-top: 20px;
    padding: 16px;
    border-radius: 12px;
  }

  .check-result.threat {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .check-result.safe {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
  }

  .check-result.error {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .check-result h4 {
    margin-bottom: 8px;
    color: #e4e4e7;
  }

  .check-result.threat h4 {
    color: #ef4444;
  }
  .check-result.safe h4 {
    color: #22c55e;
  }

  .check-result p {
    color: #a1a1aa;
    font-size: 0.9rem;
    margin-bottom: 4px;
  }

  /* History */
  .history-item.failed {
    border-color: rgba(239, 68, 68, 0.3);
  }

  .history-modes {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .arrow {
    width: 20px;
    height: 20px;
    color: #71717a;
  }

  .history-trigger {
    color: #a1a1aa;
    font-size: 0.9rem;
    margin-bottom: 8px;
  }

  .error-text {
    color: #ef4444;
  }
</style>
