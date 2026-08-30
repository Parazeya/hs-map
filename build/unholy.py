"""The Unholy modifier pools, read out of the compiled game.

An Unholy item does not carry its extra modifiers; it carries a *slot* and a
number, and the game rolls the modifier when the item drops. The snapshot the
site is otherwise built from records only the number, so the codex showed three
lines reading "Unholy 4" on Chaos Gemstone and nothing about what those three
lines could become.

The number is a pool selector. `LoadRandomSatanicStat` (compiled body
0x428d370) switches on it against the case table at 0x10c90760 and sends each
to its own `irandom` switch; `GenerateItemRandomStats` (0x6f9560) calls it once
per slot, and turns a stored 4 into `irandom(2)+1`, so a 4 means "pool 1, 2 or
3". There is no case 4 in the table at all.

  selector 1  offence and attributes    23 arms
  selector 2  casting and elements      17 arms
  selector 3  defence and resistance    17 arms
  selector 5  never appears on an item

Selector 5 is worth its own line: its eighteen ids are `buff_loot_slots`,
`buff_heroic_chance`, `buff_ancient_goblin` and their kin — the modifiers a
Satanic Zone carries, not an item. That is why no item in the table selects it,
and why the loot filter never names those ids: the filter names what can be on
an item.

Six of the seventy-five arms hold five ids instead of one. Argument 2 of the
call, `irandom(4)+1`, picks which of the five is written, and all five share one
[min, max] pair — so it moves the element and never the magnitude. The order is
the same at all six sites: 1 Arcane, 2 Cold, 3 Fire, 4 Lightning, 5 Poison.
This is what the planner site splits into five and six separate items; the game
holds one item and rolls the element.

Regenerate the input with the extractor, whose reading this is:

    hse-extractor.exe --unholy > unholy.txt
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
        # A slot's stored number, and the pools it can draw from. 4 is not a
        # pool: the caller turns it into irandom(2)+1 before the call.
        "selects": {"1": [1], "2": [2], "3": [3], "4": [1, 2, 3]},
        "elements": [ELEMENTS[i] for i in sorted(ELEMENTS)],
        "pools": {str(n): pools[n] for n in (1, 2, 3)},
        "zone": pools[5],
    }


def labelled(say):
    """The pools, with each modifier named in the eleven languages.

    Every one of the eighty-one names is a key in the game's own
    `translationsAttributes.csv`, under `[Global Stats]` — not the `stat_*`
    keys the item tooltips use, which is why the codex's stat vocabulary knows
    none of them. So the label is the game's word, not ours, in every language
    the site speaks.
    """
    data = json.loads((HERE / "unholy.json").read_text(encoding="utf-8"))
    missed = []

    def name(entry):
        said = say.by_key.get(entry["name"])
        if said:
            entry["said"] = said
        else:
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
