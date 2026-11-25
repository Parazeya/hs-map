<script>
  import { tick } from 'svelte';
  import { asset, figure, mapDocument, odds, withMF, recall, remember } from '../lib/map.js';
  import { mf, setMF } from '../lib/mf.svelte.js';
  import { hydrate, recordsOf, statsOf, grantsOf } from '../lib/book.js';
  import { talk } from '../lib/say.js';
  import { catalogueLanguage, preferredUiLanguage } from '../lib/ui-language.svelte.js';
  import CatalogueLoadStatus from '../CatalogueLoadStatus.svelte';
  import LanguageNotice from '../LanguageNotice.svelte';
  import ItemIcon from '../ItemIcon.svelte';
  import Detail from './Detail.svelte';
  import Comparison from './Comparison.svelte';
  import { codexPhrase } from './phrases.js';
  import { dropLocations } from './farm.js';

  const SHEET = 'img/codex.webp';

  let data = $state(null);
  let failed = $state(false);
  const startupLang = preferredUiLanguage();
  const language = catalogueLanguage('codex', () => haystack.clear());
  const lang = $derived(language.current);

  let query = $state('');
  let rarity = $state(null);
  let kind = $state(null);          // the item type: Sword, Helmet, Charm…
  let stat = $state(null);          // a sid, when the search is for what it does
  // Read before anything else runs: the effect that writes the address back
  // fires as soon as the page mounts, and with nothing open yet that erases
  // what the address was holding before the table has arrived to check it.
  const asked = { key: recall('item'), record: recall('record') };

  let chosen = $state(null);        // the item being read, by key
  let chosenRecord = $state(null);
  let comparison = $state([]);
  let comparing = $state(false);
  let nextSlot = 0;
  const sameRecord = (a, b) => a.key === b.key && a.variant === b.variant;
  const phrase = (text) => codexPhrase(lang, text);

  function removeComparison(slot) {
    comparison = comparison.filter(entry => entry.slot !== slot);
    if (!comparison.length) comparing = false;
  }

  function updateComparison(entry) {
    if (comparison.some(existing => existing.slot !== entry.slot && sameRecord(existing, entry))) return;
    comparison = comparison.map(existing => existing.slot === entry.slot ? entry : existing);
  }

  function toggleComparison(entry, alreadyPinned) {
    const pinned = comparison.find(existing => sameRecord(existing, entry));
    if (alreadyPinned && pinned) removeComparison(pinned.slot);
    else if (pinned) updateComparison({ ...entry, slot: pinned.slot });
    else if (comparison.length < 2) comparison = [...comparison, { ...entry, slot: nextSlot++ }];
  }
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
  // Sixty-nine sets, and until now the only way to one was to open a piece of
  // it by luck. The bonuses were on the card the whole time; nothing listed the
  // sets themselves.
  let kit = $state(null);
  let kitQuery = $state('');
  let kitOpen = $state(false);

  /** Rarest first, because that is what anyone is looking for. */
  // Rarest first, which is the order anyone looks in — and the order the
  // chips are offered in, so the eye starts where the good things are.
  const ORDER = ['Unholy', 'Angelic', 'Heroic', 'Satanic Set', 'Satanic',
                 'Runeword', 'Mythic', 'Rare', 'Superior', 'Common'];
  const RANK = Object.fromEntries(ORDER.map((r, i) => [r, i]));

  async function load(retry = false) {
    failed = false;
    try {
      const response = await fetch(asset('data/codex.json'), { cache: retry ? 'reload' : 'default' });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const loaded = await response.json();
      await language.prepare(loaded);
      data = hydrate(loaded);
      if (asked.key && data.items[asked.key]) chooseItem(asked.key, null, asked.record);
    } catch {
      failed = true;
    } finally {
      document.getElementById('boot')?.remove();
    }
  }
  const rows = $derived(data ? Object.entries(data.items) : []);

  /** Only the grades and types something is actually on. */
  const grades = $derived(
    ORDER.filter((r) => rows.some(([, it]) => recordsOf(it).some((record) => record.rarity === r))),
  );
  const kinds = $derived(
    [...new Set(rows.flatMap(([, it]) => recordsOf(it).map((record) => record.type)).filter(Boolean))].sort(),
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

  /** The sets, by the name they are shown under. */
  const kits = $derived(
    Object.entries(data?.sets ?? {})
      .map(([key, it]) => ({ key, name: it.names?.[lang] || it.names?.en || key, of: it.of ?? [] }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  );
  const kitHits = $derived.by(() => {
    const q = kitQuery.trim().toLowerCase();
    if (!q || (kit && kits.find((k) => k.key === kit)?.name.toLowerCase() === q)) return kits;
    return kits.filter((k) => k.name.toLowerCase().includes(q) || k.key.toLowerCase().includes(q));
  });
  function pickKit(k) {
    kit = k;
    kitQuery = k ? (kits.find((x) => x.key === k)?.name ?? '') : '';
    kitOpen = false;
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
  const glossary = $derived(new Map((data?.stats ?? []).map(stat => [stat.sid, stat])));
  const findable = (key, it) => {
    let s = haystack.get(key);
    if (s === undefined) {
      s = [
        it.name,
        it.names?.[lang],
        ...recordsOf(it).flatMap((record) => [record.type, record.rarity, record.tier]),
        it.set, ...Object.values(data.sets[it.set]?.names ?? {}),
        ...(it.weapons ?? []),
        // the runes a runeword asks for, so "Vex" finds the six that want one
        ...(it.sockets ?? []).flatMap((k) => [k.name, k.key]),
        ...statsOf(it).map((v) => [v.text, glossary.get(v.sid)?.names?.[lang], v.spell, v.cls].filter(Boolean).join(' ')),
        ...grantsOf(it).flatMap(grant => [grant.names?.en, grant.names?.[lang], grant.talent_key]),
        ...recordsOf(it).flatMap(record => [...dropLocations(record, 'en', data), ...dropLocations(record, lang, data)]),
        Object.values(it.lore ?? {}).join(' '),
      ].join(' ').toLowerCase();
      haystack.set(key, s);
    }
    return s;
  };

  const PAGE_SIZE = 300;
  let page = $state(0);

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
    if (rarity) out = out.filter(([, it]) => recordsOf(it).some((record) => record.rarity === rarity));
    if (kit) out = out.filter(([key]) => data.sets[kit]?.of?.includes(key));
    if (kind) out = out.filter(([, it]) => recordsOf(it).some((record) => record.type === kind));
    // a stat counts wherever it is written: fifty-six runewords keep theirs
    // under "in armour" and nowhere else
    const anyStat = statsOf;
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
        const x = dropLocations(a[1], lang, data)[0] ?? '', y = dropLocations(b[1], lang, data)[0] ?? '';
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

  const pageCount = $derived(Math.max(1, Math.ceil(found.length / PAGE_SIZE)));
  const currentPage = $derived(Math.min(page, pageCount - 1));
  const shown = $derived(found.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE));
  const item = $derived(chosen ? data?.items[chosen] : null);

  $effect(() => {
    query; rarity; kind; kit; stat; sort; down; lang;
    page = 0;
    itemList?.scrollTo(0, 0);
  });

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
  // What is open, in the address, so a card can be reloaded or sent to
  // somebody. Read once when the table arrives, because until then there is
  // nothing to check the key against.
  $effect(() => {
    if (data) remember({ item: chosen, record: chosenRecord });
  });

  function clear() {
    query = '';
    rarity = null;
    kind = null;
    kindQuery = '';
    kit = null;
    kitQuery = '';
    stat = null;
    statQuery = '';
  }

  const filtered = $derived(Boolean(query.trim() || rarity || kind || kit || stat));

  const narrowScreen = window.matchMedia('(max-width: 55rem)');
  let narrow = $state(narrowScreen.matches);
  const reading = $derived(narrow && !!item);
  let box = $state(null);
  let itemList = $state(null);
  let detailPane = $state(null);
  let detailBack = $state(null);
  let filterToggle = $state(null);
  let filterPane = $state(null);
  let returnTo;
  let listScroll = 0;

  $effect(() => {
    const changed = (event) => { narrow = event.matches; };
    narrowScreen.addEventListener('change', changed);
    return () => narrowScreen.removeEventListener('change', changed);
  });

  async function chooseItem(key, trigger = null, record = null) {
    if (trigger && chosen === key) {
      closeItem();
      return;
    }
    if (trigger) {
      returnTo = trigger;
      listScroll = itemList?.scrollTop ?? 0;
    }
    const records = recordsOf(data.items[key]);
    chosenRecord = records.slice(1).some(entry => entry.record_id === record) ? record : null;
    chosen = key;
    filters = false;
    await tick();
    detailPane?.scrollTo(0, 0);
    if (reading) detailBack?.focus({ preventScroll: true });
  }

  async function closeItem() {
    chosen = null;
    chosenRecord = null;
    await tick();
    itemList?.scrollTo(0, listScroll);
    (returnTo?.isConnected ? returnTo : box)?.focus({ preventScroll: true });
  }

  async function toggleFilters() {
    filters = !filters;
    await tick();
    if (filters) filterPane?.querySelector('button')?.focus();
    else filterToggle?.focus({ preventScroll: true });
  }

  function movePage(offset) {
    page = currentPage + offset;
    itemList?.scrollTo(0, 0);
  }

  function comparisonName(entry) {
    const record = data.items[entry.key];
    return recordsOf(record).length > 1
      ? `${nameOf(record)} · ${t('Variant')} ${entry.variant + 1}`
      : nameOf(record);
  }

  function onkeydown(e) {
    if (comparing) return;
    // Ctrl+F is what anyone presses to look for a thing on a page, and the
    // browser's own find would search the three hundred rows that happen to be
    // drawn rather than the seventeen hundred items behind them. So it is
    // taken, and it selects what is already typed, the way a find box does.
    if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) {
      if (reading) return;
      e.preventDefault();
      box?.focus();
      box?.select();
      return;
    }
    if (reading && e.key === 'Tab') {
      const controls = [...detailPane.querySelectorAll('button:not(:disabled), a[href], select:not(:disabled), summary')]
        .filter(control => control.getClientRects().length);
      const first = controls[0];
      const last = controls.at(-1);
      if (!detailPane.contains(document.activeElement) || document.activeElement === (e.shiftKey ? first : last)) {
        e.preventDefault();
        (e.shiftKey ? last : first)?.focus();
      }
      return;
    }
    if (e.key !== 'Escape') return;
    if (filters && narrow) toggleFilters();
    else if (chosen) closeItem();
    else clear();
  }
  load();
</script>

<svelte:window {onkeydown} />

{#snippet languageIssue()}
  <LanguageNotice {lang} failure={language.failure}
    retry={(next) => language.pick(data, next)} dismiss={language.dismiss} />
{/snippet}

{#if !data}
  <CatalogueLoadStatus {failed} loading={codexPhrase(startupLang, 'Reading the item table…')}
    message={codexPhrase(startupLang, 'Could not load the item catalogue.')}
    lang={startupLang} retry={() => load(true)} />
{:else}
  <!-- Three tracks, not a row: the search sits in the middle of the window
       whatever stands beside it, instead of drifting with the width of the
       buttons on its left. -->
  <header inert={reading}>
    <span class="side">
      <a class="back" href={mapDocument('index.html')}>◀ {t('Back')}</a>
      <!-- Only where the three columns cannot stand side by side. On a phone the
           filters filled the screen on their own and the list of items, which is
           what the page is for, was nowhere on it. -->
      <button class="only-narrow" class:on={filters} bind:this={filterToggle}
        aria-expanded={filters} aria-controls="codex-filters" onclick={toggleFilters}>
        {t('Filters')}{filtered ? ' ●' : ''}
      </button>
      <span class="count">
        {found.length}
        {t(found.length === 1 ? 'item' : 'items')}
      </span>
    </span>

    <input
      type="search"
      placeholder={t('Find an item, or what it does…')}
      aria-label={t('Find an item, or what it does…')}
      title={lang === 'en' ? null : t('searched in this language and English')}
      autocomplete="off"
      spellcheck="false"
      bind:this={box}
      bind:value={query}
    />

    <span class="side end">
      <!-- The same box the map has, and the same stored number: a reader who
           opens this page straight from a link has no map to set it on. -->
      <label class="mf" title={t('Your magic find, as your character sheet shows it')}>
        <span class="cap">MF</span>
        <input
          type="number"
          min="0"
          max="10000"
          step="1"
          inputmode="numeric"
          value={mf.value || ''}
          placeholder="0"
          aria-label={t('Your magic find, as your character sheet shows it')}
          oninput={(e) => setMF(e.currentTarget.value)}
        />
        <span class="pc">%</span>
      </label>
      {#if filtered}
        <button class="clear" aria-label={t('clear')} title={t('clear')} onclick={clear}>
          <span class="clear-label">{t('clear')}</span><span class="clear-icon" aria-hidden="true">×</span>
        </button>
      {/if}
      <select
        value={language.pending ?? lang}
        aria-label={t('Item names')}
        aria-busy={!!language.pending}
        class:loading={language.pending != null}
        onchange={(e) => language.pick(data, e.currentTarget.value)}
      >
        {#each data.langs as l (l)}<option value={l}>{l.toUpperCase()}</option>{/each}
      </select>
    </span>
  </header>

  <main class:reading class:with-comparison={comparison.length && !reading}>
    <aside id="codex-filters" class="filters" class:shut={!filters} inert={reading} bind:this={filterPane}>
      <p class="head">{t('Rarity')}{#if rarity}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { rarity = null; }}>×</button>{/if}</p>
      <div class="chips">
        {#each grades as r (r)}
          <button class={cls(r)} class:on={rarity === r} onclick={() => (rarity = rarity === r ? null : r)}>
            {t(r)}
          </button>
        {/each}
      </div>

      <p class="head">{t('Type')}{#if kind}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { pickKind(null); }}>×</button>{/if}</p>
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

      <p class="head">{t('Set')}{#if kit || kitQuery}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { pickKit(null); }}>×</button>{/if}</p>
      <input
        class="kindfind"
        type="search"
        placeholder={t('all')}
        autocomplete="off"
        bind:value={kitQuery}
        onfocus={() => (kitOpen = true)}
      />
      {#if kitOpen}
        <div class="kindlist">
          <button class:on={!kit} onclick={() => pickKit(null)}>{t('all')}</button>
          {#each kitHits as k (k.key)}
            <button class:on={kit === k.key} onclick={() => pickKit(k.key)}>
              {k.name}<span class="count">{k.of.length}</span>
            </button>
          {/each}
        </div>
      {/if}

      <p class="head">{t('Stats')}{#if stat || statQuery}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { stat = null; statQuery = ''; }}>×</button>{/if}</p>
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
            <span class="t">{v.names?.[lang] || t(v.text)}{v.unit ?? ''}</span>
            <span class="n">{v.n}</span>
          </button>
        {/each}
        {#if statList.length === 0}<p class="none">{t('No stat by that name.')}</p>{/if}
      </div>
    </aside>

    <!-- The headings and the rows they head are one column of the three, so
         they ride in one box; loose in the grid the headings took the middle
         track for themselves and pushed the list into the detail's. -->
    <div class="middle" inert={reading || (narrow && filters)}>
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
    <ul class="list" bind:this={itemList}>
      {#each shown as [key, it] (key)}
        <li>
          <button class:on={chosen === key} aria-current={chosen === key ? 'true' : null}
            onclick={(event) => chooseItem(key, event.currentTarget)}>
            <ItemIcon item={it} sheet={data.sheet} from={SHEET} box={32} />
            <span class="name {cls(it.rarity)}">{nameOf(it)}</span>
            {#if stat}
              {@const mine = statsOf(it).filter((s) => s.sid === stat)}
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
            <span class="from">{dropLocations(it, lang, data).join(', ')}</span>
            <span class="odds">{odds(it.rate) || '—'}{#if mf.value > 0 && it.rate}<span class="mine">({figure(withMF(it.rate, mf.value))})</span>{/if}</span>
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
    </ul>
    {#if pageCount > 1}
      <nav class="pagination" aria-label={phrase('Results pages')}>
        <button disabled={currentPage === 0} onclick={() => movePage(-1)}>{phrase('Previous')}</button>
        <span aria-live="polite">{currentPage + 1} / {pageCount}</span>
        <button disabled={currentPage === pageCount - 1} onclick={() => movePage(1)}>{phrase('Next')}</button>
      </nav>
    {/if}
    </div>

    <div class="detail" role={reading ? 'dialog' : undefined} aria-modal={reading ? 'true' : undefined}
      aria-label={reading ? nameOf(item) : undefined} bind:this={detailPane}>
      <!-- On a phone the item covers the list rather than sitting beside it,
           and this is the way back. -->
      {#if reading}
        <div class="detail-nav">
          <button class="back-to-list" aria-label={`${t('Back')} · ${t('Items')}`}
            bind:this={detailBack} onclick={closeItem}>◀ {t('Items')}</button>
          {#if comparison.length}
            <button onclick={() => (comparing = true)} aria-haspopup="dialog">
              {phrase('Compare')} {comparison.length}/2
            </button>
          {/if}
        </div>
      {/if}
      <Detail {data} {item} {lang} {t} sheet={SHEET} pick={chooseItem}
        compare={toggleComparison} {comparison} initialRecordId={chosenRecord}
        onVariantChange={(record, index) => { chosenRecord = index > 0 ? record.record_id : null; }} />
      {#if reading}{@render languageIssue()}{/if}
    </div>
  </main>
  {#if comparison.length && !reading}
    <div class="comparison-bar">
      <span class="comparison-names">{comparison.map(comparisonName).join(' · ')}</span>
      <button onclick={() => (comparing = true)} aria-haspopup="dialog">
        {phrase('Compare')} {comparison.length}/2
      </button>
    </div>
  {/if}
  {#if comparing}
    <Comparison entries={comparison} {data} {lang} {t} sheet={SHEET} change={updateComparison}
      remove={removeComparison} dismiss={() => (comparing = false)} />
  {/if}
  {#if !reading}{@render languageIssue()}{/if}
{/if}

<style>
  :global(body) { overflow: hidden; }

  .comparison-bar button, .detail-nav button, .pagination button {
    color: var(--hot);
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 6px;
    padding: 6px 10px;
    font: inherit;
    cursor: pointer;
  }
  .comparison-bar button:hover, .detail-nav button:hover, .pagination button:hover:not(:disabled) {
    border-color: var(--hot);
  }
  .with-comparison { bottom: 45px; }
  .comparison-bar {
    display: flex;
    position: fixed;
    inset: auto 0 0;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    height: 45px;
    padding: 0 12px;
    background: var(--panel);
    border-top: 1px solid var(--edge);
    z-index: 6;
  }
  .comparison-names {
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: var(--dim);
    font-size: 12px;
  }
  .comparison-bar button { flex: none; font-size: 13px; }

  header {
    position: fixed;
    inset: 0 0 auto 0;
    height: 52px;
    display: grid;
    grid-template-columns: minmax(max-content, 1fr) minmax(12rem, 32rem) minmax(max-content, 1fr);
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
  /* the cross that clears one filter, on that filter's own heading */
  .head { display: flex; align-items: center; gap: 6px; }
  .drop {
    margin-left: auto;
    padding: 0 4px;
    line-height: 1;
    color: var(--dim);
    background: none;
    border: 0;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .drop:hover { color: var(--hot); }

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
  .clear-icon { display: none; }
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
  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 6px 8px;
    border-top: 1px solid var(--edge);
    color: var(--dim);
    font-size: 12px;
  }
  .pagination button { padding: 4px 8px; }
  .pagination button:disabled { cursor: default; opacity: .46; }

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

  .list { flex: 1; margin: 0; padding: 6px 0 24px; list-style: none; }
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
    main { top: 90px; grid-template-columns: minmax(0, 1fr); }
    .only-narrow { display: inline-flex; align-items: center; }

    .filters {
      position: fixed;
      inset: 90px 0 0 0;
      z-index: 4;
      background: #100a13;
      border-right: 0;
    }
    .filters.shut { display: none; }

    .detail { display: none; }
    .reading .detail {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 7;
      overflow-y: auto;
      overscroll-behavior: contain;
      background: #100a13;
    }
    .with-comparison .filters { bottom: 45px; }
    .detail-nav {
      display: flex;
      position: sticky;
      z-index: 2;
      top: 0;
      justify-content: space-between;
      padding: 7px 12px;
      border-bottom: 1px solid var(--edge);
      background: var(--panel);
    }
    .detail-nav button { font-size: 13px; }
    header {
      height: 90px;
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-rows: auto auto;
      gap: 5px;
      padding: 6px 8px;
    }
    header input[type='search'] { grid-area: 2 / 1 / 3 / -1; width: 100%; }
    .side { gap: 5px; }
    .side.end { grid-area: 1 / 2; }
    .clear { padding-inline: 5px; }
    .clear-icon { display: inline; }
    .clear-label { display: none; }
    header .count { display: none; }
  }
  /* the box that sets it, built to stand as tall as the picker beside it */
  .mf {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 7px;
    color: #8a7a72;
    background: #180d13;
    border: 1px solid var(--edge);
    border-radius: 5px;
    font-size: 12px;
    white-space: nowrap;
    cursor: text;
  }
  .mf:hover, .mf:focus-within { border-color: var(--hot); }
  .mf .pc { color: #6d5f59; }
  .mf input {
    width: 4.2em;
    padding: 0;
    color: #e8c860;
    background: none;
    border: 0;
    font: inherit;
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .mf input:focus { outline: none; }
  .mf input::placeholder { color: #5a4e49; }
  .mf input::-webkit-outer-spin-button,
  .mf input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
  .mf input { -moz-appearance: textfield; appearance: textfield; }

  /* the same odds for whoever is reading; see mf.svelte.js */
  .mine { color: #e8c860; margin-left: .45em; }
</style>
