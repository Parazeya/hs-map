import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { zoneDropOdds } from '../../src/lib/map.js';

test('zone odds take precedence only for current zone sources', () => {
  const items = { sample: { rate: 500, chase: 100 } };
  assert.deepEqual(zoneDropOdds({}, 'sample', items), { odds: 100, oddsBasis: 'zone' });
  assert.deepEqual(
    zoneDropOdds({ reference_drops: ['sample'] }, 'sample', items),
    { odds: 500, oddsBasis: 'base' },
  );
  assert.deepEqual(zoneDropOdds({}, 'sample', { sample: { rate: 500 } }), { odds: 500, oddsBasis: 'base' });
  assert.deepEqual(zoneDropOdds({}, 'missing', items), { odds: null, oddsBasis: null });
});

test("the Devil's Breach can show current base odds", () => {
  const data = JSON.parse(readFileSync(new URL('../../public/data/map.json', import.meta.url), 'utf8'));
  const breach = data.nodes.find((node) => node.room === 'Act_04_05');
  assert.deepEqual(zoneDropOdds(breach, 'diablo', data.items), { odds: 516750, oddsBasis: 'base' });
});
