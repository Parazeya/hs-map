<script>
  // What a thing actually does, over the map.
  //
  // The right-hand list answers where something drops and how often, which is
  // what the map is for; the stats, the talent it grants and the set it belongs
  // to are the codex's answer, and this is that card without leaving the page.
  import { read, resolveItem } from './lib/book.js';
  import { talk } from './lib/say.js';
  import { mapMessages } from './lib/map-messages.js';
  import { codexPhrase } from './codex/phrases.js';

  let { name, title, itemKey, recordId, lang, onclose } = $props();

  // The map packs the things that drop somewhere and the codex packs every item
  // the game defines; this card is the codex's, so it reads the codex's sheet.
  const SHEET = 'img/codex.webp';

  // Raw rather than deep state: the table is seventeen hundred records that
  // never change, and proxying all of them to open one card is work for
  // nothing. `read` hands back a new wrapper when a language arrives, which is
  // the only thing that ever moves here.
  let book = $state.raw(null);
  let failed = $state(false);
  let attempt = $state(0);
  // The card itself is the codex page's, and it is fetched with the table
  // rather than shipped with the map: a reader who only wants to know where
  // something drops never asks for either.
  let Card = $state.raw(null);
  let dialog = $state(null);
  let dismiss = $state(null);

  // What the card is showing. It starts as the row that was clicked and moves
  // from there: a set piece and a runeword's socket are both things to read,
  // and the card names them without a way to open them otherwise.
  let picked = $state(null);
  const resolved = $derived(book ? resolveItem(book, name, itemKey, recordId) : null);
  const key = $derived(picked ?? resolved?.key);
  const item = $derived(key ? book?.items[key] : null);
  // The types are named apart from the rest of the words, the same way the
  // codex page reads them.
  const t = $derived(book ? talk(lang, { ...book.words, ...book.types }) : (s) => s);

  $effect(() => {
    const sheet = dialog;
    if (!sheet || !dismiss) return;
    sheet.showModal();
    dismiss.focus({ preventScroll: true });
    return () => { if (sheet.open) sheet.close(); };
  });

  $effect(() => {
    attempt;
    const request = read(lang);
    book = null;
    failed = false;
    let active = true;
    Promise.all([request, import('./codex/Detail.svelte')]).then(([data, module]) => {
      if (!active) return;
      Card = module.default;
      book = data;
    }).catch(() => { if (active) failed = true; });
    return () => { active = false; };
  });

  function closeFromBackdrop(event) {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onclose();
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<dialog class="sheet" aria-label={title} bind:this={dialog} onclick={closeFromBackdrop}
  oncancel={(event) => { event.preventDefault(); onclose(); }}>
  <button type="button" class="x" bind:this={dismiss} aria-label={mapMessages(lang).close} onclick={onclose}>×</button>
  {#if item && Card}
    <Card data={book} {item} {lang} sheet={SHEET} {t} initialRecordId={picked ? null : resolved?.recordId}
      pick={(k) => { picked = k; }} />
  {:else if failed}
    <div class="note">
      <p role="alert">{codexPhrase(lang, 'Could not load the item catalogue.')}</p>
      <button type="button" class="retry" onclick={() => { attempt += 1; dismiss?.focus(); }}>{mapMessages(lang).retry}</button>
    </div>
  {:else if book}
    <p class="note" role="status">{codexPhrase(lang, 'Item details are unavailable.')}</p>
  {:else}
    <p class="note" role="status">{codexPhrase(lang, 'Reading the item table…')}</p>
  {/if}
</dialog>

<style>
  .sheet {
    position: fixed;
    inset: 0;
    width: min(560px, 100% - 48px);
    max-height: calc(100dvh - 48px);
    padding: 0;
    color: var(--ink);
    background: var(--panel);
    border: 1px solid var(--edge);
    border-radius: 10px;
    box-shadow: 0 18px 60px #000000a0;
  }
  .sheet[open] { display: flex; }
  .sheet::backdrop { background: #000000a8; }
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
  .note p { margin: 0 0 .75rem; }
  .retry {
    padding: .3rem .6rem;
    color: var(--ink);
    background: var(--ground);
    border: 1px solid var(--edge);
    border-radius: 6px;
    font: inherit;
    cursor: pointer;
  }

  @media (max-width: 46rem) {
    .sheet { width: 100%; height: 100%; max-width: none; max-height: none; border: 0; border-radius: 0; }
    .sheet :global(.panel) { border-radius: 0; }
  }
</style>
