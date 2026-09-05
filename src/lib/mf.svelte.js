// The reader's own magic find, and the odds it actually buys them.
//
// The game prints two numbers on an item: one that is the same for everybody,
// and one that is the first divided by what the player is carrying. This page
// has only ever shown the first, because the second is not a fact about the
// item — it is a fact about whoever is reading. So it is asked for, once, kept,
// and then every figure on the page carries both.
//
// Module state rather than a prop threaded through nine components: the odds
// are drawn in the tooltip, the panel, the item card, the codex list and the
// codex sheet, and none of those own the number.

const KEPT = 'hs-map.mf';

/**
 * 0 means "not given" and turns the second figure off everywhere.
 *
 * A function declaration and not a `const` arrow, and that is the whole reason
 * this comment exists: `read` runs while the module is still being evaluated,
 * an arrow declared below it is in its temporal dead zone at that moment, and
 * the ReferenceError landed in `read`'s own catch — which was there for a
 * browser that refuses storage. The stored number was read, thrown away and
 * reported as "nothing stored" on every single load.
 */
function clamp(n) {
  return Math.min(10000, Math.max(0, Math.round(n)));
}

/** What was kept from last time, or 0. */
function read() {
  try {
    const n = Number(localStorage.getItem(KEPT));
    return Number.isFinite(n) && n > 0 ? clamp(n) : 0;
  } catch {
    // a browser told to refuse storage still shows the base odds
    return 0;
  }
}

/** Whole percent, 0 when it has not been given. */
export const mf = $state({ value: read() });

export function setMF(n) {
  mf.value = clamp(Number(n) || 0);
  try {
    localStorage.setItem(KEPT, String(mf.value));
  } catch {
    // it lasts the visit rather than the year, which is still worth having
  }
}
