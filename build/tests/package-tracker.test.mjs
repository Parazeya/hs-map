import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, rmSync, renameSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { publishPackage, recoverPackage, validatePackage, withMapPackageUpdate } from '../../scripts/package-tracker.mjs';
import { createHash } from 'node:crypto';

function fixture() {
  const root = mkdtempSync(join(tmpdir(), 'hs-map-package-test-')), tracker = join(root, 'tracker'), candidate = join(root, 'candidate');
  for (const path of [join(tracker, 'public', 'hs-map'), join(tracker, 'src-tauri'), join(candidate, 'data'), join(candidate, 'assets')]) mkdirSync(path, { recursive: true });
  writeFileSync(join(tracker, 'package.json'), '{}'); writeFileSync(join(tracker, 'public', 'hs-map', 'old.txt'), 'active');
  const fingerprint = 'a'.repeat(64);
  writeFileSync(join(candidate, 'index.html'), '<script type="module" src="/hs-map/assets/map-test.js"></script>');
  writeFileSync(join(candidate, 'assets', 'map-test.js'), 'export const current = true;');
  writeFileSync(join(candidate, 'data', 'source.json'), JSON.stringify({ fingerprint }));
  writeFileSync(join(candidate, 'data', 'map.json'), JSON.stringify({ source: { fingerprint } }));
  return { root, tracker, candidate, cleanup: () => rmSync(root, { recursive: true }) };
}

test('packaged map validates current source and installs only the named target', () => {
  const f = fixture(); try {
    writeFileSync(join(f.tracker, 'public', 'unrelated.txt'), 'keep');
    const report = publishPackage(f.candidate, f.tracker);
    assert.equal(report.files.length, 4); assert.equal(readFileSync(join(f.tracker, 'public', 'unrelated.txt'), 'utf8'), 'keep');
    assert.equal(readFileSync(join(report.target, 'assets', 'map-test.js'), 'utf8'), 'export const current = true;');
    assert.deepEqual(readdirSync(join(f.tracker, 'public')).sort(), ['hs-map', 'unrelated.txt']);
  } finally { f.cleanup(); }
});

test('second publication rename failure restores the previous active package', () => {
  const f = fixture(); try {
    let calls = 0;
    assert.throws(() => publishPackage(f.candidate, f.tracker, { rename(from, to) { if (++calls === 2) throw new Error('simulated install failure'); renameSync(from, to); } }), /simulated/);
    assert.equal(readFileSync(join(f.tracker, 'public', 'hs-map', 'old.txt'), 'utf8'), 'active');
    assert.deepEqual(readdirSync(join(f.tracker, 'public')), ['hs-map']);
  } finally { f.cleanup(); }
});

test('stale or broken generated inputs fail before touching the active package', () => {
  const f = fixture(); try {
    writeFileSync(join(f.candidate, 'data', 'map.json'), JSON.stringify({ source: { fingerprint: 'b'.repeat(64) } }));
    assert.throws(() => publishPackage(f.candidate, f.tracker), /fingerprint mismatch/);
    assert.equal(readFileSync(join(f.tracker, 'public', 'hs-map', 'old.txt'), 'utf8'), 'active');
  } finally { f.cleanup(); }
});

test('interrupted first rename recovers the old package before validating another candidate', () => {
  const f = fixture(); try {
    const parent = join(f.tracker, 'public'), target = join(parent, 'hs-map'), staged = join(parent, '.hs-map-package-stage-test'), backup = join(parent, '.hs-map-package-backup-test');
    mkdirSync(staged); writeFileSync(join(staged, 'partial.txt'), 'private');
    renameSync(target, backup);
    writeFileSync(join(parent, '.hs-map-package-journal.json'), JSON.stringify({ schema_version: 1, target, staged, backup, package_hash: createHash('sha256').update('future').digest('hex') }));
    assert.equal(recoverPackage(f.tracker), true);
    assert.equal(readFileSync(join(target, 'old.txt'), 'utf8'), 'active');
    assert.deepEqual(readdirSync(parent), ['hs-map']);
  } finally { f.cleanup(); }
});

test('another live publisher cannot recover or replace its active package', () => {
  const f = fixture(); try {
    writeFileSync(join(f.tracker, 'public', '.hs-map-package.lock'), JSON.stringify({ pid: process.pid, token: 'other' }));
    assert.throws(() => publishPackage(f.candidate, f.tracker), /publication lock/);
    assert.throws(() => recoverPackage(f.tracker), /publication lock/);
    assert.equal(readFileSync(join(f.tracker, 'public', 'hs-map', 'old.txt'), 'utf8'), 'active');
  } finally { f.cleanup(); }
});

test('interrupted first publication restores target absence and permits a retry', () => {
  const f = fixture(); try {
    const parent = join(f.tracker, 'public'), target = join(parent, 'hs-map'), staged = join(parent, '.hs-map-package-stage-first'), backup = join(parent, '.hs-map-package-backup-first');
    rmSync(target, { recursive: true });
    mkdirSync(staged); writeFileSync(join(staged, 'partial.txt'), 'private');
    writeFileSync(join(parent, 'unrelated.txt'), 'keep');
    writeFileSync(join(parent, '.hs-map-package-journal.json'), JSON.stringify({ schema_version: 2, existed: false, target, staged, backup, package_hash: createHash('sha256').update('future').digest('hex') }));
    assert.equal(recoverPackage(f.tracker), true);
    assert.deepEqual(readdirSync(parent), ['unrelated.txt']);
    assert.equal(publishPackage(f.candidate, f.tracker).files.length, 4);
  } finally { f.cleanup(); }
});

test('completed first publication is verified before its interrupted journal is removed', () => {
  const f = fixture(); try {
    const parent = join(f.tracker, 'public'), target = join(parent, 'hs-map'), staged = join(parent, '.hs-map-package-stage-first'), backup = join(parent, '.hs-map-package-backup-first');
    const package_hash = createHash('sha256').update(JSON.stringify(validatePackage(f.candidate))).digest('hex');
    rmSync(target, { recursive: true }); renameSync(f.candidate, target);
    writeFileSync(join(parent, '.hs-map-package-journal.json'), JSON.stringify({ schema_version: 2, existed: false, target, staged, backup, package_hash }));
    assert.equal(recoverPackage(f.tracker), true);
    assert.equal(validatePackage(target).files.length, 4);
    assert.deepEqual(readdirSync(parent), ['hs-map']);
  } finally { f.cleanup(); }
});

test('a foreign target appearing before first publication is preserved for review', () => {
  const f = fixture(); try {
    const parent = join(f.tracker, 'public'), target = join(parent, 'hs-map'), staged = join(parent, '.hs-map-package-stage-first'), backup = join(parent, '.hs-map-package-backup-first');
    mkdirSync(staged); writeFileSync(join(staged, 'partial.txt'), 'private');
    writeFileSync(join(parent, '.hs-map-package-journal.json'), JSON.stringify({ schema_version: 2, existed: false, target, staged, backup, package_hash: createHash('sha256').update('future').digest('hex') }));
    assert.throws(() => recoverPackage(f.tracker), /Ambiguous first package recovery/);
    assert.equal(readFileSync(join(target, 'old.txt'), 'utf8'), 'active');
    assert.equal(readFileSync(join(staged, 'partial.txt'), 'utf8'), 'private');
  } finally { f.cleanup(); }
});

test('the cross-project lease remains held until asynchronous publication settles', async () => {
  const f = fixture(); try {
    let release;
    const held = withMapPackageUpdate(f.tracker, () => new Promise(resolve => { release = resolve; }));
    assert.throws(() => publishPackage(f.candidate, f.tracker), /publication lock/);
    release(); await held;
    assert.equal(publishPackage(f.candidate, f.tracker).files.length, 4);
    await assert.rejects(withMapPackageUpdate(f.tracker, async () => { throw new Error('preparation failed'); }), /preparation failed/);
    assert.equal(publishPackage(f.candidate, f.tracker).files.length, 4);
  } finally { f.cleanup(); }
});
