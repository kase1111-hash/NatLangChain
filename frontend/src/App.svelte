<script>
  import { onMount } from 'svelte';
  import Navigation from './components/Navigation.svelte';
  import ChainExplorer from './components/ChainExplorer.svelte';
  import EntryForm from './components/EntryForm.svelte';
  import ContractViewer from './components/ContractViewer.svelte';
  import SearchPanel from './components/SearchPanel.svelte';
  import Dashboard from './components/Dashboard.svelte';

  let currentView = 'dashboard';
  let chainInfo = null;
  let error = null;

  function handleNavigate(event) {
    currentView = event.detail.view;
  }
</script>

<main>
  <header>
    <h1>NatLangChain</h1>
    <p class="tagline">Natural Language Blockchain Explorer</p>
  </header>

  <Navigation {currentView} on:navigate={handleNavigate} />

  <div class="content">
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
    {/if}
  </div>

  <footer>
    <p>NatLangChain - Where Natural Language Meets Blockchain</p>
  </footer>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    min-height: 100vh;
    color: #e4e4e7;
  }

  main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    text-align: center;
    padding: 30px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
  }

  h1 {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }

  .tagline {
    color: #a1a1aa;
    font-size: 1rem;
  }

  .content {
    flex: 1;
    padding: 20px 0;
  }

  footer {
    text-align: center;
    padding: 20px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: 20px;
    color: #71717a;
    font-size: 0.875rem;
  }
</style>
