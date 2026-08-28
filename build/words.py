"""What the game calls things, in the eleven languages it ships.

The pages name three kinds of thing: places, which `translationsZone.csv`
already covered; items and the sources they fall from; and the small vocabulary
around them — a rarity, a slot, the word "Level".

All of it is the game's own. Nothing here invents a translation: a name the game
does not carry stays in English and is counted, so the gap is a number in the
build's output rather than a surprise on the page.

The join is on the English text, because that is what the drop tables hold — they
name a boss "Uber Damien (Son of Lucifer)" where the game's own table says
"Fallen Damien". Where the two disagree, ALSO says so.
"""

import re

#: The eleven, in the order every translations file lists them.
LANGS = ["en", "fi", "pt", "ru", "zh", "ja", "ko", "de", "fr", "sp", "pl"]

squash = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())

#: The drop tables' spelling, and the game's own.
#:
#: Some are titles the tables drop — the game calls Gurag "Gurag the Fallen King"
#: — and some are a different name for one fight, which is the same disagreement
#: `merge_game.AS_WRITTEN` and `bosses.SAME` already know about from the other
#: side. Kept here in the tables' direction, which is the one a lookup needs.
ALSO = {
    "gurag": "Gurag the Fallen King",
    "gabriel": "Gabriel the Fallen Angel",
    "karp king": "The Karp King",
    "uber damien (son of lucifer)": "Fallen Damien",
    "shade of death (uber reaper)": "Shade of Death",
    "eternal battlefield": "Eternal Battle Field",
    "grim reaper": "Grim Reaper",
    "the sheep king": "The Sheep King",
    # the tables drop the second name where the game keeps only the other one
    "uber reaper": "Shade of Death",
    "uber damien": "Fallen Damien",
}

#: A stat this project words itself, and the key the game words it under.
#:
#: For the handful the matching below cannot reach, because the two describe the
#: same thing in different words: the snapshot's `socketed_flat` against the
#: game's `sockets`, its `chance_when_striking` against `when_strike`.
STAT_NAMED = {
    "socketed_flat": "sockets",
    "attacks_per_second_base": "attacks_per_second",
    "chance_when_striking": "when_strike",
    "chance_when_attacking": "when_attacking",
    "chance_when_casting": "when_casting",
    "chance_when_struck": "when_struck",
    "chance_after_blocking": "when_blocking",
    "chance_after_each_kill": "when_kill",
    "cooldown_recovery_percent": "stat_cooldown_reduction",
}

#: Words that say how a number is meant rather than what it is, on either side.
STAT_NOISE = {"increased", "total", "chance", "for", "a", "to", "by", "the", "of",
              "percent", "flat", "base", "none", "p", "t"}

#: What the snapshot shortens, and what the game spells out.
STAT_LONG = {"dmg": "damage", "crit": "critical", "aoe": "area", "cd": "cooldown",
             "hp": "life", "mp": "mana", "res": "resist", "resistances": "resist",
             "resistance": "resist"}


#: The vocabulary the pages need beyond names, and the key the game keeps it
#: under. Only what the game actually has: `stats`, `lore` and `fit` are not in
#: any of its files, so they are not here and are translated on the page instead.
VOCAB = {
    "Satanic": "satanic",
    "Satanic Set": "satanic_set",
    "Heroic": "heroic",
    "Angelic": "angelic",
    "Unholy": "unholy",
    "Runeword": "runeword",
    "Common": "common",
    # The rest of the scale, which the codex offers as filters and showed in
    # English beside seven Russian ones. The game's own word for "Superior" in
    # Russian is "Начальство", which is a word about people rather than gear —
    # but it is the word a Russian player is shown in the game, and inventing a
    # better one here would leave the two disagreeing.
    "Mythic": "mythic",
    "Rare": "rare",
    "Superior": "superior",
    # what the phone's one column folds the filters behind
    "Filters": "filters",
    "Rarity": "rarity",
    "Type": "type",
    "Level": "level",
    "Drop": "drop",
    "Chance": "chance",
    "Search": "search",
    "Items": "items",
    "Set Bonus": "set_bonus",
    "Close": "close",
    "Back": "back",
}


def read(folder):
    """Every translations file in the game folder, as one index.

    Returns `(by_key, by_english)`. A key is unique; an English word is not, so
    the first file to claim one keeps it — the files are read in a fixed order so
    that is at least the same answer every time.
    """
    by_key, by_english = {}, {}
    for path in sorted(folder.glob("translations*.csv")):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("|")
                if not parts or not parts[0] or parts[0].startswith("["):
                    continue
                said = {LANGS[i]: parts[1 + i].strip()
                        for i in range(min(len(LANGS), len(parts) - 1))
                        if parts[1 + i].strip()}
                if not said.get("en"):
                    continue
                by_key.setdefault(parts[0], said)
                by_english.setdefault(squash(said["en"]), said)
    return by_key, by_english


class Words:
    """A lookup from English to the eleven, with a tally of what it could not do."""

    def __init__(self, folder):
        self.by_key, self.by_english = read(folder)
        self.missed = set()

    def of(self, english):
        """What the game calls this, or None — and remember the misses."""
        if not english:
            return None
        # a difficulty in brackets is ours to keep, not the game's to translate
        bare = re.sub(r"\s*\((?:Inferno[^)]*)\)\s*$", "", english, flags=re.I).strip()
        for text in (bare, ALSO.get(bare.lower())):
            if text:
                said = self.by_english.get(squash(text))
                if said:
                    return said
        self.missed.add(english)
        return None

    @staticmethod
    def _toks(text):
        """A name reduced to what it is about, so two spellings can be compared."""
        out = set()
        for w in re.split(r"[^A-Za-z0-9]+", text or ""):
            w = w.lower()
            if not w or w in STAT_NOISE:
                continue
            w = STAT_LONG.get(w, w)
            if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
                w = w[:-1]          # the game pluralises where the snapshot does not
            out.add(w)
        return frozenset(out)

    def stats(self, sids):
        """`{sid: {lang: text}}` for the stats the game has a name for.

        The snapshot's `sid` appears in no file the game ships, so this is a
        join on meaning: both sides are reduced to the words that say what the
        stat is about — dropping "increased", "total", "chance", the unit — and
        matched exactly, then, failing that, on three quarters of their words.

        What is left keeps the English this project reads off the identifier,
        which is a plain answer rather than a wrong one.
        """
        by_key, by_text = {}, {}
        for key, said in self.by_key.items():
            if key.startswith("stat_") or key in STAT_NAMED.values():
                by_key.setdefault(self._toks(key[5:] if key.startswith("stat_") else key), key)
                by_text.setdefault(self._toks(said["en"]), key)

        def best(t):
            top, score = None, 0.0
            for table in (by_key, by_text):
                for keys, key in table.items():
                    if keys:
                        o = len(t & keys) / len(t | keys)
                        if o > score:
                            top, score = key, o
            return top if score >= 0.75 else None

        out = {}
        for sid in sids:
            t = self._toks(sid)
            key = STAT_NAMED.get(sid) or by_key.get(t) or by_text.get(t) or best(t)
            said = self.by_key.get(key) if key else None
            if said:
                out[sid] = said
        return out

    def vocab(self):
        """The small words, keyed by their English, for the pages to look up."""
        out = {}
        for english, key in VOCAB.items():
            said = self.by_key.get(key)
            if said:
                out[english] = said
        return out
