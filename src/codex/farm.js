import { figure, mapDocument } from '../lib/map.js';
import { formatDropOdds } from '../lib/drop-odds.js';
import { places } from '../lib/say.js';

const sourceIdentity = name => name.replace(/\s*\(Inferno[^)]*\)\s*$/i, '').toLowerCase();

export function dropLocations(item, lang = 'en', data) {
  const place = places(lang, data?.words, name => data?.places?.[name]?.[lang]);
  const declared = [
    ...(item?.places ?? []),
    ...(item?.reference_places ?? []).map(source => source.name).filter(Boolean),
  ];
  const seen = new Set(declared.map(sourceIdentity));
  const shelves = (item?.map_sources?.shelves ?? []).filter(source => !seen.has(sourceIdentity(source)));
  const named = [...declared, ...shelves].map(place);
  const rooms = (item?.map_sources?.rooms ?? []).map(room => {
    const name = data?.map_rooms?.[room];
    return name?.[lang] || name?.en;
  }).filter(Boolean);
  return [...new Set([...named, ...rooms])];
}

export const dropOdds = (n, lang) => n > 0
  ? formatDropOdds(lang, figure(n))
  : '';

export function itemMapLink(item) {
  if (!item?.key || !(item.map_sources?.rooms?.length || item.map_sources?.shelves?.length)) return null;
  return mapDocument('index.html', { item: item.key, find: item.name });
}
