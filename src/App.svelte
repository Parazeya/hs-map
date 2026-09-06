<script>
  import { KIND, asset, called, load, nameOf, recall } from './lib/map.js';
  import { speak } from './lib/lang.js';
  import { talk } from './lib/say.js';
  import WorldMap from './WorldMap.svelte';
  import Sidebar from './Sidebar.svelte';
  import Tooltip from './Tooltip.svelte';
  import ItemCard from './ItemCard.svelte';
  import ItemSheet from './ItemSheet.svelte';
  import BossBar from './BossBar.svelte';

  let data = $state(null);
  let failed = $state(null);
  let lang = $state('en');

  const t = $derived(data ? talk(lang, data.words) : (s) => s);

  let active = $state(null);      // clicked, and stays put
  let hovered = $state(null);     // under the pointer
  // The sidebar's search. It opens on whatever the address was handed — a card
  // in the codex links here by name, and the same box that finds an item by
  // hand lights every zone it drops in.
  let query = $state(recall('find') ?? '');
  let peek = $state(null);        // the item under the pointer in the menu
  let reading = $state(null);     // the item whose card is open over the map
  // What was clicked on the boss bar. A zone and a source are both "what is
  // pinned in the panel", so opening one closes the other rather than stacking
  // two cards nobody asked to read at once.
  let source = $state(null);
  // and a zone clicked on the map takes the panel back from the bar
  $effect(() => {
    if (active) source = null;
  });
  let at = $state({ x: 0, y: 0 });
  // Only a phone reads this. There the panel is 238 px of a 393 px screen and
  // the map is what is left, so it comes over the map when it is wanted and is
  // out of the way when it is not. A wide screen shows it whatever this says —
  // the rule that hides it lives in a media query.
  let panel = $state(false);
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

  // map.json carries English; the other ten are a file each, fetched when they
  // are picked. `lang` moves only once the names are on the records, so the map
  // is never half in one language and half in another — see src/lib/lang.js.
  let loading = $state(null);

  async function pickLang(want) {
    if (want === lang || !data) return;
    loading = want;
    try {
      await speak(data, 'map', want);
      lang = want;
    } catch {
      // the page is whole and readable in the language it is in; taking it down
      // to an error because a second file did not arrive would be the worse
      // answer, and the picker snapping back is what says the switch failed
    } finally {
      loading = null;
    }
  }

  load()
    .then(async (d) => {
      // the game ships eleven languages; the stored choice first, else the
      // browser's, and English if neither is one of them
      const want = remembered() || (navigator.language || 'en').slice(0, 2).toLowerCase();
      const first = d.langs.includes(want) ? want : 'en';
      // before the first paint, so the map is never drawn in English and then
      // relabelled a moment later
      if (first !== 'en') await speak(d, 'map', first).catch(() => {});
      data = d;
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
  <a class="go" href={asset('codex.html')}>{t('Items')} ▶</a>
  <a class="go" href={asset('skills.html')}>{t('Skills')} ▶</a>
  <a class="go" href={asset('bounty.html')}>{t('Bounties')} ▶</a>
  <button type="button" class="only-narrow" class:on={panel} onclick={() => (panel = !panel)}>
    {panel ? '✕' : '☰'}
  </button>
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
          foot={hovered.key
            ? `${t('opened with')} ${t(hovered.key)}`
            : hovered.drops.length
              ? t('the odds are for standing in this zone')
              : null}
        />
      {/if}

      <BossBar
        {data}
        {lang}
        bind:hovered={boss}
        lit={from?.who ?? null}
        {controls}
        pick={(name) => {
          source = source === name ? null : name;
          if (source) active = null;
        }}
      />

    </main>

    {#if peek && !reading}
      <ItemCard {data} name={peek.name} {lang} top={peek.top} />
    {/if}
    <ItemSheet name={reading} {lang} onclose={() => (reading = null)} />

    <!-- The drawer covers the button that opened it, so the way out is the
         map: a tap anywhere off the panel puts it away. Only ever there on a
         narrow screen — on a wide one the panel is a column and never covers
         anything. -->
    {#if panel}
      <button class="scrim only-narrow" aria-label={t('Close')} onclick={() => (panel = false)}></button>
    {/if}
    <Sidebar {data} {lang} {panel} bind:query bind:peek bind:active bind:source
             open={(name) => (reading = name)} />
  </div>
{/if}

<style>
  /* The drawer waits off the right edge, and a page that can be scrolled to it
     is a page that wanders sideways under a thumb. `position` as well as
     `overflow`: without it the drawer is laid out against the viewport rather
     than against this box, and an overflow it does not belong to cannot clip
     it — the page still scrolled 308 px to the right of itself. */
  .app { position: relative; display: flex; height: 100%; overflow: hidden; }

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
    .scrim.only-narrow { display: block; }
  }

  .broke { padding: 3rem; color: var(--rar-satanic); }
  .broke code { color: var(--dim); }

</style>
