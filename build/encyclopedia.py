"""Render every item record from one verified Extractor generation.

The bundle supplies numeric effects, translation tables, variants and evidence.
Unresolved values and references survive until their meanings can be decoded;
external catalogue enrichments carry explicit provenance in the generated data.
"""

import copy
import hashlib
import json
import math
import re
import item_grant_slots
import item_effects
import item_conditions
from data_bundle import drop_denominator, field_is_current, item_records

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

#: Compatibility names for reference snapshots without a current vocabulary.
#: Current-game stat 20 is named by the Extractor's source-bound GetItemStat /
#: localized `sockets` display-use certificate; it does not use this fallback.
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


def source_value_shape(stat):
    """Keep the source array's arity separate from its known numeric bounds."""
    for source in (stat.get("argument_interpretation"), stat.get("raw")):
        if not isinstance(source, dict):
            continue
        args = source.get("args")
        if not isinstance(args, list) or len(args) < 2:
            continue
        value = args[1]
        if isinstance(value, dict) and value.get("kind") == "list" and isinstance(value.get("value"), list):
            return {"kind": "list", "length": len(value["value"])}
    return None


def stat_line(s, stat_names=None):
    """One stat as `{sid, text, unit, min, max, of}`.

    `min2`/`max2` are the second number a two-part stat carries — "5% chance to
    cast Shadowflames at level 1 to 3" is one stat with two ranges — and the
    named fields beside them say which spell, class or range it is about.
    """
    # The current export identifies random slots separately from candidate
    # stats. Only the bundle's verified selector mapping determines their pool.
    if s.get("kind") == "random_stat_slot" or s.get("sid") == "unholy_none":
        selector = s.get("selector", s.get("min1"))
        active = s.get("active", type(selector) in (int, float) and selector > 0)
        return {"sid": "unholy_none", "pool": selector, "active": active,
                "slot": s.get("slot"), "text": "Unholy", "raw": dict(s)}
    name_contract = (stat_names or {}).get("name_contract")
    vocabulary_supported = name_contract is None or (
        name_contract.get("status") != "unsupported"
        and any(name_contract.get(field) is True for field in
                ("source_supported", "filter_supported", "tooltip_supported")))
    if not s.get("sid") and stat_names and vocabulary_supported:
        vocabulary = (stat_names.get("by_id") or {}).get(str(s.get("id")), {})
        label = vocabulary.get("tooltip_key") or vocabulary.get("filter_key")
        if label:
            s = dict(s, sid=label)
    # A supplied game vocabulary is authoritative even when it cannot name an
    # id. The reference lookup must not recreate an old label after a decoder
    # explicitly withholds it for the current source.
    if s.get("sid") is None and stat_names is None and s.get("id") in BY_ID:
        s = dict(s, sid=BY_ID[s["id"]])
    if not s.get("sid"):
        # Keep numeric values and effect references even before their meaning
        # has been decoded. The raw entry is evidence, not an invented stat.
        s = dict(s, sid=f"unresolved_{s.get('id', 'value')}")
    out = {
        "sid": s.get("sid"),
        "id": s.get("id"),
        "min": s.get("min1"),
        "max": s.get("max1"),
    }
    text, unit = phrase(s.get("sid"))
    if s["sid"].startswith("unresolved_"):
        text = "Unidentified effect"
        out["unresolved"] = True
        out["raw"] = dict(s)
    out["text"] = text
    if unit:
        out["unit"] = unit
    shape = source_value_shape(s)
    if shape is not None:
        out["value_shape"] = shape
    # A relic's stat is not rolled but climbed: the item carries the ten values
    # the stat takes at the relic's ten levels, and no min or max at all, so
    # without this those lines printed their name and no number.
    if isinstance(s.get("values"), list) and s["values"]:
        ladder = list(s["values"])
        out["values"] = ladder
        out["rank"] = 1
        # Positions are levels. An unknown first level must not inherit the
        # first known value later in the vector.
        if out["min"] is None:
            out["min"] = ladder[0]
        if out["max"] is None:
            out["max"] = ladder[-1]
    for field in ("expression", "reference", "unknown", "source", "raw", "status", "kind",
                  "argument_interpretation", "value_expression", "value_kind", "resource_references",
                  "native_observation", "outer_selector", "inner_stat_key", "scope", "runtime_condition"):
        if field in s:
            out.setdefault(field, s[field])
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


def out_of_key(tkey, kind):
    """`w_throwing_darkmoon_deck` read as "Darkmoon Deck"."""
    parts = [p for p in (tkey or "").split("_") if p]
    while parts and (len(parts[0]) == 1 or parts[0].lower() == str(kind).lower()):
        parts.pop(0)
    return " ".join(p[:1].upper() + p[1:] for p in parts)


def weapons(row):
    """The weapons a runeword may be made in, named."""
    native = (row.get("runeword") or {}).get("eligibility", {}).get("weapon_type")
    if native is not None:
        return [value.get("name") or value.get("native_label") or str(value["id"]) for value in native]
    got = row.get("runewordWeaponType")
    if not isinstance(got, list):
        return []
    return [WEAPON[n - 1] if 1 <= n <= len(WEAPON) else str(n) for n in got]


def variants(it, stat_names=None, conditions=None, socket_items=None, said=None):
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
    native = it.get("stats_channels") or {}
    labels = {"runeword_base": "runeword base modifiers",
              "runeword_two_handed": "two-handed", "runeword_armor": "in armour",
              "socket": "socket condition", "damage_type": "damage type condition"}
    for channel, group in native.items():
        rows = group.get("stats") or []
        if rows:
            lines=[stat_line(s,stat_names) for s in rows if isinstance(s,dict)]
            if channel in item_conditions.DOMAINS:
                for separate in item_conditions.partition(lines,channel):
                    condition=item_conditions.describe(separate,channel,(it.get('metadata') or {}).get('tkey'),
                                                       socket_items or {},said or (lambda _:None),conditions)
                    label=(condition.get('names') or {}).get('en')
                    when=(('With '+label if channel=='socket' else 'Damage type: '+label) if label else labels[channel])
                    out.append(dict(id=separate['id'],when=when,channel=channel,scope=group.get('scope'),
                                    condition=condition,outer_selector=separate['outer_selector'],stats=separate['stats']))
            else:
                out.append({"id":'storage:'+channel,"when": labels.get(channel, channel), "channel": channel,
                            "scope": group.get("scope"),"stats":lines})
    for field, when in VARIANT.items():
        rows = it.get(field) or []
        if not rows:
            continue
        if all(isinstance(r, dict) and r.get("stats") for r in rows):
            for index,r in enumerate(rows):
                named = r.get("ID")
                out.append({
                    "id":f'legacy:{field}:{index}',
                    "when": f"with a {named}" if named else when,
                    "stats": [stat_line(s, stat_names) for s in r["stats"] if isinstance(s, dict)],
                })
        else:
            out.append({"id":f'legacy:{field}',"when": when,
                        "stats": [stat_line(s, stat_names) for s in rows if isinstance(s, dict)]})
    return [v for v in out if v["stats"]]


def sockets(row, by_name, tidy, by_rune_id=None):
    """A runeword's recipe: what goes in it, in order, as item keys.

    `runewordSockets` names them the way the game does — its runes are renamed
    from the ones players know, so Eld is "Old" and Ith is "Uth" — and fifteen of
    the fifty-two names are not runes at all but orbs. Both are ordinary items
    with pages and icons of their own, so the recipe is stored as keys and the
    page looks the rest up.
    """
    native = row.get("runeword_recipe")
    if isinstance(native, dict) and isinstance(native.get("value"), list):
        # Native IDs are ordered, may repeat, and are a separate domain until
        # the runtime's socketable-ID join has been independently certified.
        out = []
        word = row.get("runeword") or {}
        bound = word.get("recipe_items") or []
        domain = word.get("recipe_item_domain") or {}
        for index, rune_id in enumerate(native["value"]):
            binding = bound[index] if index < len(bound) else {}
            item = None
            if (domain.get("status") == "native_runtime_binding" and domain.get("packet_field") == "b"
                    and domain.get("item_type") == 15 and binding.get("rune_id") == rune_id
                    and binding.get("status") == "source_bound_item_identity" and binding.get("key")):
                item = {"key": binding["key"], "name": binding.get("name")}
            if item is None:
                item = (by_rune_id or {}).get(rune_id)
            out.append(dict(item, id=rune_id) if item else {"id": rune_id, "unresolved": True})
        return out
    out = []
    for name in row.get("runewordSockets") or []:
        key = by_name.get(tidy(name))
        out.append({"name": name, "key": key} if key else {"name": name})
    return out


def made_in(row, current_type_names):
    native = (row.get("runeword") or {}).get("eligibility", {}).get("item_type")
    if native is not None:
        labels = []
        for value in native:
            names = current_type_names.get(value.get("id"), set())
            labels.append(next(iter(names)) if len(names) == 1 else
                          value.get("name") or value.get("native_label") or str(value["id"]))
        return " or ".join(labels) or None
    legacy = row.get("runewordItemType")
    return (BASE.get(legacy) if isinstance(legacy, int) else
            " or ".join(BASE.get(n, str(n)) for n in legacy or [])) or None


#: The stat a potion states its talent in, and the one that states the range
#: of levels it grants it at. The game writes "+[1-5] to Drunken Kung Fu" out
#: of the pair.
GRANTS, GRANT_LEVELS = "singular_skill", "stat_random_skill"
NATIVE_TALENT_PROFILE = "hero-siege-26297349-native-talent-map-keys-v1"
NATIVE_GRANT_DOMAIN_PROFILE = "hero-siege-26297349-stat202-talent-map-key-v1"
NATIVE_TALENT_SOURCE_SHA256 = "2c248a580810fbe389d2f15fcf809f2dac51d5815c60e888353071fe7dfc57fe"
NATIVE_TALENT_WITNESS_SHA256 = "26668afafd26aa2596d8c66c8549aaa1ff54e20b5c6f2396a67b6fc6266ec911"
NATIVE_TALENT_CONTRACT_ID = "e5ab15dcb1d906145c0613d0739a8551c44abd46a86056ba83b24ef67053223a"
NATIVE_GRANT_DOMAIN_REFERENCE_SHA256 = "21cbd237cc2d2c3d12ca028afef46b0c7e8dba6f5802d20b47714798ee52de58"
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
    """Legacy reference-only numbering inference; never a native ID proof.

    Older reference snapshots inferred a relationship between item-key names
    and table positions. This preserves that heuristic only for those inputs;
    the positions are not the sparse keys used by GetTalentInfo.
    """
    if number is None or not got.get("id"):
        return True
    drift = number - got["id"]
    below = [d for at, d in pins if at <= number]
    above = [d for at, d in pins if at >= number]
    return drift >= (below[-1] if below else 0) and (not above or drift <= above[0])


def pinned(raw_items, talents):
    """Legacy reference-only drift anchors, excluded from native lookups.

    These differences measure a historical reference-table assumption, not
    native insertion IDs. They must never repair a current native lookup.
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
    """An explicitly inferred legacy reference match, never a native ID join.

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


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def native_talent_context(rows, contract, source_sha256):
    """Validate the producer's native insertion-key catalog and row bindings.

    Returning an empty native context is deliberate: unsupported current data
    cannot fall through to item keys, planner suggestions or ordinal offsets.
    """
    context = {"by_id": {}, "status": "unsupported"}
    if not isinstance(contract, dict) or not isinstance(source_sha256, str):
        return context
    source_sha256 = source_sha256.lower()
    if source_sha256 != NATIVE_TALENT_SOURCE_SHA256:
        return context
    domain = contract.get("grant_domain")
    if not isinstance(domain, dict) or any((
            domain.get("status") != "complete_source_bound_grant_lookup",
            domain.get("profile") != NATIVE_GRANT_DOMAIN_PROFILE,
            domain.get("source_sha256") != source_sha256,
            type(domain.get("stat_id")) is not int or domain["stat_id"] != 202,
            domain.get("lookup") != "GetTalentInfo",
            type(domain.get("lookup_argument_index")) is not int or domain["lookup_argument_index"] != 0,
            domain.get("map_variable") != "talentStructMap",
            domain.get("same_key_transport_certified") is not True,
            domain.get("native_consumer_bound") is not True,
            domain.get("value_transform") != "identity",
            domain.get("runtime_value_inferred") is not False)):
        return context
    domain_proof = domain.get("proof")
    if (not isinstance(domain_proof, dict) or domain_proof.get("sha256") != NATIVE_GRANT_DOMAIN_REFERENCE_SHA256
            or domain_proof.get("reference") != "reference/native-evidence/item-talent-id-domain-26297349.json"):
        return context
    catalog = contract.get("record_sources")
    witness = contract.get("witness") or {}
    consumer = contract.get("consumer") or {}
    if not isinstance(catalog, list) or not catalog or not isinstance(witness, dict) or not isinstance(consumer, dict):
        return context
    if any((type(contract.get("schema_version")) is not int or contract["schema_version"] != 1,
            contract.get("status") != "complete_source_bound_native_insertion_keys",
            contract.get("profile") != NATIVE_TALENT_PROFILE,
            contract.get("source") != "Hero_Siege.exe",
            contract.get("source_sha256") != source_sha256,
            contract.get("native_numeric_map_keys_certified") is not True,
            contract.get("ordinal_fallback") is not False,
            consumer.get("script") != "GetTalentInfo",
            consumer.get("map_variable") != "talentStructMap",
            consumer.get("lookup_key") != "unrenumbered_first_script_argument",
            type(contract.get("records")) is not int or contract["records"] != len(catalog),
            witness.get("sha256") != NATIVE_TALENT_WITNESS_SHA256,
            contract.get("native_contract_id") != NATIVE_TALENT_CONTRACT_ID)):
        return context
    bindings, owners = {}, set()
    try:
        for binding in catalog:
            if not isinstance(binding, dict):
                return context
            number, key, cls = binding.get("native_id"), binding.get("key"), binding.get("class")
            if (type(number) is not int or number <= 0 or number in bindings
                    or not isinstance(key, str) or not key or not isinstance(cls, str)
                    or (key, cls) in owners or binding.get("source") != "Hero_Siege.exe"
                    or binding.get("source_sha256") != source_sha256
                    or binding.get("scope") != "static_native_numeric_map_insertion_key"
                    or binding.get("receiver") != "reviewed_same_fresh_talent_instance"
                    or any(type(binding.get(field)) is not int or binding[field] <= 0
                           for field in ("case_entry_rva", "key_anchor_rva", "map_set_call_rva"))):
                return context
            unsigned = {key: value for key, value in binding.items() if key != "binding_sha256"}
            if binding.get("binding_sha256") != _digest(unsigned):
                return context
            bindings[number] = binding
            owners.add((key, cls))
        payload = {"profile": contract["profile"], "source_sha256": source_sha256,
                   "witness_sha256": witness["sha256"],
                   "record_sources": [bindings[number] for number in sorted(bindings)]}
        if contract.get("native_contract_id") != _digest(payload):
            return context
    except (TypeError, ValueError):
        return context
    grouped = {}
    for row in rows:
        if isinstance(row, dict) and type(row.get("id")) is int:
            grouped.setdefault(row["id"], []).append(row)
    for number, candidates in grouped.items():
        if len(candidates) != 1:
            continue
        row, binding = candidates[0], bindings.get(number)
        if (binding is not None and row.get("key") == binding["key"]
                and row.get("class") == binding["class"] and row.get("id_source") == binding):
            context["by_id"][number] = row
    context.update(status="supported", source_sha256=source_sha256,
                   native_contract_id=contract["native_contract_id"], grant_domain=domain)
    return context


def _native_grant_number(line, stat_id=202):
    source = line.get("source")
    if line.get("status") != "decoded" or not isinstance(source, dict) or source.get("file") != "Hero_Siege.exe":
        return None
    value = line.get("min")
    if (type(value) not in (int, float) or value <= 0 or value > 2 ** 53
            or not math.isfinite(value) or value != int(value)):
        return None
    if line.get("max") is not None and (type(line["max"]) not in (int, float) or line["max"] != value):
        return None
    if "values" in line or "value_shape" in line:
        return None
    observed = item_grant_slots.native_call(line)
    if not isinstance(observed, dict) or not isinstance(observed.get("args"), list) or len(observed["args"]) != 2:
        return None

    def scalar(argument):
        if not isinstance(argument, dict) or argument.get("kind") != "value":
            return None
        constant = argument.get("value")
        if not isinstance(constant, dict) or constant.get("kind") not in ("int", "real"):
            return None
        number = constant.get("value")
        return number if type(number) in (int, float) else None

    if scalar(observed["args"][0]) != stat_id or scalar(observed["args"][1]) != value:
        return None
    return int(value)


def native_aura_granted(stats, said, native):
    domain = native.get("aura_slots")
    if not item_grant_slots.valid_domain(domain, native.get("source_sha256")):
        return []
    result = []
    for slot in domain["slots"]:
        selectors = [s for s in stats if type(s.get("id")) is int and s["id"] == slot["selector_stat_id"]]
        if len(selectors) != 1:
            continue
        selector = selectors[0]
        number = _native_grant_number(selector, slot["selector_stat_id"])
        talent = native["by_id"].get(number)
        if talent is None:
            continue
        operands = [s for s in stats if type(s.get("id")) is int and s["id"] == slot["level_stat_id"]]
        levels = item_grant_slots.level_range(operands[0], slot["level_stat_id"]) if len(operands) == 1 else None
        represented = [selector] + ([operands[0]] if levels is not None else [])
        grant = spoken(talent, levels, said)
        grant.update(kind="aura", holder_only=slot.get("holder_only", False),
                     talent_id=number, talent_key=talent["key"], talent_class=talent["class"],
                     source_stats=copy.deepcopy(represented),
                     provenance={"kind": "decoded", "basis": "source-bound item talent slot",
                                 "source": "Hero_Siege.exe", "source_sha256": native["source_sha256"],
                                 "native_contract_id": native["native_contract_id"],
                                 "slot_contract_sha256": domain["certificate_sha256"],
                                 "selector_stat_id": slot["selector_stat_id"], "level_stat_id": slot["level_stat_id"],
                                 "levels_scope": "base_item_definition", "runtime_value_inferred": False})
        stats[:] = [s for s in stats if all(s is not used for used in represented)]
        result.append(grant)
    return result


def native_skill_granted(stats, said, native):
    domain = native.get("aura_slots")
    if not item_grant_slots.valid_domain(domain, native.get("source_sha256")):
        return []
    result = []
    for slot in domain["skill_slots"]:
        selectors = [s for s in stats if type(s.get("id")) is int and s["id"] == slot["selector_stat_id"]]
        if len(selectors) != 1:
            continue
        selector = selectors[0]
        number = _native_grant_number(selector, slot["selector_stat_id"])
        talent = native["by_id"].get(number)
        selected_range = item_grant_slots.level_range(selector, slot["selector_stat_id"]) if number is None else None
        # A random skill keeps its selection range; no particular talent is invented.
        random = (selected_range is not None and selected_range[0] > 0
                  and selected_range[0] < selected_range[1]
                  and all(n in native["by_id"] for n in selected_range))
        if talent is None and not random:
            continue
        operands = [s for s in stats if type(s.get("id")) is int and s["id"] == slot["level_stat_id"]]
        level = item_grant_slots.skill_levels(operands[0], slot["level_stat_id"]) if len(operands) == 1 else None
        represented = [selector] + ([operands[0]] if level is not None else [])
        grant = spoken(talent, None, said) if talent else {"random_skill": True, "skill_selector_range": selected_range,
                                                         "levels": None, "lines": []}
        if talent:
            grant.update(talent_id=number, talent_key=talent["key"], talent_class=talent["class"])
        if level:
            grant.update(level)
        grant.update(kind="skill", source_stats=copy.deepcopy(represented),
                     provenance={"kind": "decoded", "basis": "source-bound item skill slot",
                                 "source": "Hero_Siege.exe", "source_sha256": native["source_sha256"],
                                 "native_contract_id": native["native_contract_id"],
                                 "slot_contract_sha256": domain["certificate_sha256"],
                                 "selector_stat_id": slot["selector_stat_id"], "level_stat_id": slot["level_stat_id"],
                                 "levels_scope": "base_item_definition", "runtime_value_inferred": False})
        stats[:] = [s for s in stats if all(s is not used for used in represented)]
        result.append(grant)
    return result


def native_triggered(stats, said, native):
    domain = native.get('item_effects')
    if not item_effects.valid_domain(domain, native.get('source_sha256')):
        return []
    result=[]
    for slot in domain['settings']['trigger_slots']:
        selectors=[s for s in stats if s.get('id')==slot['selector_stat_id']]
        if len(selectors)!=1:
            continue
        number=_native_grant_number(selectors[0],slot['selector_stat_id'])
        talent=native['by_id'].get(number)
        if talent is None:
            continue
        levels=[s for s in stats if s.get('id')==slot['level_stat_id']]
        chances=[s for s in stats if s.get('id')==slot['chance_stat_id']]
        level=item_effects.quantity(levels[0],slot['level_stat_id'],integral=True) if len(levels)==1 else None
        chance=item_effects.quantity(chances[0],slot['chance_stat_id'],ceiling=100) if len(chances)==1 else None
        grant=spoken(talent,level.get('range') if level else None,said)
        represented=[selectors[0]]
        if level:
            represented+=levels
            if 'values' in level:
                grant['level_values']=level['values']
        if chance:
            represented+=chances
            grant['chance_values' if 'values' in chance else 'chance']=chance.get('values',chance.get('range'))
        grant.update(kind='trigger',talent_id=number,talent_key=talent['key'],talent_class=talent['class'],
                     trigger=said(slot['event_key']),trigger_key=slot['event_key'],
                     source_stats=copy.deepcopy(represented),
                     provenance=dict(kind='decoded',basis='source-bound item trigger slot',source='Hero_Siege.exe',
                                     source_sha256=native['source_sha256'],slot_contract_sha256=domain['certificate_sha256'],
                                     selector_stat_id=slot['selector_stat_id'],level_stat_id=slot['level_stat_id'],
                                     chance_stat_id=slot['chance_stat_id'],levels_scope='base_item_definition',runtime_value_inferred=False))
        stats[:]=[s for s in stats if all(s is not used for used in represented)]
        result.append(grant)
    return result


def native_presentation(stats, grants, said, native):
    """Render UI controls as their actual roles, retaining every original statement."""
    domain=native.get('item_effects')
    if not item_effects.valid_domain(domain,native.get('source_sha256')):
        return []
    settings=domain['settings']
    mechanics=[]
    def take(lines):
        stats[:]=[s for s in stats if all(s is not used for used in lines)]
    def one(number):
        rows=[s for s in stats if s.get('id')==number]
        return rows[0] if len(rows)==1 else None
    def number(row):
        q=item_effects.quantity(row,row['id'],integral=True) if row and type(row.get('id')) is int else None
        return q['range'][0] if q and q.get('range') and q['range'][0]==q['range'][1] else None
    def names(en,ru):
        return {'en':en,'ru':ru}
    def effect(title,ru,lines,**extra):
        grant=dict(kind='effect',names=names(title,ru),lines=[],source_stats=copy.deepcopy(lines),
                   provenance=dict(kind='decoded',basis='source-bound item display role',source='Hero_Siege.exe',
                                   source_sha256=native['source_sha256'],slot_contract_sha256=domain['certificate_sha256'],
                                   runtime_value_inferred=False))
        grant.update(extra)
        grants.append(grant)
        take(lines)
        return grant
    def render(q):
        values=q.get('values') or q.get('range')
        return ' / '.join(map(str,values)) if 'values' in q else str(values[0]) if values[0]==values[1] else f'{values[0]}–{values[1]}'
    for role in settings.get('weapon_parameters',[]):
        for row in [s for s in stats if s.get('id')==role['stat_id']]:
            if item_effects.quantity(row,row['id']) is not None:
                mechanics.append(dict(role=role['meaning'],source_stats=[copy.deepcopy(row)]))
                take([row])
    classes={r['class_id']:r['class_key'] for r in settings.get('classes',[])}
    for selector,class_stat in settings.get('class_restrictions',{}).items():
        row=one(class_stat)
        cls=number(row)
        label=said(classes[cls]) if cls in classes else None
        if not label:
            continue
        if selector=='all_skills':
            skill=one(201)
            if skill:
                original=copy.deepcopy(skill)
                skill['class_names']=label
                skill['source_stats']=[original,copy.deepcopy(row)]
                take([row])
            else:
                original=copy.deepcopy(row)
                row.update(sid='item_all_skills_class',text='Class for All Skill Bonuses',
                           names=names('Class for All Skill Bonuses','Класс бонусов ко всем умениям'),
                           value_names=label,source_stats=[original],unit='',unitSource='native_item_effect')
                row.pop('unresolved',None)
        else:
            candidates=[g for g in grants if g.get('provenance',{}).get('selector_stat_id')==int(selector)]
            if len(candidates)==1:
                candidates[0]['class_names']=label
                candidates[0]['class_id']=cls
                candidates[0]['source_stats'].append(copy.deepcopy(row))
                take([row])
    simple={384:('Mana Recovery','Восстановление маны'),387:('Life Recovery','Восстановление здоровья'),
            390:('Effect Duration','Длительность эффекта'),413:('Extra Projectiles','Дополнительные снаряды'),
            414:('Projectile Chains','Отскоки снарядов')}
    for row in list(stats):
        sid=row.get('id')
        if str(sid) not in settings.get('simple_fields',{}) and sid not in settings.get('unit_overrides',[]):
            continue
        if item_effects.quantity(row,sid) is None:
            continue
        original=copy.deepcopy(row)
        if sid in simple:
            en,ru=simple[sid]
            row.update(sid='item_display_'+str(sid),text=en,names=names(en,ru))
            row.pop('unresolved',None)
        row.update(unit='',unitSource='native_item_effect',source_stats=[original])
        if sid==390:
            row['unit_names']=said('stat_seconds')
        if sid==413:
            row['effect_note']=said('stat_extra_projectile_03')
    for row in list(stats):
        if row.get('id') in settings.get('zone_reference_stats',[]) and row.get('resource_references'):
            original=copy.deepcopy(row)
            row.update(sid='item_zone_references',text='Zones',names=names('Zones','Зоны'),source_stats=[original])
            row.pop('unresolved',None)
        slot=settings.get('random_slots',{}).get(str(row.get('id')))
        sel=number(row)
        if slot is not None and str(sel) in settings.get('random_selector_pools',{}):
            original=copy.deepcopy(row)
            row.update(sid='unholy_none',text='Unholy',pool=sel,slot=slot,active=True,source_stats=[original])
            row.pop('unresolved',None)
    if settings.get('subskills'):
        selector,amount=one(419),one(420)
        value=item_effects.quantity(amount,420,integral=True) if amount else None
        talent_id=_native_grant_number(selector,419) if selector else None
        talent=native['by_id'].get(talent_id)
        selected=item_effects.quantity(selector,419,integral=True) if selector and talent is None else None
        random=selected and selected.get('range') and selected['range'][0]>0 and selected['range'][0]<selected['range'][1]
        if selector and amount and value and (talent or random):
            grant=effect('Sub Skills','Поднавыки',[selector,amount],kind='subskills',
                         names=said('talent_name_'+talent['key']) if talent else None,
                         levels=value.get('range'),random_skill=bool(random))
            if talent:
                grant.update(talent_id=talent_id,talent_key=talent['key'])
            else:
                grant['skill_selector_range']=selected['range']
            if value.get('values'):
                grant['level_values']=value['values']
    if settings.get('deferred_damage'):
        percent,seconds=one(279),one(280)
        p=item_effects.quantity(percent,279,ceiling=100) if percent else None
        duration=item_effects.quantity(seconds,280) if seconds else None
        if p and duration:
            texts=said('stat_damage_taken_over_01') or {'en':'of incoming damage is taken over'}
            units=said('tal_seconds') or {'en':'s'}
            lore={lang:f'{render(p)}% {text} {render(duration)} {units.get(lang,units.get("en","s"))}' for lang,text in texts.items()}
            effect('Delayed Incoming Damage','Отложенный входящий урон',[percent,seconds],lore=lore,
                   amount=p,duration=duration)
    for role in settings.get('codex_choices',[]):
        selector=one(role['selector_stat_id'])
        selected=item_effects.quantity(selector,selector['id'],integral=True) if selector else None
        bounds=selected.get('range') if selected else None
        if not bounds or bounds[0]<1 or bounds[1]>len(role['keys']):
            continue
        options=[dict(native_id=n,names=said(role['keys'][n-1])) for n in range(bounds[0],bounds[1]+1)]
        if all(option['names'] for option in options):
            positive=role['kind']=='codex_buff'
            effect('Possible Codex Buffs' if positive else 'Possible Codex Debuffs',
                   'Возможные усиления кодекса' if positive else 'Возможные ослабления кодекса',
                   [selector],options=options,selection_range=bounds)
    for flag in settings.get('tracker_flags',[]):
        row=one(flag)
        if row and number(row)==1:
            effect('Statistics Tracker','Счётчик игровой статистики',[row])
    for capability in settings.get('positive_capabilities',[]):
        row=one(capability['stat_id'])
        value=item_effects.quantity(row,row['id']) if row else None
        if value and value.get('range') and value['range'][0]>0 and capability['kind']=='bone_spirit_summon_healing':
            effect('Bone Spirit heals Necromancer summons','Костяной дух исцеляет призванных существ некроманта',[row],
                   raw_magnitude=value,numeric_unit_certified=False)
    if settings.get('random_skill_flag'):
        selector,operand=one(444),one(445)
        value=item_effects.quantity(operand,445,integral=True) if operand else None
        if selector and number(selector)==1 and value:
            grant=effect('Random skill','Случайное умение',[selector,operand],kind='skill',random_skill=True,
                         levels=value.get('range'),random_skill_rule=copy.deepcopy(settings['random_skill_flag']))
            if value.get('values'):
                grant['level_values']=value['values']
    return mechanics


def native_granted_scoped(stats, by_spoken, said, native, mechanics=None):
    """Outer storage keys are independent conditions, never duplicate slot operands."""
    contexts={}
    original=list(stats)
    for line in original:
        key=json.dumps(line.get('outer_selector'),sort_keys=True)
        contexts.setdefault(key,[]).append(line)
    grants=[]
    remaining=set()
    for key,lines in contexts.items():
        scoped=native_granted(lines,by_spoken,said,native) or []
        storage=native_presentation(lines,scoped,said,native)
        if mechanics is not None:
            for record in storage:
                if key!='null':
                    record['outer_selector']=json.loads(key)
                mechanics.append(record)
        for grant in scoped:
            if key!='null':
                grant['outer_selector']=json.loads(key)
        grants+=scoped
        remaining.update(id(line) for line in lines)
    stats[:]=[line for line in original if id(line) in remaining]
    return grants or None


def native_granted(stats, by_spoken, said, native):
    """Keep explicit spell text separate from direct, source-bound stat-202 IDs."""
    original, out, text_grants, numeric_grants = list(stats), [], [], []
    by_id, domain = native["by_id"], native.get("grant_domain") or {}

    def consume(line):
        stats[:] = [candidate for candidate in stats if candidate is not line]

    for line in original:
        if not line.get("spell") or not (line.get("sid") == BY_NAME or line.get("id") == 202):
            continue
        got = by_spoken.get(flat(line["spell"]))
        if not got:
            continue
        grant = spoken(got, [line.get("min"), line.get("max")] if line.get("sid") == BY_NAME else None, said)
        grant.update(talent_key=got["key"], talent_class=got.get("class"),
                     provenance={"kind": "decoded", "basis": "explicit spell name"},
                     source_stats=[copy.deepcopy(line)])
        text_grants.append(grant)
        out.append(grant)
        if line.get("sid") == BY_NAME:
            consume(line)

    aura_grants = native_aura_granted(stats, said, native)
    out.extend(aura_grants)
    out.extend(native_triggered(stats,said,native))
    slot_grants = native_skill_granted(stats, said, native)
    out.extend(slot_grants)
    numeric_grants.extend(g for g in slot_grants if g.get("talent_key"))
    level_observations = [line for line in original if type(line.get("id")) is int and line["id"] == 203]
    selectors = [line for line in original if type(line.get("id")) is int and line["id"] == 202]
    for named in selectors if len(selectors) == 1 else []:
        if all(named is not remaining for remaining in stats):
            continue
        if type(named.get("id")) is not int or named["id"] != 202:
            continue
        number = _native_grant_number(named)
        got = by_id.get(number)
        if got is None:
            continue
        # A separate description operand does not prove which duplicate or
        # ranged statement belongs to this grant. No adjacency or range join.
        grant = spoken(got, None, said)
        grant.update(talent_id=number, talent_key=got["key"], talent_class=got["class"],
                     provenance={"kind": "decoded", "basis": "source-bound native talent insertion key",
                                 "selector_stat_id": 202,
                                 "source": "Hero_Siege.exe", "source_sha256": native["source_sha256"],
                                 "native_contract_id": native["native_contract_id"],
                                 "scope": "static_native_numeric_map_insertion_key", "runtime_value_inferred": False},
                     source_stats=[copy.deepcopy(named)])
        if level_observations and domain.get("level_stat_id") == 203 and domain.get("level_is_separate") is True:
            grant["level_operand_observations"] = {"scope": "record_stat_observations", "pairing_certified": False,
                                                   "range_pairing_certified": False, "stats": copy.deepcopy(level_observations)}
        consume(named)
        numeric_grants.append(grant)
        out.append(grant)
    text_identities = {(grant["talent_key"], grant["talent_class"]) for grant in text_grants}
    numeric_identities = {(grant["talent_key"], grant["talent_class"]) for grant in numeric_grants}
    if text_identities and numeric_identities and text_identities != numeric_identities:
        difference = {"kind": "different_explicit_text_and_numeric_talents", "same_grant_proven": False,
                      "resolution": "independent_evidence_preserved",
                      "text": [list(identity) for identity in sorted(text_identities, key=lambda identity: (identity[0], identity[1] or ""))],
                      "numeric": [list(identity) for identity in sorted(numeric_identities, key=lambda identity: (identity[0], identity[1] or ""))]}
        for grant in out:
            grant["evidence_conflict"] = copy.deepcopy(difference)
    return out or None


def granted(tkey, stats, talents, told, by_number, by_spoken, pins, said, native=None):
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
    if native is None and any("id_source" in row for row in (by_number or {}).values()):
        native = {"by_id": {}, "status": "unsupported"}
    if native is not None:
        return native_granted(stats, by_spoken, said, native)
    if not (talents or by_number or by_spoken):
        return None
    out = []
    for line in [s for s in stats if s.get("sid") == BY_NAME and s.get("spell")]:
        got = by_spoken.get(flat(line["spell"]))
        if got:
            stats.remove(line)
            grant = spoken(got, [line.get("min"), line.get("max")], said)
            grant.update(provenance={"kind": "decoded", "basis": "spell name"}, source_stats=[dict(line)])
            out.append(grant)

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
            grant = spoken(by_key, None, said)
            grant["provenance"] = {"kind": "inferred", "basis": "item key"}
            out.append(grant)
        return out or None

    for named in marks:
        got = by_key
        basis = {"kind": "inferred", "basis": "item key"}
        if not got and named.get("min") is not None:
            got = at_number(named["min"], by_number, pins)
            basis = {"kind": "inferred", "basis": "numbering anchors"}
        if not got and alone and not out:
            got = (told or {}).get(tkey)
            basis = {"kind": "reference", "source": "HSPlanner"}
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
        grant = spoken(got, [levels.get("min"), levels.get("max")] if levels else None, said)
        grant.update(provenance=basis, source_stats=[dict(s) for s in (named, levels) if s is not None])
        out.append(grant)
    return out or None


def spoken(got, levels, said):
    """A talent as the block an item's card shows for it."""
    def line(e):
        # The mark after the number is either punctuation the game writes out —
        # a per cent sign — or a key it looks up, and `tal_seconds` is "s" in
        # English and "с" in Russian. Printed raw it read "40tal_seconds".
        mark, unit = e["mark"], said(e["mark"]) if e["mark"].startswith("tal_") else None
        got_line = {"index": e.get("index"), "start": e["start"], "per": e["per_level"],
                    "mark_known": e.get("mark_known"),
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
        "talent_source": {field: got[field] for field in
                          ("raw_fields", "interpretation_sources", "constructor_inheritance",
                           "inheritance_application", "field_write_sources", "field_write_expressions", "field_value_interpretations", "unresolved_fields", "notes",
                           "interpretation_notes", "control_flow_complete", "id_source", "kind", "kind_source") if field in got},
    }


def unique_talent_index(rows, key):
    groups = {}
    for row in rows:
        value = key(row)
        if value:
            groups.setdefault(value, []).append(row)
    return {value: records[0] for value, records in groups.items() if len(records) == 1}


def build(raw_items, csv_path, langs, icons_by_name, tidy, tables, say=None, talent_rows=None,
          named=None, stat_names=None, talent_id_contract=None, talent_id_source_sha256=None,
          item_aura_slot_contract=None, item_effect_contract=None, item_condition_contract=None):
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
    talents = unique_talent_index(talent_rows or [], lambda row: row["key"].lower())
    by_number = {t["id"]: t for t in (talent_rows or []) if t.get("id")}
    by_spoken = unique_talent_index(talent_rows or [], lambda row: flat(
        ((say.by_key.get(f"talent_name_{row['key']}") if say else None) or {}).get("en") or ""))
    current_native = (stat_names is not None or talent_id_contract is not None
                      or talent_id_source_sha256 is not None
                      or any("id_source" in row for row in talent_rows or []))
    native = native_talent_context(talent_rows or [], talent_id_contract, talent_id_source_sha256) if current_native else None
    if native is not None:
        native["aura_slots"] = item_aura_slot_contract
        native['item_effects'] = item_effect_contract
    pins = [] if current_native else pinned(raw_items, talents)
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

    socket_items=item_conditions.socket_catalogue(raw_items,said,item_condition_contract)
    # what a socket name refers to, for the runeword recipes below
    by_name = {}
    current_type_names = {}
    for it in raw_items:
        m = it.get("metadata") or {}
        tk = m.get("tkey") or ""
        if m.get("name") and (tk.startswith("socketable") or m.get("type") in ("Rune", "Orb", "Gem")):
            by_name.setdefault(tidy(m["name"]), tk)
        identity = m.get("ID")
        if (isinstance(identity, list) and len(identity) == 3 and m.get("type")
                and all(field in (m.get("fromGame") or []) for field in ("ID", "type"))):
            current_type_names.setdefault(identity[2], set()).add(m["type"])

    items = {}
    for it in raw_items:
        m = it.get("metadata") or {}
        name, tkey = m.get("name"), m.get("tkey")
        # `-Unknown Name-` is the snapshot's own shrug, sixty-five rows of it.
        # Keyed by tkey rather than by name, because two different things can
        # share one: Death's Scythe is both a Satanic Set weapon and a common
        # relic, and keying by name kept whichever came first.
        if not tkey:
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
        if not shown or shown == "-Unknown Name-":
            shown = "Unidentified item"
        low = tidy(shown)
        stats = []
        for stat in it.get("stats") or []:
            stats.append(stat_line(stat, stat_names))
        gives = granted(tkey, stats, talents, named, by_number, by_spoken, pins, said, native=native)
        gives=gives or []
        mechanics=native_presentation(stats,gives,said,native) if native is not None else []
        modes = variants(it, stat_names,conditions=item_condition_contract,socket_items=socket_items,said=said)
        if native is not None:
            for mode in modes:
                storage=[]
                conditional = native_granted_scoped(mode['stats'], by_spoken, said, native,mechanics=storage)
                if storage:
                    mode['mechanics']=storage
                if conditional:
                    mode['grants'] = conditional
                    for grant in conditional:
                        grant['condition'] = {key: mode[key] for key in ('when', 'channel', 'scope') if key in mode}
                        if grant.get('outer_selector') is not None:
                            grant['condition']['outer_selector']=copy.deepcopy(grant['outer_selector'])
                        grant['provenance']['levels_scope'] = 'conditional_item_definition'
        rate = drop_denominator(it)
        places = (it.get("dropPlaces") or []) if field_is_current(it, "dropPlaces") else []
        if isinstance(places, str):
            places = [places]
        factor = it.get("chaseDropRate") if field_is_current(it, "chaseDropRate") else None
        chase = max(1, int(rate * factor)) if rate and places and isinstance(factor, (int, float)) and factor > 0 else None
        record_id = m.get("record_id") or it.get("record_id") or ":".join(
            [tkey, *(str(n) for n in (m.get("ID") or [])), str(m.get("tier") or "")])
        rec = {
            "key": tkey,
            "record_id": record_id,
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
            "mechanics": mechanics,
            "reference": ["granted skill"] if any(g.get("provenance", {}).get("kind") == "reference" for g in gives or []) else None,
            "inferred": ["granted skill"] if any(g.get("provenance", {}).get("kind") == "inferred" for g in gives or []) else None,
            "places": places,
            "rate": rate,
            "chase": chase,
            "names": told,
            "lore": said(f"lore_{tkey}"),
            "icon": icons_by_name.get("record:" + record_id) or icons_by_name.get(low) or icons_by_name.get(tidy(name)),
            "iconSource": "game" if icons_by_name.get("record:" + record_id) else "name_match",
            "sockets": sockets(it, by_name, tidy),
            "recipeSource": (it.get("runeword_recipe") or {}).get("proof"),
            "weapons": weapons(it),
            "set": m.get("Item Set"),
            "base": made_in(it, current_type_names),
            "more": modes,
            "provenance": it.get("provenance") or m.get("provenance"),
            "unknowns": it.get("unknowns") or m.get("unknowns"),
        }
        record = {k: v for k, v in rec.items() if v not in (None, [], {})}
        if tkey in items:
            # Translation keys name families as well as individual records.
            # Retain every grade/identity while the family key keeps old links.
            siblings = items[tkey].setdefault("variants", [])
            occupied = {items[tkey]["record_id"], *(r["record_id"] for r in siblings)}
            if record["record_id"] in occupied:
                record["record_id"] += f":{len(siblings) + 1}"
            siblings.append(record)
        else:
            items[tkey] = record

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
    for rec in item_records(items):
        every = list(rec.get("stats") or [])
        for v in rec.get("more") or []:
            every += v["stats"]
        for s in every:
            row = vocab.setdefault(s["sid"], {"sid": s["sid"], "text": s["text"], "n": 0})
            if s.get("unit"):
                row["unit"] = s["unit"]
            for field in ('names','unitSource'):
                if field in s:
                    row[field]=s[field]
            if s.get('unitSource')=='native_item_effect':
                row['unit']=s.get('unit','')
            row["n"] += 1
    return items, sorted(vocab.values(), key=lambda v: (-v["n"], v["text"])), kits
