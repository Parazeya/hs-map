// The same map document runs in Tracker and in its OBS mirror. No browser
// storage, Tracker commands, or arbitrary parent messages cross this boundary.
export const MAP_CHANNEL = 'hs-map';
export const MAP_VERSION = 1;
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value)
  && Object.keys(value).sort().join(',') === [...keys].sort().join(',');
const finite = (n, min, max) => typeof n === 'number' && Number.isFinite(n) && n >= min && n <= max;

export function bridgeConfig(search) {
  const p = new URLSearchParams(search);
  if (!['source', 'mirror'].includes(p.get('mode'))) return null;
  const origin = p.get('parentOrigin');
  try {
    const u = new URL(origin);
    if (u.origin !== origin || u.protocol !== 'http:' || !['tauri.localhost', 'localhost', '127.0.0.1'].includes(u.hostname)) return null;
    return { mode: p.get('mode'), origin };
  } catch { return null; }
}

export function validState(state, rooms, languages, sources) {
  if (!exact(state, ['camera', 'viewport', 'selection', 'presentation']) || !exact(state.camera, ['center', 'scale'])
      || !exact(state.viewport, ['width', 'height']) || !exact(state.selection, ['roomId'])
      || !exact(state.presentation, ['query', 'lang', 'source'])) return false;
  const { center, scale } = state.camera;
  return Array.isArray(center) && center.length === 2 && center.every(n => finite(n, -4, 4))
    && finite(scale, 1e-6, 1024)
    && ['width', 'height'].every(k => finite(state.viewport[k], 1, 32768))
    && (state.selection.roomId === null || typeof state.selection.roomId === 'string'
      && state.selection.roomId.length <= 128 && !/[\u0000-\u001f\u007f]/.test(state.selection.roomId)
      && (!rooms || rooms.has(state.selection.roomId)))
    && typeof state.presentation.query === 'string' && state.presentation.query.length <= 256
    && typeof state.presentation.lang === 'string' && /^[a-z]{2}$/.test(state.presentation.lang)
    && (!languages || languages.has(state.presentation.lang))
    && (state.presentation.source === null || typeof state.presentation.source === 'string'
      && state.presentation.source.length <= 128 && !/[\u0000-\u001f\u007f]/.test(state.presentation.source)
      && (!sources || sources.has(state.presentation.source)))
    && (state.selection.roomId === null || state.presentation.source === null);
}

export const cameraState = (view, viewport, map) => ({
  center: [(viewport.w / 2 - view.x) / (map.w * view.k), (viewport.h / 2 - view.y) / (map.h * view.k)],
  scale: view.k,
});
export const cameraView = (camera, viewport, map) => ({
  x: viewport.w / 2 - camera.center[0] * map.w * camera.scale,
  y: viewport.h / 2 - camera.center[1] * map.h * camera.scale,
  k: camera.scale,
});

export function createMapBridge({ window: win, config, read, apply, rooms, languages, sources }) {
  if (!config || win.parent === win) return { changed() {}, destroy() {} };
  let timer = 0, raf = 0, sentAt = -Infinity, revision = 0, appliedRevision = -1, last = '', dead = false;
  let applying = false, pending = null;
  const envelope = (type, rest = {}) => ({ channel: MAP_CHANNEL, version: MAP_VERSION, type, revision: ++revision, ...rest });
  const post = message => win.parent.postMessage(message, config.origin);
  function flush() {
    raf = 0;
    if (dead || applying || config.mode !== 'source') return;
    const state = read();
    if (!validState(state, rooms, languages, sources)) return;
    const signature = JSON.stringify(state);
    if (signature === last) return;
    last = signature;
    sentAt = win.performance.now();
    post(envelope('state', { state }));
  }
  function changed() {
    if (dead || config.mode !== 'source' || timer || raf) return;
    const delay = Math.max(0, 1000 / 30 - (win.performance.now() - sentAt));
    timer = win.setTimeout(() => { timer = 0; raf = win.requestAnimationFrame(flush); }, delay);
  }
  async function receive(event) {
    if (event.source !== win.parent || event.origin !== config.origin) return;
    const m = event.data;
    if (!exact(m, ['channel', 'version', 'type', 'revision', 'state']) || m.channel !== MAP_CHANNEL
      || m.version !== MAP_VERSION || m.type !== 'apply' || !Number.isSafeInteger(m.revision)
      || m.revision < 0 || m.revision <= appliedRevision || !validState(m.state, rooms, languages, sources)) return;
    appliedRevision = m.revision;
    revision = Math.max(revision, m.revision);
    // Applying a Hub snapshot must not generate a new source snapshot through
    // the component's selection effect or its next ResizeObserver delivery.
    pending = m.state;
    if (applying) return;
    applying = true;
    try {
      while (pending && !dead) {
        const next = pending;
        pending = null;
        await apply(next);
      }
      last = JSON.stringify(read());
    } finally { applying = false; }
    // Source receives apply only when its parent restores Hub state after a
    // reload. A single resulting snapshot acknowledges the actual viewport.
    // Ordinary source snapshots are forwarded to mirrors, never back here.
    if (!dead && config.mode === 'source') { last = ''; changed(); }
  }
  win.addEventListener('message', receive);
  post(envelope('ready'));
  changed();
  return { changed, destroy() { dead = true; if (timer) win.clearTimeout(timer); if (raf) win.cancelAnimationFrame(raf); win.removeEventListener('message', receive); } };
}
