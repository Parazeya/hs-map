<script>
  import { KIND, asset, called, load, nameOf } from './lib/map.js';
  import { talk } from './lib/say.js';
  import WorldMap from './WorldMap.svelte';
  import Sidebar from './Sidebar.svelte';
  import Tooltip from './Tooltip.svelte';
  import ItemCard from './ItemCard.svelte';
  import BossBar from './BossBar.svelte';

  let data = $state(null);
  let failed = $state(null);
  let lang = $state('en');

  const t = $derived(data ? talk(lang, data.words) : (s) => s);

  let active = $state(null);      // clicked, and stays put
  let hovered = $state(null);     // under the pointer
  let query = $state('');         // the sidebar's search
  let peek = $state(null);        // the item under the pointer in the menu
  let at = $state({ x: 0, y: 0 });
  let map = $state(null);
  let boss = $state(null);      // the boss under the pointer on the shelf

  /**
   * Everything that drops the item under the pointer in the menu.
   *
   * A zone is only one of the ways a thing falls. Reading an item that comes off
   * a boss or out of a chest, the map answered with nothing at all — and the
   * answer was there to give, on the shelf beside it or on the dungeon at the
   * end of an act, since the act bosses stand on the map now.
   */
  const from = $derived.by(() => {
    if (!data || !peek) return null;
    const who = new Set(
      Object.entries(data.bosses)
        .filter(([, b]) => b.drops.some((d) => d.item === peek.name))
        .map(([name]) => name),
    );
    const codes = new Set(data.items[peek.name]?.zones ?? []);
    const rooms = new Set(
      data.nodes
        .filter((n) => (n.code && codes.has(n.code)) || (n.boss && who.has(n.boss)))
        .map((n) => n.room),
    );
    return { who, rooms };
  });

  /** Which markers the search or the studied item lights up. */
  const matches = $derived.by(() => {
    if (!data) return null;
    if (from) return from.rooms;
    const q = query.trim().toLowerCase();
    if (q.length < 2) return null;
    return new Set(
      data.nodes.filter((n) => n.drops.some((name) => name.includes(q))).map((n) => n.room),
    );
  });

  /**
   * The language, remembered between visits.
   *
   * Reading a map in a language you did not choose is a small thing to have to
   * fix on every visit. A stored choice wins over the browser's, because it was
   * made here and on purpose; the browser's is only the opening guess. Both are
   * checked against what the game actually ships before being believed.
   *
   * In a try, because storage throws outright in a browser told to refuse it
   * rather than merely coming back empty.
   */
  const KEPT = 'hs-map.lang';
  const remembered = () => {
    try {
      return localStorage.getItem(KEPT);
    } catch {
      return null;
    }
  };

  load()
    .then((d) => {
      data = d;
      // the game ships eleven languages; the stored choice first, else the
      // browser's, and English if neither is one of them
      const want = remembered() || (navigator.language || 'en').slice(0, 2).toLowerCase();
      lang = d.langs.includes(want) ? want : 'en';
    })
    .catch((e) => (failed = e));

  $effect(() => {
    if (!data) return;
    try {
      localStorage.setItem(KEPT, lang);
    } catch {
      // a browser that will not store it still shows the map
    }
  });

  function onkeydown(e) {
    if (e.key !== 'Escape') return;
    if (active) active = null;
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

<svelte:window onkeydown={onkeydown} onpointermove={track} />

<!-- The title bar was a strip of chrome across a map that is only 800px tall to
     begin with. Its two controls earn their place; the words did not. -->
{#snippet controls()}
  <select bind:value={lang} aria-label={t('Zone names')}>
    {#each data.langs as code (code)}
      <option value={code}>{code.toUpperCase()}</option>
    {/each}
  </select>
  <button type="button" onclick={() => { active = null; map.fit(); }}>{t('Fit')}</button>
  <a class="go" href={asset('codex.html')}>{t('Items')} ▶</a>
{/snippet}

{#if failed}
  <p class="broke">The map data would not load.<br><code>{failed.message}</code></p>
{:else if data}
  <div class="app">
    <main>
      <WorldMap bind:this={map} {data} {lang} bind:active bind:hovered {matches} />


      <!-- hover shows it by the cursor; clicking puts the same list in the
           panel, where it stays and can be read -->
      {#if boss}
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
            odds: data.items[n]?.chase ?? data.items[n]?.rate,
          }))}
          boss={hovered.boss ?? null}
          foot={hovered.drops.length ? t('the odds are for standing in this zone') : null}
        />
      {/if}

      <BossBar {data} {lang} bind:hovered={boss} lit={from?.who ?? null} {controls} />

    </main>

    {#if peek}
      <ItemCard {data} name={peek.name} {lang} top={peek.top} />
    {/if}

    <Sidebar {data} {lang} bind:query bind:peek bind:active />
  </div>
{/if}

<style>
  .app { display: flex; height: 100%; }

  main {
    position: relative;
    flex: 1;
    min-width: 0;
    overflow: hidden;
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
  button:hover, .go:hover { border-color: var(--hot); color: var(--hot); }
  /* inline-flex so it stands exactly as tall as the button beside it: an inline
     link is sized by its line box and came out three pixels shorter */
  .go {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }
  select option { background: #180d13; }


  .broke { padding: 3rem; color: var(--rar-satanic); }
  .broke code { color: var(--dim); }

</style>
