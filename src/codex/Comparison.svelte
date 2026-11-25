<script>
  import { tick } from 'svelte';
  import ItemIcon from '../ItemIcon.svelte';
  import { recordsOf } from '../lib/book.js';
  import { withMF } from '../lib/map.js';
  import { mf } from '../lib/mf.svelte.js';
  import { mapMessages } from '../lib/map-messages.js';
  import { formatStatRange, formatStatValue } from '../lib/stat-value.js';
  import { visibleItemStats, itemGrantGroups } from '../lib/grant-stats.js';
  import { conditionChoices, conditionName, selectedConditionModes } from '../lib/item-conditions.js';
  import { dropLocations, dropOdds, itemMapLink } from './farm.js';
  import { codexPhrase } from './phrases.js';

  let { entries, data, lang, sheet, t, change, remove, dismiss } = $props();
  let dialog = $state(null);
  const phrase = (text) => codexPhrase(lang, text);
  const word = (names) => names?.[lang] || names?.en || '';
  const glossary = $derived(new Map(data.stats.map(stat => [stat.sid, stat])));
  const records = $derived(entries.map(entry => {
    const options = recordsOf(data.items[entry.key]);
    const item = options[entry.variant] ?? options[0];
    return { entry, options, item, choices: conditionChoices(item.more) };
  }));
  const paired = $derived(records.length === 2);
  const recordName = (item, entry, options) => {
    const name = word(item.names) || item.name;
    return options.length > 1 ? `${name} · ${t('Variant')} ${entry.variant + 1}` : name;
  };

  $effect(() => {
    dialog?.showModal();
  });

  async function removeEntry(slot) {
    remove(slot);
    await tick();
    (dialog?.querySelector('.remove') ?? dialog?.querySelector('.close'))?.focus();
  }

  const stats = $derived.by(() => {
    const byKey = new Map();
    function add(index, key, label, value, mode) {
      if (!byKey.has(key)) byKey.set(key, { key, label, values: records.map(() => []) });
      byKey.get(key).values[index].push({ value, condition: mode ? conditionName(mode, lang, t) : '' });
    }

    for (const [index, { item, entry }] of records.entries()) {
      const modes = selectedConditionModes(item.more, entry.conditions);
      for (const mode of [null, ...modes]) {
        const owner = mode ?? item;
        for (const stat of visibleItemStats(owner)) {
          const label = [
            word(glossary.get(stat.sid)?.names) || t(stat.text),
            stat.spell,
            word(stat.class_names) || (stat.cls !== 'Any' ? stat.cls : ''),
          ].filter(Boolean).join(' · ');
          const value = word(stat.value_names) || formatStatValue(
            stat.unit_names ? { ...stat, unit: ' ' + word(stat.unit_names) } : stat,
          ) || '✓';
          add(index, JSON.stringify(['stat', stat.sid, stat.spell, stat.class_names?.en || stat.cls]), label, value, mode);
        }
        const rolls = (owner.stats ?? []).filter(stat => stat.sid === 'unholy_none' && stat.active !== false);
        if (rolls.length) add(index, 'random-modifiers', t('Random modifiers'), rolls.length, mode);
        for (const group of itemGrantGroups(owner)) {
          for (const grant of group.grants) {
            const name = grant.random_skill ? t('Random skill') : word(grant.names);
            const levels = grant.level_values?.length
              ? grant.level_values.map(value => value ?? '?').join(' / ')
              : formatStatRange(...(grant.levels ?? []));
            const chance = grant.chance_values?.length
              ? grant.chance_values.map(value => value ?? '?').join(' / ')
              : formatStatRange(...(grant.chance ?? []));
            const value = [
              levels && `${t('Level')} ${levels}`,
              grant.kind === 'trigger' && chance && `${chance}%`,
            ].filter(Boolean).join(' · ');
            add(index, JSON.stringify(['grant', grant.kind, grant.talent_key || grant.names?.en, grant.class_names?.en]),
              [t(group.title), name, word(grant.class_names)].filter(Boolean).join(' · '), value || '✓', mode);
          }
        }
      }
    }
    return [...byKey.values()];
  });

  const rates = [
    { field: 'rate', label: 'Base drop odds' },
    { field: 'chase', label: 'Zone drop odds' },
  ];
</script>

<dialog bind:this={dialog} onclose={dismiss} aria-labelledby="comparison-title">
  <header>
    <h2 id="comparison-title">{phrase('Item comparison')}</h2>
    <form method="dialog"><button class="close" aria-label={mapMessages(lang).close}>×</button></form>
  </header>
  <div class="content">
    {#if !paired}<p class="hint">{phrase('Choose another item to compare.')}</p>{/if}
    <div class="records" class:paired>
      {#each records as { item, entry, options, choices } (entry.slot)}
        <section>
          <div class="record-head">
            <ItemIcon {item} sheet={data.sheet} from={sheet} box={34} />
            <div>
              <h3>{recordName(item, entry, options)}</h3>
              <p>{[t(item.rarity), t(item.type), item.tier, item.lvl && `${t('Level')} ${item.lvl}`].filter(Boolean).join(' · ')}</p>
            </div>
          </div>
          {#if options.length > 1}
            <label>{t('Variant')}
              <select aria-label={t('Variant')} value={entry.variant} onchange={event => change({
                ...entry, variant: Number(event.currentTarget.value), conditions: {},
              })}>
                {#each options as option, index (option.record_id ?? index)}
                  <option value={index}
                    disabled={entries.some(other => other.slot !== entry.slot && other.key === entry.key && other.variant === index)}>
                    {t('Variant')} {index + 1} · {[t(option.rarity), t(option.type), option.tier, option.lvl && `${t('Level')} ${option.lvl}`].filter(Boolean).join(' · ')}
                  </option>
                {/each}
              </select>
            </label>
          {/if}
          {#each choices as choice (choice.kind)}
            <label>{t(choice.label)}
              <select aria-label={t(choice.label)} value={entry.conditions[choice.kind] ?? '*'} onchange={event => change({
                ...entry, conditions: { ...entry.conditions, [choice.kind]: event.currentTarget.value },
              })}>
                <option value="*">{t('All variants')}</option>
                {#each choice.options as option (option.id)}
                  <option value={option.id}>{word(option.mode.condition?.names) || conditionName(option.mode, lang, t)}</option>
                {/each}
              </select>
              {#if choice.options.some(option => option.mode.condition?.per_socket)}
                <small>{t('Bonuses per matching socket')}</small>
              {/if}
            </label>
          {/each}
          <button class="remove" onclick={() => removeEntry(entry.slot)}>{phrase('Remove')}</button>
        </section>
      {/each}
    </div>

    {#if paired}
      <table>
        <thead>
          <tr>
            <th scope="col">{t('Stats')}</th>
            {#each records as { item, entry, options } (entry.slot)}
              <th scope="col">{recordName(item, entry, options)}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{t('Drop location')}</th>
            {#each records as { item, entry } (entry.slot)}
              {@const sources = dropLocations(item, lang, data)}
              {@const link = itemMapLink(item)}
              <td>
                {sources.join(' · ') || '—'}
                {#if link}<a href={link}>{t('Show it on the map')} →</a>{/if}
              </td>
            {/each}
          </tr>
          {#each rates as { field, label } (field)}
            {@const tied = records[0].item[field] > 0 && records[0].item[field] === records[1].item[field]}
            {#if field === 'rate' || records.some(({ item }) => item[field] > 0)}
              <tr>
                <th scope="row">{phrase(label)}{#if tied}<small>{phrase('Equal odds')}</small>{/if}</th>
                {#each records as { item, entry } (entry.slot)}
                  <td>
                    {dropOdds(item[field], lang) || phrase('Unknown odds')}
                    {#if mf.value > 0 && item[field] > 0}
                      <small class="adjusted">{dropOdds(withMF(item[field], mf.value), lang)} · {mf.value}% MF</small>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/if}
          {/each}
          {#each stats as { key, label, values } (key)}
            <tr>
              <th scope="row">{label}</th>
              {#each values as cell, index (index)}
                <td>
                  {#if cell.length === 0}—{/if}
                  {#each cell as { value, condition }, entry (entry)}
                    <span>{value}{#if condition}<small>{condition}</small>{/if}</span>
                  {/each}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</dialog>

<style>
  dialog {
    width: min(52rem, calc(100% - 24px));
    max-height: calc(100dvh - 26px);
    border: 1px solid var(--edge);
    border-radius: 10px;
    background: var(--ground, #100a13);
    color: var(--ink);
    padding: 0;
  }
  dialog::backdrop { background: #08050cbf; }
  header {
    position: sticky;
    top: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid var(--edge);
    background: var(--panel);
    padding: 10px 13px;
  }
  h2 { margin: 0; font-size: 15px; }
  button, select {
    background: #0e0912;
    border: 1px solid var(--edge);
    border-radius: 6px;
    color: var(--ink);
    font: inherit;
  }
  button { padding: 5px 8px; cursor: pointer; }
  button:hover { border-color: var(--hot); }
  .close { font-size: 16px; line-height: 1; }
  .content { padding: 10px 13px 15px; }
  .records { display: grid; gap: 8px; }
  .paired { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  section { min-width: 0; padding: 8px; background: var(--panel); border: 1px solid var(--edge); border-radius: 7px; }
  .record-head { display: flex; align-items: center; gap: 8px; }
  h3 { margin: 0 0 3px; font-size: 14px; overflow-wrap: anywhere; }
  p, label { margin: 0; color: var(--dim); font-size: 12px; }
  label { display: grid; margin-top: 6px; gap: 3px; min-width: 0; }
  select { min-width: 0; width: 100%; padding: 4px; }
  .remove { margin-top: 7px; color: var(--dim); font-size: 11px; }
  .hint { margin-bottom: 8px; }
  table { width: 100%; margin-top: 8px; border-collapse: collapse; table-layout: fixed; font-size: 12px; }
  th, td { padding: 6px; border-bottom: 1px solid var(--edge); vertical-align: top; text-align: left; overflow-wrap: anywhere; }
  th:first-child { width: 32%; }
  thead th { color: var(--hot); }
  tbody th { color: var(--dim); font-weight: normal; }
  td span, small, a { display: block; }
  td span + span { margin-top: 4px; }
  small { margin-top: 2px; color: var(--dim); font-size: 11px; }
  .adjusted { color: #e8c860; }
  a { margin-top: 3px; color: var(--hot); font-size: 11px; }
  @media (max-width: 35rem) {
    .content, header { padding-left: 8px; padding-right: 8px; }
    .record-head { align-items: flex-start; }
    .records section { padding: 6px; }
    th, td { padding: 5px 4px; }
  }
</style>
