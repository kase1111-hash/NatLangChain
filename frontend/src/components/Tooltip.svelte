<script>
  /**
   * Tooltip Component
   * Provides hover tooltips with NCIP reference information
   *
   * References: NCIP-000 (Terminology Governance), NCIP-001 (Term Registry)
   */
  export let text = '';
  export let ncipRef = '';
  export let position = 'top'; // top, bottom, left, right

  let showTooltip = false;
</script>

<span
  class="tooltip-wrapper"
  on:mouseenter={() => showTooltip = true}
  on:mouseleave={() => showTooltip = false}
  on:focus={() => showTooltip = true}
  on:blur={() => showTooltip = false}
  role="tooltip"
  tabindex="0"
>
  <slot />
  {#if showTooltip && text}
    <div class="tooltip tooltip-{position}">
      <div class="tooltip-content">
        {text}
        {#if ncipRef}
          <span class="ncip-ref">[{ncipRef}]</span>
        {/if}
      </div>
    </div>
  {/if}
</span>

<style>
  .tooltip-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
  }

  .tooltip {
    position: absolute;
    z-index: 1000;
    padding: 10px 14px;
    background: rgba(30, 30, 50, 0.98);
    border: 1px solid rgba(102, 126, 234, 0.4);
    border-radius: 8px;
    color: #e4e4e7;
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: normal;
    max-width: 320px;
    min-width: 200px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    pointer-events: none;
    animation: fadeIn 0.15s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .tooltip-top {
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
  }

  .tooltip-bottom {
    top: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
  }

  .tooltip-left {
    right: calc(100% + 8px);
    top: 50%;
    transform: translateY(-50%);
  }

  .tooltip-right {
    left: calc(100% + 8px);
    top: 50%;
    transform: translateY(-50%);
  }

  .tooltip-content {
    color: #d1d5db;
  }

  .ncip-ref {
    display: block;
    margin-top: 6px;
    font-size: 0.7rem;
    color: #667eea;
    font-weight: 600;
  }
</style>
