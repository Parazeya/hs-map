<script>
  import { odds, titleCase } from '../lib/map.js';
  import ItemIcon from '../ItemIcon.svelte';

  let { data, item, lang, sheet, pick = null } = $props();

  /** A runeword's recipe, each socket resolved to the thing that goes in it. */
  const recipe = $derived(
    (item?.sockets ?? []).map((s) => ({ ...s, of: s.key ? data.items[s.key] : null })),
  );

  /** The set this belongs to, and the other pieces of it. */
  const kit = $derived(item?.set ? data.sets[item.set] : null);
  const kitName = $derived(kit?.names?.[lang] || item?.set || '');
  const pieces = $derived(
    (kit?.of ?? []).map((k) => ({ key: k, of: data.items[k] })).filter((p) => p.of),
  );

  const name = $derived(item ? (item.names?.[lang] || item.name) : '');
  const lore = $derived(item ? (item.lore?.[lang] || item.lore?.en || null) : null);
  const cls = (r) => 'r-' + String(r ?? 'common').toLowerCase().replace(/\s+/g, '-');

  /**
   * One stat as a line: its range, then what it is.
   *
   * A range with the same number at both ends is not a range, it is a number,
   * and writing "20 to 20" of it makes a reader stop and check.
   */
  function span(lo, hi, unit = '') {
    if (lo == null && hi == null) return '';
    if (hi == null || hi === lo) return `${lo}${unit}`;
    if (lo == null) return `${hi}${unit}`;
    return `${lo}–${hi}${unit}`;
  }
</script>

<section class="panel">
  {#if !item}
    <p class="idle">Pick something on the left.</p>
  {:else}
    <header>
      <ItemIcon {item} sheet={data.sheet} from={sheet} box={64} />
      <div class="who">
        <h1 class={cls(item.rarity)}>{name}</h1>
        <p class="sub">
          {[item.rarity, item.type, item.tier && `tier ${item.tier}`]
            .filter(Boolean).join(' · ')}
        </p>
      </div>
    </header>

    <dl class="facts">
      {#if item.base}<dt>Made in</dt><dd>{item.base}</dd>{/if}
      {#if item.weapons?.length}<dt>Weapons</dt><dd>{item.weapons.join(', ')}</dd>{/if}
      {#if item.lvl}<dt>Level</dt><dd>{item.lvl}</dd>{/if}
      {#if item.size}<dt>Space</dt><dd>{item.size[0]}×{item.size[1]}</dd>{/if}
      {#if item.rate}<dt>Drop rate</dt><dd>{odds(item.rate)}</dd>{/if}
      {#if item.chase && item.chase !== item.rate}
        <dt title="the odds while standing in a zone it drops in">In its zone</dt>
        <dd>{odds(item.chase)}</dd>
      {/if}
    </dl>

    {#if recipe.length}
      <h2>Runes, in this order</h2>
      <ol class="recipe">
        {#each recipe as s, i (i)}
          <li>
            <button
              class="rune"
              disabled={!s.key}
              title={s.of ? (s.of.names?.[lang] || s.of.name) : s.name}
              onclick={() => s.key && pick?.(s.key)}
            >
              <ItemIcon item={s.of} sheet={data.sheet} from={sheet} box={34} />
              <span class="n">{s.name}</span>
            </button>
          </li>
        {/each}
      </ol>
    {/if}

    {#if item.stats?.length}
      <h2>{item.more?.length ? 'Stats, as it comes' : 'Stats'}</h2>
      <ul class="stats">
        {#each item.stats as s, i (s.sid + i)}
          <li>
            <span class="v">{span(s.min, s.max, s.unit ?? '')}</span>
            <span class="t">
              {s.text}{#if s.spell}: {s.spell}{/if}{#if s.cls && s.cls !== 'Any'} ({s.cls}){/if}
              {#if s.min2 != null || s.max2 != null}
                <span class="second">at {span(s.min2, s.max2)}</span>
              {/if}
              {#if s.range}<span class="second">range {s.range}</span>{/if}
            </span>
          </li>
        {/each}
      </ul>
    {/if}

    {#each item.more ?? [] as v (v.when)}
      <h2>Stats, {v.when}</h2>
      <ul class="stats">
        {#each v.stats as s, i (s.sid + i)}
          <li>
            <span class="v">{span(s.min, s.max, s.unit ?? '')}</span>
            <span class="t">
              {s.text}{#if s.spell}: {s.spell}{/if}{#if s.cls && s.cls !== 'Any'} ({s.cls}){/if}
              {#if s.min2 != null || s.max2 != null}
                <span class="second">at {span(s.min2, s.max2)}</span>
              {/if}
            </span>
          </li>
        {/each}
      </ul>
    {/each}

    {#if pieces.length}
      <h2>{kitName}</h2>
      <ul class="pieces">
        {#each pieces as p (p.key)}
          <li>
            <button class:self={p.key === item.key} onclick={() => pick?.(p.key)}>
              <ItemIcon item={p.of} sheet={data.sheet} from={sheet} box={26} />
              <span class="n {cls(p.of.rarity)}">{p.of.names?.[lang] || p.of.name}</span>
              <span class="k">{p.of.type ?? ''}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if item.places?.length}
      <h2>Drop location</h2>
      <ul class="places">
        {#each item.places as p (p)}<li>{titleCase(p)}</li>{/each}
      </ul>
    {/if}

    {#if lore}
      <h2>Lore</h2>
      <p class="lore">{lore}</p>
    {/if}

    <p class="key">{item.key}</p>
  {/if}
</section>

<style>
  .panel {
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 12px 14px 28px;
    border-left: 1px solid var(--edge);
  }
  .idle { color: var(--dim); font-style: italic; }

  header { display: flex; gap: 12px; align-items: flex-start; }
  .who { min-width: 0; }
  h1 { margin: 0; font-size: 19px; line-height: 1.2; }
  .sub { margin: 3px 0 0; color: var(--dim); font-size: 12px; }

  h2 {
    margin: 18px 0 6px;
    color: var(--dim);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .8px;
    text-transform: uppercase;
  }

  .facts {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 10px;
    margin: 12px 0 0;
    font-size: 13px;
  }
  .facts dt { color: var(--dim); }
  .facts dd { margin: 0; font-variant-numeric: tabular-nums; }

  ul { margin: 0; padding: 0; list-style: none; }
  .stats li {
    display: flex;
    gap: 8px;
    padding: 2px 0;
    border-top: 1px solid #ffffff10;
    font-size: 13px;
    line-height: 1.35;
  }
  .stats li:first-child { border-top: 0; }
  .stats .v {
    flex: none;
    min-width: 4.2rem;
    color: var(--hot);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .stats .t { flex: 1; min-width: 0; }
  .second { color: var(--dim); }

  /* The recipe reads left to right, because the order matters: the same runes
     in another order are another runeword, or none. */
  .recipe {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 0;
    padding: 0;
    list-style: none;
    counter-reset: socket;
  }
  .rune {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1px;
    width: 46px;
    padding: 3px 1px 2px;
    color: inherit;
    font: inherit;
    background: none;
    border: 1px solid var(--edge);
    border-radius: 7px;
    cursor: pointer;
  }
  .rune:hover:not(:disabled) { border-color: var(--hot); background: #ffffff10; }
  .rune:disabled { cursor: default; opacity: .6; }
  .rune .n { font-size: 11px; color: var(--dim); }

  /* the rest of the set, so a piece is never read on its own */
  .pieces { display: flex; flex-direction: column; gap: 2px; }
  .pieces button {
    width: 100%;
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 2px 6px;
    color: inherit;
    font: inherit;
    text-align: left;
    background: none;
    border: 1px solid transparent;
    border-radius: 6px;
    cursor: pointer;
  }
  .pieces button:hover { background: #ffffff0c; border-color: var(--edge); }
  .pieces button.self { border-color: var(--hot); }
  .pieces .n { flex: 1; min-width: 0; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pieces .k { flex: none; color: var(--dim); font-size: 11px; }

  .places li { padding: 1px 0; font-size: 13px; }
  .lore { margin: 0; color: var(--dim); font-size: 13px; line-height: 1.45; font-style: italic; }
  .key {
    margin: 22px 0 0;
    color: var(--dim);
    opacity: .5;
    font-size: 11px;
    font-family: ui-monospace, monospace;
  }
</style>
