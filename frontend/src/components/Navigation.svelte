<script>
  import { createEventDispatcher } from 'svelte';

  export let currentView = 'dashboard';

  const dispatch = createEventDispatcher();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'explorer', label: 'Chain Explorer', icon: '🔗' },
    { id: 'submit', label: 'Submit Entry', icon: '✏️' },
    { id: 'contracts', label: 'Contracts', icon: '📜' },
    { id: 'search', label: 'Search', icon: '🔍' },
  ];

  function navigate(view) {
    dispatch('navigate', { view });
  }
</script>

<nav>
  <ul>
    {#each navItems as item}
      <li>
        <button
          class:active={currentView === item.id}
          on:click={() => navigate(item.id)}
        >
          <span class="icon">{item.icon}</span>
          <span class="label">{item.label}</span>
        </button>
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
