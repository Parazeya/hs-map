<script>
  import { asset, called, odds, titleCase } from './lib/map.js';
  import { talk } from './lib/say.js';
  import ItemIcon from './ItemIcon.svelte';

  let { data, title, subtitle, rows, at, foot = null, boss = null, lang = 'en' } = $props();

  const t = $derived(talk(lang, data.words));

  // The boss's own drops are not the zone's. An act boss stands at the end of
  // its act, in this dungeon, and what it gives up it gives up for killing it —
  // not for standing here. So it gets its own block rather than a few more rows
  // in a list whose footnote would then be wrong about half of them.
  const BOX = 84;
  const face = $derived(boss ? data.bosses[boss]?.icon : null);
  const scale = $derived(face ? Math.min(1, BOX / Math.max(face[2], face[3])) : 1);

  const GAP = 18;
  const EDGE = 10;

  let box = $state(null);
  let size = $state(null);

  // Measured, not guessed. It used to start from an assumed size, be placed on
  // that, and jump once the real one was known — which is what made it appear
  // in one spot and settle in another. It stays invisible until it has been
  // measured, so the first frame anyone sees is the right one.
  $effect(() => {
    // read the list so a change of content re-measures
    shown.length;
    boss;
    if (box) size = { w: box.offsetWidth, h: box.offsetHeight };
  });

  /**
   * As many rows as the window can hold, and a line saying what was left out.
   *
   * The panel cannot scroll — it is pointer-transparent by design — so a list
   * longer than the window used to be cut off mid-row with nothing to say so.
   */
  const ROW = 25, CHROME = 74;
  const cap = $derived(Math.max(4, Math.floor((innerHeight * 0.78 - CHROME) / ROW)));
  const shown = $derived(rows.slice(0, cap));
  const hidden = $derived(rows.length - shown.length);

  const place = $derived.by(() => {
    if (!size) return null;
    const x = at.x + GAP + size.w > innerWidth - EDGE
      ? Math.max(EDGE, at.x - GAP - size.w)
      : at.x + GAP;
    // below the cursor by choice, above it when there is no room below
    const y = at.y + GAP + size.h > innerHeight - EDGE
      ? Math.max(EDGE, at.y - GAP - size.h)
      : at.y + GAP;
    return { x, y };
  });
</script>

<div
  class="tip"
  class:ready={place}
  bind:this={box}
  style="left: {place?.x ?? 0}px; top: {place?.y ?? 0}px"
>
  <h2>{title}</h2>
  <p class="where">{subtitle}</p>

  {#if boss}
    {@const b = data.bosses[boss]}
    <div class="boss">
      <!-- The box is the drawn size and the sprite inside it is the real one,
           scaled. A transform does not change what an element reserves in the
           flow, so a 300px portrait shrunk to 84 would still have pushed the
           list 300px to the right. -->
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
        <h3>{called(data.bosses[boss], boss, lang)}</h3>
        <ul class="his">
          {#each b.drops as d (d.item)}
            {@const it = data.items[d.item] ?? {}}
            <li>
              <ItemIcon item={it} sheet={data.sheet} box={20} />
              <span class="tier">{data.tiers[(it.tier ?? 1) - 1] ?? '?'}</span>
              <span class="name r-{String(it.rarity ?? 'common').toLowerCase()}">{called(it, d.item, lang)}</span>
              {#if d.inferno}<span class="inferno" title={t('only on Inferno')}>INF</span>{/if}
            </li>
          {/each}
        </ul>
      </div>
    </div>
  {/if}

  {#if rows.length === 0}
    <p class="empty">{t(boss ? 'Nothing else drops here.' : 'Nothing is tied to this.')}</p>
  {:else}
    <ul>
      {#each shown as row (row.name)}
        {@const it = data.items[row.name] ?? {}}
        <li>
          <ItemIcon item={it} sheet={data.sheet} box={20} />
          <span class="tier">{data.tiers[(it.tier ?? 1) - 1] ?? '?'}</span>
          <span class="name r-{String(it.rarity ?? 'common').toLowerCase()}">{called(it, row.name, lang)}</span>
          {#if row.inferno}<span class="inferno" title={t('only on Inferno')}>INF</span>{/if}
          <span class="odds">{odds(row.odds)}</span>
        </li>
      {/each}
    </ul>
    {#if hidden > 0}<p class="foot">…{t('and')} {hidden} {t('more')}</p>{/if}
    {#if foot}<p class="foot">{foot}</p>{/if}
  {/if}

</div>

<style>
  .tip {
    position: fixed;
    z-index: 20;
    width: max-content;
    max-width: 26rem;
    max-height: 78vh;
    overflow: hidden;
    opacity: 0;
    padding: 10px 12px 11px;
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 9px;
    box-shadow: 0 10px 40px #000a;
    /* it follows the cursor; it must never be what the cursor is over */
    pointer-events: none;
  }
  .tip.ready { opacity: 1; }

  h2 { margin: 0; font-size: 15px; font-weight: 600; }
  .where { margin: 1px 0 8px; color: var(--dim); font-size: 11px; }
  .empty { margin: 0; color: var(--dim); font-style: italic; font-size: 13px; }
  .foot { margin: 8px 0 0; color: var(--dim); font-size: 11px; font-style: italic; }

  /* the boss block: its face beside its own short list */
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
  .who { min-width: 0; flex: 1; }
  h3 {
    margin: 0 0 3px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .4px;
    text-transform: uppercase;
    color: var(--hot);
  }

  ul { margin: 0; padding: 0; list-style: none; }
  li {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 2px 0;
    border-top: 1px solid #ffffff10;
    white-space: nowrap;
  }
  li:first-child { border-top: 0; }

  /* A name long enough to push the odds past the panel's edge loses its tail
     instead: the box is clipped, so what was pushed out was simply gone. The
     dungeon lists are where it showed — "Покрытые Шрамами Боевые Дротики" is
     wider than the panel on its own. */
  .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .tier {
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
  .inferno {
    flex: none;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .5px;
    color: #ffd0a0;
    background: #7a2410;
    border-radius: 3px;
    padding: 1px 4px;
  }
  .odds { flex: none; color: var(--dim); font-size: 12px; font-variant-numeric: tabular-nums; }

  .r-satanic { color: var(--rar-satanic); }
  .r-heroic { color: var(--rar-heroic); }
  .r-set { color: var(--rar-set); }
  .r-angelic { color: var(--rar-angelic); }
  .r-unholy { color: var(--rar-unholy); }
  .r-runeword { color: var(--rar-runeword); }
  .r-common { color: var(--rar-common); }
</style>
