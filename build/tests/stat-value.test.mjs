import test from 'node:test';
import assert from 'node:assert/strict';
import { formatStatRange, formatStatValue } from '../../src/lib/stat-value.js';

const range = { kind: 'list', length: 2 };

test('partial ranges retain unknown endpoints and explicit zero', () => {
  assert.equal(formatStatValue({ max: 1, value_shape: range }), '?–1');
  assert.equal(formatStatValue({ min: 0, value_shape: range }), '0–?');
  assert.equal(formatStatValue({ min: 0, max: null, unit: '%', value_shape: range }), '0–?%');
  assert.equal(formatStatValue({ values: [null, 1], value_shape: range }), '?–1');
  assert.equal(formatStatValue({ values: [0, null], value_shape: range }), '0–?');
  assert.equal(formatStatValue({ min: null, max: null, value_shape: range, status: 'unresolved' }), '?');
  assert.equal(formatStatRange(null, 1), '?–1');
});

test('ordinary fixed scalars and complete ranges retain their display', () => {
  assert.equal(formatStatValue({ min: 0 }), '0');
  assert.equal(formatStatValue({ min: 8, unit: '%' }), '8%');
  assert.equal(formatStatValue({ min: 2, max: 2, value_shape: range }), '2');
  assert.equal(formatStatValue({ min: 2, max: 4, value_shape: range }), '2–4');
  assert.equal(formatStatValue({ status: 'partial' }), '?');
  assert.equal(formatStatValue({ min: 0, status: 'partial' }), '0');
});

test('Holy Bible keeps four unknown levels before all six known levels', () => {
  const values = [null, null, null, null, 1, 1, 1, 1, 1, 2];
  const stat = { max: 2, rank: 1, values, value_shape: { kind: 'list', length: 10 } };
  assert.equal(formatStatValue(stat), '? / ? / ? / ? / 1 / 1 / 1 / 1 / 1 / 2');
  assert.deepEqual(values, [null, null, null, null, 1, 1, 1, 1, 1, 2]);
});

test('inner, trailing and entirely unknown levels retain their positions', () => {
  assert.equal(formatStatValue({ min: 0, values: [0, null, 2, null], unit: '%' }), '0 / ? / 2 / ?%');
  assert.equal(formatStatValue({ values: [null, null, null], status: 'unresolved' }), '?');
  assert.equal(formatStatValue({ min: 2, max: 20, values: [2, 4, 6, 8, 10, 12, 14, 16, 18, 20] }), '2 / 4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20');
});

test('current relic1000kg dense stat203 vector retains every supplied ordinal', () => {
  const values = [2, 4, 8, 12, 16, 22, 28, 34, 42, 50];
  const stat = { id: 203, min: 2, max: 50, values, rank: 1,
    value_shape: { kind: 'list', length: 10 }, status: 'decoded' };
  const before = structuredClone(stat);
  assert.equal(formatStatValue(stat), '2 / 4 / 8 / 12 / 16 / 22 / 28 / 34 / 42 / 50');
  assert.deepEqual(stat, before);
});

test('dense repeated and nonmonotonic vectors do not lose interior values or positions', () => {
  assert.equal(formatStatValue({ min: 0, max: 0, values: [0, 0, 0] }), '0 / 0 / 0');
  assert.equal(formatStatValue({ min: 1, max: 3, values: [1, 1, 2, 2, 3] }), '1 / 1 / 2 / 2 / 3');
  assert.equal(formatStatValue({ min: 1, max: 3, values: [1, 4, 2, 5, 3] }), '1 / 4 / 2 / 5 / 3');
  assert.equal(formatStatValue({ values: [1, null, 3, null] }), '1 / ? / 3 / ?');
});

test('two-endpoint ranges, scalar bounds and entirely unknown vectors keep their contract', () => {
  assert.equal(formatStatValue({ min: 2, max: 20 }), '2–20');
  assert.equal(formatStatValue({ values: [2, 20] }), '2–20');
  assert.equal(formatStatValue({ values: [2, 20], value_shape: range }), '2–20');
  assert.equal(formatStatValue({ values: [null, null, null], status: 'partial',
    value_shape: { kind: 'list', length: 3 } }), '?');
});

test('array arity alone does not turn resources or entirely unknown values into a numeric range', () => {
  assert.equal(formatStatValue({ value_shape: range, status: 'unresolved' }), '?');
  assert.equal(formatStatValue({ value_shape: range, values: [null, null], status: 'partial' }), '?');
  assert.equal(formatStatValue({ value_shape: range, resource_references: [{ payload_hex: '0x0100000300000001' }] }), '');
  assert.equal(formatStatValue({ value_shape: range, value_expression: { numeric: false } }), '');
  assert.equal(formatStatValue({ value_shape: range, status: 'interpreted' }), '');
});
