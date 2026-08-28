<script>
  import { asset, odds, titleCase } from '../lib/map.js';
  import { talk } from '../lib/say.js';
  import ItemIcon from '../ItemIcon.svelte';
  import Detail from './Detail.svelte';

  const SHEET = 'img/codex.webp';

  let data = $state(null);
  let failed = $state(null);
  let lang = $state('en');

  let query = $state('');
  let rarity = $state(null);
  let kind = $state(null);          // the item type: Sword, Helmet, Charm…
  let stat = $state(null);          // a sid, when the search is for what it does
  let chosen = $state(null);        // the item being read, by key

  /** Rarest first, because that is what anyone is looking for. */
  const ORDER = ['Mythic', 'Satanic Set', 'Satanic', 'Unholy', 'Angelic', 'Heroic',
                 'Runeword', 'Rare', 'Superior', 'Common'];
  const RANK = Object.fromEntries(ORDER.map((r, i) => [r, i]));

  // The language is remembered the way the map's is, and for the same reason.
  const KEPT = 'hs-map.lang';
  const remembered = () => {
    try {
      return localStorage.getItem(KEPT);
    } catch {
      return null;
    }
  };

  fetch(asset('data/codex.json'))
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
    .then((d) => {
      data = d;
      const want = remembered() || (navigator.language || 'en').slice(0, 2).toLowerCase();
      lang = d.langs.includes(want) ? want : 'en';
    })
    .catch((e) => (failed = e));

  $effect(() => {
    if (!data) return;
    try {
      localStorage.setItem(KEPT, lang);
    } catch {
      // a browser that will not store it still shows the page
    }
  });

  const rows = $derived(data ? Object.entries(data.items) : []);

  /** Only the grades and types something is actually on. */
  const grades = $derived(
    ORDER.filter((r) => rows.some(([, it]) => it.rarity === r)),
  );
  const kinds = $derived(
    [...new Set(rows.map(([, it]) => it.type).filter(Boolean))].sort(),
  );

  /**
   * Everything an item can be found by, as one lower-case string.
   *
   * Its name in every language it has one, what it does, what it asks for and
   * what it is — so "resist" finds the things that give it and "Ледяная" finds
   * the same item a Russian player would name. Built once per item and kept,
   * because a search that rebuilds seventeen hundred of these on every keystroke
   * is a search that stutters.
   */
  const haystack = new Map();
  const findable = (key, it) => {
    let s = haystack.get(key);
    if (s === undefined) {
      s = [
        it.name,
        ...Object.values(it.names ?? {}),
        it.type, it.rarity, it.tier,
        it.set, ...Object.values(data.sets[it.set]?.names ?? {}),
        ...(it.weapons ?? []),
        ...[...(it.stats ?? []), ...(it.more ?? []).flatMap((m) => m.stats)]
          .map((v) => `${v.text} ${v.spell ?? ''} ${v.cls ?? ''}`),
        ...(it.places ?? []),
        Object.values(it.lore ?? {}).join(' '),
      ].join(' ').toLowerCase();
      haystack.set(key, s);
    }
    return s;
  };

  const CAP = 300;

  const found = $derived.by(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    let out = rows;
    if (rarity) out = out.filter(([, it]) => it.rarity === rarity);
    if (kind) out = out.filter(([, it]) => it.type === kind);
    // a stat counts wherever it is written: fifty-six runewords keep theirs
    // under "in armour" and nowhere else
    const anyStat = (it) => [...(it.stats ?? []), ...(it.more ?? []).flatMap((m) => m.stats)];
    if (stat) out = out.filter(([, it]) => anyStat(it).some((s) => s.sid === stat));
    if (q) out = out.filter(([k, it]) => findable(k, it).includes(q));

    // With a stat picked, the biggest of it leads — that is what picking one is
    // for. Otherwise the rarest, then the highest tier, then by name.
    const worth = ([, it]) =>
      Math.max(...anyStat(it).filter((s) => s.sid === stat)
        .map((s) => s.max ?? s.min ?? 0), 0);
    return out.slice().sort((a, b) =>
      (stat ? worth(b) - worth(a) : 0) ||
      (RANK[a[1].rarity] ?? 99) - (RANK[b[1].rarity] ?? 99) ||
      (b[1].lvl ?? 0) - (a[1].lvl ?? 0) ||
      a[1].name.localeCompare(b[1].name));
  });

  const shown = $derived(found.slice(0, CAP));
  const item = $derived(chosen ? data?.items[chosen] : null);

  /** The stats worth offering, commonest first, with a search of their own. */
  let statQuery = $state('');
  const statList = $derived.by(() => {
    if (!data) return [];
    const q = statQuery.trim().toLowerCase();
    return data.stats.filter((v) => !q
      || v.text.toLowerCase().includes(q)
      || (v.names?.[lang] ?? '').toLowerCase().includes(q)
      || v.sid.includes(q));
  });

  const nameOf = (it) => it.names?.[lang] || it.name;
  // the game's own vocabulary first, then this site's; see lib/say.js
  const t = $derived(data ? talk(lang, { ...data.words, ...data.types }) : (s) => s);
  const cls = (r) => 'r-' + String(r ?? 'common').toLowerCase().replace(/\s+/g, '-');

  function clear() {
    query = '';
    rarity = null;
    kind = null;
    stat = null;
    statQuery = '';
  }

  const filtered = $derived(Boolean(query.trim() || rarity || kind || stat));

  function onkeydown(e) {
    if (e.key !== 'Escape') return;
    if (chosen) chosen = null;
    else clear();
  }
</script>

<svelte:window {onkeydown} />

{#if failed}
  <p class="failed">{t('The item table would not load')}: {failed.message}</p>
{:else if !data}
  <p class="failed">{t('Reading the item table…')}</p>
{:else}
  <header>
    <a class="back" href={asset('index.html')}>◀ {t('Back')}</a>
    <input
      type="search"
      placeholder={t('Find an item, or what it does…')}
      autocomplete="off"
      spellcheck="false"
      bind:value={query}
    />
    <span class="count">
      {found.length}
      {t(found.length === 1 ? 'item' : 'items')}{found.length > CAP ? `, ${t('showing')} ${CAP}` : ''}
    </span>
    {#if filtered}
      <button class="clear" onclick={clear}>{t('clear')}</button>
    {/if}
    <select bind:value={lang} aria-label={t('Item names')}>
      {#each data.langs as l (l)}<option value={l}>{l.toUpperCase()}</option>{/each}
    </select>
  </header>

  <main>
    <aside class="filters">
      <p class="head">{t('Rarity')}</p>
      <div class="chips">
        {#each grades as r (r)}
          <button class={cls(r)} class:on={rarity === r} onclick={() => (rarity = rarity === r ? null : r)}>
            {t(r)}
          </button>
        {/each}
      </div>

      <p class="head">{t('Type')}</p>
      <div class="chips">
        {#each kinds as k (k)}
          <button class:on={kind === k} onclick={() => (kind = kind === k ? null : k)}>{t(k)}</button>
        {/each}
      </div>

      <p class="head">{t('Stats')}</p>
      <input
        class="statfind"
        type="search"
        placeholder={t('a stat…')}
        autocomplete="off"
        bind:value={statQuery}
      />
      <div class="stats">
        {#each statList as v (v.sid)}
          <button class:on={stat === v.sid} onclick={() => (stat = stat === v.sid ? null : v.sid)}>
            <span class="t">{v.names?.[lang] || v.text}{v.unit ?? ''}</span>
            <span class="n">{v.n}</span>
          </button>
        {/each}
        {#if statList.length === 0}<p class="none">{t('No stat by that name.')}</p>{/if}
      </div>
    </aside>

    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <ul class="list">
      {#each shown as [key, it] (key)}
        <li>
          <button class:on={chosen === key} onclick={() => (chosen = chosen === key ? null : key)}>
            <ItemIcon item={it} sheet={data.sheet} from={SHEET} box={32} />
            <span class="name {cls(it.rarity)}">{nameOf(it)}</span>
            {#if stat}
              {@const mine = [...(it.stats ?? []), ...(it.more ?? []).flatMap((m) => m.stats)].filter((s) => s.sid === stat)}
              <span class="worth">{mine.map((s) => s.max ?? s.min).join(', ')}</span>
            {/if}
            <span class="tier">{it.tier ?? ''}</span>
            <span class="lvl">{it.lvl ? `lvl ${it.lvl}` : ''}</span>
          </button>
        </li>
      {/each}
      {#if found.length === 0}
        <li class="none">{t('Nothing by that name, and nothing that does that.')}</li>
      {/if}
      {#if found.length > CAP}
        <li class="none">…{t('and')} {found.length - CAP} {t('more')}. {t('Narrow it down.')}</li>
      {/if}
    </ul>

    <Detail {data} {item} {lang} {t} sheet={SHEET} pick={(k) => (chosen = k)} />
  </main>
{/if}

<style>
  :global(body) { overflow: hidden; }

  .failed {
    margin: 3rem auto;
    max-width: 34rem;
    color: var(--dim);
    text-align: center;
  }

  header {
    position: fixed;
    inset: 0 0 auto 0;
    height: 52px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 12px;
    background: var(--panel);
    border-bottom: 1px solid var(--edge);
    z-index: 5;
  }
  .back {
    flex: none;
    color: var(--dim);
    text-decoration: none;
    font-size: 12px;
    padding: 5px 8px;
    border: 1px solid var(--edge);
    border-radius: 7px;
  }
  .back:hover { color: var(--hot); border-color: var(--hot); }

  header input[type='search'] {
    flex: 1;
    min-width: 0;
    max-width: 32rem;
    padding: 7px 10px;
    color: inherit;
    font: inherit;
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 8px;
  }
  .count { flex: none; color: var(--dim); font-size: 12px; }
  .clear {
    flex: none;
    color: var(--dim);
    background: none;
    border: 1px solid var(--edge);
    border-radius: 7px;
    padding: 5px 9px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }
  .clear:hover { color: var(--hot); border-color: var(--hot); }
  header select {
    flex: none;
    color: inherit;
    font: inherit;
    font-size: 12px;
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 7px;
    padding: 5px 6px;
  }

  main {
    position: fixed;
    inset: 52px 0 0 0;
    display: grid;
    grid-template-columns: 15rem minmax(0, 1fr) 24rem;
  }

  .filters, .list {
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .filters {
    padding: 10px 12px 24px;
    border-right: 1px solid var(--edge);
  }
  .head {
    margin: 12px 0 6px;
    color: var(--dim);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .8px;
    text-transform: uppercase;
  }
  .head:first-child { margin-top: 0; }
  .chips { display: flex; flex-wrap: wrap; gap: 3px; }
  .chips button, .stats button {
    color: var(--dim);
    background: none;
    border: 1px solid var(--edge);
    border-radius: 6px;
    padding: 3px 7px;
    font: inherit;
    font-size: 11px;
    cursor: pointer;
  }
  .chips button:hover, .stats button:hover { background: #ffffff10; }
  .chips button.on, .stats button.on { border-color: currentColor; background: #ffffff12; }

  .statfind {
    width: 100%;
    box-sizing: border-box;
    padding: 5px 8px;
    color: inherit;
    font: inherit;
    font-size: 12px;
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 7px;
  }
  .stats {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: 6px;
  }
  .stats button {
    display: flex;
    gap: 8px;
    align-items: baseline;
    text-align: left;
  }
  .stats .t { flex: 1; min-width: 0; }
  .stats .n { flex: none; opacity: .55; font-variant-numeric: tabular-nums; }

  .list { margin: 0; padding: 6px 0 24px; list-style: none; }
  .list li { padding: 0 8px; }
  .list li button {
    width: 100%;
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 3px 8px;
    color: inherit;
    font: inherit;
    text-align: left;
    background: none;
    border: 1px solid transparent;
    border-radius: 7px;
    cursor: pointer;
  }
  .list li button:hover { background: #ffffff0c; }
  .list li button.on { border-color: var(--hot); background: #ffffff12; }
  .list .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .list .worth {
    flex: none;
    color: var(--hot);
    font-variant-numeric: tabular-nums;
  }
  .list .tier {
    flex: none;
    min-width: 1.8rem;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    color: #100a13;
    background: var(--dim);
    border-radius: 3px;
    padding: 1px 4px;
  }
  .list .lvl { flex: none; width: 4rem; text-align: right; color: var(--dim); font-size: 12px; }
  .none { color: var(--dim); font-style: italic; padding: 8px 16px; }

  :global(.r-satanic) { color: var(--rar-satanic); }
  :global(.r-satanic-set) { color: var(--rar-set); }
  :global(.r-heroic) { color: var(--rar-heroic); }
  :global(.r-angelic) { color: var(--rar-angelic); }
  :global(.r-unholy) { color: var(--rar-unholy); }
  :global(.r-runeword) { color: var(--rar-runeword); }
  :global(.r-common), :global(.r-rare), :global(.r-superior), :global(.r-mythic) {
    color: var(--rar-common);
  }
</style>
