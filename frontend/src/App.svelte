<script>
  import { onMount, onDestroy } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import Navigation from './components/Navigation.svelte';
  import ChainExplorer from './components/ChainExplorer.svelte';
  import EntryForm from './components/EntryForm.svelte';
  import ContractViewer from './components/ContractViewer.svelte';
  import SearchPanel from './components/SearchPanel.svelte';
  import Dashboard from './components/Dashboard.svelte';
  import ChatHelper from './components/ChatHelper.svelte';
  import Settings from './components/Settings.svelte';
  import HelpCenter from './components/HelpCenter.svelte';
  import SecurityPanel from './components/SecurityPanel.svelte';
  import DebugWindow from './components/DebugWindow.svelte';
  import { settings, debug } from './lib/stores.js';
  import { getDreamingStatus } from './lib/api.js';

  let currentView = 'dashboard';
  let mounted = false;
  let chatOpen = false;

  // Dreaming status (polls every 5 seconds)
  let dreamingStatus = { message: 'Initializing...', state: 'idle' };
  let dreamingInterval;

  async function updateDreamingStatus() {
    try {
      dreamingStatus = await getDreamingStatus();
    } catch (_e) {
      // Silently fail - dreaming is non-critical
      dreamingStatus = { message: 'Dreaming quietly...', state: 'idle' };
    }
  }

  onMount(() => {
    mounted = true;
    debug.info('App', 'Application initialized');

    // Start dreaming status polling (every 5 seconds)
    updateDreamingStatus();
    dreamingInterval = setInterval(updateDreamingStatus, 5000);
  });

  onDestroy(() => {
    if (dreamingInterval) clearInterval(dreamingInterval);
  });

  function handleNavigate(event) {
    currentView = event.detail.view;
    debug.info('Navigation', `Navigated to ${event.detail.view}`);
  }

  function toggleChat() {
    chatOpen = !chatOpen;
  }
</script>

<div class="app-wrapper">
  <!-- Animated background -->
  <div class="bg-gradient"></div>
  <div class="bg-pattern"></div>
  <div class="floating-orbs">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
  </div>

  <main>
    {#if mounted}
      <header in:fly={{ y: -20, duration: 600, delay: 100 }}>
        <div class="logo-container">
          <div class="logo-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect
                x="4"
                y="4"
                width="32"
                height="32"
                rx="8"
                stroke="url(#logo-grad)"
                stroke-width="2"
              />
              <path
                d="M12 20h16M20 12v16"
                stroke="url(#logo-grad)"
                stroke-width="2"
                stroke-linecap="round"
              />
              <circle cx="20" cy="20" r="4" fill="url(#logo-grad)" />
              <defs>
                <linearGradient id="logo-grad" x1="4" y1="4" x2="36" y2="36">
                  <stop stop-color="#667eea" />
                  <stop offset="1" stop-color="#764ba2" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="logo-text">
            <h1>NatLangChain</h1>
            <p class="tagline">Natural Language Blockchain Explorer</p>
          </div>
        </div>
        <div class="header-stats">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span>Connected</span>
          </div>
        </div>
      </header>

      <Navigation {currentView} on:navigate={handleNavigate} />

      <div class="content">
        {#key currentView}
          <div in:fade={{ duration: 200 }}>
            {#if currentView === 'dashboard'}
              <Dashboard />
            {:else if currentView === 'explorer'}
              <ChainExplorer />
            {:else if currentView === 'submit'}
              <EntryForm />
            {:else if currentView === 'contracts'}
              <ContractViewer />
            {:else if currentView === 'search'}
              <SearchPanel />
            {:else if currentView === 'security'}
              <SecurityPanel />
            {:else if currentView === 'help'}
              <HelpCenter />
            {:else if currentView === 'settings'}
              <Settings />
            {/if}
          </div>
        {/key}
      </div>

      <footer in:fly={{ y: 20, duration: 600, delay: 300 }}>
        <div class="footer-content">
          {#if dreamingStatus.message}
            <div class="dreaming-status" class:active={dreamingStatus.state === 'active'} in:fade={{ duration: 200 }} out:fade={{ duration: 200 }}>
              <span class="dreaming-indicator" class:pulse={dreamingStatus.state === 'active'}></span>
              <span class="dreaming-message">{dreamingStatus.message}</span>
              {#if dreamingStatus.state === 'active' && dreamingStatus.duration}
                <span class="dreaming-duration">({dreamingStatus.duration}s)</span>
              {/if}
            </div>
          {:else}
            <div class="footer-spacer"></div>
          {/if}
          <div class="footer-links">
            <span class="version">v0.1.0-alpha</span>
          </div>
        </div>
      </footer>
    {/if}
  </main>

  <!-- AI Chat Helper -->
  <ChatHelper {currentView} isOpen={chatOpen} on:toggle={toggleChat} />

  <!-- Debug Window (shown when enabled in settings) -->
  {#if $settings.debugWindowEnabled}
    <DebugWindow />
  {/if}
</div>

<style>
  :global(*) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    font-family:
      'Inter',
      -apple-system,
      BlinkMacSystemFont,
      'Segoe UI',
      Roboto,
      Oxygen,
      Ubuntu,
      Cantarell,
      'Open Sans',
      'Helvetica Neue',
      sans-serif;
    min-height: 100vh;
    color: #e4e4e7;
    overflow-x: hidden;
  }

  :global(::selection) {
    background: rgba(102, 126, 234, 0.4);
    color: #fff;
  }

  :global(::-webkit-scrollbar) {
    width: 8px;
    height: 8px;
  }

  :global(::-webkit-scrollbar-track) {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
  }

  :global(::-webkit-scrollbar-thumb) {
    background: rgba(102, 126, 234, 0.5);
    border-radius: 4px;
  }

  :global(::-webkit-scrollbar-thumb:hover) {
    background: rgba(102, 126, 234, 0.7);
  }

  .app-wrapper {
    min-height: 100vh;
    position: relative;
    background: #0a0a0f;
  }

  .bg-gradient {
    position: fixed;
    inset: 0;
    background:
      radial-gradient(ellipse at 20% 0%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 100%, rgba(118, 75, 162, 0.15) 0%, transparent 50%),
      linear-gradient(180deg, #0d0d14 0%, #1a1a2e 50%, #0d0d14 100%);
    z-index: 0;
  }

  .bg-pattern {
    position: fixed;
    inset: 0;
    background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    z-index: 0;
  }

  .floating-orbs {
    position: fixed;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
    z-index: 0;
  }

  .orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
    animation: float 20s infinite ease-in-out;
  }

  .orb-1 {
    width: 400px;
    height: 400px;
    background: rgba(102, 126, 234, 0.3);
    top: -100px;
    left: -100px;
    animation-delay: 0s;
  }

  .orb-2 {
    width: 300px;
    height: 300px;
    background: rgba(118, 75, 162, 0.3);
    bottom: -50px;
    right: -50px;
    animation-delay: -7s;
  }

  .orb-3 {
    width: 200px;
    height: 200px;
    background: rgba(102, 126, 234, 0.2);
    top: 50%;
    left: 50%;
    animation-delay: -14s;
  }

  @keyframes float {
    0%,
    100% {
      transform: translate(0, 0) scale(1);
    }
    25% {
      transform: translate(30px, -30px) scale(1.05);
    }
    50% {
      transform: translate(-20px, 20px) scale(0.95);
    }
    75% {
      transform: translate(20px, 30px) scale(1.02);
    }
  }

  main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    position: relative;
    z-index: 1;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    margin-bottom: 24px;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    box-shadow:
      0 4px 24px rgba(0, 0, 0, 0.2),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  .logo-container {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .logo-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(102, 126, 234, 0.1);
    border-radius: 12px;
    border: 1px solid rgba(102, 126, 234, 0.2);
  }

  .logo-icon svg {
    width: 32px;
    height: 32px;
  }

  .logo-text h1 {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #667eea 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 3s ease-in-out infinite;
  }

  @keyframes shimmer {
    0%,
    100% {
      background-position: 0% center;
    }
    50% {
      background-position: 100% center;
    }
  }

  .tagline {
    font-size: 0.875rem;
    color: #71717a;
    margin-top: 2px;
  }

  .header-stats {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 20px;
    font-size: 0.875rem;
    color: #22c55e;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
      box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
    }
    50% {
      opacity: 0.8;
      box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
    }
  }

  .content {
    flex: 1;
    padding: 0;
  }

  footer {
    margin-top: 24px;
    padding: 20px 24px;
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
  }

  .footer-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }


  .footer-links {
    display: flex;
    gap: 16px;
  }

  .version {
    color: #3f3f46;
    font-size: 0.75rem;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 6px;
  }

  /* Dreaming status line */
  .dreaming-status {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #52525b;
    font-size: 0.8rem;
    font-style: italic;
    transition: color 0.3s ease;
  }

  .dreaming-status.active {
    color: #a78bfa;
  }

  .dreaming-indicator {
    width: 6px;
    height: 6px;
    background: #52525b;
    border-radius: 50%;
    transition: all 0.3s ease;
  }

  .dreaming-indicator.pulse {
    background: #a78bfa;
    animation: dreamPulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(167, 139, 250, 0.5);
  }

  @keyframes dreamPulse {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(1.2);
    }
  }

  .dreaming-message {
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dreaming-duration {
    color: #71717a;
    font-size: 0.7rem;
  }

  @media (max-width: 768px) {
    header {
      flex-direction: column;
      gap: 16px;
      text-align: center;
    }

    .logo-container {
      flex-direction: column;
    }

    .footer-content {
      flex-direction: column;
      gap: 12px;
      text-align: center;
    }
  }
</style>
