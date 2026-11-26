"""Fill missing zone drop edges with the previous published map catalogue."""

import hashlib
import json
from pathlib import Path

CATALOGUE = Path(__file__).with_name("reference") / "published-zone-drops-20261126.json"


def catalogue():
    raw = CATALOGUE.read_bytes()
    value = json.loads(raw)
    if value.get("schema_version") != 1 or value["reference"].get("verified_for_game_build") is not False:
        raise ValueError("Published zone lists must remain explicitly unverified reference data")
    value["reference"]["catalogue_sha256"] = hashlib.sha256(raw).hexdigest()
    return value


def _rarity(value):
    if not isinstance(value, str):
        return ""
    folded = " ".join(value.casefold().split())
    return "set" if folded == "satanic set" else folded


def merge_map(items, nodes, reference):
    """Append historical edges and retain matching old odds only on those edges."""
    by_location = {(node["room"], node.get("code")): node for node in nodes}
    added = 0
    for zone in reference["zones"]:
        node = by_location.get((zone["room"], zone["code"]))
        if node is None:
            continue
        present = set(node["drops"])
        for row in zone["drops"]:
            name = row["item"]
            item = items.get(name)
            if item is None or name in present or item.get("zones") or item.get("places"):
                continue
            expected_rarity = _rarity(row.get("rarity"))
            if not expected_rarity or _rarity(item.get("rarity")) != expected_rarity:
                continue
            node["drops"].append(name)
            node.setdefault("reference_drops", []).append(name)
            old_rate, old_chase = row.get("rate"), row.get("chase")
            current_rate = item.get("rate")
            if (type(old_rate) is int and old_rate > 0 and type(current_rate) is int and current_rate == old_rate
                    and type(old_chase) is int and old_chase > 0):
                node.setdefault("reference_drop_odds", {})[name] = old_chase
            present.add(name)
            added += 1
    return added
