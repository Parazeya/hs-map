"""One file per language, because a reader reads one.

Every name in this project arrives from the game in eleven languages, and both
data files carried all eleven to everyone: 780 KB of the codex's 1987 KB was
`names` and `lore`, and map.json is the same shape for zones, bosses and drops.
Gzip does not save you from that — eleven languages in five alphabets share
almost nothing to fold together.

So each file is written twice over. The base keeps English and nothing else,
because English is the fallback everywhere: a name the game never translated
already falls back to it, and a reader who picks Finnish still needs it under
the six hundred stat lines Finnish has no word for. The other ten ride in their
own file, fetched only when someone picks that language.

A translation is found rather than listed: any dict whose keys are all language
codes is one, which over both files is exactly `names`, `lore`, `said` and the
rows of `words` and `types`, and nothing else. The side file mirrors the shape
of the base so the page can graft it back by walking the two together; a list
becomes an object keyed by index, so the sixty nodes that need nothing from a
given language cost nothing in it. See `graft` in src/lib/lang.js.

Nothing is mutated on the way through, and that is not fussiness: the build
hands the same translation dict to several places at once — `say.by_key` rows
end up in `words`, in `types` and on the bosses — so cutting one in place would
quietly empty the others.
"""

import gzip
import json


# A name with nothing in English — the site's own sentences are all of them —
# has no business in the English file at all, so it leaves no trace there and
# `graft` makes the record for it when the language arrives.
_GONE = object()


def _cut(node, langs):
    """`node` in English, and a mirror of everything else, or None for neither."""
    if isinstance(node, dict):
        if node and set(node) <= langs:
            rest = {k: v for k, v in node.items() if k != "en"}
            # tagged as a 1-tuple so the walk below can tell a finished
            # translation from more structure under it
            return ({"en": node["en"]} if "en" in node else _GONE), ((rest,) if rest else None)
        keep, mirror = {}, {}
        for k, v in node.items():
            said, m = _cut(v, langs)
            if said is not _GONE:
                keep[k] = said
            if m is not None:
                mirror[k] = m
        return keep, (mirror or None)
    if isinstance(node, list):
        keep, mirror = [], {}
        for i, v in enumerate(node):
            said, m = _cut(v, langs)
            # a list holds its shape: an entry that is only a name in another
            # language still has to keep its index
            keep.append({} if said is _GONE else said)
            if m is not None:
                mirror[str(i)] = m
        return keep, (mirror or None)
    return node, None


def _pick(mirror, lang):
    out = {}
    for k, v in mirror.items():
        if isinstance(v, tuple):
            if lang in v[0]:
                out[k] = v[0][lang]
        elif (m := _pick(v, lang)):
            out[k] = m
    return out


def write(out, langs, path):
    """Write `path` in English and `path.stem.<lang>.json` for the other ten.

    Returns the files written, English first, for the build's own report.
    """
    english, mirror = _cut(out, set(langs))
    made = []
    for name, doc in [(path.name, english)] + [
            (f"{path.stem}.{lang}{path.suffix}", _pick(mirror or {}, lang))
            for lang in langs if lang != "en"]:
        p = path.with_name(name)
        p.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")
        made.append(p)
    return made


def over_the_wire(path):
    """KB gzipped, which is what a reader actually waits for."""
    return len(gzip.compress(path.read_bytes(), 9)) // 1024
