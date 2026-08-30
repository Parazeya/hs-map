/**
 * Everything on these pages that is not a name the game gives, said in the
 * reader's language.
 *
 * The sentences this site writes itself used to be an object literal here and
 * rode in the JavaScript, all ten languages of them, to every reader — 8.6 KB
 * gzipped that an English reader had no use for, because `talk` hands English
 * straight back. They are in build/said.py now and go out inside `words`, which
 * is already split one file per language: English ships none of them and any
 * other language gets them in the file it was fetching anyway. See
 * build/langsplit.py.
 *
 * So `words` is now the whole dictionary — the game's own vocabulary and this
 * site's, merged at build time with the game's winning, which is the order this
 * function used to apply itself.
 */

/**
 * A drop place in the reader's language.
 *
 * Most are names — a boss, a zone, a chest — and the data carries what the game
 * calls them. Sixty of the hundred and twenty are not names at all but phrases
 * the drop tables compose: "Act I Zone 1-2", "Act V & VIII Dungeons". Those are
 * taken apart and put back together from words that are translated, which is
 * the only honest way to read them in another language.
 *
 * The difficulty in brackets stays as it is: "(Inferno Difficulty)" is the
 * tables' own note, not something the game gives a name to.
 */
export function places(lang, words, named) {
  const t = talk(lang, words);
  return (place) => {
    if (!place) return place;
    const hard = /\s*(\((?:Inferno[^)]*)\))\s*$/i.exec(place);
    const bare = hard ? place.slice(0, hard.index).trim() : place;

    // the whole string first, because the build names some of them bracket and
    // all — "Uber Reaper (Inferno Difficulty)" is a key it knows — and only
    // then the fight on its own
    // the bracket is the tables' own note about difficulty, not a name the game
    // gives, so it is translated here rather than looked up
    const note = hard
      ? ` (${t(hard[1].slice(1, -1).replace(/\b\w/g, (c) => c.toUpperCase()))})`
      : '';

    const whole = named?.(place);
    if (whole) return whole.includes('(') ? whole : whole + note;
    const said = named?.(bare);
    if (said) return said + note;

    // "Act <roman> <what><rest>", the shape the tables build
    const m = /^Act ([IVX]+(?:\s*&\s*[IVX]+)*)\s+(Boss Dungeons?|Dungeons?|Overworld|Zone)\b(.*)$/i
      .exec(bare);
    if (m) {
      const what = m[2].replace(/\b\w/g, (c) => c.toUpperCase());
      const out = `${t('Act')} ${m[1]} ${t(what)}${m[3]}`.replace(/\s+/g, ' ').trim();
      return out + (hard ? ` ${hard[1]}` : '');
    }
    return place;
  };
}

/**
 * One word or sentence in the reader's language.
 *
 * Anything the dictionary does not cover stays in English, which is a plain
 * answer rather than a missing one — and it is what a name the game never
 * translated does already.
 */
export function talk(lang, words) {
  return (text) => {
    if (!text || lang === 'en') return text;
    return words?.[text]?.[lang] ?? text;
  };
}
