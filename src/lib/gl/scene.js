// The world map's picture, drawn by the renderer instead of by the compositor.
//
// WHY THIS EXISTS. Hovering a marker made Chrome re-rasterise the whole scaled
// map layer with a different filter: an 80x80 patch of map art went from 132
// distinct colours at rest to 1,278, page-wide, for 43% of the frames of a
// hover-leave-hover cycle. `image-rendering: pixelated` is a request the
// compositor does not have to honour, and nine attempts at the CSS level —
// containment, will-change, promoting the box, promoting the layer, two device
// pixel ratios, two GPUs — did not move it by a single frame. A texture the
// renderer samples itself cannot be resampled behind its back.
//
// WHAT IS HERE and what is not: everything on the map that was a picture — the
// 2902x800 background, the 54 link bars, the 20 animated props, the marker art
// and the twelve-frame zone flourish. The names, the tooltip and the 72
// keyboard targets stay DOM in WorldMap.svelte, positioned by the same view.
//
// TWO CANVASES, AND THE REASON IS THE PAINT ORDER. In the DOM the 63 labels are
// written before the 72 markers, so a marker's 80px glow covers the label above
// it and tints it red on hover. A DOM layer cannot be sandwiched inside one
// canvas, so the map, the props and the links are three draws on an opaque
// canvas UNDER the labels, and the marker layer is one draw on a see-through
// canvas OVER them. Four draws a frame, against the 433 elements inside .world.
//
// Every number a reader can see is the stylesheet's own: the same easings and
// durations on the same four hover moves, six frames a second on the props and
// the flourish, the frames frozen while a drag runs, the 34px hit box, the
// nearest-neighbour sampling. A picture that is nearly the map proves nothing.

import {
  createContext, sizeCanvas, Renderer, View,
  packSheet, createTexture, loadImage, loadAll,
  buildQuads, createDynamicQuads, cellUV, stripUV,
  createTarget, freeTarget, freeObject, freeTexture, pickBox, rgb,
} from './index.js';
import { ART } from '../map.js';

/** half of the 34x34 .node button, in world units */
const HIT = 17;
/** the page's own background, behind a map that does not always fill the stage */
const BG = rgb('#100a13');
/** the game's rate, and every animation on this map runs at it */
const FPS = 6;
/** the marker canvas clears to nothing at all: the labels are under it */
const CLEAR_OVER = [0, 0, 0, 0];
/** what a marker can carry: glow, flourish, pin, ring, skull */
const PIECES = 5;

/**
 * A CSS cubic-bezier as a function of progress: Newton on x, then read y.
 * Four iterations is inside a thousandth over 0..1.
 *
 * These are here because the transitions they drive are the ones the stylesheet
 * loses when the marker art leaves the DOM — `--pin-k .1s ease-out` and the
 * three beside it. A different curve is a change a reader can see.
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

/**
 * One animatable number with the from/to/at a CSS transition keeps.
 *
 * The duration is given to `set` and not to the constructor, because two of
 * these have no single duration. `.node.faded` declares its transition INSIDE
 * the rule, so it eases in over .15s and snaps back the instant the class goes;
 * and `prefers-reduced-motion` takes the transition off `.pin` and `.glow`
 * while leaving it on `.ring` and `.skull`, and a reader can change that
 * setting with the page open.
 */
class Tween {
  constructor(v) {
    this.v = this.from = this.to = v;
    this.dur = 0;
    this.t0 = -1;
  }
  set(to, now, dur) {
    if (to === this.to) return;
    this.from = this.v;
    this.to = to;
    this.dur = dur;
    this.t0 = now;
  }
  at(now, ease) {
    if (this.t0 < 0 || !this.dur || now >= this.t0 + this.dur) return (this.v = this.to);
    return (this.v = this.from + (this.to - this.from) * ease((now - this.t0) / this.dur));
  }
  get busy() { return this.v !== this.to; }
}

/**
 * Build the scene. Throws if this machine cannot draw it — a refused context, a
 * program that will not link, a driver whose largest texture is smaller than
 * the map — and the caller falls back to the DOM map, which is still there.
 *
 * @param base    the opaque canvas, under the labels
 * @param over    the see-through canvas, over them
 * @param stage   the element both are stretched across
 * @param asset   the site's stamped URL builder
 * @param onFail  called if the scene dies after it started (a lost context)
 * @param onCount called when the draw-count line changes, never per frame
 */
export function createScene({ data, base, over, stage, asset, onFail, onCount }) {
  // Two contexts, and each uploads only what it draws — the base has the
  // background, the trail tile and the prop strips, the overlay has the marker
  // sheet, and nothing is held twice.
  const gl = createContext(base);
  const gl2 = createContext(over, { alpha: true });
  if (!gl || !gl2) throw new Error('WebGL 2 context refused');

  // WebGL 2 only guarantees 2048, and the background is 2902 wide. Every
  // desktop driver and every GLES 3 phone gives 4096 or more, but a machine
  // that gave 2048 would silently draw a black map, and a black map is worse
  // than the DOM one this falls back to.
  const cap = gl.getParameter(gl.MAX_TEXTURE_SIZE);
  if (cap < data.map.w) throw new Error(`largest texture is ${cap}, the map is ${data.map.w}`);

  const r = new Renderer(gl);   // throws with the driver's own log; see program.js
  const r2 = new Renderer(gl2);

  let dead = false;
  const die = (why) => { if (!dead) { dead = true; onFail?.(why); } };
  const lost = (e) => { e.preventDefault(); die('the graphics context was lost'); };
  base.addEventListener('webglcontextlost', lost);
  over.addEventListener('webglcontextlost', lost);

  // ── the view ──────────────────────────────────────────────────────────────
  // The pan and zoom RULES live in the component, where they are written down;
  // this only holds the answer and turns it into a uniform.
  const view = new View();
  let css = { x: 0, y: 0, k: 1 };

  // ── what a frame is drawn from ────────────────────────────────────────────
  const STILL = matchMedia('(prefers-reduced-motion: reduce)');
  let hovered = null, active = null, matches = null, dragging = false;

  /**
   * The five facts a frame needs about a marker, copied out of the records
   * once.
   *
   * `data` is the component's reactive state, so every `n.x` on it is a proxy
   * read — 72 markers times ten reads is 720 of them a frame, sixty times a
   * second, for numbers that never change. The names DO change, when the reader
   * picks one of the other ten languages and `speak()` grafts them onto these
   * same records, but a name is never drawn here: it is DOM, above the canvas.
   */
  const nodes = data.nodes.map((n) => ({ room: n.room, x: n.x, y: n.y, kind: n.kind, boss: !!n.boss }));

  const st = nodes.map(() => ({
    pinK: new Tween(1),      // .pin    --pin-k   .1s  ease-out
    skullY: new Tween(-168), // .skull  --skull-y .1s  ease-out
    glowA: new Tween(0),     // .glow   --glow-a  .14s ease-out
    glowK: new Tween(0.6),   //         --glow-k  .14s
    ringA: new Tween(0),     // .ring   --ring-a  .12s ease-out
    ringK: new Tween(0.8),   //         --ring-k  .12s
    fade: new Tween(1),      // .node.faded opacity .15s, one way only
    fxT0: -1,                // when this marker's flourish was added
  }));

  // ── art ───────────────────────────────────────────────────────────────────
  // Four arrivals, each drawn the moment it lands. The DOM map paints the
  // background as soon as map.webp is decoded and fills the markers in as their
  // own files arrive; waiting for all 26 before the first frame would put a
  // blank stage where a map used to be for as long as the biggest file takes.
  let mapTex = null, linkTex = null, propSheet = null, markSheet = null;
  let mapBatch = null, linkBatch = null, propBatch = null, markerBatch = null;
  // the second pass a faded marker needs, and the quad that puts it back
  let groupBatch = null, blitBatch = null, target = null;
  let spots = [], PIN = {}, GLOW = null, RING = null, SKULL = null, FX = null;
  let sheetSize = '…';

  const nodeAt = Object.fromEntries(nodes.map((n) => [n.room, n]));
  const [TILE_W, TILE_H] = data.linkTile;

  loadImage(asset('img/map.webp')).then((img) => {
    if (dead || !img) return;
    mapTex = createTexture(gl, img);
    mapBatch = buildQuads(gl, [{
      x: data.map.w / 2, y: data.map.h / 2, w: data.map.w, h: data.map.h,
      u0: 0, v0: 0, u1: 1, v1: 1,
    }], mapTex);
    redraw();
  });

  loadImage(asset('img/link.webp')).then((img) => {
    if (dead || !img) return;
    // The one thing on this map that REPEATS: a 300px path is the 16px trail
    // tile nineteen times, which is a u running to 18.75 and a wrap mode, not
    // nineteen quads. The bar rotates about the node it leaves from, and half a
    // length along the angle is where that rectangle's centre is (writeQuad).
    linkTex = createTexture(gl, img, { wrapS: 'repeat' });
    const bars = data.links.flatMap(([a, b]) => {
      const p = nodeAt[a], q = nodeAt[b];
      if (!p || !q) return [];
      const dx = q.x - p.x, dy = q.y - p.y;
      const len = Math.hypot(dx, dy), turn = Math.atan2(dy, dx);
      return [{
        x: p.x + Math.cos(turn) * len / 2, y: p.y + Math.sin(turn) * len / 2,
        w: len, h: TILE_H, turn, u0: 0, v0: 0, u1: len / TILE_W, v1: 1,
      }];
    });
    linkBatch = buildQuads(gl, bars, linkTex);
    redraw();
  });

  const propUrls = {};
  for (const p of data.props) propUrls[p.art] = asset(`img/${p.art}.webp`);
  loadAll(propUrls, { alive: () => !dead }).then((imgs) => {
    if (dead || !imgs.length) return;
    propSheet = packSheet(gl, imgs);
    // A prop is placed by its top-left in the DOM, so its centre is half a
    // sprite in. Its UVs are all that changes, six times a second.
    for (const p of data.props) {
      const cell = propSheet.cell.get(p.art);
      if (!cell) continue;
      for (const [sx, sy] of p.at) spots.push({ p, cell, x: sx + p.w / 2, y: sy + p.h / 2 });
    }
    propBatch = createDynamicQuads(gl, spots.length, propSheet.tex);
    propTick = -2; // so the first frame writes it
    redraw();
  });

  const markUrls = {};
  for (const n of ['glow', 'node-ring', 'skull', 'fx-zone.12x6', ...new Set(Object.values(ART))])
    markUrls[n] = asset(`img/${n}.webp`);
  loadAll(markUrls, { alive: () => !dead }).then((imgs) => {
    if (dead || !imgs.length) return;
    markSheet = packSheet(gl2, imgs);
    const uv = (name) => cellUV(markSheet.cell.get(name), markSheet.w, markSheet.h);
    GLOW = uv('glow'); RING = uv('node-ring'); SKULL = uv('skull');
    FX = markSheet.cell.get('fx-zone.12x6');
    // The four pins carry no width or height in the markup, so each draws at
    // its own intrinsic size — 24, 24, 22 and 26. One box for all four moves
    // seventeen markers.
    for (const [kind, art] of Object.entries(ART)) {
      const c = markSheet.cell.get(art);
      if (c) PIN[kind] = { w: c.w, h: c.h, ...cellUV(c, markSheet.w, markSheet.h) };
    }
    markerBatch = createDynamicQuads(gl2, nodes.length * PIECES, markSheet.tex);
    groupBatch = createDynamicQuads(gl2, PIECES, markSheet.tex);
    sheetSize = `${markSheet.w}x${markSheet.h}`;
    redraw();
  });

  // ── the stylesheet's cascade, as numbers ──────────────────────────────────
  /**
   * `.node.on .glow` is written after `.node.lit .glow` and an active marker
   * carries both classes, so `on` wins the glow — which is why it is tested
   * first here. The rest is value for value what the rules say.
   *
   * The reduced-motion rule takes the transition off `.pin` and `.glow` ONLY.
   * The ring, the skull and the two fades still tween with it set; tidying that
   * up would change what a reader who asked for stillness gets.
   */
  function retarget(now) {
    const still = STILL.matches;
    const hover = still ? 0 : 100, glow = still ? 0 : 140;
    const onRoom = active?.room, litRoom = hovered?.room;
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i], s = st[i];
      const on = onRoom === n.room;
      const lit = on || litRoom === n.room;
      const hit = matches?.has(n.room);
      s.pinK.set(lit || hit ? 1.15 : 1, now, hover);
      s.skullY.set(lit ? -190 : -168, now, 100);
      s.glowA.set(on ? 0.85 : lit ? 0.55 : 0, now, glow);
      s.glowK.set(on ? 1 : lit ? 0.8 : 0.6, now, glow);
      s.ringA.set(lit ? 1 : 0, now, 120);
      s.ringK.set(lit ? 1 : 0.8, now, 120);
      // One way. The transition is declared inside `.node.faded`, so adding the
      // class eases the marker back over .15s and removing it takes the
      // declaration away with it and the opacity snaps.
      const dim = matches && !hit;
      s.fade.set(dim ? 0.45 : 1, now, dim ? 150 : 0);
      // the flourish is added and removed rather than faded, and its two
      // seconds start when it is added — that is what {#if on || hit || lit} did
      const show = on || hit || lit;
      s.fxT0 = show ? (s.fxT0 < 0 ? now : s.fxT0) : -1;
    }
  }

  /**
   * The marker layer, in DOM order: each node's glow, flourish, pin, ring and
   * skull, then the next node's. That order is why this is one packed sheet —
   * an 80px glow reaches its neighbours, and drawing every glow before every
   * pin would be a different picture.
   *
   * A piece at alpha 0 is left out rather than drawn invisible: the DOM keeps a
   * transparent <img> there, and blending nothing over the map is the same map.
   * At rest that is 79 quads for 72 markers instead of 295.
   */
  const marks = [];
  /**
   * The markers that have to be composited before they are faded.
   *
   * `.node.faded` is `opacity: .45` on the button, and a CSS opacity on an
   * element with children fades the children as ONE picture. So a faded marker
   * with more than one piece — a glow under its own pin, a skull overlapping
   * it — is drawn into a target first and then drawn once at the fade. One
   * piece cannot overlap itself, so a lone pin needs none of that and takes the
   * ordinary path. See target.js for what it costs and what it fixes.
   */
  const groups = [];
  function markerQuads(now) {
    marks.length = 0;
    groups.length = 0;
    const frozen = dragging || STILL.matches;
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i], s = st[i];
      const was = marks.length;
      const fade = s.fade.at(now, EASE);
      const glowA = s.glowA.at(now, EASE_OUT) * fade, glowK = s.glowK.at(now, EASE_OUT);
      const pinK = s.pinK.at(now, EASE_OUT);
      const ringA = s.ringA.at(now, EASE_OUT) * fade, ringK = s.ringK.at(now, EASE_OUT);
      const skullY = s.skullY.at(now, EASE_OUT);
      if (glowA > 0.004)
        marks.push({ x: n.x, y: n.y, w: 80 * glowK, h: 80 * glowK, ...GLOW, a: glowA });
      if (s.fxT0 >= 0 && FX) {
        // 12 frames of 137x113 every 139px — 137 and build.py's 2px gutter
        const f = frozen ? 0 : Math.floor(((now - s.fxT0) / 1000) * FPS) % 12;
        marks.push({ x: n.x, y: n.y, w: 137, h: 113, ...stripUV(FX, f, 137, 139, markSheet.w, markSheet.h), a: fade });
      }
      const p = PIN[n.kind];
      if (p) marks.push({ x: n.x, y: n.y, w: p.w * pinK, h: p.h * pinK, u0: p.u0, v0: p.v0, u1: p.u1, v1: p.v1, a: fade });
      if (ringA > 0.004)
        marks.push({ x: n.x, y: n.y, w: 24 * ringK, h: 24 * ringK, ...RING, a: ringA });
      // translate(-50%, var(--skull-y)%) on a 17px sprite whose box starts at
      // the marker's centre: the percentage is of its own height, so its centre
      // lands 17*(y/100) + 8.5 below it. -168 is -20.06 px, -190 is -23.8.
      if (n.boss) marks.push({ x: n.x, y: n.y + 17 * (skullY / 100) + 8.5, w: 14, h: 17, ...SKULL, a: fade });
      // Only when something translucent is in the stack. A faded marker whose
      // pieces are just its pin and its skull needs no second pass: at rest the
      // skull's box overlaps the pin's by 0.44px and both are opaque there, and
      // grouping all seven boss markers as well changed not one pixel of the
      // page at a threshold of 8/255 while costing thirteen more draw calls.
      if (fade < 1 && marks.length - was > 1 && (glowA > 0.004 || s.fxT0 >= 0 || ringA > 0.004)) {
        // its pieces come out of the run and are drawn at their own alphas into
        // the target, then put back at exactly this point in the order
        const pieces = marks.splice(was, marks.length - was).map((q) => ({ ...q, a: q.a / fade }));
        groups.push({ at: was, pieces, fade, x: n.x, y: n.y });
      }
    }
    return marks;
  }

  /** every prop at frame `tick`; a drag parks them all on frame 0 */
  const torches = [];
  function propQuads(tick) {
    torches.length = 0;
    for (const { p, cell, x, y } of spots)
      torches.push({
        x, y, w: p.w, h: p.h,
        ...stripUV(cell, tick < 0 ? 0 : tick % p.n, p.w, p.step ?? p.w, propSheet.w, propSheet.h),
      });
    return torches;
  }

  // ── the frame ─────────────────────────────────────────────────────────────
  // The drawing buffers are resized when the window is and NOT inside a draw:
  // sizeCanvas reads clientWidth, and reading a layout property straight after
  // writing .world's transform forces the layout it just invalidated — 150 of
  // them in a 150-step drag, which is the cost this port exists to stop paying.
  let size = { w: 0, h: 0, dpr: 1 };
  // Where the canvas is on screen, read when it is measured and not when the
  // pointer moves. This is pointerPos's arithmetic — including the divide by
  // the effective CSS zoom, without which a hit test drifts by a tenth of the
  // distance from the canvas origin — with its getBoundingClientRect hoisted
  // out, for the same reason sizeCanvas is not called inside the draw: reading
  // a layout property straight after writing .world's transform forces the
  // layout that write invalidated, and a drag does it 150 times.
  let rect = { left: 0, top: 0, z: 1 };
  let raf = 0, needBase = true, needOver = true, propTick = -2, lastFx = 0, shown = '';
  // What the picture on screen cost, kept per canvas rather than per frame. A
  // resting frame steps the props and touches the base alone, and the marker
  // canvas keeps showing its last commit until something on it moves — so the
  // number worth putting on the page is what the whole picture takes, which is
  // these two added up and not whichever of them ran last.
  let dBase = 0, dOver = 0, sprites = 0;

  const schedule = () => { if (!raf && !dead) raf = requestAnimationFrame(frame); };
  const redraw = () => { needBase = needOver = true; schedule(); };

  /**
   * One faded marker, composited and then faded — what `opacity: .45` on its
   * button did.
   *
   * The scissor is the whole cost control: the target is the size of the
   * drawing buffer so the blit back is a full-screen quad landing texel on
   * texel, and the clear, the group and the blit are all clipped to this one
   * marker's box. The box is the flourish's 137x113 plus a pixel, which is the
   * furthest any piece of a marker reaches.
   *
   * If the target cannot be made — a driver that will not give a framebuffer —
   * the marker is drawn piece by piece instead. That is the picture this is
   * here to correct, but it is the whole marker in the right place, which is
   * worth more than a hole.
   */
  function drawGroup(g) {
    if (!target) {
      target = createTarget(gl2, gl2.drawingBufferWidth, gl2.drawingBufferHeight);
      if (target) {
        blitBatch ??= createDynamicQuads(gl2, 1, target.tex);
        blitBatch.tex = target.tex; // a new buffer size is a new texture
      }
    }
    if (!target || !groupBatch || !blitBatch) {
      // no target: the pieces one at a time, which is the picture this method
      // exists to correct but is still the whole marker in the right place
      groupBatch?.write(g.pieces.map((q) => ({ ...q, a: q.a * g.fade })));
      r2.sprites(view.uniform, [groupBatch]);
      return;
    }
    // the marker's box, in the drawing buffer's own pixels, counted from the
    // bottom because that is where a framebuffer's first row is
    const [sx, sy] = view.toScreen(g.x, g.y);
    const k = 1 / view.scaling, d = size.dpr, H = target.h;
    const x0 = Math.max(0, Math.floor((sx - 69.5 * k) * d));
    const x1 = Math.min(target.w, Math.ceil((sx + 69.5 * k) * d));
    const y0 = Math.max(0, Math.floor(H - (sy + 57.5 * k) * d));
    const y1 = Math.min(H, Math.ceil(H - (sy - 57.5 * k) * d));
    if (x1 <= x0 || y1 <= y0) return; // wholly off screen
    gl2.enable(gl2.SCISSOR_TEST);
    gl2.scissor(x0, y0, x1 - x0, y1 - y0);
    gl2.bindFramebuffer(gl2.FRAMEBUFFER, target.fb);
    gl2.clearColor(0, 0, 0, 0);
    gl2.clear(gl2.COLOR_BUFFER_BIT);
    groupBatch.write(g.pieces);
    r2.sprites(view.uniform, [groupBatch]);
    gl2.bindFramebuffer(gl2.FRAMEBUFFER, null);
    // the whole canvas as one quad, in world units, so the tap is an identity;
    // v runs 1 to 0 because a framebuffer's first row is the bottom of the page
    const s = view.scaling;
    blitBatch.write([{
      x: (size.w / 2) * s - view.ox, y: (size.h / 2) * s - view.oy,
      w: size.w * s, h: size.h * s,
      u0: 0, v0: 1, u1: 1, v1: 0, a: g.fade,
    }]);
    r2.sprites(view.uniform, [blitBatch], { straight: false });
    gl2.disable(gl2.SCISSOR_TEST);
  }

  function frame(now) {
    raf = 0;
    if (dead) return;
    retarget(now);

    // one clock for everything that moves: the props and the flourish are both
    // six frames a second, the rate the game plays them at
    const tick = dragging || STILL.matches ? -1 : Math.floor((now / 1000) * FPS);
    if (propBatch && tick !== propTick) {
      propBatch.write(propQuads(tick));
      propTick = tick;
      needBase = true;
    }

    // A flourish is twelve frames at six a second, and a marker whose tween has
    // settled is not moving at all — so the marker layer is rewritten when one
    // of its numbers actually changed, not on every animation frame. Without
    // this the overlay committed sixty times a second for a picture that moves
    // six, and the compositor duly re-composited the page each time: the far
    // markers metric read 396 changed pixels a frame instead of 271.
    let busy = false, anyFx = false, fxKey = 0;
    for (const s of st) {
      if (s.fxT0 >= 0) { anyFx = true; fxKey = fxKey * 13 + Math.floor((now - s.fxT0) * FPS / 1000); }
      if (s.pinK.busy || s.skullY.busy || s.glowA.busy || s.glowK.busy ||
          s.ringA.busy || s.ringK.busy || s.fade.busy) busy = true;
    }
    if (markerBatch && (busy || needOver || fxKey !== lastFx)) {
      markerBatch.write(markerQuads(now));
      lastFx = fxKey;
      needOver = true;
    }

    if (needBase) {
      r.begin({ ...size, clear: BG });
      // back to front, and this list IS the DOM order it replaces
      r.sprites(view.uniform, [mapBatch, propBatch, linkBatch]);
      dBase = r.end();
      needBase = false;
    }
    if (needOver) {
      r2.begin({ ...size, clear: CLEAR_OVER });
      // The marker layer in DOM order, with each faded marker taken out of the
      // run, composited on its own and put back where it stood.
      let from = 0;
      for (const g of groups) {
        if (g.at > from) r2.sprites(view.uniform, [{ ...markerBatch, first: from * 6, count: (g.at - from) * 6 }]);
        from = g.at;
        drawGroup(g);
      }
      if (markerBatch && markerBatch.count > from * 6)
        r2.sprites(view.uniform, [{ ...markerBatch, first: from * 6, count: markerBatch.count - from * 6 }]);
      dOver = r2.end();
      needOver = false;
    }
    sprites = (mapBatch ? 1 : 0) + spots.length
      + (linkBatch ? linkBatch.count / 6 : 0) + (markerBatch ? markerBatch.count / 6 : 0);
    const line = `${dBase + dOver} draw calls · ${sprites} sprites · sheets ${sheetSize}`;
    if (line !== shown) onCount?.((shown = line)); // never a DOM write per frame

    // keep the clock while anything is moving: the props always are, unless a
    // drag or the reader's own setting has taken their animation away
    if (busy || (!STILL.matches && (anyFx || !dragging))) schedule();
  }

  // the setting can be changed with the page open, and a frozen frame 0 has to
  // give way to a moving one when it is
  STILL.onchange = redraw;

  // ── what the component asks of it ─────────────────────────────────────────
  return {
    /** the pan and zoom the component decided, as one uniform and a redraw */
    setView(x, y, k) {
      css = { x, y, k };
      view.setCss(x, y, k);
      redraw();
    },
    /** hover, click, search and drag — everything the picture is drawn from */
    setState(s) {
      hovered = s.hovered; active = s.active; matches = s.matches; dragging = s.dragging;
      redraw();
    },
    resize() {
      size = sizeCanvas(base, stage);
      sizeCanvas(over, stage);
      const r = base.getBoundingClientRect();
      rect = { left: r.left, top: r.top, z: (r.width / (base.clientWidth || 1)) || 1 };
      // the group target is the drawing buffer's size, so a new buffer needs a
      // new one; it is remade on demand rather than here, since most sessions
      // never fade a marker at all
      target = freeTarget(gl2, target);
      redraw();
    },
    /**
     * The marker under the pointer: a 34x34 BOX in world units, and the LAST
     * match wins. Both are what the DOM did — the button is a square and two
     * markers here are 30 units apart, so their boxes overlap in a 4-unit band
     * that document order gives to the later one. A radius test would answer
     * differently at a marker's corners and hand that band the other way.
     */
    pick(e) {
      // over the live records and not the copy above: what comes back is handed
      // straight to `hovered`, and the tooltip beside the map reads a node's
      // name, act, code and drop table off it
      const at = { mx: (e.clientX - rect.left) / rect.z, my: (e.clientY - rect.top) / rect.z };
      return pickBox(data.nodes, at, view, (n) => [n.x, n.y], HIT);
    },
    /**
     * The props and the links as screen boxes. The measuring harnesses mask the
     * props out of a whole-frame comparison and name a changed pixel by what it
     * fell on, and there is no element left for getBoundingClientRect to find.
     */
    boxes() {
      const out = [];
      const put = (kind, x, y, w, h) => {
        const [sx, sy] = view.toScreen(x, y);
        out.push({ kind, x: sx, y: sy, w: w * css.k, h: h * css.k });
      };
      for (const { p, x, y } of spots) put('prop', x - p.w / 2, y - p.h / 2, p.w, p.h);
      // a link's box is the rectangle the rotated bar sweeps, which is what a
      // getBoundingClientRect on the DOM bar gave
      for (const [a, b] of data.links) {
        const p = nodeAt[a], q = nodeAt[b];
        if (!p || !q) continue;
        put('link', Math.min(p.x, q.x), Math.min(p.y, q.y) - TILE_H / 2,
          Math.abs(q.x - p.x) || TILE_H, Math.abs(q.y - p.y) + TILE_H);
      }
      return out;
    },
    stats: () => ({ draws: dBase + dOver, base: dBase, over: dOver, sprites, sheet: sheetSize, k: css.k, x: css.x, y: css.y }),

    destroy() {
      dead = true;
      if (raf) cancelAnimationFrame(raf);
      STILL.onchange = null;
      mapBatch = freeObject(gl, mapBatch);
      linkBatch = freeObject(gl, linkBatch);
      propBatch = freeObject(gl, propBatch);
      markerBatch = freeObject(gl2, markerBatch);
      groupBatch = freeObject(gl2, groupBatch);
      blitBatch = freeObject(gl2, blitBatch);
      target = freeTarget(gl2, target);
      mapTex = freeTexture(gl, mapTex);
      linkTex = freeTexture(gl, linkTex);
      propSheet = freeTexture(gl, propSheet);
      markSheet = freeTexture(gl2, markSheet);
      r.destroy();
      r2.destroy();
      // a context left open holds one of the browser's small pool for the rest
      // of the session, and this component is torn down whenever the page is
      gl.getExtension('WEBGL_lose_context')?.loseContext();
      gl2.getExtension('WEBGL_lose_context')?.loseContext();
    },
  };
}
