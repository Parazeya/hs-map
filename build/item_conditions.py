"""Source-bound conditional stores, kept separate for each native outer key."""
import copy
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
from data_bundle import field_is_current
from item_effects import SOURCE, DATA_WIN

PROFILE='hero-siege-26297349-item-conditions-v1'
REFERENCE=Path(__file__).with_name('native-item-conditions-26297349.json')
REFERENCE_SHA256='4b9e801306a4c7dca7f9b38a0acded43a889f4f93667771de71bf865d469097c'
DOMAINS={'socket':'itemBaseSocketStatStruct.outer_key',
         'damage_type':'itemBaseDamageTypeStatStruct.outer_key'}

def certificate():
    raw=REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=REFERENCE_SHA256:
        raise ValueError('Reviewed item-condition certificate changed')
    return json.loads(raw)

def verify(source_sha256,data_win_sha256,read):
    if source_sha256!=SOURCE or data_win_sha256!=DATA_WIN:
        return None
    proof=certificate()
    if proof['profile']!=PROFILE or proof['source_sha256']!=SOURCE or proof['data_win_sha256']!=DATA_WIN:
        raise ValueError('Item-condition source differs')
    for row in proof['spans']:
        raw=read(row['start_rva'],row['end_rva']-row['start_rva'])
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Item-condition native transport changed: '+row['name'])
    return dict(profile=PROFILE,source_sha256=SOURCE,data_win_sha256=DATA_WIN,
                certificate_sha256=REFERENCE_SHA256,settings=proof['settings'])

def discover(executable,source_sha256,data_win_sha256):
    if source_sha256!=SOURCE or data_win_sha256!=DATA_WIN:
        return None
    raw=Path(executable).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE:
        raise ValueError('Item-condition executable changed during generation')
    pe=struct.unpack_from('<I',raw,0x3c)[0]
    sections=[struct.unpack_from('<IIII',raw,pe+24+struct.unpack_from('<H',raw,pe+20)[0]+40*n+8)
              for n in range(struct.unpack_from('<H',raw,pe+6)[0])]
    def read(at,size):
        for _,start,length,offset in sections:
            if start<=at and at+size<=start+length:
                return raw[offset+at-start:offset+at-start+size]
        return b''
    return verify(source_sha256,data_win_sha256,read)

@lru_cache(maxsize=1)
def expected_settings():
    return json.dumps(certificate()['settings'],sort_keys=True)

def valid_domain(domain):
    return (isinstance(domain,dict) and domain.get('profile')==PROFILE
            and domain.get('source_sha256')==SOURCE and domain.get('data_win_sha256')==DATA_WIN
            and domain.get('certificate_sha256')==REFERENCE_SHA256
            and domain.get('settings')==json.loads(expected_settings()))

def socket_catalogue(raw_items,said,domain):
    if not valid_domain(domain):
        return {}
    found={}
    for row in raw_items:
        meta=row.get('metadata') or {}
        identity=meta.get('ID')
        if (not field_is_current(row,'ID') or not isinstance(identity,list) or len(identity)!=3
                or any(type(n) is not int for n in identity) or identity[2]!=domain['settings']['socket_item_type']
                or identity[0]<0 or not meta.get('tkey')):
            continue
        key=meta['tkey']
        names=said(key) or ({'en':meta['name']} if meta.get('name') else None)
        if names:
            found.setdefault(identity[0],{})[key]=dict(item_key=key,names=names,record_id=meta.get('record_id'))
    # A duplicate numeric key with distinct named definitions is ambiguous.
    return {number:next(iter(entries.values())) for number,entries in found.items() if len(entries)==1}

def selector_value(outer,channel):
    if not isinstance(outer,dict) or outer.get('domain')!=DOMAINS.get(channel) or outer.get('argument_index')!=0:
        return None
    observed=outer.get('observed')
    if not isinstance(observed,dict) or observed.get('kind')!='value':
        return None
    value=observed.get('value')
    if not isinstance(value,dict) or value.get('kind') not in ('int','real'):
        return None
    n=value.get('value')
    if type(n) not in (int,float) or not math.isfinite(n) or n<0 or int(n)!=n:
        return None
    return int(n)

def partition(rows,channel):
    """Grouping is structural even when a new source cannot name its selectors."""
    groups={}
    for row in rows:
        outer=row.get('outer_selector')
        key=json.dumps(outer,sort_keys=True,separators=(',',':'))
        if key not in groups:
            value=selector_value(outer,channel)
            suffix=str(value) if value is not None else 'unresolved-'+hashlib.sha256(key.encode()).hexdigest()[:16]
            groups[key]=dict(id=channel+':'+suffix,selector=value,outer_selector=copy.deepcopy(outer),stats=[])
        groups[key]['stats'].append(row)
    # Different typed keys with equal numbers must still never collapse or collide.
    collisions={}
    for group in groups.values():
        collisions[group['id']]=collisions.get(group['id'],0)+1
    for key,group in groups.items():
        if collisions[group['id']]>1:
            group['id']+=':'+hashlib.sha256(key.encode()).hexdigest()[:12]
    return list(groups.values())

def describe(group,channel,item_key,catalogue,said,domain):
    result=dict(id=group['id'],kind=channel,selector=group['selector'],resolved=False)
    if not valid_domain(domain) or group['selector'] is None:
        return result
    if channel=='socket':
        binding=catalogue.get(group['selector'])
        if binding:
            result.update(copy.deepcopy(binding),resolved=True,per_socket=True,selection='each_matching_socket')
    elif channel=='damage_type':
        entry=domain['settings']['damage_groups'].get(item_key,{}).get(str(group['selector']))
        signature=sorted(row.get('id') for row in group['stats'] if type(row.get('id')) is int)
        if entry and signature==entry['stat_ids']:
            names=said(entry['label_key'])
            if names:
                result.update(names=names,resolved=True,selection='one_generated_variant')
    if result['resolved']:
        result['provenance']=dict(kind='decoded' if channel=='socket' else 'derived',
            basis='native socketable item ID' if channel=='socket' else 'unambiguous current native stat-family signature',
            source_sha256=SOURCE,certificate_sha256=REFERENCE_SHA256)
    return result
