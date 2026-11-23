"""Source-bound item aura selectors and their separate base-level ranges."""
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path

SOURCE = "2c248a580810fbe389d2f15fcf809f2dac51d5815c60e888353071fe7dfc57fe"
REFERENCE = Path(__file__).with_name("native-item-aura-slots-26297349.json")
REFERENCE_SHA256 = "6a4fe14f6e18e09a34d22f2948987c1e070bfae38410e116a0ecca6c53a662b1"
PROFILE = "hero-siege-26297349-item-grant-slots-v2"


def certificate():
    raw = REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError("The reviewed item aura-slot certificate changed")
    return json.loads(raw)


def verify(source_sha256, read):
    if source_sha256 != SOURCE:
        return None
    proof = certificate()
    if proof["profile"] != PROFILE or proof["source_sha256"] != source_sha256:
        raise ValueError("Item aura-slot source identity differs")
    for span in proof["spans"]:
        size = span["end_rva"] - span["start_rva"]
        raw = read(span["start_rva"], size)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != span["sha256"]:
            raise ValueError("Item aura-slot native transport changed: " + span["name"])
    for box in proof["numeric_boxes"]:
        raw = read(box["rva"], 16)
        if len(raw) != 16 or int.from_bytes(raw[:8], "little", signed=True) != box["value"] or int.from_bytes(raw[12:], "little") != 10:
            raise ValueError("Item aura-slot selector changed")
    return {"profile": PROFILE, "source_sha256": source_sha256,
            "certificate_sha256": REFERENCE_SHA256, "slots": proof["slots"],
            "skill_slots": proof["skill_slots"]}


def discover(executable, source_sha256):
    if source_sha256 != SOURCE:
        return None
    raw = Path(executable).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE:
        raise ValueError("Item aura-slot executable changed during generation")
    pe = struct.unpack_from("<I", raw, 0x3c)[0]
    optional_size = struct.unpack_from("<H", raw, pe + 20)[0]
    sections = [struct.unpack_from("<IIII", raw, pe + 24 + optional_size + 40 * n + 8)
                for n in range(struct.unpack_from("<H", raw, pe + 6)[0])]

    def read(rva, size):
        for _, start, length, offset in sections:
            if start <= rva and rva + size <= start + length:
                return raw[offset + rva - start:offset + rva - start + size]
        return b""

    return verify(source_sha256, read)


@lru_cache(maxsize=1)
def expected_slots():
    proof = certificate()
    return json.dumps({key: proof[key] for key in ("slots", "skill_slots")}, sort_keys=True)


def valid_domain(value, source_sha256):
    return (isinstance(value, dict) and source_sha256 == SOURCE
            and value.get("profile") == PROFILE and value.get("source_sha256") == SOURCE
            and value.get("certificate_sha256") == REFERENCE_SHA256
            and {key: value.get(key) for key in ("slots", "skill_slots")} == json.loads(expected_slots()))


def native_call(line):
    """Unwrap the one explicit envelope used for an unnamed decoded stat."""
    source = line.get("source") or {}
    if source.get("file") != "Hero_Siege.exe" or type(source.get("rva")) is not int or source["rva"] <= 0:
        return None
    raw = line.get("argument_interpretation", line.get("raw"))
    if not isinstance(raw, dict):
        return None
    if "args" not in raw:
        if raw.get("id") != line.get("id") or raw.get("source") != source or raw.get("status") != "decoded":
            return None
        raw = raw.get("raw")
    if not isinstance(raw, dict) or raw.get("rva") != source["rva"]:
        return None
    return raw


def level_range(line, stat_id):
    """Read only an actual scalar or complete two-endpoint native operand."""
    if line.get("status") != "decoded" or line.get("id") != stat_id:
        return None
    raw = native_call(line)
    args = (raw or {}).get("args") or []
    if len(args) != 2 or args[0] != {"kind": "value", "value": {"kind": "int", "value": stat_id}}:
        return None
    value = args[1]
    if not isinstance(value, dict):
        return None
    if value.get("kind") == "list":
        operands = value.get("value")
        if not isinstance(operands, list) or len(operands) != 2:
            return None
    elif value.get("kind") == "value":
        operands = [value.get("value")] * 2
    else:
        return None
    result = []
    for operand in operands:
        if not isinstance(operand, dict) or operand.get("kind") not in ("int", "real"):
            return None
        number = operand.get("value")
        if type(number) not in (int, float) or not math.isfinite(number) or number < 0 or int(number) != number:
            return None
        result.append(int(number))
    return result if result[0] <= result[1] else None


def skill_levels(line, stat_id):
    """Read complete source operands, retaining relic ranks rather than their extrema."""
    levels = level_range(line, stat_id)
    if levels is not None:
        return {"levels": levels}
    raw = native_call(line)
    args = (raw or {}).get("args") or []
    if (line.get("status") != "decoded" or line.get("id") != stat_id or len(args) != 2
            or args[0] != {"kind": "value", "value": {"kind": "int", "value": stat_id}}
            or args[1].get("kind") != "list"):
        return None
    operands = args[1].get("value")
    if not isinstance(operands, list) or len(operands) != 10:
        return None
    values = []
    for operand in operands:
        if not isinstance(operand, dict) or operand.get("kind") not in ("int", "real"):
            return None
        value = operand.get("value")
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or int(value) != value:
            return None
        values.append(int(value))
    return {"levels": None, "level_values": values}
