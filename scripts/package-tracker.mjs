import { createHash, randomUUID } from 'node:crypto';
import { closeSync, cpSync, existsSync, linkSync, lstatSync, mkdirSync, mkdtempSync, openSync, readdirSync, readFileSync, realpathSync, renameSync, rmSync, unlinkSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const same = (a, b) => process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
function removeOwned(path, parent, prefix) {
  const absolute = resolve(path);
  if (!same(dirname(absolute), resolve(parent)) || !basename(absolute).startsWith(prefix) || lstatSync(absolute).isSymbolicLink()) throw new Error(`Unsafe package cleanup path: ${absolute}`);
  rmSync(absolute, { recursive: true });
}
function inventory(at, base = at, files = []) {
  for (const entry of readdirSync(at, { withFileTypes: true }).sort((a, b) => Buffer.compare(Buffer.from(a.name), Buffer.from(b.name)))) {
    const path = join(at, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Package contains a symbolic link: ${path}`);
    if (entry.isDirectory()) inventory(path, base, files);
    else if (entry.isFile()) { const bytes = readFileSync(path); files.push({ path: path.slice(base.length + 1).replaceAll('\\', '/'), sha256: hash(bytes), size: bytes.length }); }
    else throw new Error(`Unsupported package entry: ${path}`);
  }
  return files;
}

function paths(tracker) {
  tracker = realpathSync(tracker);
  if (!existsSync(join(tracker, 'package.json')) || !existsSync(join(tracker, 'src-tauri'))) throw new Error('Expected an HS Tracker checkout');
  const parent = join(tracker, 'public'); mkdirSync(parent, { recursive: true });
  if (!same(realpathSync(parent), parent)) throw new Error('Tracker public directory must not be redirected');
  const target = join(parent, 'hs-map');
  if (existsSync(target) && (lstatSync(target).isSymbolicLink() || !same(realpathSync(target), target))) throw new Error('Packaged map target must not be redirected');
  return { parent, target, journal: join(parent, '.hs-map-package-journal.json') };
}
function withPackageLock(parent, action, filename = '.hs-map-package.lock') {
  const path = join(parent, filename), token = randomUUID(), pending = `${path}.${token}`;
  writeFileSync(pending, JSON.stringify({ pid: process.pid, token }), { flag: 'wx' });
  const alive = pid => { try { process.kill(pid, 0); return true; } catch (error) { return error.code !== 'ESRCH'; } };
  try {
    try { linkSync(pending, path); }
    catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const previousText = readFileSync(path, 'utf8'), previous = JSON.parse(previousText);
      if (!Number.isSafeInteger(previous.pid) || previous.pid <= 0 || alive(previous.pid)) throw new Error('Another map package update owns the publication lock');
      const recovery = filename === '.hs-map-data.lock' ? join(parent, '.hs-map-lock-recovery') : path + '.recovery', guard = openSync(recovery, 'wx');
      try { if (readFileSync(path, 'utf8') !== previousText) throw new Error('Map package lock changed; retry'); unlinkSync(path); linkSync(pending, path); }
      finally { closeSync(guard); unlinkSync(recovery); }
    }
  } finally { unlinkSync(pending); }
  const release = () => { if (existsSync(path) && JSON.parse(readFileSync(path, 'utf8')).token === token) unlinkSync(path); };
  let result;
  try { result = action(); }
  catch (error) { release(); throw error; }
  if (result && typeof result.then === 'function') return Promise.resolve(result).finally(release);
  release();
  return result;
}

// The coordinator holds the data lock first, then this package lock, for its
// entire asynchronous transaction. A standalone packager uses the same order.
export function withMapPackageUpdate(tracker, action) {
  return withPackageLock(paths(tracker).parent, () => { recoverUnlocked(tracker); return action(); });
}
function recoverUnlocked(tracker, { rename = renameSync } = {}) {
  const { parent, target, journal } = paths(tracker);
  if (!existsSync(journal)) return false;
  if (lstatSync(journal).isSymbolicLink()) throw new Error('Package journal must not be redirected');
  const transaction = JSON.parse(readFileSync(journal, 'utf8'));
  const { staged, backup, package_hash } = transaction;
  if (![1, 2].includes(transaction.schema_version) || (transaction.schema_version === 2 && typeof transaction.existed !== 'boolean') || !same(transaction.target, target)
    || ![staged, backup].every(p => typeof p === 'string' && same(dirname(resolve(p)), parent))
    || !basename(staged).startsWith('.hs-map-package-stage-') || !basename(backup).startsWith('.hs-map-package-backup-')
    || !/^[0-9a-f]{64}$/.test(package_hash)) throw new Error('Invalid package recovery journal');
  for (const p of [staged, backup]) if (existsSync(p) && lstatSync(p).isSymbolicLink()) throw new Error('Package recovery directory must not be redirected');
  if (transaction.existed === false && (existsSync(backup) || (existsSync(target) && existsSync(staged)))) throw new Error('Ambiguous first package recovery; preserved all directories');
  if (existsSync(backup)) {
    if (!existsSync(target)) rename(backup, target);
    else if (!existsSync(staged) && hash(JSON.stringify(validatePackage(target))) === package_hash) removeOwned(backup, parent, '.hs-map-package-backup-');
    else throw new Error(`Ambiguous package recovery; preserved ${backup}`);
  } else if (!existsSync(target) && transaction.existed !== false) throw new Error('Package recovery cannot find the active map or its backup');
  else if (existsSync(target) && !existsSync(staged) && hash(JSON.stringify(validatePackage(target))) !== package_hash) throw new Error('Package recovery cannot verify the installed map');
  // A stage that still exists means publication never completed (or was rolled
  // back). The previous target is already restored before this removal.
  if (existsSync(staged)) removeOwned(staged, parent, '.hs-map-package-stage-');
  rmSync(journal);
  return true;
}
export function recoverPackage(tracker, options) { return withPackageLock(paths(tracker).parent, () => recoverUnlocked(tracker, options)); }

export function validatePackage(candidate) {
  const source = JSON.parse(readFileSync(join(candidate, 'data', 'source.json')));
  const map = JSON.parse(readFileSync(join(candidate, 'data', 'map.json')));
  if (!/^[0-9a-f]{64}$/.test(source.game?.fingerprint ?? source.fingerprint ?? '') || map.source?.fingerprint !== (source.game?.fingerprint ?? source.fingerprint)) throw new Error('Map package source fingerprint mismatch');
  const html = readFileSync(join(candidate, 'index.html'), 'utf8');
  const scripts = [...html.matchAll(/src="([^"]+\.js)"/g)].map(m => m[1]);
  if (!scripts.length || scripts.some(path => !path.startsWith('/hs-map/assets/') || !existsSync(join(candidate, path.slice('/hs-map/'.length))))) throw new Error('Map package entry point is not self-contained under /hs-map/');
  return { schema_version: 1, game_fingerprint: map.source.fingerprint,
    source_sha256: hash(readFileSync(join(candidate, 'data', 'source.json'))),
    files: inventory(candidate).filter(f => f.path !== 'package-manifest.json') };
}

export function publishPackage(candidate, tracker, options = {}) { return withPackageLock(paths(tracker).parent, () => publishUnlocked(candidate, tracker, options)); }
function publishUnlocked(candidate, tracker, { rename = renameSync } = {}) {
  recoverUnlocked(tracker, { rename });
  candidate = realpathSync(candidate);
  const { parent, target, journal } = paths(tracker);
  const report = validatePackage(candidate), token = randomUUID();
  const staged = join(parent, '.hs-map-package-stage-' + token), backup = join(parent, '.hs-map-package-backup-' + token);
  let old = false;
  try {
    cpSync(candidate, staged, { recursive: true, errorOnExist: true, force: false });
    const copied = validatePackage(staged);
    if (JSON.stringify(copied) !== JSON.stringify(report)) throw new Error('Map package changed while being copied');
    const temporaryJournal = journal + '.' + token + '.tmp';
    writeFileSync(temporaryJournal, JSON.stringify({ schema_version: 2, existed: existsSync(target), target, staged, backup, package_hash: hash(JSON.stringify(report)) }), { flag: 'wx' });
    renameSync(temporaryJournal, journal);
    if (existsSync(target)) { rename(target, backup); old = true; }
    try { rename(staged, target); }
    catch (error) {
      if (old) { rename(backup, target); old = false; }
      rmSync(journal);
      throw error;
    }
    if (old) { removeOwned(backup, parent, '.hs-map-package-backup-'); old = false; }
    rmSync(journal);
    return { target, ...report };
  } finally {
    if (!existsSync(journal) && existsSync(staged)) removeOwned(staged, parent, '.hs-map-package-stage-');
    // A failed rollback leaves its named backup intact for recovery.
  }
}

export function main(argv = process.argv.slice(2)) {
  let tracker = process.env.HS_TRACKER ?? resolve(root, '..', 'HeroSiege'), dry = false;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--tracker' && argv[i + 1]) tracker = resolve(argv[++i]);
    else if (argv[i] === '--dry') dry = true;
    else throw new Error(`Unknown package option: ${argv[i]}`);
  }
  return withPackageLock(root, () => {
  const stage = mkdtempSync(join(root, '.hs-map-stage-package-')), candidate = join(stage, 'docs');
  const result = spawnSync(process.execPath, [join(root, 'node_modules', 'vite', 'bin', 'vite.js'), 'build', '--base', '/hs-map/', '--outDir', candidate], { cwd: root, env: process.env, stdio: 'inherit' });
  if (result.status !== 0) throw new Error(`Map candidate build failed; retained ${stage}`);
  const report = validatePackage(candidate);
  writeFileSync(join(candidate, 'package-manifest.json'), JSON.stringify(report, null, 2) + '\n');
  if (dry) console.log(JSON.stringify({ candidate, ...report }, null, 2));
  else {
    const installed = publishPackage(candidate, tracker);
    console.log(JSON.stringify({ target: installed.target, game_fingerprint: installed.game_fingerprint, source_sha256: installed.source_sha256, files: installed.files.length }, null, 2));
    removeOwned(stage, root, '.hs-map-stage-package-');
  }
  }, '.hs-map-data.lock');
}

if (process.argv[1] && same(resolve(process.argv[1]), fileURLToPath(import.meta.url))) {
  try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
