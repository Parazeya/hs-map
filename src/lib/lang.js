// The other ten languages, fetched one at a time.
//
// Both data files ship English only — see build/langsplit.py for why and for
// the shape of the side files. Each of those mirrors the base: where the base
// holds a name, the side file holds a string, and a list is an object keyed by
// index so the records that need nothing cost nothing.
//
// So grafting is walking the two together. It writes into the records the page
// is already holding, which is the point: a name that arrives becomes
// `it.names.ru` beside the `it.names.en` that was always there, and every
// `names[lang] || names.en` in the components keeps working unchanged.

import { asset } from './map.js';

// Which languages are already on the records, per file. Keyed by the file and
// not by the data, because a page holds one of each and the object it holds is
// a Svelte proxy after the first paint and the bare object before it.
const on = new Map();

function graft(base, side, lang) {
  for (const key in side) {
    const said = side[key];
    // `??=` because a name the game only has in other languages — every
    // sentence this site writes itself is one — is absent from the English
    // file rather than sitting there empty
    if (typeof said === 'string') (base[key] ??= {})[lang] = said;
    else graft(base[key], said, lang);
  }
}

/**
 * Make `data` speak `lang`, fetching its names if this is the first time.
 *
 * Resolves once the records carry the language; the caller switches to it only
 * then, so the page never blanks — it stays in the language it was in while the
 * fifty kilobytes are on the wire. English is already there and costs nothing.
 */
export async function speak(data, file, lang) {
  let done = on.get(file);
  if (!done) on.set(file, (done = new Set(['en'])));
  if (done.has(lang)) return;

  const res = await fetch(asset(`data/${file}.${lang}.json`));
  if (!res.ok) throw new Error(`${file}.${lang}.json: ${res.status} ${res.statusText}`);
  graft(data, await res.json(), lang);
  done.add(lang);
}
