import test from 'node:test';
import assert from 'node:assert/strict';
import { bridgeConfig, cameraState, cameraView, createMapBridge, validState } from '../../src/lib/map-bridge.js';

const state = () => ({ camera: { center: [.5, .5], scale: 1.35 }, viewport: { width: 1920, height: 1080 }, selection: { roomId: null }, presentation: { query: '', lang: 'en', source: null } });
const rooms = new Set(['Town_01_rm']);
const languages = new Set(['en', 'ru']);
const sources = new Set(['Amun Ra']);
function fixture(mode = 'source') {
  let now = 0, id = 0, current = state(); const tasks = new Map(), messages = [], listeners = new Map();
  const win = { parent: { postMessage: (message, origin) => messages.push({ message, origin }) }, performance: { now: () => now },
    setTimeout(fn, delay) { const key = ++id; tasks.set(key, { fn, at: now + delay }); return key; },
    clearTimeout: key => tasks.delete(key), requestAnimationFrame(fn) { return this.setTimeout(fn, 1); }, cancelAnimationFrame: key => tasks.delete(key),
    addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name),
  };
  const applied = [];
  const bridge = createMapBridge({ window: win, config: { mode, origin: 'http://tauri.localhost' }, rooms, languages, sources,
    read: () => current, apply: async s => { applied.push(s); current = s; },
  });
  return { bridge, messages, applied, set: s => { current = s; },
    async receive(state, revision = 1, origin = 'http://tauri.localhost', source = win.parent) { await listeners.get('message')?.({ origin, source, data: { channel: 'hs-map', version: 1, type: 'apply', revision, state } }); },
    advance(ms) { const until = now + ms; while (true) { const next = [...tasks].sort((a, b) => a[1].at - b[1].at)[0]; if (!next || next[1].at > until) break; now = next[1].at; tasks.delete(next[0]); next[1].fn(now); } now = until; },
  };
}

test('bridge opt-in requires an exact local parent origin', () => {
  assert.deepEqual(bridgeConfig('?mode=mirror&parentOrigin=http%3A%2F%2F127.0.0.1%3A5111'), { mode: 'mirror', origin: 'http://127.0.0.1:5111' });
  for (const origin of ['https://evil.test', 'http://localhost.evil.test', 'http://localhost/', 'http://user@localhost', 'null', '*']) assert.equal(bridgeConfig('?mode=mirror&parentOrigin=' + encodeURIComponent(origin)), null);
  assert.equal(bridgeConfig(''), null);
});

test('state validates finite camera, current room/language/source and exact fields', () => {
  const s = state(); assert.equal(validState(s, rooms, languages, sources), true);
  for (const change of [s => s.camera.scale = NaN, s => s.camera.center[0] = Infinity, s => s.selection.roomId = 'old_room', s => s.presentation.lang = 'tw', s => s.presentation.source = 'old_boss', s => { s.selection.roomId = 'Town_01_rm'; s.presentation.source = 'Amun Ra'; }, s => s.presentation.query = 'x'.repeat(257), s => s.command = 'invoke']) {
    const invalid = state(); change(invalid); assert.equal(validState(invalid, rooms, languages, sources), false);
  }
});

test('camera normalization round-trips and preserves world centre in another viewport', () => {
  const view = { x: -1152.85, y: 24, k: 1.35 }, map = { w: 2902, h: 800 }, viewport = { w: 1612, h: 1080 };
  const camera = cameraState(view, viewport, map), restored = cameraView(camera, viewport, map);
  assert.ok(Math.abs(restored.x - view.x) < 1e-9); assert.ok(Math.abs(restored.y - view.y) < 1e-9);
  assert.deepEqual(cameraState(cameraView(camera, { w: 1200, h: 900 }, map), { w: 1200, h: 900 }, map), camera);
});

test('source coalesces burst state, limits posts to 30Hz and cancels pending work', () => {
  const f = fixture(); f.advance(1);
  assert.equal(f.messages.filter(m => m.message.type === 'state').length, 1);
  for (let i = 0; i < 1000; i++) { const s = state(); s.camera.center[0] = .6 + i / 10000; f.set(s); f.bridge.changed(); }
  f.advance(31); assert.equal(f.messages.length, 2); f.advance(4);
  assert.equal(f.messages.length, 3); assert.equal(f.messages.at(-1).message.state.camera.center[0], .6999);
  f.set(state()); f.bridge.changed(); f.bridge.destroy(); f.advance(100); assert.equal(f.messages.length, 3);
});

test('mirror rejects foreign/stale/unknown state and never echoes applied changes', async () => {
  const f = fixture('mirror'), s = state(); s.selection.roomId = 'Town_01_rm'; s.presentation.lang = 'ru';
  await f.receive(s, 1, 'http://localhost:1234'); await f.receive(s, 1, 'http://tauri.localhost', {});
  assert.equal(f.applied.length, 0);
  await f.receive(s, 2); await f.receive(state(), 1); assert.equal(f.applied.length, 1);
  f.bridge.changed(); f.advance(100); assert.equal(f.messages.length, 1); assert.equal(f.messages[0].message.type, 'ready');
});

test('source restoration acknowledges its resulting viewport once, then emits later user movement', async () => {
  const f = fixture(); f.advance(1); const s = state(); s.camera.center[0] = .7;
  await f.receive(s, 4); f.bridge.changed(); f.advance(100); assert.equal(f.messages.length, 3);
  assert.equal(f.messages.at(-1).message.revision, 5);
  f.bridge.changed(); f.advance(100); assert.equal(f.messages.length, 3);
  const moved = structuredClone(s); moved.camera.center[0] = .8; f.set(moved); f.bridge.changed(); f.advance(100);
  assert.equal(f.messages.length, 4); assert.equal(f.messages.at(-1).message.state.camera.center[0], .8);
});
