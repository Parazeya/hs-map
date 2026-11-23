/** Native storage modes keep their identity when a display language changes. */
export function conditionModeKey(mode, index = 0) {
  if (mode?.id != null) return String(mode.id);
  if (mode?.condition?.id != null) return String(mode.condition.id);
  const condition = mode?.condition;
  if (condition?.kind && condition.selector != null)
    return `${condition.kind}:${JSON.stringify(condition.selector)}`;
  return `${mode?.channel ?? 'legacy'}:${mode?.when ?? ''}:${index}`;
}

export function conditionRecordKey(item, variant = 0) {
  return item?.record_id ?? `${item?.key ?? ''}:${variant}`;
}

export function isPreviewCondition(mode) {
  return ['socket', 'damage_type'].includes(mode?.condition?.kind);
}

/** Keep the native option order; socket and damage selectors are independent. */
export function conditionChoices(modes = []) {
  const groups = new Map();
  for (const [index, mode] of modes.entries()) {
    if (!isPreviewCondition(mode)) continue;
    const kind = mode.condition.kind;
    if (!groups.has(kind)) groups.set(kind, { kind, label: kind === 'socket' ? 'Socketed item' : 'Damage type', options: [] });
    groups.get(kind).options.push({ id: conditionModeKey(mode, index), mode });
  }
  return [...groups.values()];
}

/** An absent or stale choice shows all outcomes, never an unrelated condition. */
export function selectedConditionModes(modes = [], selections = {}) {
  const choices = conditionChoices(modes);
  const active = new Map(choices.map(group => {
    const selected = selections[group.kind];
    return [group.kind, group.options.some(option => option.id === selected) ? selected : '*'];
  }));
  return modes.filter((mode, index) => !isPreviewCondition(mode)
    || active.get(mode.condition.kind) === '*'
    || active.get(mode.condition.kind) === conditionModeKey(mode, index));
}

export function conditionName(mode, lang = 'en', t = value => value) {
  const condition = mode?.condition;
  const name = condition?.names?.[lang] || condition?.names?.en;
  if (name) {
    if (condition.resolved === false) return name;
    if (condition.kind === 'socket') return `${t('With')} ${name}`;
    if (condition.kind === 'damage_type') return `${t('Damage type')}: ${name}`;
    return name;
  }
  const when = mode?.when ?? '';
  return when.startsWith('with a ') ? `${t('with a')} ${when.slice(7)}` : t(when);
}
