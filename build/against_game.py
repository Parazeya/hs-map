"""Check what the site will show against what the game itself says.

`game_drops.json` was recovered from the compiled code — the item definitions'
own `dropPlaces`, read out of the executable rather than out of a datamined
snapshot. It agrees with the snapshot the site is otherwise built from, which is
the point: the two corroborate each other, and every gap that has turned up so
far has been one fight split across two names.

    Uber Damien      4 items       Fallen Damien      5 items
    Son of Lucifer   1 item                            ↑ the same fight

So this compares the two source by source. It knows about the decisions taken
deliberately — the four ordinary chests shown as one, the act bosses left to
their markers on the map — so that what it prints is a surprise rather than a
recital of things already settled.
"""

import json
import re

squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

#: the three ways the game says "only on Inferno"; stripped before comparing
INFERNO = re.compile(r"\s*\((?:Inferno(?: Difficulty| Only)?)\)\s*$", re.I)

#: Two spellings of one thing. The game's boss table and the item definitions'
#: `dropPlaces` do not agree on how to write a name.
SAME_THING = {
    "fallendamien": "uberdamien",
    "gabrielthefallenangel": "gabriel",
    "guragthefallenking": "gurag",
    "thekarpking": "karpking",
    "colossalmimic": "mimic",
    "sonoflucifer": "uberdamien",
    "uberreaper": "shadeofdeath",
}

#: Shown under another name on purpose: the four ordinary chests share a loot
#: table, so they are one row. The dungeon chest and the colossal one do not,
#: and stand on their own — listing them here said they were covered when they
#: were not, which is exactly the kind of quiet the check exists to break.
#: `thesheepking` is the enemy's `exclusiveDrops` list and `sheeponia` is the
#: place the game states for the same things — see bosses.SAME. Its two items are
#: among Sheeponia's nine, so folding the key here checks that they are still
#: shown rather than excusing them from the check.
MERGED = {"thesheepking": "sheeponia",
          "commonchest": "crystalchest", "goldenchest": "crystalchest"}

#: Left out on purpose. `Dev Command` is a developer's drop, and there is no
#: Circle of Hatred in the game — the room of that name is a place, not a fight.
DROPPED = {"devcommand", "circleofhatred", "thecircleofhatred"}


def report(game_path, bosses, items=None, out=print):
    try:
        game = json.loads(game_path.read_text(encoding="utf-8"))
    except OSError:
        return

    known = {n.lower() for n in (items or {})}

    mine = {}
    for name, row in bosses.items():
        # a merged entry answers to every name in it: "A (B)" is both A and B
        for part in re.split(r"\s*[()]\s*", INFERNO.sub("", name)):
            if part.strip():
                mine.setdefault(squash(part), set()).update(d["item"] for d in row["drops"])

    gaps = []
    for source, row in sorted(game.items()):
        if source.startswith("Act "):
            continue
        key = squash(INFERNO.sub("", source))
        key = SAME_THING.get(key, key)
        if key in DROPPED:
            continue
        key = MERGED.get(key, key)

        # an item with no rarity is not in the site's catalogue at all, so its
        # absence says nothing about this source
        want = {i.strip().lower() for i in row.get("items") or []}
        want = {i for i in want if i and (not known or i in known)}
        if not want:
            continue

        got = mine.get(key)
        if got is None:
            gaps.append(f"{source} is not shown at all ({len(want)} items)")
        elif want - got:
            gaps.append(f"{source} also drops {sorted(want - got)}")

    if gaps:
        out(f"check    {len(gaps)} difference(s) from the game's own tables:")
        for g in gaps[:12]:
            out(f"         {g}")
    else:
        out("check    agrees with the game's own tables")
