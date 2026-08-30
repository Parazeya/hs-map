// Turning sprites into vertex buffers. Nothing here knows what a marker, a
// link or a torch is: it takes quads and hands back objects the renderer draws.
//
// The whole point of the port lives in this file, and the sentence is the
// tree's: the DOM walks every element on every frame; here a sprite is written
// into a buffer once and a frame is a handful of draw calls, because panning
// and zooming only move a uniform. So anything that does NOT change while the
// user drags belongs in a static batch, and only genuinely per-frame geometry
// goes in a dynamic one.
//
// On this map that line falls in a definite place. The 54 links never move, so
// they are static. The 20 props change UV six times a second and the ~230
// marker pieces change scale and alpha for the ~100ms a hover takes, so both
// are dynamic — and both are rewritten only on the frames where their own
// numbers actually changed, not on every frame of a drag.
//
// PoETools' QuadGroups, buildCircles, arcPoints and stripTris are not ported:
// everything on this map except the 2902x800 background comes out of one packed
// sheet (textures.js), so there is nothing to group by texture, and there is no
// circle and no polyline on it at all.

/** floats per vertex: pos2, corner2, uv2, alpha1 */
const STRIDE = 7;

/**
 * One quad into `d32` at float offset `o`, six vertices.
 *
 * `q` is `{ x, y, w, h, u0, v0, u1, v1, a = 1, turn = 0 }`: centred on (x, y),
 * sized in world units, and rotated about that centre by `turn` radians.
 *
 * Rotating the CORNER rather than a matrix is what makes a link one sprite. The
 * DOM bar rotates about its left edge, so a caller that wants the same bar puts
 * the centre half a length along the angle — `x + len/2*cos, y + len/2*sin` —
 * and the two are the same rectangle.
 *
 * A grown pin is the same trick with no rotation: `w` and `h` already carry the
 * hover's scale, so --pin-k costs four numbers in a buffer rather than a
 * uniform, a second batch or a second program.
 *
 * @returns the new float offset
 */
function writeQuad(d32, o, q) {
  const hw = q.w / 2, hh = q.h / 2;
  const a = q.a ?? 1;
  const t = q.turn ?? 0;
  const cos = t ? Math.cos(t) : 1, sin = t ? Math.sin(t) : 0;
  // the four corners, rotated once and then written twice each — spelled out
  // rather than looped over an array of arrays, because this runs for every
  // sprite of every rewritten batch and that array is 24 objects of garbage
  // per quad for a collector to find later
  const ax = -hw * cos + hh * sin, ay = -hw * sin - hh * cos; // top left
  const bx = hw * cos + hh * sin, by = hw * sin - hh * cos;   // top right
  const cx = hw * cos - hh * sin, cy = hw * sin + hh * cos;   // bottom right
  const dx = -hw * cos - hh * sin, dy = -hw * sin + hh * cos; // bottom left
  const x = q.x, y = q.y, u0 = q.u0, v0 = q.v0, u1 = q.u1, v1 = q.v1;
  d32[o++] = x; d32[o++] = y; d32[o++] = ax; d32[o++] = ay; d32[o++] = u0; d32[o++] = v0; d32[o++] = a;
  d32[o++] = x; d32[o++] = y; d32[o++] = bx; d32[o++] = by; d32[o++] = u1; d32[o++] = v0; d32[o++] = a;
  d32[o++] = x; d32[o++] = y; d32[o++] = cx; d32[o++] = cy; d32[o++] = u1; d32[o++] = v1; d32[o++] = a;
  d32[o++] = x; d32[o++] = y; d32[o++] = ax; d32[o++] = ay; d32[o++] = u0; d32[o++] = v0; d32[o++] = a;
  d32[o++] = x; d32[o++] = y; d32[o++] = cx; d32[o++] = cy; d32[o++] = u1; d32[o++] = v1; d32[o++] = a;
  d32[o++] = x; d32[o++] = y; d32[o++] = dx; d32[o++] = dy; d32[o++] = u0; d32[o++] = v1; d32[o++] = a;
  return o;
}

/** the four attributes of SPRITE_VERT, against a buffer already bound */
function attribs(gl) {
  const parts = [[0, 2, 0], [1, 2, 8], [2, 2, 16], [3, 1, 24]]; // pos, corner, uv, alpha
  for (const [loc, size, off] of parts) {
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, size, gl.FLOAT, false, STRIDE * 4, off);
  }
}

/**
 * A batch of sprites sharing one texture, uploaded once and never rewritten.
 * @returns {{ tex: WebGLTexture, vao: WebGLVertexArrayObject, buf: WebGLBuffer, count: number } | null}
 */
export function buildQuads(gl, quads, tex) {
  const n = quads.length;
  if (!n || !tex) return null;
  const d32 = new Float32Array(n * 6 * STRIDE);
  let o = 0;
  for (const q of quads) o = writeQuad(d32, o, q);
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, d32, gl.STATIC_DRAW);
  attribs(gl);
  gl.bindVertexArray(null);
  return { tex, vao, buf, count: n * 6 };
}

/**
 * A quad buffer that is rewritten when its contents change — the props, whose
 * UVs step six times a second, and the marker layer, whose alphas and scales
 * move for the ~100ms a hover transition runs.
 *
 * Allocated once at `capacity` quads; `write()` uploads a prefix of it. Calling
 * it is the only cost of a hover: no rebuild, no new buffer, no reallocation,
 * and nothing at all on the frames where the caller does not call it.
 */
export function createDynamicQuads(gl, capacity, tex) {
  const scratch = new Float32Array(capacity * 6 * STRIDE);
  const vao = gl.createVertexArray();
  gl.bindVertexArray(vao);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, scratch.byteLength, gl.DYNAMIC_DRAW);
  attribs(gl);
  gl.bindVertexArray(null);
  const obj = {
    tex, vao, buf, count: 0, capacity,
    write(quads) {
      const n = Math.min(quads.length, capacity);
      let o = 0;
      for (let i = 0; i < n; i++) o = writeQuad(scratch, o, quads[i]);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferSubData(gl.ARRAY_BUFFER, 0, scratch, 0, o);
      obj.count = n * 6;
      return obj;
    },
  };
  return obj;
}

/**
 * The UVs of one cell of a packed sheet — `{ x, y, w, h }` in texels.
 * Texel edges, not centres: the sampler is NEAREST and the cells carry a 2px
 * gutter, so a corner sample lands inside its own cell and never half a texel
 * into the next one.
 */
export function cellUV(cell, sheetW, sheetH) {
  return {
    u0: cell.x / sheetW, v0: cell.y / sheetH,
    u1: (cell.x + cell.w) / sheetW, v1: (cell.y + cell.h) / sheetH,
  };
}

/**
 * Frame `i` of a sprite strip inside a packed sheet.
 *
 * The strips are laid out every `step` px — the frame's own width plus the 2px
 * gutter GUTTER puts between them in build/build.py — which is why this takes
 * `step` and `w` separately and does not assume they are the same number.
 *
 * This is what advances a torch: a prop's quad is unchanged except for two
 * floats, six times a second.
 */
export function stripUV(cell, i, w, step, sheetW, sheetH) {
  const x = cell.x + i * step;
  return {
    u0: x / sheetW, v0: cell.y / sheetH,
    u1: (x + w) / sheetW, v1: (cell.y + cell.h) / sheetH,
  };
}

/** hand one buffer object back to the driver; returns null so callers can assign */
export function freeObject(gl, o) {
  if (o && gl) {
    gl.deleteVertexArray(o.vao);
    gl.deleteBuffer(o.buf);
  }
  return null;
}
