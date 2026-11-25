<script>
  import { withMF } from '../lib/map.js';
  import { mf } from '../lib/mf.svelte.js';
  import { dropLocations, dropOdds, itemMapLink } from './farm.js';
  import { codexPhrase } from './phrases.js';

  let { item, lang, data, t } = $props();
  const sources = $derived(dropLocations(item, lang, data));
  const link = $derived(itemMapLink(item));
  const odds = $derived([
    ...(item.rate > 0 ? [{ key: 'Drop rate', rate: item.rate }] : []),
    ...(item.chase > 0 && item.chase !== item.rate ? [{ key: 'In its zone', rate: item.chase }] : []),
  ]);
  const phrase = (text) => codexPhrase(lang, text);
</script>

{#if sources.length || odds.length}
  <section class="summary" aria-label={t('Drop location')}>
    {#if sources.length}
      <div class="sources">
        <h2>{t('Drop location')}</h2>
        <p>{sources.slice(0, 2).join(' · ')}</p>
        {#if sources.length > 2}
          <details>
            <summary>{phrase('More sources')} ({sources.length - 2})</summary>
            <ul>{#each sources.slice(2) as source, index (index)}<li>{source}</li>{/each}</ul>
          </details>
        {/if}
      </div>
    {/if}
    {#if odds.length}
      <dl>
        {#each odds as entry (entry.key)}
          <dt>{t(entry.key)}</dt>
          <dd>
            {dropOdds(entry.rate, lang)}
            {#if mf.value > 0}
              <span class="adjusted">{dropOdds(withMF(entry.rate, mf.value), lang)} · {mf.value}% MF</span>
            {/if}
          </dd>
        {/each}
      </dl>
    {:else}
      <p class="unknown">{phrase('Unknown odds')}</p>
    {/if}
    {#if link}<a href={link}>{t('Show it on the map')} →</a>{/if}
  </section>
{/if}

<style>
  .summary {
    display: grid;
    gap: 7px;
    margin: 8px 0 0;
    padding: 9px 11px;
    border: 1px solid var(--edge);
    border-radius: 7px;
    background: #ffffff04;
    overflow-wrap: anywhere;
    font-size: 13px;
  }
  h2 { margin: 0 0 3px; color: var(--dim); font-size: 10px; text-transform: uppercase; letter-spacing: .07em; }
  p, dl { margin: 0; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 2px 8px; align-items: baseline; }
  dt, .unknown, details { color: var(--dim); font-size: 12px; }
  dd { margin: 0; font-variant-numeric: tabular-nums; }
  .adjusted { display: inline-block; margin-left: .35em; color: #e8c860; font-size: 12px; }
  details { margin-top: 3px; }
  details summary { cursor: pointer; }
  ul { margin: 4px 0 0; padding-left: 1.1em; }
  a { justify-self: start; color: var(--hot); font-size: 12px; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
