<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { fly, fade, slide } from 'svelte/transition';
  import { getChatStatus, sendChatMessage, getChatQuestions, clearChatHistory } from '../lib/api.js';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  const dispatch = createEventDispatcher();

  // Props
  export let currentView = 'dashboard';
  export let isOpen = false;

  // State
  let messages = [];
  let inputMessage = '';
  let isLoading = false;
  let ollamaStatus = { available: false, models: [], model_available: false };
  let starterQuestions = [];
  let showStarterQuestions = true;
  let chatContainer;
  let inputFocused = false;
  let currentTipIndex = 0;
  let tipInterval;
  let showCopyWarning = false;
  let copyWarningTimeout;

  // NCIP Tips - helpful guidance from the documentation
  const ncipTips = [
    {
      tip: "An Intent is your expression of desired outcome - write it in your own words, not legalese.",
      ncipRef: "NCIP-001",
      category: "intent"
    },
    {
      tip: "Be specific about what, who, when, and how much. Vague terms lead to disputes.",
      ncipRef: "NCIP-004",
      category: "clarity"
    },
    {
      tip: "Proof of Understanding means you can explain the contract in your own words, not just copy it.",
      ncipRef: "NCIP-004",
      category: "understanding"
    },
    {
      tip: "Include clear success criteria - how will both parties know the agreement was fulfilled?",
      ncipRef: "NCIP-001",
      category: "success"
    },
    {
      tip: "State what happens if things go wrong. Good contracts plan for failure gracefully.",
      ncipRef: "NCIP-005",
      category: "failure"
    },
    {
      tip: "Avoid ambiguous phrases like 'reasonable time' or 'best effort' - be concrete.",
      ncipRef: "NCIP-002",
      category: "ambiguity"
    },
    {
      tip: "Both parties must explicitly ratify an Agreement - silence is not consent.",
      ncipRef: "NCIP-001",
      category: "ratification"
    },
    {
      tip: "Semantic drift happens when meaning changes over time. Lock important terms at signing.",
      ncipRef: "NCIP-002",
      category: "drift"
    },
    {
      tip: "A contract's meaning is bound to its creation time (Temporal Fixity) - context matters.",
      ncipRef: "NCIP-001",
      category: "temporal"
    },
    {
      tip: "List all Key Obligations clearly - what must each party actually do?",
      ncipRef: "NCIP-004",
      category: "obligations"
    },
    {
      tip: "Disputes have a 24-72 hour cooling period for clarification before escalation.",
      ncipRef: "NCIP-005",
      category: "disputes"
    },
    {
      tip: "When in doubt, ask yourself: would a neutral third party understand this the same way?",
      ncipRef: "NCIP-004",
      category: "clarity"
    }
  ];

  // View-specific tips
  const viewTips = {
    submit: [0, 1, 2, 3, 5, 9],  // Intent, clarity, understanding tips
    contracts: [3, 4, 6, 7, 10], // Success, failure, ratification tips
    dashboard: [8, 7],           // Temporal, drift tips
    explorer: [8, 7],            // Temporal, drift tips
    search: [5, 11]              // Ambiguity, clarity tips
  };

  $: relevantTipIndices = viewTips[currentView] || [0, 1, 2, 3];
  $: currentTip = ncipTips[relevantTipIndices[currentTipIndex % relevantTipIndices.length]];

  // Rotate tips every 6 seconds
  function startTipRotation() {
    stopTipRotation();
    tipInterval = setInterval(() => {
      currentTipIndex = (currentTipIndex + 1) % relevantTipIndices.length;
    }, 6000);
  }

  function stopTipRotation() {
    if (tipInterval) {
      clearInterval(tipInterval);
      tipInterval = null;
    }
  }

  function handleInputFocus() {
    inputFocused = true;
    stopTipRotation();
  }

  function handleInputBlur() {
    // Keep tips hidden once focused, until chat is cleared
  }

  function handleCopyAttempt(e) {
    // Prevent copying assistant messages
    e.preventDefault();
    showCopyWarning = true;

    // Clear any existing timeout
    if (copyWarningTimeout) {
      clearTimeout(copyWarningTimeout);
    }

    // Hide warning after 4 seconds
    copyWarningTimeout = setTimeout(() => {
      showCopyWarning = false;
    }, 4000);
  }

  // Check Ollama status and load starter questions on mount
  onMount(async () => {
    await checkStatus();
    await loadStarterQuestions();
    startTipRotation();
  });

  onDestroy(() => {
    stopTipRotation();
    if (copyWarningTimeout) {
      clearTimeout(copyWarningTimeout);
    }
  });

  async function checkStatus() {
    try {
      ollamaStatus = await getChatStatus();
    } catch (e) {
      ollamaStatus = { available: false, error: e.message };
    }
  }

  async function loadStarterQuestions() {
    try {
      const result = await getChatQuestions();
      starterQuestions = result.questions || [];
    } catch (e) {
      starterQuestions = [];
    }
  }

  function scrollToBottom() {
    if (chatContainer) {
      setTimeout(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }, 50);
    }
  }

  async function sendMessage() {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    inputMessage = '';
    showStarterQuestions = false;

    // Add user message
    messages = [...messages, { role: 'user', content: userMessage }];
    scrollToBottom();

    isLoading = true;

    try {
      const context = {
        current_view: currentView
      };

      const result = await sendChatMessage(userMessage, context);

      if (result.success) {
        messages = [...messages, { role: 'assistant', content: result.response }];
      } else {
        messages = [...messages, {
          role: 'assistant',
          content: result.error || 'Sorry, I encountered an error. Please try again.',
          isError: true
        }];
      }
    } catch (e) {
      messages = [...messages, {
        role: 'assistant',
        content: `Connection error: ${e.message}. Make sure Ollama is running.`,
        isError: true
      }];
    } finally {
      isLoading = false;
      scrollToBottom();
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function askStarterQuestion(question) {
    inputMessage = question;
    sendMessage();
  }

  async function clearChat() {
    try {
      await clearChatHistory();
      messages = [];
      showStarterQuestions = true;
      inputFocused = false;
      currentTipIndex = 0;
      startTipRotation();
      await loadStarterQuestions();
    } catch (e) {
      console.error('Failed to clear chat:', e);
    }
  }

  function togglePanel() {
    dispatch('toggle');
  }

  // View-specific context hints
  const viewHints = {
    dashboard: "I can help you understand the blockchain overview and stats.",
    explorer: "I can explain blocks and entries you're viewing.",
    submit: "I can help you write clear entries and contracts.",
    contracts: "I can help you understand and create contracts.",
    search: "I can help you find what you're looking for."
  };

  $: contextHint = viewHints[currentView] || "How can I help you today?";
</script>

<!-- Toggle Button (always visible) -->
<button
  class="chat-toggle"
  class:open={isOpen}
  on:click={togglePanel}
  title={isOpen ? "Close helper" : "Open AI helper"}
>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    {#if isOpen}
      <path d="M6 18L18 6M6 6l12 12" />
    {:else}
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="10" r="1" fill="currentColor" />
      <circle cx="8" cy="10" r="1" fill="currentColor" />
      <circle cx="16" cy="10" r="1" fill="currentColor" />
    {/if}
  </svg>
</button>

<!-- Chat Panel -->
{#if isOpen}
  <div class="chat-panel" transition:fly={{ x: 320, duration: 300 }}>
    <div class="chat-header">
      <div class="header-info">
        <div class="header-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
            <path d="M8 14s1.5 2 4 2 4-2 4-2" />
            <circle cx="9" cy="10" r="1" fill="currentColor" />
            <circle cx="15" cy="10" r="1" fill="currentColor" />
          </svg>
        </div>
        <div class="header-text">
          <h3>Contract Helper</h3>
          <span class="status" class:connected={ollamaStatus.available}>
            {ollamaStatus.available ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
      <button class="clear-btn" on:click={clearChat} title="Clear conversation">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z" />
        </svg>
      </button>
    </div>

    <div class="chat-messages" bind:this={chatContainer}>
      {#if !ollamaStatus.available}
        <div class="status-message warning" in:fade>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <div>
            <strong>Ollama not connected</strong>
            <p>Start Ollama to enable the AI helper. Run <code>ollama serve</code> in a terminal.</p>
          </div>
        </div>
      {:else if messages.length === 0 && showStarterQuestions}
        <div class="welcome-message" in:fade>
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
              <path d="M8 14s1.5 2 4 2 4-2 4-2" />
              <circle cx="9" cy="10" r="1" fill="currentColor" />
              <circle cx="15" cy="10" r="1" fill="currentColor" />
            </svg>
          </div>
          <h4>Hi! I'm here to help.</h4>
          <p>{contextHint}</p>

          <!-- NCIP Tips - shown until user focuses on input -->
          {#if !inputFocused && currentTip}
            <div class="ncip-tip" in:fade={{ duration: 300 }} out:fade={{ duration: 200 }}>
              <div class="tip-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4M12 8h.01" />
                </svg>
              </div>
              <div class="tip-content">
                <p class="tip-text">{currentTip.tip}</p>
                <span class="tip-ref">{currentTip.ncipRef}</span>
              </div>
            </div>
            <div class="tip-dots">
              {#each relevantTipIndices as _, i}
                <span
                  class="tip-dot"
                  class:active={i === currentTipIndex % relevantTipIndices.length}
                ></span>
              {/each}
            </div>
          {/if}

          {#if inputFocused && starterQuestions.length > 0}
            <div class="starter-questions" in:fade>
              <span class="questions-label">Try asking:</span>
              {#each starterQuestions as question}
                <button
                  class="question-btn"
                  on:click={() => askStarterQuestion(question)}
                >
                  {question}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      {#each messages as message, i}
        <div
          class="message"
          class:user={message.role === 'user'}
          class:assistant={message.role === 'assistant'}
          class:error={message.isError}
          in:fly={{ y: 10, duration: 200, delay: 50 }}
        >
          {#if message.role === 'assistant'}
            <div class="message-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                <circle cx="9" cy="10" r="1" fill="currentColor" />
                <circle cx="15" cy="10" r="1" fill="currentColor" />
              </svg>
            </div>
          {/if}
          <div
            class="message-content"
            class:no-copy={message.role === 'assistant'}
            on:copy|preventDefault={handleCopyAttempt}
          >
            {message.content}
          </div>
          {#if message.role === 'assistant' && !message.isError}
            <div class="no-copy-badge" title="Write your own contract - copying defeats Proof of Understanding">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" />
              </svg>
            </div>
          {/if}
        </div>
      {/each}

      {#if isLoading}
        <div class="message assistant" in:fade>
          <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M8 14s1.5 2 4 2 4-2 4-2" />
              <circle cx="9" cy="10" r="1" fill="currentColor" />
              <circle cx="15" cy="10" r="1" fill="currentColor" />
            </svg>
          </div>
          <div class="message-content typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Copy warning message -->
    {#if showCopyWarning}
      <div class="copy-warning" in:fly={{ y: 10, duration: 200 }} out:fade={{ duration: 150 }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
        <div>
          <strong>Write your own contract</strong>
          <p>Per NCIP-004, you must demonstrate Proof of Understanding. Copying defeats this requirement.</p>
        </div>
      </div>
    {/if}

    <div class="chat-input">
      <textarea
        bind:value={inputMessage}
        on:keydown={handleKeydown}
        on:focus={handleInputFocus}
        on:blur={handleInputBlur}
        placeholder="Ask me anything about contracts..."
        rows="1"
        disabled={!ollamaStatus.available || isLoading}
      ></textarea>
      <button
        class="send-btn"
        on:click={sendMessage}
        disabled={!inputMessage.trim() || !ollamaStatus.available || isLoading}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>
    </div>
  </div>
{/if}

<style>
  .chat-toggle {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
    transition: all 0.3s ease;
    z-index: 1000;
  }

  .chat-toggle:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
  }

  .chat-toggle.open {
    background: rgba(255, 255, 255, 0.1);
    box-shadow: none;
  }

  .chat-toggle svg {
    width: 24px;
    height: 24px;
    color: white;
  }

  .chat-panel {
    position: fixed;
    bottom: 96px;
    right: 24px;
    width: 360px;
    max-height: 600px;
    background: rgba(20, 20, 30, 0.95);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    z-index: 999;
    overflow: hidden;
  }

  .chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.02);
  }

  .header-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
    border-radius: 12px;
  }

  .header-icon svg {
    width: 24px;
    height: 24px;
    color: #a78bfa;
  }

  .header-text h3 {
    font-size: 1rem;
    font-weight: 600;
    color: #e4e4e7;
    margin: 0;
  }

  .status {
    font-size: 0.75rem;
    color: #ef4444;
  }

  .status.connected {
    color: #22c55e;
  }

  .clear-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .clear-btn:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .clear-btn svg {
    width: 16px;
    height: 16px;
    color: #71717a;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    min-height: 300px;
    max-height: 400px;
  }

  .status-message {
    display: flex;
    gap: 12px;
    padding: 16px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 12px;
  }

  .status-message svg {
    width: 20px;
    height: 20px;
    color: #f87171;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .status-message strong {
    display: block;
    color: #f87171;
    margin-bottom: 4px;
  }

  .status-message p {
    font-size: 0.875rem;
    color: #a1a1aa;
    margin: 0;
  }

  .status-message code {
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.8rem;
    color: #e4e4e7;
  }

  .welcome-message {
    text-align: center;
    padding: 24px 16px;
  }

  .welcome-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
    border-radius: 50%;
  }

  .welcome-icon svg {
    width: 32px;
    height: 32px;
    color: #a78bfa;
  }

  .welcome-message h4 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #e4e4e7;
    margin: 0 0 8px;
  }

  .welcome-message p {
    font-size: 0.875rem;
    color: #71717a;
    margin: 0 0 20px;
  }

  .starter-questions {
    text-align: left;
  }

  .questions-label {
    display: block;
    font-size: 0.75rem;
    color: #52525b;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .question-btn {
    display: block;
    width: 100%;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #a1a1aa;
    font-size: 0.875rem;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }

  .question-btn:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.3);
    color: #e4e4e7;
  }

  .message {
    display: flex;
    gap: 10px;
    margin-bottom: 12px;
  }

  .message.user {
    flex-direction: row-reverse;
  }

  .message-avatar {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
    border-radius: 50%;
  }

  .message-avatar svg {
    width: 16px;
    height: 16px;
    color: #a78bfa;
  }

  .message-content {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 0.875rem;
    line-height: 1.5;
    word-wrap: break-word;
  }

  .message.user .message-content {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-bottom-right-radius: 4px;
  }

  .message.assistant .message-content {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
    border-bottom-left-radius: 4px;
  }

  /* Copy protection for assistant messages */
  .message-content.no-copy {
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    cursor: default;
  }

  .no-copy-badge {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 16px;
    height: 16px;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .message.assistant {
    position: relative;
  }

  .message.assistant:hover .no-copy-badge {
    opacity: 0.4;
  }

  .no-copy-badge svg {
    width: 12px;
    height: 12px;
    color: #71717a;
  }

  .message.error .message-content {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
  }

  .message-content.typing {
    display: flex;
    gap: 4px;
    padding: 14px 18px;
  }

  .message-content.typing span {
    width: 6px;
    height: 6px;
    background: #71717a;
    border-radius: 50%;
    animation: typing 1.4s infinite;
  }

  .message-content.typing span:nth-child(2) {
    animation-delay: 0.2s;
  }

  .message-content.typing span:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes typing {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-4px); opacity: 1; }
  }

  /* Copy warning message */
  .copy-warning {
    display: flex;
    gap: 10px;
    padding: 12px 16px;
    margin: 0 16px 8px;
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 10px;
    animation: pulse-warning 2s ease-in-out;
  }

  @keyframes pulse-warning {
    0%, 100% { border-color: rgba(251, 191, 36, 0.3); }
    50% { border-color: rgba(251, 191, 36, 0.6); }
  }

  .copy-warning svg {
    width: 20px;
    height: 20px;
    color: #fbbf24;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .copy-warning strong {
    display: block;
    color: #fbbf24;
    font-size: 0.8125rem;
    margin-bottom: 2px;
  }

  .copy-warning p {
    font-size: 0.75rem;
    color: #a1a1aa;
    margin: 0;
    line-height: 1.4;
  }

  .chat-input {
    display: flex;
    gap: 10px;
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.02);
  }

  .chat-input textarea {
    flex: 1;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    color: #e4e4e7;
    font-size: 0.875rem;
    font-family: inherit;
    resize: none;
    outline: none;
    transition: all 0.2s;
  }

  .chat-input textarea:focus {
    border-color: rgba(102, 126, 234, 0.5);
    background: rgba(255, 255, 255, 0.08);
  }

  .chat-input textarea::placeholder {
    color: #52525b;
  }

  .chat-input textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .send-btn {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .send-btn:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .send-btn svg {
    width: 18px;
    height: 18px;
    color: white;
  }

  /* NCIP Tips styling */
  .ncip-tip {
    display: flex;
    gap: 12px;
    padding: 14px 16px;
    margin: 16px 0 8px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    border: 1px solid rgba(102, 126, 234, 0.2);
    border-radius: 12px;
    text-align: left;
  }

  .tip-icon {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .tip-icon svg {
    width: 20px;
    height: 20px;
    color: #a78bfa;
  }

  .tip-content {
    flex: 1;
    min-width: 0;
  }

  .tip-text {
    font-size: 0.8125rem;
    line-height: 1.5;
    color: #d4d4d8;
    margin: 0 0 6px;
  }

  .tip-ref {
    display: inline-block;
    font-size: 0.6875rem;
    font-weight: 500;
    color: #a78bfa;
    background: rgba(167, 139, 250, 0.15);
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.02em;
  }

  .tip-dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin-bottom: 16px;
  }

  .tip-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    transition: all 0.3s ease;
  }

  .tip-dot.active {
    background: #a78bfa;
    transform: scale(1.2);
  }

  /* Mobile responsiveness */
  @media (max-width: 480px) {
    .chat-panel {
      right: 12px;
      left: 12px;
      width: auto;
      bottom: 88px;
    }

    .chat-toggle {
      right: 16px;
      bottom: 16px;
      width: 48px;
      height: 48px;
    }

    .ncip-tip {
      padding: 12px;
    }

    .tip-text {
      font-size: 0.75rem;
    }
  }
</style>
