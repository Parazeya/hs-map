// The codex's table, for a page that is not the codex.
//
// The map's own file is 39 KB and the codex's is 145. A reader who never opens
// an item should not pay for the second, so it is fetched the first time one is
// opened and kept for the rest of the visit — the map page reads what a thing
// does out of the same file the codex page does, rather than out of a second
// copy of it cut down to size.

import { speak } from './lang.js';
import { asset } from './map.js';

/**
 * Put back what the file leaves out, so nothing below has to know it was gone.
 *
 * codex.json says four things once that it used to say for every item: the key,
 * the English name, and on each stat line the stat's own English text and its
 * unit — all of which the `stats` vocabulary at the root or the record's own
 * place in `items` already answers. A line names its stat by index into that
 * vocabulary; here it gets its identifier back. See `squeeze` in build/build.py.
 */
export function hydrate(d) {
  for (const [key, it] of Object.entries(d.items)) {
    it.key = key;
    it.name ??= it.names?.en;
    for (const row of [...(it.stats ?? []), ...(it.more ?? []).flatMap((m) => m.stats)]) {
      const said = d.stats[row.sid];
      row.sid = said.sid;
      row.text = said.text;
      if (said.unit !== undefined) row.unit = said.unit;
    }
  }
  return d;
}

let held = null;

/**
 * The table, in the reader's language, fetched at most once.
 *
 * A shallow copy each time so a caller holding it in raw state sees a new
 * object when a language has been grafted onto the old one; the records inside
 * are the same records, which is what makes the grafting worth doing.
 */
export async function read(lang) {
  held ??= fetch(asset('data/codex.json'))
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
    .then(hydrate);
  const got = await held;
  if (lang && lang !== 'en') await speak(got, 'codex', lang).catch(() => {});
  return { ...got };
}

const indexed = new WeakMap();

/**
 * The codex's key for a thing the map named.
 *
 * The two files key items differently — the map by the lowercased English name
 * it reads out of the drop tables, the codex by the game's own key — and the
 * English name is what they have in common. All 1126 of the map's items find
 * their record this way.
 */
export function find(book, name) {
  let by = indexed.get(book);
  if (!by) {
    by = new Map();
    for (const [key, it] of Object.entries(book.items)) {
      const said = it.name || it.names?.en;
      if (said) by.set(said.replace(/\s+/g, ' ').trim().toLowerCase(), key);
    }
    indexed.set(book, by);
  }
  return by.get(name) ?? null;
}
