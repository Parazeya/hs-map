import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from encyclopedia import stat_line


def real(value):
    return {"kind": "real", "value": value}


def source_call(values, stat_id=20, rva=0xD34AB9):
    return {"rva": rva, "args": [
        {"kind": "value", "value": {"kind": "int", "value": stat_id}},
        {"kind": "list", "value": values},
    ]}


class PartialStatTests(unittest.TestCase):
    def test_current_vocabulary_does_not_recreate_a_missing_or_unsupported_label(self):
        source = {"id": 20, "min1": 0, "max1": 2, "status": "decoded",
                  "source": {"file": "Hero_Siege.exe", "rva": 123},
                  "raw": source_call([real(0), real(2)])}
        original = copy.deepcopy(source)
        for vocabulary in ({}, {"by_id": {}}, {
            "by_id": {"20": {"filter_key": "old_label"}},
            "name_contract": {"status": "unsupported", "source_supported": False,
                              "filter_supported": False, "tooltip_supported": False},
        }):
            line = stat_line(source, vocabulary)
            self.assertEqual(line["sid"], "unresolved_20")
            self.assertTrue(line["unresolved"])
            self.assertEqual((line["min"], line["max"]), (0, 2))
            self.assertEqual(line["raw"]["id"], source["id"])
            self.assertEqual(line["raw"]["raw"], source["raw"])
            self.assertEqual(line["source"], source["source"])
        self.assertEqual(source, original)

    def test_current_supported_label_and_independent_explicit_label_survive(self):
        vocabulary = {"by_id": {"20": {"filter_key": "socketed_flat"}},
                      "name_contract": {"status": "supported_reviewed_source_layout",
                                        "source_supported": True}}
        line = stat_line({"id": 20, "min1": 0}, vocabulary)
        self.assertEqual(line["sid"], "socketed_flat")
        self.assertEqual(line["min"], 0)
        explicit = stat_line({"id": 20, "sid": "independent_source", "max1": 1},
                             {"by_id": {}})
        self.assertEqual(explicit["sid"], "independent_source")

    def test_actual_startup_lower_bound_and_known_upper_remain_partial(self):
        source = {"id": 20, "sid": "socketed_flat", "status": "partial", "max1": 1,
                  "raw": source_call([{"kind": "startup", "value": 0x10B802B8}, real(1)])}
        original = copy.deepcopy(source)
        line = stat_line(source)
        self.assertEqual(line["value_shape"], {"kind": "list", "length": 2})
        self.assertNotIn("min", line)
        self.assertEqual(line["max"], 1)
        self.assertEqual(line["status"], "partial")
        self.assertEqual(line["raw"], source["raw"])
        self.assertEqual(source, original)

    def test_zero_lower_and_unknown_upper_are_not_a_fixed_zero_scalar(self):
        line = stat_line({"id": 20, "min1": 0, "raw": source_call([
            real(0), {"kind": "startup", "value": 0x10B802B8}])})
        self.assertEqual(line["min"], 0)
        self.assertNotIn("max", line)
        self.assertEqual(line["value_shape"]["length"], 2)
        scalar = stat_line({"id": 20, "min1": 0, "status": "partial",
                            "raw": {"args": [None, {"kind": "value", "value": real(0)}]}})
        self.assertEqual(scalar["min"], 0)
        self.assertNotIn("value_shape", scalar)

    def test_holy_bible_preserves_all_ten_levels_without_inventing_level_one(self):
        values = [None, None, None, None, 1, 1, 1, 1, 1, 2]
        source_values = [{"kind": "startup", "value": 0x10B80288} for _ in range(4)] + [real(n) for n in values[4:]]
        source = {"id": 201, "sid": "all_talents", "values": values,
                  "status": "partial", "raw": source_call(source_values, 201, 0xBB44BB)}
        line = stat_line(source)
        self.assertEqual(line["values"], values)
        self.assertEqual(line["value_shape"], {"kind": "list", "length": 10})
        self.assertNotIn("min", line)
        self.assertEqual(line["max"], 2)
        self.assertEqual(line["rank"], 1)

    def test_middle_trailing_and_all_unknown_levels_are_preserved(self):
        for values in ([0, None, 2, None], [None, None, None]):
            line = stat_line({"id": 201, "values": values})
            self.assertEqual(line["values"], values)
            self.assertEqual(line.get("min"), values[0])
            self.assertEqual(line.get("max"), values[-1])
            self.assertNotIn("value_shape", line)

    def test_shape_uses_interpreted_arglist_before_raw_without_guessing_from_values(self):
        source = {"id": 201, "raw": source_call([real(0), real(1)]),
                  "argument_interpretation": source_call([real(1), real(2), real(3)])}
        line = stat_line(source)
        self.assertEqual(line["value_shape"], {"kind": "list", "length": 3})
        self.assertEqual(line["argument_interpretation"], source["argument_interpretation"])
        self.assertNotIn("value_shape", stat_line({"id": 20, "min1": 0, "max1": 1, "values": [0, 1]}))
        self.assertNotIn("value_shape", stat_line({"id": 20, "raw": {"args": [None, {"kind": "list", "value": "not an array"}]}}))


if __name__ == "__main__":
    unittest.main()
