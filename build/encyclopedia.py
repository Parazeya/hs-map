"""Every item the game defines, with what it does, written for a reader.

The map answers "what falls here". This answers "what is this thing", which is a
different question and needs different parts of the same two sources:

  the snapshot   e:\\Workspace\\HeroSiege\\tools\\data\\helper\\items.json — the
                 stats, their ranges, the level it wants, the space it takes in
                 a bag, its rarity and tier
  the game       translationsItem.csv — the name and the lore, in the eleven
                 languages it ships

The stat lines are worded here rather than looked up, because there is nothing to
look up: `sid` is the snapshot's own naming and appears nowhere in the game's
files. It is regular enough to read mechanically — 295 of the 305 in use come out
as plain English by splitting on the underscores and reading the last word as a
unit — and the handful that do not are named below.
"""

import json
import re

#: The last word of a `sid` is how the number is meant, not part of its name.
UNIT = {
    "percent": "%",
    "flat": "",
    "base": "",
    "none": "",
    "chance": "%",
}

#: Words the snapshot shortens, and what they are short for.
LONG = {
    "dmg": "damage",
    "aoe": "area",
    "cd": "cooldown",
    "exp": "experience",
    "crit": "critical",
    "hp": "life",
    "mp": "mana",
}

#: The ones the rule gets wrong or cannot read at all.
#:
#: Six are bare numbers — 104, 108, 110, 259, 260, 267 — one row each, and they
#: name nothing. They are shown as they are rather than dressed up: an unread
#: line that says so is better than one that invents a meaning.
SAID = {
    "increased_experience_gain_below_100_percent": ("Increased experience gain below level 100", "%"),
    "codex_affix_2": ("Second codex affix", ""),
    "codex_affix_3": ("Third codex affix", ""),
    "codex_affix_4": ("Fourth codex affix", ""),
    "codex_duration": ("Codex duration", ""),
    "codex_experience_percent": ("Codex experience", "%"),
    "codex_packSize": ("Codex pack size", ""),
    "codex_possible_zones": ("Codex zones", ""),
    "enjoyer_tracker_stat": ("Enjoyer tracker", ""),
    "grant_spell": ("Grants the spell", ""),
    "grant_aura": ("Grants the aura", ""),
    "grant_aura_holder_only": ("Grants the aura, to its holder only", ""),
    "grant_subskills": ("Grants the sub-skills", ""),
    "socketed_flat": ("Sockets", ""),
    "all_skills_flat": ("To all skills", ""),
    "all_skills_flat_class": ("To all skills of a class", ""),
    "cannot_be_frozen_none": ("Cannot be frozen", ""),
    "half_freeze_duration_none": ("Half freeze duration", ""),
    "double_jump": ("Double jump", ""),
}

#: A stat the snapshot numbers but does not name.
#:
#: Stat 20 sits on 399 items and no item carries both it and `socketed_flat`,
#: which is the same thing coming from the snapshot's named half. Its values
#: are pairs like 2-4, 0-3 and 4-6 — nothing else on an item is bounded that
#: way — and the game draws it as `Sockets (4) [2-4]` on the very item whose
#: reading raised the question. So the two are one stat under two names, and
#: this gives the numbered half the name the other half already has.
BY_ID = {20: "socketed_flat"}

#: An unread stat: the snapshot gives a number for a name it does not explain.
UNREAD = re.compile(r"^\d+$")

#: What a runeword can be made in, by `runewordItemType`.
#:
#: Read off the data rather than assumed: across all hundred runewords the number
#: and the item's own `type` agree without a single exception — every 0 is a
#: Helmet, every 3 a Weapon — and the two that carry a pair, [3, 1] and [3, 6],
#: are the two whose type is "Unknown Type", which is the snapshot's way of
#: saying it goes in either.
#:
#: `runewordWeaponType` is left alone. It is a list of numbers with nothing to
#: check them against, and a guess about which weapon a runeword fits is worse
#: than saying nothing.
BASE = {0: "Helmet", 1: "Body Armor", 2: "Boots", 3: "Weapon", 6: "Shield",
        11: "Consumable"}

#: Which weapon a runeword goes in, by `runewordWeaponType`.
#:
#: The order is the game's own. `translationsItem.csv` lists its item types in
#: one run, and sixteen of them are weapons — sword through throwing — which is
#: exactly the range these numbers cover.
#:
#: Checked rather than assumed, three ways. Only the weapon bases carry the
#: field at all: every runeword made in a helmet, armour, boots or a shield has
#: it empty. Read this way the lists group by class — True Aim, Arcanum, Epilogue
#: and Deus Ex Machina allow a bow and a gun and nothing else, Sovereignty and
#: Flowing Sands the casters, Harvester and Brutality the melee — where a wrong
#: offset would scatter them. And of the forty runewords carrying a two-handed
#: stat list, thirty-nine allow a weapon that can be held in two hands.
WEAPON = ["Sword", "Dagger", "Mace", "Axe", "Polearm", "Claw", "Chainsaw",
          "Staff", "Cane", "Wand", "Book", "Spellblade", "Bow", "Gun", "Vial",
          "Throwing"]

#: The same thing has different numbers in different bases, and the snapshot
#: keeps a list per base. `stats` is the plain one; these are the rest, worded.
#:
#: Fifty-six of the hundred runewords carry only `stats_armor`, so an item read
#: from `stats` alone had no stats at all and the page said so — wrongly.
VARIANT = {
    "stats_2h": "two-handed",
    "stats_armor": "in armour",
    "stats_socket": "per socket",
    "stats_damageType": "by damage type",
    "stats_random": "random",
}


def phrase(sid):
    """A `sid` as a line a person can read, and the unit its numbers carry."""
    if sid in SAID:
        return SAID[sid]
    if UNREAD.match(sid or ""):
        return (f"Unnamed stat {sid}", "")
    parts = [p for p in (sid or "").split("_") if p]
    unit = ""
    if parts and parts[-1] in UNIT:
        unit = UNIT[parts[-1]]
        parts = parts[:-1]
    words = [LONG.get(p, p) for p in parts]
    if not words:
        return (sid or "?", unit)
    return (" ".join(words).capitalize(), unit)


def stat_line(s):
    """One stat as `{sid, text, unit, min, max, of}`.

    `min2`/`max2` are the second number a two-part stat carries — "5% chance to
    cast Shadowflames at level 1 to 3" is one stat with two ranges — and the
    named fields beside them say which spell, class or range it is about.
    """
    # An Unholy slot is not a stat with a value. The number the snapshot
    # records against it is the pool the game rolls from — `LoadRandomSatanicStat`
    # switches on it, and a stored 4 means "pool 1, 2 or 3" — so it is written
    # as a pool and never as a magnitude. See build/unholy.py.
    if s.get("sid") == "unholy_none":
        return {"sid": "unholy_none", "pool": s.get("min1"), "text": "Unholy"}
    if s.get("sid") is None and s.get("id") in BY_ID:
        s = dict(s, sid=BY_ID[s["id"]])
    out = {
        "sid": s.get("sid"),
        "min": s.get("min1"),
        "max": s.get("max1"),
    }
    text, unit = phrase(s.get("sid"))
    out["text"] = text
    if unit:
        out["unit"] = unit
    # A relic's stat is not rolled but climbed: the item carries the ten values
    # the stat takes at the relic's ten levels, and no min or max at all, so
    # without this those lines printed their name and no number.
    if out["min"] is None and s.get("values"):
        ladder = [v for v in s["values"] if v is not None]
        if ladder:
            out["min"], out["max"], out["rank"] = ladder[0], ladder[-1], 1
    if s.get("min2") is not None or s.get("max2") is not None:
        out["min2"] = s.get("min2")
        out["max2"] = s.get("max2")
    for key, field in (("Spell Name", "spell"), ("Class Name", "cls"),
                       ("Spell Range", "range")):
        if s.get(key) is not None:
            out[field] = s[key]
    return {k: v for k, v in out.items() if v is not None}


def text_rows(path):
    """`translationsItem.csv` as `{key: [each language]}`."""
    rows = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("|")
            if parts and parts[0] and not parts[0].startswith("["):
                rows[parts[0]] = parts[1:]
    return rows


#: What the engine leaves in a record that never states a drop rate. It is not
#: a chance of one in fifty million; it is the game's way of saying it does not
#: fall out of the world at all — from a boss, a chest or a tower instead. The
#: tracker's own tables already refuse it; this file was reading the snapshot's
#: raw number as a fallback and printing it, on 701 of 1,728 items.
#:
#: Exactly this number, not everything above it: three items are written rarer
#: than the default and mean it — 50,696,969, 111,111,111 and 999,999,999.
NO_DROP = 50_000_000


def plain(rate):
    """A drop rate, or None where the number is the engine's shrug."""
    return None if rate == NO_DROP else rate


def out_of_key(tkey, kind):
    """`w_throwing_darkmoon_deck` read as "Darkmoon Deck"."""
    parts = [p for p in (tkey or "").split("_") if p]
    while parts and (len(parts[0]) == 1 or parts[0].lower() == str(kind).lower()):
        parts.pop(0)
    return " ".join(p[:1].upper() + p[1:] for p in parts)


def weapons(row):
    """The weapons a runeword may be made in, named."""
    got = row.get("runewordWeaponType")
    if not isinstance(got, list):
        return []
    return [WEAPON[n - 1] if 1 <= n <= len(WEAPON) else str(n) for n in got]


def variants(it):
    """The stat lists that are not the plain one, each with what it depends on.

    Two shapes. Most are a flat list under a name that says which base it is
    for — `stats_2h`, `stats_armor` — and fifty-six of the hundred runewords
    keep theirs only under `stats_armor`, so reading `stats` alone said they did
    nothing at all.

    `stats_socket` nests instead: each row names a gem and carries the list that
    gem grants, so King's Garb has one for the Pristine Amethyst and another for
    the Pristine Ruby. Four items are written that way.
    """
    out = []
    for field, when in VARIANT.items():
        rows = it.get(field) or []
        if not rows:
            continue
        if all(isinstance(r, dict) and r.get("stats") for r in rows):
            for r in rows:
                named = r.get("ID")
                out.append({
                    "when": f"with a {named}" if named else when,
                    "stats": [stat_line(s) for s in r["stats"] if s.get("sid") or s.get("id") in BY_ID],
                })
        else:
            out.append({"when": when,
                        "stats": [stat_line(s) for s in rows if s.get("sid") or s.get("id") in BY_ID]})
    return [v for v in out if v["stats"]]


def sockets(row, by_name, tidy):
    """A runeword's recipe: what goes in it, in order, as item keys.

    `runewordSockets` names them the way the game does — its runes are renamed
    from the ones players know, so Eld is "Old" and Ith is "Uth" — and fifteen of
    the fifty-two names are not runes at all but orbs. Both are ordinary items
    with pages and icons of their own, so the recipe is stored as keys and the
    page looks the rest up.
    """
    out = []
    for name in row.get("runewordSockets") or []:
        key = by_name.get(tidy(name))
        out.append({"name": name, "key": key} if key else {"name": name})
    return out


#: The stat a potion states its talent in, and the one that states the range
#: of levels it grants it at. The game writes "+[1-5] to Drunken Kung Fu" out
#: of the pair.
GRANTS, GRANT_LEVELS = "singular_skill", "stat_random_skill"
#: The other way an item says what it grants: the spell by name, in a field
#: beside the stat. Runewords are written this way and a few uniques with them,
#: and Torment names three this way in one go.
BY_NAME = "grant_spell"

def flat(text):
    """A name with nothing in it but letters and digits, for comparing two."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def camel(key):
    """`consumable_bottle_of_sake` -> `bottleOfSake`, which is what the talent
    populators call it."""
    parts = key.split("_", 1)[1].split("_") if "_" in key else [key]
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


#: Where an item's key and its talent's key parted.
#:
#: The two are the same word everywhere else, so each of these is a rename that
#: happened on one side only: a typo (Basiliks for Basilisks, Vajdra for
#: Vadjra, Almighty for Allmighty), a word dropped from the end, or an
#: ampersand spelled out. Each names a talent no other item claims, and the
#: spelling on the right is the game's own — this is a list of what the game
#: calls things, not a guess at what it might have meant.
RENAMED = {
    "relic_thiefsGlove": "relicThievesGlove",
    "relic_basilisksTooth": "relicBasiliksTooth",
    "relic_theAllmightyFedora": "relicTheAlmightyFedora",
    "relic_vadjra": "relicVajdra",
    "relic_fireIce": "relicFireAndIce",
    "relic_rainbowGate": "relicRainbow",
    "relic_squishyTheSuicidalPig": "relicSquishy",
    "relic_angelStaffOfApocalypse": "relicAngelStaff",
    "relic_daPlayersDislocatedHead": "relicDaPlayer",
    "relic_shocker3000": "relicShocker",
}


def called(key):
    """Every name the talent an item grants could be filed under.

    A relic keeps the word: `relic_shrunkenHead` grants `relicShrunkenHead`,
    where a potion drops it — `consumable_bottle_of_sake` grants `bottleOfSake`.
    Eighty-two relics answer to the second spelling and none to the first, and
    two more drop the article the item keeps.
    """
    got = [camel(key)]
    if key.startswith("relic_"):
        parts = key.split("_", 1)[1].split("_")
        stuck = lambda ps: "relic" + "".join(p[:1].upper() + p[1:] for p in ps)
        whole = stuck(parts)
        got.append(whole)
        # `relic_theHolyGrail` grants `relicHolyGrail`: the item keeps the
        # article and the talent does not.
        if whole.startswith("relicThe"):
            got.append("relic" + whole[len("relicThe"):])
    if key in RENAMED:
        got.append(RENAMED[key])
    return got


def fits(number, got, pins):
    """Whether the talent an item's key names can be the one its number means.

    A key can name a talent by coincidence rather than by grant: the ring
    Absolute Zero is spelled like the Jotunn ultimate and does not give it. The
    item states a number as well, and the two together settle it — the
    difference between the number and where that talent sits has to lie between
    what the anchors either side of it measure, and for the ring it is two
    hundred and fifty-one where they allow one to three.

    Relics are not asked. Their numbers and the order the talents are defined in
    have come apart — whole runs of relics are numbered twenty-six places from
    where they are made — while their keys still name their talents exactly,
    agreeing with the planner on seventy-three of the seventy-four it also names.
    """
    if number is None or not got.get("id"):
        return True
    drift = number - got["id"]
    below = [d for at, d in pins if at <= number]
    above = [d for at, d in pins if at >= number]
    return drift >= (below[-1] if below else 0) and (not above or drift <= above[0])


def pinned(raw_items, talents):
    """How far the talents' numbering runs from ours, where an item says so.

    An item names the talent it grants by a number, and the number is its place
    in the order the game defines them. The extractor numbers them the same way
    and the two agree for the first five hundred and fifty — but past that it
    makes three fewer records than the game, and each one missed puts every
    number after it out by one more.

    An item whose own key spells the talent out says both things at once, so it
    measures the difference at its own number. Measured rather than written
    down because it moves: every repair to the populator reader changes how
    many records it makes.

    The relics are left out of it although their keys name their talents too.
    What they show is not a count running behind but an order running
    differently: whole runs of them sit twenty-six places later than the game
    puts them and others twenty earlier, so past where the potions reach there
    is no single difference to measure and the number is not read at all.
    """
    seen = []
    for row in raw_items:
        key = (row.get("metadata") or {}).get("tkey")
        if not key:
            continue
        number = next((s.get("min1") for s in row.get("stats") or []
                       if s.get("sid") == GRANTS), None)
        got = talents.get(camel(key).lower())
        if number is not None and got and got.get("id"):
            seen.append((number, number - got["id"]))
    seen.sort()
    # The difference only grows: a record can be missed, never invented. An
    # anchor that says otherwise is not measuring the same thing — Absolute
    # Zero is a ring whose key spells a Jotunn talent it does not grant — and
    # is dropped rather than left to poison the numbers around it.
    kept = []
    for at, drift in seen:
        while kept and kept[-1][1] > drift:
            kept.pop()
        kept.append((at, drift))
    return kept


def at_number(n, by_number, pins):
    """The talent an item's number names, where the numbering can be trusted.

    Trusted means bracketed: an anchor at or below the number and another at or
    above it, both saying the same thing. Below the first anchor there is
    nothing to bracket against, but nothing can be missing either while that
    anchor still reads nought. Above the last one the difference is unbounded,
    and the number is left on the card as a number.
    """
    above = [(at, d) for at, d in pins if at >= n]
    if not above:
        return None
    below = [(at, d) for at, d in pins if at <= n]
    drift = below[-1][1] if below else 0
    if drift != above[0][1]:
        return None
    return by_number.get(n - drift)


def granted(tkey, stats, talents, told, by_number, by_spoken, pins, said):
    """What the item does, out of the talents it grants — a list, because some
    items grant several.

    Asked four ways, in the order of how much each one knows.

    The game spells the spell out itself on a hundred-odd items, in a field
    beside the stat that grants it, and Torment names three that way in one go.
    A potion or a relic says which talent it is in its own key —
    `consumable_bottle_of_sake` grants `bottleOfSake` — which is exact for the
    same reason. Then the number, where `at_number` can vouch for the numbering.
    A name somebody has read off the tooltip comes last: where it and the number
    both answer they disagree sixty times over, and the third witness sides with
    the number on fifty-nine of them.
    """
    if not talents:
        return None
    out = []
    for line in [s for s in stats if s.get("sid") == BY_NAME and s.get("spell")]:
        got = by_spoken.get(flat(line["spell"]))
        if got:
            stats.remove(line)
            out.append(spoken(got, [line.get("min"), line.get("max")], said))

    marks = [s for s in stats if s.get("sid") == GRANTS]
    # The item's own key spells out one talent and only one, so it answers only
    # where the item grants only one. Shadow Carver and the Witch's Wand grant
    # two, and there the number is the only thing that tells them apart.
    alone = len(marks) <= 1
    by_key = None
    # A key is asked only where the game has named nothing itself. It can name
    # a talent by coincidence — the runeword Martyr is spelled like the talent
    # `martyr` and grants Thorn's Aura, which the item says in as many words.
    if alone and not out and not any(s.get("spell") for s in stats):
        by_key = next((talents[k] for k in (c.lower() for c in called(tkey)) if k in talents), None)
        told_number = marks[0].get("min") if marks else None
        if by_key and not tkey.startswith("relic_") and not fits(told_number, by_key, pins):
            by_key = None

    # A relic states no number at all — the ability is the relic and its key
    # says which — so twenty-three of them are named here and nowhere else.
    if not marks:
        if by_key:
            out.append(spoken(by_key, None, said))
        return out or None

    for named in marks:
        got = by_key
        if not got and named.get("min") is not None:
            got = at_number(named["min"], by_number, pins)
        if not got and alone and not out:
            got = (told or {}).get(tkey)
        if not got:
            continue
        # The level it is granted at is a roll like any other, stated under the
        # random-skill mark that follows the talent it belongs to. A few items
        # state it as a range of skill levels with no name on it instead, which
        # is the only line on them that carries one.
        after = stats[stats.index(named) + 1:]
        levels = next((s for s in after
                       if s.get("sid") == GRANT_LEVELS and s.get("max") is not None), None)
        if levels is None and alone:
            levels = next((s for s in stats
                           if s.get("sid") in ("all_talents", "all_skills_flat")
                           and s.get("max") is not None), None)
            # That range is how many levels of the granted talent the item
            # rolls, not a bonus to every skill the character has. Left in the
            # stat list it reads as the second, and the card says both.
            if levels is not None:
                stats.remove(levels)
        # and the number itself is plumbing: the game prints the talent's name
        # in its place, which is now what this returns
        stats.remove(named)
        out.append(spoken(got, [levels.get("min"), levels.get("max")] if levels else None, said))
    return out or None


def spoken(got, levels, said):
    """A talent as the block an item's card shows for it."""
    def line(e):
        # The mark after the number is either punctuation the game writes out —
        # a per cent sign — or a key it looks up, and `tal_seconds` is "s" in
        # English and "с" in Russian. Printed raw it read "40tal_seconds".
        mark, unit = e["mark"], said(e["mark"]) if e["mark"].startswith("tal_") else None
        got_line = {"start": e["start"], "per": e["per_level"],
                    "mark": "" if unit else mark,
                    "of": said(e["desc"]) or {"en": e["desc"]}}
        if unit:
            got_line["unit"] = unit
        return got_line

    return {
        "names": said(f"talent_name_{got['key']}"),
        "lore": said(f"talent_desc_{got['key']}"),
        "lines": [line(e) for e in got.get("effects") or []],
        "lasts": got.get("duration"),
        "levels": levels,
    }


def build(raw_items, csv_path, langs, icons_by_name, tidy, tables, say=None, talent_rows=None,
          named=None):
    """Every item worth a page, keyed by the game's own translation key.

    `icons_by_name` is the icon sheet's boxes, so an item that has one shows it
    and one that does not simply has none — the same answer the map gives.

    `tables` is the tracker's, and the odds come from it rather than from the
    snapshot beside them. The snapshot's `chaseDropRate` is a multiplier — 1 for
    nearly two thousand items, 0.3175 for a hundred and some — and printed as
    odds it read "1 in 1", which is a promise the game does not make. The
    tracker's `DROP_CHASE` is the "one in N" the game's own tooltip prints.
    """
    # the talents by the key a potion names them with, and by the number
    # everything else names them with. Both off the list rather than one off
    # the other: two talents are called `blazingTrail`, so a table keyed by
    # name is one number short.
    talents = {}
    for row in talent_rows or []:
        talents.setdefault(row["key"].lower(), row)
    by_number = {t["id"]: t for t in (talent_rows or []) if t.get("id")}
    by_spoken = {}
    for row in talent_rows or []:
        spoken_as = ((say.by_key.get(f"talent_name_{row['key']}") if say else None) or {}).get("en")
        if spoken_as:
            by_spoken.setdefault(flat(spoken_as), row)
    pins = pinned(raw_items, talents)
    rows = text_rows(csv_path)

    def said(key):
        """One key in every language the game ships, English filled in for gaps.

        `translationsItem.csv` is where an item's name belongs and where nearly
        every one of them is. Not all: the 156 relics and one throwing weapon
        are named in another of the game's translation files, and reading only
        this one left them showing their key — `relic_rubberDuck` was on the
        page in every language. So a key this file has no row for is asked of
        the whole set before it is given up on.
        """
        got = rows.get(key)
        if not got:
            return say.by_key.get(key) if say else None
        out = {}
        for i, lang in enumerate(langs):
            word = got[i].strip() if i < len(got) else ""
            if word:
                out[lang] = word
        return out or None

    # what a socket name refers to, for the runeword recipes below
    by_name = {}
    for it in raw_items:
        m = it.get("metadata") or {}
        tk = m.get("tkey") or ""
        if m.get("name") and (tk.startswith("socketable") or m.get("type") in ("Rune", "Orb", "Gem")):
            by_name.setdefault(tidy(m["name"]), tk)

    items = {}
    for it in raw_items:
        m = it.get("metadata") or {}
        name, tkey = m.get("name"), m.get("tkey")
        # `-Unknown Name-` is the snapshot's own shrug, sixty-five rows of it.
        # Keyed by tkey rather than by name, because two different things can
        # share one: Death's Scythe is both a Satanic Set weapon and a common
        # relic, and keying by name kept whichever came first.
        if not tkey or tkey == "-Unknown Name-":
            continue
        # `item_type_gem`, `item_type_belt` and seventeen more are the names of
        # the kinds, sitting in the table beside the things — no type, no stats,
        # no art, because they are labels and not items.
        if tkey.startswith("item_type_"):
            continue
        if tkey in items:
            continue
        told = said(tkey)
        # The game's own English name leads; the snapshot's fills a gap. Where
        # neither knows — one item, a Heroic throwing weapon the snapshot calls
        # "Unknown Name" and the game names nowhere — the key is read out
        # instead, minus the letter that says what kind of thing it is and the
        # word that repeats its type. A name taken off the game's own identifier
        # beats "Unknown Name" on a page whose whole job is to name things.
        shown = (told or {}).get("en") or (name or "").strip()
        if not shown or shown == "Unknown Name":
            shown = out_of_key(tkey, m.get("type"))
        if not shown:
            continue
        low = tidy(shown)
        stats = [stat_line(s) for s in (it.get("stats") or []) if s.get("sid") or s.get("id") in BY_ID]
        gives = granted(tkey, stats, talents, named, by_number, by_spoken, pins, said)
        rec = {
            "key": tkey,
            "name": shown,
            "rarity": m.get("rarity"),
            "tier": m.get("tier"),
            # "Unknown Type" is not a type. It is the snapshot shrugging at the
            # two runewords that go in either of two bases — `base` below says
            # which two — and offered as a filter it read like a fault. Left
            # unset, no chip is made for it and nothing else changes.
            "type": None if m.get("type") == "Unknown Type" else m.get("type"),
            "lvl": m.get("lvlreq"),
            "size": [m.get("Width"), m.get("Height")] if m.get("Width") else None,
            "stats": stats,
            "grants": gives,
            "places": tables["DROP_PLACES"].get(low) or it.get("dropPlaces") or [],
            "rate": tables["DROP_RATE"].get(low) or plain((it.get("droprate") or {}).get("base")),
            "chase": tables["DROP_CHASE"].get(low),
            "names": told,
            "lore": said(f"lore_{tkey}"),
            "icon": icons_by_name.get(low) or icons_by_name.get(tidy(name)),
            "sockets": sockets(it, by_name, tidy),
            "weapons": weapons(it),
            "set": m.get("Item Set"),
            "base": (BASE.get(it.get("runewordItemType"))
                     if isinstance(it.get("runewordItemType"), int)
                     else " or ".join(BASE.get(n, str(n))
                                      for n in it.get("runewordItemType") or [])) or None,
            "more": variants(it),
        }
        items[tkey] = {k: v for k, v in rec.items() if v not in (None, [], {})}

    # Sets: which pieces belong to each, and what the set is called in every
    # language. The game keys those under `*_setname` and the item data names
    # its set in English, so the two are joined on that name. Nothing in the
    # data says what wearing the whole set does, so nothing is said about it.
    said_set = {}
    for key, got in rows.items():
        if key.endswith("setname") and got and got[0].strip():
            said_set[got[0].strip()] = {langs[i]: got[i].strip()
                                        for i in range(min(len(langs), len(got)))
                                        if got[i].strip()}
    kits = {}
    for tkey, rec in items.items():
        if rec.get("set"):
            kits.setdefault(rec["set"], []).append(tkey)
    kits = {name: {"of": sorted(members), "names": said_set.get(name)}
            for name, members in sorted(kits.items())}

    # The stat vocabulary, so the page can offer a list rather than free text.
    #
    # A list and not an object: six of these sids are bare numbers, and a
    # JavaScript object puts integer-like keys first whatever order it was built
    # in — so the commonest-first sort survived the file and died on arrival,
    # with "Unnamed stat 104" at the head of the list.
    vocab = {}
    for rec in items.values():
        every = list(rec.get("stats") or [])
        for v in rec.get("more") or []:
            every += v["stats"]
        for s in every:
            row = vocab.setdefault(s["sid"], {"sid": s["sid"], "text": s["text"], "n": 0})
            if s.get("unit"):
                row["unit"] = s["unit"]
            row["n"] += 1
    return items, sorted(vocab.values(), key=lambda v: (-v["n"], v["text"])), kits
