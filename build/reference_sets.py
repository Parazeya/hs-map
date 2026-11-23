"""Restore published set relationships without replacing current item facts."""
import copy
import hashlib
import json
from pathlib import Path

CATALOGUE = Path(__file__).with_name('reference') / 'published-item-sets-20261120.json'


def catalogue():
    raw = CATALOGUE.read_bytes()
    data = json.loads(raw)
    if data.get('schema_version') != 1 or data.get('reference', {}).get('verified_for_game_build') is not False:
        raise ValueError('Set catalogue must remain reference data')
    members = data.get('memberships', {})
    seen = set()
    for name, kit in data.get('sets', {}).items():
        for key in kit.get('of', []):
            if key in seen or members.get(key, {}).get('set') != name:
                raise ValueError('Ambiguous published set member: ' + key)
            seen.add(key)
    if seen != set(members):
        raise ValueError('Published set membership is incomplete')
    data['reference']['catalogue_sha256'] = hashlib.sha256(raw).hexdigest()
    return data


def merge(items, kits, reference, names=None):
    """Exact item keys and compatible types/rarities only; native ownership wins."""
    names = names or {}
    added, skipped = [], []
    applied = {}
    for key, member in reference['memberships'].items():
        family = items.get(key)
        matched = False
        for record in [family, *(family or {}).get('variants', [])] if family else []:
            # A family may also contain an ordinary base with the same key.
            # A missing rarity can retain reference membership, never a new rarity.
            if record.get('set') or record.get('rarity') not in (None, 'Satanic Set'):
                continue
            if not member.get('type') or record.get('type') != member['type']:
                continue
            name = member['set']
            record['set'] = name
            record['reference_set'] = copy.deepcopy(reference['reference'])
            if 'set membership' not in record.setdefault('reference', []):
                record['reference'].append('set membership')
            added.append({'key': key, 'record_id': record.get('record_id'), 'set': name})
            matched = True
        if matched:
            applied.setdefault(member['set'], []).append(key)
        else:
            skipped.append(key)
    for name, members in applied.items():
        snapshot = reference['sets'][name]
        if name not in kits:
            kits[name] = {field: copy.deepcopy(snapshot[field]) for field in ('names', 'bonuses') if field in snapshot}
            kits[name]['of'] = []
            if names.get(name):
                kits[name]['names'] = copy.deepcopy(names[name])
            kits[name]['provenance'] = {'membership': copy.deepcopy(reference['reference']),
                                       'bonuses': copy.deepcopy(reference['reference'])}
        kit = kits[name]
        kit['of'] = sorted(set(kit.get('of', []) + members))
    return {'restored_records': len(added), 'restored_sets': len(applied),
            'records': added, 'skipped_members': skipped,
            'reference': copy.deepcopy(reference['reference'])}
