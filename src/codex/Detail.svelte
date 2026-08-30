<script>
  import { odds, titleCase } from '../lib/map.js';
  import { places } from '../lib/say.js';
  import ItemIcon from '../ItemIcon.svelte';

  let { data, item, lang, sheet, t = (s) => s, pick = null } = $props();

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
   * A stat as the game names it, or as this project reads it off the identifier.
   *
   * 212 of the 322 are the game's own — see words.Words.stats for how the two
   * are joined — which is nine in ten of the lines anyone actually meets.
   */
  const place = $derived(places(lang, data?.words));

  /**
   * The Unholy slots, grouped by the pool each rolls from.
   *
   * An Unholy item does not carry these modifiers, it carries a slot: the game
   * rolls one when the item drops, so the honest thing to show is what the
   * slot can become. Three slots reading the same pool are one line and one
   * list, not three of each.
   */
  // Held against the item and not as a plain flag, so opening one item's list
  // does not leave the next item's already open.
  let openFor = $state(null);
  const showPool = $derived(openFor != null && openFor === item?.key);
  const unholy = $derived.by(() => {
    const slots = (item?.stats ?? []).filter((v) => v.sid === 'unholy_none');
    if (!slots.length || !data?.unholy) return [];
    const by = new Map();
    for (const v of slots) {
      const sel = String(v.pool ?? '');
      by.set(sel, (by.get(sel) ?? 0) + 1);
    }
    return [...by].map(([sel, n]) => {
      const from = data.unholy.selects[sel] ?? [];
      const rolls = from.flatMap((k) => data.unholy.pools[String(k)]?.rolls ?? []);
      return { sel, n, rolls };
    });
  });
  /**
   * A modifier's name, or the five an elemental roll chooses between.
   *
   * Written down the middle rather than five times over: the five differ by one
   * word and share the rest, so "Ignore Arcane Resistance · Ignore Cold
   * Resistance · …" is the same sentence four times too many. The words they
   * agree on at each end are kept once and the elements listed between them,
   * which works in every language because it is measured off the names
   * themselves and not off a rule about where the element goes.
   */
  function middle(names) {
    const words = names.map((n) => n.split(' '));
    const short = Math.min(...words.map((w) => w.length));
    let head = 0;
    while (head < short - 1 && words.every((w) => w[head] === words[0][head])) head++;
    let tail = 0;
    while (
      tail < short - head - 1 &&
      words.every((w) => w[w.length - 1 - tail] === words[0][words[0].length - 1 - tail])
    ) tail++;
    const between = words.map((w) => w.slice(head, w.length - tail).join(' ')).join(' / ');
    return [words[0].slice(0, head).join(' '), between, words[0].slice(words[0].length - tail).join(' ')]
      .filter(Boolean)
      .join(' ');
  }
  const rolled = $derived((r) => {
    const names = (r.elements ?? [r]).map((e) => e.said?.[lang] || e.said?.en || e.name);
    return names.length > 1 ? middle(names) : names[0];
  });
  const byStat = $derived(Object.fromEntries((data?.stats ?? []).map((v) => [v.sid, v])));
  const said = $derived((s) => byStat[s.sid]?.names?.[lang] || s.text);

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
    <p class="idle">{t('Pick something on the left.')}</p>
  {:else}
    <header>
      <ItemIcon {item} sheet={data.sheet} from={sheet} box={64} />
      <div class="who">
        <h1 class={cls(item.rarity)}>{name}</h1>
        <p class="sub">
          {[t(item.rarity), t(item.type), item.tier].filter(Boolean).join(' · ')}
        </p>
      </div>
    </header>

    <dl class="facts">
      {#if item.base}<dt>{t('Made in')}</dt><dd>{t(item.base)}</dd>{/if}
      {#if item.weapons?.length}
        <dt>{t('Weapons')}</dt><dd>{item.weapons.map(t).join(', ')}</dd>
      {/if}
      {#if item.lvl}<dt>{t('Level')}</dt><dd>{item.lvl}</dd>{/if}
      {#if item.size}<dt>{t('Space')}</dt><dd>{item.size[0]}×{item.size[1]}</dd>{/if}
      {#if item.rate}<dt>{t('Drop rate')}</dt><dd>{odds(item.rate)}</dd>{/if}
      {#if item.chase && item.chase !== item.rate}
        <dt>{t('In its zone')}</dt>
        <dd>{odds(item.chase)}</dd>
      {/if}
    </dl>

    {#if recipe.length}
      <h2>{t('Runes, in this order')}</h2>
      <ol class="recipe">
        {#each recipe as s, i (i)}
          <li>
            <button
              class="rune"
              disabled={!s.key}
              aria-label={s.of ? (s.of.names?.[lang] || s.of.name) : s.name}
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
      <h2>{t(item.more?.length ? 'Stats, as it comes' : 'Stats')}</h2>
      <ul class="stats">
        {#each item.stats.filter((v) => v.sid !== 'unholy_none') as s, i (s.sid + i)}
          <li>
            <span class="v">{span(s.min, s.max, s.unit ?? '')}</span>
            <span class="t">
              {said(s)}{#if s.spell}: {s.spell}{/if}{#if s.cls && s.cls !== 'Any'} ({s.cls}){/if}
              {#if s.min2 != null || s.max2 != null}
                <span class="second">at {span(s.min2, s.max2)}</span>
              {/if}
              {#if s.range}<span class="second">range {s.range}</span>{/if}
            </span>
          </li>
        {/each}
      </ul>
    {/if}

    {#each unholy as g (g.sel)}
      <h2>{t('Unholy')}</h2>
      <p class="rolls">
        {g.n} × {t('rolled when the item drops')} — {t('one of')} {g.rolls.length}
      </p>
      <button class="more" onclick={() => (openFor = showPool ? null : item.key)}>
        {showPool ? t('Hide') : t('Show')}
      </button>
      {#if showPool}
        <ul class="stats pool">
          {#each g.rolls as r, i (i)}
            <li>
              <span class="v">{span(r.min, r.max)}</span>
              <span class="t">
                {rolled(r)}
                {#if r.elements}<span class="second">{t('one element of the five')}</span>{/if}
              </span>
            </li>
          {/each}
        </ul>
      {/if}
    {/each}

    {#each item.more ?? [] as v (v.when)}
      <h2>{t('Stats')}, {v.when.startsWith('with a ')
        ? `${t('with a')} ${v.when.slice(7)}` : t(v.when)}</h2>
      <ul class="stats">
        {#each v.stats as s, i (s.sid + i)}
          <li>
            <span class="v">{span(s.min, s.max, s.unit ?? '')}</span>
            <span class="t">
              {said(s)}{#if s.spell}: {s.spell}{/if}{#if s.cls && s.cls !== 'Any'} ({s.cls}){/if}
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
              <span class="k">{t(p.of.type ?? '')}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if item.places?.length}
      <h2>{t('Drop location')}</h2>
      <ul class="places">
        {#each item.places as p (p)}<li>{place(titleCase(p))}</li>{/each}
      </ul>
    {/if}

    {#if lore}
      <h2>{t('Lore')}</h2>
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

  /* What an Unholy slot can roll. Folded away by default because a slot that
     draws from all three pools offers 57 lines, which would bury the stats the
     item actually carries. */
  .rolls { margin: 0 0 6px; color: var(--dim); font-size: 12px; line-height: 1.4; }
  .more {
    padding: 3px 9px;
    color: inherit;
    font: inherit;
    font-size: 12px;
    background: none;
    border: 1px solid var(--edge);
    border-radius: 7px;
    cursor: pointer;
  }
  .more:hover { background: #ffffff10; }
  .stats.pool { margin-top: 8px; }
  .stats.pool .second { display: block; font-size: 11px; }

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
