import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import talent_activation as activation
import skills


def identity_fixture():
    return json.loads((Path(__file__).resolve().parent / "fixtures/native-talent-ids-26297349.json").read_text(encoding="utf-8"))


def checked_context(rows, contract, source, *args):
    return activation.context(rows, contract, source, *args, native_id_contract=identity_fixture())


def fixture():
    folder = Path(__file__).resolve().parent / "fixtures"
    ids = json.loads((folder / "native-talent-ids-26297349.json").read_text(encoding="utf-8"))
    contract = json.loads((folder / "native-talent-types-26297349.json").read_text(encoding="utf-8"))
    by_name = {(row["key"], row["class"]): row for row in contract["record_sources"]}
    rows = []
    for identity in ids["record_sources"]:
        record = by_name.get((identity["key"], identity["class"]))
        raw = {"kind": "value", "value": {"kind": "int", "value": record["code"]}} if record else None
        row = {"key": identity["key"], "class": identity["class"], "id": identity["native_id"],
               "id_source": copy.deepcopy(identity), "kind": record["label"] if record else None,
               "raw_fields": {"abilityType": raw} if record else {}, "tags": [], "element": [], "effects": []}
        if record:
            row["kind_source"] = {"native_contract_id": contract["native_contract_id"], "value": copy.deepcopy(record),
                                  "raw_field": "abilityType", "raw_value": raw,
                                  "owner_binding_sha256": identity["binding_sha256"],
                                  "aura_override_applied": False, "final_runtime_activity_certified": False}
        rows.append(row)
    return rows, contract


class TalentActivationTests(unittest.TestCase):
    def test_all_429_source_values_and_388_missing_fields(self):
        rows, contract = fixture()
        facts = checked_context(rows, contract, activation.SOURCE)
        self.assertEqual(len(facts), 429)
        self.assertEqual(sum(f["label"] == "active" for f in facts.values()), 414)
        self.assertEqual(sum(f["label"] == "passive" for f in facts.values()), 15)
        self.assertNotIn(("weaponMaster", "Viking"), facts)

    def test_wrong_raw_value_owner_absence_and_scope_cannot_gain_names(self):
        for change in (
                lambda rows, c: rows[next(i for i, r in enumerate(rows) if r["kind"] == "active")]["raw_fields"]["abilityType"]["value"].update(value=1),
                lambda rows, c: next(r for r in rows if r["kind"])["kind_source"].update(owner_binding_sha256="a" * 64),
                lambda rows, c: next(r for r in rows if r["kind"] is None).update(kind="active"),
                lambda rows, c: c.update(missing_type_inferred=True),
                lambda rows, c: rows.pop()):
            rows, contract = fixture()
            change(rows, contract)
            self.assertEqual(checked_context(rows, contract, activation.SOURCE), {})

    def test_unknown_source_missing_or_self_rehashed_proof_fails_closed(self):
        rows, contract = fixture()
        self.assertEqual(checked_context(rows, contract, "future"), {})
        self.assertEqual(checked_context(rows, None, activation.SOURCE), {})
        record = contract["record_sources"][0]
        record["proof"]["final_write_rva"] += 1
        record["binding_sha256"] = activation.digest({k: v for k, v in record.items() if k != "binding_sha256"})
        contract["native_contract_id"] = activation.digest({"profile": contract["profile"], "source_sha256": activation.SOURCE,
                                                          "witness_sha256": contract["proof"]["sha256"], "record_sources": contract["record_sources"]})
        self.assertEqual(checked_context(rows, contract, activation.SOURCE), {})

    def test_activation_does_not_replace_reference_buff_or_aura_categories(self):
        rows, contract = fixture()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "reference.json").write_text(json.dumps([
                {"classId": "Viking", "id": "defensiveShout", "name": "Defensive Shout", "kind": "buff"},
                {"classId": "Pyromancer", "id": "scorchingAura", "name": "Scorching Aura", "kind": "aura"}]), encoding="utf-8")
            result, *_ = skills.build(rows, [], lambda _: None, ["en"], folder,
                                      talent_type_contract=contract, talent_type_source_sha256=activation.SOURCE,
                                      talent_id_contract=identity_fixture())
        for key, category in (("defensiveShout", "buff"), ("scorchingAura", "aura")):
            row = result["skills"][key]
            self.assertEqual(row["kind"], category)
            self.assertEqual(row["activation_type"], "active")
            self.assertIn("activation_type", row["provenance"]["game"])
            self.assertIn("kind", row["provenance"]["reference"])
        self.assertIsNone(result["skills"]["weaponMaster"]["activation_type"])

    def test_booleans_resources_startup_and_nonfinite_values_are_not_codes(self):
        for kind, value in (("bool", False), ("bool", True), ("text", "0"), ("startup", 0),
                            ("real", float("nan")), ("real", float("inf")), ("real", .5), ("int", 2)):
            self.assertIsNone(activation.raw_code({"kind": "value", "value": {"kind": kind, "value": value}}))
        self.assertIsNone(activation.raw_code({"kind": "list", "value": [{"kind": "int", "value": 0}]}))

    def test_independent_id_catalog_rejects_synchronized_owner_forgery_and_wrong_id(self):
        rows, contract = fixture()
        self.assertEqual(activation.context(rows, contract, activation.SOURCE), {})
        row = next(r for r in rows if r["kind"])
        row["id_source"]["binding_sha256"] = "f" * 64
        row["kind_source"]["owner_binding_sha256"] = "f" * 64
        self.assertEqual(checked_context(rows, contract, activation.SOURCE), {})
        rows, contract = fixture()
        rows[0]["id"] = 99999
        self.assertEqual(checked_context(rows, contract, activation.SOURCE), {})
