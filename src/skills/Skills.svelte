<script>
  import { tick } from 'svelte';
  import { asset, mapDocument, recall, remember } from '../lib/map.js';
  import { talk } from '../lib/say.js';
  import { catalogueLanguage, preferredUiLanguage } from '../lib/ui-language.svelte.js';
  import { catalogueMessages } from '../lib/catalogue-messages.js';
  import CatalogueLoadStatus from '../CatalogueLoadStatus.svelte';
  import LanguageNotice from '../LanguageNotice.svelte';
  import ItemIcon from '../ItemIcon.svelte';

  const SHEET = 'img/skills.webp';

  let data = $state(null);
  let failed = $state(false);
  const language = catalogueLanguage('skills');
  const lang = $derived(language.current);
  const startupLang = preferredUiLanguage();
  const messages = catalogueMessages(startupLang);

  let query = $state('');
  let hero = $state(null); // a class id
  let element = $state(null); // a damage type key
  let tag = $state(null); // an abilityTag* key
  // Read before anything else runs: the effect below writes the address back
  // as soon as the page mounts, and with nothing open yet that erases what the
  // address was holding before the table has arrived to check it against.
  const asked = { skill: recall('skill'), node: Number(recall('node') ?? NaN) };

  let chosen = $state(null); // the skill being read, by key
  let node = $state(null); // the place in its tree being read, 0 to 14
  let filters = $state(false); // only means anything on a phone
  // The hero is chosen by typing, so the box holds what was typed and the list
  // under it holds what still matches. Picking one writes it into the box.
  let heroQuery = $state('');
  let heroOpen = $state(false);
  let tagQuery = $state('');

  const t = $derived(talk(lang, data?.words));
  /** One of the game's phrases, in the reader's language. */
  const word = (o) => o?.[lang] || o?.en || '';

  const all = $derived(
    Object.entries(data?.skills ?? {}).map(([key, s]) => ({ ...s, key })),
  );

  /**
   * Where a word was found in a skill, if it was found at all.
   *
   * The specialisations are searched as well as the skill. Three thousand three
   * hundred of them are drawn on this page and none of them was reachable by
   * typing what it does: "stun" found nothing, while Tectonic Hit — a chance to
   * stun monsters on hit — sat two clicks away on a tree nobody had a reason to
   * open.
   *
   * The node that answered is carried back so the row can say so and the tree
   * can open on it. A skill whose own name matches says nothing extra: it is
   * already the thing on the row.
   */
  function found(s, q) {
    if (!q) return { hit: true, at: null };
    if (word(s.names).toLowerCase().includes(q) || word(s.lore).toLowerCase().includes(q)) {
      return { hit: true, at: null };
    }
    const at = (s.subs ?? []).find(
      (n) =>
        word(n.names).toLowerCase().includes(q) ||
        word(n.lore).toLowerCase().includes(q) ||
        (n.gives?.base ?? []).some((g) => String(g.of).toLowerCase().includes(q)),
    );
    return at ? { hit: true, at } : { hit: false, at: null };
  }

  const shown = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return all
      .filter((s) => !hero || s.class === hero)
      .filter((s) => !element || s.element.includes(element))
      .filter((s) => !tag || s.tags.includes(tag))
      .map((s) => ({ ...s, via: found(s, q) }))
      .filter((s) => s.via.hit)
      // By hero first, because a tree read together is what a hero's page is;
      // inside one, the order it is learned in.
      .sort((a, b) =>
        (hero ? 0 : a.class.localeCompare(b.class))
        || (a.lvl ?? 0) - (b.lvl ?? 0)
        || word(a.names).localeCompare(word(b.names)));
  });

  const open = $derived(chosen ? all.find((s) => s.key === chosen) : null);

  // The game lays every tree out the same way — the same fifteen places, wired
  // the same — and only what stands in each place changes. The drawing is
  // 587x514 in the game and is drawn here at whatever fraction of that the
  // panel has room for, so a wide window gets a big tree and a narrow one still
  // gets a whole tree; every piece of its art scales with it.
  const RING = 587;
  const RUNG = 514;
  let panelW = $state(0);
  const K = $derived(Math.max(0.5, Math.min(1, (panelW - 44) / RING)) || 0.62);

  const NODES = 'img/subskills.webp';

  /** A node's own icon, which the game keeps a frame of per place in the tree. */
  const face = (key, i) => {
    const f = data?.faces;
    const at = f?.at?.[key]?.[i];
    if (!at) return '';
    const side = i === 0 || i > 10 ? f.bg : f.sm;
    return (
      `width:${side * K}px;height:${side * K}px;` +
      `background-image:url(${asset(NODES)});` +
      `background-position:${-at[0] * K}px ${-at[1] * K}px;` +
      `background-size:${f.w * K}px ${f.h * K}px;`
    );
  };

  /** A box out of the icon sheet, drawn at the tree's scale. */
  const art = (b) =>
    b
      ? `width:${b[2] * K}px;height:${b[3] * K}px;` +
        `background-image:url(${asset(SHEET)});` +
        `background-position:${-b[0] * K}px ${-b[1] * K}px;` +
        `background-size:${data.sheet.w * K}px ${data.sheet.h * K}px;`
      : '';

  /** The colour the tree is wired and plated in: the skill's own. */
  const el = $derived(open?.element?.[0] ?? 'physical');
  const layout = $derived(data?.layout ?? []);
  /** Each wire once, however many places name it. */
  const wires = $derived.by(() => {
    const seen = new Set();
    const out = [];
    layout.forEach((n, i) => {
      for (const j of n.to) {
        const k = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (seen.has(k)) continue;
        seen.add(k);
        out.push([n.at, layout[j].at]);
      }
    });
    return out;
  });
  const reading = $derived(node == null ? null : open?.subs?.find((x) => x.i === node));

  const narrowScreen = window.matchMedia('(max-width: 60rem)');
  let detailTitle = $state(null);
  let detailPanel = $state(null);
  let listPanel = $state(null);
  let filtersPanel = $state(null);
  let searchBox = $state(null);
  let filtersButton = $state(null);
  let lastResult;
  let resultScroll = 0;

  async function read(key, at, button) {
    lastResult = button;
    resultScroll = listPanel?.scrollTop ?? 0;
    chosen = key;
    node = at;
    await tick();
    detailPanel?.scrollTo(0, 0);
    if (narrowScreen.matches) detailTitle?.focus({ preventScroll: true });
  }

  async function backToResults() {
    chosen = null;
    node = null;
    await tick();
    listPanel?.scrollTo(0, resultScroll);
    (lastResult?.isConnected ? lastResult : searchBox)?.focus({ preventScroll: true });
  }

  async function toggleFilters() {
    filters = !filters;
    if (!filters) filtersButton?.focus();
    else {
      await tick();
      filtersPanel?.querySelector('button:not(:disabled), input')?.focus();
    }
  }

  function onkeydown(event) {
    if (event.key !== 'Escape') return;
    if (open) {
      event.preventDefault();
      backToResults();
    } else if (filters && narrowScreen.matches) {
      event.preventDefault();
      toggleFilters();
    }
  }

  // What is open, in the address, so a skill can be reloaded or sent to
  // somebody — the node it is opened at as well, because a tree of fifteen is
  // worth pointing at one of.
  $effect(() => {
    if (data) remember({ skill: chosen, node: chosen && node != null ? node : null });
  });

  function nothing() {
    query = '';
    hero = null;
    heroQuery = '';
    element = null;
    tag = null;
    tagQuery = '';
  }

  const filtered = $derived(Boolean(query.trim() || hero || element || tag || tagQuery.trim()));

  /** A proc, as one line: what sets it off and how often. */
  const chance = (p) => {
    const c = p?.chance;
    if (c == null) return null;
    if (typeof c === 'number') return `${c}%`;
    return c.perRank ? `+${c.perRank}% ${t('per rank')}` : `${c.base}%`;
  };
  const trigger = (p) => (p?.trigger ?? '').replace(/_/g, ' ');

  /** How many skills each chip would leave, so a dead end is visible before it is taken. */
  const left = $derived.by(() => {
    const by = { hero: {}, element: {}, tag: {} };
    for (const s of all) {
      if ((!element || s.element.includes(element)) && (!tag || s.tags.includes(tag))) {
        by.hero[s.class] = (by.hero[s.class] ?? 0) + 1;
      }
      if (!hero || s.class === hero) {
        for (const e of s.element) by.element[e] = (by.element[e] ?? 0) + 1;
        for (const g of s.tags) by.tag[g] = (by.tag[g] ?? 0) + 1;
      }
    }
    return by;
  });

  async function load(retry = false) {
    failed = false;
    try {
      const res = await fetch(asset('data/skills.json'), { cache: retry ? 'reload' : 'default' });
      if (!res.ok) throw new Error(`skills.json: ${res.status} ${res.statusText}`);
      const loaded = await res.json();
      await language.prepare(loaded);
      data = loaded;
      // and what the address was holding, now that there is a table to check
      if (asked.skill && data.skills[asked.skill]) {
        chosen = asked.skill;
        if (Number.isInteger(asked.node) && asked.node >= 0 && asked.node < 15) {
          node = asked.node;
        }
      }
    } catch {
      failed = true;
    } finally {
      document.getElementById('boot')?.remove();
    }
  }
  load();

  const only = (set, v) => (set === v ? null : v);

  const heroHits = $derived.by(() => {
    const q = heroQuery.trim().toLowerCase();
    return (data?.classes ?? []).filter((c) => !q || word(c.names).toLowerCase().includes(q));
  });

  function pickHero(c) {
    hero = c?.id ?? null;
    heroQuery = c ? word(c.names) : '';
    heroOpen = false;
  }

  const tagList = $derived.by(() => {
    const q = tagQuery.trim().toLowerCase();
    return (data?.tags ?? [])
      .map((g) => ({ ...g, n: left.tag[g.id] ?? 0 }))
      .filter((g) => !q || word(g.names).toLowerCase().includes(q))
      .filter((g) => g.n || tag === g.id)
      .sort((a, b) => b.n - a.n || word(a.names).localeCompare(word(b.names)));
  });
</script>

<svelte:window {onkeydown} />

<header class:detail-open={open}>
  <a class="back" href={mapDocument('index.html')}>◀ {t('Map')}</a>
  <h1>{t('Skills')}</h1>
  {#if data}
  <input class="find" type="search" bind:this={searchBox} bind:value={query}
    aria-label={t('a skill…')} placeholder={t('a skill…')} />
  {#if filtered}
    <button class="wipe" onclick={nothing}>{t('clear')}</button>
  {/if}
  <button class="narrow" bind:this={filtersButton} aria-expanded={filters} aria-controls="skill-filters"
    onclick={toggleFilters}>{t('Filters')}</button>
    <select class="lang" aria-label={t('Language')} value={language.pending ?? lang}
      aria-busy={!!language.pending} onchange={(e) => language.pick(data, e.currentTarget.value)}>
      {#each data.langs as l (l)}<option value={l}>{l.toUpperCase()}</option>{/each}
    </select>
  {/if}
</header>

{#if !data}
  <CatalogueLoadStatus {failed} loading={messages.skillsLoading} message={messages.skillsError}
    lang={startupLang} retry={() => load(true)} />
{:else}
  <main class:reading={open} class:filtering={filters}>
    <aside id="skill-filters" class="side" class:open={filters} bind:this={filtersPanel}>
      <p class="head">{t('Damage')}{#if element}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { element = null; }}>×</button>{/if}</p>
      <div class="chips">
        {#each data.elements as e (e.id)}
          <button class="e-{e.id}" class:on={element === e.id}
            disabled={!left.element[e.id] && element !== e.id}
            onclick={() => (element = only(element, e.id))}>{word(e.names)}</button>
        {/each}
      </div>

      <p class="head">{t('Hero')}{#if hero || heroQuery}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { pickHero(null); }}>×</button>{/if}</p>
      <input
        class="pick"
        type="search"
        placeholder={t('all')}
        autocomplete="off"
        bind:value={heroQuery}
        onfocus={() => (heroOpen = true)}
      />
      {#if heroOpen}
        <div class="picklist">
          <button class:on={!hero} onclick={() => pickHero(null)}>{t('all')}</button>
          {#each heroHits as c (c.id)}
            <button class:on={hero === c.id} disabled={!left.hero[c.id] && hero !== c.id}
              onclick={() => pickHero(c)}>{word(c.names)}</button>
          {/each}
          {#if heroHits.length === 0}<p class="none">{t('No hero by that name.')}</p>{/if}
        </div>
      {/if}

      <p class="head">{t('Tag')}{#if tag || tagQuery}<button class="drop" title={t('clear')} aria-label={t('clear')} onclick={() => { tag = null; tagQuery = ''; }}>×</button>{/if}</p>
      <input class="pick" type="search" placeholder={t('a tag…')} autocomplete="off"
        bind:value={tagQuery} />
      <div class="counted">
        {#each tagList as g (g.id)}
          <button class:on={tag === g.id} onclick={() => (tag = only(tag, g.id))}>
            <span class="t">{word(g.names)}</span>
            <span class="n">{g.n}</span>
          </button>
        {/each}
        {#if tagList.length === 0}<p class="none">{t('No tag by that name.')}</p>{/if}
      </div>
    </aside>

    <section class="list" bind:this={listPanel}>
      <p class="count">{shown.length} {t('of')} {all.length}</p>
      <ul>
        {#each shown as s (s.key)}
          <li>
            <button
              class="row"
              class:on={chosen === s.key}
              aria-current={chosen === s.key ? 'true' : null}
              onclick={(event) => read(s.key, s.via.at?.i ?? null, event.currentTarget)}
            >
              <ItemIcon item={s} sheet={data.sheet} from={SHEET} box={22} />
              <span class="nm">
                {word(s.names)}
                <!-- the word was not in the skill but in one of its
                     specialisations, and the row says which -->
                {#if s.via.at}<span class="via">{word(s.via.at.names)}</span>{/if}
              </span>
              <span class="cl">{word(data.classes.find((c) => c.id === s.class)?.names)}</span>
              {#if s.lvl}<span class="lv">{t('lvl')} {s.lvl}</span>{/if}
              {#if s.subs.length}<span class="sub">{s.subs.length}</span>{/if}
            </button>
          </li>
        {/each}
      </ul>
    </section>

    <section class="panel" class:reading={open} bind:this={detailPanel} bind:clientWidth={panelW}>
      {#if open}
        <div class="detail-nav">
          <button aria-label={`${t('Back')} · ${t('Skills')}`} onclick={backToResults}>← {t('Skills')}</button>
        </div>
        <h2 class="title" tabindex="-1" bind:this={detailTitle}>
          <ItemIcon item={open} sheet={data.sheet} from={SHEET} box={34} />
          {word(open.names)}
        </h2>
        <p class="under">
          {word(data.classes.find((c) => c.id === open.class)?.names)}
          {#if open.lvl} · {t('lvl')} {open.lvl}{/if}
          {#each open.element as e}
            · <span class="el {e}">{word(data.elements.find((x) => x.id === e)?.names)}</span>
          {/each}
        </p>
        {#if word(open.lore)}<p class="lore">{word(open.lore)}</p>{/if}


        {#if open.lines.length}
          <h3>{t('Effect')}</h3>
          <ul class="lines">
            {#each open.lines as l, i (i)}
              <li>
                <span class="v">{l.start ?? '?'}{l.mark}{#if l.unit} {word(l.unit)}{/if}</span>
                <span class="w">
                  {word(l.of)}
                  {#if l.mark_known === false}<span class="per">{t('Unit is unknown.')}</span>{/if}
                  {#if l.per == null}<span class="per">{t('Growth per level is unknown.')}</span>
                  {:else if l.per !== 0}<span class="per">+{l.per}{l.mark} {t('per level')}</span>{/if}
                </span>
              </li>
            {/each}
          </ul>
        {/if}

        <dl class="facts">
          {#if open.kind}
            <dt>{t('Kind')}</dt>
            <dd>{word(data.kinds.find((k) => k.id === open.kind)?.names)}</dd>
          {/if}
          {#if open.mana}
            <dt>{t('Mana')}</dt>
            <dd>{open.mana.base}{#if open.mana.perLevel}<span class="per"
              >+{open.mana.perLevel} {t('per level')}</span>{/if}</dd>
          {/if}
          {#if open.dmg}
            <dt>{t('Base damage')}</dt>
            <dd>{open.dmg.base}{#if open.dmg.perLevel}<span class="per"
              >+{open.dmg.perLevel} {t('per level')}</span>{/if}</dd>
          {/if}
          {#if open.range}<dt>{t('Range')}</dt><dd>{open.range}</dd>{/if}
          {#if open.rate}<dt>{t('Rate')}</dt><dd>{open.rate}</dd>{/if}
          <dt>{t('Speed follows')}</dt>
          <dd>{open.scales === 'cast' ? t('Cast speed')
             : open.scales === 'attack' ? t('Attack speed') : t('Nothing')}</dd>
          {#if open.move != null}
            <dt>{t('Movement')}</dt>
            <dd>{open.move}% <span class="per">{t('of speed while it runs')}</span></dd>
          {/if}
          {#if open.cooldown != null}<dt>{t('Cooldown')}</dt><dd>{open.cooldown}</dd>{/if}
          {#if open.lasts != null}<dt>{t('Lasts')}</dt><dd>{open.lasts}</dd>{/if}
          {#if open.rank}<dt>{t('Ranks')}</dt><dd>{open.rank}</dd>{/if}
        </dl>

        {#if open.bonus.length}
          <h3>{t('Receives bonuses from')}</h3>
          <ul class="lines">
            {#each open.bonus as b, i (i)}
              <li>
                <span class="v">+{b.v}%</span>
                <span class="w">
                  {b.of}
                  <span class="per">{b.from} ·
                    {b.per === 'skill_level' ? t('per skill level') : t('per attribute point')}</span>
                </span>
              </li>
            {/each}
          </ul>
        {/if}

        {#if open.tags.length}
          <div class="worn">
            {#each open.tags as g (g)}
              <span>{word(data.tags.find((x) => x.id === g)?.names)}</span>
            {/each}
          </div>
        {/if}

        {#if open.subs.length}
          <h3>{t('Specialisations')} <span class="n">{open.subs.length}</span></h3>
          <!-- The game draws this on a rune circle: the keystone at the foot,
               the four notables at the corners, the ten minors wired between
               them, every plate coloured by the skill's damage type. The shape
               is one template — only what stands in each place changes. -->
          <div class="tree" style="width:{RING * K}px;height:{RUNG * K}px">
            <svg class="wires {el}" viewBox="0 0 100 100" preserveAspectRatio="none">
              {#each wires as w, i (i)}
                <line x1={w[0][0] * 100} y1={w[0][1] * 100}
                  x2={w[1][0] * 100} y2={w[1][1] * 100} />
              {/each}
            </svg>
            {#each open.subs as x (x.i)}
              {@const spot = layout[x.i]}
              {@const big = spot && spot.role !== 'minor'}
              {#if spot}
                <button
                  class="dot"
                  class:on={node === x.i}
                  style="left:{spot.at[0] * 100}%;top:{spot.at[1] * 100}%"
                  title={word(x.names)}
                  aria-label={word(x.names)}
                  aria-pressed={node === x.i}
                  onclick={() => (node = node === x.i ? null : x.i)}
                >
                  <span class="disc" style={art(data.nodes?.disc?.[big ? 'bg' : 'sm'])}></span>
                  <span class="face" style={face(open.key, x.i)}></span>
                  <span class="ring" style={art(data.nodes?.[big ? 'bg' : 'sm']?.[el])}></span>
                </button>
              {/if}
            {/each}
          </div>

          {#if reading}
            <div class="read">
              <b>{word(reading.names)}</b>
              {#if reading.rank}<span class="cap">0 / {reading.rank}</span>{/if}
              {#if word(reading.lore)}<p class="says">{word(reading.lore)}</p>{/if}
              {#if reading.gives}
                <ul class="gives">
                  {#each reading.gives.per ?? [] as g, i (i)}
                    <li><span class="v">+{g.v}</span> {g.of}
                      <span class="per">{t('per rank')}</span></li>
                  {/each}
                  {#each (reading.gives.base ?? []).filter((g) => g.v) as g, i (i)}
                    <li><span class="v">+{g.v}</span> {g.of}</li>
                  {/each}
                </ul>
              {/if}
              {#if reading.proc}
                <p class="proc">
                  {t('Chance')} {chance(reading.proc) ?? ''} · {trigger(reading.proc)}
                </p>
              {/if}
            </div>
          {:else}
            <p class="hint tiny">{t('Pick a node to read it.')}</p>
          {/if}
        {/if}
      {:else}
        <p class="hint">{t('Pick a skill to read it.')}</p>
      {/if}
    </section>
  </main>
  <LanguageNotice {lang} failure={language.failure}
    retry={(next) => language.pick(data, next)} dismiss={language.dismiss} />
{/if}

<style>
  /* theme.css paints the page and sets the ink; nothing here repeats it. It
     also turns scrolling off on the body, so the columns scroll themselves. */
  header {
    position: fixed;
    inset: 0 0 auto 0;
    height: 52px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 12px;
    background: var(--panel);
    border-bottom: 1px solid var(--edge);
    z-index: 5;
  }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; letter-spacing: .04em; }
  .back { color: var(--dim); text-decoration: none; font-size: 13px; white-space: nowrap; }
  .back:hover { color: var(--ink); }
  .find {
    flex: 1; max-width: 32rem; background: rgba(0, 0, 0, .35); color: var(--ink);
    border: 1px solid var(--edge); border-radius: 6px; padding: 6px 10px; font: inherit;
  }
  .lang {
    margin-left: auto; background: rgba(0, 0, 0, .35); color: var(--ink);
    border: 1px solid var(--edge); border-radius: 6px; padding: 5px 8px; font: inherit;
  }
  .narrow, .detail-nav { display: none; }

  main {
    position: fixed;
    inset: 52px 0 0 0;
    display: grid;
    grid-template-columns: 15rem minmax(0, 1fr) minmax(26rem, 34rem);
  }
  .side, .list, .panel { overflow-y: auto; overscroll-behavior: contain; }

  .side { padding: 12px 12px 24px; border-right: 1px solid var(--edge); }
  .panel h3 {
    font-size: 11px; text-transform: uppercase; letter-spacing: .1em;
    color: var(--dim); margin: 14px 0 6px;
  }
  .head {
    display: flex; align-items: center; gap: 6px;
    margin: 12px 0 6px; color: var(--dim); font-size: 10px; font-weight: 700;
    letter-spacing: .8px; text-transform: uppercase;
  }
  /* the cross that clears one filter, on that filter's own heading */
  .drop {
    margin-left: auto; padding: 0 4px; line-height: 1;
    color: var(--dim); background: none; border: 0;
    font: inherit; font-size: 13px; cursor: pointer;
  }
  .drop:hover { color: var(--hot); }
  .wipe {
    background: rgba(0, 0, 0, .3); color: var(--dim);
    border: 1px solid var(--edge); border-radius: 6px; padding: 5px 9px;
    font: inherit; font-size: 12px; cursor: pointer; white-space: nowrap;
  }
  .wipe:hover { color: var(--hot); border-color: var(--hot); }
  .head:first-child { margin-top: 0; }

  /* A damage type wears its own colour, the way a rarity does on the codex:
     the eye goes to the red one, not to the third word in the second row. */
  .chips { display: flex; flex-wrap: wrap; gap: 3px; }
  .chips button, .counted button {
    color: var(--chip, var(--dim));
    background: none;
    border: 1px solid color-mix(in srgb, var(--chip, var(--edge)) 40%, var(--edge));
    border-radius: 6px; padding: 3px 7px; font: inherit; font-size: 11px; cursor: pointer;
  }
  .chips button.on, .chips button.on:hover {
    color: #120c15; background: var(--chip, var(--dim));
    border-color: var(--chip, var(--dim)); font-weight: 700;
  }
  .chips button:hover, .counted button:hover { background: #ffffff10; }
  .chips button:disabled { opacity: .3; cursor: default; }

  .e-fire { --chip: #ff8b53 } .e-cold { --chip: #7fd6ff } .e-lightning { --chip: #ffe066 }
  .e-poison { --chip: #9ad86b } .e-magic { --chip: var(--hot) } .e-physical { --chip: #d8cfd8 }
  .e-elemental { --chip: #ffb2e6 }
  .fire { color: #ff8b53 } .cold { color: #7fd6ff } .lightning { color: #ffe066 }
  .poison { color: #9ad86b } .magic { color: var(--hot) } .physical { color: #d8cfd8 }
  .elemental { color: #ffb2e6 }

  .pick {
    width: 100%; box-sizing: border-box; padding: 5px 8px; color: inherit;
    font: inherit; font-size: 12px; background: #0e0912;
    border: 1px solid var(--edge); border-radius: 7px;
  }
  .pick:focus { outline: none; border-color: var(--hot); }
  .picklist, .counted {
    display: flex; flex-direction: column; gap: 2px; margin-top: 4px;
    max-height: 13rem; overflow-y: auto; overscroll-behavior: contain;
  }
  .picklist button {
    text-align: left; color: var(--dim); background: none;
    border: 1px solid transparent; border-radius: 6px; padding: 3px 7px;
    font: inherit; font-size: 12px; cursor: pointer;
  }
  .picklist button:hover:not(:disabled) { color: var(--ink); background: #ffffff0c; }
  .picklist button.on { color: var(--ink); border-color: var(--hot); }
  .picklist button:disabled { opacity: .3; cursor: default; }
  .counted { margin-top: 6px; max-height: 18rem; }
  .counted button { display: flex; gap: 8px; align-items: baseline; text-align: left; }
  .counted button.on { border-color: currentColor; background: #ffffff12; }
  .counted .t { flex: 1; min-width: 0; }
  .counted .n { flex: none; opacity: .55; font-variant-numeric: tabular-nums; }
  .none { color: var(--dim); font-size: 12px; margin: 6px 0 0; }

  /* the tags a skill wears, in the reading panel */
  .worn { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 10px; }
  .worn span {
    color: var(--dim); border: 1px solid var(--edge); border-radius: 6px;
    padding: 2px 7px; font-size: 11px;
  }

  .list { padding: 10px 10px 24px; border-right: 1px solid var(--edge); }
  .count { color: var(--dim); font-size: 12px; margin: 0 0 8px; padding-left: 8px; }
  .list ul { list-style: none; margin: 0; padding: 0; }
  .row {
    display: flex; align-items: baseline; gap: 10px; width: 100%; text-align: left;
    background: none; border: 0; border-radius: 6px; padding: 6px 8px;
    color: var(--ink); font: inherit; cursor: pointer;
  }
  .row:hover { background: rgba(255, 255, 255, .05); }
  .row.on { background: #33203c; }
  .nm { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* the specialisation the search found, under the skill holding it */
  .via { display: block; color: var(--dim); font-size: 10px; }
  .cl, .lv { color: var(--dim); font-size: 12px; white-space: nowrap; }
  .sub {
    color: var(--hot); font-size: 11px; border: 1px solid var(--edge);
    border-radius: 999px; padding: 0 6px;
  }

  .panel { padding: 14px 16px 28px; }
  .title { margin: 0; font-size: 18px; display: flex; align-items: center; gap: 10px; }
  .under { color: var(--dim); font-size: 12px; margin: 4px 0 10px; }
  .lore { color: var(--dim); font-style: italic; margin: 0 0 12px; }
  .lines { list-style: none; margin: 0; padding: 0; }
  .lines li { display: flex; gap: 10px; padding: 5px 0; border-top: 1px solid var(--edge); }
  .lines li:first-child { border-top: 0; }
  .v { min-width: 62px; text-align: right; color: var(--hot); }
  .w { flex: 1; }
  .per { display: block; color: var(--dim); font-size: 12px; }
  .facts { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; margin: 10px 0 0; font-size: 13px; }
  .facts dt { color: var(--dim); }
  .facts dd { margin: 0; }
  .facts .per { display: inline; margin-left: 6px; }

  /* The rune circle the game lays a tree out on, with the nodes placed on it
     by the same fractions the game uses. */
  .tree {
    position: relative;
    margin: 10px auto 8px;
  }
  .wires { position: absolute; inset: 0; width: 100%; height: 100%; }
  /* the wires wear the skill's colour, as the plates do */
  .wires line { stroke: currentColor; stroke-width: .45; opacity: .45; }
  .dot {
    position: absolute;
    transform: translate(-50%, -50%);
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    background: none;
    line-height: 0;
    cursor: pointer;
  }
  .dot > span {
    grid-area: 1 / 1;
    display: block;
    image-rendering: pixelated;
  }
  .dot .disc { opacity: .85; }
  .dot:hover .ring { filter: brightness(1.5); }
  .dot.on { z-index: 2; }
  .dot.on .ring { filter: brightness(1.8) drop-shadow(0 0 4px currentColor); }

  .read { border-top: 1px solid var(--edge); margin-top: 4px; padding-top: 8px; }
  .read b { font-weight: 600; }
  .cap { color: var(--hot); font-size: 12px; margin-left: 6px; }
  .gives { list-style: none; margin: 6px 0 0; padding: 0; font-size: 13px; }
  .gives li { display: flex; gap: 8px; padding: 2px 0; }
  .gives .v { min-width: 46px; text-align: right; color: var(--hot); flex: none; }
  .proc { color: var(--dim); font-size: 12px; margin: 6px 0 0; }
  .tiny { font-size: 12px; }
  .says { display: block; color: var(--dim); font-size: 12px; margin: 4px 0 0; }
  .n { color: var(--dim); }
  .hint { color: var(--dim); }

  @media (max-width: 60rem) {
    main { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
    .narrow {
      display: inline-block; background: rgba(0, 0, 0, .3); color: var(--ink);
      border: 1px solid var(--edge); border-radius: 6px; padding: 5px 9px;
      font: inherit; cursor: pointer;
    }
    .side { display: none; border-right: 0; }
    .side.open { display: block; }
    .list { border-right: 0; min-height: 0; }
    main.filtering .list, main.reading .list, main.reading .side { display: none; }
    .panel { display: none; }
    .panel.reading {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 6;
      background: var(--ground, #100a13);
      padding-top: 0;
    }
    .detail-nav {
      display: flex;
      position: sticky;
      top: 0;
      z-index: 3;
      background: var(--ground, #100a13);
      margin: 0 -16px 12px;
      padding: 8px 16px;
      border-bottom: 1px solid var(--edge);
    }
    .detail-nav button {
      padding: 5px 9px;
      color: var(--ink);
      background: var(--panel);
      border: 1px solid var(--edge);
      border-radius: 6px;
      font: inherit;
      cursor: pointer;
    }
    header.detail-open { visibility: hidden; }
  }
  @media (max-width: 38rem) {
    header {
      height: 92px;
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) repeat(3, auto);
      grid-template-rows: minmax(0, 1fr) auto;
      gap: 5px 8px;
      padding: 5px 12px 8px;
    }
    .find { grid-area: 2 / 1 / 3 / -1; width: 100%; min-width: 0; max-width: none; }
    .wipe { grid-area: 1 / 3; }
    .narrow { grid-area: 1 / 4; }
    .lang { grid-area: 1 / 5; margin-left: 0; }
    main { top: 92px; }
  }
</style>
