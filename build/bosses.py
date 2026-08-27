"""The things that drop items and are not places on the map.

The game's own `dropPlaces` mixes three kinds of answer together — a zone
("Act IX Zone 4-5"), a container ("Crystal Chest") and a boss ("Possessed
Luna") — and it writes the difficulty into the boss's name when a drop only
happens on the hardest one:

    Possessed Luna                    at any difficulty
    Possessed Luna (Inferno Only)     only on Inferno
    Amun Ra (Inferno Difficulty)      the same thing, said differently
    Son of Lucifer (Inferno)          and again

So Inferno does not have to be hunted for in the compiled code after all. It is
written down, in three spellings, in the field that says where a thing falls.
"""

import re


def game_list(path):
    """The game's own `[Bosses]` section, as `{key: english name}`.

    The key is what separates the two kinds. `e_damien_1` is the boss at the end
    of an act, standing in a dungeon the map already draws a marker for;
    `e_uberDamien_1` is the summoned fight, which has no place on the map at
    all. Reading the prefix is better than deciding from the outside which
    names sound like act bosses.
    """
    out, on = {}, False
    for line in open(path, encoding="utf-8"):
        row = line.rstrip().split("|")
        if not row or not row[0]:
            continue
        if row[0].startswith("["):
            on = row[0] == "[Bosses]"
            continue
        if on and len(row) > 1:
            out[row[0]] = row[1]
    return out


squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def classify(name, listed, already):
    """Leave a container or a machine where `collect` put it."""
    if already == "source":
        return "source"
    for _, (shown, kind) in SAME.items():
        if shown == name:
            return kind
    return _boss_kind(name, listed)


def _boss_kind(name, listed):
    """`uber`, `act`, or `other` for a name the drop tables use.

    The exact English name wins, because "Anubis" is both `e_anubis_1` and part
    of `e_uberAnubis_1` — whose English name is Amun Ra.
    """
    flat = squash(name)
    if name.lower() in ELSEWHERE:
        return "other"
    for key, english in listed.items():
        if squash(english) == flat:
            return _act_or_uber(key, name)
    for key in listed:
        if flat and flat in squash(key):
            return _act_or_uber(key, name)
    return "other"


def _act_or_uber(key, name):
    """`act` only for a boss the map has somewhere to put.

    The `e_uber` prefix separates the summoned fights from the rest, but the rest
    is not all act bosses — see ELSEWHERE. Anything keyed like one and missing
    from ACT_OF stays on the shelf rather than being given an act it has not
    earned; `report` says so at build time.
    """
    if key.startswith("e_uber"):
        return "uber"
    return "act" if name.lower() in ACT_OF else "other"

#: Which act each boss stands at the end of, and how that was settled.
#:
#: None of it is guessed from the names. The game says it four different ways
#: and they all agree:
#:
#:   the quest text     "Retrieve an Ancient Coin from Gurag in Act I", "Kill
#:                      Candy Grim Reaper in Act II", "the Christmas Tree from
#:                      Anubis in Act III", "the Christmas star from Damien in
#:                      Act IV" — said outright, in translationsQuest.csv.
#:   the arena names    The Soul Forge book is one page per act boss, each named
#:                      with the room it is in: page 11 from Gurag in The King's
#:                      Throne, 12 from The Reaper in The Death's Breach, 13 from
#:                      Anubis in The Tomb of the Fallen King, 14 from Damien in
#:                      The Altar of Lost Souls, 15 from The Karp King in The
#:                      Emperor's Chamber, the last from Satan in the Seventh
#:                      Layer of Hell. Those are, in order, the zone names of
#:                      Act_01_Boss through Act_06_Boss.
#:   the achievements   normalGurag, normalReaper, normalAnubis, normalDamien,
#:                      normalKarpKing, normalSatan, normalMevius, normalOdin —
#:                      in that order, which is act order.
#:   the rooms          Act_08_Boss is furnished with Odin_Pillar_01_obj,
#:                      Odin_Bridge_obj and Odin_Cutscene_obj, and Act_09_Boss
#:                      with Cthulhu_Boss_*. Odin and Cthulhu drop nothing the
#:                      tables list, so acts VIII and IX have no entry here.
ACT_OF = {
    "gurag": 1,
    "grim reaper": 2,
    "anubis": 3,
    "damien": 4,
    "karp king": 5,
    "satan": 6,
    "mevius": 7,
}

#: Keyed like an act boss, and not one.
#:
#: `e_grimbone_1` has no `e_uber` prefix, so the prefix rule called it an act
#: boss and the map would have had to find it an act. It has none: every line of
#: its lore puts it in Niflhel, and Niflhel_01_rm is a room with its own
#: summoning pentagram and no marker on the world map. It stays on the shelf,
#: which is where a fight the map cannot point at belongs.
ELSEWHERE = {"grimbone": "Niflhel"}

#: Places the map already draws a marker for, and only those.
#:
#: This used to match the word "Dungeon" anywhere, and "Battlefield", and
#: "Sheeponia" — none of which has a marker. So the Challenge Dungeon, the
#: Eternal Battlefield and Sheeponia itself fell down the gap between the map,
#: which does not draw them, and the shelves, which were told not to. The map
#: holds the act zones, their boss dungeons and the towns; everything else that
#: is not a boss belongs on a shelf.
ON_THE_MAP = re.compile(r"^Act\b", re.I)

#: Not a boss, but not a place on the map either: a container, a rift, a
#: machine. They belong beside the bosses rather than among them.
A_SOURCE = re.compile(
    r"Chest|Rift|Chaos Tower|Mimic|Chaos Pillar|Gamba|Dungeon|Battlefield|"
    r"Sheeponia|Wormhole|Grindfest|Labyrinth|Overworld", re.I)

#: Nothing at all. `Dev Command` is a developer's drop, and there is no Circle
#: of Hatred in the game — the room of that name is a place, not a fight.
NOT_REAL = re.compile(r"^\s*$|Dev Command|Circle of Hatred", re.I)

#: Two names for one fight.
#:
#: The drop tables use both, and the game's own `[Bosses]` table calls
#: `e_shadowreaper_1` "Shade of Death" while players call the encounter Uber
#: Reaper. Kept apart they were two half-empty lists of the same boss's loot.
#: The `e_uber` rule does not catch this one — its key has no such prefix — so
#: its kind is set outright.
SAME = {
    "uber reaper": ("Shade of Death (Uber Reaper)", "uber"),
    "shade of death": ("Shade of Death (Uber Reaper)", "uber"),
    # The encyclopedia calls this fight Son of Lucifer and the game's own boss
    # table calls it Fallen Damien. Apart, they were four items and one; the
    # game lists five for `e_uberDamien_1`, and four plus one is five.
    "uber damien": ("Uber Damien (Son of Lucifer)", "uber"),
    "son of lucifer": ("Uber Damien (Son of Lucifer)", "uber"),
    # Three of the ordinary chests share one loot table — the common, the
    # crystal and the golden list the same seven things, all seven in each — so
    # reading them apart is three times the work for no more knowledge. Shown as
    # the crystal one.
    #
    # The ruby chest is NOT one of them, and was merged in here on the strength
    # of the word "chest" alone. It has two items and shares neither with the
    # other three: Fulgurite says "Ruby Chests" on its own card in the game and
    # was being shown under a chest it does not come out of. The colossal chest
    # was always its own thing.
    "common chest": ("Crystal Chest", "source"),
    "crystal chest": ("Crystal Chest", "source"),
    "golden chest": ("Crystal Chest", "source"),
    # one fight, two spellings: the game's tables write it singular and the
    # snapshot plural
    "ruby chest": ("Ruby Chest", "source"),
    "ruby chests": ("Ruby Chest", "source"),
    # The King is how Sheeponia is reached, not a second way into it. The game
    # states one place for all three of his items — "Sheeponia", with "(Inferno
    # Only)" on two of them — and that is what a player is shown. "The Sheep
    # King" comes from somewhere else: the `exclusiveDrops` list on his object,
    # which holds his hide and his wool and not his crown. Kept apart, the shelf
    # carried both, and the one named after him was missing the crown that is
    # also named after him.
    #
    # Those lists cannot carry a source on their own. Sheeponia's other six
    # things are King Steve's, by their names, and his object has no exclusive
    # list at all — so read as an account of who drops what, they say Steve
    # drops nothing, which is plainly untrue.
    "the sheep king": ("Sheeponia", "source"),
}

#: the three ways the game says "only on Inferno"
INFERNO = re.compile(r"\s*\((?:Inferno(?: Difficulty| Only)?)\)\s*$", re.I)


def split(place):
    """A place, as (name, inferno-only)."""
    hard = bool(INFERNO.search(place))
    return INFERNO.sub("", place).strip(), hard


def collect(items):
    """`{boss: {"drops": [...], "inferno": bool}}`, rarest drops first.

    An item is listed under the boss whatever the difficulty; the flag rides on
    the item, because the same boss drops some things always and some only on
    Inferno. Wants `mark_inferno` to have run first.
    """
    bosses = {}
    for name, it in items.items():
        for place in it.get("places") or []:
            if NOT_REAL.search(place) or ON_THE_MAP.search(place):
                continue
            who, hard = split(place)
            if not who:
                continue
            # A name folded in from `exclusiveDrops` carries no difficulty of its
            # own, so it takes the item's: if the thing falls nowhere but on
            # Inferno, then killing this is no exception.
            if place in (it.get("_machinery") or []):
                hard = bool(it.get("inferno"))
            forced = SAME.get(who.lower())
            if forced:
                who = forced[0]
            row = bosses.setdefault(
                who,
                {"drops": {}, "inferno_only": True,
                 "kind": "source" if A_SOURCE.search(place) else "other"},
            )
            # Once per item, not once per listing. Merging the four ordinary
            # chests into one put things in twice, and a list with the same key
            # twice is one Svelte refuses to render at all — which is why the
            # crystal chest had no panel while everything beside it did. An item
            # is Inferno-only for this boss when every listing of it says so.
            was = row["drops"].get(name)
            row["drops"][name] = hard if was is None else (was and hard)
            if not hard:
                row["inferno_only"] = False

    for row in bosses.values():
        row["drops"] = sorted(
            ({"item": n, "inferno": hard} for n, hard in row["drops"].items()),
            key=lambda d: (-(items[d["item"]].get("tier") or 0),
                           items[d["item"]].get("rate") or 1 << 40),
        )
    return dict(sorted(bosses.items()))


def disagrees_about_inferno(items):
    """Items whose stated places do not agree on the difficulty.

    There is nothing wrong with such an item in principle — a thing can fall in
    one place at any difficulty and in another only on Inferno — but there was
    none in the game when this was written, and four items looked like this only
    because names from `exclusiveDrops` had been counted as places. So it is
    reported rather than assumed: if the game grows a real one, it should be a
    line in the build's output and not a silent change of a badge.
    """
    out = []
    for name, it in items.items():
        machinery = it.get("_machinery") or []
        stated = [p for p in it.get("places") or [] if p not in machinery]
        marks = [bool(INFERNO.search(p)) for p in stated]
        if any(marks) and not all(marks):
            out.append((name, stated))
    return out


def mark_inferno(items):
    """Flag the items that fall nowhere but on Inferno.

    Every place the game states for them carries the difficulty, so there is no
    other way to get one — which is worth saying on the item rather than making
    a reader compare a list of places.

    "States" is the whole of it. The places a player is shown come from the
    item's own `dropPlaces`, and those say "(Inferno Only)" when it applies. The
    names folded in from an enemy's or a chest's `exclusiveDrops` say nothing
    about difficulty — see merge_game — and silence is not a denial. Counting
    them was telling anyone reading that Sheep King's Hide drops at any
    difficulty, while the game's own card for it says Sheeponia (Inferno Only)
    and nothing else.

    Run before `collect`, which needs the answer.
    """
    n = 0
    for it in items.values():
        machinery = it.get("_machinery") or []
        stated = [p for p in it.get("places") or [] if p not in machinery]
        if stated and all(INFERNO.search(p) for p in stated):
            it["inferno"] = True
            n += 1
    return n
