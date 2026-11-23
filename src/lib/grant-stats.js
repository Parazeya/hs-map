/** Backend-retained grant operands remain visible; Unholy slots have their own panel. */
export function visibleItemStats(item) {
  return (item?.stats ?? []).filter(stat => stat.sid !== 'unholy_none');
}

/** Current slots are complete for this record; older suggestions are a fallback. */
export function itemGrantGroups(item) {
  const native = item?.grants ?? [];
  const name = grant => (grant.names?.en ?? grant.talent_key ?? '').trim().toLowerCase();
  const known = new Set();
  const combined = [...native];
  for (const grant of native.length ? [] : item?.reference_grants ?? []) {
    const identity = name(grant);
    if (identity && known.has(identity)) continue;
    combined.push(grant);
    if (identity) known.add(identity);
  }
  return [
    { title: 'Auras', grants: combined.filter(grant => grant.kind === 'aura') },
    { title: 'Triggered effects', grants: combined.filter(grant => grant.kind === 'trigger') },
    { title: 'Skills', grants: combined.filter(grant => !['aura', 'trigger', 'effect'].includes(grant.kind)) },
    { title: 'Effects', grants: combined.filter(grant => grant.kind === 'effect') },
  ].filter(group => group.grants.length);
}
