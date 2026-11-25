const fold = text => text.trim().toLowerCase().replace(/^to\s+/, '');

export function setBonusText(line, lang, data) {
  if (lang === 'en') return line.says;
  const parsed = /^([+−–-]?\d+(?:\.\d+)?%?)\s+([^()]+?)(?:\s*\(([^()]+)\))?$/.exec(line.says);
  if (!parsed) return line.says;
  const [, amount, label, owner] = parsed;
  const words = new Set((data.stats ?? [])
    .filter(stat => stat.names?.en && fold(stat.names.en) === fold(label))
    .map(stat => stat.names[lang]).filter(Boolean));
  if (words.size !== 1) return line.says;
  const named = owner && (data.classes ?? []).find(row => row.names?.en === owner)?.names?.[lang];
  if (owner && !named) return line.says;
  return `${amount} ${[...words][0]}${named ? ` (${named})` : ''}`;
}
