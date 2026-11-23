"""Field-specific constructor evidence for an absent raw abilityType."""
import hashlib
import json

SOURCE = "2c248a580810fbe389d2f15fcf809f2dac51d5815c60e888353071fe7dfc57fe"
PROFILE = "hero-siege-26297349-constructor-ability-type-v1"
WITNESS = "34d08b19819ffdf73c553a8b2a9a48e9f24b4b37f04cdb5642a95827a75f2a50"
CONTRACT = "d12bbc3d6dee2d91851331c1d4c6f0c6eec82ba92ac011713db5c1866d491795"
CATALOG = "afd63a4d941efc873e0ab6759fb4021dd63f4455bb48cbdc173eab89668162a9"
RELATIVE = "cfe0bfcb4264a010fde0007e554eee4f195b14aa3054317fcd8a748af5fbaeac"
DLL = {"path": "ac_dll_gm.dll", "size": 15360, "sha256": "ea33261a54ba922b4074ae211990087c3a74fa840ead44ab30f0c74e504c505a"}
DATA = {"path": "data.win", "size": 763181620, "sha256": "7d66e5b5f579f349f63e46e0608c27d1f9a8c9260091036a9de4a872869a490a"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def context(rows, contract, base, inventory, native_id_contract=None):
    """None means absent/invalid support; callers may not infer a default."""
    if not isinstance(rows, list) or any(not isinstance(row, dict) or
            row.get("kind_source") is not None and not isinstance(row["kind_source"], dict) for row in rows):
        return None
    if contract is None:
        return {} if not any((row.get("kind_source") or {}).get("inheritance") for row in rows) else None
    import talent_identity
    if not talent_identity.valid(rows, native_id_contract, SOURCE):
        return None
    if not isinstance(contract, dict) or not isinstance(base, dict) or not isinstance(inventory, list):
        return None
    proof, runtime = contract.get("proof") or {}, base.get("runtime_contract") or {}
    records = contract.get("record_sources")
    if (contract.get("schema_version") != 1 or contract.get("profile") != PROFILE
            or contract.get("source_sha256") != SOURCE or contract.get("status") != "complete_source_bound_constructor_type_inheritance"
            or contract.get("scope") != "constructor_inherited_abilityType_enum" or contract.get("native_contract_id") != CONTRACT
            or contract.get("relative_receiver_contract_id") != RELATIVE or contract.get("catalog_sha256") != CATALOG
            or proof != {"reference": "reference/native-evidence/talent-type-inheritance-26297349.json", "sha256": WITNESS}
            or contract.get("records") != 388 or not isinstance(records, list) or len(records) != 388
            or contract.get("raw_fields_rewritten") is not False or contract.get("aura_override_applied") is not False
            or contract.get("final_runtime_activity_certified") is not False or contract.get("existing_effect_diagnostics_unchanged") is not True
            or base.get("source_sha256") != SOURCE or base.get("native_contract_id") != RELATIVE
            or not isinstance(runtime, dict) or runtime.get("status") != "source_bound_relative_receiver_contracts"
            or runtime.get("source_sha256") != SOURCE or digest(runtime) != RELATIVE
            or next((r for r in inventory if r.get("path") == DLL["path"]), None) != DLL
            or next((r for r in inventory if r.get("path") == DATA["path"]), None) != DATA):
        return None
    try:
        if digest({"profile": PROFILE, "source_sha256": SOURCE, "native_contract_id": CONTRACT, "record_sources": records}) != CATALOG:
            return None
        by_name = {}
        for record in records:
            name = (record["key"], record["class"])
            if name in by_name or record["binding_sha256"] != digest({k: v for k, v in record.items() if k != "binding_sha256"}):
                return None
            by_name[name] = record
        cases = {(r["key"], r["class"]): r for r in base.get("case_rows", [])}
        facts = {}
        for row in rows:
            name = (row["key"], row["class"])
            record = by_name.get(name)
            if record is None:
                if (row.get("kind_source") or {}).get("inheritance"):
                    return None
                continue
            p, owner, case = record["proof"], row.get("id_source") or {}, cases.get(name)
            binding, scpt = runtime.get("constructor_registration") or {}, p.get("SCPT_binding") or {}
            if (not isinstance(case, dict) or "abilityType" in (row.get("raw_fields") or {})
                    or record.get("status") != "proven_constructor_type_inheritance" or record.get("scope") != "constructor_inherited_abilityType_enum"
                    or record.get("field") != "abilityType" or type(record.get("code")) is not int or record["code"] != 1
                    or record.get("label") != "passive" or record.get("typed_value") != {"kind": "int", "value": 1}
                    or any(record.get(k) is not False for k in ("raw_field_present", "raw_fields_rewritten", "aura_override_applied", "final_runtime_activity_certified"))
                    or record.get("source") != "Hero_Siege.exe" or record.get("source_sha256") != SOURCE
                    or p.get("native_contract_id") != CONTRACT or p.get("relative_receiver_contract_id") != RELATIVE
                    or any(p.get(k) is not True for k in ("normal_case_CFG_complete", "constructor_receiver_bound", "receiver_writes_certified", "callee_nonmutation_certified", "constructor_initialization_certified", "final_field_not_overwritten"))
                    or any(case.get(k) is not True for k in ("normal_case_CFG_complete", "constructor_receiver_bound", "receiver_writes_certified", "callee_nonmutation_certified"))
                    or case.get("unknown_edges") or case.get("receiver_write_errors")
                    or "abilityType" in (case.get("observed_fields") or []) or "abilityType" in (case.get("receiver_fields") or [])
                    or "abilityType" in (case.get("field_write_rvas") or {})
                    or any(p.get(k) != case.get(k) or p.get(k) != owner.get(other) for k, other in (
                        ("case_entry", "case_entry_rva"), ("key_anchor", "key_anchor_rva"), ("record_end", "record_end_rva")))
                    or p.get("input_sources") != [{"relative_path": DLL["path"], "size": DLL["size"], "sha256": DLL["sha256"]}]
                    or any(scpt.get(k) != binding.get(other) for k, other in (
                        ("index", "SCPT_index"), ("name", "SCPT_name"), ("code_raw", "SCPT_code_raw"),
                        ("record_offset", "SCPT_record_offset"), ("script_id", "script_id"), ("slot_rva", "script_id_slot_rva")))
                    or p.get("reviewed_normal_initialization_assumption") != runtime.get("reviewed_normal_initialization_assumption")):
                return None
            expected = {"inheritance": record, "owner_binding_sha256": owner.get("binding_sha256"), "raw_field": "abilityType",
                        "aura_override_applied": False, "final_runtime_activity_certified": False}
            if row.get("kind") != "passive" or row.get("kind_source") != expected:
                return None
            facts[name] = {"label": "passive", "source": expected}
        return facts if len(facts) == 388 else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
