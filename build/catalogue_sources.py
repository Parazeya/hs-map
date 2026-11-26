"""Join map drops to unique current Codex records and project their destinations."""

from collections import Counter, defaultdict
from unicodedata import normalize


def folded(value):
    value = normalize("NFC", value or "").replace("’", "'").replace("‘", "'")
    return " ".join(value.lower().split())


def rarity(value):
    return {"satanic set": "set"}.get(folded(value), folded(value))


def candidate_rows(items):
    rows = defaultdict(list)
    for key, item in items.items():
        for record in [item, *(item.get("variants") or [])]:
            record.pop("map_sources", None)
            name = (record.get("names") or item.get("names") or {}).get("en")
            if name:
                rows[folded(name), rarity(record.get("rarity"))].append((key, record))
    return rows


def match(alias, item, candidates):
    grade = rarity(item.get("rarity"))
    for name in dict.fromkeys((alias, (item.get("names") or {}).get("en"))):
        matches = candidates.get((folded(name), grade), [])
        if matches:
            break
    else:
        return None, None

    if len(matches) > 1:
        tier = item.get("tier")
        tiers = ["D", "C", "B", "A", "S", "SS"]
        tier = tiers[tier - 1] if type(tier) is int and 1 <= tier <= len(tiers) else tier
        comparable = {column: item[column] for column in ("rate", "chase") if item.get(column) is not None}
        if tier:
            comparable["tier"] = tier
        exact = [(key, record) for key, record in matches
                 if all(record.get(column) == value for column, value in comparable.items())]
        if exact:
            matches = exact

    if len(matches) == 1:
        return matches[0]
    keys = {key for key, _ in matches}
    return (keys.pop(), None) if len(keys) == 1 else (None, None)


def attach(items, nodes, shelves, places, codex):
    """Use map rows as published, preserving native/reference data boundaries."""
    rooms_by_item = defaultdict(list)
    odds_by_item = defaultdict(dict)
    shelves_by_item = defaultdict(list)
    rooms_by_code = defaultdict(list)
    room_names = {}
    for node in nodes:
        room = node["room"]
        if node.get("code"):
            rooms_by_code[node["code"]].append(room)
        room_names[room] = node.get("name") or {"en": room}
        reference_drops = set(node.get("reference_drops", []))
        reference_odds = node.get("reference_drop_odds", {})
        for alias in node.get("drops", []):
            rooms_by_item[alias].append(room)
            if alias in reference_drops:
                rate = reference_odds.get(alias)
                if type(rate) is int and rate > 0:
                    odds_by_item[alias][room] = {"rate": rate, "reference": True}
            else:
                rate = items.get(alias, {}).get("chase")
                if type(rate) is int and rate > 0:
                    odds_by_item[alias][room] = {"rate": rate}
        for drop in shelves.get(node.get("boss"), {}).get("drops", []):
            rooms_by_item[drop["item"]].append(room)

    source_names = dict(places)
    for name, shelf in shelves.items():
        source_names.setdefault(name, shelf.get("names") or {"en": name})
        if shelf.get("kind") in {"uber", "other", "source"}:
            for drop in shelf.get("drops", []):
                shelves_by_item[drop["item"]].append(name)

    candidates = candidate_rows(codex["items"])
    matches = {alias: match(alias, item, candidates) for alias, item in items.items()}
    by_key = Counter(key for key, _ in matches.values() if key is not None)
    used_rooms = set()
    for alias, item in items.items():
        item.pop("key", None)
        item.pop("record_id", None)
        key, record = matches[alias]
        if key is None:
            continue
        item["key"] = key
        if record is not None and record.get("record_id"):
            item["record_id"] = record["record_id"]
        if record is None or by_key[key] != 1:
            continue

        rooms = list(dict.fromkeys([
            *rooms_by_item[alias],
            *(room for code in item.get("zones", []) for room in rooms_by_code[code]),
        ]))
        sources = list(dict.fromkeys(shelves_by_item[alias]))
        if rooms or sources:
            record["map_sources"] = {}
            if rooms:
                record["map_sources"]["rooms"] = rooms
                used_rooms.update(rooms)
            if room_odds := odds_by_item.get(alias):
                record["map_sources"]["room_odds"] = room_odds
            if sources:
                record["map_sources"]["shelves"] = sources

    codex["map_rooms"] = {key: names for key, names in room_names.items() if key in used_rooms}
    codex["places"] = source_names
