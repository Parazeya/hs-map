export const ITEM_GRADES = ['Satanic', 'Unholy', 'Angelic', 'Heroic', 'Set', 'Runeword', 'Common'];
const rank = new Map(ITEM_GRADES.map((rarity, index) => [rarity, index]));

export function searchText(value) {
  return value.normalize('NFC').trim().toLowerCase().replace(/[‘’]/g, "'").replace(/\s+/g, ' ');
}

export function searchItems(items, query, rarity) {
  const rows = [];
  const exact = [];
  const tokens = query.match(/[\p{L}\p{N}\p{M}]+/gu) ?? [];
  for (const [name, item] of items) {
    if (rarity && item.rarity !== rarity) continue;
    if (query) {
      const names = [name, ...Object.values(item.names ?? {})].map(searchText);
      if (!names.some(alias => alias.includes(query) || tokens.length > 0 && tokens.every(token => alias.includes(token)))) continue;
      if (names.includes(query)) exact.push(name);
    }
    rows.push([name, item]);
  }
  rows.sort(([a, first], [b, second]) =>
    (rank.get(first.rarity) ?? 9) - (rank.get(second.rarity) ?? 9) ||
    (second.tier ?? 0) - (first.tier ?? 0) || a.localeCompare(b));
  return { rows, exact: exact.length === 1 ? exact[0] : null };
}

export function buildSourceIndex({ nodes, bosses, items }) {
  const index = new Map(Object.keys(items).map((name) => [name, { rooms: new Set(), sources: new Set() }]));
  const byCode = new Map();
  for (const node of nodes) {
    if (node.code) {
      if (!byCode.has(node.code)) byCode.set(node.code, []);
      byCode.get(node.code).push(node.room);
    }
    for (const item of node.drops) index.get(item)?.rooms.add(node.room);
    for (const { item } of bosses[node.boss]?.drops ?? []) index.get(item)?.rooms.add(node.room);
  }
  for (const [name, item] of Object.entries(items)) {
    for (const code of item.zones ?? []) {
      for (const room of byCode.get(code) ?? []) index.get(name).rooms.add(room);
    }
  }
  for (const [name, boss] of Object.entries(bosses)) {
    if (!isShelfSource(boss)) continue;
    for (const { item } of boss.drops) index.get(item)?.sources.add(name);
  }
  return index;
}

export const isShelfSource = (boss) => ['uber', 'other', 'source'].includes(boss?.kind);

export function canonicalMapItem(items, key) {
  if (!key) return null;
  const rows = Object.entries(items).filter(([, item]) => item.key === key);
  return rows.length === 1 ? rows[0][0] : null;
}

export function itemSourceDetails(data, index, name) {
  const entry = index?.get(name);
  return {
    rooms: data.nodes.filter(node => entry?.rooms.has(node.room)),
    sources: Object.entries(data.bosses).filter(([key]) => entry?.sources.has(key)),
  };
}

export function itemSources(index, names) {
  const rooms = new Set();
  const sources = new Set();
  for (const name of names) {
    const item = index.get(name);
    if (!item) continue;
    for (const room of item.rooms) rooms.add(room);
    for (const source of item.sources) sources.add(source);
  }
  return { rooms, sources };
}
