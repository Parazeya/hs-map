"""Source-bound item trigger and display metadata, separate from raw operands."""
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
import item_grant_slots

SOURCE = item_grant_slots.SOURCE
PROFILE = 'hero-siege-26297349-item-effects-v1'
DATA_WIN = '7d66e5b5f579f349f63e46e0608c27d1f9a8c9260091036a9de4a872869a490a'
REFERENCE = Path(__file__).with_name('native-item-effects-26297349.json')
REFERENCE_SHA256 = '25bb7fa6c23379ee6a0ef798db63baf72af93708e9d9d4625e0fdbcd190b72bd'

def certificate():
    raw = REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Reviewed item-effect certificate changed')
    return json.loads(raw)

def verify(source_sha256, read, data_win_sha256):
    if source_sha256 != SOURCE or data_win_sha256 != DATA_WIN:
        return None
    proof = certificate()
    if proof['profile'] != PROFILE or proof['source_sha256'] != SOURCE or proof['data_win_sha256']!=DATA_WIN:
        raise ValueError('Item-effect source differs')
    for row in proof['spans']:
        raw = read(row['start_rva'], row['end_rva']-row['start_rva'])
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Item-effect native transport changed: '+row['name'])
    for row in proof['numeric_boxes']:
        raw = read(row['rva'],16)
        if len(raw)!=16 or int.from_bytes(raw[:8],'little',signed=True)!=row['value'] or int.from_bytes(raw[12:],'little')!=10:
            raise ValueError('Item-effect stat selector changed')
    return dict(profile=PROFILE,source_sha256=SOURCE,data_win_sha256=DATA_WIN,certificate_sha256=REFERENCE_SHA256,settings=proof['settings'])

def discover(executable, source_sha256, data_win_sha256):
    if source_sha256 != SOURCE or data_win_sha256 != DATA_WIN:
        return None
    raw = Path(executable).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE:
        raise ValueError('Item-effect executable changed during generation')
    pe=struct.unpack_from('<I',raw,0x3c)[0]
    sections=[struct.unpack_from('<IIII',raw,pe+24+struct.unpack_from('<H',raw,pe+20)[0]+40*n+8)
              for n in range(struct.unpack_from('<H',raw,pe+6)[0])]
    def read(at,size):
        for _,start,length,offset in sections:
            if start<=at and at+size<=start+length:
                return raw[offset+at-start:offset+at-start+size]
        return b''
    return verify(source_sha256,read,data_win_sha256)

@lru_cache(maxsize=1)
def expected_settings():
    return json.dumps(certificate()['settings'],sort_keys=True)

def valid_domain(domain, source_sha256):
    return (isinstance(domain,dict) and source_sha256==SOURCE and domain.get('profile')==PROFILE
            and domain.get('source_sha256')==SOURCE and domain.get('certificate_sha256')==REFERENCE_SHA256
            and domain.get('data_win_sha256')==DATA_WIN
            and domain.get('settings')==json.loads(expected_settings()))

def quantity(line, stat_id, integral=False, ceiling=None):
    if line.get('status')!='decoded' or line.get('id')!=stat_id:
        return None
    raw=item_grant_slots.native_call(line)
    args=(raw or {}).get('args') or []
    if len(args)!=2 or args[0]!={'kind':'value','value':{'kind':'int','value':stat_id}} or not isinstance(args[1],dict):
        return None
    value=args[1]
    if value.get('kind')=='value':
        operands=[value.get('value')]*2
    elif value.get('kind')=='list' and isinstance(value.get('value'),list) and len(value['value']) in (2,10):
        operands=value['value']
    else:
        return None
    values=[]
    for operand in operands:
        if not isinstance(operand,dict) or operand.get('kind') not in ('int','real'):
            return None
        number=operand.get('value')
        if (type(number) not in (int,float) or not math.isfinite(number) or number<0
                or (ceiling is not None and number>ceiling) or (integral and number!=int(number))):
            return None
        values.append(int(number) if number==int(number) else number)
    if len(values)==2:
        return {'range':values} if values[0]<=values[1] else None
    return {'values':values}
