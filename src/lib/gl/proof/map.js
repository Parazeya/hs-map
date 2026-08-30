// The whole world map, drawn by the ported renderer instead of by the DOM.
//
// This is the proof, not the product: WorldMap.svelte is not mine to change, so
// the port stands here beside it, on the same data, the same art and the same
// dev server, where the same harness can hover both and compare. Everything a
// reader sees is reproduced from the stylesheet it came from — the same easings
// and durations on the same four hover moves, the same six frames a second on
// the props, the same clamped pan, the same 34px hit box, the same names in the
// same places — because a picture that is nearly the map proves nothing.
//
// What is DOM here, and stays DOM: the names in eleven languages, the 72 hit
// targets a keyboard reaches, the focus ring. What is canvas: the map picture,
// the 54 links, the 20 props, the marker art, the zone flourish.
//
// A frame is four draw calls and the count is on the page.

import { load, asset, ART, nameOf } from '../../map.js';
import { speak } from '../../lang.js';
import {
  createContext, hasWebGL2, sizeCanvas, Renderer, View,
  packSheet, createTexture, loadImage, loadAll,
  buildQuads, createDynamicQuads, cellUV, stripUV,
  pointerPos, pickBox, rgb,
} from '../index.js';

// WorldMap.svelte's numbers, and the comments there say why each one is what it
// is. They are repeated and not reinvented: a proof that pans differently is
// not a proof of anything.
const MAX = 3, SLACK = 60, SHELF_TOP = 84, SHELF_BOTTOM = 84;
const HIT = 17;              // half of the 34x34 .node button, in world units
const BG = rgb('#100a13');   // theme.css's page background, behind the map
const FPS = 6;               // the game's rate, and every animation on this map

// The stylesheet's last rule, and it is not decoration: with reduce set, the
// props and the flourish do not play and the four hover moves do not tween.
// A renderer that ignored it would be putting motion back that a reader has
// asked the operating system to take away.
const STILL = matchMedia('(prefers-reduced-motion: reduce)');

const stage = document.querySelector('.stage');
const canvas = document.querySelector('canvas');
const world = document.querySelector('.world');
const hud = document.querySelector('.hud');
const find = document.querySelector('.find');

/**
 * There is no second renderer to hand the page back to here — in the component
 * this is `onfallback`, and the DOM map takes over. On this page saying so is
 * the honest thing; pretending to fall back to something that does not exist
 * would be a flag that lies.
 */
function giveUp(msg) {
  document.body.innerHTML = `<p class="broke">no GL: ${msg}<br>the component falls back to the DOM map here</p>`;
  throw new Error(msg);
}

const data = await load();

// The names in whichever of the eleven the reader is owed — the stored choice
// first, else the browser's, exactly as App.svelte picks it. They are the one
// thing on this map that stays DOM, so a port that only ever proved itself in
// English would not have proved the part that matters: a name is text, it is
// translated, it is selectable and it is read aloud, and none of that belongs
// in a texture.
const want = localStorage.getItem('hs-map.lang') || (navigator.language || 'en').slice(0, 2).toLowerCase();
const lang = data.langs.includes(want) ? want : 'en';
if (lang !== 'en') await speak(data, 'map', lang);

// ── art ─────────────────────────────────────────────────────────────────────
// The background is its own texture: at 2902x800 it would push the packed sheet
// past the 2048 that WebGL 2 guarantees, and it is one quad and one draw either
// way. The link tile is its own too, because it is the one thing here that
// REPEATS — a 300px path is that 16px tile nineteen times, which is a u running
// to 18.75 and a wrap mode, not nineteen quads.
const propArt = data.props.map((p) => p.art);
const sheetUrls = {};
for (const n of ['glow', 'node', 'dungeon', 'dungeonmark', 'town', 'node-ring', 'skull', 'fx-zone.12x6', ...propArt])
  sheetUrls[n] = asset(`img/${n}.webp`);

const [mapImg, linkImg, sheetImgs] = await Promise.all([
  loadImage(asset('img/map.webp')),
  loadImage(asset('img/link.webp')),
  loadAll(sheetUrls),
]);
if (!mapImg || !linkImg) giveUp('the art would not load');

if (!hasWebGL2()) giveUp('this browser has no WebGL 2');
const gl = createContext(canvas);
if (!gl) giveUp('the context would not open');
let r;
try {
  r = new Renderer(gl);
} catch (e) {
  giveUp(e.message); // a program that will not link is exactly what onfallback is for
}
canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); giveUp('the graphics context was lost'); });

const mapTex = createTexture(gl, mapImg);
const linkTex = createTexture(gl, linkImg, { wrapS: 'repeat' });
const sheet = packSheet(gl, sheetImgs);
const uvOf = (name) => cellUV(sheet.cell.get(name), sheet.w, sheet.h);
const cellOf = (name) => sheet.cell.get(name);

// ── the batches ─────────────────────────────────────────────────────────────
// One quad, and it never moves in world space.
const mapBatch = buildQuads(gl, [{
  x: data.map.w / 2, y: data.map.h / 2, w: data.map.w, h: data.map.h,
  u0: 0, v0: 0, u1: 1, v1: 1,
}], mapTex);

// The 54 paths, exactly as `paths` derives them: centre to centre, the tile
// repeating along the bar, the bar rotated about the node it leaves from. Half
// a length along the angle is where that rectangle's centre is (see writeQuad).
const nodeAt = Object.fromEntries(data.nodes.map((n) => [n.room, n]));
const [TILE_W, TILE_H] = data.linkTile;
const linkQuads = data.links.flatMap(([a, b]) => {
  const p = nodeAt[a], q = nodeAt[b];
  if (!p || !q) return [];
  const dx = q.x - p.x, dy = q.y - p.y;
  const len = Math.hypot(dx, dy), turn = Math.atan2(dy, dx);
  return [{
    x: p.x + Math.cos(turn) * len / 2, y: p.y + Math.sin(turn) * len / 2,
    w: len, h: TILE_H, turn,
    u0: 0, v0: 0, u1: len / TILE_W, v1: 1,
  }];
});
const linkBatch = buildQuads(gl, linkQuads, linkTex);

// The props are placed by their top-left in the DOM, so their centre is half a
// sprite in. Their UVs are all that changes, six times a second.
const spots = [];
for (const p of data.props) for (const [sx, sy] of p.at)
  spots.push({ p, cell: cellOf(p.art), x: sx + p.w / 2, y: sy + p.h / 2 });
const propBatch = createDynamicQuads(gl, spots.length, sheet.tex);

// Five pieces is the most a marker can carry — glow, flourish, pin, ring, skull.
const markerBatch = createDynamicQuads(gl, data.nodes.length * 5, sheet.tex);

const GLOW = uvOf('glow'), RING = uvOf('node-ring'), SKULL = uvOf('skull');
const FX = cellOf('fx-zone.12x6');
const PIN = {};
for (const [kind, art] of Object.entries(ART)) {
  const c = cellOf(art);
  PIN[kind] = { w: c.w, h: c.h, ...cellUV(c, sheet.w, sheet.h) };
}

// ── the hover, moved off CSS and reproduced exactly ──────────────────────────
/**
 * A CSS cubic-bezier as a function of progress. Newton on x, then read y — the
 * usual solve, and four iterations is inside a thousandth over 0..1.
 *
 * These are here because the transitions they drive are the ones the stylesheet
 * loses: --pin-k .1s ease-out and the other three. Running them with a
 * different curve would be a change a reader can see, which is the one thing
 * forbidden.
 */
function bezier(x1, y1, x2, y2) {
  const A = (a, b) => 1 - 3 * b + 3 * a, B = (a, b) => 3 * b - 6 * a, C = (a) => 3 * a;
  const at = (t, a, b) => ((A(a, b) * t + B(a, b)) * t + C(a)) * t;
  const slope = (t, a, b) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + C(a);
  return (p) => {
    if (p <= 0 || p >= 1) return p;
    let t = p;
    for (let i = 0; i < 4; i++) {
      const d = slope(t, x1, x2);
      if (!d) break;
      t -= (at(t, x1, x2) - p) / d;
    }
    return at(t, y1, y2);
  };
}
const EASE_OUT = bezier(0, 0, 0.58, 1);  // the four hover moves
const EASE = bezier(0.25, 0.1, 0.25, 1); // `transition: opacity .15s`, unnamed

/** one animatable number, with the from/to/at a CSS transition keeps */
class Tween {
  constructor(v, dur, ease) {
    this.v = this.from = this.to = v;
    this.dur = dur;
    this.ease = ease;
    this.t0 = -1;
  }
  set(to, now) {
    if (to === this.to) return;
    this.from = this.v;
    this.to = to;
    this.t0 = now;
  }
  at(now) {
    if (this.t0 < 0 || now >= this.t0 + this.dur) return (this.v = this.to);
    return (this.v = this.from + (this.to - this.from) * this.ease((now - this.t0) / this.dur));
  }
  get busy() { return this.v !== this.to; }
}

/** every duration here is the stylesheet's, or zero where it asks for stillness */
const ms = (n) => (STILL.matches ? 0 : n);

const st = data.nodes.map(() => ({
  pinK: new Tween(1, ms(100), EASE_OUT),      // .pin  transition: --pin-k .1s
  skullY: new Tween(-168, ms(100), EASE_OUT), // .skull            --skull-y .1s
  glowA: new Tween(0, ms(140), EASE_OUT),     // .glow             --glow-a .14s
  glowK: new Tween(0.6, ms(140), EASE_OUT),
  ringA: new Tween(0, ms(120), EASE_OUT),     // .ring             --ring-a .12s
  ringK: new Tween(0.8, ms(120), EASE_OUT),
  fade: new Tween(1, ms(150), EASE),          // .node.faded opacity .15s
  fxT0: -1,                               // when this marker's flourish started
}));

let hovered = null, active = null, matches = null, dragging = false;

/**
 * The stylesheet's cascade, as numbers.
 *
 * `.node.on .glow` and `.node.lit .glow` have the same specificity, so the
 * later rule wins where both apply — which is why `on` is tested first here.
 */
function retarget(now) {
  for (let i = 0; i < data.nodes.length; i++) {
    const n = data.nodes[i], s = st[i];
    const on = active?.room === n.room;
    const lit = on || hovered?.room === n.room;
    const hit = matches?.has(n.room);
    s.pinK.set(lit || hit ? 1.15 : 1, now);
    s.skullY.set(lit ? -190 : -168, now);
    s.glowA.set(on ? 0.85 : lit ? 0.55 : 0, now);
    s.glowK.set(on ? 1 : lit ? 0.8 : 0.6, now);
    s.ringA.set(lit ? 1 : 0, now);
    s.ringK.set(lit ? 1 : 0.8, now);
    s.fade.set(matches && !hit ? 0.45 : 1, now);
    // the flourish is added and removed rather than faded, and its two seconds
    // start when it is added — that is what {#if on || hit || lit} does
    const show = on || hit || lit;
    s.fxT0 = show ? (s.fxT0 < 0 ? now : s.fxT0) : -1;
  }
}

/**
 * The marker layer, in DOM order: for each node its glow, its flourish, its
 * pin, its ring, its skull, and then the next node's. That order is why all of
 * this is one packed sheet — an 80px glow reaches its neighbours, and drawing
 * every glow before every pin would be a different picture. See packSheet.
 *
 * A piece at alpha 0 is left out rather than drawn invisible: the DOM keeps a
 * transparent <img> there, and blending nothing over the map is the same map.
 * At rest that is 79 quads for 72 markers instead of 295.
 */
function markerQuads(now, frozen) {
  const out = [];
  for (let i = 0; i < data.nodes.length; i++) {
    const n = data.nodes[i], s = st[i];
    const fade = s.fade.at(now);
    const glowA = s.glowA.at(now) * fade, glowK = s.glowK.at(now);
    const pinK = s.pinK.at(now);
    const ringA = s.ringA.at(now) * fade, ringK = s.ringK.at(now);
    const skullY = s.skullY.at(now);
    if (glowA > 0.004)
      out.push({ x: n.x, y: n.y, w: 80 * glowK, h: 80 * glowK, ...GLOW, a: glowA });
    if (s.fxT0 >= 0) {
      // 12 frames of 137x113 every 139px — 137 and build.py's 2px gutter
      const f = frozen || STILL.matches ? 0 : Math.floor(((now - s.fxT0) / 1000) * FPS) % 12;
      out.push({ x: n.x, y: n.y, w: 137, h: 113, ...stripUV(FX, f, 137, 139, sheet.w, sheet.h), a: fade });
    }
    const p = PIN[n.kind];
    out.push({ x: n.x, y: n.y, w: p.w * pinK, h: p.h * pinK, u0: p.u0, v0: p.v0, u1: p.u1, v1: p.v1, a: fade });
    if (ringA > 0.004)
      out.push({ x: n.x, y: n.y, w: 24 * ringK, h: 24 * ringK, ...RING, a: ringA });
    // translate(-50%, var(--skull-y)%) on a 17px sprite whose box starts at the
    // marker's centre: the percentage is of its own height, so its centre lands
    // 17*(y/100) + 17/2 below the marker.
    if (n.boss)
      out.push({ x: n.x, y: n.y + 17 * (skullY / 100) + 8.5, w: 14, h: 17, ...SKULL, a: fade });
  }
  return out;
}

/** every prop at frame `tick`; frozen (a drag) parks them all on frame 0 */
function propQuads(tick) {
  return spots.map(({ p, cell, x, y }) => ({
    x, y, w: p.w, h: p.h,
    ...stripUV(cell, tick < 0 ? 0 : tick % p.n, p.w, p.step ?? p.w, sheet.w, sheet.h),
  }));
}

// ── the view, with WorldMap's own rules ─────────────────────────────────────
const view = new View();
let css = { x: 0, y: 0, k: 1 };
const floor = () => (stage.clientHeight ? stage.clientHeight / data.map.h : 0.4);

function clamped(v) {
  const vw = stage.clientWidth, vh = stage.clientHeight;
  const w = data.map.w * v.k, h = data.map.h * v.k;
  const x = w <= vw ? (vw - w) / 2 : Math.min(SLACK, Math.max(vw - w - SLACK, v.x));
  const a = SHELF_TOP, b = vh - SHELF_BOTTOM - h;
  const lo = Math.min(a, b) - SLACK, hi = Math.max(a, b) + SLACK;
  return { k: v.k, x, y: Math.min(hi, Math.max(lo, v.y)) };
}
function setView(v) {
  css = clamped(v);
  view.setCss(css.x, css.y, css.k);
  world.style.transform = `translate(${css.x}px, ${css.y}px) scale(${css.k})`;
  needDraw = true;
  schedule();
}
function fit() {
  const k = Math.min(MAX, floor());
  setView({ k, x: (stage.clientWidth - data.map.w * k) / 2, y: 0 });
}

// ── the DOM that stays DOM ──────────────────────────────────────────────────
// Built once and never touched again by a hover: the state a hover changes
// lives in the marker buffer, so nothing here restyles, relayouts or asks the
// compositor for anything while the pointer moves.
{
  const frag = document.createDocumentFragment();
  for (const n of data.nodes) {
    if (n.kind !== 'dungeons') { // its name would smudge into the boss dungeon's
      const t = document.createElement('span');
      t.className = 'tag' + (n.boss ? ' high' : '');
      t.style.left = n.x + 'px';
      t.style.top = n.y + 'px';
      t.textContent = nameOf(n, lang);
      t.dataset.room = n.room;
      frag.append(t);
    }
  }
  for (const n of data.nodes) {
    const b = document.createElement('button');
    b.className = 'node';
    b.style.left = n.x + 'px';
    b.style.top = n.y + 'px';
    b.setAttribute('aria-label', nameOf(n, lang));
    // the keyboard's path and only it, exactly as the component has it: a click
    // from a pointer is decided in the pointerup below and never arrives here
    b.onclick = (e) => { if (e.detail === 0) { active = active?.room === n.room ? null : n; schedule(); } };
    frag.append(b);
  }
  world.append(frag);
}

// ── pointer ─────────────────────────────────────────────────────────────────
let drag = null, pressed = null;
const nodeXY = (n) => [n.x, n.y];

stage.onpointerdown = (e) => {
  if (e.button !== 0) return;
  pressed = pickBox(data.nodes, pointerPos(canvas, e), view, nodeXY, HIT);
  drag = { id: e.pointerId, x: e.clientX, y: e.clientY, ox: css.x, oy: css.y, moved: 0 };
  stage.setPointerCapture(e.pointerId);
  dragging = true;
  stage.classList.add('dragging');
  schedule();
};
stage.onpointermove = (e) => {
  if (drag && e.pointerId === drag.id) {
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
    setView({ ...css, x: drag.ox + dx, y: drag.oy + dy });
    return;
  }
  const hit = pickBox(data.nodes, pointerPos(canvas, e), view, nodeXY, HIT);
  if (hit !== hovered) { hovered = hit; schedule(); }
};
const release = (e) => {
  if (!drag || e.pointerId !== drag.id) return;
  if (drag.moved < 4) active = pressed && active?.room !== pressed.room ? pressed : null;
  pressed = null;
  drag = null;
  dragging = false;
  stage.classList.remove('dragging');
  schedule();
};
stage.onpointerup = release;
stage.onpointercancel = release;
stage.onwheel = (e) => {
  e.preventDefault();
  const rect = stage.getBoundingClientRect();
  const px = e.clientX - rect.left, py = e.clientY - rect.top;
  const k = Math.max(floor(), Math.min(MAX, css.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
  if (k === css.k) return;
  setView({ k, x: px - (px - css.x) * (k / css.k), y: py - (py - css.y) * (k / css.k) });
};

find.oninput = () => {
  const q = find.value.trim().toLowerCase();
  matches = q ? new Set(data.nodes.filter((n) => nameOf(n, lang).toLowerCase().includes(q)).map((n) => n.room)) : null;
  for (const t of world.querySelectorAll('.tag'))
    t.classList.toggle('faded', !!matches && !matches.has(t.dataset.room));
  schedule();
};

// The drawing buffer is resized when the window is, and NOT on every frame.
// `sizeCanvas` reads clientWidth, and reading a layout property right after
// writing `.world`'s transform forces the layout it just invalidated — 150 of
// them in a 150-step drag, which is exactly the cost this port is here to stop
// paying.
let size = { w: 0, h: 0, dpr: 1 };
function measure() {
  size = sizeCanvas(canvas, stage);
  needDraw = true;
}
addEventListener('resize', () => { measure(); setView(css); });
// the setting can be changed while the page is open, and the frozen frame 0 has
// to give way to a moving one when it is
STILL.onchange = () => { needDraw = true; schedule(); };

// ── the frame ───────────────────────────────────────────────────────────────
let raf = 0, needDraw = true, propTick = -2, draws = 0, quads = 0, shown = '';
function schedule() { if (!raf) raf = requestAnimationFrame(frame); }

function frame(now) {
  raf = 0;
  retarget(now);
  // one clock for everything that moves: the props and the flourish are both
  // six frames a second, which is the rate the game plays them at
  const tick = dragging || STILL.matches ? -1 : Math.floor((now / 1000) * FPS);
  if (tick !== propTick) {
    propBatch.write(propQuads(tick));
    propTick = tick;
    needDraw = true;
  }
  let busy = false;
  for (const s of st)
    if (s.pinK.busy || s.skullY.busy || s.glowA.busy || s.glowK.busy ||
        s.ringA.busy || s.ringK.busy || s.fade.busy) { busy = true; break; }
  const anyFx = st.some((s) => s.fxT0 >= 0);
  if (busy || anyFx || needDraw) {
    const q = markerQuads(now, dragging);
    quads = q.length + spots.length + linkQuads.length + 1;
    markerBatch.write(q);
    needDraw = true;
  }
  if (needDraw) {
    r.begin({ ...size, clear: BG });
    // back to front, and this list IS the DOM order it replaces
    r.sprites(view.uniform, [mapBatch, propBatch, linkBatch, markerBatch]);
    draws = r.end();
    needDraw = false;
    const line = `${draws} draw calls\n${quads} sprites\n${sheet.w}x${sheet.h} sheet`;
    if (line !== shown) hud.textContent = shown = line; // never a DOM write per frame
  }
  // keep the clock while anything is moving: the props always are, unless a
  // drag has taken their animation away
  if (busy || (!STILL.matches && (anyFx || !dragging))) schedule();
}

// A view in the URL, `#x,y,k`, so a harness can put this page on exactly the
// pixels the DOM map is on and diff the two. It goes through the same clamp as
// every other view, so a hash cannot park the map somewhere a drag could not.
measure();
const hash = location.hash.slice(1).split(',').map(Number);
if (hash.length === 3 && hash.every(Number.isFinite)) setView({ x: hash[0], y: hash[1], k: hash[2] });
else fit();

window.__gl = () => ({ draws, quads, sheet: [sheet.w, sheet.h], k: css.k, x: css.x, y: css.y });
// The harness masks the props out of a whole-frame comparison, and on this page
// there is no .prop element for it to find — so the boxes come from here, in
// the same screen coordinates getBoundingClientRect would have given.
window.__boxes = () => {
  const out = [];
  const put = (kind, x, y, w, h) => {
    const [sx, sy] = view.toScreen(x, y);
    out.push({ kind, x: sx, y: sy, w: w * css.k, h: h * css.k });
  };
  for (const { p, x, y } of spots) put('prop', x - p.w / 2, y - p.h / 2, p.w, p.h);
  for (const n of data.nodes) put('node', n.x - 17, n.y - 17, 34, 34);
  for (const l of linkQuads) put('link', l.x - l.w / 2, l.y - l.h / 2, l.w, l.h);
  return { boxes: out, vw: innerWidth, vh: innerHeight };
};
