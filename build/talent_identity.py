"""Exact native-ID catalog prerequisite for consumers of named talent facts."""
import hashlib
import json

SOURCE = "2c248a580810fbe389d2f15fcf809f2dac51d5815c60e888353071fe7dfc57fe"
PROFILE = "hero-siege-26297349-native-talent-map-keys-v1"
WITNESS = "26668afafd26aa2596d8c66c8549aaa1ff54e20b5c6f2396a67b6fc6266ec911"
CONTRACT = "e5ab15dcb1d906145c0613d0739a8551c44abd46a86056ba83b24ef67053223a"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def valid(rows, contract, source_sha256):
    if not isinstance(rows, list) or len(rows) != 817 or not isinstance(contract, dict) or source_sha256 != SOURCE:
        return False
    witness = contract.get("witness") or {}
    catalog = contract.get("record_sources")
    if (type(contract.get("schema_version")) is not int or contract["schema_version"] != 1 or contract.get("profile") != PROFILE
            or contract.get("source") != "Hero_Siege.exe" or contract.get("source_sha256") != SOURCE
            or type(contract.get("source_size")) is not int or contract["source_size"] != 281605632
            or type(contract.get("records")) is not int or contract["records"] != 817
            or contract.get("status") != "complete_source_bound_native_insertion_keys"
            or contract.get("native_numeric_map_keys_certified") is not True
            or contract.get("final_runtime_map_contents_certified") is not False or contract.get("ordinal_fallback") is not False
            or contract.get("current_emitted_ids_used_as_proof") is not False or not isinstance(witness, dict)
            or contract.get("method") != "explicit_native_case_payload_to_dispatch_label_to_named_fresh_object_to_ds_map_set_key"
            or contract.get("consumer") != {"script": "GetTalentInfo", "map_variable": "talentStructMap", "routine": "ds_map_find_value",
                                            "call_rva": 63909389, "lookup_key": "unrenumbered_first_script_argument"}
            or witness.get("path") != "reference/native-evidence/talent-native-map-keys-26297349.json"
            or witness.get("sha256") != WITNESS or contract.get("native_contract_id") != CONTRACT
            or not isinstance(catalog, list) or len(catalog) != 817):
        return False
    try:
        if digest({"profile": PROFILE, "source_sha256": SOURCE, "witness_sha256": WITNESS, "record_sources": catalog}) != CONTRACT:
            return False
        by_name = {(record["key"], record["class"]): record for record in catalog}
        if len(by_name) != 817:
            return False
        seen, ids = set(), set()
        for row in rows:
            name = (row["key"], row["class"])
            proof = by_name.get(name)
            if (name in seen or type(row.get("id")) is not int or row["id"] in ids or proof is None
                    or row["id"] != proof["native_id"] or row.get("id_source") != proof):
                return False
            seen.add(name)
            ids.add(row["id"])
        return len(seen) == 817
    except (TypeError, KeyError, ValueError):
        return False
