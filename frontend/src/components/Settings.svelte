<script>
  import { onMount } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { settings, debug, clearDebugLogs, debugLogs } from '../lib/stores.js';

  let localSettings;
  let _hasChanges = false; // Track for future "unsaved changes" indicator
  let saveMessage = '';

  // Subscribe to settings store
  $: localSettings = { ...$settings };

  function updateSetting(key, value) {
    settings.update((s) => ({ ...s, [key]: value }));
    _hasChanges = true;
    showSaveMessage('Settings saved automatically');
  }

  function showSaveMessage(msg) {
    saveMessage = msg;
    setTimeout(() => (saveMessage = ''), 2000);
  }

  function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      settings.set({
        debugWindowEnabled: false,
        debugWindowPosition: { x: 20, y: 20 },
        debugWindowSize: { width: 500, height: 400 },
        debugLogLevel: 'info',
        debugMaxLines: 500,
        theme: 'dark',
        animationsEnabled: true,
        compactMode: false,
      });
      clearDebugLogs();
      showSaveMessage('Settings reset to defaults');
      debug.info('Settings', 'All settings reset to defaults');
    }
  }

  function exportSettings() {
    const data = JSON.stringify($settings, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'natlangchain-settings.json';
    a.click();
    URL.revokeObjectURL(url);
    debug.info('Settings', 'Settings exported');
  }

  function importSettings(event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const imported = JSON.parse(e.target.result);
          settings.set({ ...$settings, ...imported });
          showSaveMessage('Settings imported successfully');
          debug.info('Settings', 'Settings imported', imported);
        } catch (err) {
          alert('Failed to import settings: Invalid JSON file');
          debug.error('Settings', 'Failed to import settings', err);
        }
      };
      reader.readAsText(file);
    }
  }

  onMount(() => {
    debug.info('Settings', 'Settings page opened');
  });
</script>

<div class="settings-container" in:fly={{ y: 20, duration: 300 }}>
  <div class="settings-header">
    <div class="header-content">
      <h2>Settings</h2>
      <p class="subtitle">Configure application preferences</p>
    </div>
    {#if saveMessage}
      <div class="save-message" in:fade={{ duration: 150 }} out:fade={{ duration: 150 }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 13l4 4L19 7" />
        </svg>
        {saveMessage}
      </div>
    {/if}
  </div>

  <div class="settings-grid">
    <!-- Debug Settings Section -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon debug">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        </div>
        <div>
          <h3>Debug Console</h3>
          <p>Developer tools and logging options</p>
        </div>
      </div>

      <div class="settings-group">
        <div class="setting-item">
          <div class="setting-info">
            <label for="debugWindow">Enable Debug Window</label>
            <span class="setting-description"
              >Show a floating debug console with real-time logs</span
            >
          </div>
          <label class="toggle">
            <input
              type="checkbox"
              id="debugWindow"
              checked={localSettings.debugWindowEnabled}
              on:change={(e) => updateSetting('debugWindowEnabled', e.target.checked)}
            />
            <span class="toggle-slider"></span>
          </label>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <label for="debugLogLevel">Log Level</label>
            <span class="setting-description">Minimum level of logs to display</span>
          </div>
          <select
            id="debugLogLevel"
            class="setting-select"
            value={localSettings.debugLogLevel}
            on:change={(e) => updateSetting('debugLogLevel', e.target.value)}
          >
            <option value="debug">Debug (All)</option>
            <option value="info">Info</option>
            <option value="warn">Warnings</option>
            <option value="error">Errors Only</option>
          </select>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <label for="debugMaxLines">Max Log Lines</label>
            <span class="setting-description">Maximum number of log entries to keep in memory</span>
          </div>
          <select
            id="debugMaxLines"
            class="setting-select"
            value={localSettings.debugMaxLines}
            on:change={(e) => updateSetting('debugMaxLines', parseInt(e.target.value))}
          >
            <option value={100}>100 lines</option>
            <option value={250}>250 lines</option>
            <option value={500}>500 lines</option>
            <option value={1000}>1000 lines</option>
            <option value={2500}>2500 lines</option>
          </select>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <span class="setting-label">Current Log Count</span>
            <span class="setting-description">{$debugLogs.length} entries in memory</span>
          </div>
          <button class="btn btn-secondary" on:click={clearDebugLogs}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            Clear Logs
          </button>
        </div>
      </div>
    </section>

    <!-- Appearance Section -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon appearance">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path
              d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
            />
          </svg>
        </div>
        <div>
          <h3>Appearance</h3>
          <p>Customize the look and feel</p>
        </div>
      </div>

      <div class="settings-group">
        <div class="setting-item">
          <div class="setting-info">
            <label for="animations">Enable Animations</label>
            <span class="setting-description">Show smooth transitions and animations</span>
          </div>
          <label class="toggle">
            <input
              type="checkbox"
              id="animations"
              checked={localSettings.animationsEnabled}
              on:change={(e) => updateSetting('animationsEnabled', e.target.checked)}
            />
            <span class="toggle-slider"></span>
          </label>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <label for="compactMode">Compact Mode</label>
            <span class="setting-description">Reduce spacing for more content on screen</span>
          </div>
          <label class="toggle">
            <input
              type="checkbox"
              id="compactMode"
              checked={localSettings.compactMode}
              on:change={(e) => updateSetting('compactMode', e.target.checked)}
            />
            <span class="toggle-slider"></span>
          </label>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <label for="theme">Theme</label>
            <span class="setting-description">Color scheme for the interface</span>
          </div>
          <select
            id="theme"
            class="setting-select"
            value={localSettings.theme}
            on:change={(e) => updateSetting('theme', e.target.value)}
          >
            <option value="dark">Dark</option>
            <option value="light" disabled>Light (Coming Soon)</option>
            <option value="system" disabled>System (Coming Soon)</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Data Management Section -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon data">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path
              d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
            />
          </svg>
        </div>
        <div>
          <h3>Data Management</h3>
          <p>Export, import, and reset settings</p>
        </div>
      </div>

      <div class="settings-group">
        <div class="setting-item">
          <div class="setting-info">
            <span class="setting-label">Export Settings</span>
            <span class="setting-description">Download your settings as a JSON file</span>
          </div>
          <button class="btn btn-secondary" on:click={exportSettings}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export
          </button>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <span class="setting-label">Import Settings</span>
            <span class="setting-description">Load settings from a JSON file</span>
          </div>
          <label class="btn btn-secondary file-input-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Import
            <input
              type="file"
              accept=".json"
              on:change={importSettings}
              class="hidden-file-input"
            />
          </label>
        </div>

        <div class="setting-item danger">
          <div class="setting-info">
            <span class="setting-label">Reset All Settings</span>
            <span class="setting-description">Restore all settings to their default values</span>
          </div>
          <button class="btn btn-danger" on:click={resetToDefaults}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Reset to Defaults
          </button>
        </div>
      </div>
    </section>

    <!-- About Section -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon about">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <h3>About</h3>
          <p>Application information</p>
        </div>
      </div>

      <div class="settings-group">
        <div class="about-info">
          <div class="about-row">
            <span class="about-label">Application</span>
            <span class="about-value">NatLangChain</span>
          </div>
          <div class="about-row">
            <span class="about-label">Version</span>
            <span class="about-value">1.0.0</span>
          </div>
          <div class="about-row">
            <span class="about-label">Platform</span>
            <span class="about-value">{navigator.platform || 'Unknown'}</span>
          </div>
          <div class="about-row">
            <span class="about-label">User Agent</span>
            <span class="about-value small">{navigator.userAgent}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</div>

<style>
  .settings-container {
    padding: 0;
  }

  .settings-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 32px;
  }

  .header-content h2 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }

  .subtitle {
    color: #71717a;
    font-size: 1rem;
  }

  .save-message {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 10px;
    color: #22c55e;
    font-size: 0.875rem;
  }

  .save-message svg {
    width: 16px;
    height: 16px;
  }

  .settings-grid {
    display: grid;
    gap: 24px;
  }

  .settings-section {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    transition: border-color 0.3s ease;
  }

  .settings-section:hover {
    border-color: rgba(255, 255, 255, 0.12);
  }

  .section-header {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .section-icon {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    flex-shrink: 0;
  }

  .section-icon svg {
    width: 22px;
    height: 22px;
  }

  .section-icon.debug {
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
  }

  .section-icon.appearance {
    background: rgba(168, 85, 247, 0.15);
    color: #a855f7;
  }

  .section-icon.data {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .section-icon.about {
    background: rgba(251, 191, 36, 0.15);
    color: #fbbf24;
  }

  .section-header h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .section-header p {
    font-size: 0.875rem;
    color: #71717a;
  }

  .settings-group {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .setting-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 12px;
    gap: 24px;
  }

  .setting-item.danger {
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  .setting-info {
    flex: 1;
  }

  .setting-info label,
  .setting-info .setting-label {
    display: block;
    font-size: 0.9375rem;
    font-weight: 500;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .setting-description {
    font-size: 0.8125rem;
    color: #71717a;
  }

  /* Toggle switch */
  .toggle {
    position: relative;
    display: inline-block;
    width: 48px;
    height: 26px;
    flex-shrink: 0;
  }

  .toggle input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    inset: 0;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 26px;
    transition: all 0.3s ease;
  }

  .toggle-slider::before {
    position: absolute;
    content: '';
    height: 20px;
    width: 20px;
    left: 3px;
    bottom: 3px;
    background: #71717a;
    border-radius: 50%;
    transition: all 0.3s ease;
  }

  .toggle input:checked + .toggle-slider {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .toggle input:checked + .toggle-slider::before {
    transform: translateX(22px);
    background: #fff;
  }

  .toggle input:focus + .toggle-slider {
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
  }

  /* Select */
  .setting-select {
    padding: 10px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #e4e4e7;
    font-size: 0.875rem;
    cursor: pointer;
    outline: none;
    transition: all 0.2s ease;
    min-width: 150px;
  }

  .setting-select:hover {
    border-color: rgba(255, 255, 255, 0.2);
  }

  .setting-select:focus {
    border-color: rgba(102, 126, 234, 0.5);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
  }

  .setting-select option {
    background: #1a1a2e;
    color: #e4e4e7;
  }

  /* Buttons */
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border: none;
    border-radius: 10px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
  }

  .btn svg {
    width: 16px;
    height: 16px;
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
  }

  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .btn-danger {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
  }

  .btn-danger:hover {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
  }

  .file-input-label {
    cursor: pointer;
  }

  .hidden-file-input {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }

  /* About section */
  .about-info {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .about-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px 16px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 10px;
  }

  .about-label {
    color: #71717a;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  .about-value {
    color: #e4e4e7;
    font-size: 0.875rem;
    text-align: right;
    word-break: break-word;
  }

  .about-value.small {
    font-size: 0.75rem;
    color: #a1a1aa;
    max-width: 400px;
  }

  @media (max-width: 768px) {
    .settings-header {
      flex-direction: column;
      gap: 16px;
    }

    .setting-item {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .setting-select,
    .btn {
      width: 100%;
      justify-content: center;
    }

    .about-row {
      flex-direction: column;
      gap: 4px;
    }

    .about-value {
      text-align: left;
    }
  }
</style>
