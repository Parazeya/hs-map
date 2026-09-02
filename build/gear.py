"""What the game states about an item that its own tables do not spell out.

The datamined item tables give a stat's key and its range and nothing else, so
`35–65 Magic Skill Damage` is as much as the codex could say — while the game
says `Magic Skill Damage increased by 43% [35-65]`, and between a flat 43 and
43% lies the whole difference between a good item and a useless one. The same
tables say nothing about how many sockets an item rolls, what a set gives for
wearing more of it, or which skill an item grants.

HSPlanner has read the tooltips (github.com/HeroSiegePlanner/HSPlanner, MIT,
Copyright (c) 2026 zium; vendored under `planner/gear/`), and its lines are
written out the way the game writes them — `+[25-50]% Enhanced Defense`. So the
unit is not inferred from a stat's name or guessed from its size: it is read
off a line the game wrote about that stat.

Its items are joined to ours by name, which binds 1233 of the 1252 it carries.
"""

import glob
import json
import re
from collections import Counter, defaultdict

#: A value with a per-cent sign after it, which is the line saying so.
PCT = re.compile(r'(\[[-\d]+(?:-\d+)?\]|-?\d+(?:\.\d+)?)\s*%')

#: A value, however it is written. Used to count them, not to read them.
VALUE = re.compile(r'\[[-\d]+(?:-\d+)?\]|(?<![\w.])-?\d+(?:\.\d+)?')


def flat(text):
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def read(folder):
    """The planner's gear tables."""
    out = {'items': [], 'sets': [], 'affixes': [], 'granted': [], 'stats': []}
    for path in sorted((folder / 'items').glob('*.json')):
        out['items'] += json.loads(path.read_text('utf-8'))
    for name in ('sets', 'affixes'):
        p = folder / f'{name}.json'
        if p.exists():
            out[name] = json.loads(p.read_text('utf-8'))
    p = folder / 'item-granted-skills.json'
    if p.exists():
        out['granted'] = json.loads(p.read_text('utf-8'))
    p = folder / 'game-config.json'
    if p.exists():
        out['stats'] = json.loads(p.read_text('utf-8')).get('stats') or []
    return out


def written(gear):
    """Every line that states one number about one thing, and which kind it is.

    A line naming a stat is only evidence about that stat if the number in it
    is the stat's own. `Enhanced Defense/Damage and +1 Affix` names two stats
    and counts affixes, and read as evidence it says Enhanced Defense is a flat
    number — which is how a shield's 450% came to be printed as 450.
    """
    lines = []
    for a in gear['affixes']:
        if a.get('description'):
            lines.append(a['description'])
    for kit in gear['sets']:
        for b in kit.get('bonuses') or []:
            lines += b.get('descriptions') or []
    out = []
    for line in lines:
        if 'affix' in line.lower() or len(VALUE.findall(line)) != 1:
            continue
        out.append((line.lower(), 'percent' if PCT.search(line) else 'flat'))
    return out


def paired(gear, vocab, items):
    """Our stat under the name the planner keeps it by, matched on the numbers.

    An item states the same stat on both sides with the same range — a shield
    is `450-600` here and `enhanced_defense: [450, 600]` there — so the pair
    can be read off the items themselves rather than off two spellings of a
    name. Ranges collide sometimes, which is why this is the last word tried
    and not the first.
    """
    by_sid = {}
    mine = {}
    for record in items.values():
        nm = (record.get('names') or {}).get('en')
        if nm:
            mine.setdefault(flat(nm), record)
    names = [v['sid'] for v in vocab]
    vote = defaultdict(Counter)
    for x in gear['items']:
        ours = mine.get(flat(x['name']))
        if not ours:
            continue
        at = {}
        for key, val in (x.get('implicit') or {}).items():
            span = (val[0], val[1]) if isinstance(val, list) else (val, None)
            at.setdefault(span, []).append(key)
            if not isinstance(val, list):
                at.setdefault((val, val), []).append(key)
        for st in ours.get('stats') or []:
            sid = st.get('sid')
            sid = names[sid] if isinstance(sid, int) else sid
            for key in at.get((st.get('min'), st.get('max')), []):
                vote[sid][key] += 1
    for sid, c in vote.items():
        top, n = c.most_common(1)[0]
        if n >= 0.6 * sum(c.values()):
            by_sid[sid] = top
    return by_sid


def units(gear, vocab, items, said):
    """Which of our stats are percentages.

    The game keeps a table of its stats and says of each whether it is written
    as a percentage — 507 of the 662 are. Ours are the same stats under other
    spellings, so the work is binding the two, and that is done in the order
    the answers can be trusted:

      the key itself, where the two spell it the same
      the name, plain and in the longer phrasing the game keeps beside it
      the numbers, which pair a stat to the one an item states alongside it

    Nothing later overrules something earlier: `stat_defense` and
    `enhanced_defense` sit on the same item with the same range often enough
    for the numbers to confuse them, and the name settles it first.
    """
    told = {}
    by_key, by_name = {}, {}
    for x in gear['stats']:
        by_key.setdefault(flat(x['key']), x['format'])
        by_name.setdefault(flat(x['name']), x['format'])

    for v in vocab:
        sid = v['sid']
        tries = [flat(sid), flat((v.get('names') or {}).get('en') or '')]
        for key in ({sid} if sid.startswith('stat_')
                    else {f'stat_{sid}', f'stat_{sid.rstrip("s")}'}):
            phrase = said(key)
            if phrase:
                tries.append(flat(phrase.get('en') or ''))
        for probe in tries:
            got = by_key.get(probe) or by_name.get(probe)
            if got:
                told[sid] = got
                break

    for sid, key in paired(gear, vocab, items).items():
        if sid not in told and flat(key) in by_key:
            told[sid] = by_key[flat(key)]

    # The table classifies a stat; the written lines show how it is printed,
    # and where every line that mentions a stat writes a per-cent sign, that is
    # what a reader sees. `mana_replenish` is filed flat and written
    # `Replenish Mana [20-50]%`, and the mask states 76% of it.
    lines = written(gear)
    seen = defaultdict(Counter)
    for v in vocab:
        want = flat((v.get('names') or {}).get('en') or '')
        if len(want) < 5:
            continue
        for text, kind in lines:
            if want in flat(text):
                seen[v['sid']][kind] += 1
    for sid, c in seen.items():
        if len(c) == 1 and sum(c.values()) >= 2:
            told[sid] = next(iter(c))
    return told


def by_name(gear):
    """Their items, under the name ours are known by."""
    out = {}
    for x in gear['items']:
        out.setdefault(flat(x['name']), x)
    return out


def sockets(gear, items):
    """How many sockets an item carries.

    The planner states the rolled pair; a range is what an item is worth saying
    about, and where the two agree it is a fixed number.
    """
    theirs = by_name(gear)
    n = 0
    for record in items.values():
        got = theirs.get(flat((record.get('names') or {}).get('en')))
        if not got or got.get('maxSockets') in (None, 0):
            continue
        lo, hi = got.get('sockets') or 0, got['maxSockets']
        record['sockets'] = [lo, hi] if lo != hi else [hi]
        n += 1
    return n


def grants(gear, items):
    """The skill an item grants, by name.

    The item tables name it by a number whose count runs behind the game's, and
    only where that difference is pinned can the number be read. The planner
    names it outright, which needs no pinning and covers the rest.
    """
    theirs = by_name(gear)
    out = {}
    for key, record in items.items():
        got = theirs.get(flat((record.get('names') or {}).get('en')))
        for name, level in ((got or {}).get('skillBonuses') or {}).items():
            out[key] = (name, level if isinstance(level, list) else [level])
    return out


#: The stats that say an item carries an aura rather than gives a number.
AURA = {"aura_self", "grant_aura", "grant_aura_holder_only"}


def auras(gear, items, vocab):
    """Mark the items that carry an aura, and take their class list away.

    An aura is not a stat the wearer keeps to themselves: it buffs whoever is
    standing near it, so an item that grants one is worn for the party and not
    for what its own damage type suits. In practice it goes on a mercenary as
    often as on the player, which is a thing to say and not a class to name.

    Two ways to tell: the item states one of the aura stats, or the skill it
    grants is one the planner has flagged as an aura.
    """
    named = {flat(x['name']) for x in gear['granted'] if x.get('aura')}
    n = 0
    for record in items.values():
        by_stat = any(vocab[s['sid']] in AURA if isinstance(s.get('sid'), int)
                      else s.get('sid') in AURA
                      for s in record.get('stats') or [])
        gives = ((record.get('grants') or {}).get('names') or {}).get('en')
        if by_stat or (gives and flat(gives) in named):
            record.pop('suits', None)
            record['aura'] = 1
            n += 1
    return n


def sets(gear, kits, said, unit_of):
    """What a set gives for wearing more of it.

    The lines are the planner's own wording and there is no translation for
    them, so the stat is named from the game's tables where its key is one the
    codex already knows and left in English where it is not.
    """
    theirs = {flat(k['name']): k for k in gear['sets']}
    bound = 0
    for name, kit in kits.items():
        got = theirs.get(flat((kit.get('names') or {}).get('en') or name))
        if not got:
            continue
        steps = []
        for b in got.get('bonuses') or []:
            said_lines = b.get('descriptions') or []
            stats = list((b.get('stats') or {}).items())
            lines = []
            for i, text in enumerate(said_lines):
                key, value = stats[i] if i < len(stats) else (None, None)
                lines.append({'says': text, 'of': key, 'v': value})
            if lines:
                steps.append({'pieces': b.get('pieces'), 'lines': lines})
        if steps:
            kit['bonuses'] = steps
            bound += 1
    return bound
