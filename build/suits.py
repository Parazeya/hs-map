"""Which class an item is for, argued from what its stats do.

No item says. What an item does say is its stats, and what a class's skills say
is which of those stats they are built out of: Stormweaver's skills take their
damage from `lightning_skill_damage`, the Necromancer's nodes raise
`summon_max_amount`, a Marksman's are wired to `projectile_count`. So the two
sides can be brought together through the thing they have in common — not the
stat names, which disagree, but what the stats are about.

That is what a concept is here: `lightning`, `summon`, `cast`. An item's stats
are read into concepts by what they are named, a class's skills and sub-skills
into the same ones, and an item suits the classes that care about what it gives.

Only stats that point somewhere count. Defense, life and resistances are worth
having on every class and so say nothing about which — scoring them would make
every item suit everyone equally, which is the same as saying nothing at all
while looking like an answer. An item with nothing pointed on it gets no
suggestion, which is the honest reading of a pair of boots that give armour.
"""

import json
import re
from collections import Counter

import skills as skilltree

#: What an item's stat is about, by what it is called.
#:
#: The tests are on the stat's key, which is the game's own name for it, and
#: they are ordered: the first that matches wins, so `summon_attack_speed` is
#: about summons rather than about attacking, and `sentry_attack_speed` about
#: sentries. Without that order the archetype stats would all read as generic
#: speed and the classes they point at would be lost.
ITEM_ABOUT = [
    (r"^summon_|_summon_", "summon"),
    (r"^sentry_|_sentry_|guardian", "sentry"),
    (r"aura", "aura"),
    (r"projectile", "projectile"),
    (r"\bfire\b|fire_", "fire"),
    (r"\bcold\b|cold_|frost|freez", "cold"),
    (r"lightning", "lightning"),
    (r"poison", "poison"),
    (r"arcane|magic_damage|magic_skill|magic_reduction|^skill_damage", "magic"),
    # A crushing blow, a deadly blow, an open wound and ignoring the target's
    # defence are all read off the weapon swing and all scale with physical
    # damage. Nothing in their names says so, but a build carrying them is a
    # physical one — boots with a crushing blow chance are Butcher's boots.
    (r"physical|crushing_blow|deadly_blow|open_wound|ignore_defense", "physical"),
    (r"crit", "crit"),
    (r"ailment|burn|bleed|poisoned|frozen|stasis|stunned", "ailment"),
    # Mana is on everything and says nothing: only the rate a skill is cast at
    # marks a caster.
    (r"cast_rate|when_casting|spell_crit|spell_damage", "cast"),
    # Weapon damage and what is taken back on the swing. `enhanced_damage` is
    # the weapon's own, `stat_base_damage` the attack's, and life or mana
    # stolen per hit is only stolen by hitting — none of them names an attack
    # and all of them are on it. `enhanced_defense` is not: hence `_dmg`
    # spelled out rather than `enhanced_d`.
    (r"attack_speed|attacks_per_second|attack_rating|melee|weapon_damage"
     r"|when_strike|when_attacking|enhanced_damage|enhanced_dmg"
     r"|stat_base_damage|attack_dmg|_per_hit|_steal", "attack"),
    (r"movement|blink|dodge", "movement"),
]

#: The same, for the vocabulary the skills are described in.
SKILL_ABOUT = [
    (r"^summon_|summon", "summon"),
    (r"^sentry_|sentry", "sentry"),
    (r"projectile", "projectile"),
    (r"fire|burning", "fire"),
    (r"cold|frost|freeze|permafrost", "cold"),
    (r"lightning", "lightning"),
    (r"poison|rabies", "poison"),
    (r"arcane", "magic"),
    (r"physical|deadly_blow|crushing_blow", "physical"),
    (r"crit", "crit"),
    (r"ailment|bleed|poisoned|burning|frozen|stasis|stunned", "ailment"),
    (r"cast_rate|mana", "cast"),
    (r"attack_speed|attack_rating|attack_damage", "attack"),
    (r"movement", "movement"),
]

#: A tag or kind a skill wears, and the concept it stands for. These are worth
#: more than a stat mention: a skill tagged `Summon` IS a summon, where a node
#: that happens to raise a summon's speed only touches on it.
WORN = {
    "Summon": "summon", "Sentry": "sentry", "Aura": "aura",
    "Projectile": "projectile", "Cast": "cast", "Attack": "attack",
    "Movement": "movement",
}

#: What is held at arm's length, and what is fired from across the room.
#:
#: A skill says which it is by wearing `Melee` or `Ranged`, and a class that
#: only ever swings cannot make a gun work: Butcher's skills are all melee, so
#: a Glock is not Butcher's gun however good its stats are. Everything else a
#: character wears is worn the same way whatever they fight with, so only
#: weapons are asked this question.
HELD = {
    "Sword": "melee", "Axe": "melee", "Mace": "melee", "Dagger": "melee",
    "Polearm": "melee", "Claw": "melee", "Chainsaw": "melee",
    "Spellblade": "melee",
    "Bow": "ranged", "Gun": "ranged", "Throwing": "ranged",
}

#: The tags that say a skill reaches that far.
REACH = {"Melee": "melee", "Strike": "melee", "Ranged": "ranged"}

#: How much of a class's whole a concept must be before it is said to be its
#: business. A tenth of a class's skills being fire is a fire class; one skill
#: in fifty is a coincidence.
FLOOR = 0.10

#: How near the best a class must come to be worth naming beside it.
#:
#: A helm that pierces lightning resistance is the Stormweaver's before anyone
#: else's — a little over half of that class is lightning — but a quarter of
#: the Bard is lightning too, and a Bard playing that way wants the helm. Cut
#: at two thirds of the best and the Bard is not told; cut here and it is,
#: while the classes with no lightning at all still are not.
NEAR = 0.45


def about(key, rules):
    """What this stat is about, or nothing."""
    for pattern, concept in rules:
        if re.search(pattern, key):
            return concept
    return None


def profile(talents, planner_dir):
    """What each class is made of, as a share per concept.

    A class is read from its own skills: the damage they deal, what they are
    tagged as, the stats their bonuses are taken from, and what their sub-skill
    nodes raise. Shares rather than counts, so a class with fifty skills does
    not out-argue one with eighteen simply by being longer.
    """
    planner = skilltree.read(planner_dir)
    known, _ = skilltree.pair(planner, talents)
    by_key = {t["key"]: t for t in talents}

    weight, reach = {}, {}
    for key, p in known.items():
        cls = (by_key.get(key) or {}).get("class")
        if not cls:
            continue
        for tag in p.get("tags") or []:
            if tag in REACH:
                reach.setdefault(cls, Counter())[REACH[tag]] += 1
        seen = Counter()
        element = p.get("damageType")
        if element:
            seen[skilltree.ELEMENT.get(element, element)] += 3
        for tag in p.get("tags") or []:
            if tag in WORN:
                seen[WORN[tag]] += 2
        if p.get("kind") == "aura":
            seen["aura"] += 2
        for b in p.get("bonusSources") or []:
            got = about(b["stat"], SKILL_ABOUT)
            if got:
                seen[got] += 1
        for side in (p.get("passiveStats") or {}).values():
            for stat in side:
                got = about(stat, SKILL_ABOUT)
                if got:
                    seen[got] += 1
        for node in p.get("subskills") or []:
            for block in (node.get("effects"), (node.get("proc") or {}).get("effects")):
                for side in (block or {}).values():
                    for stat in side:
                        got = about(stat, SKILL_ABOUT)
                        if got:
                            seen[got] += 1
        for concept, n in seen.items():
            weight.setdefault(cls, Counter())[concept] += n

    out = {}
    for cls, seen in weight.items():
        total = sum(seen.values()) or 1
        got = reach.get(cls) or Counter()
        out[cls] = {
            "about": {c: n / total for c, n in seen.items() if n / total >= FLOOR},
            # only what the skills actually say; a class the tables tag neither
            # way is left alone rather than guessed at
            "reach": {k: got[k] for k in ("melee", "ranged") if got[k]},
        }
    return out


def wants(record, vocab):
    """What an item is about, by the stats it carries."""
    seen = set()
    for line in record.get("stats") or []:
        sid = line.get("sid")
        name = vocab[sid] if isinstance(sid, int) and sid < len(vocab) else sid
        got = about(str(name), ITEM_ABOUT)
        if got:
            seen.add(got)
    return seen


def tag(items, profiles, vocab):
    """Give each item the classes its stats are built for.

    A class scores by how much of itself the item feeds. The best is named, and
    with it anything that comes near enough — a fire item is for every fire
    class, and saying only the most fiery of them would be a false precision.
    """
    named = 0
    for record in items.values():
        asked = wants(record, vocab)
        if not asked:
            continue
        # A weapon is only for a class that can fight with it. The test is one
        # way round on purpose: a class is dropped only when its skills say it
        # fights at the other range, never for saying nothing — several classes
        # carry no reach tag at all and excluding them would be inventing a
        # restriction the tables do not state.
        wielded = HELD.get(record.get("type"))
        score = {}
        for cls, p in profiles.items():
            has, reach = p["about"], p["reach"]
            if wielded and reach and wielded not in reach:
                continue
            hit = asked & set(has)
            if hit:
                score[cls] = (sum(has[c] for c in hit), hit)
        if not score:
            continue
        best = max(v[0] for v in score.values())
        picked = sorted(
            ((cls, v) for cls, v in score.items() if v[0] >= best * NEAR),
            key=lambda kv: -kv[1][0],
        )
        # Everything suiting everything is not an answer, and an item carrying
        # nothing sharper than attack speed reaches half the roster. Four names
        # is a reading; the rest are dropped rather than the item, because the
        # four best are still the four best.
        record["suits"] = [{"c": cls, "why": sorted(hit)} for cls, (_, hit) in picked[:4]]
        named += 1
    return named


#: The concept, and the tag the game already has a word for.
AS_TAG = {"summon": "Summon", "sentry": "Sentry", "aura": "Aura",
          "projectile": "Projectile", "movement": "Movement",
          "cast": "Cast", "attack": "Attack"}

#: The two the game words nowhere, said in ours.
AS_PHRASE = {"crit": "Critical", "ailment": "Ailments"}


def words(said):
    """What to call each concept, in every language the game says it in.

    Most of them the game already has a word for and uses in the same sense —
    an element is an element and a summon is a summon — so they are asked for
    rather than written out again here.
    """
    out = {}
    for concept, tag in AS_TAG.items():
        out[concept] = skilltree.tag_word(tag, said)
    for concept in ("fire", "cold", "lightning", "poison", "magic", "physical"):
        out[concept] = said(concept) or {"en": concept.capitalize()}
    for concept, plain in AS_PHRASE.items():
        out[concept] = {"en": plain}
    return out


def unreachable(items, profiles):
    """How many suggestions the reach test threw out, to know it is doing work."""
    n = 0
    for record in items.values():
        wielded = HELD.get(record.get("type"))
        if not wielded:
            continue
        n += sum(1 for p in profiles.values() if p["reach"] and wielded not in p["reach"])
    return n


def report(items, profiles):
    named = sum(1 for r in items.values() if r.get("suits"))
    spread = Counter(c["c"] for r in items.values() for c in r.get("suits") or [])
    reaches = sum(1 for p in profiles.values() if p["reach"])
    print(f"suits    {named} of {len(items)} items say which class they are for, "
          f"out of {len(profiles)} class profiles, {reaches} of which say how far "
          f"they reach")
    if spread:
        top = ", ".join(f"{c} {n}" for c, n in spread.most_common(4))
        print(f"         most often: {top}")
