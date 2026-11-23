import test from 'node:test';
import assert from 'node:assert/strict';
import { hydrate, statsOf, grantsOf } from '../../src/lib/book.js';

test('hydration restores the stat vocabulary on every record variant', () => {
  const data = hydrate({ stats: [{ sid: 'damage', text: 'Damage', unit: '%' }], items: {
    base: { names: { en: 'Base' }, stats: [{ sid: 0, min: 2 }], variants: [
      { record_id: 'second', tier: 'C', stats: [{ sid: 0, min: 9 }] },
    ] },
  } });
  const second = data.items.base.variants[0];
  assert.equal(second.key, 'base');
  assert.equal(second.name, 'Base');
  assert.deepEqual(second.stats[0], { sid: 'damage', text: 'Damage', unit: '%', min: 9 });
  assert.equal(statsOf(data.items.base).length, 2);
});

test('an invalid vocabulary reference fails explicitly', () => {
  assert.throws(() => hydrate({ stats: [], items: { broken: { stats: [{ sid: 7 }] } } }), /Missing stat/);
});

test('item search includes every grant, conditional mode and record variant', () => {
  const grants = Array.from({ length: 5 }, (_, n) => ({ names: { en: `Skill ${n}` } }));
  const item = { grants: [grants[0]], reference_grants: [grants[1]], more: [{ grants: [grants[2]] }],
    variants: [{ grants: [grants[3]], more: [{ grants: [grants[4]] }] }] };
  const before = structuredClone(item);
  assert.deepEqual(grantsOf(item), grants);
  assert.deepEqual(item, before);
  assert.deepEqual(grantsOf(null), []);
});
