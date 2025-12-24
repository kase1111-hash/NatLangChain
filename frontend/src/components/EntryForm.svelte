<script>
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
</script>

<div class="entry-form">
  <h2>Submit New Entry</h2>

  <form on:submit|preventDefault={handleSubmit}>
    <div class="form-group">
      <Tooltip text={ncipDefinitions.author.text} ncipRef={ncipDefinitions.author.ncipRef} position="right">
        <label for="author">Author *</label>
      </Tooltip>
      <input
        id="author"
        type="text"
        bind:value={author}
        placeholder="Your name or identifier"
        required
      />
    </div>

    <div class="form-group">
      <Tooltip text={ncipDefinitions.intent.text} ncipRef={ncipDefinitions.intent.ncipRef} position="right">
        <label for="intent">Intent *</label>
      </Tooltip>
      <input
        id="intent"
        type="text"
        bind:value={intent}
        placeholder="What is the purpose of this entry?"
        required
      />
    </div>

    <div class="form-group">
      <Tooltip text={ncipDefinitions.content.text} ncipRef={ncipDefinitions.content.ncipRef} position="right">
        <label for="content">Content *</label>
      </Tooltip>
      <textarea
        id="content"
        bind:value={content}
        placeholder="Enter the natural language content of your entry..."
        rows="6"
        required
      ></textarea>
    </div>

    <div class="form-group checkbox-group">
      <Tooltip text={ncipDefinitions.agreement.text} ncipRef={ncipDefinitions.agreement.ncipRef} position="right">
        <label>
          <input type="checkbox" bind:checked={isContract} />
          This is a contract entry
        </label>
      </Tooltip>
    </div>

    {#if isContract}
      <div class="form-group">
        <label for="contractType">Contract Type</label>
        <select id="contractType" bind:value={contractType}>
          <option value="offer">Offer</option>
          <option value="seek">Seek</option>
          <option value="proposal">Proposal</option>
          <option value="response">Response</option>
        </select>
      </div>
    {/if}

    {#if error}
      <div class="error-message">{error}</div>
    {/if}

    <div class="form-actions">
      <Tooltip text={ncipDefinitions.validateFirst.text} ncipRef={ncipDefinitions.validateFirst.ncipRef} position="top">
        <button
          type="button"
          class="btn-secondary"
          on:click={handleValidate}
          disabled={validating || !content || !author || !intent}
        >
          {validating ? 'Validating...' : 'Validate First'}
        </button>
      </Tooltip>

      <Tooltip text={ncipDefinitions.entry.text} ncipRef={ncipDefinitions.entry.ncipRef} position="top">
        <button
          type="submit"
          class="btn-primary"
          disabled={submitting || !content || !author || !intent}
        >
          {submitting ? 'Submitting...' : 'Submit Entry'}
        </button>
      </Tooltip>

      <button type="button" class="btn-ghost" on:click={clearForm}>
        Clear
      </button>
    </div>
  </form>

  {#if validationResult}
    <div class="result-section validation-result">
      <h3>Validation Result</h3>
      <div class="result-content">
        <div class="result-status" class:valid={validationResult.validation?.decision === 'VALID'}>
          {validationResult.validation?.decision || 'Unknown'}
        </div>
        {#if validationResult.validation?.paraphrase}
          <div class="result-item">
            <strong>Paraphrase:</strong>
            <p>{validationResult.validation.paraphrase}</p>
          </div>
        {/if}
        {#if validationResult.validation?.reasoning}
          <div class="result-item">
            <strong>Reasoning:</strong>
            <p>{validationResult.validation.reasoning}</p>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  {#if result}
    <div class="result-section submission-result">
      <h3>Submission Result</h3>
      <div class="result-content">
        <div class="result-status success">Entry Submitted</div>
        <p>Your entry has been added to the pending pool.</p>

        <Tooltip text={ncipDefinitions.mining.text} ncipRef={ncipDefinitions.mining.ncipRef} position="top">
          <button
            class="btn-primary mine-btn"
            on:click={handleMine}
            disabled={mining}
          >
            {mining ? 'Mining...' : 'Mine Block Now'}
          </button>
        </Tooltip>

        {#if result.mined}
          <div class="mined-info">
            <p>Block mined successfully!</p>
            <p>Block Index: #{result.mined.block?.index}</p>
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

  h2 {
    font-size: 1.5rem;
    color: #e4e4e7;
    margin-bottom: 24px;
  }

  .form-group {
    margin-bottom: 20px;
  }

  label {
    display: block;
    margin-bottom: 8px;
    color: #a1a1aa;
    font-size: 0.875rem;
  }

  input[type="text"],
  textarea,
  select {
    width: 100%;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    color: #e4e4e7;
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  input[type="text"]:focus,
  textarea:focus,
  select:focus {
    outline: none;
    border-color: #667eea;
  }

  textarea {
    resize: vertical;
    min-height: 120px;
    font-family: inherit;
  }

  select {
    cursor: pointer;
  }

  .checkbox-group label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .checkbox-group input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }

  .error-message {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
  }

  .form-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  button {
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: #e4e4e7;
    border: 1px solid rgba(255, 255, 255, 0.2);
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.15);
  }

  .btn-ghost {
    background: transparent;
    color: #a1a1aa;
  }

  .btn-ghost:hover {
    color: #e4e4e7;
  }

  .result-section {
    margin-top: 32px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
  }

  .result-section h3 {
    margin-bottom: 16px;
    color: #e4e4e7;
  }

  .result-status {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 600;
    margin-bottom: 16px;
    background: rgba(245, 158, 11, 0.2);
    color: #f59e0b;
  }

  .result-status.valid,
  .result-status.success {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
  }

  .result-item {
    margin-bottom: 12px;
  }

  .result-item strong {
    color: #a1a1aa;
    display: block;
    margin-bottom: 4px;
  }

  .result-item p {
    color: #e4e4e7;
    line-height: 1.5;
  }

  .mine-btn {
    margin-top: 16px;
  }

  .mined-info {
    margin-top: 16px;
    padding: 12px;
    background: rgba(34, 197, 94, 0.1);
    border-radius: 8px;
    color: #22c55e;
  }
</style>
