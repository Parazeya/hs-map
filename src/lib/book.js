// The codex's table, for a page that is not the codex.
//
// The map's own file is 39 KB and the codex's is 145. A reader who never opens
// an item should not pay for the second, so it is fetched the first time one is
// opened and kept for the rest of the visit — the map page reads what a thing
// does out of the same file the codex page does, rather than out of a second
// copy of it cut down to size.

import { speak } from './lang.js';
import { asset } from './map.js';

export const recordsOf = (item) => item ? [item, ...(item.variants ?? [])] : [];
export const grantsOf = (item) => recordsOf(item).flatMap(record => [
  ...(record.grants ?? []), ...(record.reference_grants ?? []),
  ...(record.more ?? []).flatMap(mode => mode.grants ?? []),
]);
export const statsOf = (item) => recordsOf(item).flatMap((record) => [
  ...(record.stats ?? []), ...(record.more ?? []).flatMap((mode) => mode.stats),
]);

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
    for (const record of recordsOf(it)) {
      record.key = key;
      record.name ??= record.names?.en ?? it.name ?? it.names?.en ?? key;
      for (const row of [...(record.stats ?? []), ...(record.more ?? []).flatMap((m) => m.stats)]) {
        const said = d.stats[row.sid];
        if (!said) throw new Error(`Missing stat vocabulary entry ${row.sid}`);
        row.sid = said.sid;
        row.text = said.text;
        if (said.unit !== undefined) row.unit = said.unit;
      }
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
    .then(hydrate)
    .catch((error) => { held = null; throw error; });
  const got = await held;
  if (lang && lang !== 'en') await speak(got, 'codex', lang);
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
const folded = (name) => name?.normalize('NFC').replace(/[‘’]/g, "'").replace(/\s+/g, ' ').trim().toLowerCase();

export function resolveItem(book, name, key, recordId) {
  if (key) {
    const item = Object.hasOwn(book.items, key) ? book.items[key] : null;
    if (!item || (recordId && !recordsOf(item).some(record => record.record_id === recordId))) return null;
    return { key, recordId: recordId ?? null };
  }
  let by = indexed.get(book);
  if (!by) {
    by = new Map();
    for (const [key, it] of Object.entries(book.items)) {
      for (const record of recordsOf(it)) {
        const said = folded(record.name || record.names?.en);
        if (!said) continue;
        if (!by.has(said)) by.set(said, new Set());
        by.get(said).add(key);
      }
    }
    indexed.set(book, by);
  }
  const keys = by.get(folded(name));
  return keys?.size === 1 ? { key: [...keys][0], recordId: null } : null;
}

export const find = (book, name, key) => resolveItem(book, name, key)?.key ?? null;
