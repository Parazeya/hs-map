import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const local = join(root, '..', 'HeroSiege Extractor', '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON || (existsSync(local) ? local : 'python');
try {
  execFileSync(python, process.argv.slice(2), { cwd: root, stdio: 'inherit', windowsHide: true });
} catch (error) {
  if (error.code === 'ENOENT') console.error(`Python was not found: ${python}. Set PYTHON to an interpreter with requirements.txt installed.`);
  process.exitCode = error.status ?? 1;
}
