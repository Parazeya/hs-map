<script>
  import { asset, odds, titleCase } from '../lib/map.js';
  import { speak } from '../lib/lang.js';
  import { places, talk } from '../lib/say.js';
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
  // Shut, which only means anything on a phone: the rule that reads this flag
  // lives in a media query, so a wide screen shows the column whatever it says.
  // On a narrow one the list is what the page opens on — it is what the page is
  // for — and the button in the header is what brings the filters over it.
  let filters = $state(false);
  // The type is chosen by typing, so the box holds what was typed and the list
  // under it holds what still matches. Picking one writes it into the box and
  // folds the list away, which is what says a choice has been made.
  let kindQuery = $state('');
  let kindOpen = $state(false);

  /** Rarest first, because that is what anyone is looking for. */
  // Rarest first, which is the order anyone looks in — and the order the
  // chips are offered in, so the eye starts where the good things are.
  const ORDER = ['Unholy', 'Angelic', 'Heroic', 'Satanic Set', 'Satanic',
                 'Runeword', 'Mythic', 'Rare', 'Superior', 'Common'];
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

  /**
   * Put back what the file leaves out, so nothing below has to know it was gone.
   *
   * codex.json says four things once that it used to say for every item: the
   * key, the English name, and on each of the 8678 stat lines the stat's own
   * English text and its unit — all of which the `stats` vocabulary at the root
   * or the record's own place in `items` already answers. A line names its stat
   * by index into that vocabulary; here it gets its identifier back. 461 KB of
   * the 2237 raw, and it costs one pass over seventeen hundred records.
   * See `squeeze` in build/build.py.
   */
  function hydrate(d) {
    for (const [key, it] of Object.entries(d.items)) {
      it.key = key;
      it.name ??= it.names?.en;
      for (const row of [...(it.stats ?? []), ...(it.more ?? []).flatMap((m) => m.stats)]) {
        const said = d.stats[row.sid];
        row.sid = said.sid;
        row.text = said.text;
        if (said.unit !== undefined) row.unit = said.unit;
      }
    }
    return d;
  }

  // The language a name is in and the language it is fetched in are two things
  // now: `lang` only moves once the names for it are on the records, so the
  // page never goes blank or half-translated waiting for them. `loading` is
  // what it is waiting for, and it is only ever one file of about fifty
  // kilobytes — see src/lib/lang.js.
  let loading = $state(null);

  async function pickLang(want) {
    if (want === lang || !data) return;
    loading = want;
    try {
      await speak(data, 'codex', want);
      // the search index holds the names it was built from, and there are more
      // of them now
      haystack.clear();
      lang = want;
    } catch {
      // the page is whole and readable in the language it is in; taking it down
      // to an error because a second file did not arrive would be the worse
      // answer, and the picker snapping back is what says the switch failed
    } finally {
      loading = null;
    }
  }

  fetch(asset('data/codex.json'))
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
    .then(async (d) => {
      const want = remembered() || (navigator.language || 'en').slice(0, 2).toLowerCase();
      const first = d.langs.includes(want) ? want : 'en';
      // grafted before the page ever draws, so a Russian reader's first paint
      // is already Russian rather than English replaced a moment later
      if (first !== 'en') await speak(d, 'codex', first).catch(() => {});
      data = hydrate(d);
      lang = first;
    })
    .catch((e) => (failed = e));

  /**
   * Take the boot screen down once there is something to look at.
   *
   * It lives in the HTML rather than here so it paints before this file has
   * been fetched, let alone run — which is the whole point of it — and so
   * taking it down is this file's job. Removed rather than hidden: it covers
   * the window, and a hidden thing that covers the window is a bug waiting.
   */
  $effect(() => {
    if (data) document.getElementById('boot')?.remove();
  });

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
  const kindHits = $derived.by(() => {
    const q = kindQuery.trim().toLowerCase();
    if (!q || (kind && t(kind).toLowerCase() === q)) return kinds;
    return kinds.filter((k) => t(k).toLowerCase().includes(q) || k.toLowerCase().includes(q));
  });
  function pickKind(k) {
    kind = k;
    kindQuery = k ? t(k) : '';
    kindOpen = false;
  }

  /**
   * Everything an item can be found by, as one lower-case string.
   *
   * Its name, what it does, what it asks for and what it is — so "resist" finds
   * the things that give it and "Ледяная" finds the same item a Russian player
   * would name. Built once per item and kept, because a search that rebuilds
   * seventeen hundred of these on every keystroke is a search that stutters.
   *
   * "Its name" used to mean all eleven; a reader now holds English and the one
   * they are reading, so that is what the box looks through, and the empty
   * answer says so rather than letting a search quietly cover less than it did.
   * Cleared when a language arrives, because there is more to look through.
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

  /// Which column the list is ordered by, and which way round. "rarity" is what
  /// it has always been and stays the default.
  const TIERS = ['D', 'C', 'B', 'A', 'S', 'SS'];
  let sort = $state('rarity');
  let down = $state(true);
  function order(by) {
    if (sort === by) down = !down;
    else { sort = by; down = true; }
  }

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
    // for. Otherwise whichever column the reader asked for, and under it the
    // same tie-breaks as always: rarest, then highest tier, then by name.
    const worth = ([, it]) =>
      Math.max(...anyStat(it).filter((s) => s.sid === stat)
        .map((s) => s.max ?? s.min ?? 0), 0);
    const usual = (a, b) =>
      (RANK[a[1].rarity] ?? 99) - (RANK[b[1].rarity] ?? 99) ||
      (b[1].lvl ?? 0) - (a[1].lvl ?? 0) ||
      a[1].name.localeCompare(b[1].name);
    // The direction is inside each comparison rather than a minus sign around
    // it, because two columns must not be turned over with the rest: an item
    // the game states no drop rate for, or no place for, sorts last whichever
    // way the arrow points. It is not the commonest thing in the game — it is a
    // thing the table says nothing about, and floating it to the top of
    // "commonest first" would be the same lie the number 50,000,000 told.
    const dir = down ? 1 : -1;
    const last = (x, y) => (!x !== !y ? (x ? -1 : 1) : 0);
    const BY = {
      rarity: (a, b) => dir * usual(a, b),
      name: (a, b) => dir * a[1].name.localeCompare(b[1].name),
      tier: (a, b) => dir * (TIERS.indexOf(b[1].tier) - TIERS.indexOf(a[1].tier)) || usual(a, b),
      lvl: (a, b) => dir * ((b[1].lvl ?? 0) - (a[1].lvl ?? 0)) || usual(a, b),
      from: (a, b) => {
        const x = a[1].places?.[0] ?? '', y = b[1].places?.[0] ?? '';
        return last(x, y) || dir * x.localeCompare(y) || usual(a, b);
      },
      rate: (a, b) => {
        const x = a[1].rate ?? 0, y = b[1].rate ?? 0;
        return last(x, y) || dir * (y - x) || usual(a, b);
      },
    };
    const cmp = BY[sort] ?? BY.rarity;
    return out.slice().sort((a, b) => (stat ? worth(b) - worth(a) : 0) || cmp(a, b));
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
  /// "Act I Dungeons" and "Colossal Chest" as the reader's language spells them.
  const place = $derived(data ? places(lang, data.words) : (x) => x);

  function clear() {
    query = '';
    rarity = null;
    kind = null;
    stat = null;
    statQuery = '';
  }

  const filtered = $derived(Boolean(query.trim() || rarity || kind || stat));

  let box;                          // the search field, for the shortcut below

  function onkeydown(e) {
    // Ctrl+F is what anyone presses to look for a thing on a page, and the
    // browser's own find would search the three hundred rows that happen to be
    // drawn rather than the seventeen hundred items behind them. So it is
    // taken, and it selects what is already typed, the way a find box does.
    if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
      e.preventDefault();
      box?.focus();
      box?.select();
      return;
    }
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
  <!-- Three tracks, not a row: the search sits in the middle of the window
       whatever stands beside it, instead of drifting with the width of the
       buttons on its left. -->
  <header>
    <span class="side">
      <a class="back" href={asset('index.html')}>◀ {t('Back')}</a>
      <!-- Only where the three columns cannot stand side by side. On a phone the
           filters filled the screen on their own and the list of items, which is
           what the page is for, was nowhere on it. -->
      <button class="only-narrow" class:on={filters} onclick={() => (filters = !filters)}>
        {t('Filters')}{filtered ? ' ●' : ''}
      </button>
      <span class="count">
        {found.length}
        {t(found.length === 1 ? 'item' : 'items')}{found.length > CAP ? `, ${t('showing')} ${CAP}` : ''}
      </span>
    </span>

    <input
      type="search"
      placeholder={t('Find an item, or what it does…')}
      title={lang === 'en' ? null : t('searched in this language and English')}
      autocomplete="off"
      spellcheck="false"
      bind:this={box}
      bind:value={query}
    />

    <span class="side end">
      {#if filtered}
        <button class="clear" onclick={clear}>{t('clear')}</button>
      {/if}
      <select
        value={loading ?? lang}
        aria-label={t('Item names')}
        aria-busy={loading ? 'true' : null}
        class:loading
        onchange={(e) => pickLang(e.currentTarget.value)}
      >
        {#each data.langs as l (l)}<option value={l}>{l.toUpperCase()}</option>{/each}
      </select>
    </span>
  </header>

  <main class:picked={item}>
    <aside class="filters" class:shut={!filters}>
      <p class="head">{t('Rarity')}</p>
      <div class="chips">
        {#each grades as r (r)}
          <button class={cls(r)} class:on={rarity === r} onclick={() => (rarity = rarity === r ? null : r)}>
            {t(r)}
          </button>
        {/each}
      </div>

      <p class="head">{t('Type')}</p>
      <!-- Thirty-four of them, and as a wrapped cloud of chips they were a wall
           to read rather than a thing to choose from. Typed instead: the box
           narrows the list as it is written, the same way the stats below
           already work, and what is picked is written in the box. -->
      <input
        class="kindfind"
        type="search"
        placeholder={t('all')}
        autocomplete="off"
        bind:value={kindQuery}
        onfocus={() => (kindOpen = true)}
      />
      {#if kindOpen}
        <div class="kindlist">
          <button class:on={!kind} onclick={() => pickKind(null)}>{t('all')}</button>
          {#each kindHits as k (k)}
            <button class:on={kind === k} onclick={() => pickKind(k)}>{t(k)}</button>
          {/each}
          {#if kindHits.length === 0}<p class="none">{t('No stat by that name.')}</p>{/if}
        </div>
      {/if}

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

    <!-- The headings and the rows they head are one column of the three, so
         they ride in one box; loose in the grid the headings took the middle
         track for themselves and pushed the list into the detail's. -->
    <div class="middle">
    <div class="cols">
      <!-- The same widths as a row, so a heading stands over its own column.
           Clicking one orders by it; clicking it again turns it round. -->
      <span class="pad"></span>
      <button class="h name" class:by={sort === 'name'} class:down onclick={() => order('name')}>{t('Items')}</button>
      <button class="h tier" class:by={sort === 'tier'} class:down onclick={() => order('tier')}>{t('Tier')}</button>
      <button class="h lvl" class:by={sort === 'lvl'} class:down onclick={() => order('lvl')}>{t('Level')}</button>
      <button class="h from" class:by={sort === 'from'} class:down onclick={() => order('from')}>{t('Drop location')}</button>
      <button class="h odds" class:by={sort === 'rate'} class:down onclick={() => order('rate')}>{t('Chance')}</button>
    </div>

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
            <!-- the badge in a cell of the heading's width, so the two line up -->
            <span class="tiercell">{#if it.tier}<span class="tier">{it.tier}</span>{/if}</span>
            <span class="lvl">{it.lvl ? `lvl ${it.lvl}` : ''}</span>
            <!-- What anyone is actually after, without opening the card: where
                 it comes from and how often. A dash where the game states no
                 rate at all — it does that for two items in five, and printing
                 its placeholder said "one in fifty million" of a thing that
                 simply does not fall out of the world. -->
            <span class="from">{(it.places ?? []).map(place).join(', ')}</span>
            <span class="odds">{odds(it.rate) || '—'}</span>
          </button>
        </li>
      {/each}
      {#if found.length === 0}
        <li class="none">
          {t('Nothing by that name, and nothing that does that.')}
          <!-- and what was looked through, since it is no longer all eleven -->
          {#if lang !== 'en'}<em>{t('searched in this language and English')}</em>{/if}
        </li>
      {/if}
      {#if found.length > CAP}
        <li class="none">…{t('and')} {found.length - CAP} {t('more')}. {t('Narrow it down.')}</li>
      {/if}
    </ul>
    </div>

    <div class="detail">
      <!-- On a phone the item covers the list rather than sitting beside it,
           and this is the way back. -->
      <button class="only-narrow back-to-list" onclick={() => (chosen = null)}>
        ◀ {t('Items')}
      </button>
      <Detail {data} {item} {lang} {t} sheet={SHEET} pick={(k) => (chosen = k)} />
    </div>
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
    display: grid;
    grid-template-columns: 1fr minmax(0, 32rem) 1fr;
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

  .side { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .side.end { justify-content: flex-end; }

  header input[type='search'] {
    width: 100%;
    min-width: 0;
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
  /* while its names are on the wire — the list stays readable in the language
     it is in, and the picker is what says another one is coming */
  header select.loading { opacity: .55; cursor: progress; }

  main {
    position: fixed;
    inset: 52px 0 0 0;
    display: grid;
    grid-template-columns: 15rem minmax(0, 1fr) 24rem;
  }

  .detail { display: contents; }
  .only-narrow { display: none; }

  .middle { display: flex; flex-direction: column; min-height: 0; }
  .cols { flex: none; }

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
  /* The rarity chips wear their own colour, which is how anyone looks for
     them: the eye goes to the red one, not to the third word in the second
     row. Only the rarities — a type has no colour to wear. */
  .chips .r-satanic { --chip: var(--rar-satanic); }
  .chips .r-heroic { --chip: var(--rar-heroic); }
  .chips .r-angelic { --chip: var(--rar-angelic); }
  .chips .r-unholy { --chip: var(--rar-unholy); }
  .chips .r-runeword { --chip: var(--rar-runeword); }
  /* A Satanic Set is a Set — the game shows it green, and it is set pieces that
     it is made of. */
  .chips .r-set, .chips .r-satanic-set { --chip: var(--rar-set); }
  .chips .r-common, .chips .r-mythic,
  .chips .r-rare, .chips .r-superior { --chip: var(--rar-common); }


  /* The same box as the stat search below it. With only a width it fell back
     to the browser's own search input — a pale rounded thing with a different
     height, which is what "the style breaks when you pick one" was. */
  .kindfind {
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
  .kindfind:focus, .statfind:focus { outline: none; border-color: var(--hot); }
  .kindlist {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 13rem;
    margin-top: 4px;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .kindlist button {
    text-align: left;
    color: var(--dim);
    background: none;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 7px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }
  .kindlist button:hover { color: var(--ink); background: #ffffff0c; }
  .kindlist button.on { color: var(--ink); border-color: var(--hot); }

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
  /* Off, a chip is written in its own colour on the dark. On, the two change
     places: dark letters on a solid block of that colour. Text a shade brighter
     was not enough to say which of ten was picked — it read as a hover. */
  .chips button {
    color: var(--chip, var(--dim));
    border-color: color-mix(in srgb, var(--chip, var(--edge)) 40%, var(--edge));
  }
  .chips button.on,
  .chips button.on:hover {
    color: #120c15;
    background: var(--chip, var(--dim));
    border-color: var(--chip, var(--dim));
    font-weight: 700;
  }
  .chips button:hover, .stats button:hover { background: #ffffff10; }
  .stats button.on { border-color: currentColor; background: #ffffff12; }

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

  /* One grid of widths shared by the headings and by every row under them. */
  .cols {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 6px 16px 4px;
    border-bottom: 1px solid var(--edge);
  }
  .cols .pad { flex: none; width: 32px; }
  .cols .h {
    color: var(--dim);
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .6px;
    text-transform: uppercase;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cols .h:hover { color: var(--ink); }
  .cols .h.by { color: var(--hot); }
  .cols .h.by::after { content: ' ↓'; }
  .cols .h.by:not(.down)::after { content: ' ↑'; }
  .cols .name { flex: 1; min-width: 0; text-align: left; }
  .cols .tier { flex: none; width: 4.4rem; text-align: center; }
  .cols .lvl { flex: none; width: 4rem; text-align: right; }
  .cols .from { flex: 0 1 14rem; min-width: 0; text-align: right; }
  .cols .odds { flex: none; width: 6rem; text-align: right; }

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
  .list .tiercell { flex: none; width: 4.4rem; text-align: center; }
  .list .tier {
    display: inline-block;
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
  .list .from {
    flex: 0 1 14rem;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--dim);
    font-size: 12px;
    text-align: right;
  }
  .list .odds {
    flex: none;
    width: 6rem;
    text-align: right;
    color: var(--dim);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  /* A phone has room for the name and little else. */
  @media (max-width: 55rem) {
    .list .from, .list .lvl,
    .cols .from, .cols .lvl { display: none; }
    .list .odds, .cols .odds { width: 4.6rem; }
  }
  .none { color: var(--dim); font-style: italic; padding: 8px 16px; }
  /* what the box looked through, on its own line under the answer */
  .none em { display: block; margin-top: 3px; font-style: normal; opacity: .7; font-size: 12px; }

  :global(.r-satanic) { color: var(--rar-satanic); }
  :global(.r-satanic-set) { color: var(--rar-set); }
  :global(.r-heroic) { color: var(--rar-heroic); }
  :global(.r-angelic) { color: var(--rar-angelic); }
  :global(.r-unholy) { color: var(--rar-unholy); }
  :global(.r-runeword) { color: var(--rar-runeword); }
  :global(.r-common), :global(.r-rare), :global(.r-superior), :global(.r-mythic) {
    color: var(--rar-common);
  }

  /* ── one column at a time ────────────────────────────────────────────────
     Three columns need about 55rem; below that they were 15rem of filters,
     whatever was left for the list, and a detail panel off the edge of the
     screen. On a 393px phone that left the list invisible and the page
     useless. So the filters fold away behind a button, the item covers the
     list while it is open, and each of the three gets the whole width when it
     is the one being read. */
  @media (max-width: 55rem) {
    main { grid-template-columns: minmax(0, 1fr); }
    .only-narrow { display: inline-flex; align-items: center; }

    .filters {
      position: fixed;
      inset: 52px 0 0 0;
      z-index: 4;
      background: #100a13;
      border-right: 0;
    }
    .filters.shut { display: none; }

    .detail {
      display: block;
      position: fixed;
      inset: 52px 0 0 0;
      z-index: 3;
      overflow-y: auto;
      overscroll-behavior: contain;
      background: #100a13;
    }
    /* nothing picked, nothing to cover the list with */
    main:not(.picked) .detail { display: none; }
    .back-to-list {
      margin: 10px 0 0 12px;
    }

    /* The three tracks want 32rem for the middle one alone, which is wider than
       the phone. A row again there, and the search takes what is left of it —
       `width: 100%` in a row is 100% of the header, which laid the search over
       the buttons on both sides of it. */
    header { display: flex; gap: 6px; padding: 0 8px; }
    header input[type='search'] { flex: 1; width: auto; }
    .side { flex: none; }
    header .count { display: none; }
  }
</style>
