"""Every item's inventory icon, cut from the game and packed into one sheet.

Three naming schemes are in play and none of them is the translation key the
item data carries:

    helmet_harlequin_crest   Helmet_Harlequin_Crest_spr     the key, as it is
    armors_marsh_shroud      Armor_Marsh_Shroud_spr         category singular
    w_melee_godfather        Weapon_Sword_Godfather_spr     category rewritten
    (display name)           Unique_Godfather_spr           named, not keyed

So the category words are thrown away on both sides and what is left — the part
that actually names the thing — is what is matched. The item's own type breaks
a tie, because `Ring_Signet_spr` and `Amulet_Signet_spr` are both "signet".

Whatever is still not found is reported by name rather than passed over: a
missing icon is a gap in this file, not a fact about the game.
"""

import json
import re
from collections import defaultdict

from PIL import Image

squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

#: The snapshot writes some names with a trailing space and some with two spaces
#: in the middle. The drop tables do not, and the two are compared by name, so a
#: single stray space kept an item out of this loop entirely and it was reported
#: as having no art when the art was sitting there: "Brute's Cord " against
#: `Belts_Brutes_Cord_spr`.
tidy = lambda s: re.sub(r"\s+", " ", s or "").strip().lower()

#: words either side puts in front of the actual name
CATEGORY = {
    "helmet", "helmets", "armor", "armors", "boots", "boot", "gloves", "glove",
    "belt", "belts", "ring", "rings", "amulet", "amulets", "shield", "shields",
    "charm", "charms", "weapon", "weapons", "w", "melee", "ranged", "magic",
    "spell", "polearm", "sword", "axe", "mace", "bow", "crossbow", "staff",
    "wand", "dagger", "spear", "scythe", "claw", "cane", "orb", "book", "tome",
    "flask", "flasks", "vial", "consumable", "consumables", "potion",
    "potions", "unique", "pickup", "the", "of", "s",
    # The art marks base gear "Normal" and the item data does not, so
    # `armors_boneweave` and `Armors_Normal_Boneweave_spr` did not meet. And a
    # rune is named twice over on the item side and once on the art's:
    # `socketable_el_rune` against `Rune_El_spr`.
    "normal", "socketable", "rune", "runes",
}

#: the item type, as the data spells it, and how the art spells it
TYPE_HINT = {
    "helmet": "helmet", "body armor": "armor", "boots": "boots",
    "gloves": "gloves", "belt": "belt", "ring": "ring", "amulet": "amulet",
    "shield": "shield", "charm": "charm", "flask": "flask",
    "potion": "potions",
}


#: The category word the art puts in a sprite name, and the item type it means.
#:
#: Used to refuse a match, never to make one. `core` throws the category words
#: away on both sides so that `armors_marsh_shroud` can find
#: `Armor_Marsh_Shroud_spr` — but thrown away, "Molten Dagger" and "Molten Orb"
#: are both just "molten", and one orb came to stand for a dagger and a sword at
#: once. The art saying orb where the item says dagger settles it: whatever that
#: sprite draws, it is not this item.
#:
#: It caught five: a bow wearing the marksman's gloves, an axe and a sword
#: wearing the crystal wand, a spear wearing Odin's axe, and a helmet wearing a
#: flail — that last one mine, from a fallback added without a type to hold it.
ART_KIND = {
    "helmet": "helmet", "helmets": "helmet",
    "armor": "body armor", "armors": "body armor",
    "boot": "boots", "boots": "boots",
    "glove": "gloves", "gloves": "gloves",
    "belt": "belt", "belts": "belt",
    "ring": "ring", "rings": "ring",
    "amulet": "amulet", "amulets": "amulet",
    "shield": "shield", "shields": "shield",
    "charm": "charm", "charms": "charm",
    # one thing under two words: the art says flask, the data says potion
    "flask": "potion", "flasks": "potion",
    "potion": "potion", "potions": "potion",
    "sword": "sword", "axe": "axe", "mace": "mace", "bow": "bow",
    "staff": "staff", "wand": "wand", "dagger": "dagger", "cane": "cane",
    "orb": "orb", "book": "book", "gun": "gun", "chainsaw": "chainsaw",
    "claw": "claw", "scythe": "scythe", "throwing": "throwing",
    "polearm": "polearm", "spear": "polearm", "spellblade": "spellblade",
}


#: the types the art has a word for, and so can be argued with
NAMED_KINDS = set(ART_KIND.values())


def contradicts(sprite, kind):
    """Whether the art names a category this item is not.

    Silent about a type the art has no word for. A Relic is not a helmet or a
    sword or any other slot, so `Relic_Frozen_Orb_spr` saying "orb" says nothing
    against it — and the rule, asked anyway, threw out twenty-nine relics that
    had art sitting right there under their own names.
    """
    kind = (kind or "").lower()
    if kind not in NAMED_KINDS:
        return False
    said = {ART_KIND[w.lower()] for w in re.split(r"[^A-Za-z0-9]+", sprite)
            if w.lower() in ART_KIND}
    return bool(said) and kind not in said


def core(text):
    """Whatever is left once the category words are gone."""
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", text) if p]
    kept = [p for p in parts if p.lower() not in CATEGORY]
    return squash("".join(kept or parts))


def index(dw):
    """core name -> the sprites that could be it, icons before ground drops."""
    out = defaultdict(list)
    for name in dw.sprites:
        if not name.endswith("_spr"):
            continue
        stem = name[:-4]
        out[core(stem)].append(name)
    for key in out:
        out[key].sort(key=lambda n: (n.startswith("Pickup_"), len(n)))
    return out


#: An inventory icon is a few cells across. The biggest in the game is well
#: inside this; anything past it matched something that is not an item — a
#: moon, a piece of scenery — and taking it would put a planet in the list.
#:
#: 96 was one pixel too mean: Valkyrie's Thunder Javelin is drawn 31 by 97, and
#: a javelin is a long thing to be drawn.
MAX_ICON = 170

#: Named outright, because no rule can reach them.
#:
#: Four are the art keeping a name the item no longer has — there is no item
#: called Lost Dieties Sigil, Hallgar's Dreadful Wall or Hello Steve, and
#: `Weapon_Bow_Amitiels_spr` is the only Amitiel there is. Each was checked for a
#: rival: a sprite is only claimed here when no other item in the game answers to
#: the name on it, which is why Arch Angel's Phase Blade is not in this list —
#: the only phase blade art belongs to the Holy Warrior's, and that item exists.
NAMED = {
    "hello its me, steve!": "Charms_Hello_Steve_spr",
    # The art drops the owner from one and misspells him in the other: no item
    # is plainly called Warlock, and none is called Thots Agony.
    "metal vocalist's warlock": "Weapon_Mace_Warlock_spr",
    "thoth's agony": "Amulet_Thots_Agony_spr",
    # A puppet is a doll. `Charms_Voodoo_Puppet_spr` is the only charm sprite in
    # the game whose name answers to no item, and Voodoo Doll was the only charm
    # left without art.
    "voodoo doll": "Charms_Voodoo_Puppet_spr",
    # Three that share their picture with the thing they are a better version
    # of, deliberately: same slot, same name but for a word, and the levels say
    # which came first. Holy Warrior's Phase Blade is a level 66 Satanic sword
    # and the Arch Angel's a level 100 Heroic one; Clafaxier is a level 23 wand
    # and its Legacy a level 99 one; Perkele and Suatana are both level 92
    # shields. The art is named for the half they have in common, so it belongs
    # to both — this is the one place two items may draw the same sprite, and
    # the difference from a mismatch is that it is written down here.
    # The dragon set is drawn under a name no item has. There are five pieces of
    # `Ruby_Dragon` gear art — helmet, armour, amulet, ring and charm — and
    # nothing in the game is called Ruby Dragon anything. Facing them are five
    # level 100 dragon items, one per slot. The charm end of it was already
    # matched by the fuzzy rule on its own: Dragon's Heart draws
    # `Charms_Ruby_Dragon_Heart_spr`, which is what says the other four are not
    # a guess.
    "dragon knight's helmet": "Helmet_Ruby_Dragon_Helmet_spr",
    "dragon knight's vanguard": "Armor_Ruby_Dragon_Armor_spr",
    "dragon's eye": "Amulet_Ruby_Dragon_Amulet_spr",
    "dragon's blessing": "Rings_Ruby_Dragon_Ring_spr",
    "arch angel's phase blade": "Weapon_Sword_Holy_Warriors_Phase_Blade_spr",
    "clafaxier's legacy": "Weapon_Wand_Clafaxier_spr",
    "suomi finland suatana": "Shields_Suomi_Finland_Perkele_spr",
    "st. amitiel's truth": "Weapon_Bow_Amitiels_spr",
    "lost dieties authority": "Amulet_Lost_Dieties_Sigil_spr",
    "st. hallgar's bloodforged aegis": "Shields_Hallgars_Dreadful_Wall_spr",
}


def sized(dw, name):
    """The sprite's own bounds, without decoding its texture page."""
    frames = dw.sprites[name]["frames"]
    if not frames:
        return None
    w, h = dw.tpag[frames[0]]["bound"]
    return (w, h) if 0 < w <= MAX_ICON and 0 < h <= MAX_ICON else None


def pick(dw, sprites, kind):
    """The first icon-sized candidate, with the item's own type breaking a tie.

    `Signet` is both a ring and an amulet, and the art says which.
    """
    fits = [n for n in sprites if sized(dw, n) and not contradicts(n, kind)]
    if not fits:
        return None
    if len(fits) > 1 and kind:
        want = TYPE_HINT.get(kind.lower())
        if want:
            for n in fits:
                if n.lower().startswith(want):
                    return n
    return fits[0]


def words(text):
    """The naming words, stemmed to their first five letters.

    Five is enough to survive the spelling the two sides disagree about —
    `fumas` against `Fumacinas`, `amithiels` against `amitiels`, `helm` against
    `helmet` — and short enough not to glue unrelated names together.
    """
    parts = re.split(r"[^A-Za-z0-9]+", text)
    return {p.lower()[:5] for p in parts if p and p.lower() not in CATEGORY}


def nearest(dw, by_words, item_words, kind):
    """The best-overlapping sprite, or nothing if nothing is close enough.

    A last resort for the names where the key and the art disagree about word
    order (`armors_mantle_exiled_pagan` is drawn by `Armor_Exiled_Pagans_Mantle`)
    rather than about spelling. Held to a high bar and to the item's own type,
    because a wrong icon is worse than none: it says something false about an
    item quietly, where a blank says nothing at all.
    """
    want = TYPE_HINT.get((kind or "").lower())
    best, score = None, 0.0
    for name, tokens in by_words:
        if want and not name.lower().startswith(want):
            continue
        if contradicts(name, kind):
            continue
        if not tokens:
            continue
        overlap = len(item_words & tokens) / len(item_words | tokens)
        # A tie goes to the inventory icon, not the thing lying on the ground:
        # `Pickup_` and its twin carry the same naming words, so three items were
        # drawn by whichever the sprite table happened to list first.
        if overlap > score or (overlap == score and best
                               and best.startswith("Pickup_")
                               and not name.startswith("Pickup_")):
            best, score = name, overlap
    if score >= 0.6 and sized(dw, best):
        return best
    return None


def build(dw, items, wanted, out_png):
    """Pack the icons of `wanted` (lower-case names) into one sheet.

    Returns `{name: [x, y, w, h]}` and the list of names with no sprite.
    """
    by_core = index(dw)
    by_words = [(n, words(n[:-4])) for n in dw.sprites if n.endswith("_spr")]
    # the second pass has only a name to go on, and a match with nothing holding
    # it is how a helmet came to wear a flail
    kind_of = {tidy((it.get("metadata") or {}).get("name")):
               (it.get("metadata") or {}).get("type") for it in items}
    # A runeword is not a thing with a picture. It is what a base becomes when
    # the runes go in, so the art it wears is the base's — and there is no
    # sprite anywhere in the game under a runeword's name. Every match one gets
    # by name is therefore some other item's picture, and the names are close
    # enough that it lands: the runeword "Justice" took the Justice tarot
    # card's scales, "Shroud of Elements" a hood, "Shadow" a black disc. So
    # they are kept out of the matching entirely and given the emblem below.
    runewords = {tidy((it.get("metadata") or {}).get("name"))
                 for it in items if (it.get("metadata") or {}).get("rarity") == "Runeword"}
    runewords.discard("")

    cut = {}
    chosen = {}          # item -> the sprite it was cut from, for arguing with
    missing = []
    guessed = []
    for it in items:
        m = it.get("metadata") or {}
        tk, nm = m.get("tkey"), m.get("name")
        if not tk or not nm:
            continue
        low = tidy(nm)
        if low not in wanted or low in cut or low in runewords:
            continue
        # The game names a boss's soulgem after the boss and nothing else:
        # `socketable_gem_gurag` is drawn by `Boss_Gemstone_Gurag_spr`. Neither
        # the key nor the display name shares a word with that, so nine gems
        # came out blank. Read off the key rather than written out: the nine
        # follow the same rule and a tenth boss would too.
        gem = re.fullmatch(r"socketable_gem_(\w+)", tk or "")
        if gem:
            art = f"Boss_Gemstone_{gem.group(1).capitalize()}_spr"
            if art in dw.sprites:
                try:
                    cut[low] = dw.sprite_frames(art)[0]
                    chosen[low] = art
                    continue
                except Exception:
                    pass
        named = NAMED.get(low)
        if named and named in dw.sprites:
            try:
                cut[low] = dw.sprite_frames(named)[0]
                chosen[low] = named
                continue
            except Exception:
                pass
        for key in (core(tk), core(nm)):
            got = by_core.get(key)
            if not got:
                continue
            name = pick(dw, got, m.get("type"))
            if not name:
                continue
            try:
                cut[low] = dw.sprite_frames(name)[0]
                chosen[low] = name
            except Exception:
                break
            break
        if low not in cut:
            name = nearest(dw, by_words, words(tk) | words(nm), m.get("type"))
            if name:
                try:
                    cut[low] = dw.sprite_frames(name)[0]
                    chosen[low] = name
                    guessed.append(f"{nm} -> {name}")
                except Exception:
                    pass
        if low not in cut:
            missing.append(nm)

    # Some items the drop tables know are not in the datamined snapshot at all,
    # so the loop above never sees them and never asks. They still have a name,
    # and a name is enough to look with.
    for low in sorted(wanted - set(cut) - runewords):
        name = None
        want = kind_of.get(low)
        got = by_core.get(core(low))
        if got:
            name = pick(dw, got, want)
        # and the same last resort the loop above gets. Without it a possessive
        # was enough to lose an icon: `core` keeps "brutecord" for the item and
        # "brutescord" for the sprite, which are not equal, while the word test
        # stems both to "brute" and matches.
        if not name:
            name = nearest(dw, by_words, words(low), want)
        if not name:
            continue
        try:
            cut[low] = dw.sprite_frames(name)[0]
            chosen[low] = name
            guessed.append(f"{low} -> {name} (by name; not in the snapshot)")
        except Exception:
            pass
    missing = [m for m in missing if m.lower() not in cut]

    # A runeword has no picture of its own, and cannot: it is a thing you make
    # in a base, and what it wears is the base's art. The game draws it as the
    # emblem in its own journal — four runes around a stone — and that is what
    # goes here, the same way `portraits.py` gives a kind of place its door
    # rather than a portrait of one. 94 of the 147 icons the codex was missing
    # were runewords, all of them blank.
    #
    # `Inventory_Equipped_*_Runeword_spr` are not this: they are the empty
    # slot plates the inventory draws behind an item, brown and featureless.
    #
    # Cut once and shared, not packed ninety-four times: one 128 by 128 picture
    # per runeword took the sheet from 3,751 rows to 5,488 for one image.
    EMBLEM = "Journal_Runewords_spr"
    emblem_for = set()
    if EMBLEM in dw.sprites:
        try:
            art = dw.sprite_frames(EMBLEM)[0]
        except Exception:
            art = None
        if art is not None:
            for low in sorted(runewords & set(wanted)):
                emblem_for.add(low)
                chosen[low] = EMBLEM
            if emblem_for:
                cut[EMBLEM] = art
                missing = [m for m in missing if tidy(m) not in emblem_for]

    # shelf-packed by height, which for a few hundred small icons is as good as
    # anything cleverer and fits in a dozen lines
    order = sorted(cut.items(), key=lambda kv: -kv[1].height)
    WIDTH, PAD = 1024, 1
    x = y = shelf = 0
    place = {}
    for name, im in order:
        if x + im.width + PAD > WIDTH:
            x = 0
            y += shelf + PAD
            shelf = 0
        place[name] = (x, y, im.width, im.height)
        x += im.width + PAD
        shelf = max(shelf, im.height)
    sheet = Image.new("RGBA", (WIDTH, y + shelf + PAD))
    for name, im in order:
        px, py, _, _ = place[name]
        sheet.paste(im, (px, py))
    # After the sheet is drawn, because the paste reads `place` by the same key
    # it was packed under: every runeword points at the one emblem, and the
    # sentinel that carried it is not an item and does not go out.
    for low in emblem_for:
        place[low] = place[EMBLEM]
    place.pop(EMBLEM, None)
    # lossless WebP: see build.py's `picture` for why
    sheet.save(out_png.with_suffix(".webp"), lossless=True, quality=100, method=6)

    return place, sorted(missing), sheet.size, sorted(guessed), chosen
