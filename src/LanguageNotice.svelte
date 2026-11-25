<script>
  import { catalogueMessages } from './lib/catalogue-messages.js';
  import { mapMessages } from './lib/map-messages.js';

  let { lang, failure, retry, dismiss } = $props();
</script>

{#if failure}
  <div class="notice">
    <p role="status">{catalogueMessages(lang).languageError}</p>
    <button onclick={() => retry(failure)}>{mapMessages(lang).retry}</button>
    <button aria-label={mapMessages(lang).close} onclick={dismiss}>×</button>
  </div>
{/if}

<style>
  .notice {
    position: fixed;
    z-index: 8;
    bottom: 56px;
    inset-inline-end: 10px;
    display: flex;
    align-items: center;
    gap: 7px;
    width: max-content;
    max-width: calc(100% - 20px);
    padding: 8px;
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 6px;
    font-size: 13px;
  }
  p { margin: 0; }
  button {
    flex: none;
    padding: 5px 7px;
    color: var(--hot);
    background: transparent;
    border: 1px solid var(--edge);
    border-radius: 5px;
    font: inherit;
    cursor: pointer;
  }
  button:hover { border-color: var(--hot); }
</style>
