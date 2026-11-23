/** A known lower bound can be a scalar; two source operands establish a range. */
export function formatStatRange(lo, hi, unit = '', range = false) {
  if (lo == null && hi == null) return '';
  if (lo == null) return `?–${hi}${unit}`;
  if (hi == null) return range ? `${lo}–?${unit}` : `${lo}${unit}`;
  return hi === lo ? `${lo}${unit}` : `${lo}–${hi}${unit}`;
}

/** Level vectors keep every ordinal; scalars and two-operand ranges keep their shape. */
export function formatStatValue(stat) {
  const values = stat?.values;
  const unit = stat?.unit ?? '';
  const numeric = value => typeof value === 'number' && Number.isFinite(value);
  const numericLevels = Array.isArray(values) && values.some(numeric);
  const numericBounds = numeric(stat?.min) || numeric(stat?.max);
  const range = stat?.value_shape?.kind === 'list' && stat.value_shape.length === 2;
  if (!numericBounds && !numericLevels) {
    if (stat?.resource_references?.length || stat?.value_expression?.numeric === false || stat?.status === 'interpreted') return '';
    return stat?.unresolved || stat?.value_shape || ['partial', 'unresolved'].includes(stat?.status) ? '?' : '';
  }
  if (numericLevels && !range && (values.length > 2 || values.some(value => !numeric(value))))
    return `${values.map(value => numeric(value) ? String(value) : '?').join(' / ')}${unit}`;
  const lo = stat?.min ?? (numericLevels ? values[0] : undefined);
  const hi = stat?.max ?? (numericLevels ? values.at(-1) : undefined);
  return formatStatRange(lo, hi, unit, range);
}
