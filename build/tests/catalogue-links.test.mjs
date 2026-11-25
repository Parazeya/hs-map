import assert from 'node:assert/strict';
import test from 'node:test';
import { hydrate, resolveItem } from '../../src/lib/book.js';
import { canonicalMapItem, searchItems, searchText } from '../../src/lib/source-search.js';
import { setBonusText } from '../../src/lib/set-bonuses.js';

test('canonical identities select the exact record and never guess a shared name', () => {
  const book = hydrate({ items: {
    charm: { record_id: 'charm@0', names: { en: 'Shrunken Head' }, variants: [{ record_id: 'charm@1' }] },
    relic: { record_id: 'relic@0', names: { en: 'Shrunken Head' } },
    nameless: { record_id: 'nameless@0' },
  } });
  assert.equal(resolveItem(book, 'shrunken head'), null);
  assert.deepEqual(resolveItem(book, 'shrunken head', 'charm', 'charm@1'), { key: 'charm', recordId: 'charm@1' });
  assert.equal(resolveItem(book, 'shrunken head', 'charm', 'relic@0'), null);
  assert.equal(book.items.nameless.name, 'nameless');
  assert.equal(canonicalMapItem({ 'shrunken head': { key: 'charm' } }, 'charm'), 'shrunken head');
});

test('search accepts fragments in another order without treating them as exact', () => {
  const items = [['rapid bone', { names: { ru: 'Рапид Бонер' } }]];
  const { rows, exact } = searchItems(items, searchText('боне / рапи'));
  assert.equal(rows[0][0], 'rapid bone');
  assert.equal(exact, null);
});

test('translated set bonuses retain the visible value and class', () => {
  const data = {
    stats: [{ names: { en: 'All Skills', ru: 'Все умения' } }],
    classes: [{ names: { en: 'Amazon', ru: 'Амазонка' } }],
  };
  const line = { says: '+3 to All Skills (Amazon)', v: 25, of: 'ignore_poison_res' };
  assert.equal(setBonusText(line, 'ru', data), '+3 Все умения (Амазонка)');
  assert.equal(setBonusText(line, 'en', data), line.says);
  assert.equal(setBonusText({ says: '+1 to Summon Abomination' }, 'ru', data), '+1 to Summon Abomination');
});
