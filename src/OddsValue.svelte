<script>
  import { figure, odds, withMF } from './lib/map.js';
  import { mapMessages } from './lib/map-messages.js';
  import { mf } from './lib/mf.svelte.js';

  let { rate, lang, reference = false, empty = '' } = $props();
  const formatted = $derived(odds(rate, lang));
</script>

{#if formatted}
  <span class="value" title={reference ? mapMessages(lang).estimatedOdds : undefined}>
    {#if reference}<span class="estimate">≈</span>{/if}{formatted}
    {#if mf.value > 0}<span class="mine">({figure(withMF(rate, mf.value))})</span>{/if}
  </span>
{:else}
  {empty}
{/if}

<style>
  .value { display: inline-block; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .estimate { margin-inline-end: .25em; color: var(--dim); }
  .mine { color: #e8c860; margin-inline-start: .45em; }
</style>
