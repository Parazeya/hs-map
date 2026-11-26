import { figure, mapDocument } from '../lib/map.js';
import { formatDropOdds } from '../lib/drop-odds.js';
import { places } from '../lib/say.js';

const sourceIdentity = name => name.replace(/\s*\(Inferno[^)]*\)\s*$/i, '').toLowerCase();

export function dropLocationRows(item, lang = 'en', data) {
  const place = places(lang, data?.words, name => data?.places?.[name]?.[lang]);
  const declared = [
    ...(item?.places ?? []),
    ...(item?.reference_places ?? []).map(source => source.name).filter(Boolean),
  ];
  const seen = new Set(declared.map(sourceIdentity));
  const shelves = (item?.map_sources?.shelves ?? []).filter(source => !seen.has(sourceIdentity(source)));
  const rows = new Map();
  for (const source of [...declared, ...shelves]) {
    const name = place(source);
    rows.set(name, { name });
  }
  for (const room of item?.map_sources?.rooms ?? []) {
    const names = data?.map_rooms?.[room];
    const name = names?.[lang] || names?.en;
    if (!name) continue;
    const chance = item.map_sources.room_odds?.[room];
    if (!rows.has(name) || (chance && !rows.get(name).rate)) rows.set(name, { name, ...chance });
  }
  return [...rows.values()];
}

export const dropLocations = (item, lang, data) => dropLocationRows(item, lang, data).map(row => row.name);

export const dropOdds = (n, lang) => n > 0
  ? formatDropOdds(lang, figure(n))
  : '';

export function itemMapLink(item) {
  if (!item?.key || !(item.map_sources?.rooms?.length || item.map_sources?.shelves?.length)) return null;
  return mapDocument('index.html', { item: item.key, find: item.name });
}
