<script>
  // The Bounty Board, and what it asks for.
  //
  // The board stands in Tarethiel and posts one job a day out of a fixed set of
  // thirteen. Every word on this page — the name, the brief, each objective — is
  // the game's own, in whichever of the eleven languages the reader picked; see
  // build/bounty.py for which quests are the board's and how that was settled.
  //
  // The video beside each one is the part the game cannot supply. Until there is
  // a link the card draws the space where it goes, so a quest without one reads
  // as "not yet" rather than as broken.
  import { asset, recall, remember } from '../lib/map.js';
  import { speak } from '../lib/lang.js';
  import { talk } from '../lib/say.js';

  let data = $state(null);
  let failed = $state(null);
  let lang = $state('en');
  let query = $state(recall('find') ?? '');
  let loading = $state(null);

  const KEPT = 'hs-map.lang';
  const remembered = () => {
    try {
      return localStorage.getItem(KEPT);
    } catch {
      return null;
    }
  };

  const t = $derived(talk(lang, data?.words));
  /** One of the game's phrases, in the reader's language. */
  const word = (o) => o?.[lang] || o?.en || '';

  /**
   * The quests that answer what was typed.
   *
   * Name, brief and every objective, because a reader looking for the one about
   * the amulet does not know it is called "Anita's Amulet" — they know there was
   * an amulet in it. The English is searched under the reader's own language for
   * the same reason it is everywhere else on this site: half the community talks
   * about these quests in English whatever their game is set to.
   */
  const found = $derived.by(() => {
    const q = query.trim().toLowerCase();
    const all = data?.quests ?? [];
    if (q.length < 2) return all;
    const hay = (o) => `${o?.[lang] ?? ''} ${o?.en ?? ''}`.toLowerCase();
    return all.filter(
      (x) =>
        hay(x.name).includes(q) ||
        hay(x.brief).includes(q) ||
        x.goals.some((g) => hay(g).includes(q)),
    );
  });

  $effect(() => {
    remember({ find: query.trim() || null });
  });

  /**
   * How long the job on the board has left.
   *
   * The board is cleared at midnight UTC, so the countdown is the same figure
   * for everybody and the reader's own time zone never comes into it. Taken
   * off `Date.UTC` of tomorrow rather than by adding twenty-four hours: a local
   * day is not always twenty-four hours long, and the difference shows up as an
   * hour out twice a year.
   */
  let now = $state(Date.now());
  $effect(() => {
    const tick = setInterval(() => (now = Date.now()), 1000);
    return () => clearInterval(tick);
  });

  const left = $derived.by(() => {
    const d = new Date(now);
    const midnight = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + 1);
    const secs = Math.max(0, Math.round((midnight - now) / 1000));
    const two = (n) => String(n).padStart(2, '0');
    return `${two(Math.floor(secs / 3600))}:${two(Math.floor(secs / 60) % 60)}:${two(secs % 60)}`;
  });

  async function load() {
    try {
      const res = await fetch(asset('data/bounty.json'));
      if (!res.ok) throw new Error(`bounty.json: ${res.status} ${res.statusText}`);
      data = await res.json();
      const want = remembered();
      if (want && want !== 'en' && data.langs.includes(want)) {
        await speak(data, 'bounty', want);
        lang = want;
      }
    } catch (e) {
      failed = String(e);
    } finally {
      document.getElementById('boot')?.remove();
    }
  }
  load();

  async function say(next) {
    if (next === lang || !data) return;
    loading = next;
    try {
      if (next !== 'en') await speak(data, 'bounty', next);
      lang = next;
      localStorage.setItem(KEPT, next);
    } catch {
      // the page is whole in the language it is in; the picker snapping back is
      // what says the switch failed
    } finally {
      loading = null;
    }
  }
</script>

{#if failed}
  <p class="broke">The bounty list would not load.<br><code>{failed}</code></p>
{:else if data}
  <!-- The scroller, and it has to be here rather than on the document:
       theme.css pins html and body for the map, which fills the window and
       must never scroll behind itself. Every other page scrolls a box of its
       own for the same reason, and this is that box. -->
  <div class="scroll">
  <div class="page">
    <header>
      <span class="side">
        <a class="back" href={asset('index.html')}>◀ {t('Back')}</a>
        <span class="count">{found.length} / {data.quests.length}</span>
      </span>

      <input
        type="search"
        placeholder={t('Find a quest, or what it asks for…')}
        title={lang === 'en' ? null : t('searched in this language and English')}
        autocomplete="off"
        spellcheck="false"
        bind:value={query}
      />

      <span class="side end">
        {#if query.trim()}
          <button class="clear" onclick={() => (query = '')}>{t('clear')}</button>
        {/if}
        <select
          value={loading ?? lang}
          aria-label={t('Language')}
          aria-busy={loading ? 'true' : null}
          class:loading
          onchange={(e) => say(e.currentTarget.value)}
        >
          {#each data.langs as l (l)}<option value={l}>{l.toUpperCase()}</option>{/each}
        </select>
      </span>
    </header>

    <div class="lede">
      <p>{t('The board in Tarethiel posts one of these a day. What each asks for is the game’s own wording.')}</p>
      <span class="reset" title={t('the board is cleared at 00:00 UTC')}>
        {t('Reset in')}
        <span class="clock">{left}</span>
      </span>
    </div>

    {#if found.length === 0}
      <p class="empty">{t('Nothing matches.')}</p>
    {:else}
      <ul class="quests">
        {#each found as q (q.key)}
          <li class="quest" id={q.key}>
            <div class="what">
              <h2>{word(q.name)}</h2>
              {#if word(q.brief)}<p class="brief">{word(q.brief)}</p>{/if}
              {#if q.goals.length}
                <p class="head">{t('Objectives')}</p>
                <ul class="goals">
                  {#each q.goals as g, i (i)}<li>{word(g)}</li>{/each}
                </ul>
              {/if}
            </div>

            <!-- The video, or the space it will take. A 16:9 box either way, so
                 a list half filled in does not jump about as it is filled. -->
            <div class="film">
              <!-- The referrer policy sends the origin and never the path. The
                   tighter `no-referrer` is what the player refuses: with no
                   Referer at all it cannot tell which site embedded it, and
                   every video came back as a player configuration error, 153,
                   instead of playing. Privacy is `youtube-nocookie` above. -->
              {#if q.video}
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${q.video}`}
                  title={word(q.name)}
                  loading="lazy"
                  referrerpolicy="strict-origin-when-cross-origin"
                  allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture"
                  allowfullscreen
                ></iframe>
              {:else}
                <div class="soon">
                  <span class="play">▶</span>
                  <span>{t('a walkthrough goes here')}</span>
                </div>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
  </div>
{/if}

<style>
  .scroll {
    height: 100%;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 14px 40px;
  }

  header {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 10px 0;
    background: #100a13;
    border-bottom: 1px solid var(--edge);
  }
  .side { display: flex; gap: 10px; align-items: center; flex: none; }
  .side.end { margin-left: auto; }
  .count { color: var(--dim); font-size: 12px; font-variant-numeric: tabular-nums; }
  .back { color: var(--dim); text-decoration: none; font-size: 13px; }
  .back:hover { color: var(--hot); }

  input[type='search'] {
    flex: 1;
    min-width: 0;
    padding: 6px 10px;
    color: inherit;
    background: #180d13;
    border: 1px solid var(--edge);
    border-radius: 5px;
    font: inherit;
    font-size: 13px;
  }
  input[type='search']:focus { outline: none; border-color: var(--hot); }

  button.clear, select {
    padding: 4px 8px;
    color: var(--dim);
    background: #180d13;
    border: 1px solid var(--edge);
    border-radius: 5px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }
  button.clear:hover, select:hover { border-color: var(--hot); color: var(--hot); }
  select.loading { opacity: .55; cursor: progress; }
  select option { background: #180d13; }

  /* The sentence and the clock on one line, and the clock under it once that
     stops fitting rather than squeezing the sentence to two words. */
  .lede {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
    margin: 14px 0 18px;
    color: var(--dim);
    font-size: 13px;
  }
  .lede p { margin: 0; flex: 1 1 22em; }

  .reset {
    display: inline-flex;
    gap: 7px;
    align-items: baseline;
    flex: none;
    padding: 5px 10px;
    background: #180d13;
    border: 1px solid var(--edge);
    border-radius: 999px;
    font-size: 12px;
    white-space: nowrap;
    cursor: help;
  }
  /* Fixed-width digits, or the whole pill twitches once a second as the glyphs
     change width under it. */
  .clock {
    color: var(--hot);
    font-variant-numeric: tabular-nums;
    letter-spacing: .5px;
  }
  .empty { color: var(--dim); font-style: italic; }
  .broke { padding: 40px; text-align: center; color: var(--dim); }

  .quests { margin: 0; padding: 0; list-style: none; display: grid; gap: 14px; }

  /* Words on the left, picture on the right, and one under the other as soon as
     that stops fitting — the brief is three lines and the film is 16:9, so side
     by side is only worth having on a wide screen. */
  .quest {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 16px;
    padding: 14px 16px;
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 9px;
  }
  @media (max-width: 720px) {
    .quest { grid-template-columns: 1fr; }
  }

  .what { min-width: 0; }
  h2 {
    margin: 0 0 4px;
    font-size: 15px;
    font-weight: 600;
    color: var(--hot);
  }
  .brief { margin: 0; font-size: 13px; line-height: 1.5; }
  .head {
    margin: 12px 0 4px;
    color: var(--dim);
    font-size: 10px;
    letter-spacing: .5px;
    text-transform: uppercase;
  }
  .goals { margin: 0; padding: 0 0 0 16px; font-size: 13px; line-height: 1.6; }
  .goals li::marker { color: var(--dim); }

  .film { align-self: start; }
  .film iframe,
  .soon {
    display: block;
    width: 100%;
    aspect-ratio: 16 / 9;
    border: 0;
    border-radius: 6px;
  }
  .soon {
    display: grid;
    place-content: center;
    gap: 8px;
    justify-items: center;
    color: #5f5259;
    background: #150e19;
    border: 1px dashed var(--edge);
    font-size: 11px;
    text-align: center;
  }
  .soon .play { font-size: 20px; opacity: .5; }
</style>
