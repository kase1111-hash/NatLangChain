<script>
  import { onMount } from 'svelte';
  import { fade, fly, slide } from 'svelte/transition';
  import Tooltip from './Tooltip.svelte';

  // Tab state
  let activeTab = 'overview';
  let selectedNCIP = null;
  let selectedMP = null;
  let selectedConcept = null;
  let searchQuery = '';
  let searchResults = [];
  let expandedCategory = null;

  // Data loaded from API
  let helpOverview = null;
  let ncipsByCategory = {};
  let mpList = [];
  let concepts = {};
  let philosophy = null;
  let loading = true;
  let error = null;

  // Fetch governance data
  async function fetchGovernanceData() {
    try {
      loading = true;
      const baseUrl = 'http://localhost:5000';

      const [overviewRes, ncipsRes, mpsRes, conceptsRes, philosophyRes] = await Promise.all([
        fetch(`${baseUrl}/api/help/overview`),
        fetch(`${baseUrl}/api/help/ncips/by-category`),
        fetch(`${baseUrl}/api/help/mps`),
        fetch(`${baseUrl}/api/help/concepts`),
        fetch(`${baseUrl}/api/help/philosophy`)
      ]);

      if (overviewRes.ok) helpOverview = await overviewRes.json();
      if (ncipsRes.ok) ncipsByCategory = await ncipsRes.json();
      if (mpsRes.ok) mpList = await mpsRes.json();
      if (conceptsRes.ok) concepts = await conceptsRes.json();
      if (philosophyRes.ok) philosophy = await philosophyRes.json();

      loading = false;
    } catch (err) {
      console.warn('Could not fetch governance data from API, using embedded data');
      // Use embedded fallback data
      loadEmbeddedData();
      loading = false;
    }
  }

  // Embedded fallback data for when API is not available
  function loadEmbeddedData() {
    helpOverview = {
      title: "NatLangChain Governance",
      subtitle: "Comprehensive governance framework for semantic contracts",
      stats: { ncip_count: 15, mp_count: 4, concept_count: 12 },
      highlights: [
        { title: "15 NCIPs", description: "NatLangChain Improvement Proposals define protocol governance" },
        { title: "4 Mediator Protocols", description: "Specifications for mediation, disputes, and settlement" },
        { title: "Human-Centered", description: "Automation assists, humans decide" },
        { title: "Semantic Validation", description: "Multi-LLM consensus for meaning, not just syntax" }
      ]
    };

    ncipsByCategory = {
      foundation: {
        title: "Foundation & Terminology",
        description: "Core concepts, terms, and semantic governance",
        ncips: [
          { id: "NCIP-000", title: "Terminology & Semantics Governance", summary: "Establishes canonical vocabulary" },
          { id: "NCIP-001", title: "Canonical Term Registry", summary: "Official registry of defined terms" }
        ]
      },
      semantic_integrity: {
        title: "Semantic Integrity",
        description: "Drift detection, thresholds, and multilingual support",
        ncips: [
          { id: "NCIP-002", title: "Semantic Drift Thresholds", summary: "D0-D4 drift bands and responses" },
          { id: "NCIP-003", title: "Multilingual Alignment", summary: "Cross-language semantic preservation" },
          { id: "NCIP-004", title: "Proof of Understanding", summary: "Semantic verification of comprehension" }
        ]
      },
      dispute_resolution: {
        title: "Dispute Resolution",
        description: "Escalation, locking, appeals, and precedent",
        ncips: [
          { id: "NCIP-005", title: "Dispute Escalation", summary: "Cooling periods and semantic locks" },
          { id: "NCIP-008", title: "Appeals & Precedent", summary: "Case law encoding" }
        ]
      },
      trust_reputation: {
        title: "Trust & Reputation",
        description: "Validator scoring, mediator dynamics",
        ncips: [
          { id: "NCIP-007", title: "Validator Trust Scoring", summary: "Reliability weighting" },
          { id: "NCIP-010", title: "Mediator Reputation", summary: "Slashing and market dynamics" },
          { id: "NCIP-011", title: "Validator-Mediator Coupling", summary: "Role separation" }
        ]
      },
      jurisdiction_compliance: {
        title: "Jurisdiction & Compliance",
        description: "Legal bridging and regulatory interfaces",
        ncips: [
          { id: "NCIP-006", title: "Jurisdictional Interpretation", summary: "Legal system bridging" },
          { id: "NCIP-009", title: "Regulatory Interface", summary: "Compliance modules" }
        ]
      },
      human_experience: {
        title: "Human Experience",
        description: "UX, cognitive load, emergency handling",
        ncips: [
          { id: "NCIP-012", title: "Human Ratification UX", summary: "Cognitive load limits" },
          { id: "NCIP-013", title: "Emergency Overrides", summary: "Force majeure handling" }
        ]
      },
      protocol_evolution: {
        title: "Protocol Evolution",
        description: "Amendments, sunset, historical semantics",
        ncips: [
          { id: "NCIP-014", title: "Protocol Amendments", summary: "Constitutional change process" },
          { id: "NCIP-015", title: "Sunset Clauses", summary: "Archival and historical semantics" }
        ]
      }
    };

    mpList = [
      { id: "MP-02", title: "Proof-of-Effort Receipts", summary: "Work recording and verification" },
      { id: "MP-03", title: "Dispute & Escalation", summary: "Evidence freezing and escalation" },
      { id: "MP-04", title: "Licensing & Delegation", summary: "Rights and authority delegation" },
      { id: "MP-05", title: "Settlement & Capitalization", summary: "Economic finality" }
    ];

    concepts = {
      entry: { term: "Entry", definition: "A discrete, timestamped record containing prose, metadata, and signatures." },
      intent: { term: "Intent", definition: "A human-authored expression of desired outcome or commitment." },
      agreement: { term: "Agreement", definition: "Mutually ratified intents establishing shared understanding." },
      ratification: { term: "Ratification", definition: "An explicit act of consent confirming understanding." },
      semantic_drift: { term: "Semantic Drift", definition: "Divergence between original meaning and subsequent interpretation." },
      proof_of_understanding: { term: "Proof of Understanding", definition: "Evidence of semantic comprehension." },
      semantic_lock: { term: "Semantic Lock", definition: "A binding freeze of interpretive meaning at a specific time." },
      cooling_period: { term: "Cooling Period", definition: "Mandatory delay preventing immediate escalation." },
      mediator: { term: "Mediator", definition: "Entity that helps surface alignment between parties." },
      validator: { term: "Validator", definition: "Entity that measures semantic validity and drift." },
      temporal_fixity: { term: "Temporal Fixity", definition: "Binding of meaning to a specific point in time." },
      settlement: { term: "Settlement", definition: "Final resolution with binding obligations." }
    };

    philosophy = {
      title: "NatLangChain Design Philosophy",
      subtitle: "Why Non-Determinism is a Feature",
      principles: [
        { name: "Human-Centered Recording", summary: "The blockchain provides immutability. Humans provide judgment." },
        { name: "Semantic, Not Syntactic", summary: "Meaning matters, not exact text matching." },
        { name: "Multiple Valid Interpretations", summary: "Disagreement is valuable information." },
        { name: "The Refusal Doctrine", summary: "What we explicitly refuse to automate." },
        { name: "Temporal Context", summary: "Meaning is bound to time." },
        { name: "Decentralized Validation", summary: "Multiple LLM providers prevent centralization." }
      ],
      refusal_doctrine: {
        will_not_automate: [
          "Consent - Only humans can consent",
          "Agreement - Only humans can agree",
          "Authority - Only humans can delegate",
          "Value Finality - Only humans can close",
          "Dispute Resolution - Only humans judge",
          "Moral Judgment - No automated ethics"
        ],
        will_automate: [
          "Possibility Expansion",
          "Consistency Checking",
          "Evidence Collection",
          "Provenance",
          "Risk Surfacing",
          "Mediation Support"
        ]
      }
    };
  }

  async function handleSearch() {
    if (!searchQuery.trim()) {
      searchResults = [];
      return;
    }

    try {
      const res = await fetch(`http://localhost:5000/api/help/search?q=${encodeURIComponent(searchQuery)}`);
      if (res.ok) {
        searchResults = await res.json();
      }
    } catch {
      // Local search fallback
      const q = searchQuery.toLowerCase();
      searchResults = [];

      // Search NCIPs
      Object.values(ncipsByCategory).forEach(cat => {
        cat.ncips?.forEach(ncip => {
          if (ncip.title.toLowerCase().includes(q) || ncip.summary.toLowerCase().includes(q)) {
            searchResults.push({ type: 'ncip', ...ncip });
          }
        });
      });

      // Search concepts
      Object.entries(concepts).forEach(([id, c]) => {
        if (c.term.toLowerCase().includes(q) || c.definition.toLowerCase().includes(q)) {
          searchResults.push({ type: 'concept', id, title: c.term, summary: c.definition });
        }
      });
    }
  }

  function toggleCategory(catId) {
    expandedCategory = expandedCategory === catId ? null : catId;
  }

  function selectNCIP(ncip) {
    selectedNCIP = ncip;
    activeTab = 'ncip-detail';
  }

  function selectMP(mp) {
    selectedMP = mp;
    activeTab = 'mp-detail';
  }

  function selectConcept(conceptId) {
    selectedConcept = { id: conceptId, ...concepts[conceptId] };
    activeTab = 'concept-detail';
  }

  function goBack() {
    if (activeTab === 'ncip-detail') {
      selectedNCIP = null;
      activeTab = 'ncips';
    } else if (activeTab === 'mp-detail') {
      selectedMP = null;
      activeTab = 'protocols';
    } else if (activeTab === 'concept-detail') {
      selectedConcept = null;
      activeTab = 'glossary';
    }
  }

  onMount(() => {
    fetchGovernanceData();
  });
</script>

<div class="help-center" in:fade={{ duration: 200 }}>
  <div class="help-header">
    <h2>📚 Governance & Help</h2>
    <p class="subtitle">NatLangChain's unique governance framework</p>
  </div>

  <!-- Search Bar -->
  <div class="search-bar">
    <input
      type="text"
      placeholder="Search governance docs..."
      bind:value={searchQuery}
      on:input={handleSearch}
    />
    {#if searchResults.length > 0}
      <div class="search-results" transition:slide>
        {#each searchResults as result}
          <button
            class="search-result"
            on:click={() => {
              if (result.type === 'ncip') selectNCIP(result);
              else if (result.type === 'mp') selectMP(result);
              else if (result.type === 'concept') selectConcept(result.id);
              searchQuery = '';
              searchResults = [];
            }}
          >
            <span class="result-type">{result.type.toUpperCase()}</span>
            <span class="result-title">{result.title || result.id}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Tab Navigation -->
  <div class="tab-nav">
    <button class:active={activeTab === 'overview'} on:click={() => activeTab = 'overview'}>
      Overview
    </button>
    <button class:active={activeTab === 'ncips' || activeTab === 'ncip-detail'} on:click={() => { activeTab = 'ncips'; selectedNCIP = null; }}>
      NCIPs
    </button>
    <button class:active={activeTab === 'protocols' || activeTab === 'mp-detail'} on:click={() => { activeTab = 'protocols'; selectedMP = null; }}>
      Protocols
    </button>
    <button class:active={activeTab === 'glossary' || activeTab === 'concept-detail'} on:click={() => { activeTab = 'glossary'; selectedConcept = null; }}>
      Glossary
    </button>
    <button class:active={activeTab === 'philosophy'} on:click={() => activeTab = 'philosophy'}>
      Philosophy
    </button>
  </div>

  <!-- Content Area -->
  <div class="tab-content">
    {#if loading}
      <div class="loading">Loading governance documentation...</div>
    {:else}
      <!-- Overview Tab -->
      {#if activeTab === 'overview'}
        <div class="overview" in:fade>
          {#if helpOverview}
            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-number">{helpOverview.stats?.ncip_count || 15}</span>
                <span class="stat-label">NCIPs</span>
              </div>
              <div class="stat-card">
                <span class="stat-number">{helpOverview.stats?.mp_count || 4}</span>
                <span class="stat-label">Protocols</span>
              </div>
              <div class="stat-card">
                <span class="stat-number">{helpOverview.stats?.concept_count || 12}</span>
                <span class="stat-label">Core Terms</span>
              </div>
            </div>

            <div class="highlights">
              <h3>Why NatLangChain is Different</h3>
              <div class="highlight-grid">
                {#each helpOverview.highlights || [] as highlight}
                  <div class="highlight-card">
                    <h4>{highlight.title}</h4>
                    <p>{highlight.description}</p>
                  </div>
                {/each}
              </div>
            </div>

            <div class="quick-links">
              <h3>Quick Start</h3>
              <button on:click={() => activeTab = 'philosophy'}>
                🧠 Read the Design Philosophy
              </button>
              <button on:click={() => activeTab = 'glossary'}>
                📖 Browse the Glossary
              </button>
              <button on:click={() => { activeTab = 'ncips'; expandedCategory = 'foundation'; }}>
                📋 Start with NCIP-000
              </button>
            </div>
          {/if}
        </div>

      <!-- NCIPs Tab -->
      {:else if activeTab === 'ncips'}
        <div class="ncips-browser" in:fade>
          <h3>NatLangChain Improvement Proposals</h3>
          <p class="section-desc">The formal governance specifications that define how NatLangChain works.</p>

          {#each Object.entries(ncipsByCategory) as [catId, category]}
            <div class="category-section">
              <button
                class="category-header"
                class:expanded={expandedCategory === catId}
                on:click={() => toggleCategory(catId)}
              >
                <span class="category-title">{category.title}</span>
                <span class="category-count">{category.ncips?.length || 0} NCIPs</span>
                <span class="expand-icon">{expandedCategory === catId ? '▼' : '▶'}</span>
              </button>

              {#if expandedCategory === catId}
                <div class="category-content" transition:slide>
                  <p class="category-desc">{category.description}</p>
                  {#each category.ncips || [] as ncip}
                    <button class="ncip-item" on:click={() => selectNCIP(ncip)}>
                      <span class="ncip-id">{ncip.id}</span>
                      <span class="ncip-title">{ncip.title}</span>
                      <span class="ncip-arrow">→</span>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        </div>

      <!-- NCIP Detail -->
      {:else if activeTab === 'ncip-detail' && selectedNCIP}
        <div class="detail-view" in:fly={{ x: 20, duration: 200 }}>
          <button class="back-btn" on:click={goBack}>← Back to NCIPs</button>
          <div class="detail-header">
            <span class="detail-id">{selectedNCIP.id}</span>
            <h3>{selectedNCIP.title}</h3>
          </div>
          <div class="detail-body">
            <p class="detail-summary">{selectedNCIP.summary}</p>

            {#if selectedNCIP.key_concepts?.length}
              <div class="detail-section">
                <h4>Key Concepts</h4>
                <div class="concept-tags">
                  {#each selectedNCIP.key_concepts as concept}
                    <span class="concept-tag">{concept}</span>
                  {/each}
                </div>
              </div>
            {/if}

            {#if selectedNCIP.related?.length}
              <div class="detail-section">
                <h4>Related NCIPs</h4>
                <div class="related-links">
                  {#each selectedNCIP.related as relId}
                    <button class="related-link" on:click={() => {
                      const found = Object.values(ncipsByCategory)
                        .flatMap(c => c.ncips || [])
                        .find(n => n.id === relId);
                      if (found) selectNCIP(found);
                    }}>
                      {relId}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </div>

      <!-- Protocols Tab -->
      {:else if activeTab === 'protocols'}
        <div class="protocols-browser" in:fade>
          <h3>Mediator Protocol Specifications</h3>
          <p class="section-desc">Technical specifications for mediation, disputes, and settlements.</p>

          {#each mpList as mp}
            <button class="mp-item" on:click={() => selectMP(mp)}>
              <span class="mp-id">{mp.id}</span>
              <div class="mp-info">
                <span class="mp-title">{mp.title}</span>
                <span class="mp-summary">{mp.summary}</span>
              </div>
              <span class="mp-arrow">→</span>
            </button>
          {/each}
        </div>

      <!-- MP Detail -->
      {:else if activeTab === 'mp-detail' && selectedMP}
        <div class="detail-view" in:fly={{ x: 20, duration: 200 }}>
          <button class="back-btn" on:click={goBack}>← Back to Protocols</button>
          <div class="detail-header">
            <span class="detail-id">{selectedMP.id}</span>
            <h3>{selectedMP.title}</h3>
          </div>
          <div class="detail-body">
            <p class="detail-summary">{selectedMP.summary}</p>

            {#if selectedMP.key_features?.length}
              <div class="detail-section">
                <h4>Key Features</h4>
                <ul class="feature-list">
                  {#each selectedMP.key_features as feature}
                    <li>{feature}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        </div>

      <!-- Glossary Tab -->
      {:else if activeTab === 'glossary'}
        <div class="glossary" in:fade>
          <h3>Core Concepts</h3>
          <p class="section-desc">Quick reference for NatLangChain terminology.</p>

          <div class="concept-grid">
            {#each Object.entries(concepts) as [id, concept]}
              <button class="concept-card" on:click={() => selectConcept(id)}>
                <span class="concept-term">{concept.term}</span>
                <span class="concept-def">{concept.definition.substring(0, 80)}...</span>
              </button>
            {/each}
          </div>
        </div>

      <!-- Concept Detail -->
      {:else if activeTab === 'concept-detail' && selectedConcept}
        <div class="detail-view" in:fly={{ x: 20, duration: 200 }}>
          <button class="back-btn" on:click={goBack}>← Back to Glossary</button>
          <div class="detail-header">
            <h3>{selectedConcept.term}</h3>
          </div>
          <div class="detail-body">
            <p class="detail-summary">{selectedConcept.definition}</p>
            {#if selectedConcept.example}
              <div class="detail-section">
                <h4>Example</h4>
                <p class="example-text">{selectedConcept.example}</p>
              </div>
            {/if}
          </div>
        </div>

      <!-- Philosophy Tab -->
      {:else if activeTab === 'philosophy'}
        <div class="philosophy" in:fade>
          {#if philosophy}
            <h3>{philosophy.title}</h3>
            <p class="philosophy-subtitle">{philosophy.subtitle}</p>

            <div class="principles">
              {#each philosophy.principles || [] as principle}
                <div class="principle-card">
                  <h4>{principle.name}</h4>
                  <p>{principle.summary}</p>
                  {#if principle.detail}
                    <p class="principle-detail">{principle.detail}</p>
                  {/if}
                </div>
              {/each}
            </div>

            {#if philosophy.refusal_doctrine}
              <div class="refusal-doctrine">
                <h3>The Refusal Doctrine</h3>
                <div class="doctrine-columns">
                  <div class="doctrine-column will-not">
                    <h4>❌ Will NOT Automate</h4>
                    <ul>
                      {#each philosophy.refusal_doctrine.will_not_automate as item}
                        <li>{item}</li>
                      {/each}
                    </ul>
                  </div>
                  <div class="doctrine-column will">
                    <h4>✅ WILL Automate</h4>
                    <ul>
                      {#each philosophy.refusal_doctrine.will_automate as item}
                        <li>{item}</li>
                      {/each}
                    </ul>
                  </div>
                </div>
              </div>
            {/if}
          {/if}
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .help-center {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
  }

  .help-header {
    margin-bottom: 24px;
  }

  .help-header h2 {
    font-size: 1.5rem;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .subtitle {
    color: #71717a;
    font-size: 0.9rem;
  }

  /* Search */
  .search-bar {
    position: relative;
    margin-bottom: 20px;
  }

  .search-bar input {
    width: 100%;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    color: #e4e4e7;
    font-size: 0.95rem;
  }

  .search-bar input::placeholder {
    color: #52525b;
  }

  .search-results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: #1a1a2e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    margin-top: 4px;
    max-height: 300px;
    overflow-y: auto;
    z-index: 100;
  }

  .search-result {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 16px;
    background: none;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #e4e4e7;
    text-align: left;
    cursor: pointer;
  }

  .search-result:hover {
    background: rgba(102, 126, 234, 0.1);
  }

  .result-type {
    font-size: 0.7rem;
    padding: 2px 6px;
    background: rgba(102, 126, 234, 0.3);
    border-radius: 4px;
    color: #a5b4fc;
  }

  /* Tab Navigation */
  .tab-nav {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .tab-nav button {
    padding: 10px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #a1a1aa;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab-nav button:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
  }

  .tab-nav button.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
    color: #fff;
  }

  /* Tab Content */
  .tab-content {
    min-height: 400px;
  }

  .loading {
    text-align: center;
    padding: 40px;
    color: #71717a;
  }

  /* Overview */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: rgba(102, 126, 234, 0.1);
    border: 1px solid rgba(102, 126, 234, 0.2);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }

  .stat-number {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: #a5b4fc;
  }

  .stat-label {
    color: #71717a;
    font-size: 0.85rem;
  }

  .highlights h3, .quick-links h3 {
    font-size: 1.1rem;
    color: #e4e4e7;
    margin-bottom: 16px;
  }

  .highlight-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }

  .highlight-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 16px;
  }

  .highlight-card h4 {
    color: #a5b4fc;
    font-size: 0.95rem;
    margin-bottom: 6px;
  }

  .highlight-card p {
    color: #71717a;
    font-size: 0.85rem;
  }

  .quick-links {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .quick-links button {
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #e4e4e7;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }

  .quick-links button:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
  }

  /* NCIPs Browser */
  .section-desc {
    color: #71717a;
    font-size: 0.9rem;
    margin-bottom: 20px;
  }

  .category-section {
    margin-bottom: 8px;
  }

  .category-header {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #e4e4e7;
    cursor: pointer;
    transition: all 0.2s;
  }

  .category-header:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .category-header.expanded {
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    border-bottom-color: transparent;
  }

  .category-title {
    flex: 1;
    text-align: left;
    font-weight: 500;
  }

  .category-count {
    color: #71717a;
    font-size: 0.8rem;
    margin-right: 12px;
  }

  .expand-icon {
    color: #71717a;
    font-size: 0.8rem;
  }

  .category-content {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 12px;
  }

  .category-desc {
    color: #71717a;
    font-size: 0.85rem;
    margin-bottom: 12px;
    padding: 0 4px;
  }

  .ncip-item, .mp-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    color: #e4e4e7;
    cursor: pointer;
    margin-bottom: 6px;
    transition: all 0.2s;
  }

  .ncip-item:hover, .mp-item:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.2);
  }

  .ncip-id, .mp-id {
    font-family: monospace;
    font-size: 0.8rem;
    color: #a5b4fc;
    background: rgba(102, 126, 234, 0.2);
    padding: 4px 8px;
    border-radius: 4px;
    margin-right: 12px;
  }

  .ncip-title {
    flex: 1;
    text-align: left;
  }

  .mp-info {
    flex: 1;
    text-align: left;
  }

  .mp-title {
    display: block;
    font-weight: 500;
  }

  .mp-summary {
    display: block;
    font-size: 0.8rem;
    color: #71717a;
  }

  .ncip-arrow, .mp-arrow {
    color: #71717a;
  }

  /* Detail View */
  .detail-view {
    padding: 4px;
  }

  .back-btn {
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #a1a1aa;
    cursor: pointer;
    margin-bottom: 16px;
    font-size: 0.85rem;
  }

  .back-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
  }

  .detail-header {
    margin-bottom: 20px;
  }

  .detail-id {
    font-family: monospace;
    font-size: 0.85rem;
    color: #a5b4fc;
    background: rgba(102, 126, 234, 0.2);
    padding: 4px 10px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 8px;
  }

  .detail-header h3 {
    font-size: 1.3rem;
    color: #e4e4e7;
  }

  .detail-summary {
    color: #a1a1aa;
    line-height: 1.6;
    margin-bottom: 24px;
  }

  .detail-section {
    margin-bottom: 20px;
  }

  .detail-section h4 {
    font-size: 0.95rem;
    color: #e4e4e7;
    margin-bottom: 12px;
  }

  .concept-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .concept-tag {
    padding: 6px 12px;
    background: rgba(102, 126, 234, 0.15);
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.8rem;
  }

  .related-links {
    display: flex;
    gap: 8px;
  }

  .related-link {
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #e4e4e7;
    cursor: pointer;
    font-family: monospace;
    font-size: 0.85rem;
  }

  .related-link:hover {
    background: rgba(102, 126, 234, 0.1);
  }

  .feature-list {
    list-style: none;
    padding: 0;
  }

  .feature-list li {
    padding: 8px 0;
    padding-left: 24px;
    position: relative;
    color: #a1a1aa;
  }

  .feature-list li::before {
    content: '→';
    position: absolute;
    left: 0;
    color: #a5b4fc;
  }

  /* Glossary */
  .concept-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }

  .concept-card {
    display: flex;
    flex-direction: column;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }

  .concept-card:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.2);
  }

  .concept-term {
    font-weight: 600;
    color: #a5b4fc;
    margin-bottom: 6px;
  }

  .concept-def {
    color: #71717a;
    font-size: 0.85rem;
    line-height: 1.4;
  }

  .example-text {
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-left: 3px solid #a5b4fc;
    color: #a1a1aa;
    font-style: italic;
  }

  /* Philosophy */
  .philosophy h3 {
    font-size: 1.3rem;
    color: #e4e4e7;
    margin-bottom: 4px;
  }

  .philosophy-subtitle {
    color: #a5b4fc;
    font-size: 1rem;
    margin-bottom: 24px;
  }

  .principles {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .principle-card {
    padding: 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
  }

  .principle-card h4 {
    color: #a5b4fc;
    font-size: 1rem;
    margin-bottom: 8px;
  }

  .principle-card p {
    color: #a1a1aa;
    font-size: 0.9rem;
    line-height: 1.5;
  }

  .principle-detail {
    margin-top: 8px;
    font-size: 0.85rem !important;
    color: #71717a !important;
  }

  .refusal-doctrine {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .refusal-doctrine h3 {
    margin-bottom: 20px;
  }

  .doctrine-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  .doctrine-column {
    padding: 20px;
    border-radius: 12px;
  }

  .doctrine-column.will-not {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  .doctrine-column.will {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
  }

  .doctrine-column h4 {
    font-size: 0.95rem;
    margin-bottom: 12px;
  }

  .doctrine-column.will-not h4 {
    color: #fca5a5;
  }

  .doctrine-column.will h4 {
    color: #86efac;
  }

  .doctrine-column ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .doctrine-column li {
    padding: 6px 0;
    font-size: 0.85rem;
    color: #a1a1aa;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .stats-grid {
      grid-template-columns: 1fr;
    }

    .highlight-grid {
      grid-template-columns: 1fr;
    }

    .doctrine-columns {
      grid-template-columns: 1fr;
    }

    .tab-nav {
      flex-wrap: wrap;
    }

    .tab-nav button {
      flex: 1 1 45%;
    }
  }
</style>
