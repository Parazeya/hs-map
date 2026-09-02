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

def camel(key):
    """`consumable_bottle_of_sake` -> `bottleOfSake`, which is what the talent
    populators call it."""
    parts = key.split("_", 1)[1].split("_") if "_" in key else [key]
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def pinned(raw_items, talents, also=None):
    """How far our count of the talents runs from the game's, where it can be told.

    An item names the talent it grants by a number, and the number is its place
    in an order the compiler settled. Reading the populators gives an order too
    and the two do not match: ours runs about twenty ahead by the end of the
    list, and the difference is not constant.

    It can be measured, though, and by the items themselves. A potion names its
    talent twice over — by number and by a key its own key spells out — so each
    of them says what the difference is at its own number. Between two that
    agree, the difference is known; outside them it is not, and an item there
    keeps its number rather than be given a name that may be the neighbour's.

    Measured rather than written down because it moves: every repair to the
    populator reader changes how many records it makes, and a table of numbers
    would then be quietly wrong instead of loudly absent.
    """
    seen = []
    for row in raw_items:
        key = (row.get("metadata") or {}).get("tkey")
        if not key:
            continue
        number = next((s.get("min1") for s in row.get("stats") or []
                       if s.get("sid") == GRANTS), None)
        if number is None:
            continue
        # the item's own key spells the talent out, or somebody has read the
        # tooltip and named it
        got = talents.get(camel(key).lower()) or (also or {}).get(key)
        if got and got.get("id"):
            seen.append((number, number - got["id"]))
    seen.sort()
    return seen


def at_number(n, talents, pins):
    """The talent an item's number names, where the count can be trusted.

    Trusted means bracketed: an anchor at or below the number and another at or
    above it, both saying the same thing about the difference.
    """
    below = [(at, d) for at, d in pins if at <= n]
    above = [(at, d) for at, d in pins if at >= n]
    if len(below) < 2 or len(above) < 2:
        return None
    # Three in a row saying the same thing. Two would do if every anchor were
    # sound, and they are not: a name matched to the wrong talent puts a wild
    # difference into the list, and two neighbouring wild ones would agree with
    # each other about nothing in particular.
    near = [below[-2][1], below[-1][1], above[0][1], above[1][1]]
    if len(set(near)) != 1:
        return None
    return talents.get(n - near[0])


def granted(tkey, stats, talents, by_number, pins, said):
    """What the item does, out of the talent it grants.

    Asked two ways. A potion says which talent it is in its own key —
    `consumable_bottle_of_sake` grants `bottleOfSake` — and that is exact, so
    it is asked first. Everything else says only the number, which is read
    where the count is pinned; see `PINNED`.
    """
    if not talents:
        return None
    named = next((s for s in stats if s.get("sid") == GRANTS), None)
    if named is None:
        return None
    got = talents.get(camel(tkey).lower())
    if not got and named.get("min") is not None:
        got = at_number(named["min"], by_number, pins)
    if not got:
        return None
    # The level it is granted at is a roll like any other. A potion states it
    # under the random-skill mark; the rest state it as a range of skill levels
    # with no name on it, which is the only line on the item that carries one.
    levels = next((s for s in stats
                   if s.get("sid") == GRANT_LEVELS and s.get("max") is not None), None)
    if levels is None:
        levels = next((s for s in stats
                       if s.get("sid") in ("all_talents", "all_skills_flat")
                       and s.get("max") is not None), None)

    # The range is how many levels of the granted talent the item rolls, not a
    # bonus to every skill the character has. Left in the stat list it reads as
    # the second, and the card says the item does both.
    if levels is not None and levels.get("sid") != GRANT_LEVELS:
        stats.remove(levels)
    # and the number itself is plumbing: the game prints the talent's name in
    # its place, which is now what this returns
    stats.remove(named)
    return spoken(got, [levels.get("min"), levels.get("max")] if levels else None, said)


def spoken(got, levels, said):
    """A talent as the block an item's card shows for it."""
    return {
        "names": said(f"talent_name_{got['key']}"),
        "lore": said(f"talent_desc_{got['key']}"),
        "lines": [{"start": e["start"], "per": e["per_level"], "mark": e["mark"],
                   "of": said(e["desc"]) or {"en": e["desc"]}}
                  for e in got.get("effects") or []],
        "lasts": got.get("duration"),
        "levels": levels,
    }


def build(raw_items, csv_path, langs, icons_by_name, tidy, tables, say=None, talents=None,
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
    # the same talents, by the number an item names them with
    by_number = {t["id"]: t for t in (talents or {}).values() if t.get("id")}
    # what the items themselves say about the numbering, before the numbers are
    # taken off them
    pins = pinned(raw_items, talents or {}, named)
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
        gives = granted(tkey, stats, talents, by_number, pins, said)
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
