<script>
  import { fly, fade, scale } from 'svelte/transition';
  import { submitEntry, validateEntry, mineBlock } from '../lib/api.js';
  import Tooltip from './Tooltip.svelte';
  import { ncipDefinitions } from '../lib/ncip-definitions.js';

  let content = '';
  let author = '';
  let intent = '';
  let isContract = false;
  let contractType = 'offer';

  let submitting = false;
  let validating = false;
  let mining = false;
  let result = null;
  let validationResult = null;
  let error = null;

  async function handleValidate() {
    if (!content || !author || !intent) {
      error = 'Please fill in all required fields';
      return;
    }

    validating = true;
    error = null;
    validationResult = null;

    try {
      validationResult = await validateEntry(content, intent, author);
    } catch (e) {
      error = 'Validation failed: ' + e.message;
    } finally {
      validating = false;
    }
  }

  async function handleSubmit() {
    if (!content || !author || !intent) {
      error = 'Please fill in all required fields';
      return;
    }

    submitting = true;
    error = null;
    result = null;

    try {
      const metadata = {};
      if (isContract) {
        metadata.is_contract = true;
        metadata.contract_type = contractType;
      }

      result = await submitEntry(content, author, intent, metadata);
    } catch (e) {
      error = 'Submission failed: ' + e.message;
    } finally {
      submitting = false;
    }
  }

  async function handleMine() {
    mining = true;
    error = null;

    try {
      const mineResult = await mineBlock('web-miner');
      result = { ...result, mined: mineResult };
    } catch (e) {
      error = 'Mining failed: ' + e.message;
    } finally {
      mining = false;
    }
  }

  function clearForm() {
    content = '';
    author = '';
    intent = '';
    isContract = false;
    contractType = 'offer';
    result = null;
    validationResult = null;
    error = null;
  }

  const icons = {
    user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    target: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    document: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    contract: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
    check: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    send: 'M12 19l9 2-9-18-9 18 9-2zm0 0v-8',
    clear: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
    mining: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4'
  };
</script>

<div class="entry-form" in:fly={{ y: 20, duration: 400 }}>
  <div class="form-header">
    <div class="header-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 4v16m8-8H4" />
      </svg>
    </div>
    <div class="header-text">
      <h2>Submit New Entry</h2>
      <p class="subtitle">Add content to the blockchain</p>
    </div>
  </div>

  <form on:submit|preventDefault={handleSubmit}>
    <div class="form-card">
      <div class="form-group" in:fly={{ y: 10, duration: 300, delay: 100 }}>
        <Tooltip text={ncipDefinitions.author.text} ncipRef={ncipDefinitions.author.ncipRef} position="right">
          <label for="author">
            <span class="label-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d={icons.user} />
              </svg>
            </span>
            Author <span class="required">*</span>
          </label>
        </Tooltip>
        <input
          id="author"
          type="text"
          bind:value={author}
          placeholder="Your name or identifier"
          required
        />
      </div>

      <div class="form-group" in:fly={{ y: 10, duration: 300, delay: 150 }}>
        <Tooltip text={ncipDefinitions.intent.text} ncipRef={ncipDefinitions.intent.ncipRef} position="right">
          <label for="intent">
            <span class="label-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d={icons.target} />
              </svg>
            </span>
            Intent <span class="required">*</span>
          </label>
        </Tooltip>
        <input
          id="intent"
          type="text"
          bind:value={intent}
          placeholder="What is the purpose of this entry?"
          required
        />
      </div>

      <div class="form-group" in:fly={{ y: 10, duration: 300, delay: 200 }}>
        <Tooltip text={ncipDefinitions.content.text} ncipRef={ncipDefinitions.content.ncipRef} position="right">
          <label for="content">
            <span class="label-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d={icons.document} />
              </svg>
            </span>
            Content <span class="required">*</span>
          </label>
        </Tooltip>
        <textarea
          id="content"
          bind:value={content}
          placeholder="Enter the natural language content of your entry..."
          rows="6"
          required
        ></textarea>
        <div class="char-count">{content.length} characters</div>
      </div>

      <div class="form-group checkbox-group" in:fly={{ y: 10, duration: 300, delay: 250 }}>
        <Tooltip text={ncipDefinitions.agreement.text} ncipRef={ncipDefinitions.agreement.ncipRef} position="right">
          <label class="checkbox-label">
            <div class="checkbox-wrapper">
              <input type="checkbox" bind:checked={isContract} />
              <div class="checkbox-custom">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            </div>
            <span class="checkbox-text">
              <span class="label-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d={icons.contract} />
                </svg>
              </span>
              This is a contract entry
            </span>
          </label>
        </Tooltip>
      </div>

      {#if isContract}
        <div class="form-group contract-type" in:fly={{ y: 10, duration: 300 }}>
          <label for="contractType">Contract Type</label>
          <div class="select-wrapper">
            <select id="contractType" bind:value={contractType}>
              <option value="offer">Offer</option>
              <option value="seek">Seek</option>
              <option value="proposal">Proposal</option>
              <option value="response">Response</option>
            </select>
            <div class="select-arrow">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
          </div>
        </div>
      {/if}
    </div>

    {#if error}
      <div class="error-message" in:scale={{ duration: 200 }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        {error}
      </div>
    {/if}

    <div class="form-actions" in:fly={{ y: 10, duration: 300, delay: 300 }}>
      <Tooltip text={ncipDefinitions.validateFirst.text} ncipRef={ncipDefinitions.validateFirst.ncipRef} position="top">
        <button
          type="button"
          class="btn btn-secondary"
          on:click={handleValidate}
          disabled={validating || !content || !author || !intent}
        >
          {#if validating}
            <div class="btn-spinner"></div>
          {:else}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d={icons.check} />
            </svg>
          {/if}
          <span>{validating ? 'Validating...' : 'Validate First'}</span>
        </button>
      </Tooltip>

      <Tooltip text={ncipDefinitions.entry.text} ncipRef={ncipDefinitions.entry.ncipRef} position="top">
        <button
          type="submit"
          class="btn btn-primary"
          disabled={submitting || !content || !author || !intent}
        >
          {#if submitting}
            <div class="btn-spinner"></div>
          {:else}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d={icons.send} />
            </svg>
          {/if}
          <span>{submitting ? 'Submitting...' : 'Submit Entry'}</span>
        </button>
      </Tooltip>

      <button type="button" class="btn btn-ghost" on:click={clearForm}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d={icons.clear} />
        </svg>
        <span>Clear</span>
      </button>
    </div>
  </form>

  {#if validationResult}
    <div class="result-section validation-result" in:fly={{ y: 20, duration: 300 }}>
      <div class="result-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d={icons.check} />
        </svg>
        <h3>Validation Result</h3>
      </div>
      <div class="result-content">
        <div class="result-status" class:valid={validationResult.validation?.decision === 'VALID'}>
          <span class="status-dot"></span>
          {validationResult.validation?.decision || 'Unknown'}
        </div>
        {#if validationResult.validation?.paraphrase}
          <div class="result-item">
            <strong>Paraphrase</strong>
            <p>{validationResult.validation.paraphrase}</p>
          </div>
        {/if}
        {#if validationResult.validation?.reasoning}
          <div class="result-item">
            <strong>Reasoning</strong>
            <p>{validationResult.validation.reasoning}</p>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  {#if result}
    <div class="result-section submission-result" in:fly={{ y: 20, duration: 300 }}>
      <div class="result-header success">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3>Entry Submitted</h3>
      </div>
      <div class="result-content">
        <p class="success-message">Your entry has been added to the pending pool and awaits mining.</p>

        <Tooltip text={ncipDefinitions.mining.text} ncipRef={ncipDefinitions.mining.ncipRef} position="top">
          <button
            class="btn btn-primary mine-btn"
            on:click={handleMine}
            disabled={mining}
          >
            {#if mining}
              <div class="btn-spinner"></div>
            {:else}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d={icons.mining} />
              </svg>
            {/if}
            <span>{mining ? 'Mining...' : 'Mine Block Now'}</span>
          </button>
        </Tooltip>

        {#if result.mined}
          <div class="mined-info" in:scale={{ duration: 200 }}>
            <div class="mined-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 12l2 2 4-4" />
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              </svg>
            </div>
            <div class="mined-text">
              <p class="mined-title">Block Mined Successfully!</p>
              <p class="mined-index">Block #{result.mined.block?.index}</p>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .entry-form {
    max-width: 700px;
    margin: 0 auto;
  }

  .form-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
  }

  .header-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 16px;
    color: #667eea;
  }

  .header-icon svg {
    width: 28px;
    height: 28px;
  }

  .header-text h2 {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #a855f7 50%, #667eea 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
  }

  .subtitle {
    color: #71717a;
    font-size: 0.9rem;
  }

  .form-card {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 28px;
    margin-bottom: 24px;
  }

  .form-group {
    margin-bottom: 24px;
  }

  .form-group:last-child {
    margin-bottom: 0;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    color: #a1a1aa;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .label-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    color: #667eea;
  }

  .label-icon svg {
    width: 16px;
    height: 16px;
  }

  .required {
    color: #ef4444;
  }

  input[type="text"],
  textarea,
  select {
    width: 100%;
    padding: 14px 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    color: #e4e4e7;
    font-size: 1rem;
    transition: all 0.3s ease;
  }

  input[type="text"]:focus,
  textarea:focus,
  select:focus {
    outline: none;
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  input::placeholder,
  textarea::placeholder {
    color: #52525b;
  }

  textarea {
    resize: vertical;
    min-height: 140px;
    font-family: inherit;
    line-height: 1.6;
  }

  .char-count {
    text-align: right;
    font-size: 0.75rem;
    color: #52525b;
    margin-top: 8px;
  }

  /* Custom Checkbox */
  .checkbox-group {
    margin-top: 8px;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    margin-bottom: 0;
  }

  .checkbox-wrapper {
    position: relative;
  }

  .checkbox-wrapper input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  .checkbox-custom {
    width: 22px;
    height: 22px;
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .checkbox-custom svg {
    width: 14px;
    height: 14px;
    color: white;
    opacity: 0;
    transform: scale(0.5);
    transition: all 0.2s ease;
  }

  .checkbox-wrapper input:checked + .checkbox-custom {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
  }

  .checkbox-wrapper input:checked + .checkbox-custom svg {
    opacity: 1;
    transform: scale(1);
  }

  .checkbox-text {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a1a1aa;
  }

  /* Select Wrapper */
  .select-wrapper {
    position: relative;
  }

  .select-wrapper select {
    appearance: none;
    padding-right: 40px;
    cursor: pointer;
  }

  .select-arrow {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    color: #71717a;
    pointer-events: none;
  }

  .contract-type {
    padding-left: 34px;
    border-left: 2px solid rgba(102, 126, 234, 0.3);
    margin-left: 11px;
  }

  /* Error Message */
  .error-message {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 14px 18px;
    border-radius: 12px;
    margin-bottom: 20px;
    font-size: 0.9rem;
  }

  .error-message svg {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  /* Form Actions */
  .form-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 14px 24px;
    border-radius: 12px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: none;
  }

  .btn svg {
    width: 18px;
    height: 18px;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.05);
    color: #e4e4e7;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.25);
    transform: translateY(-1px);
  }

  .btn-ghost {
    background: transparent;
    color: #71717a;
    padding: 14px 16px;
  }

  .btn-ghost:hover {
    color: #e4e4e7;
    background: rgba(255, 255, 255, 0.05);
  }

  .btn-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid transparent;
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Result Sections */
  .result-section {
    margin-top: 24px;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    overflow: hidden;
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 20px 24px;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #667eea;
  }

  .result-header.success {
    color: #22c55e;
  }

  .result-header svg {
    width: 24px;
    height: 24px;
  }

  .result-header h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e4e4e7;
  }

  .result-content {
    padding: 24px;
  }

  .result-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 20px;
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .result-status.valid {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border-color: rgba(34, 197, 94, 0.3);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .result-item {
    margin-bottom: 16px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
  }

  .result-item:last-child {
    margin-bottom: 0;
  }

  .result-item strong {
    display: block;
    color: #71717a;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;
  }

  .result-item p {
    color: #e4e4e7;
    line-height: 1.6;
  }

  .success-message {
    color: #a1a1aa;
    margin-bottom: 20px;
  }

  .mine-btn {
    width: 100%;
    justify-content: center;
  }

  .mined-info {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 20px;
    padding: 20px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 12px;
  }

  .mined-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(34, 197, 94, 0.2);
    border-radius: 12px;
    color: #22c55e;
  }

  .mined-icon svg {
    width: 24px;
    height: 24px;
  }

  .mined-title {
    color: #22c55e;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .mined-index {
    color: #86efac;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9rem;
  }

  /* Responsive */
  @media (max-width: 640px) {
    .form-header {
      flex-direction: column;
      text-align: center;
    }

    .header-text h2 {
      font-size: 1.5rem;
    }

    .form-card {
      padding: 20px;
    }

    .form-actions {
      flex-direction: column;
    }

    .btn {
      width: 100%;
      justify-content: center;
    }

    .contract-type {
      padding-left: 16px;
      margin-left: 0;
    }
  }
</style>
