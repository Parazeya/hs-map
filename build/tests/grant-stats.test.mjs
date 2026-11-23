import test from 'node:test';
import assert from 'node:assert/strict';
import { visibleItemStats, itemGrantGroups } from '../../src/lib/grant-stats.js';
import { formatStatValue } from '../../src/lib/stat-value.js';

test('a grant with unknown levels retains its unpaired stat203 range and ladder holes', () => {
  const range = { id: 203, sid: 'stat_random_skill', min: 0, value_shape: { kind: 'list', length: 2 } };
  const ladder = { id: 203, sid: 'stat_random_skill', values: [null, 1, null, 3], max: 3 };
  const item = { grants: [{ talent_id: 11, levels: null }], stats: [range, ladder] };
  const before = structuredClone(item);
  const shown = visibleItemStats(item);
  assert.deepEqual(shown, [range, ladder]);
  assert.equal(shown[0], range);
  assert.equal(formatStatValue(shown[0]), '0–?');
  assert.equal(formatStatValue(shown[1]), '? / 1 / ? / 3');
  assert.deepEqual(item, before);
});

test('an explicit text grant cannot hide an unrelated unresolved stat202 selector', () => {
  const selector = { id: 202, sid: 'singular_skill', min: 209, max: 217, status: 'unresolved',
    source: { file: 'Hero_Siege.exe', rva: 123 } };
  const item = { grants: [{ names: { en: 'Charge' }, provenance: { basis: 'explicit spell name' } }],
    stats: [selector] };
  assert.deepEqual(visibleItemStats(item), [selector]);
  assert.equal(formatStatValue(visibleItemStats(item)[0]), '209–217');
});

test('backend-consumed source statements are not reintroduced or matched by SID', () => {
  const consumed = { id: 202, sid: 'singular_skill', min: 11, source: { file: 'Hero_Siege.exe', rva: 123 } };
  const remaining = { id: 202, sid: 'singular_skill', min: 11, status: 'unresolved',
    source: { file: 'Hero_Siege.exe', rva: 456 } };
  const level = { id: 203, sid: 'stat_random_skill', values: [null, null, 2] };
  const item = { grants: [{ talent_id: 11, levels: null, source_stats: [consumed] }],
    stats: [remaining, level] };
  assert.deepEqual(visibleItemStats(item), [remaining, level]);
  assert.equal(visibleItemStats(item).some(stat => stat.source?.rva === 123), false);
  assert.deepEqual(item.grants[0].source_stats, [consumed]);
});

test('only Unholy slots move to their separate panel', () => {
  const ordinary = { id: 20, sid: 'socketed_flat', min: 0 };
  const item = { grants: [{ levels: null }], stats: [
    { sid: 'unholy_none', pool: 1 }, ordinary,
  ] };
  assert.deepEqual(visibleItemStats(item), [ordinary]);
  assert.deepEqual(visibleItemStats(null), []);
});

test('all independent aura and skill slots display once without duplicate catalogue copies', () => {
  const aura = { kind: 'aura', names: { en: 'Lunar Aura', ru: 'Лунная аура' }, levels: [5, 10] };
  const skill = { kind: 'skill', names: { en: 'Charge' }, level_values: [0, 1, 2, 3] };
  const item = { grants: [aura, skill, { ...skill, levels: [2, 5], level_values: undefined }],
    reference_grants: [{ names: { en: ' lunar aura ' } }, { kind: 'skill', names: { en: 'Whirlwind' } }] };
  const before = structuredClone(item);
  const groups = itemGrantGroups(item);
  assert.deepEqual(groups.map(group => [group.title, group.grants.length]), [['Auras', 1], ['Skills', 2]]);
  assert.equal(groups[0].grants[0], aura);
  assert.equal(groups[1].grants[0], skill);
  assert.deepEqual(item, before);
  assert.deepEqual(itemGrantGroups(null), []);
});

test('one example from a random skill range is not displayed as an additional guaranteed skill', () => {
  const random = { kind: 'skill', random_skill: true, skill_selector_range: [335, 343], levels: [4, 8] };
  const example = { names: { en: 'Avalanche' }, talent_source: { id_source: { native_id: 341 } } };
  const independent = { names: { en: 'Charge' }, talent_source: { id_source: { native_id: 11 } } };
  const item = { grants: [random], reference_grants: [example, independent] };
  const before = structuredClone(item);
  assert.deepEqual(itemGrantGroups(item)[0].grants, [random]);
  assert.deepEqual(itemGrantGroups({ reference_grants: [example, independent, example] })[0].grants, [example, independent]);
  assert.deepEqual(item, before);
});

test('auras, event triggers, skills, subskills and special effects retain their separate roles', () => {
  const grants = ['aura','trigger','skill','subskills','effect'].map((kind,n) => ({kind,names:{en:`Effect ${n}`}}));
  const before = structuredClone(grants);
  const groups = itemGrantGroups({grants});
  assert.deepEqual(groups.map(g=>[g.title,g.grants.length]), [['Auras',1],['Triggered effects',1],['Skills',2],['Effects',1]]);
  assert.deepEqual(groups.flatMap(g=>g.grants).sort((a,b)=>a.names.en.localeCompare(b.names.en)),grants);
  assert.deepEqual(grants,before);
});
