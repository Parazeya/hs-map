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
}

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

    def vocab(self):
        """The small words, keyed by their English, for the pages to look up."""
        out = {}
        for english, key in VOCAB.items():
            said = self.by_key.get(key)
            if said:
                out[english] = said
        return out
