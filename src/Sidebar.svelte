<script>
  import { KIND, asset, called, nameOf, odds, titleCase } from './lib/map.js';
  import { talk } from './lib/say.js';
  import ItemIcon from './ItemIcon.svelte';

  let {
    data,
    lang,
    query = $bindable(''),
    peek = $bindable(null),      // the item under the pointer, and where its row sits
    active = $bindable(null),
    panel = false,               // only a narrow screen reads this; see App
  } = $props();

  /** Rarest first, because that is what anyone is looking for. */
  const ORDER = ['Satanic', 'Unholy', 'Angelic', 'Heroic', 'Set', 'Runeword', 'Common'];
  const RANK = Object.fromEntries(ORDER.map((r, i) => [r, i]));

  let rarity = $state(null);

  const all = $derived(Object.entries(data.items));
  // Only the grades something is actually on. The full scale has seven rungs
  // and the tables use five: nothing in the game is Common or a Runeword, so
  // those two buttons could only ever answer "Nothing by that name". Counted
  // rather than crossed off a list, so a patch that adds a runeword brings its
  // button back without anyone remembering to.
  const grades = $derived(ORDER.filter((r) => all.some(([, it]) => it.rarity === r)));

  const found = $derived.by(() => {
    const q = query.trim().toLowerCase();
    let rows = all;
    if (rarity) rows = rows.filter(([, it]) => it.rarity === rarity);
    // by any of its names, not only the English key: a reader who has set the
    // page to Russian types Russian, and the eleven names ride on the item
    if (q) rows = rows.filter(([name, it]) =>
      name.includes(q) ||
      Object.values(it.names ?? {}).some((n) => n.toLowerCase().includes(q)));
    return rows
      .sort((a, b) =>
        (RANK[a[1].rarity] ?? 9) - (RANK[b[1].rarity] ?? 9) ||
        (b[1].tier ?? 0) - (a[1].tier ?? 0) ||
        a[0].localeCompare(b[0]))
      .slice(0, 400);
  });

  const t = $derived(talk(lang, data.words));
  const cls = (r) => 'r-' + String(r ?? 'common').toLowerCase();
  const tier = (item) => data.tiers[(item?.tier ?? 1) - 1] ?? '?';

  // The act boss that stands here, if one does. Pinning a zone must not lose
  // it: the marker is where it was put, and this panel is what the marker is
  // for once the pointer has gone somewhere else.
  const BOX = 76;
  const boss = $derived(active?.boss ? data.bosses[active.boss] : null);
  const face = $derived(boss?.icon ?? null);
  const scale = $derived(face ? Math.min(1, BOX / Math.max(face[2], face[3])) : 1);

  /** Hovering a row shows its card; there is nothing here to click. */
  const show = (name) => (e) =>
    (peek = { name, top: e.currentTarget.getBoundingClientRect().top });
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<aside class:open={panel} onpointerleave={() => (peek = null)}>
  {#if active}
    <!-- the zone that was clicked, so it can be read without the pointer -->
    <section class="zone">
      <header>
        <h2>{nameOf(active, lang)}</h2>
        <button class="x" aria-label={t('Let it go')} onclick={() => (active = null)}>×</button>
      </header>
      <p class="sub">
        {[t(KIND[active.kind]), active.act ? `${t('act')} ${active.act}` : null, active.code]
          .filter(Boolean).join(' · ')}
      </p>

      {#if boss}
        <div class="boss">
          {#if face}
            <span
              class="facebox"
              style="width: {Math.round(face[2] * scale)}px; height: {Math.round(face[3] * scale)}px"
            >
              <span
                class="face"
                style="
                  width: {face[2]}px; height: {face[3]}px;
                  transform: scale({scale});
                  background-image: url({asset('img/bosses.webp')});
                  background-position: {-face[0]}px {-face[1]}px;
                  background-size: {data.bossSheet.w}px {data.bossSheet.h}px;
                "
              ></span>
            </span>
          {/if}
          <div class="who">
            <h3>{called(data.bosses[active.boss], active.boss, lang)}</h3>
            <ul class="rows">
              {#each boss.drops as d (d.item)}
                {@const item = data.items[d.item] ?? {}}
                <li class:lit={peek?.name === d.item} onpointerenter={show(d.item)}>
                  <ItemIcon {item} sheet={data.sheet} />
                  <span class="name {cls(item.rarity)}">{called(item, d.item, lang)}</span>
                  {#if d.inferno}<span class="inferno">INF</span>{/if}
                </li>
              {/each}
            </ul>
          </div>
        </div>
      {/if}

      {#if active.drops.length === 0}
        <p class="note">
          {t(boss
            ? 'Nothing else drops here.'
            : active.kind === 'town' ? 'Nothing drops in a town.' : 'The tables tie nothing to this zone.')}
        </p>
      {:else}
        <ul class="rows">
          {#each active.drops as name (name)}
            {@const item = data.items[name] ?? {}}
            <li class:lit={peek?.name === name} onpointerenter={show(name)}>
              <ItemIcon {item} sheet={data.sheet} />
              <span class="name {cls(item.rarity)}">{called(item, name, lang)}</span>
              {#if item.inferno}<span class="inferno">INF</span>{/if}
              <span class="odds">{odds(item.chase ?? item.rate)}</span>
            </li>
          {/each}
        </ul>
        <p class="foot">{t('the odds are for standing in this zone')}</p>
      {/if}
    </section>
  {/if}

  <div class="head">
    <input
      type="search"
      bind:value={query}
      placeholder={t('Find an item…')}
      autocomplete="off"
      spellcheck="false"
    >
    <div class="rarities">
      <button class:on={!rarity} onclick={() => (rarity = null)}>{t('all')}</button>
      {#each grades as r (r)}
        <button class={cls(r)} class:on={rarity === r} onclick={() => (rarity = rarity === r ? null : r)}>
          {t(r)}
        </button>
      {/each}
    </div>
  </div>

  <p class="count">
    <span>{found.length}{found.length === 400 ? '+' : ''} {t('items')}</span>
    <!-- The badge sits on rows all over this page and on the cards, and said
         what it meant only to a pointer that stopped on it. It says it here
         instead, once, beside the count — where the eye already goes to read
         how many things the search found. -->
    <span class="legend"><span class="inferno">INF</span> {t('only on Inferno')}</span>
  </p>
  <ul class="rows list">
    {#each found as [name, item] (name)}
      <li class:lit={peek?.name === name} onpointerenter={show(name)}>
        <ItemIcon {item} sheet={data.sheet} />
        <span class="tier">{tier(item)}</span>
        <span class="name {cls(item.rarity)}">{called(item, name, lang)}</span>
        {#if item.inferno}<span class="inferno">INF</span>{/if}
        <span class="odds">{odds(item.rate)}</span>
      </li>
    {/each}
    {#if found.length === 0}<li class="note">Nothing by that name.</li>{/if}
  </ul>
</aside>

<style>
  /* the boss that stands in this zone: its face beside its own short list */
  .boss {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 0 0 8px;
    margin: 0 0 8px;
    border-bottom: 1px solid #ffffff14;
  }
  .facebox { flex: none; position: relative; }
  .face {
    position: absolute;
    top: 0;
    left: 0;
    transform-origin: top left;
    background-repeat: no-repeat;
    image-rendering: pixelated;
  }
  .who { flex: 1; min-width: 0; }
  .who h3 {
    margin: 0 0 3px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .4px;
    text-transform: uppercase;
    color: var(--hot);
  }

  aside {
    flex: 0 0 22rem;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: #16101a;
    border-left: 1px solid var(--edge);
  }

  /* ── the clicked zone ─────────────────────────────────────────────────── */
  .zone {
    flex: 0 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 8px 10px 10px;
    border-bottom: 1px solid var(--edge);
    background: #1a121f;
  }
  .zone header { display: flex; align-items: baseline; gap: 8px; }
  .zone h2 { flex: 1; margin: 0; font-size: 16px; font-weight: 600; color: var(--ink); }
  .x {
    background: none; border: 0; padding: 0 2px;
    color: var(--dim); font: inherit; font-size: 18px; line-height: 1; cursor: pointer;
  }
  .x:hover { color: var(--hot); }
  .sub { margin: 1px 0 7px; color: var(--dim); font-size: 11px; }
  .zone .rows { overflow-y: auto; }
  .foot { margin: 6px 0 0; color: var(--dim); font-size: 11px; font-style: italic; }

  /* ── search ───────────────────────────────────────────────────────────── */
  .head { padding: 9px 10px 8px; }

  input {
    width: 100%;
    padding: 6px 9px;
    color: var(--ink);
    background: rgba(10, 6, 12, .8);
    border: 1px solid var(--edge);
    border-radius: 6px;
    font: inherit;
    font-size: 13px;
  }
  input:focus { outline: none; border-color: var(--hot); }
  input::placeholder { color: var(--dim); }

  .rarities { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 7px; }
  .rarities button {
    background: none;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 0 5px;
    font: inherit;
    font-size: 11px;
    color: var(--dim);
    cursor: pointer;
  }
  .rarities button.on { border-color: currentColor; background: #ffffff0f; }
  .rarities button:hover { background: #ffffff14; }

  .count {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin: 2px 10px 3px;
    color: var(--dim);
    font-size: 11px;
  }
  .legend { display: inline-flex; align-items: center; gap: 4px; }

  /* ── lists ────────────────────────────────────────────────────────────── */
  .rows { margin: 0; padding: 0; list-style: none; }
  .list { flex: 1; overflow-y: auto; padding: 0 4px 8px; }

  .rows li {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 13px;
    cursor: default;
  }
  .rows li:hover, .rows li.lit { background: #ffffff12; }
  .name { flex: 1; }
  .odds { flex: none; color: var(--dim); font-size: 12px; font-variant-numeric: tabular-nums; }

  .tier {
    flex: none;
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
    flex: none;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .5px;
    color: #ffd0a0;
    background: #7a2410;
    border-radius: 3px;
    padding: 0 4px;
  }

  .note { margin: 6px 8px; color: var(--dim); font-size: 12px; font-style: italic; }

  .r-satanic { color: var(--rar-satanic); }
  .r-heroic { color: var(--rar-heroic); }
  .r-set { color: var(--rar-set); }
  .r-angelic { color: var(--rar-angelic); }
  .r-unholy { color: var(--rar-unholy); }
  .r-runeword { color: var(--rar-runeword); }
  .r-common { color: var(--rar-common); }

  @media (max-width: 900px) {
    aside { flex-basis: 17rem; }
  }

  /* A drawer rather than a column: below this the map has no room to spare, and
     a panel that cannot be folded away leaves it a strip. It slides rather than
     appearing, so it is plain that the map is still underneath. */
  @media (max-width: 46rem) {
    aside {
      position: absolute;
      inset: 0 0 0 auto;
      z-index: 30;
      width: min(90vw, 22rem);
      flex-basis: auto;
      transform: translateX(100%);
      transition: transform .18s ease-out;
      box-shadow: -12px 0 30px #0008;
    }
    aside.open { transform: none; }
  }

  @media (max-width: 46rem) and (prefers-reduced-motion: reduce) {
    aside { transition: none; }
  }
</style>
