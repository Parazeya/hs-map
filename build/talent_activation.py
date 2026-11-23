"""Validate finite native activation names without inferring missing fields."""
import hashlib
import json
import math

SOURCE = "2c248a580810fbe389d2f15fcf809f2dac51d5815c60e888353071fe7dfc57fe"
PROFILE = "hero-siege-26297349-ability-type-v1"
WITNESS = "04c7f9296a8710f2f6340982666ee5f795dd50590e22c40cc9246f2aa48e3cba"
CONTRACT = "7fb8b5fc0aaa98f152a93ed0f888befaa5fa4641fcced25240546e182ee9488c"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def raw_code(arg):
    if not isinstance(arg, dict) or arg.get("kind") != "value":
        return None
    value = arg.get("value")
    if not isinstance(value, dict) or value.get("kind") not in ("int", "real"):
        return None
    number = value.get("value")
    return number if type(number) in (int, float) and math.isfinite(number) and number in (0, 1) else None


def context(rows, contract, source_sha256, inheritance_contract=None, defaults_contract=None, inventory=None, native_id_contract=None):
    """Return only source-verified activation facts; categories stay separate."""
    if not isinstance(rows, list) or not isinstance(contract, dict) or source_sha256 != SOURCE:
        return {}
    import talent_identity
    if not talent_identity.valid(rows, native_id_contract, source_sha256):
        return {}
    import talent_type_inheritance
    inherited = talent_type_inheritance.context(rows, inheritance_contract, defaults_contract, inventory, native_id_contract)
    if inherited is None:
        return {}
    proof = contract.get("proof") or {}
    records = contract.get("record_sources")
    if (contract.get("profile") != PROFILE or contract.get("source_sha256") != SOURCE
            or type(contract.get("schema_version")) is not int or contract["schema_version"] != 1
            or contract.get("source") != "Hero_Siege.exe"
            or contract.get("status") != "complete_source_bound_finite_ability_type_names"
            or contract.get("scope") != "observed_raw_abilityType_enum"
            or contract.get("aura_overrides_display_label") is not True
            or contract.get("final_runtime_activity_certified") is not False
            or any(contract.get(field) is not False for field in (
                "raw_fields_rewritten", "missing_type_inferred", "unknown_codes_named",
                "aura_override_applied", "whole_native_enum_certified"))
            or type(contract.get("records")) is not int or contract["records"] != 429
            or type(contract.get("without_explicit_type")) is not int or contract["without_explicit_type"] != 388
            or contract.get("native_value_counts") != {"0": 414, "1": 15}
            or not isinstance(proof, dict)
            or proof.get("reference") != "reference/native-evidence/talent-type-26297349.json"
            or proof.get("sha256") != WITNESS or contract.get("native_contract_id") != CONTRACT
            or not isinstance(records, list) or len(records) != 429 or len(rows) != 817):
        return {}
    try:
        if digest({"profile": PROFILE, "source_sha256": SOURCE, "witness_sha256": WITNESS,
                   "record_sources": records}) != CONTRACT:
            return {}
        by_name = {}
        for record in records:
            if not isinstance(record, dict):
                return {}
            name = (record.get("key"), record.get("class"))
            code = record.get("code")
            sites = record.get("writer_rvas")
            if (type(code) is not int or code not in (0, 1) or name in by_name
                    or not isinstance(name[0], str) or not name[0] or not isinstance(name[1], str)
                    or record.get("source") != "Hero_Siege.exe" or record.get("source_sha256") != SOURCE
                    or record.get("scope") != "observed_raw_abilityType_enum"
                    or record.get("label") != ("active", "passive")[code]
                    or not isinstance(sites, list) or not sites or any(type(at) is not int or at <= 0 for at in sites)
                    or record.get("binding_sha256") != digest({k: v for k, v in record.items() if k != "binding_sha256"})):
                return {}
            by_name[name] = record
        facts, seen = {}, set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("raw_fields"), dict):
                return {}
            name = (row.get("key"), row.get("class"))
            if name in seen:
                return {}
            seen.add(name)
            record, raw_fields = by_name.get(name), row.get("raw_fields") or {}
            if record is None:
                if name in inherited:
                    facts[name] = inherited[name]
                    continue
                if "abilityType" in raw_fields or row.get("kind") is not None or "kind_source" in row:
                    return {}
                continue
            raw = raw_fields.get("abilityType")
            identity = row.get("id_source")
            if not isinstance(identity, dict):
                return {}
            owner = identity.get("binding_sha256")
            expected = {"native_contract_id": CONTRACT, "value": record, "raw_field": "abilityType",
                        "raw_value": raw, "owner_binding_sha256": owner,
                        "aura_override_applied": False, "final_runtime_activity_certified": False}
            if (raw_code(raw) != record["code"] or row.get("kind") != record["label"]
                    or not isinstance(owner, str) or len(owner) != 64 or row.get("kind_source") != expected):
                return {}
            facts[name] = {"label": record["label"], "source": row["kind_source"]}
        return facts if len(facts) == 429 + len(inherited) else {}
    except (TypeError, ValueError, KeyError):
        return {}
