"""Every class skill the game defines, the numbers behind it, and its tree.

The words are the game's own — `talent_name_<key>` and `talent_desc_<key>` in
`translationsTalent.csv`, `sub<Class><Skill><NN>` in `translationsSubTalent.csv`
— in all eleven languages, and the icons are cut out of the game's own sprites.

The numbers come from HSPlanner (github.com/HeroSiegePlanner/HSPlanner, MIT,
Copyright (c) 2026 zium), vendored under `planner/`. What the executable states
about a skill is only half of it: it holds the level requirement, the damage
type and the per-level lines, but not the mana cost, the movement the skill
allows while it runs, the rate it fires at, or the skills that feed it. Those
are on the tooltip, and reading tooltips is what the planner has done.

The two sides are joined on the skill's key: 415 of the 432 spell it the same
way, and the rest are written down in `CALLED`. A sub-skill joins on its place
in the tree — the game's `<NN>` is the planner's `positionIndex`, with index 0
the core, which is the skill itself and has no row of its own.
"""

import json
import re

from PIL import Image

#: A skill the two sides spell differently.
#:
#: The planner's id is the skill's name run together; the game's key usually is
#: too, which binds 415 of the 432 with nothing written down. What is left is
#: an abbreviation (`Grenade Jump` is `grenado`), a plural (`sandGuardian`), a
#: word the game leaves out (`Summon Raven` is `raven`) or adds
#: (`raiseSkeletonWarrior`), and one plain misspelling — `Vendigo` for the
#: Wendigo. Nearness would bind `Raise Skeleton` to the mastery as readily as
#: to the warrior, so these are named.
CALLED = {
    "crowd_dive": "crowdDiver",
    "sand_guardians": "sandGuardian",
    "gravitation_slam": "gravitationalSlam",
    "raise_skeleton": "raiseSkeletonWarrior",
    "summon_mastery": "skeletonMastery",
    "healing_sunrays": "sunRay",
    "grenade_jump": "grenado",
    "explosive_bullets": "explosiveBullet",
    "freezing_chain_shot": "freezeChainShot",
    "summon_raven": "raven",
    "summon_ent_colossus": "entColossus",
    "summon_spirit_of_the_forest": "spiritOfForest",
    "storm_hawk": "spiritOfHawk",
    "spirit_of_the_ent": "spiritOfEnt",
    "spirit_of_the_wendigo": "spiritOfWendigo",
    "throw": "monsterThrow",
    "chain_of_holy_lightning": "chainOfHolyLight",
}

#: A sub-skill group whose middle does not spell its skill's key.
#:
#: The same disagreement as `CALLED`, on the other table: a group is keyed
#: `sub<Class><Skill><NN>` and the middle is meant to be the skill. The habit
#: holds for 207 of the 215 groups the game spells out.
SUB_CALLED = {
    ("Viking", "Throw"): "monsterThrow",
    ("Jotunn", "SweepFreeze"): "flashFreeze",
    ("Marksman", "GunnerDrones"): "gunnerDrone",
    ("Necromancer", "RaiseSkeleton"): "raiseSkeletonWarrior",
    ("Pirate", "ExplosiveBullets"): "explosiveBullet",
    ("Pirate", "FreezingChainShot"): "freezeChainShot",
    ("Prophet", "SpiritOfVendigo"): "spiritOfWendigo",
    ("Prophet", "StormHawk"): "spiritOfHawk",
    ("Redneck", "ChainSlash"): "chainsawSlash",
}

#: A tree whose node sprites are filed under another spelling again.
#:
#: The sprite names are a third spelling of the same skills, disagreeing with
#: both the key and the name: a plural (`Summon_Ravens`), a word the sprite
#: keeps that the key drops (`Spirit_of_The_Forest`), the Wendigo misspelt once
#: more, and Frost Sunder still filed under the name it had when it was Sweep
#: Freeze.
SUB_ART = {
    "raven": "Sub_Prophet_Summon_Ravens",
    "spiritOfForest": "Sub_Prophet_Spirit_of_The_Forest",
    "spiritOfWendigo": "Sub_Prophet_Spirit_of_Vendigo",
    "frostSunder": "Sub_Jotunn_Sweep_Freeze",
}

#: The planner's word for the game's `magic`. Everything else agrees.
ELEMENT = {"arcane": "magic"}

#: A tag the game keys by something other than its own name run together.
#:
#: The tags are the planner's list because that is what the tooltips say, but
#: the game has a translated word for most of them under `abilityTag<Name>`,
#: and that is what the page should print. Four disagree on the spelling; six
#: more — Attack, Cast and the four element names — the game has no tag word
#: for at all, and those fall back to the element's own word or to English.
TAG_KEY = {
    "Area of Effect": "Aoe",
    "Chain Lightning": "ChainLightning",
    "Orbital": "Orbit",
    "Shape Shift": "ShapeShifting",
}

#: A tag that names an element rather than a habit: said elsewhere.
TAG_ELEMENT = {"Arcane": "magic", "Lightning": "lightning", "Physical": "physical",
               "Poison": "poison"}

#: Where the fifteen nodes of a sub-skill tree sit, and what is wired to what.
#:
#: Every tree in the game is this one shape — the same fifteen places, the same
#: wires — and only what stands in each place changes. The keystone is at the
#: foot, the four notables at the corners, the ten minors between them. Taken
#: from HSPlanner's `frontend/utils/tree/subtreeTemplate.ts`; the coordinates
#: are fractions of the pentagram the game draws behind the tree.
LAYOUT = [
    {"at": [0.500, 0.870], "role": "core", "to": [1, 2]},
    {"at": [0.453, 0.724], "role": "minor", "to": [0, 4]},
    {"at": [0.547, 0.724], "role": "minor", "to": [0, 6]},
    {"at": [0.253, 0.579], "role": "minor", "to": [4, 11]},
    {"at": [0.406, 0.579], "role": "minor", "to": [1, 3, 5, 8]},
    {"at": [0.500, 0.579], "role": "minor", "to": [4, 6]},
    {"at": [0.594, 0.579], "role": "minor", "to": [2, 5, 7, 9]},
    {"at": [0.747, 0.579], "role": "minor", "to": [6, 14]},
    {"at": [0.347, 0.399], "role": "minor", "to": [4, 10, 11, 12]},
    {"at": [0.653, 0.399], "role": "minor", "to": [6, 10, 13, 14]},
    {"at": [0.500, 0.289], "role": "minor", "to": [8, 9, 12, 13]},
    {"at": [0.100, 0.579], "role": "notable", "to": [3, 8]},
    {"at": [0.253, 0.109], "role": "notable", "to": [8, 10]},
    {"at": [0.747, 0.109], "role": "notable", "to": [9, 10]},
    {"at": [0.900, 0.579], "role": "notable", "to": [7, 9]},
]

SUB = re.compile(r"^sub(Desc)?([A-Za-z]+?)(\d\d)$")


def flat(name):
    """`Storm Bolt`, `storm_bolt` and `stormBolt` all come out the same."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def lower_camel(name):
    """`DemolishingWinds` -> `demolishingWinds`, which is how a talent is keyed."""
    return name[:1].lower() + name[1:]


def read(folder):
    """The planner's tables, one file to a class."""
    out = []
    for path in sorted(folder.glob("*.json")):
        rows = json.loads(path.read_text("utf-8"))
        if isinstance(rows, list) and rows and "classId" in rows[0]:
            out += rows
    return out


def pair(planner, talents):
    """Which game talent each of the planner's skills is.

    Keyed on the game's side, because that is what the words and the icons are
    keyed on.
    """
    by_key = {flat(t["key"]): t["key"] for t in talents}
    out, loose = {}, []
    for s in planner:
        named = CALLED.get(s["id"])
        key = named or by_key.get(flat(s["id"])) or by_key.get(flat(s["name"]))
        if key is None:
            loose.append(f"{s['classId']}.{s['id']}")
            continue
        out[key] = s
    return out, loose


def groups(rows, classes):
    """The sub-skills, gathered by the class and skill they hang under.

    A class whose name is two words — DemonSlayer, PlagueDoctor, WhiteMage —
    cannot be cut off the front of a key by shape, so the known classes are
    matched longest first and what is left is the skill.
    """
    known = sorted(classes, key=len, reverse=True)
    out = {}
    for key in rows:
        m = SUB.match(key)
        if not m or m.group(1):          # the description rows are read beside
            continue
        _, rest, n = m.groups()
        cls = next((c for c in known if rest.startswith(c)), None)
        if cls is None:
            continue
        out.setdefault((cls, rest[len(cls):]), []).append((int(n), key))
    for v in out.values():
        v.sort()
    return out


def worded(key):
    """`projectile_speed` -> `Projectile Speed`, for a stat with no translation.

    The planner's own vocabulary, which the game has no word for: the node says
    what it does in the player's language on the line above, so this only has
    to label the number under it.
    """
    small = {"of", "as", "per", "to", "below", "pct"}
    words = key.split("_")
    out = []
    for i, w in enumerate(words):
        if w == "pct":
            continue
        out.append(w if i and w in small else w.capitalize())
    return " ".join(out)


def stats(side):
    """A `{stat: value}` bag as lines the page can print in order."""
    return [{"of": worded(k), "v": v} for k, v in (side or {}).items()]


def effects(block):
    """A sub-skill's per-rank effect, or a proc's."""
    if not block:
        return None
    out = {}
    base, per = stats(block.get("base")), stats(block.get("perRank"))
    if base:
        out["base"] = base
    if per:
        out["per"] = per
    return out or None


def tag_word(name, said):
    """What the game calls a tag, in every language it says it in."""
    key = TAG_KEY.get(name, name.replace(" ", ""))
    return (said(f"abilityTag{key}")
            or said(TAG_ELEMENT.get(name, ""))
            or {"en": name})


def scaling(tags):
    """What the skill's rate follows — the tooltip says so with a tag."""
    if "Cast" in tags:
        return "cast"
    if "Attack" in tags:
        return "attack"
    return None


def build(talents, rows, said, langs, planner_dir):
    """The document the skills page reads."""
    planner = read(planner_dir)
    known, loose = pair(planner, talents)

    by_class = {}
    for t in talents:
        if t["class"]:
            by_class.setdefault(t["class"], []).append(t)

    # the game's own words for the nodes, gathered under the skill they hang on
    under = groups(rows, by_class)
    bound = 0
    words_of = {}
    for (cls, skill), members in sorted(under.items()):
        want = SUB_CALLED.get((cls, skill), lower_camel(skill))
        here = {t["key"]: t for t in by_class.get(cls, [])}
        key = want if want in here else next(
            (k for k in here if k.lower().endswith(skill.lower())), None)
        if key is None:
            continue
        bound += 1
        words_of[key] = {n: k for n, k in members}

    skills = {}
    for cls, ts in by_class.items():
        for t in ts:
            key = t["key"]
            p = known.get(key, {})
            tags = p.get("tags") or t.get("tags") or []
            element = ([ELEMENT.get(p["damageType"], p["damageType"])]
                       if p.get("damageType") else t.get("element") or [])
            said_sub = words_of.get(key, {})

            subs = []
            for node in p.get("subskills") or []:
                i = node["positionIndex"]
                row = said_sub.get(i)
                subs.append({
                    "i": i,
                    "key": row,
                    # the core is the skill itself and has no row of its own
                    "names": said(row) if row else said(f"talent_name_{key}"),
                    "lore": said(f"subDesc{row[3:]}") if row else None,
                    "rank": node.get("maxRank"),
                    "gives": effects(node.get("effects")),
                    "proc": node.get("proc") or None,
                })

            skills[key] = {
                "class": cls,
                "names": said(f"talent_name_{key}"),
                "lore": said(f"talent_desc_{key}"),
                "lvl": t.get("level_req"),
                "cooldown": t.get("cooldown") or p.get("baseCooldown"),
                "lasts": t.get("duration") or p.get("effectDuration"),
                "element": element,
                "tags": tags,
                "kind": p.get("kind"),
                "rank": p.get("maxRank"),
                "tree": p.get("tree"),
                "pos": [p["position"]["row"], p["position"]["col"]] if p.get("position") else None,
                # the share of its speed the player keeps while the skill runs
                "move": p.get("movementDuringUse"),
                "range": p.get("range"),
                "rate": p.get("baseCastRate"),
                "scales": scaling(tags),
                "mana": p.get("manaCostFormula"),
                "dmg": p.get("damageFormula"),
                "hits": p.get("hitModel"),
                "holds": effects(p.get("passiveStats")),
                "bonus": [{"from": b["source"], "of": worded(b["stat"]),
                           "v": b["value"], "per": b["per"]}
                          for b in p.get("bonusSources") or []],
                # `mark` is a symbol on most lines and a translation key on
                # the rest — `tal_seconds` and its kin — so the key is asked of
                # the game rather than printed as it stands.
                "lines": [{"start": e["start"], "per": e["per_level"],
                           "mark": "" if e["mark"].startswith("tal_") else e["mark"],
                           "unit": said(e["mark"]) if e["mark"].startswith("tal_") else None,
                           "of": said(e["desc"]) or {"en": e["desc"]}}
                          for e in t.get("effects") or []],
                "subs": subs,
            }

    classes = [{"id": c, "names": said(c.lower()) or {"en": c}} for c in sorted(by_class)]
    elements = sorted({e for s in skills.values() for e in s["element"]})
    tags = sorted({g for s in skills.values() for g in s["tags"]})
    kinds = sorted({s["kind"] for s in skills.values() if s["kind"]})
    doc = {
        "langs": langs,
        "classes": classes,
        "elements": [{"id": e, "names": said(e) or {"en": e}} for e in elements],
        "tags": [{"id": g, "names": tag_word(g, said)} for g in tags],
        # a kind is a tag every skill of that kind wears, so it is already said
        "kinds": [{"id": k, "names": tag_word(k.capitalize(), said)} for k in kinds],
        "layout": LAYOUT,
        "skills": skills,
    }
    return doc, bound, len(under), len(known), loose


def report(doc, bound, wanted, known, loose):
    skills = doc["skills"]
    with_subs = sum(1 for s in skills.values() if s["subs"])
    subs = sum(len(s["subs"]) for s in skills.values())
    told = sum(1 for s in skills.values() for x in s["subs"] if x["key"])
    numbered = sum(1 for s in skills.values() if s["rank"])
    print(f"skills   {len(skills)} on {len(doc['classes'])} class trees, "
          f"{with_subs} of them with sub-skills ({subs} in all)")
    print(f"         {numbered} carry the planner's numbers"
          + (f"; loose: {', '.join(loose[:6])}" if loose else ""))
    print(f"         {told} of {subs} nodes say their name in the game's own words, "
          f"out of {bound} of {wanted} groups")
    print(f"         {len(doc['elements'])} damage types, {len(doc['tags'])} tags, "
          f"{len(doc['kinds'])} kinds to filter by")


def art(dw, talents, out_png, planner_dir):
    """Cut every icon the page draws.

    A talent names its own icon by asset reference and the extractor resolves
    that to a sprite name, so nothing is matched by nearness — the game says
    which picture is which. Forty-odd say nothing, and those are looked up by
    name in `Talent_*`, which is where the rest of them live anyway.

    A tree's fifteen icons are frames of two sprites the game keeps per tree:
    `Sub_<Class>_<Skill>_Big_spr` holds the keystone and the four notables,
    `_Small_spr` the ten minors between them, each in the order the tree
    numbers them. They go on a sheet of their own, which is asked for only when
    a tree is opened.
    """
    named = {}
    for name in getattr(dw, "sprites", {}) or {}:
        if name.startswith("Talent_") and name.endswith("_spr"):
            named.setdefault(flat(name[7:-4]), name)

    cut = {}
    missing = []
    # `elemental` has no plate of its own — a talent that deals several — and
    # wears the arcane one, which is what the game's own tree does with it.
    PLATE = {"physical": "Physical", "magic": "Arcane", "cold": "Cold", "fire": "Fire",
             "lightning": "Lightning", "poison": "Poison", "elemental": "Arcane"}
    # A node is its icon on a dark disc with a ring around it in the skill's
    # colour: the big ring on the keystone and the four notables, the small one
    # on the ten minors. The rings are the only part that changes colour.
    for key, art_name in PLATE.items():
        for size, tag in (("Small", "sm"), ("Big", "bg")):
            try:
                cut[f"{tag}:{key}"] = dw.sprite_frames(f"Sub_Talent_{size}_{art_name}_spr")[0]
            except Exception:
                pass
    for name, tag in (("Sub_Talent_Small_Circle_spr", "disc:sm"),
                      ("Sub_Talent_Big_Circle_spr", "disc:bg")):
        try:
            cut[tag] = dw.sprite_frames(name)[0]
        except Exception:
            pass

    for t in talents:
        name = t.get("icon") or named.get(flat(t["key"]))
        if name:
            try:
                cut[t["key"]] = dw.sprite_frames(name)[0]
                continue
            except Exception:
                pass
        missing.append(t["key"])

    faces, blank = nodes_art(dw, talents, planner_dir, out_png.with_name("subskills.webp"))
    # The keystone of a skill's own tree is the skill's picture drawn larger, so
    # a skill the talent tables name no icon for is not left blank while the
    # game plainly has one.
    for key in list(missing):
        frames = faces["core"].get(key)
        if frames is not None:
            cut[key] = frames
            missing.remove(key)

    place, size = shelve(cut, out_png.with_suffix(".webp"))
    nodes = {"sm": {}, "bg": {}, "disc": {}}
    for k in [k for k in place if ":" in k]:
        tag, _, rest = k.partition(":")
        (nodes["disc"] if tag == "disc" else nodes[tag])[rest] = place.pop(k)

    faces.pop("core")
    return place, nodes, size, sorted(missing), faces, blank


def nodes_art(dw, talents, planner_dir, out_webp):
    """The fifteen icons of every tree, on a sheet of their own.

    The two sprites a tree's icons live in are named for the class and the
    skill, which the game spells its own way on this side too — the sprite for
    Throw! is `Sub_Viking_Throw_*` — so the skill's key, the planner's id and
    the skill's English name are all tried before a tree is given up on.
    """
    known, _ = pair(read(planner_dir), talents)
    # `blazingTrail` is a Pyromancer skill and also a relic's, and the relic's
    # copy carries no class, so the one that knows its class wins
    by_class = {}
    for t in talents:
        if t["class"] or t["key"] not in by_class:
            by_class[t["key"]] = t["class"]

    pairs = {}
    for name in getattr(dw, "sprites", {}) or {}:
        m = re.match(r"^Sub_([A-Za-z]+)_(.+)_(Small|Big)_spr$", name)
        if m and not name.startswith("Sub_Talent_"):
            pairs.setdefault(flat(m.group(1) + m.group(2)), {})[m.group(3)] = name

    cut, blank, core = {}, [], {}
    for key, p in known.items():
        if not p.get("subskills"):
            continue
        cls = by_class.get(key, "")
        named = SUB_ART.get(key)
        found = next((pairs[f] for f in
                      (flat(named[4:]) if named else "", flat(cls + key),
                       flat(cls + p["id"]), flat(cls + p["name"])) if f in pairs), None)
        if not found or "Small" not in found or "Big" not in found:
            blank.append(key)
            continue
        try:
            small = dw.sprite_frames(found["Small"])
            big = dw.sprite_frames(found["Big"])
        except Exception:
            blank.append(key)
            continue
        # the keystone and the four notables are the big sprite's five frames,
        # the ten minors between them the small sprite's ten
        core[key] = big[0]
        for i in range(15):
            frames, n = (big, 0) if i == 0 else (small, i - 1) if i <= 10 else (big, i - 10)
            if n < len(frames):
                cut[f"{key}:{i}"] = frames[n]

    place, size = shelve(cut, out_webp)
    # a tree as fifteen corners rather than fifteen boxes: every icon is one of
    # the game's two sizes, and which one is settled by the place it stands in
    at = {}
    for key, box in place.items():
        skill, _, i = key.rpartition(":")
        at.setdefault(skill, [None] * 15)[int(i)] = [box[0], box[1]]
    small = next((b[2] for k, b in place.items() if not k.endswith((":0", ":11", ":12", ":13", ":14"))), 28)
    big = next((b[2] for k, b in place.items() if k.endswith(":0")), 44)
    return ({"at": at, "sm": small, "bg": big, "w": size[0], "h": size[1], "core": core},
            sorted(blank))


def shelve(cut, out_webp):
    """Pack what was cut onto one sheet, shelf by shelf, tallest first."""
    order = sorted(cut.items(), key=lambda kv: -kv[1].height)
    WIDTH, PAD = 1024, 1
    x = y = shelf = 0
    place = {}
    for key, im in order:
        if x + im.width + PAD > WIDTH:
            x, y, shelf = 0, y + shelf + PAD, 0
        place[key] = (x, y, im.width, im.height)
        x += im.width + PAD
        shelf = max(shelf, im.height)
    sheet = Image.new("RGBA", (WIDTH, y + shelf + PAD))
    for key, im in order:
        px, py, _, _ = place[key]
        sheet.paste(im, (px, py))
    sheet.save(out_webp, lossless=True, quality=100, method=6)
    return place, sheet.size
