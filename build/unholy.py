"""Label random modifier pools from the same verified Extractor generation.

Item slots and candidate stats are different structures. Pool routing is taken
from the current bundle; an unknown selector remains unknown. The legacy text
parser below is a diagnostic utility and is never an input to the site build.
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
ELEMENTS = {1: "Arcane", 2: "Cold", 3: "Fire", 4: "Lightning", 5: "Poison"}

ARM = re.compile(
    r"^\s*(\d+)\s+\d+\s+0x[0-9a-f]+\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)\s*$"
)
POOL = re.compile(r"^\s*--\s*selector\s+(\d+)\s*--.*?(\d+)\s+arms")


def read(dump: Path) -> dict:
    """Parse one `--unholy` dump into pools of named modifiers."""
    pools: dict[int, dict] = {}
    here = None
    for line in dump.read_text(encoding="utf-8", errors="replace").splitlines():
        head = POOL.match(line)
        if head:
            here = int(head.group(1))
            pools[here] = {"arms": int(head.group(2)), "rolls": []}
            continue
        if here is None:
            continue
        hit = ARM.match(line)
        if not hit:
            continue
        arm, sid, lo, hi, name = (
            int(hit.group(1)), int(hit.group(2)),
            int(hit.group(3)), int(hit.group(4)), hit.group(5),
        )
        rolls = pools[here]["rolls"]
        # Five ids under one arm number is a sibling set: same range, one
        # element each, in the order argument 2 reads them.
        if rolls and rolls[-1]["arm"] == arm:
            twin = rolls[-1]
            if "elements" not in twin:
                twin["elements"] = [{"id": twin.pop("id"), "name": twin.pop("name")}]
            twin["elements"].append({"id": sid, "name": name})
        else:
            rolls.append({"arm": arm, "id": sid, "name": name, "min": lo, "max": hi})
    for pool in pools.values():
        for roll in pool["rolls"]:
            roll.pop("arm", None)
            if "elements" in roll:
                for i, el in enumerate(roll["elements"], 1):
                    el["element"] = ELEMENTS.get(i, str(i))
    return pools


def build(dump: Path) -> dict:
    pools = read(dump)
    missing = [n for n in (1, 2, 3, 5) if n not in pools]
    if missing:
        raise SystemExit(f"the dump is missing selector {missing} — is it a whole --unholy?")
    for n, want in ((1, 23), (2, 17), (3, 17), (5, 18)):
        got = len(pools[n]["rolls"])
        if got != want or pools[n]["arms"] != want:
            raise SystemExit(f"selector {n}: {got} rolls read, {pools[n]['arms']} arms claimed, {want} expected")
    return {
        "note": "read out of Hero_Siege.exe; see build/unholy.py",
        "selects": {str(n): [n] for n in (1, 2, 3)},
        "elements": [ELEMENTS[i] for i in sorted(ELEMENTS)],
        "pools": {str(n): pools[n] for n in (1, 2, 3)},
        "zone": pools[5],
    }


def labelled(say, data=None):
    """The pools, with each modifier named in the eleven languages.

    Every one of the eighty-one names is a key in the game's own
    `translationsAttributes.csv`, under `[Global Stats]` — not the `stat_*`
    keys the item tooltips use, which is why the codex's stat vocabulary knows
    none of them. So the label is the game's word, not ours, in every language
    the site speaks.
    """
    if data is None:
        # Do not reintroduce an independent dump from another game build.
        return None
    data = json.loads(json.dumps(data))
    if isinstance(data.get("pools"), list):
        pools, selects, zone = {}, {}, None
        for pool in data["pools"]:
            rolls = []
            for arm in pool.get("arms", []):
                sites = arm.get("sites", [])
                if not sites:
                    continue
                by_site = {site.get("source_rva"): site for site in sites}
                ordered = [by_site[at] for _, at in sorted(arm.get("arg2", [])) if at in by_site]
                entries = ordered or sites
                roll = dict(entries[0])
                if len(entries) > 1:
                    roll["elements"] = entries
                    if len({(entry.get("min"), entry.get("max")) for entry in entries}) != 1:
                        roll.pop("min", None)
                        roll.pop("max", None)
                rolls.append(roll)
            record = {"rolls": rolls, "source": pool.get("source_rva")}
            selector = str(pool["selector"])
            if selector == "5":
                zone = record
            else:
                pools[selector] = record
                selects[selector] = [pool["selector"]]
        rules = data.get("selection_rules") or {}
        if rules.get("status") == "verified_instruction_pattern":
            remap = rules.get("selector_remap") or {}
            selector = remap.get("when_selector")
            values = (remap.get("roll") or {}).get("values")
            if (type(selector) is int and isinstance(values, list) and values
                    and all(type(value) is int and str(value) in pools for value in values)):
                selects[str(selector)] = values
        data = {"pools": pools, "selects": selects, "selection_rules": rules,
                "zone": zone or {"rolls": []}, "coverage": data.get("coverage")}
    if not isinstance(data.get("pools"), dict) or "selects" not in data:
        print("unholy   current export preserved as raw data; display mapping is incomplete")
        return None
    missed = []

    def name(entry):
        key = entry.get("name")
        said = say.by_key.get(key)
        if said:
            entry["said"] = said
        else:
            entry["name"] = key or "Unidentified effect"
            missed.append(entry["name"])
        return entry

    for pool in data["pools"].values():
        for roll in pool["rolls"]:
            for entry in roll.get("elements", [roll]):
                name(entry)
    for roll in data["zone"]["rolls"]:
        name(roll)
    if missed:
        # The zone buffs are expected here: the game files name them under
        # `[Satanic Buffs]` with keys of its own spelling — `satanicBuffLootSlots`
        # against the code's `buff_loot_slots` — and matching those by hand is a
        # separate job. Items are what this page shows, and all 81 are named.
        print(f"unholy   {len(missed)} of the pools unnamed by the game "
              f"({', '.join(sorted(missed)[:3])}...)")
    return data


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "unholy.txt"
    out = build(src)
    (HERE / "unholy.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    n = sum(len(p["rolls"]) for p in out["pools"].values())
    twins = sum(1 for p in out["pools"].values() for r in p["rolls"] if "elements" in r)
    print(f"ok unholy.json — {n} rolls over 3 item pools, {twins} of them elemental, "
          f"{len(out['zone']['rolls'])} zone buffs")
