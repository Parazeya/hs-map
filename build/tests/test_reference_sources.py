import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reference_sources as references


class ReferenceSourceTests(unittest.TestCase):
    def test_two_reported_chests_keep_exactly_seven_and_one_published_entries(self):
        reference = references.catalogue()
        reference["sources"] = [row for row in reference["sources"] if row["name"] in ("Crystal Chest", "Dungeon Chest")]
        items = {row["item"]: {"rate": 42, "places": []} for source in reference["sources"] for row in source["drops"]}
        before = copy.deepcopy(items)
        sources = {}
        self.assertEqual(references.merge_map(items, sources, reference), 8)
        self.assertEqual(len(sources["Crystal Chest"]["drops"]), 7)
        self.assertEqual([r["item"] for r in sources["Dungeon Chest"]["drops"]], ["signet of kadosh"])
        self.assertTrue(all(row["reference"]["verified_for_game_build"] is False for s in sources.values() for row in s["drops"]))
        self.assertEqual(items, before, "reference connections never replace current rates or declared locations")
        self.assertEqual(references.merge_map(items, sources, reference), 0)
        duplicated = copy.deepcopy(reference)
        duplicated["sources"][0]["drops"] *= 2
        unique = {}
        self.assertEqual(references.merge_map(items, unique, duplicated), 8)
        self.assertEqual(len(unique["Crystal Chest"]["drops"]), 7)

    def test_verified_edges_are_not_replaced_and_absent_items_are_not_invented(self):
        reference = references.catalogue()
        original = {"item": "signet of kadosh", "inferno": False, "provenance": {"kind": "decoded"}}
        sources = {"Dungeon Chest": {"kind": "source", "drops": [copy.deepcopy(original)], "inferno_only": False}}
        self.assertEqual(references.merge_map({"signet of kadosh": {}}, sources, reference), 0)
        self.assertEqual(sources["Dungeon Chest"]["drops"], [original])
        self.assertNotIn("Crystal Chest", sources)

    def test_item_cards_keep_reference_locations_separate_and_do_not_duplicate_them(self):
        reference = references.catalogue()
        items = {"belt": {"names": {"en": "Belt of Infinite Wealth"}, "places": ["Verified source"]}}
        self.assertEqual(references.merge_records(items, reference), 1)
        self.assertEqual(items["belt"]["places"], ["Verified source"])
        self.assertEqual(items["belt"]["reference_places"][0]["name"], "Crystal Chest")
        self.assertEqual(references.merge_records(items, reference), 0)
