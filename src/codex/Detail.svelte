<script>
  import { asset, figure, odds, titleCase, withMF } from '../lib/map.js';
  import { mf } from '../lib/mf.svelte.js';
  import { places } from '../lib/say.js';
  import { formatStatRange as statSpan, formatStatValue } from '../lib/stat-value.js';
  import { visibleItemStats, itemGrantGroups } from '../lib/grant-stats.js';
  import { conditionModeKey, conditionRecordKey, isPreviewCondition, conditionChoices, selectedConditionModes, conditionName } from '../lib/item-conditions.js';
  import ItemIcon from '../ItemIcon.svelte';

  let { data, item: selection, lang, sheet, t = (s) => s, pick = null } = $props();
  let variant = $state(0);
  const records = $derived(selection ? [selection, ...(selection.variants ?? [])] : []);
  const item = $derived(records[variant] ?? selection);
  let conditionSelections = $state({});
  const conditionScope = $derived(conditionRecordKey(item, variant));
  const choices = $derived(conditionChoices(item?.more ?? []));
  const modes = $derived(selectedConditionModes(item?.more ?? [], conditionSelections));
  const plainModes = $derived(modes.filter(mode => !isPreviewCondition(mode)));
  const conditionalModes = $derived(modes.filter(isPreviewCondition));
  $effect(() => {
    conditionScope;
    conditionSelections = {};
  });
  $effect(() => {
    selection?.key;
    variant = 0;
  });

  /** A runeword's recipe, each socket resolved to the thing that goes in it. */
  const recipe = $derived(
    (item?.sockets ?? []).map((s) => ({ ...s, of: s.key ? data.items[s.key] : null })),
  );

  /**
   * What asks for this one.
   *
   * A rune's card said what the rune does and nothing about the hundred
   * runewords that call for it, which is the question anyone holding a rune
   * actually has. Read off the recipes rather than written down.
   */
  const wanted = $derived.by(() => {
    if (!item?.key || !item.key.startsWith('socketable')) return [];
    return Object.entries(data?.items ?? {})
      .filter(([, r]) => (r.sockets ?? []).some((k) => k.key === item.key))
      .map(([key, r]) => ({ key, of: r }));
  });

  /** The set this belongs to, and the other pieces of it. */
  const kit = $derived(item?.set ? data.sets[item.set] : null);
  const kitName = $derived(kit?.names?.[lang] || item?.set || '');
  const pieces = $derived(
    (kit?.of ?? []).map((k) => ({ key: k, of: data.items[k] })).filter((p) => p.of),
  );

  /** The classes this item's stats are built for, and what pointed at them. */
  const suits = $derived(
    (item?.suits ?? []).map((s) => ({
      name: data.classes?.find((c) => c.id === s.c)?.names?.[lang] || s.c,
      why: (s.why ?? []).map((w) => data.about?.[w]?.[lang] || data.about?.[w]?.en || w),
    })),
  );

  const name = $derived(item ? (item.names?.[lang] || item.name) : '');

  /// Where the map would open for this item, or nothing for something that
  /// drops nowhere the map draws.
  ///
  /// The map keys its items by the lowercased English name and takes the name
  /// in `find`. Anything with a place or a drop rate is worth offering: of the
  /// 1140 that pass, the map knows 1129, and it knows nothing this refuses.
  /// `asset` already puts a query on the path, so the second one is joined.
  const onMap = $derived.by(() => {
    if (!item?.name || !(item.places?.length || item.rate != null)) return null;
    const at = asset('index.html');
    return `${at}${at.includes('?') ? '&' : '?'}find=${encodeURIComponent(item.name.toLowerCase())}`;
  });
  const lore = $derived(item ? (item.lore?.[lang] || item.lore?.en || null) : null);

  /** One of the game's phrases, in the reader's language. */
  const word = (o) => o?.[lang] || o?.en || '';
  const statValue = s => s.value_names ? word(s.value_names)
    : formatStatValue(s.unit_names ? { ...s, unit: ' ' + word(s.unit_names) } : s);

  /**
   * What a potion grants, which is a talent and not a stat.
   *
   * Native talent references use source-bound map insertion keys. The backend
   * consumes only statements represented by a proved grant. Unpaired level
   * operands and unresolved talent references remain in the stat list, even
   * when another grant supplies a description on the same card.
   */
  const grantGroups = $derived([
    ...itemGrantGroups(item),
    ...plainModes.flatMap(mode => itemGrantGroups(mode).map(group => ({ ...group, mode }))),
  ]);
  const modeLabel = mode => conditionName(mode, lang, t);
  const dropPlaces = $derived([...new Set([
    ...(item?.places ?? []).map(titleCase),
    ...(item?.reference_places ?? []).map(source => source.name),
  ])]);
  const shown = $derived(visibleItemStats(item));
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
  const unholy = $derived([
    ...rollGroups(item),
    ...plainModes.flatMap(mode => rollGroups(mode, mode)),
  ]);
  function rollGroups(record, mode = null) {
    const slots = (record?.stats ?? []).filter(s => s.sid === 'unholy_none' && s.active !== false);
    if (!slots.length) return [];
    const by = new Map();
    for (const s of slots) {
      const sel = String(s.pool ?? '');
      by.set(sel, (by.get(sel) ?? 0) + 1);
    }
    return [...by].map(([sel, n]) => {
      const from = data?.unholy?.selects?.[sel] ?? [];
      const rolls = from.flatMap((k) => data?.unholy?.pools?.[String(k)]?.rolls ?? []);
      return { id: `${mode ? conditionModeKey(mode) : 'base'}:${sel}`, sel, mode, n, rolls };
    });
  }
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
  const said = $derived((s) => byStat[s.sid]?.names?.[lang] || t(s.text));

</script>

{#snippet statList(rows, owner)}
  <ul class="stats">
    {#each rows as s, i (s.sid + i)}
      <li>
        <span class="v">{statValue(s)}</span>
        <span class="t">
          {said(s)}{#if s.spell}: {s.spell}{/if}{#if s.cls && s.cls !== 'Any'}{' (' + s.cls + ')'}{/if}
          {#if word(s.class_names)}<span class="second"> ({t('Class only')}: {word(s.class_names)})</span>{/if}
          {#if word(s.effect_note)}<span class="second"> {word(s.effect_note)}</span>{/if}
          {#if s.min2 != null || s.max2 != null}<span class="second">at {statSpan(s.min2, s.max2)}</span>{/if}
          {#if s.outer_selector && owner?.condition?.resolved !== true}<span class="second">{t('Condition has not been identified.')}</span>{/if}
          {#if s.range}<span class="second">range {s.range}</span>{/if}
          {#if s.rank}<span class="second">{t('by relic level')}</span>{/if}
          {#if s.resource_references?.length}
            <details class="resource-references">
              <summary>{t('Zone references')} ({s.resource_references.length})</summary>
              <ul>
                {#each s.resource_references as reference, n (`${reference.payload_hex}:${n}`)}
                  <li>{reference.room?.name ?? reference.payload_hex}</li>
                {/each}
              </ul>
            </details>
          {/if}
        </span>
      </li>
    {/each}
  </ul>
{/snippet}

{#snippet grantBlocks(groups, owner, nested)}
  {#each groups as group, index (`${conditionModeKey(owner ?? group.mode, index)}:${group.title}`)}
    {@const mode = owner ?? group.mode}
    {#if nested}<h3>{t(group.title)}</h3>{:else}<h2>{t(group.title)}{#if mode}, {modeLabel(mode)}{/if}</h2>{/if}
    {#each group.grants as g, n (n)}
      <p class="grant">
        {#if g.kind === 'trigger'}
          <span class="chance">{g.chance_values?.length ? g.chance_values.map(v => v == null ? '?' : v).join(' / ') : g.chance ? statSpan(g.chance[0], g.chance[1]) : '?'}% {t('chance to cast')}</span>
        {/if}
        {#if g.level_values?.length}
          <span class="lvl">{#if g.kind === 'trigger'}{t('Level') + ' '}{/if}{g.level_values.map(value => value == null ? '?' : `${g.kind === 'trigger' ? '' : '+'}${value}`).join(' / ')} <span class="second">({t('by relic level')})</span></span>
        {:else if g.levels?.[0] != null || g.levels?.[1] != null}
          <span class="lvl">{['aura', 'trigger'].includes(g.kind) ? t('Level') + ' ' : '+'}{statSpan(g.levels[0], g.levels[1])}</span>
        {/if}
        <strong>{g.random_skill ? t('Random skill') : word(g.names)}</strong>
        {#if g.kind === 'subskills'}<span class="second"> · {t('Sub Skills')}</span>{/if}
        {#if word(g.class_names)}<span class="second"> ({t('Class only')}: {word(g.class_names)})</span>{/if}
        {#if g.kind === 'trigger'}<span class="second">{word(g.trigger)}</span>{/if}
        {#if g.outer_selector && mode?.condition?.resolved !== true}<span class="second">{t('Condition has not been identified.')}</span>{/if}
        {#if g.holder_only}<span class="second">({t('Holder Only')})</span>{/if}
        {#if g.lasts}<span class="second">{g.lasts} {t('seconds')}</span>{/if}
      </p>
      {#if g.options?.length}
        <details class="effect-options">
          <summary>{t('Possible effects')} ({g.options.length})</summary>
          <ul class="places">{#each g.options as option (option.native_id)}<li>{word(option.names)}</li>{/each}</ul>
        </details>
      {/if}
      <ul class="stats">
        {#each g.lines ?? [] as l, i (i)}
          <li>
            <span class="v">{l.start ?? '?'}{l.mark}{#if l.unit}{word(l.unit)}{/if}</span>
            <span class="t">
              {word(l.of)}
              {#if l.per != null && l.per !== 0}<span class="second">+{l.per}{l.mark}{#if l.unit}{word(l.unit)}{/if} {t('per level')}</span>{/if}
            </span>
          </li>
        {/each}
      </ul>
      {#if word(g.lore)}<p class="lore">{word(g.lore)}</p>{/if}
    {/each}
  {/each}
{/snippet}

{#snippet unholyBlocks(groups, nested)}
  {#each groups as g (g.id)}
    {#if nested}<h3>{t('Unholy')}</h3>{:else}<h2>{t('Unholy')}{#if g.mode}, {modeLabel(g.mode)}{/if}</h2>{/if}
    {#if !g.rolls.length}
      <p class="rolls">{g.n} × {t('Random modifiers')}</p>
    {:else}
      <p class="rolls">{g.n} × {t('Random modifiers')} — {t('one of')} {g.rolls.length}</p>
      <button class="more" onclick={() => (openFor = showPool ? null : item.key)}>{showPool ? t('Hide') : t('Show')}</button>
      {#if showPool}
        <ul class="stats pool">
          {#each g.rolls as r, i (i)}
            <li>
              <span class="v">{statSpan(r.min, r.max)}</span>
              <span class="t">{rolled(r)}{#if r.elements}<span class="second">{t('one element of the five')}</span>{/if}</span>
            </li>
          {/each}
        </ul>
      {/if}
    {/if}
  {/each}
{/snippet}

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

    {#if records.length > 1}
      <label class="variant">
        {t('Variant')}
        <select bind:value={variant}>
          {#each records as record, i (record.record_id ?? i)}
            <option value={i}>{`${t('Variant')} ${i + 1}`}{#if record.rarity || record.type || record.tier || record.lvl != null} · {[record.rarity ? t(record.rarity) : null, record.type ? t(record.type) : null, record.tier, record.lvl != null ? `${t('Level')} ${record.lvl}` : null].filter(Boolean).join(' · ')}{/if}</option>
          {/each}
        </select>
      </label>
    {/if}

    <dl class="facts">
      {#if item.base}<dt>{t('Made in')}</dt><dd>{t(item.base)}</dd>{/if}
      {#if item.weapons?.length}
        <dt>{t('Weapons')}</dt><dd>{item.weapons.map(t).join(', ')}</dd>
      {/if}
      {#if item.lvl}<dt>{t('Level')}</dt><dd>{item.lvl}</dd>{/if}
      {#if item.size}<dt>{t('Space')}</dt><dd>{item.size[0]}×{item.size[1]}</dd>{/if}
      <!-- and beside each, what it is for whoever is reading: the same figure
           divided by the magic find they gave the map. See mf.svelte.js. -->
      {#if item.rate}
        <dt>{t('Drop rate')}</dt>
        <dd>{odds(item.rate)}{#if mf.value > 0 && item.rate}<span class="mine">({figure(withMF(item.rate, mf.value))})</span>{/if}</dd>
      {/if}
      {#if item.chase && item.chase !== item.rate}
        <dt>{t('In its zone')}</dt>
        <dd>{odds(item.chase)}{#if mf.value > 0 && item.chase}<span class="mine">({figure(withMF(item.chase, mf.value))})</span>{/if}</dd>
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
              aria-label={s.of ? (s.of.names?.[lang] || s.of.name) : (s.name || `${t('Unidentified rune')} ${s.id}`)}
              onclick={() => s.key && pick?.(s.key)}
            >
              <ItemIcon item={s.of} sheet={data.sheet} from={sheet} box={34} />
              <span class="n">{s.of ? (s.of.names?.[lang] || s.of.name) : (s.name || `${t('Unidentified rune')} ${s.id}`)}</span>
            </button>
          </li>
        {/each}
      </ol>
    {/if}

    {#if choices.length}
      <div class="condition-controls">
        {#each choices as group (group.kind)}
          {@const selected = group.options.some(option => option.id === conditionSelections[group.kind]) ? conditionSelections[group.kind] : '*'}
          <label>
            <span>{t(group.label)}</span>
            <select aria-label={t(group.label)} value={selected}
              onchange={event => (conditionSelections = { ...conditionSelections, [group.kind]: event.currentTarget.value })}>
              <option value="*">{t('All variants')}</option>
              {#each group.options as option (option.id)}
                <option value={option.id}>{option.mode.condition?.names?.[lang] || option.mode.condition?.names?.en || modeLabel(option.mode)}</option>
              {/each}
            </select>
            {#if group.kind === 'socket' && group.options.some(option => option.mode.condition?.per_socket)}
              <small>{t('Bonuses per matching socket')}</small>
            {/if}
          </label>
        {/each}
      </div>
    {/if}

    {#if shown.length}
      <h2>{t(item.more?.length ? 'Stats, as it comes' : 'Stats')}</h2>
      {@render statList(shown, item)}
    {/if}

    {@render grantBlocks(grantGroups, null, false)}
    {@render unholyBlocks(unholy, false)}

    {#each conditionalModes as mode, index (conditionModeKey(mode, index))}
      <section class="condition-outcome" data-condition-id={conditionModeKey(mode, index)}>
        <h2>{modeLabel(mode)}</h2>
        {@render statList(visibleItemStats(mode), mode)}
        {@render grantBlocks(itemGrantGroups(mode), mode, true)}
        {@render unholyBlocks(rollGroups(mode, mode), true)}
      </section>
    {/each}

    {#each plainModes as mode, index (conditionModeKey(mode, index))}
      {#if visibleItemStats(mode).length}
        <h2>{t('Stats')}, {modeLabel(mode)}</h2>
        {@render statList(visibleItemStats(mode), mode)}
      {/if}
    {/each}

    {#if kit?.bonuses?.length}
      <h2>{kitName}</h2>
      <!-- What the set gives at each count of pieces worn. The wording is the
           game's own English; there is no translated table for it. -->
      <ul class="bonuses">
        {#each kit.bonuses as step (step.pieces)}
          <li>
            <span class="worn">{step.pieces}</span>
            <span class="gives">
              {#each step.lines as l, i (i)}<span class="line">{l.says}</span>{/each}
            </span>
          </li>
        {/each}
      </ul>
    {/if}

    {#if pieces.length}
      {#if !kit?.bonuses?.length}<h2>{kitName}</h2>{/if}
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

    {#if item.aura}
      <h2>{t('Suits')}</h2>
      <!-- An aura is worn for whoever is standing near it, so the item is not
           any one class's — and as often as not it is worn by a mercenary. -->
      <p class="anyone">{t('Any class — often carried by a mercenary.')}</p>
    {:else if suits.length}
      <h2>{t('Suits')}</h2>
      <!-- Nothing in the game says who an item is for. This is read off the
           stats: the classes whose skills and sub-skills are built out of what
           this item gives, and the part of it that says so. -->
      <ul class="suits">
        {#each suits as s (s.name)}
          <li>
            <span class="who">{s.name}</span>
            <span class="why">{s.why.join(' · ')}</span>
          </li>
        {/each}
      </ul>
    {/if}

    {#if wanted.length}
      <h2>{t('Asked for by')}</h2>
      <ul class="pieces">
        {#each wanted as w (w.key)}
          <li>
            <button onclick={() => pick?.(w.key)}>
              <ItemIcon item={w.of} sheet={data.sheet} from={sheet} box={26} />
              <span class="n {cls(w.of.rarity)}">{w.of.names?.[lang] || w.of.name}</span>
              <span class="k">{(w.of.sockets ?? []).map((x) => x.name).join(' · ')}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if dropPlaces.length}
      <h2>{t('Drop location')}</h2>
      <ul class="places">
        {#each dropPlaces as p (p)}<li>{place(p)}</li>{/each}
      </ul>
    {/if}

    <!-- The two pages knew the same item and had no way to say so: this one
         names the places, the map draws them. The link carries the name the map
         keys its items by, which is what its own search box takes. -->
    {#if onMap}
      <p class="tomap"><a href={onMap}>{t('Show it on the map')} ▶</a></p>
    {/if}

    {#if lore}
      <h2>{t('Lore')}</h2>
      <p class="lore">{lore}</p>
    {/if}

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
  .variant { display: flex; gap: 8px; align-items: center; margin: 12px 0; color: var(--dim); font-size: 12px; }
  .variant select { color: var(--ink); background: var(--ground, #180d13); border: 1px solid var(--edge); padding: 4px 7px; font: inherit; }
  .condition-controls { display: grid; gap: 9px; margin: 14px 0; }
  .condition-controls label { display: flex; flex-direction: column; gap: 4px; color: var(--dim); font-size: 12px; }
  .condition-controls select { width: 100%; min-width: 0; max-width: 100%; color: var(--ink); background: var(--ground, #180d13); border: 1px solid var(--edge); border-radius: 5px; padding: 6px 7px; font: inherit; }
  .condition-controls small { font-size: 11px; line-height: 1.35; }
  .condition-outcome { border-top: 1px solid var(--edge); margin-top: 16px; }
  .condition-outcome > h2 { margin-top: 12px; color: var(--hot); }
  h3 { margin: 12px 0 6px; color: var(--dim); font-size: 10px; font-weight: 700; letter-spacing: .6px; text-transform: uppercase; }

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
    max-width: 55%;
    overflow-wrap: anywhere;
    color: var(--hot);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .stats .t { flex: 1; min-width: 0; }
  .resource-references { margin-top: 4px; color: var(--dim); }
  .resource-references summary { cursor: pointer; }
  .resource-references ul { margin: 4px 0 0; max-height: 15rem; overflow-y: auto; }
  .resource-references ul li { display: block; border: 0; font-size: 12px; overflow-wrap: anywhere; }
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
  .tomap { margin: 10px 0 0; }
  .tomap a { color: var(--hot); font-size: 12px; text-decoration: none; }
  .tomap a:hover { text-decoration: underline; }
  .anyone { margin: 0; font-size: 13px; }
  .suits { list-style: none; margin: 0; padding: 0; }
  .suits li {
    display: flex;
    gap: 10px;
    align-items: baseline;
    padding: 3px 0;
  }
  .suits .who { flex: none; }
  .suits .why { color: var(--dim); font-size: 12px; }

  .bonuses { list-style: none; margin: 0 0 10px; padding: 0; }
  .bonuses li { display: flex; gap: 10px; padding: 4px 0; border-top: 1px solid var(--edge); }
  .bonuses li:first-child { border-top: 0; }
  .bonuses .worn {
    flex: none;
    min-width: 22px;
    text-align: right;
    color: var(--hot);
    font-variant-numeric: tabular-nums;
  }
  .bonuses .gives { display: flex; flex-direction: column; gap: 2px; font-size: 13px; }

  .lore { margin: 0; color: var(--dim); font-size: 13px; line-height: 1.45; font-style: italic; }
  .grant { margin: 6px 0 2px; font-size: 13px; }
  .grant .lvl { color: var(--dim); }
  .grant .chance { color: var(--hot); }
  .effect-options { margin: 4px 0 8px; font-size: 12px; }
  .effect-options summary { cursor: pointer; color: var(--dim); }
  .grant strong { color: var(--gold, #d8b45a); font-weight: 600; }
  .grant .second { margin-left: 6px; }
  /* the same odds for whoever is reading; a margin and not a space, which
     Svelte trims at the edge of an {#if} */
  .mine { color: #e8c860; margin-left: .45em; }
</style>
