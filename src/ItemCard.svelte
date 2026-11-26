<script>
  import { called, nameOf, zoneDropOdds } from './lib/map.js';
  import { mapMessages } from './lib/map-messages.js';
  import { places, talk } from './lib/say.js';
  import { itemSourceDetails } from './lib/source-search.js';
  import ItemIcon from './ItemIcon.svelte';
  import OddsValue from './OddsValue.svelte';

  let { data, index, name, lang, top, selectedRoom = null } = $props();

  const it = $derived(data.items[name] ?? {});
  const cls = $derived('r-' + String(it.rarity ?? 'common').toLowerCase());
  const t = $derived(talk(lang, data.words));

  const place = $derived(
    places(lang, data.words,
           (n) => data.places?.[n]?.[lang] || data.bosses[n]?.names?.[lang]),
  );

  const locations = $derived(itemSourceDetails(data, index, name));
  const rooms = $derived(locations.rooms.map(node => {
    const chance = node.drops.includes(name) ? zoneDropOdds(node, name, data.items) : null;
    return { node, chance: chance?.oddsBasis === 'base' ? null : chance };
  }));
  const shownRooms = $derived([...rooms].sort((a, b) =>
    Number(b.node.room === selectedRoom) - Number(a.node.room === selectedRoom)
    || Number(Boolean(b.chance?.odds)) - Number(Boolean(a.chance?.odds)),
  ).slice(0, 7));
  const showOwnZone = $derived(it.chase > 0 && !rooms.some(({ chance }) => chance?.oddsBasis === 'zone'));

  // pinned to the menu's edge, level with the row, and kept inside the window
  const y = $derived(Math.max(8, Math.min(top - 20, innerHeight - 340)));
</script>

<div class="card" style="top: {y}px">
  <header>
    <ItemIcon item={it} sheet={data.sheet} box={40} />
    <div>
      <h3 class={cls}>{called(it, name, lang)}</h3>
      <p class="kind">
        <span class="tier">{data.tiers[(it.tier ?? 1) - 1] ?? '?'}</span>
        <span class={cls}>{t(it.rarity)}</span>
        {#if it.inferno}<span class="inferno">{t('Inferno only')}</span>{/if}
      </p>
    </div>
  </header>

  {#if it.rate || showOwnZone}
    <dl>
      {#if it.rate}
        <dt>{t('anywhere')}</dt>
        <dd><OddsValue rate={it.rate} {lang} /></dd>
      {/if}
      {#if showOwnZone}
        <dt>{t('in its own zone')}</dt>
        <dd><OddsValue rate={it.chase} {lang} /></dd>
      {/if}
    </dl>
  {/if}

  {#if locations.sources.length}
    <h4>{t('drops from')}</h4>
    <ul class="zones">
      {#each locations.sources as [key, source] (key)}<li>{called(source, key, lang)}</li>{/each}
    </ul>
  {:else if !locations.rooms.length && it.places?.length}
    <h4>{t('drops from')}</h4>
    <ul>{#each it.places as p (p)}<li>{place(p)}</li>{/each}</ul>
  {/if}

  {#if shownRooms.length}
    <h4>{t('on the map')}</h4>
    <ul class="zones">
      {#each shownRooms as { node, chance } (node.room)}
        <li class="room">
          <span>{nameOf(node, lang)}</span>
          {#if chance?.odds}
            <span class="odds"><OddsValue rate={chance.odds} {lang} reference={chance.oddsBasis === 'reference-zone'} /></span>
          {/if}
        </li>
      {/each}
    </ul>
    {#if rooms.length > shownRooms.length}<p class="foot">…{t('and')} {rooms.length - shownRooms.length} {t('more')}</p>{/if}
    {#if shownRooms.some(({ chance }) => chance?.oddsBasis === 'reference-zone')}
      <p class="foot">≈ {mapMessages(lang).estimatedOdds}</p>
    {/if}
  {/if}
</div>

<style>
  .card {
    position: fixed;
    right: 22.4rem;            /* just off the menu's edge */
    z-index: 30;
    width: 19rem;
    max-height: 22rem;
    overflow: hidden;
    padding: 10px 12px 12px;
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 9px;
    box-shadow: 0 10px 40px #000a;
    pointer-events: none;
  }

  header { display: flex; gap: 10px; align-items: center; }
  h3 { margin: 0; font-size: 15px; font-weight: 600; }
  .kind { display: flex; gap: 7px; align-items: baseline; margin: 3px 0 0; font-size: 12px; }

  .tier {
    min-width: 1.7rem;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    color: #100a13;
    background: var(--dim);
    border-radius: 2px;
    padding: 0 4px;
  }

  .inferno {
    font-size: 10px;
    font-weight: 700;
    color: #ffd0a0;
    background: #7a2410;
    border-radius: 3px;
    padding: 1px 5px;
  }

  dl { display: grid; grid-template-columns: 1fr auto; gap: 2px 12px; margin: 11px 0 0; }
  dt { color: var(--dim); font-size: 12px; }
  dd { margin: 0; font-size: 13px; font-variant-numeric: tabular-nums; }

  h4 {
    margin: 11px 0 3px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .7px;
    color: var(--edge);
  }
  ul { margin: 0; padding: 0; list-style: none; }
  li { font-size: 12px; color: var(--ink); }
  .zones li { color: var(--hot); }
  .room { display: flex; justify-content: space-between; gap: 8px; }
  .odds { color: var(--ink); }
  .foot { color: var(--dim); font-size: 11px; margin: 4px 0 0; }

  .r-satanic { color: var(--rar-satanic); }
  .r-heroic { color: var(--rar-heroic); }
  .r-set { color: var(--rar-set); }
  .r-angelic { color: var(--rar-angelic); }
  .r-unholy { color: var(--rar-unholy); }
  .r-runeword { color: var(--rar-runeword); }
  .r-common { color: var(--rar-common); }

  @media (max-width: 900px) {
    .card { display: none; }
  }
</style>
