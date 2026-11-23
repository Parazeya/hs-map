import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gear


class MultipleGrantTests(unittest.TestCase):
    def test_crown_of_doom_keeps_all_four_reference_auras_and_level_ranges(self):
        rows = json.loads((Path(__file__).resolve().parents[1] / "planner/gear/items/helmets.json").read_text(encoding="utf-8"))
        crown = next(row for row in rows if row["name"] == "Crown of Doom")
        source = json.loads(json.dumps(crown))
        result = gear.grants({"items": [crown]}, {"helmet_crown_of_doom": {"names": {"en": "Crown of Doom"}}})
        self.assertEqual(result["helmet_crown_of_doom"], [
            ("Stoneskin Aura", [5, 15]), ("Hasteful Aura", [5, 15]),
            ("Baleful Aura", [5, 15]), ("Fortunate Aura", [5, 15])])
        self.assertEqual(crown, source)

    def test_single_skill_and_zero_level_are_preserved(self):
        result = gear.grants({"items": [{"name": "Example", "skillBonuses": {"Charge": 0}}]},
                             {"example": {"names": {"en": "Example"}}})
        self.assertEqual(result, {"example": [("Charge", [0])]})
