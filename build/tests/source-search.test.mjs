import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { buildSourceIndex, itemSources, searchItems, searchText } from '../../src/lib/source-search.js';

const read = (file) => JSON.parse(readFileSync(new URL(`../../public/data/${file}`, import.meta.url), 'utf8'));
const map = read('map.json');
const ru = read('map.ru.json');
const items = Object.entries(map.items).map(([name, item]) => [name, {
  ...item,
  names: { ...item.names, ...(ru.items[name]?.names ? { ru: ru.items[name].names } : {}) },
}]);
const index = buildSourceIndex(map);
const match = (query, grade) => searchItems(items, searchText(query), grade);

test('English and localized aliases reach the same rooms through one item result', () => {
  const english = match('  Bonetti’s  Rapier ');
  const russian = match('Рапира Бонетти');
  assert.deepEqual(english.rows, russian.rows);
  assert.equal(english.exact, "bonetti's rapier");
  assert.equal(english.exact, russian.exact);
  assert.deepEqual([...itemSources(index, [english.exact]).rooms].sort(), ['Act_01_01', 'Act_01_02', 'Act_01_03']);
  assert.equal(match('Рапира Бонетти', 'Common').rows.length, 0);
});

test('chest-only drops resolve to the shelf even when the item lists no zone', () => {
  const belt = match('Belt of Infinite Wealth').exact;
  assert.equal(belt, 'belt of infinite wealth');
  assert.deepEqual(itemSources(index, [belt]), { rooms: new Set(), sources: new Set(['Crystal Chest']) });
  const dungeon = map.bosses['Dungeon Chest'].drops[0].item;
  assert.ok(itemSources(index, [dungeon]).sources.has('Dungeon Chest'));
});

test('act boss drops resolve to their room without adding a separate shelf entry', () => {
  const room = map.nodes.find((node) => node.boss && map.bosses[node.boss]?.drops.length);
  const item = map.bosses[room.boss].drops[0].item;
  const location = itemSources(index, [item]);
  assert.ok(location.rooms.has(room.room));
  assert.ok(!location.sources.has(room.boss));
});
