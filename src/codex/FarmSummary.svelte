<script>
  import { withMF } from '../lib/map.js';
  import { mf } from '../lib/mf.svelte.js';
  import OddsValue from '../OddsValue.svelte';
  import { dropLocationRows, dropOdds, itemMapLink } from './farm.js';
  import { codexPhrase } from './phrases.js';

  let { item, lang, data, t } = $props();
  const sources = $derived(dropLocationRows(item, lang, data));
  const link = $derived(itemMapLink(item));
  const currentZoneOdds = $derived(sources.some(source => source.rate > 0 && !source.reference));
  const odds = $derived([
    ...(item.rate > 0 ? [{ key: 'Drop rate', rate: item.rate }] : []),
    ...(!currentZoneOdds && item.chase > 0 && item.chase !== item.rate ? [{ key: 'In its zone', rate: item.chase }] : []),
  ]);
  const phrase = (text) => codexPhrase(lang, text);
</script>

{#snippet sourceList(rows)}
  <ul>
    {#each rows as { name, rate, reference } (name)}
      <li><span>{name}</span>{#if rate > 0}<OddsValue {rate} {lang} {reference} />{/if}</li>
    {/each}
  </ul>
{/snippet}

{#if sources.length || odds.length}
  <section class="summary" aria-label={t('Drop location')}>
    {#if sources.length}
      <div class="sources">
        <h2>{t('Drop location')}</h2>
        {@render sourceList(sources.slice(0, 2))}
        {#if sources.length > 2}
          <details>
            <summary>{phrase('More sources')} ({sources.length - 2})</summary>
            {@render sourceList(sources.slice(2))}
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
  ul { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
  li { display: flex; justify-content: space-between; gap: 8px; }
  details ul { margin-top: 4px; }
  a { justify-self: start; color: var(--hot); font-size: 12px; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
