<script>
  import { mapMessages } from './lib/map-messages.js';

  let { failed, loading, message, lang, retry } = $props();
</script>

<section class="load-status">
  {#if failed}
    <p role="alert">{message}</p>
    <button onclick={retry}>{mapMessages(lang).retry}</button>
  {:else}
    <p role="status">{loading}</p>
  {/if}
</section>

<style>
  .load-status {
    margin: 4rem auto 0;
    max-width: 34rem;
    padding: 18px;
    color: var(--dim);
    text-align: center;
  }
  button {
    color: var(--hot);
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 6px;
    padding: 6px 10px;
    font: inherit;
    cursor: pointer;
  }
  button:hover { border-color: var(--hot); }
</style>
