"""Retain explicitly labelled published chest lists beside current game facts."""
import copy
import hashlib
import json
import re
from pathlib import Path

CATALOGUE = Path(__file__).with_name("reference") / "published-chest-drops-20261120.json"


def catalogue():
    raw = CATALOGUE.read_bytes()
    value = json.loads(raw)
    if value.get("schema_version") != 1 or value["reference"].get("verified_for_game_build") is not False:
        raise ValueError("Published chest lists must remain explicitly unverified reference data")
    value["reference"]["catalogue_sha256"] = hashlib.sha256(raw).hexdigest()
    return value


def merge_map(items, sources, reference):
    added = 0
    for record in reference["sources"]:
        name = record["name"]
        present = {row["item"] for row in sources.get(name, {}).get("drops", [])}
        missing = []
        for row in record["drops"]:
            if row["item"] in items and row["item"] not in present:
                missing.append(row)
                present.add(row["item"])
        if not missing:
            continue
        source = sources.setdefault(name, {"kind": "source", "drops": [], "inferno_only": False})
        source["reference"] = copy.deepcopy(reference["reference"])
        for row in missing:
            source["drops"].append(dict(row, reference=copy.deepcopy(reference["reference"])))
            added += 1
    return added


def merge_records(items, reference):
    normalize = lambda name: re.sub(r"[^a-z0-9]", "", name.lower())
    links = {}
    for source in reference["sources"]:
        for row in source["drops"]:
            links.setdefault(normalize(row["item"]), []).append(source["name"])
    added = 0
    for item in items.values():
        for record in [item, *(item.get("variants") or [])]:
            key = normalize((record.get("names") or {}).get("en") or (item.get("names") or {}).get("en") or "")
            verified = {normalize(name) for name in record.get("places") or []}
            present = {row["name"] for row in record.get("reference_places") or []}
            for name in links.get(key, []):
                if normalize(name) in verified or name in present:
                    continue
                record.setdefault("reference_places", []).append({"name": name, "provenance": copy.deepcopy(reference["reference"])})
                present.add(name)
                added += 1
    return added
