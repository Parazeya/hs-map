import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import talent_activation as activation
import talent_type_inheritance as inheritance
from test_talent_activation import fixture as observed_fixture, checked_context


def fixture():
    rows, observed = observed_fixture()
    folder = Path(__file__).resolve().parent / "fixtures"
    contract = json.loads((folder / "native-talent-type-inheritance-26297349.json").read_text(encoding="utf-8"))
    base = json.loads((folder / "native-talent-type-inheritance-context-26297349.json").read_text(encoding="utf-8"))
    records = {(r["key"], r["class"]): r for r in contract["record_sources"]}
    for row in rows:
        record = records.get((row["key"], row["class"]))
        if record:
            row["kind"] = "passive"
            row["kind_source"] = {"inheritance": record, "owner_binding_sha256": row["id_source"]["binding_sha256"],
                                  "raw_field": "abilityType", "aura_override_applied": False, "final_runtime_activity_certified": False}
    return rows, observed, contract, base, [copy.deepcopy(inheritance.DATA), copy.deepcopy(inheritance.DLL)]


class InheritedActivationTests(unittest.TestCase):
    def test_all_817_activation_names_keep_388_raw_fields_absent(self):
        rows, observed, contract, base, inventory = fixture()
        facts = checked_context(rows, observed, activation.SOURCE, contract, base, inventory)
        self.assertEqual(len(facts), 817)
        self.assertEqual(sum(f["label"] == "active" for f in facts.values()), 414)
        self.assertEqual(sum(f["label"] == "passive" for f in facts.values()), 403)
        weapon = next(row for row in rows if (row["key"], row["class"]) == ("weaponMaster", "Viking"))
        self.assertEqual(facts[("weaponMaster", "Viking")]["label"], "passive")
        self.assertNotIn("abilityType", weapon["raw_fields"])

    def test_touched_field_broken_case_or_missing_runtime_inputs_cannot_inherit(self):
        for mutate in (
                lambda rows, c, b, inv: b["case_rows"][0]["receiver_fields"].append("abilityType"),
                lambda rows, c, b, inv: b["case_rows"][0].update(callee_nonmutation_certified=False),
                lambda rows, c, b, inv: b["case_rows"][0].update(normal_case_CFG_complete=False),
                lambda rows, c, b, inv: b.pop("runtime_contract"),
                lambda rows, c, b, inv: inv.pop(),
                lambda rows, c, b, inv: inv[0].update(sha256="a" * 64)):
            rows, observed, contract, base, inventory = fixture()
            mutate(rows, contract, base, inventory)
            self.assertEqual(checked_context(rows, observed, activation.SOURCE, contract, base, inventory), {})

    def test_inferred_defaults_owner_aliases_or_aura_runtime_claims_are_blocked(self):
        for mutate in (
                lambda rows, c: next(r for r in rows if "inheritance" in r["kind_source"])["raw_fields"].update(abilityType={"kind": "value", "value": {"kind": "int", "value": 1}}),
                lambda rows, c: next(r for r in rows if "inheritance" in r["kind_source"])["kind_source"].update(owner_binding_sha256="a" * 64),
                lambda rows, c: next(r for r in rows if "inheritance" in r["kind_source"])["kind_source"].update(aura_override_applied=True),
                lambda rows, c: c.update(final_runtime_activity_certified=True),
                lambda rows, c: c["record_sources"][0]["typed_value"].update(value=0)):
            rows, observed, contract, base, inventory = fixture()
            mutate(rows, contract)
            self.assertEqual(checked_context(rows, observed, activation.SOURCE, contract, base, inventory), {})
        rows, observed, _, base, inventory = fixture()
        self.assertEqual(checked_context(rows, observed, activation.SOURCE, None, base, inventory), {})

    def test_constructor_owner_cannot_be_self_recertified(self):
        rows, observed, contract, base, inventory = fixture()
        row = next(r for r in rows if "inheritance" in r["kind_source"])
        row["id_source"]["binding_sha256"] = "f" * 64
        row["kind_source"]["owner_binding_sha256"] = "f" * 64
        self.assertEqual(checked_context(rows, observed, activation.SOURCE, contract, base, inventory), {})
