import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import encyclopedia as book
import item_grant_slots as slots
from test_native_talent_grants import fixture, selector


NAMES = {"stoneSkinAura": "Stoneskin Aura", "hastefulAura": "Hasteful Aura",
         "balefulAura": "Baleful Aura", "fortunateAura": "Fortunate Aura"}


def domain():
    proof = slots.certificate()
    images = {(row["start_rva"], row["end_rva"] - row["start_rva"]): bytes.fromhex(row["bytes_hex"]) for row in proof["spans"]}
    images.update({(row["rva"], 16): bytes.fromhex(row["bytes_hex"]) for row in proof["numeric_boxes"]})
    return slots.verify(slots.SOURCE, lambda at, size: images.get((at, size), b"")), images


def statement(stat, operand, rva):
    row = selector(1)
    row.update(id=stat, min=operand if isinstance(operand, int) else operand[0])
    row["source"]["rva"] = rva
    row["raw"] = {"rva": rva, "args": [{"kind": "value", "value": {"kind": "int", "value": stat}},
        {"kind": "value", "value": {"kind": "int", "value": operand}} if isinstance(operand, int) else
        {"kind": "list", "value": [{"kind": "real", "value": value} if value is not None else None for value in operand]}]}
    if isinstance(operand, list) and operand[-1] is not None:
        row["max"] = operand[-1]
    return row


class ItemAuraSlotTests(unittest.TestCase):
    def setUp(self):
        rows, contract = fixture()
        self.native = book.native_talent_context(rows, contract, slots.SOURCE)
        self.native["aura_slots"], self.images = domain()
        self.said = lambda key: {"en": NAMES[key.removeprefix("talent_name_")]} if key.removeprefix("talent_name_") in NAMES else None

    def test_actual_unnamed_crown_stat_envelopes_produce_all_four_auras(self):
        stats = json.loads((Path(__file__).with_name("fixtures") / "crown-of-doom-aura-stat-lines-26297349.json").read_bytes())
        result = book.native_aura_granted(stats, self.said, self.native)
        self.assertEqual([row["talent_id"] for row in result], [584, 585, 586, 587])
        self.assertEqual([row["levels"] for row in result], [[5, 15]] * 4)
        self.assertEqual(stats, [])

    def test_a_different_nested_stat_or_source_cannot_authorize_a_grant(self):
        original = json.loads((Path(__file__).with_name("fixtures") / "crown-of-doom-aura-stat-lines-26297349.json").read_bytes())[:2]
        for mode in ("id", "source", "call"):
            stats = copy.deepcopy(original)
            if mode == "id":
                stats[0]["raw"]["id"] = 321
            elif mode == "source":
                stats[0]["raw"]["source"]["rva"] += 1
            else:
                stats[0]["raw"]["raw"]["rva"] += 1
            self.assertEqual(book.native_aura_granted(stats, self.said, self.native), [])
            self.assertEqual(len(stats), 2)

    def test_crown_has_four_distinct_current_talents_and_four_base_ranges(self):
        stats = [statement(stat, value, 100 + n) for n, (stat, value) in enumerate([
            (319, 584), (320, [5, 15]), (321, 585), (322, [5, 15]),
            (323, 586), (324, [5, 15]), (325, 587), (326, [5, 15])])]
        unrelated = statement(154, [900, 1000], 200)
        stats.append(unrelated)
        result = book.native_aura_granted(stats, self.said, self.native)
        self.assertEqual([r["talent_id"] for r in result], [584, 585, 586, 587])
        self.assertEqual([r["names"]["en"] for r in result], list(NAMES.values()))
        self.assertEqual([r["levels"] for r in result], [[5, 15]] * 4)
        self.assertEqual(stats, [unrelated])
        self.assertTrue(all(len(r["source_stats"]) == 2 and r["provenance"]["runtime_value_inferred"] is False for r in result))

    def test_unknown_or_ambiguous_levels_stay_raw_without_hiding_the_talent(self):
        for mode in ("hole", "duplicate", "reversed", "fractional", "wrong_source", "scalar_zero"):
            level = statement(320, [5, None] if mode == "hole" else [15, 5] if mode == "reversed" else [1.5, 3] if mode == "fractional" else 0 if mode == "scalar_zero" else [5, 15], 11)
            stats = [statement(319, 584, 10), level]
            if mode == "duplicate":
                stats.append(copy.deepcopy(level))
            if mode == "wrong_source":
                level["source"]["file"] = "reference"
            result = book.native_aura_granted(stats, self.said, self.native)
            self.assertEqual(len(result), 1, mode)
            self.assertEqual(result[0]["levels"], [0, 0] if mode == "scalar_zero" else None, mode)
            self.assertEqual(len(stats), 0 if mode == "scalar_zero" else 2 if mode == "duplicate" else 1, mode)

    def test_missing_cross_source_or_mutated_slot_domains_leave_both_statements(self):
        for mode in ("missing", "source", "selector", "level", "certificate", "duplicate_selector", "unknown_talent"):
            native = copy.deepcopy(self.native)
            stats = [statement(319, 9999 if mode == "unknown_talent" else 584, 10), statement(320, [5, 15], 11)]
            if mode == "missing":
                native.pop("aura_slots")
            elif mode == "source":
                native["source_sha256"] = "0" * 64
            elif mode in ("selector", "level"):
                native["aura_slots"]["slots"][0][mode + "_stat_id"] += 1
            elif mode == "certificate":
                native["aura_slots"]["certificate_sha256"] = "0" * 64
            elif mode == "duplicate_selector":
                stats.append(copy.deepcopy(stats[0]))
            original = copy.deepcopy(stats)
            self.assertEqual(book.native_aura_granted(stats, self.said, native), [], mode)
            self.assertEqual(stats, original, mode)

    def test_changed_native_transport_fails_and_new_game_source_withholds_the_profile(self):
        self.assertIsNone(slots.verify("0" * 64, lambda *_: b""))
        first = slots.certificate()["spans"][0]
        at = first["start_rva"]
        with self.assertRaisesRegex(ValueError, "transport changed"):
            slots.verify(slots.SOURCE, lambda start, size: bytes(size) if start == at else self.images.get((start, size), b""))
