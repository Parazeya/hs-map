import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_zones as references


class ReferenceZoneTests(unittest.TestCase):
    def test_published_snapshot_restores_five_current_items_to_the_devils_breach(self):
        reference = references.catalogue()
        self.assertEqual(reference["reference"]["snapshot_commit"], "6a39f9b634d77906d26fdf2c18d067fe7c964f90")
        self.assertEqual(reference["reference"]["snapshot_sha256"], "ce57efed86153c4aecc1ae8b5c24aff75da99e3a7541f151de026b371857dc3f")
        self.assertEqual(reference["reference"]["catalogue_sha256"], hashlib.sha256(references.CATALOGUE.read_bytes()).hexdigest())
        self.assertIs(reference["reference"]["verified_for_game_build"], False)
        self.assertEqual(len(reference["zones"]), 81)
        self.assertEqual(sum(len(zone["drops"]) for zone in reference["zones"]), 641)

        expected = [
            "set's lightning sash",
            "frostbitten necrosis",
            "diablo",
            "deathquill",
            "elixir of unworldly cognition",
        ]
        items = {name: {"rarity": "Heroic", "zones": [], "places": [], "rate": 42, "chase": None} for name in expected}
        before = copy.deepcopy(items)
        room = {"room": "Act_04_05", "code": "4-5", "drops": ["current item"]}
        self.assertEqual(references.merge_map(items, [room], reference), 5)
        self.assertEqual(room["drops"], ["current item", *expected])
        self.assertEqual(room["reference_drops"], expected)
        self.assertNotIn("reference_drop_odds", room)
        self.assertEqual(items, before)
        self.assertEqual(references.merge_map(items, [room], reference), 0)
        self.assertEqual(room["drops"], ["current item", *expected])
        self.assertEqual(room["reference_drops"], expected)

    def test_requires_exact_node_and_identity_and_never_overrides_an_explicit_location(self):
        drops = [
            {"item": "native", "rarity": "Heroic"},
            {"item": "other place", "rarity": "Heroic"},
            {"item": "other zone code", "rarity": "Heroic"},
            {"item": "renamed item", "rarity": "Heroic"},
            {"item": "rarity changed", "rarity": "Heroic"},
            {"item": "rarity unknown"},
            {"item": "set piece", "rarity": "Satanic Set"},
            {"item": "set piece", "rarity": "Set"},
        ]
        reference = {"zones": [{"room": "Act_04_05", "code": "4-5", "drops": drops}]}
        items = {
            "native": {"rarity": "Heroic"},
            "other place": {"rarity": "Heroic", "places": ["Dungeons"]},
            "other zone code": {"rarity": "Heroic", "zones": ["4-1"]},
            "renamed-item": {"rarity": "Heroic"},
            "rarity changed": {"rarity": "Unholy"},
            "rarity unknown": {},
            "set piece": {"rarity": " set "},
        }
        correct = {"room": "Act_04_05", "code": "4-5", "drops": ["native"]}
        wrong_code = {"room": "Act_04_05", "code": "4-4", "drops": []}
        wrong_room = {"room": "Another_Room", "code": "4-5", "drops": []}
        self.assertEqual(references.merge_map(items, [correct, wrong_code, wrong_room], reference), 1)
        self.assertEqual(correct["drops"], ["native", "set piece"])
        self.assertEqual(correct["reference_drops"], ["set piece"])
        for untouched in (wrong_code, wrong_room):
            self.assertEqual(untouched["drops"], [])
            self.assertNotIn("reference_drops", untouched)

    def test_published_ak47_odds_stay_on_the_three_matching_rooms(self):
        item = {"rarity": "Heroic", "zones": [], "places": [], "rate": 527120, "chase": None}
        rooms = [
            {"room": "Act_07_04", "code": "7-4", "drops": []},
            {"room": "Act_07_05", "code": "7-5", "drops": []},
            {"room": "Act_07_Boss_Dungeon_03", "code": "7-BD", "drops": []},
            {"room": "Act_07_03", "code": "7-3", "drops": []},
        ]
        items = {"ak-47": item}
        self.assertEqual(references.merge_map(items, rooms, references.catalogue()), 3)
        for room in rooms[:3]:
            self.assertEqual(room["reference_drops"], ["ak-47"])
            self.assertEqual(room["reference_drop_odds"], {"ak-47": 167360})
        self.assertNotIn("reference_drop_odds", rooms[3])
        self.assertIsNone(item["chase"])

    def test_keeps_known_locations_when_historical_odds_do_not_match(self):
        drops = [
            {"item": "changed base", "rarity": "Heroic", "rate": 70, "chase": 25},
            {"item": "missing base", "rarity": "Heroic", "chase": 25},
            {"item": "invalid chase", "rarity": "Heroic", "rate": 50, "chase": True},
            {"item": "zero chase", "rarity": "Heroic", "rate": 50, "chase": 0},
            {"item": "native", "rarity": "Heroic", "rate": 50, "chase": 25},
        ]
        reference = {"zones": [{"room": "Act_04_05", "code": "4-5", "drops": drops}]}
        items = {drop["item"]: {"rarity": "Heroic", "rate": 50} for drop in drops}
        room = {"room": "Act_04_05", "code": "4-5", "drops": ["native"]}
        self.assertEqual(references.merge_map(items, [room], reference), 4)
        self.assertEqual(room["reference_drops"], [drop["item"] for drop in drops[:4]])
        self.assertNotIn("reference_drop_odds", room)
