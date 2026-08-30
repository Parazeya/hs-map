"""Fold the game's own drop table into the places the snapshot knows.

`game_drops.json` was read out of the compiled code — the item definitions'
own `dropPlaces`, recovered by disassembling the executable. It agrees with the
item table the site is otherwise built from, which is the point: the two
corroborate each other, and where that table is silent the game is not.

That table is itself mostly the game's own word now — the extractor decodes the
names, rarities, grades, identities and drop rates out of Hero_Siege.exe and
carries only the stats, sizes, types and chase rates from the datamined snapshot
it starts from. This file predates that and is kept because a second reading of
the same thing is still worth having.

Three sources existed only on the game's side — a Chest Drop, a Dungeon Chest,
and the Colossal Mimic — so adding by hand would have fixed those three and left
the next patch's additions to be noticed by a person. The union does not need
noticing.

Not every name it adds is a place, though, and the difference matters for
difficulty. The game keeps two lists: what an item's own `dropPlaces` says, which
is the line a player reads on the item and which carries "(Inferno Only)" when it
applies; and what an enemy or a chest carries in `exclusiveDrops`, which is the
machinery behind one of those lines and says nothing about difficulty at all.
Folding the second in as though it were the first is how Sheep King's Hide
stopped being Inferno-only: the game says "Sheeponia (Inferno Only)" and nothing
else, and beside it we had written "The Sheep King", which is not another way to
get it — it is the same way, named after the thing you kill. So a name that comes
from `exclusiveDrops` is added as a place and marked as machinery, and the
Inferno test steps over it.
"""

import json
import re

from bosses import INFERNO

#: The game writes at least one item name with a trailing space.
tidy = lambda s: re.sub(r"\s+", " ", s).strip().lower()

#: The game's boss table and the item definitions' `dropPlaces` spell the same
#: fights differently. Folding one into the other without this puts Gabriel on
#: the shelf twice, once under each name, each with half his loot.
AS_WRITTEN = {
    "fallen damien": "Uber Damien",
    "gabriel the fallen angel": "Gabriel",
    "gurag the fallen king": "Gurag",
    "the karp king": "Karp King",
    "colossal mimic": "Mimic",
}


base = lambda s: tidy(INFERNO.sub("", s))

#: The names a source's own `exclusiveDrops` list carries, out of its notes.
EXCLUSIVE = re.compile(r"exclusiveDrops list: (.+?)\. ")


def machinery(row):
    """The items this source is listed for by mechanism rather than by place."""
    m = EXCLUSIVE.search(row.get("notes") or "")
    return {tidy(n) for n in m.group(1).split(", ")} if m else set()


def fold(items, path, out=print):
    """Add to each item any place the game lists and the snapshot does not."""
    try:
        game = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        out("merge    no game_drops.json; places are the snapshot's alone")
        return 0, 0

    added = 0
    unknown = set()
    for source, row in game.items():
        by_mechanism = machinery(row)
        source = AS_WRITTEN.get(tidy(source), source)
        for raw in row.get("items") or []:
            name = tidy(raw)
            it = items.get(name)
            if it is None:
                unknown.add(raw.strip())
                continue
            places = it.setdefault("places", [])
            # Compared without the difficulty, so the plainer spelling never
            # displaces the more exact one. The game's table writes "Amun Ra"
            # where the snapshot writes "Amun Ra (Inferno Difficulty)", and
            # adding both told the page the item drops at any difficulty — which
            # quietly emptied the Inferno marks from twenty-five items down to
            # two.
            if not any(base(p) == base(source) for p in places):
                places.append(source)
                added += 1
                if name in by_mechanism:
                    it.setdefault("_machinery", []).append(source)

    out(f"merge    {added} place(s) the game knows and the snapshot did not")
    if unknown:
        out(f"         {len(unknown)} name(s) in the game's table match no item here: "
            f"{', '.join(sorted(unknown)[:6])}{' …' if len(unknown) > 6 else ''}")
    return added, len(unknown)
