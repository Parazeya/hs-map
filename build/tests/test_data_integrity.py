import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_bundle import Bundle, BundleError, attach_exclusive_sources, drop_denominator, inventory_fingerprint, place_codes, tables_from_items, verify_item_coverage, verify_map_marker_sources
import encyclopedia
import skills
import words
import unholy
import portraits


class ExportBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.game = self.home / "game"
        self.game.mkdir()
        binary = self.game / "Hero_Siege.exe"
        binary.write_bytes(b"the selected game build")
        data = self.game / "data.win"
        data.write_bytes(b"game data")
        self.folder = self.home / "bundle"
        self.folder.mkdir()
        files = [{"path": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "size": source.stat().st_size} for source in (binary, data)]
        self.manifest = {"schema_version": 1, "game": {
            "fingerprint": inventory_fingerprint(files), "files": files},
            "datasets": {}}
        for name, rows in (("items", [{"metadata": {"tkey": "test", "record_id": "test@0", "fromGame": []}}]),
                           ("talents", [{"id": 1, "key": "test"}])):
            file = self.folder / f"{name}.json"
            file.write_text(json.dumps(rows), encoding="utf-8")
            self.manifest["datasets"][name] = {"file": file.name,
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "records": len(rows), "status": "complete"}
        self.save()

    def save(self):
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_modified_dataset_is_rejected_before_use(self):
        (self.folder / "items.json").write_text('[{"stale":true}]', encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "SHA-256"):
            Bundle(self.folder, self.game)

    def test_source_inventory_and_fingerprint_cannot_drift_apart(self):
        self.manifest["game"]["files"][0]["size"] += 1
        self.save()
        with self.assertRaisesRegex(BundleError, "fingerprint does not match"):
            Bundle(self.folder)

    def test_source_inventory_requires_both_native_inputs(self):
        self.manifest["game"]["files"] = self.manifest["game"]["files"][:1]
        self.save()
        with self.assertRaisesRegex(BundleError, "must contain"):
            Bundle(self.folder)

    def test_inventory_canonicalization_sorts_utf8_and_ignores_object_key_order(self):
        files = self.manifest["game"]["files"] + [{"size": 1, "sha256": "b" * 64, "path": "я.csv"},
                                                    {"size": 2, "path": "é.csv", "sha256": "c" * 64}]
        expected = hashlib.sha256(json.dumps([{key: row[key] for key in ("path", "sha256", "size")}
                                  for row in sorted(files, key=lambda row: row["path"].encode("utf-8"))],
                                  ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(inventory_fingerprint(list(reversed(files))), expected)

    def test_game_update_requires_a_new_export(self):
        (self.game / "Hero_Siege.exe").write_bytes(b"another game build")
        with self.assertRaisesRegex(BundleError, "differs"):
            Bundle(self.folder, self.game)

    def test_dataset_cannot_escape_export_directory(self):
        self.manifest["datasets"]["items"]["file"] = "../outside.json"
        self.save()
        with self.assertRaisesRegex(BundleError, "escapes"):
            Bundle(self.folder, self.game)

    def test_all_declared_files_are_verified(self):
        self.manifest["datasets"]["other"] = {"file": "absent.json", "sha256": "0" * 64, "status": "partial"}
        self.save()
        with self.assertRaises(BundleError):
            Bundle(self.folder, self.game)

    def test_record_count_and_identity_are_part_of_the_boundary(self):
        self.manifest["datasets"]["items"]["records"] = 2
        self.save()
        with self.assertRaisesRegex(BundleError, "record count"):
            Bundle(self.folder, self.game)

    def test_a_complete_manifest_loads_nested_generation_paths(self):
        old = self.folder / "items.json"
        nested = self.folder / "generations" / "one" / old.name
        nested.parent.mkdir(parents=True)
        old.rename(nested)
        self.manifest["datasets"]["items"]["file"] = "generations/one/items.json"
        self.save()
        bundle = Bundle(self.folder, self.game)
        self.assertEqual(bundle.read("items")[0]["metadata"]["record_id"], "test@0")


class ItemPreservationTests(unittest.TestCase):
    def test_generic_and_compound_dungeon_locations(self):
        rooms = ["Act_01_01", "Act_08_02", "Act_09_04", "Act_01_Boss_Dungeon_03", "Act_09_Boss", "Town_01_rm"]
        self.assertEqual(place_codes("Boss Dungeons", rooms), ["1-BD", "9-BD"])
        self.assertEqual(place_codes("Dungeons", rooms), ["1-D", "8-D", "9-D"])
        self.assertEqual(place_codes("Act V & VIII Dungeons", rooms), ["5-D", "8-D"])
        self.assertEqual(place_codes("Act IV Boss Dungeons", rooms), ["4-BD"])
        self.assertEqual(place_codes("Challenge Dungeon (Inferno Only)", rooms), [])

    def test_native_recipe_keeps_order_duplicates_and_does_not_guess_id_domain(self):
        row = {"runeword_recipe": {"value": [14, 17, 14]},
               "runewordSockets": ["Old reference"]}
        self.assertEqual(encyclopedia.sockets(row, {"old reference": "stale"}, str.lower),
                         [{"id": 14, "unresolved": True}, {"id": 17, "unresolved": True},
                          {"id": 14, "unresolved": True}])
        resolved = {14: {"key": "rune14", "name": "Del"}}
        self.assertEqual(encyclopedia.sockets(row, {}, str.lower, resolved)[0],
                         {"id": 14, "key": "rune14", "name": "Del"})
        row["runeword"] = {"recipe_item_domain": {"status": "native_runtime_binding", "packet_field": "b", "item_type": 15},
                           "recipe_items": [{"status": "source_bound_item_identity", "rune_id": 14,
                                             "key": "current-rune14", "name": "Current name"}]}
        self.assertEqual(encyclopedia.sockets(row, {}, str.lower, resolved)[0]["key"], "current-rune14")
        row["runeword"]["recipe_item_domain"]["item_type"] = 3
        self.assertTrue(encyclopedia.sockets(row, {}, str.lower)[0]["unresolved"])

    def test_native_equipment_domains_use_current_names_and_keep_scalar_weapon_restrictions(self):
        row = {"runeword": {"eligibility": {"item_type": [{"id": 1, "name": "Chest"}, {"id": 3, "name": "Weapon"}],
                                             "weapon_type": [{"id": 5, "name": "Polearm"}]}}}
        self.assertEqual(encyclopedia.weapons(row), ["Polearm"])
        self.assertEqual(encyclopedia.made_in(row, {1: {"Body Armor"}, 3: {"Sword", "Axe"}}), "Body Armor or Weapon")

    def test_native_stat_storage_keeps_variants_and_outer_selector_separate(self):
        selector = {"domain": "socket.outer_key", "observed": {"kind": "value", "value": {"kind": "int", "value": 69}}}
        row = {"stats": [{"id": 21, "min1": 100}], "stats_channels": {
            "runeword_base": {"stats": [{"id": 21, "min1": 0}]},
            "runeword_two_handed": {"stats": [{"id": 21, "min1": 10}]},
            "socket": {"stats": [{"id": 226, "min1": 1, "outer_selector": selector,
                                     "native_observation": {"arguments": [69, 226, 1]}}]}}}
        groups = encyclopedia.variants(row)
        self.assertEqual([g["channel"] for g in groups], ["runeword_base", "runeword_two_handed", "socket"])
        self.assertEqual([g["stats"][0]["min"] for g in groups], [0, 10, 1])
        self.assertEqual(groups[2]["stats"][0]["id"], 226)
        self.assertEqual(groups[2]["stats"][0]["outer_selector"], selector)
        self.assertEqual(row["stats"], [{"id": 21, "min1": 100}])

    def test_all_native_markers_and_inferred_reference_offsets_are_auditable(self):
        native = [{"room": "Cabin", "x": 10, "y": 20, "source": {"kind": "decoded"}}]
        rendered = [native[0], {"room": "Reference dungeon", "x": 40, "y": 20, "source": {
            "kind": "inferred", "anchor_room": "Cabin", "offset": {"x": 30, "y": 0},
            "reference": {"kind": "reference", "verified_for_game_build": False}}}]
        self.assertEqual(verify_map_marker_sources(native, rendered)["reference_markers"], 1)
        with self.assertRaisesRegex(BundleError, "omitted"):
            verify_map_marker_sources(native, [])
        rendered[1].pop("source")
        with self.assertRaisesRegex(BundleError, "no coordinate provenance"):
            verify_map_marker_sources(native, rendered)

    def test_only_the_tutorial_cabin_is_excluded_from_the_public_map(self):
        cabin = {"room": "Cabin_01_rm", "x": 109, "y": 521, "source": {"kind": "decoded"}}
        town = {"room": "Town_01_rm", "x": 145, "y": 530, "source": {"kind": "decoded"}}
        other_cabin = {"room": "Cabin_02_rm", "x": 200, "y": 530, "source": {"kind": "decoded"}}
        native = [cabin, town, other_cabin]

        coverage = verify_map_marker_sources(native, [town, other_cabin])
        self.assertEqual(coverage["native_exported"], 3)
        self.assertEqual(coverage["native_shown"], 2)
        self.assertEqual(coverage["native_excluded"], [
            {"room": "Cabin_01_rm", "reason": "tutorial_cabin_without_drops"},
        ])
        self.assertEqual(coverage["rendered_markers"], 2)

        with self.assertRaisesRegex(BundleError, "displayed excluded marker: Cabin_01_rm"):
            verify_map_marker_sources(native, native)
        with self.assertRaisesRegex(BundleError, "omitted verified native markers: Cabin_02_rm"):
            verify_map_marker_sources(native, [town])

    def test_failed_record_icon_binding_does_not_certify_a_name_match(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "translationsItem.csv"
            csv.write_text("test|Test\n", encoding="utf-8")
            rows = [{"metadata": {"tkey": "test", "record_id": "one", "name": "Test", "sprite": "CurrentSprite"}}]
            matched = {"test": [1, 2, 3, 4]}
            items, _, _ = encyclopedia.build(rows, csv, ["en"], matched, str.lower, {})
            self.assertEqual(items["test"]["iconSource"], "name_match")
            matched["record:one"] = [5, 6, 7, 8]
            items, _, _ = encyclopedia.build(rows, csv, ["en"], matched, str.lower, {})
            self.assertEqual(items["test"]["iconSource"], "game")
            self.assertEqual(items["test"]["icon"], [5, 6, 7, 8])

    def test_unverified_place_observation_is_not_a_codex_drop_location(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "translationsItem.csv"
            csv.write_text("test|Test\n", encoding="utf-8")
            rows = [{"metadata": {"tkey": "test", "record_id": "one", "name": "Test", "fromGame": []},
                     "dropPlaces": ["Unverified Boss"], "provenance": {"dropPlaces": {"kind": "heuristic"}}}]
            items, _, _ = encyclopedia.build(rows, csv, ["en"], {}, str.lower, {})
            self.assertNotIn("places", items["test"])

    def test_no_verified_drop_sources_still_produces_valid_portrait_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            _, _, size, _ = portraits.build(None, [], output / "bosses.png", output / "contact.png")
            self.assertGreater(size[1], 0)
            self.assertTrue((output / "contact.png").is_file())

    def test_exclusive_edges_do_not_become_locations_or_leak_to_base_variants(self):
        rows = [{"metadata": {"record_id": rid, "tkey": "same", "named": named, "ID": identity}}
                for rid, named, identity in (("base", False, [4, 0, 5]), ("named", True, [4, 0, 5]),
                                             ("other-named", True, [99, 0, 5]))]
        items = {"same": {"record_id": "base", "variants": [{"record_id": "named"}, {"record_id": "other-named"}]}}
        graph = {"payload_contract": {"status": "verified"}, "sources": [{
            "key": "exclusive:123", "name": None, "kind": "native_script", "items": ["same"],
            "semantics": "exclusive_drop_mechanism", "ownership_status": "unresolved_conditional_owner",
            "provenance": {"entries": [{"item": "same", "tuple": [5, 0, 4], "named": True, "status": "verified_named_identity"}]}}]}
        self.assertEqual(attach_exclusive_sources(rows, items, graph), 1)
        self.assertNotIn("exclusive_sources", items["same"])
        variant = items["same"]["variants"][0]
        self.assertEqual(variant["exclusive_sources"][0]["kind"], "native_script")
        self.assertNotIn("places", variant)
        self.assertNotIn("inferno", variant)
        self.assertNotIn("exclusive_sources", items["same"]["variants"][1])
        graph["payload_contract"]["status"] = "unresolved"
        self.assertEqual(attach_exclusive_sources(rows, {"same": {"record_id": "named"}}, graph), 0)

    def test_explicit_fifty_million_is_a_denominator_until_code_says_no_drop(self):
        row = {"provenance": {"droprate": {"kind": "decoded"}},
               "droprate": {"base": 50_000_000, "meaning": "denominator"}}
        self.assertEqual(drop_denominator(row), 50_000_000)
        row["droprate"]["meaning"] = "no_drop"
        self.assertIsNone(drop_denominator(row))
        row["droprate"] = {"base": float("inf")}
        self.assertIsNone(drop_denominator(row))

    def test_numeric_candidate_stats_and_explicit_slots_remain_distinct(self):
        candidate = {"id": 110, "min1": 8, "max1": 12}
        variant = encyclopedia.variants({"stats_random": [candidate]})
        self.assertEqual(variant[0]["stats"][0]["raw"]["id"], 110)
        self.assertEqual(variant[0]["stats"][0]["min"], 8)
        slot = encyclopedia.stat_line({"kind": "random_stat_slot", "slot": 2, "selector": 4})
        self.assertEqual((slot["pool"], slot["slot"]), (4, 2))
        self.assertNotIn("min", slot)
        inactive = encyclopedia.stat_line({"kind": "random_stat_slot", "selector": 0, "active": False})
        self.assertFalse(inactive["active"])

    def test_pool_remap_requires_verified_current_caller_rules(self):
        class Say:
            by_key = {"damage": {"en": "Damage"}}
        pools = [{"selector": n, "arms": [{"sites": [{"id": 110, "name": "damage", "min": 1, "max": 2}]}]} for n in (1, 2, 3)]
        rules = {"status": "unresolved", "selector_remap": {"when_selector": 4, "roll": {"values": [1, 2, 3]}}}
        self.assertNotIn("4", unholy.labelled(Say(), {"pools": pools, "selection_rules": rules})["selects"])
        rules["status"] = "verified_instruction_pattern"
        self.assertEqual(unholy.labelled(Say(), {"pools": pools, "selection_rules": rules})["selects"]["4"], [1, 2, 3])

    def test_numeric_effect_and_its_entire_ladder_survive(self):
        raw = {"id": 185, "values": [1, 4, 3], "reference": {"talent": 713}}
        line = encyclopedia.stat_line(raw)
        self.assertEqual(line["sid"], "unresolved_185")
        self.assertEqual(line["values"], [1, 4, 3])
        self.assertEqual(line["reference"], {"talent": 713})
        self.assertEqual(line["raw"]["id"], 185)
        self.assertTrue(line["unresolved"])

    def test_named_effect_also_retains_its_typed_reference_arguments(self):
        raw_call = {"args": [{"kind": "value", "value": {"kind": "int", "value": 42}},
                             {"kind": "reference", "value": "talentReference"}], "rva": 123}
        line = encyclopedia.stat_line({"id": 42, "sid": "chance_when_striking", "min1": 5,
                                       "status": "unresolved", "raw": raw_call})
        self.assertEqual(line["raw"], raw_call)
        self.assertEqual(line["status"], "unresolved")

    def test_resource_expression_retains_exact_tokens_without_becoming_a_numeric_ladder(self):
        reference = {"native_kind": 15, "reference_tag": 3, "index": 1,
                     "payload_hex": "0x0100000300000001", "room": {"name": "Act_01_01"}}
        expression = {"status": "source_bound_call_expression", "numeric": False,
                      "expression": {"call": "GetTabletZones"}}
        raw = {"id": 347, "status": "interpreted", "resource_references": [reference],
               "value_expression": expression, "value_kind": "source_bound_resource_reference_expression"}
        line = encyclopedia.stat_line(raw)
        self.assertEqual(line["resource_references"], [reference])
        self.assertEqual(line["value_expression"], expression)
        self.assertIsNone(line.get("min"))
        self.assertIsNone(line.get("max"))
        self.assertNotIn("rank", line)

    def test_every_record_of_one_translation_key_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "translationsItem.csv"
            csv.write_text("helmet_normal_cap|Cap\n", encoding="utf-8")
            rows = [{"metadata": {"tkey": "helmet_normal_cap", "name": "Cap", "type": "Helmet",
                                  "tier": tier, "ID": [i, 0, 0], "record_id": f"cap-{tier}"},
                     "stats": [{"id": 999, "min1": value}]} for i, tier, value in ((0, "D", 3), (1, "C", 9))]
            tables = {key: {} for key in ("DROP_PLACES", "DROP_RATE", "DROP_CHASE")}
            items, vocab, _ = encyclopedia.build(rows, csv, ["en"], {}, str.lower, tables)
            cap = items["helmet_normal_cap"]
            self.assertEqual(cap["stats"][0]["min"], 3)
            self.assertEqual(cap["variants"][0]["stats"][0]["min"], 9)
            self.assertEqual(cap["variants"][0]["record_id"], "cap-C")
            self.assertEqual(vocab[0]["n"], 2)
            self.assertEqual(verify_item_coverage(rows, items)["output_records"], 2)
            cap["variants"].clear()
            with self.assertRaisesRegex(BundleError, "lost or replaced"):
                verify_item_coverage(rows, items)

    def test_old_chase_factor_cannot_combine_with_a_fresh_rate(self):
        row = {"metadata": {"name": "Test sword", "rarity": "Satanic", "tier": "S",
                            "fromGame": ["name", "rarity", "tier", "droprate", "dropPlaces"]},
               "droprate": {"base": 1000}, "chaseDropRate": .1, "dropPlaces": ["Act IX Zone 3"]}
        tables = tables_from_items([row], ["Act_09_03"])
        self.assertEqual(tables["DROP_RATE"]["test sword"], 1000)
        self.assertNotIn("test sword", tables["DROP_CHASE"])
        self.assertEqual(tables["DROP_ZONES"]["test sword"], ["9-3"])


class SkillAuthorityTests(unittest.TestCase):
    def test_duplicate_talent_keys_or_names_do_not_select_a_winner_and_numbers_remain_available(self):
        rows = [{"id": 19, "key": "blazingTrail", "class": "Pyromancer"},
                {"id": 660, "key": "blazingTrail", "class": ""},
                {"id": 1, "key": "uniqueSkill", "class": "Viking"}]
        index = encyclopedia.unique_talent_index(rows, lambda row: row["key"].lower())
        self.assertNotIn("blazingtrail", index)
        self.assertEqual(index["uniqueskill"]["id"], 1)
        numbers = {row["id"]: row for row in rows}
        self.assertEqual(numbers[660]["class"], "")
        self.assertIsNone(encyclopedia.at_number(660, numbers, []),
                          "a retained numeric record does not establish the game's runtime numbering")
        names = encyclopedia.unique_talent_index(rows[:2], lambda row: "Blazing Trail")
        self.assertEqual(names, {})

    def test_partial_effects_and_decoder_uncertainty_survive_both_consumers(self):
        talent = {"key": "partialSkill", "class": "Viking", "tags": [], "element": [],
                  "effects": [{"index": 1, "start": None, "per_level": 8, "mark": "", "mark_known": False, "desc": "damage"},
                              {"index": 2, "start": None, "per_level": 0, "mark": "", "mark_known": True, "desc": "chance"},
                              {"index": 3, "start": 4, "per_level": None, "mark": "tal_future_unit", "mark_known": True, "desc": "time"}],
                  "control_flow_complete": False,
                  "interpretation_notes": ["starting values are unread"],
                  "constructor_inheritance": {"status": "proven_constructor_inheritance", "fields": {}},
                  "inheritance_application": {"scope": "existing_effect_projections_only", "applied_fields": []},
                  "field_write_sources": {"abilityValue1": {"source": "Hero_Siege.exe", "write_rva": 42}},
                  "field_value_interpretations": {"abilitySprite": {"source": "Hero_Siege.exe", "raw_value_rewritten": False}},
                  "unresolved_fields": ["abilityMark1", "abilityStartingValue1", "abilityStartingValue2"],
                  "raw_fields": {"abilityValue1": {"kind": "value", "value": {"kind": "int", "value": 8}}}}
        with tempfile.TemporaryDirectory() as directory:
            result, *_ = skills.build([talent], [], lambda _: None, ["en"], Path(directory))
        skill = result["skills"]["partialSkill"]
        grant = encyclopedia.spoken(talent, None, lambda _: None)
        for lines in (skill["lines"], grant["lines"]):
            self.assertIsNone(lines[0]["start"])
            self.assertEqual(lines[0]["per"], 8)
            self.assertIsNone(lines[1]["start"])
            self.assertEqual(lines[1]["per"], 0)
            self.assertFalse(lines[0]["mark_known"])
            self.assertTrue(lines[1]["mark_known"])
            self.assertEqual(lines[0]["mark"], "")
            self.assertEqual(lines[1]["mark"], "")
            self.assertTrue(lines[2]["mark_known"])
            self.assertEqual(lines[2]["mark"], "tal_future_unit",
                             "an untranslated known unit must not disappear into a flat value")
        for source in (skill, grant["talent_source"]):
            self.assertFalse(source["control_flow_complete"])
            self.assertEqual(source["interpretation_notes"], talent["interpretation_notes"])
            self.assertEqual(source["unresolved_fields"], talent["unresolved_fields"])
            self.assertEqual(source["raw_fields"], talent["raw_fields"])
            self.assertEqual(source["constructor_inheritance"], talent["constructor_inheritance"])
            self.assertEqual(source["inheritance_application"], talent["inheritance_application"])
            self.assertEqual(source["field_write_sources"], talent["field_write_sources"])
            self.assertEqual(source["field_value_interpretations"], talent["field_value_interpretations"])

    def test_game_zero_and_empty_tags_override_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            planner = [{"classId": "Viking", "id": "zeroSkill", "name": "Zero Skill",
                        "baseCooldown": 12, "effectDuration": 30, "tags": ["Attack"], "damageType": "fire"}]
            (folder / "viking.json").write_text(json.dumps(planner), encoding="utf-8")
            current = [{"key": "zeroSkill", "class": "Viking", "cooldown": 0,
                        "duration": 0, "tags": [], "element": [],
                        "effects": [{"index": 1, "start": 9, "per_level": None, "mark": "%", "desc": "damage"}],
                        "unresolved_fields": ["Description1_PerLevel"], "raw_fields": {"Description1_PerLevel": {"kind": "unknown"}}}]
            result, *_ = skills.build(current, [], lambda _: None, ["en"], folder)
            skill = result["skills"]["zeroSkill"]
            self.assertEqual(skill["cooldown"], 0)
            self.assertEqual(skill["lasts"], 0)
            self.assertEqual(skill["tags"], [])
            self.assertEqual(skill["element"], [])
            self.assertNotIn("cooldown", skill["provenance"]["reference"])
            self.assertIsNone(skill["lines"][0]["per"])
            self.assertEqual(skill["lines"][0]["index"], 1)
            self.assertEqual(skill["unresolved_fields"], ["Description1_PerLevel"])

    def test_translation_lookup_reads_only_manifest_selected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            current = folder / "translationsCurrent.csv"
            current.write_text("current|Current name|Nykyinen\n", encoding="utf-8")
            (folder / "translationsOld.csv").write_text("stale|Old name\n", encoding="utf-8")
            lookup = words.Words(paths=[current])
            self.assertEqual(lookup.by_key["current"]["en"], "Current name")
            self.assertNotIn("stale", lookup.by_key)


if __name__ == "__main__":
    unittest.main()
