<script>
  import { createEventDispatcher } from 'svelte';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  export let currentView = 'dashboard';

  const dispatch = createEventDispatcher();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', tooltip: ncipDefinitions.dashboard },
    { id: 'explorer', label: 'Chain Explorer', icon: '🔗', tooltip: ncipDefinitions.chainExplorer },
    { id: 'submit', label: 'Submit Entry', icon: '✏️', tooltip: ncipDefinitions.submitEntry },
    { id: 'contracts', label: 'Contracts', icon: '📜', tooltip: ncipDefinitions.contracts },
    { id: 'search', label: 'Search', icon: '🔍', tooltip: ncipDefinitions.search },
  ];

  function navigate(view) {
    dispatch('navigate', { view });
  }
</script>

<nav>
  <ul>
    {#each navItems as item}
      <li>
        <Tooltip text={item.tooltip.text} ncipRef={item.tooltip.ncipRef} position="bottom">
          <button
            class:active={currentView === item.id}
            on:click={() => navigate(item.id)}
          >
            <span class="icon">{item.icon}</span>
            <span class="label">{item.label}</span>
          </button>
        </Tooltip>
      </li>
    {/each}
  </ul>
</nav>

<style>
  nav {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 8px;
    margin-bottom: 20px;
  }

  ul {
    list-style: none;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
  }

  button {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #a1a1aa;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  button:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
  }

  button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .icon {
    font-size: 1.1rem;
  }

  @media (max-width: 600px) {
    .label {
      display: none;
    }

    button {
      padding: 12px;
    }

    .icon {
      font-size: 1.3rem;
    }
  }
</style>
