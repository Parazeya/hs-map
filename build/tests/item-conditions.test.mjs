import test from 'node:test';
import assert from 'node:assert/strict';
import { conditionModeKey, conditionRecordKey, conditionChoices, selectedConditionModes, conditionName } from '../../src/lib/item-conditions.js';

const socket = (n, en, ru) => ({ id: `socket:${n}`, when: 'socket condition', condition: {
  id: `socket:${n}`, kind: 'socket', selector: n, names: { en, ru }, resolved: true,
}, stats: [{ id: 48, min: n }], grants: [{ names: { en: `Skill ${n}` } }] });
const damage = n => ({ id: `damage_type:${n}`, when: 'damage type condition', condition: {
  id: `damage_type:${n}`, kind: 'damage_type', selector: n, names: { en: n ? 'Arcane' : 'Physical' }, resolved: true,
}, stats: [{ id: 128, min: n }] });

test('default preview keeps every named outcome and unconditional storage mode', () => {
  const plain = { id: 'armor', when: 'in armour', stats: [{ id: 154, min: 20 }] };
  const modes = [socket(70, 'Gurag', 'Гураг'), socket(71, 'Death', 'Смерть'), plain, damage(0), damage(1)];
  const before = structuredClone(modes);
  assert.deepEqual(selectedConditionModes(modes), modes);
  assert.deepEqual(conditionChoices(modes).map(g => [g.kind, g.options.map(o => o.id)]), [
    ['socket', ['socket:70', 'socket:71']], ['damage_type', ['damage_type:0', 'damage_type:1']],
  ]);
  assert.deepEqual(modes, before);
});

test('each selector filters the entire outcome while retaining other kinds and base storage', () => {
  const one = socket(70, 'Gurag', 'Гураг'), two = socket(71, 'Death', 'Смерть');
  const plain = { when: 'two-handed', stats: [{ id: 28, min: 50 }] };
  const physical = damage(0), arcane = damage(1);
  const modes = [one, two, plain, physical, arcane];
  assert.deepEqual(selectedConditionModes(modes, { socket: 'socket:71' }), [two, plain, physical, arcane]);
  assert.deepEqual(selectedConditionModes(modes, { socket: 'socket:71', damage_type: 'damage_type:0' }), [two, plain, physical]);
  assert.equal(selectedConditionModes(modes, { socket: 'socket:70' })[0].grants, one.grants);
  assert.deepEqual(selectedConditionModes(modes, { socket: 'socket:999' }), modes);
});

test('language changes labels without changing option or record identity', () => {
  const mode = socket(70, "Gurag's Soulgem", 'Самоцвет Гурага');
  const selected = { socket: conditionModeKey(mode) };
  assert.equal(conditionName(mode, 'en'), "With Gurag's Soulgem");
  assert.equal(conditionName(mode, 'ru', text => ({ With: 'С' })[text] ?? text), 'С Самоцвет Гурага');
  assert.equal(conditionModeKey(mode), 'socket:70');
  assert.equal(selectedConditionModes([mode], selected)[0], mode);
  const item = { key: 'ring', record_id: 'ring@7:1:0', names: { en: 'Ring', ru: 'Кольцо' } };
  assert.equal(conditionRecordKey(item), conditionRecordKey({ ...item, names: { en: 'Other' } }));
  assert.notEqual(conditionRecordKey(item), conditionRecordKey({ ...item, record_id: 'ring@7:1:1' }));
});

test('zero damage selector and unresolved modes keep independent stable keys', () => {
  assert.equal(conditionModeKey({ condition: { kind: 'damage_type', selector: 0 } }), 'damage_type:0');
  const unknown = { id: 'socket:opaque:1', when: 'socket condition', condition: { kind: 'socket', names: { en: 'Socket condition' }, resolved: false } };
  assert.equal(conditionName(unknown), 'Socket condition');
  assert.notEqual(conditionModeKey(unknown), conditionModeKey({ ...unknown, id: 'socket:opaque:2' }));
  assert.equal(conditionName({ when: 'with a Rune' }), 'with a Rune');
  assert.deepEqual(conditionChoices(), []);
});
