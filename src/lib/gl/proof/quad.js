// One textured quad, drawn at NEAREST, with the draw count and the number the
// whole port turns on printed beside it.
//
// The bug this renderer exists for is measured in distinct colours. The owner's
// report: an 80x80 patch of map art holds 132 of them at rest and 1,278 when
// Chrome re-rasterises the composited layer with a smoothing filter. So the
// proof that a quad is drawn RIGHT is not that it appears — it is that the same
// patch of the same art, at the scale the live page actually sits at, still
// holds 132 and not more.
//
// The patch is map.webp at (520, 280), 80x80, which holds exactly 132 distinct
// colours in the file. The scale is 1.00625, which is 805px of window over an
// 800px map — the number WorldMap.svelte's own comment records as this screen's.
//
// The second canvas draws the identical geometry through a LINEAR sampler,
// because a check that passes either way proves nothing: it is the compositor's
// filter, and it is what 1,278 looks like.

import { createContext, createTexture, buildQuads, Renderer, View } from '../index.js';

const K = 1.00625;   // the live page's scale
const K2 = 3.7;      // and a loudly fractional one
const PATCH = { x: 520, y: 280, w: 80, h: 80 };
const SOURCE_COLOURS = 132; // counted in the file, see the header

const src = `${import.meta.env.BASE_URL}img/map.webp`;
const img = await new Promise((ok, no) => {
  const i = new Image();
  i.onload = () => ok(i);
  i.onerror = () => no(new Error(src));
  i.src = src;
});

/** distinct RGB triples in a readPixels buffer, over a top-down screen box */
function colours(px, w, h, x0, y0, cw, ch) {
  const seen = new Set();
  for (let y = y0; y < y0 + ch; y++) {
    for (let x = x0; x < x0 + cw; x++) {
      const o = ((h - 1 - y) * w + x) * 4; // readPixels is bottom-up
      seen.add((px[o] << 16) | (px[o + 1] << 8) | px[o + 2]);
    }
  }
  return seen.size;
}

function run(canvasId, filter) {
  const canvas = document.getElementById(canvasId);
  const gl = createContext(canvas, { preserveDrawingBuffer: true });
  if (!gl) return { err: 'no WebGL 2' };
  const r = new Renderer(gl);

  const tex = createTexture(gl, img);
  if (filter === 'linear') {
    // deliberately wrong, so the count has something to be measured against
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  }

  const uv = {
    u0: PATCH.x / img.naturalWidth, v0: PATCH.y / img.naturalHeight,
    u1: (PATCH.x + PATCH.w) / img.naturalWidth, v1: (PATCH.y + PATCH.h) / img.naturalHeight,
  };
  // Half-pixel centres on purpose: neither copy is allowed to land on the texel
  // grid by luck, which is the only way a nearest sample flatters itself.
  const batch = buildQuads(gl, [
    { x: 60, y: 80, w: PATCH.w * K, h: PATCH.h * K, ...uv },
    { x: 270, y: 160, w: PATCH.w * K2, h: PATCH.h * K2, ...uv },
  ], tex);

  // no sizeCanvas here: the canvas carries its own width/height, and the point
  // of the count is that a device pixel is a CSS pixel, so dpr is 1 by hand
  const view = new View().setCss(0, 0, 1);
  r.begin({ w: canvas.width, h: canvas.height, dpr: 1, clear: [0, 0, 0] });
  r.sprites(view.uniform, [batch]);
  const draws = r.end();

  const px = new Uint8Array(canvas.width * canvas.height * 4);
  gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, px);
  return {
    draws,
    live: colours(px, canvas.width, canvas.height, 20, 40, 80, 80),
    big: colours(px, canvas.width, canvas.height, 150, 60, 140, 140),
  };
}

const near = run('near', 'nearest');
const lin = run('lin', 'linear');

const rows = [
  ['draw calls per canvas (two sprites, one batch)', `${near.draws} and ${lin.draws}`, near.draws === 1 && lin.draws === 1],
  [`colours in the 80x80 source patch, in the file`, SOURCE_COLOURS, null],
  ['drawn at k=1.00625, NEAREST', near.live, near.live <= SOURCE_COLOURS],
  ['drawn at k=1.00625, LINEAR — the compositor', lin.live, null],
  ['NEAREST invents nothing the art has not got', near.live <= SOURCE_COLOURS, near.live <= SOURCE_COLOURS],
  ['LINEAR invents a few hundred', lin.live > near.live * 4, lin.live > near.live * 4],
  ['at k=3.7: NEAREST', near.big, near.big <= SOURCE_COLOURS],
  ['at k=3.7: LINEAR', lin.big, null],
];
document.getElementById('out').innerHTML = '<table>' + rows.map(([k, v, ok]) =>
  `<tr><td>${k}</td><td class="n ${ok === null ? '' : ok ? 'ok' : 'bad'}">${v}</td></tr>`).join('') + '</table>';
window.__proof = { source: SOURCE_COLOURS, near, lin, pass: rows.every(([, , ok]) => ok !== false) };
