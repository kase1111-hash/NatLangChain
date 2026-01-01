<script>
  import { createEventDispatcher } from 'svelte';
  import { fly } from 'svelte/transition';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  export let currentView = 'dashboard';

  const dispatch = createEventDispatcher();

  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
      tooltip: ncipDefinitions.dashboard,
    },
    {
      id: 'explorer',
      label: 'Explorer',
      icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
      tooltip: ncipDefinitions.chainExplorer,
    },
    {
      id: 'submit',
      label: 'New Entry',
      icon: 'M12 4v16m8-8H4',
      tooltip: ncipDefinitions.submitEntry,
    },
    {
      id: 'contracts',
      label: 'Contracts',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      tooltip: ncipDefinitions.contracts,
    },
    {
      id: 'search',
      label: 'Search',
      icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
      tooltip: ncipDefinitions.search,
    },
    {
      id: 'help',
      label: 'Help',
      icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
      tooltip: {
        text: 'Browse governance documentation, NCIPs, protocols, and the design philosophy. NatLangChain has 15 NCIPs defining comprehensive governance.',
        ncipRef: 'NCIP-000+',
      },
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
      tooltip: {
        text: 'Configure application settings, debug console, and preferences',
        ncipRef: '',
      },
    },
  ];

  function navigate(view) {
    dispatch('navigate', { view });
  }
</script>

<nav in:fly={{ y: -10, duration: 400, delay: 200 }}>
  <div class="nav-container">
    {#each navItems as item, _i}
      <Tooltip text={item.tooltip.text} ncipRef={item.tooltip.ncipRef} position="bottom">
        <button
          class="nav-item"
          class:active={currentView === item.id}
          on:click={() => navigate(item.id)}
        >
          <div class="nav-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d={item.icon} />
            </svg>
          </div>
          <span class="nav-label">{item.label}</span>
          {#if currentView === item.id}
            <div class="glow"></div>
          {/if}
        </button>
      </Tooltip>
    {/each}
  </div>
</nav>

<style>
  nav {
    margin-bottom: 24px;
  }

  .nav-container {
    display: flex;
    gap: 8px;
    padding: 8px;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  }

  .nav-item {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 20px;
    background: transparent;
    border: none;
    border-radius: 12px;
    color: #71717a;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }

  .nav-item::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
    opacity: 0;
    transition: opacity 0.3s ease;
    border-radius: 12px;
  }

  .nav-item:hover {
    color: #e4e4e7;
    transform: translateY(-1px);
  }

  .nav-item:hover::before {
    opacity: 1;
  }

  .nav-item.active {
    color: #fff;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow:
      0 4px 15px rgba(102, 126, 234, 0.4),
      0 0 0 1px rgba(255, 255, 255, 0.1) inset;
    transform: translateY(-1px);
  }

  .nav-item.active::before {
    opacity: 0;
  }

  .glow {
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at center, rgba(255, 255, 255, 0.2), transparent 70%);
    pointer-events: none;
    animation: glowPulse 2s ease-in-out infinite;
  }

  @keyframes glowPulse {
    0%,
    100% {
      opacity: 0.5;
    }
    50% {
      opacity: 0.2;
    }
  }

  .nav-icon {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 1;
  }

  .nav-icon svg {
    width: 100%;
    height: 100%;
  }

  .nav-label {
    position: relative;
    z-index: 1;
  }

  @media (max-width: 768px) {
    .nav-container {
      flex-wrap: wrap;
    }

    .nav-item {
      flex: 0 0 calc(50% - 4px);
      padding: 12px 16px;
    }

    .nav-label {
      font-size: 0.8rem;
    }
  }

  @media (max-width: 480px) {
    .nav-item {
      flex: 0 0 calc(50% - 4px);
      flex-direction: column;
      gap: 6px;
      padding: 12px 8px;
    }

    .nav-icon {
      width: 24px;
      height: 24px;
    }

    .nav-label {
      font-size: 0.7rem;
    }
  }
</style>
