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

test('historical odds are limited to the exact reference row', () => {
  const items = { sample: { rate: 500, chase: 100 }, other: { rate: 400 } };
  const node = { reference_drops: ['sample'], reference_drop_odds: { sample: 150, other: 75 } };
  assert.deepEqual(zoneDropOdds(node, 'sample', items), { odds: 150, oddsBasis: 'reference-zone' });
  assert.deepEqual(zoneDropOdds(node, 'other', items), { odds: 400, oddsBasis: 'base' });
  node.reference_drop_odds.sample = -1;
  assert.deepEqual(zoneDropOdds(node, 'sample', items), { odds: 500, oddsBasis: 'base' });
});

test('restored zone odds and current zone odds keep their separate basis', () => {
  const data = JSON.parse(readFileSync(new URL('../../public/data/map.json', import.meta.url), 'utf8'));
  const breach = data.nodes.find((node) => node.room === 'Act_04_05');
  const mind = data.nodes.find((node) => node.room === 'Act_07_05');
  const cave = data.nodes.find((node) => node.room === 'Act_04_03');
  assert.deepEqual(zoneDropOdds(breach, 'diablo', data.items), { odds: 164068, oddsBasis: 'reference-zone' });
  assert.deepEqual(zoneDropOdds(mind, 'ak-47', data.items), { odds: 167360, oddsBasis: 'reference-zone' });
  assert.deepEqual(zoneDropOdds(cave, "rugal's sash of undertaking", data.items), { odds: 155817, oddsBasis: 'zone' });
});
