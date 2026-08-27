"""A picture for each boss, chest and machine.

There is no portrait set in the game — the art is animation frames named by
direction (`Gurag_Attack_Down_spr`, `Anubis_Head_spr`), and every boss names
them differently. So candidates are gathered by name, ranked, and the choice is
written out twice: as `chosen.json`, and as a labelled contact sheet. Neither is
for the page. Both are for arguing with.

Anything nothing can find is reported rather than guessed at. Another monster's
face beside a drop list is worse than a blank.
"""

import re

from PIL import Image, ImageDraw

squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

#: A boss is drawn much larger than an item — the Architect is 308 by 299, and a
#: smaller ceiling let his flame effect win the part. Still not so large that a
#: whole arena qualifies: the Leviathan's idle frame is 688 by 490.
MAX = 420

#: Never the thing a boss throws or stands on, only the boss. Without this the
#: Architect is represented by a purple flame and Gabriel by his altar.
DENY = ("effect", "flame", "explosion", "ball", "projectile", "bullet", "aura",
        "trail", "portal", "altar", "chain", "arrow", "shadow", "spawn",
        "black_hole", "light", "cloud", "debuff", "curse", "buff", "icon",
        "frame", "clock", "darkness", "hitbox", "indicator", "mask", "sonar")

#: What makes one sprite a better portrait than another, lowest tier first.
#:
#: Two mistakes were made here and both are worth keeping written down.
#:
#: Facing: the game is drawn from above, so `_Down` is the front of a character
#: and `_Up` is the back of its head. Ranking the pose above the facing, with
#: ties broken by the shorter name, stood King Rakhul and Gabriel with their
#: backs turned.
#:
#: And "no pose word" is not the same as "the creature itself". Nearly every
#: sprite in a boss's family has no pose word — they are body parts, props and
#: effects — so calling that the second-best kind handed Blood Maiden her own
#: heart, the Leviathan a sword-swing, and the Architect a ring.
TIERS = (
    lambda s: "_idle" in s and "_down" in s,      # facing you, standing still
    lambda s: "_idle" in s,                       # standing still, some other way
    lambda s: "_down" in s,                       # facing you, doing something
    lambda s: "_head" in s,                       # a portrait by another name
    lambda s: "_boss" in s,                       # the fight's own sprite
    lambda s: "_cast" in s or "_attack" in s,     # mid-move, but still the thing
    lambda s: any(w in s for w in ("_up", "_left", "_right")),   # turned away
)

#: Chosen outright, because the search cannot get these from the name.
#:
#: The gambling machine is not called Gamba anywhere in the art — `Glyph_of_Gamba`
#: is the relic, not the machine. The rift's own sprites are 29px tiles of the
#: ether effect rather than the portal. And Damien has a body: the head is a
#: separate sprite because it comes off during the fight.
PICKED = {
    "uber damien (son of lucifer)": "Damien_Headless_Uber_spr",
    "gamba machine": "Slot_Machine_01_spr",
    "unstable rift": "Rift_Portal_spr",
    "uber damien": "Damien_Headless_Uber_spr",
    # Two the object gets wrong. `Karp_King_obj` wears only his crown — he is
    # built from a crown, a head and a torso — and `Sheep_King_obj` wears the
    # frame with his back turned. Both are corrected to the same creature seen
    # from the front.
    "karp king": "Karp_King_Head_spr",
    # And the sources that are not creatures at all, so each is shown as the way
    # into it. The battlefield has the game's own journal plate, which says its
    # name in so many words; the challenge is its summoning sigil; Sheeponia is
    # its woolly gate, now that its king is his own entry. The two categories of
    # dungeon get a door apiece — a plain cave mouth and a skull gate — which are
    # illustrations of a kind of place rather than pictures of a particular one.
    #
    # Both were something worse first. "Dungeons" was a door sprite that is a
    # black rectangle with a blue strip on it, and the challenge was the journal
    # page beside the plate, which carries another quest's text across it: at
    # shelf size it read "LACK TOWER".
    "challenge dungeon": "Challenger_spr",
    "eternal battlefield": "Journal_Eternal_Battle_Field_spr",
    "sheeponia": "Sheep_Enemy_King_Idle_Down_spr",
    "dungeons": "Treasure_Dungeon_Entrance_01_spr",
    "boss dungeons": "Shipwreck_Cove_Dungeon_Entrance_spr",
}

#: The object each of these is, so the game can be asked what it wears.
#:
#: Searching the sprite names finds a limb. Almost every boss is assembled from
#: parts — `Anubis_Left_Upper_Arm_spr`, `Satan_Jaw_spr`, `Grimbone_Front_Leg_
#: Middle_Down_spr` — and the whole creature, where there is one, is not named
#: any differently from them. The object says which sprite is the creature, and
#: it is the game saying it rather than this file guessing.
#:
#: It answers the ones no search could. `Uber_Luna_obj` wears
#: `Fortune_Teller_Head_spr` — Possessed Luna is the fortune teller, which is why
#: the only sprites called Luna are her crystal ball and her black hole.
#: `Uber_Anubis_Dummy_obj` wears `Uber_Anubis_Head_spr`, and the drop tables call
#: that boss Amun Ra. `Uber_Endrixia_obj` wears `Dragon_Whelp_Ancient_Down_spr`:
#: she is that dragon, scaled up, and the only sprite bearing her own name is her
#: flames.
WEARS = {
    "gurag": "Gurag_obj",
    "grim reaper": "Reaper_obj",
    "anubis": "Anubis_obj",
    "damien": "Damien_obj",
    "satan": "Satan_obj",
    "mevius": "Mevius_obj",
    "amun ra": "Uber_Anubis_Dummy_obj",
    "possessed luna": "Uber_Luna_obj",
    "endrixia": "Uber_Endrixia_obj",
    "grimbone": "Grimbone_obj",
}

#: Names the drop tables use, and what the art calls them.
#:
#: Possessed Luna is deliberately absent: the only sprites starting "Luna" are
#: her crystal ball and her black hole, and "Lunar_Exo" is a different creature
#: altogether. A gap says less than the wrong monster's face would.
ALIAS = {
    "shade of death": ["shadeofdeath", "shade"],
    "shade of death (uber reaper)": ["shadeofdeath", "shade", "reaper"],
    "amun ra": ["uberamunra", "amunra"],
    "architect of ruin": ["architectboss", "architect"],
    "endrixia": ["uberendrixia", "endrixia"],
    "son of lucifer": ["sonoflucifer", "lucifer"],
    "uber damien": ["uberdamien", "damien"],
    "uber damien (son of lucifer)": ["uberdamien", "damien"],
    "uber reaper": ["uberreaper", "grimreaper", "reaper"],
    "grim reaper": ["grimreaper", "reaper"],
    "karp king": ["karpking"],
    "mimic": ["mimic"],
    "chaos pillar": ["chaospillar"],
    "crystal chest": ["crystalchest"],
    "colossal chest": ["colossalchest"],
    "chaos tower": ["chaostower"],
    "rogue chaos tower": ["chaostower"],
}


def candidates(dw, boss):
    keys = ALIAS.get(boss.lower(), []) + [squash(boss)]
    out = []
    for name in dw.sprites:
        if not name.endswith("_spr"):
            continue
        flat = squash(name)
        if any(flat.startswith(k) for k in keys):
            out.append(name)
    return out


def rank(name):
    low = name.lower()
    tier = next((i for i, ok in enumerate(TIERS) if ok(low)), len(TIERS))
    return (tier, len(name))


def fits(dw, name):
    if any(word in name.lower() for word in DENY):
        return False
    frames = dw.sprites[name]["frames"]
    if not frames:
        return False
    w, h = dw.tpag[frames[0]]["bound"]
    return 8 <= w <= MAX and 8 <= h <= MAX


def choose(dw, boss):
    """A sprite for one name: the override, then the game, then the search."""
    picked = PICKED.get(boss.lower())
    if picked and picked in dw.sprites:
        return picked
    worn = dw.objects.get(WEARS.get(boss.lower(), ""))
    if worn and worn in dw.sprites:
        return worn
    ok = [n for n in candidates(dw, boss) if fits(dw, n)]
    return min(ok, key=rank) if ok else None


def build(dw, names, out_png, contact_png=None):
    """Pack a picture per name. Returns `{name: [x, y, w, h]}` and the misses."""
    cut, missing, chosen = {}, [], {}
    for boss in names:
        name = choose(dw, boss)
        if not name:
            missing.append(boss)
            continue
        try:
            cut[boss] = dw.sprite_frames(name)[0]
            chosen[boss] = name
        except Exception:
            missing.append(boss)

    order = sorted(cut.items(), key=lambda kv: -kv[1].height)
    WIDTH, PAD = 1024, 2
    x = y = shelf = 0
    place = {}
    for boss, im in order:
        if x + im.width + PAD > WIDTH:
            x = 0
            y += shelf + PAD
            shelf = 0
        place[boss] = (x, y, im.width, im.height)
        x += im.width + PAD
        shelf = max(shelf, im.height)
    sheet = Image.new("RGBA", (WIDTH, y + shelf + PAD))
    for boss, im in order:
        px, py, _, _ = place[boss]
        sheet.paste(im, (px, py))
    # lossless WebP: see build.py's `picture` for why
    sheet.save(out_png.with_suffix(".webp"), lossless=True, quality=100, method=6)

    if contact_png:
        contact(cut, chosen, contact_png)
    return place, sorted(missing), sheet.size, chosen


def contact(cut, chosen, path):
    """One labelled cell per entry, to be read by a person before it is believed."""
    CELL, PADX = 150, 8
    cols = 6
    rows = (len(cut) + cols - 1) // cols
    im = Image.new("RGBA", (cols * (CELL + PADX), rows * (CELL + 26)), (20, 14, 22, 255))
    d = ImageDraw.Draw(im)
    for i, (boss, art) in enumerate(sorted(cut.items())):
        cx = (i % cols) * (CELL + PADX)
        cy = (i // cols) * (CELL + 26)
        k = min(1.0, (CELL - 8) / max(art.width, art.height))
        small = art.resize((max(1, int(art.width * k)), max(1, int(art.height * k))), Image.NEAREST)
        im.alpha_composite(small, (cx + (CELL - small.width) // 2, cy + (CELL - small.height) // 2))
        d.text((cx + 4, cy + CELL + 2), boss[:22], fill=(230, 220, 210, 255))
        d.text((cx + 4, cy + CELL + 13), chosen[boss][:30], fill=(140, 130, 140, 255))
    im.save(path)
