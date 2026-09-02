<script>
  // What a thing actually does, over the map.
  //
  // The right-hand list answers where something drops and how often, which is
  // what the map is for; the stats, the talent it grants and the set it belongs
  // to are the codex's answer, and this is that card without leaving the page.
  import { find, read } from './lib/book.js';
  import { talk } from './lib/say.js';

  let { name = null, lang = 'en', onclose } = $props();

  // The map packs the things that drop somewhere and the codex packs every item
  // the game defines; this card is the codex's, so it reads the codex's sheet.
  const SHEET = 'img/codex.webp';

  // Raw rather than deep state: the table is seventeen hundred records that
  // never change, and proxying all of them to open one card is work for
  // nothing. `read` hands back a new wrapper when a language arrives, which is
  // the only thing that ever moves here.
  let book = $state.raw(null);
  let failed = $state(null);
  // The card itself is the codex page's, and it is fetched with the table
  // rather than shipped with the map: a reader who only wants to know where
  // something drops never asks for either.
  let Card = $state.raw(null);

  // What the card is showing. It starts as the row that was clicked and moves
  // from there: a set piece and a runeword's socket are both things to read,
  // and the card names them without a way to open them otherwise.
  let picked = $state(null);
  const key = $derived(picked ?? (book && name ? find(book, name) : null));
  const item = $derived(key ? book?.items[key] : null);
  // The types are named apart from the rest of the words, the same way the
  // codex page reads them.
  const t = $derived(book ? talk(lang, { ...book.words, ...book.types }) : (s) => s);

  // A new row is a new card, whatever the last one was showing.
  $effect(() => {
    name;
    picked = null;
  });

  $effect(() => {
    if (!name) return;
    if (!Card) import('./codex/Detail.svelte').then((m) => (Card = m.default));
    read(lang)
      .then((d) => { book = d; failed = null; })
      .catch((e) => (failed = e));
  });
</script>

<svelte:window onkeydown={(e) => name && e.key === 'Escape' && onclose()} />

{#if name}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="over" onclick={onclose}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="sheet" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
      <button class="x" aria-label={t('Let it go')} onclick={onclose}>×</button>
      {#if item && Card}
        <Card data={book} {item} {lang} sheet={SHEET} {t} pick={(k) => (picked = k)} />
      {:else if failed}
        <p class="note">{failed.message}</p>
      {:else}
        <p class="note">…</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .over {
    position: fixed;
    inset: 0;
    z-index: 40;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: #000000a8;
  }
  .sheet {
    position: relative;
    display: flex;
    width: min(560px, 100%);
    max-height: 100%;
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 10px;
    box-shadow: 0 18px 60px #000000a0;
  }
  /* the codex's card carries the border it needs against the list it sits
     beside, and there is no list here */
  .sheet :global(.panel) {
    flex: 1;
    min-width: 0;
    border-left: 0;
    border-radius: 10px;
  }
  .x {
    position: absolute;
    top: 6px;
    right: 8px;
    z-index: 1;
    padding: 2px 7px;
    color: var(--dim);
    background: #00000060;
    border: 0;
    border-radius: 6px;
    font: inherit;
    font-size: 18px;
    line-height: 1.1;
    cursor: pointer;
  }
  .x:hover { color: var(--hot); }
  .note { margin: 0; padding: 28px; color: var(--dim); }

  @media (max-width: 700px) {
    .over { padding: 0; }
    .sheet { width: 100%; height: 100%; max-height: none; border: 0; border-radius: 0; }
    .sheet :global(.panel) { border-radius: 0; }
  }
</style>
