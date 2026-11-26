<script>
  import { tick } from 'svelte';
  import { KIND, called, load, mapDocument, nameOf, recall, remember, zoneDropOdds } from './lib/map.js';
  import { mapMessages } from './lib/map-messages.js';
  import { buildSourceIndex, canonicalMapItem, isShelfSource, itemSources, searchItems, searchText } from './lib/source-search.js';
  import { catalogueLanguage, preferredUiLanguage } from './lib/ui-language.svelte.js';
  import { talk } from './lib/say.js';
  import WorldMap from './WorldMap.svelte';
  import Sidebar from './Sidebar.svelte';
  import Tooltip from './Tooltip.svelte';
  import ItemCard from './ItemCard.svelte';
  import ItemSheet from './ItemSheet.svelte';
  import LanguageNotice from './LanguageNotice.svelte';
  import BossBar from './BossBar.svelte';
  import { bridgeConfig, createMapBridge } from './lib/map-bridge.js';

  const mapConfig = bridgeConfig(location.search);
  const mirror = mapConfig?.mode === 'mirror';
  let mapBridge = null;

  let data = $state(null);
  let failed = $state(false);
  let retrying = $state(false);
  const preferredLanguage = preferredUiLanguage();
  const startup = mapMessages(preferredLanguage);
  const language = catalogueLanguage('map');
  const lang = $derived(language.current);
  const loading = $derived(language.pending);

  const t = $derived(data ? talk(lang, data.words) : (s) => s);

  let active = $state(null);
  let hovered = $state(null);
  let query = $state(recall('find') ?? '');
  let linkedItem = $state(null);
  let rarity = $state(null);
  let peek = $state(null);
  let reading = $state(null);
  let pickedSource = $state(null);
  let dismissedQuery = $state(null);
  let at = $state({ x: 0, y: 0 });
  // Only a phone reads this. There the panel is 238 px of a 393 px screen and
  // the map is what is left, so it comes over the map when it is wanted and is
  // out of the way when it is not. A wide screen shows it whatever this says —
  // the rule that hides it lives in a media query.
  let panel = $state(false);
  let map = $state(null);
  let sidebar = $state(null);
  let searchControl = $state(null);
  let boss = $state(null);
  const narrowScreen = matchMedia('(max-width: 46rem)');
  let narrow = $state(narrowScreen.matches);
  const drawerOpen = $derived(narrow && panel);
  let drawerTrigger = null;
  let drawerFocus = 'close';
  let itemTrigger = null;

  const search = $derived(searchText(query));
  const items = $derived(data ? Object.entries(data.items) : []);
  const exactLink = $derived(linkedItem?.query === search ? linkedItem : null);
  const results = $derived.by(() => {
    if (!exactLink) return searchItems(items, search, rarity);
    const item = data.items[exactLink.name];
    if (rarity && rarity !== item.rarity) return { rows: [], exact: null };
    return { rows: [[exactLink.name, item]], exact: exactLink.name };
  });
  const index = $derived(data ? buildSourceIndex(data) : null);
  const searchTargets = $derived(index && (search || rarity)
    ? itemSources(index, results.rows.map(([name]) => name)) : null);
  const targets = $derived(searchTargets ?? (index && peek ? itemSources(index, [peek.name]) : null));
  const exactSources = $derived(results.exact ? index?.get(results.exact) : null);
  const suggested = $derived(!mirror && !active && search !== dismissedQuery && exactSources?.rooms.size === 0
    && exactSources.sources.size === 1 ? exactSources.sources.values().next().value : null);
  const source = $derived(pickedSource ?? suggested);
  const sourceChoices = $derived(search && searchTargets ? [
    ...data.nodes.filter((node) => searchTargets.rooms.has(node.room)).map((node) => ({
      key: node.room, label: nameOf(node, lang), selected: active?.room === node.room,
      pick: () => chooseRoom(active?.room === node.room ? null : node, true),
    })),
    ...[...searchTargets.sources].map((name) => ({
      key: name, label: called(data.bosses[name], name, lang), selected: source === name,
      pick: () => chooseSource(name),
    })),
  ] : []);

  function chooseRoom(node, focus = false) {
    active = node;
    if (!node) {
      dismissedQuery = search;
      return;
    }
    pickedSource = null;
    boss = null;
    peek = null;
    showPanel();
    if (focus) map?.focusOn(node);
  }

  function dismissSource() {
    pickedSource = null;
    boss = null;
    dismissedQuery = search;
  }

  function chooseSource(name) {
    if (pickedSource === name) {
      dismissSource();
      return;
    }
    pickedSource = name;
    active = null;
    hovered = null;
    boss = null;
    peek = null;
    showPanel();
  }

  function showPanel(focus = 'close') {
    if (!panel && narrow) {
      drawerTrigger = document.activeElement;
      drawerFocus = focus;
    }
    panel = true;
  }

  function focusSearch() {
    if (narrow && !panel) showPanel('search');
    else sidebar?.focus('search');
  }

  async function closePanel() {
    panel = false;
    peek = null;
    await tick();
    const trigger = drawerTrigger instanceof HTMLElement && drawerTrigger !== document.body && drawerTrigger.isConnected
      ? drawerTrigger : searchControl;
    trigger?.focus({ preventScroll: true });
    drawerTrigger = null;
    drawerFocus = 'close';
  }

  function openItem(name, trigger) {
    peek = null;
    itemTrigger = trigger;
    reading = name;
  }

  async function closeItem() {
    const trigger = itemTrigger;
    reading = null;
    itemTrigger = null;
    await tick();
    if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    else sidebar?.focus('search');
  }

  $effect(() => {
    const onChange = (event) => { narrow = event.matches; };
    narrowScreen.addEventListener('change', onChange);
    return () => narrowScreen.removeEventListener('change', onChange);
  });
  $effect(() => {
    if (drawerOpen && sidebar) sidebar.focus(drawerFocus);
  });

  $effect(() => {
    if (!data || !map) return;
    const bridge = createMapBridge({ window, config: mapConfig,
      rooms: new Set(data.nodes.map(n => n.room)),
      languages: new Set(data.langs), sources: new Set(Object.keys(data.bosses)),
      read: () => ({ camera: map.readCamera(), viewport: { width: innerWidth, height: innerHeight }, selection: { roomId: active?.room ?? null }, presentation: { query: query.slice(0, 256), lang, source } }),
      apply: async state => {
        map.applyCamera(state.camera);
        active = data.nodes.find(n => n.room === state.selection.roomId) ?? null;
        query = state.presentation.query;
        linkedItem = null;
        pickedSource = active ? null : state.presentation.source;
        await pickLang(state.presentation.lang);
      },
    });
    mapBridge = bridge;
    return () => { bridge.destroy(); if (mapBridge === bridge) mapBridge = null; };
  });
  $effect(() => { active?.room; query; lang; source; mapBridge?.changed(); });
  $effect(() => { if (mapConfig && query.length > 256) query = query.slice(0, 256); });
  $effect(() => {
    if (data && !mirror) remember({ find: query.trim(), item: exactLink?.key, source: pickedSource, room: active?.room });
  });
  $effect(() => {
    if (dismissedQuery !== null && search !== dismissedQuery) dismissedQuery = null;
    if (linkedItem && !exactLink) linkedItem = null;
  });

  const pickLang = (want) => language.pick(data, want, !mirror);

  async function loadMap() {
    try {
      const d = await load(retrying);
      if (!Array.isArray(d?.langs) || !Array.isArray(d.nodes) || !d.items || !d.bosses || !d.map) {
        throw new Error('Invalid map data');
      }
      await language.prepare(d);
      const sourceKey = recall('source');
      const roomKey = recall('room');
      if (!mirror) {
        const key = recall('item');
        const exactItem = canonicalMapItem(d.items, key);
        if (exactItem) {
          query = called(d.items[exactItem], exactItem, lang);
          linkedItem = { key, name: exactItem, query: searchText(query) };
        }
        if (Object.hasOwn(d.bosses, sourceKey) && isShelfSource(d.bosses[sourceKey])) pickedSource = sourceKey;
        else active = d.nodes.find((node) => node.room === roomKey) ?? null;
        panel = Boolean(active || pickedSource || query.trim());
      }
      data = d;
      failed = false;
      if (active) {
        await tick();
        if (active) map?.focusOn(active);
      }
      if (retrying && !drawerOpen) {
        await tick();
        searchControl?.focus({ preventScroll: true });
      }
    } catch {
      failed = true;
    } finally {
      retrying = false;
    }
  }

  loadMap();

  function retry() {
    retrying = true;
    loadMap();
  }


  /**
   * Take the boot screen down once there is something to look at.
   *
   * It lives in the HTML rather than here so it paints before this file has
   * been fetched, let alone run — which is the whole point of it — and so
   * taking it down is this file's job. Removed rather than hidden: it covers
   * the window, and a hidden thing that covers the window is a bug waiting.
   */
  $effect(() => {
    if (data || failed) document.getElementById('boot')?.remove();
  });

  function onkeydown(e) {
    if (mirror || reading || e.defaultPrevented) return;
    if (e.key === 'Tab' && drawerOpen) sidebar?.trapTab(e);
    if (e.key === '/' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.target.closest?.('input, select, textarea, [contenteditable]')) {
      e.preventDefault();
      focusSearch();
    }
    if (e.key !== 'Escape') return;
    e.preventDefault();
    if (drawerOpen) closePanel();
    else if (active) chooseRoom(null);
    else if (source) dismissSource();
    else query = '';
  }

  // Only while something is under the pointer: tracking every move of the mouse
  // across the whole window costs a render each time and buys nothing.
  //
  // The boss shelf was left out of this at first, so a boss's list appeared
  // wherever the last marker had been — or in the corner, if no marker had been
  // touched yet.
  function track(e) {
    if (hovered || boss) at = { x: e.clientX, y: e.clientY };
  }
</script>

<svelte:window onkeydown={onkeydown} onpointermove={track} onresize={() => mapBridge?.changed()} />

{#snippet languageIssue()}
  <LanguageNotice {lang} failure={language.failure} retry={pickLang} dismiss={language.dismiss} />
{/snippet}

<!-- The title bar was a strip of chrome across a map that is only 800px tall to
     begin with. Its two controls earn their place; the words did not. -->
{#snippet controls()}
  <select
    value={loading ?? lang}
    aria-label={t('Zone names')}
    aria-busy={loading ? 'true' : null}
    class:loading
    onchange={(e) => pickLang(e.currentTarget.value)}
  >
    {#each data.langs as code (code)}
      <option value={code}>{code.toUpperCase()}</option>
    {/each}
  </select>
  <button type="button" onclick={() => { active = null; map.fit(); }}>{t('Fit')}</button>
  <a class="go" href={mapDocument('codex.html')} draggable="false">{t('Items')} ▶</a>
  <a class="go" href={mapDocument('skills.html')} draggable="false">{t('Skills')} ▶</a>
  <a class="go" href={mapDocument('bounty.html')} draggable="false">{t('Bounties')} ▶</a>
  <span class="only-narrow search-slot" aria-hidden="true"></span>
{/snippet}

{#if failed}
  <section class="broke" lang={preferredLanguage === 'sp' ? 'es' : preferredLanguage}>
    <p role="status">{retrying ? startup.loading : startup.unavailable}</p>
    <button type="button" disabled={retrying} onclick={retry}>{startup.retry}</button>
  </section>
{:else if data}
  <div class="app" inert={mirror}>
    <main inert={drawerOpen}>
      <button type="button" class="search-access" bind:this={searchControl} aria-label={t('Find an item…')}
        aria-controls="map-sidebar" aria-expanded={narrow ? panel : undefined} onclick={focusSearch}>
        <span class="search-label">{t('Find an item…')}</span><span class="only-narrow" aria-hidden="true">☰</span>
      </button>
      <WorldMap bind:this={map} {data} {lang} bind:active={() => active, (node) => chooseRoom(node)} bind:hovered
        matches={targets?.rooms ?? null} onview={() => mapBridge?.changed()} />


      <!-- hover shows it by the cursor; clicking puts the same list in the
           panel, where it stays and can be read -->
      {#if boss && boss !== source}
        {@const b = data.bosses[boss]}
        <Tooltip
          {data}
          {at}
          {lang}
          title={called(b, boss, lang)}
          subtitle={t(b.kind === 'source' ? 'not a boss' : 'boss')
            + (b.inferno_only ? ` · ${t('only gives these up on Inferno')}` : '')}
          rows={b.drops.map((d) => ({ name: d.item, inferno: d.inferno, odds: data.items[d.item]?.rate }))}
        />
      {:else if hovered && hovered.room !== active?.room}
        <Tooltip
          {data}
          {at}
          {lang}
          title={nameOf(hovered, lang)}
          subtitle={[t(KIND[hovered.kind]), hovered.act ? `${t('act')} ${hovered.act}` : null, hovered.code]
            .filter(Boolean).join(' · ')}
          rows={hovered.drops.map((n) => ({
            name: n,
            inferno: data.items[n]?.inferno,
            ...zoneDropOdds(hovered, n, data.items),
          }))}
          boss={hovered.boss ?? null}
          foot={hovered.key
            ? `${t('opened with')} ${t(hovered.key)}`
            : hovered.drops.length && hovered.drops.every((n) => zoneDropOdds(hovered, n, data.items).oddsBasis === 'zone')
              ? t('the odds are for standing in this zone')
              : null}
        />
      {/if}

      <BossBar
        {data}
        {lang}
        bind:hovered={boss}
        lit={targets?.sources ?? null}
        selected={source}
        {controls}
        pick={chooseSource}
      />

      {#if !drawerOpen}{@render languageIssue()}{/if}

    </main>

    {#if peek && !reading}
      <ItemCard {data} {index} name={peek.name} {lang} top={peek.top} selectedRoom={active?.room} />
    {/if}
    {#if reading}
      <ItemSheet name={reading} title={called(data.items[reading], reading, lang)} {lang}
        itemKey={data.items[reading]?.key} recordId={data.items[reading]?.record_id} onclose={closeItem} />
    {/if}

    <!-- The drawer covers the button that opened it, so the way out is the
         map: a tap anywhere off the panel puts it away. Only ever there on a
         narrow screen — on a wide one the panel is a column and never covers
         anything. -->
    {#if drawerOpen}
      <button type="button" class="scrim" tabindex="-1" aria-label={mapMessages(lang).close} onclick={closePanel}></button>
    {/if}
    <Sidebar bind:this={sidebar} {data} {lang} panel={drawerOpen} {narrow} bind:query bind:peek bind:rarity {active} {source}
      rows={results.rows} {sourceChoices} closeRoom={() => chooseRoom(null)} closeSource={dismissSource}
      {closePanel} open={openItem} {languageIssue} />
  </div>
{/if}

<style>
  /* The drawer waits off the right edge, and a page that can be scrolled to it
     is a page that wanders sideways under a thumb. `position` as well as
     `overflow`: without it the drawer is laid out against the viewport rather
     than against this box, and an overflow it does not belong to cannot clip
     it — the page still scrolled 308 px to the right of itself. */
  .app { position: relative; display: flex; height: 100%; overflow: clip; }

  main {
    position: relative;
    flex: 1;
    min-width: 0;
    overflow: clip;
  }


  /* The link is given a class of its own rather than being reached through its
     parent: `.controls` belongs to BossBar, which renders this snippet, and a
     selector written here cannot see a class scoped to there — so `.controls a`
     matched nothing and the link sat among the buttons underlined and blue. */
  select, button, .go {
    color: var(--ink);
    background: rgba(18, 12, 21, .9);
    border: 1px solid var(--edge);
    border-radius: 6px;
    padding: 5px 9px;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  select:focus, button:focus-visible { outline: none; border-color: var(--hot); }
  /* while its names are on the wire — the map stays readable in the language it
     is in, and the picker is what says another one is coming */
  select.loading { opacity: .55; cursor: progress; }
  button:hover, .go:hover { border-color: var(--hot); color: var(--hot); }
  /* inline-flex so it stands exactly as tall as the button beside it: an inline
     link is sized by its line box and came out three pixels shorter */
  .go {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }
  select option { background: #180d13; }



  .only-narrow { display: none; }
  .search-access { position: absolute; z-index: 12; top: 8px; right: 10px; }
  .search-access:not(:focus-visible) { clip-path: inset(50%); }

  .scrim {
    position: absolute;
    inset: 0;
    z-index: 29;
    padding: 0;
    background: #0007;
    border: 0;
    border-radius: 0;
    cursor: default;
  }

  /* ── the panel comes over the map ────────────────────────────────────────
     On a phone the sidebar took 238 of 393 px and left the map a strip 155 px
     wide, with no way to fold it. It is a drawer there instead, and this is
     the handle. */
  @media (max-width: 46rem) {
    .only-narrow { display: inline-flex; align-items: center; }
    .search-slot { width: 31px; }
    .search-access { top: 26px; min-height: 31px; }
    .search-access:not(:focus-visible) { clip-path: none; }
    .search-label { display: none; }
  }

  .broke { display: grid; height: 100%; place-content: center; justify-items: center; padding: 1.5rem; }
  .broke p { margin: 0 0 .75rem; color: var(--ink); }
  .broke button:disabled { cursor: progress; opacity: .6; }

</style>
