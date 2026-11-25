"""Validate and consume one Extractor export without mixing game builds."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path


class BundleError(ValueError):
    pass


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[a-fA-F0-9]{64}", value) is not None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory_fingerprint(files) -> str:
    """The producer's canonical compact UTF-8 inventory serialization."""
    if not isinstance(files, list) or not files:
        raise BundleError("Extractor bundle has no source file hashes")
    normalized, names = [], set()
    for entry in files:
        if (not isinstance(entry, dict) or not isinstance(entry.get("path"), str)
                or not entry["path"] or not _hash(entry.get("sha256"))
                or type(entry.get("size")) is not int or entry["size"] < 0):
            raise BundleError("Extractor bundle has an invalid source file fingerprint")
        name = entry["path"]
        relative = Path(name)
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise BundleError("Extractor source path escapes the game folder")
        if name in names:
            raise BundleError("Extractor source inventory has duplicate paths")
        names.add(name)
        normalized.append({"path": name, "sha256": entry["sha256"].lower(), "size": entry["size"]})
    if not {"Hero_Siege.exe", "data.win"}.issubset(names):
        raise BundleError("Extractor source inventory must contain Hero_Siege.exe and data.win")
    try:
        normalized.sort(key=lambda entry: entry["path"].encode("utf-8"))
        serialized = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except UnicodeError as error:
        raise BundleError("Extractor source inventory has an invalid UTF-8 path") from error
    return hashlib.sha256(serialized).hexdigest()


def configured_game() -> Path:
    """Explicit configuration wins; Steam's installed library is the default."""
    explicit = os.environ.get("HERO_SIEGE_BIN") or os.environ.get("HERO_SIEGE")
    if explicit:
        return Path(explicit).expanduser().resolve()
    steam = []
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                steam.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except OSError:
            pass
    steam += [Path.home() / ".steam/steam", Path.home() / ".local/share/Steam",
              Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam"]
    libraries = []
    for home in steam:
        libraries.append(home)
        config = home / "steamapps/libraryfolders.vdf"
        if config.is_file():
            libraries += [Path(p.replace("\\\\", "\\")) for p in
                          re.findall(r'"path"\s+"([^"]+)"', config.read_text("utf-8", errors="replace"))]
    for home in libraries:
        candidate = home / "steamapps/common/HeroSiege/bin"
        if (candidate / "data.win").is_file():
            return candidate.resolve()
    raise BundleError("Hero Siege was not found; set HERO_SIEGE_BIN to its bin folder")


class Bundle:
    def __init__(self, folder: Path, game: Path | None = None):
        self.folder = folder.resolve()
        try:
            self.manifest = json.loads((self.folder / "manifest.json").read_text("utf-8"))
        except (OSError, ValueError) as error:
            raise BundleError(f"Cannot read Extractor manifest at {self.folder}: {error}") from error
        if type(self.manifest.get("schema_version")) is not int or self.manifest["schema_version"] != 1:
            raise BundleError("Unsupported Extractor bundle schema; expected schema_version 1")
        self.game = self.manifest.get("game") or {}
        if not isinstance(self.game, dict) or not _hash(self.game.get("fingerprint")):
            raise BundleError("Extractor bundle has no game fingerprint")
        if inventory_fingerprint(self.game.get("files")) != self.game["fingerprint"].lower():
            raise BundleError("Extractor game fingerprint does not match its source inventory")
        self.datasets = self.manifest.get("datasets") or {}
        if not isinstance(self.datasets, dict) or not self.datasets:
            raise BundleError("Extractor bundle has no datasets")
        self._cache = {}
        # Validate every declared output before exposing even the first table.
        for name, record in self.datasets.items():
            path = self.path(name)
            expected = record.get("sha256")
            if record.get("status") not in ("complete", "partial"):
                raise BundleError(f"Extractor dataset {name} has no extraction status")
            if not _hash(expected) or not path.is_file() or sha256(path) != expected.lower():
                raise BundleError(f"Extractor dataset {name} is missing or its SHA-256 does not match")
        if game is not None:
            self.validate_game(game)
        for name in ("items", "talents"):
            if name not in self.datasets:
                raise BundleError(f"Extractor bundle is missing required dataset {name}")
            rows = self.read(name)
            count = self.datasets[name].get("records")
            if not isinstance(rows, list) or not rows or type(count) is not int or count != len(rows):
                raise BundleError(f"Extractor dataset {name} is empty or its record count does not match")
            identities = set()
            for row in rows:
                if not isinstance(row, dict):
                    raise BundleError(f"Extractor dataset {name} has a non-record entry")
                if name == "items":
                    metadata = row.get("metadata") or {}
                    identity = metadata.get("record_id") or row.get("record_id")
                    if not isinstance(metadata.get("tkey"), str) or not metadata["tkey"] or not isinstance(metadata.get("fromGame"), list):
                        raise BundleError("An item is missing its translation key or field provenance")
                    valid_id = isinstance(identity, str) and bool(identity)
                else:
                    identity = row.get("id")
                    valid_id = type(identity) is int and isinstance(row.get("key"), str) and bool(row["key"])
                if not valid_id or identity in identities:
                    raise BundleError(f"Extractor dataset {name} has absent or duplicate record identities")
                identities.add(identity)

    def path(self, name: str) -> Path:
        record = self.datasets.get(name)
        if not isinstance(record, dict) or not isinstance(record.get("file"), str) or not record["file"]:
            raise BundleError(f"Extractor dataset {name} has no file")
        relative = Path(record["file"])
        path = (self.folder / relative).resolve()
        if relative.is_absolute() or relative.drive or not path.is_relative_to(self.folder):
            raise BundleError(f"Extractor dataset {name} escapes the bundle folder")
        return path

    def validate_game(self, folder: Path):
        folder = folder.resolve()
        files = self.game.get("files") or []
        if not isinstance(files, list) or not files:
            raise BundleError("Extractor bundle has no source file hashes")
        for entry in files:
            if not isinstance(entry, dict) or not _hash(entry.get("sha256")) or type(entry.get("size")) is not int or entry["size"] < 0:
                raise BundleError("Extractor bundle has an invalid source file fingerprint")
            relative = Path(entry.get("path", ""))
            path = (folder / relative).resolve()
            if not entry.get("path") or relative.is_absolute() or relative.drive or not path.is_relative_to(folder):
                raise BundleError("Extractor source path escapes the game folder")
            if not path.is_file() or path.stat().st_size != entry.get("size") or sha256(path) != entry["sha256"].lower():
                raise BundleError(f"Game file {relative} differs from the Extractor export; export the current build again")

    def read(self, name: str, default=None):
        if name not in self.datasets:
            return default
        if name not in self._cache:
            try:
                self._cache[name] = json.loads(self.path(name).read_text("utf-8"))
            except (OSError, ValueError) as error:
                raise BundleError(f"Cannot read Extractor dataset {name}: {error}") from error
        return self._cache[name]

    def source(self):
        return {"schema_version": 1, "fingerprint": self.game["fingerprint"],
                "build_id": self.game.get("build_id"),
                "datasets": {name: {"sha256": row["sha256"], "status": row.get("status", "partial")}
                             for name, row in self.datasets.items()}}


def item_records(items):
    """The representative and every additional record of each translation key."""
    for record in items.values():
        yield record
        yield from record.get("variants", [])


def verify_item_coverage(rows, items):
    expected = [(row.get("metadata") or {}).get("record_id") or row.get("record_id") for row in rows]
    actual = [row.get("record_id") for row in item_records(items)]
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise BundleError("Codex generation lost or replaced canonical item records")
    return {"input_records": len(expected), "output_records": len(actual), "families": len(items)}


MAP_MARKER_EXCLUSIONS = {"Cabin_01_rm": "tutorial_cabin_without_drops"}


def verify_map_marker_sources(native, rendered):
    exported = {row["room"]: row for row in native}
    if len(exported) != len(native):
        raise BundleError("Map export duplicated a marker identity")
    excluded = [{"room": room, "reason": MAP_MARKER_EXCLUSIONS[room]}
                for room in sorted(exported.keys() & MAP_MARKER_EXCLUSIONS.keys())]
    by_room = {room: row for room, row in exported.items() if room not in MAP_MARKER_EXCLUSIONS}
    shown, references = set(), []
    native_shown = set()
    for row in rendered:
        room, source = row["room"], row.get("source") or {}
        if room in MAP_MARKER_EXCLUSIONS:
            raise BundleError(f"Map generation displayed excluded marker: {room}")
        if room in shown:
            raise BundleError("Map generation duplicated a marker identity")
        shown.add(room)
        if source.get("kind") == "decoded":
            current = by_room.get(room)
            if current is None or (row["x"], row["y"]) != (current["x"], current["y"]):
                raise BundleError("A native map marker lost its verified coordinates")
            native_shown.add(room)
        elif source.get("kind") == "inferred":
            anchor = by_room.get(source.get("anchor_room"))
            reference = source.get("reference") or {}
            offset = source.get("offset") or {}
            if (anchor is None or reference.get("kind") != "reference"
                    or reference.get("verified_for_game_build") is not False
                    or row["x"] != anchor["x"] + offset.get("x", float("nan"))
                    or row["y"] != anchor["y"] + offset.get("y", float("nan"))):
                raise BundleError("An inferred map marker has no explicit reference and anchor")
            references.append({"room": room, "source": source})
        else:
            raise BundleError("A map marker has no coordinate provenance")
    missing = by_room.keys() - native_shown
    if missing:
        raise BundleError("Map generation omitted verified native markers: " + ", ".join(sorted(missing)))
    return {"native_exported": len(native), "native_shown": len(native_shown), "native_excluded": excluded,
            "reference_markers": len(references), "rendered_markers": len(rendered), "references": references}


def attach_exclusive_sources(rows, items, graph):
    """Keep proven named-item edges separate from location/difficulty claims."""
    if not isinstance(graph, dict) or (graph.get("payload_contract") or {}).get("status") != "verified":
        return 0
    by_record = {row.get("record_id"): row for row in item_records(items)}
    named = {}
    for row in rows:
        meta = row.get("metadata") or {}
        identity = meta.get("ID")
        if meta.get("named") is True and isinstance(identity, list) and len(identity) == 3:
            # metadata.ID is game-id/weapon-type/item-type; the audited native
            # payload tuple is item-type/weapon-type/game-id.
            key = (meta.get("tkey"), (identity[2], identity[1], identity[0]))
            named.setdefault(key, []).append(meta.get("record_id") or row.get("record_id"))
    edges = 0
    for source in graph.get("sources") or []:
        if source.get("semantics") != "exclusive_drop_mechanism":
            continue
        proof = source.get("provenance") or {}
        keys = {(entry.get("item"), tuple(entry["tuple"])) for entry in proof.get("entries") or []
                if entry.get("status") == "verified_named_identity" and entry.get("named") is True
                and isinstance(entry.get("tuple"), list) and len(entry["tuple"]) == 3
                and all(type(value) is int and value >= 0 for value in entry["tuple"])
                and entry.get("item") in (source.get("items") or [])}
        for key in keys:
            for record_id in named.get(key, []):
                record = by_record.get(record_id)
                if record is None:
                    raise BundleError("A verified exclusive-source edge has no canonical item record")
                record.setdefault("exclusive_sources", []).append({field: source[field] for field in
                    ("key", "kind", "name", "ownership_status", "semantics", "status", "provenance") if field in source})
                edges += 1
    return edges


def field_is_current(row, field):
    provenance = row.get("provenance") or (row.get("metadata") or {}).get("provenance") or {}
    stated = (row.get("metadata") or {}).get("fromGame") or []
    evidence = provenance.get(field) or {}
    return (evidence.get("kind") == "decoded"
            or evidence.get("kind") == "engine_default" and field in stated
            or not provenance and field in stated)


def drop_denominator(row):
    if not field_is_current(row, "droprate"):
        return None
    rate = row.get("droprate") or {}
    value = rate.get("base")
    if rate.get("meaning") == "no_drop":
        return None
    return int(value) if type(value) in (int, float) and math.isfinite(value) and value > 0 else None


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
         "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}


def place_codes(place: str, rooms) -> list[str]:
    act_number = r"[IVX]+|\d+"
    if dungeon := re.fullmatch(
            rf"(?:Act\s+((?:{act_number})(?:\s*(?:&|and)\s*(?:Act\s+)?(?:{act_number}))*)\s+)?"
            r"(Boss\s+)?Dungeons?", place.strip(), re.I):
        suffix = "BD" if dungeon[2] else "D"
        if dungeon[1]:
            acts = {int(token) if token.isdigit() else ROMAN.get(token.upper())
                    for token in re.findall(act_number, dungeon[1], re.I)}
        else:
            room_pattern = r"Act_(\d\d)_Boss(?:_Dungeon_\d+)?"
            if not dungeon[2]:
                room_pattern = r"Act_(\d\d)_\d\d"
            acts = {int(room[1]) for name in rooms if (room := re.fullmatch(room_pattern, name))}
        return [f"{act}-{suffix}" for act in sorted(acts - {None})]

    match = re.search(r"\bAct\s+([IVX]+|\d+)\s+(.*)", place, re.I)
    if not match:
        return []
    act = ROMAN.get(match[1].upper()) if not match[1].isdigit() else int(match[1])
    if act is None:
        return []
    tail = match[2].lower()
    if "boss dungeon" in tail:
        return [f"{act}-BD"]
    if "dungeon" in tail:
        return [f"{act}-D"]
    available = sorted({int(m[2]) for name in rooms
                        if (m := re.fullmatch(r"Act_(\d+)_(\d+)", name)) and int(m[1]) == act})
    if "overworld" in tail:
        return [f"{act}-{zone}" for zone in available]
    if match := re.search(r"zones?\s+(\d+)(?:\s*[-–]\s*(\d+))?", tail):
        return [f"{act}-{zone}" for zone in available
                if int(match[1]) <= zone <= int(match[2] or match[1])]
    return []


def tables_from_items(rows, rooms):
    """Map lookup tables from this bundle, with ambiguous names left unanswered."""
    out = {name: {} for name in ("DROP_RATE", "DROP_CHASE", "DROP_PLACES", "DROP_ZONES", "RARITY_BY_NAME", "TIER_BY_NAME")}
    out["TIER_LETTERS"] = ["D", "C", "B", "A", "S", "SS"]
    claims = {}
    for row in rows:
        meta = row.get("metadata") or {}
        name = (meta.get("name") or "").strip().lower()
        if not name:
            continue
        stated_rarity = meta.get("rarity") if field_is_current(row, "rarity") else None
        rarity = {"Satanic Set": "Set"}.get(stated_rarity, stated_rarity)
        tier = meta.get("tier") if field_is_current(row, "tier") else None
        rate = drop_denominator(row)
        places = (row.get("dropPlaces") or []) if field_is_current(row, "dropPlaces") else []
        if isinstance(places, str):
            places = [places]
        factor = row.get("chaseDropRate") if field_is_current(row, "chaseDropRate") else None
        claim = (rarity, tier, rate, factor, tuple(places))
        claims.setdefault(name, set()).add(claim)
    for name, values in claims.items():
        # A name shared by a named item and a relic is resolved only for the
        # named-item map. Two competing notable claims remain unknown.
        notable = [v for v in values if v[0] in {"Satanic", "Set", "Heroic", "Angelic", "Unholy"}]
        if len(notable) != 1:
            continue
        rarity, tier, rate, factor, places = notable[0]
        out["RARITY_BY_NAME"][name] = rarity
        if tier in out["TIER_LETTERS"]:
            out["TIER_BY_NAME"][name] = out["TIER_LETTERS"].index(tier) + 1
        if isinstance(rate, (int, float)) and rate > 0:
            out["DROP_RATE"][name] = int(rate)
            if places and isinstance(factor, (int, float)) and factor > 0:
                out["DROP_CHASE"][name] = max(1, int(rate * factor))
        if places:
            out["DROP_PLACES"][name] = sorted(set(places))
            codes = sorted({code for place in places for code in place_codes(place, rooms)})
            if codes:
                out["DROP_ZONES"][name] = codes
    return out
