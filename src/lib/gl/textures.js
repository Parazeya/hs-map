// Images in, GL textures out.

/**
 * Upload an image.
 *
 * NEAREST both ways, and no mip chain, and that is the entire reason this
 * renderer exists. Every picture on this map is pixel art the game drew at 1:1;
 * the page has always asked for `image-rendering: pixelated`, and what it could
 * not ask for is that the COMPOSITOR honour it. Chrome re-rasterises a promoted
 * layer with its own filter, and an 80x80 patch of map art went from 132
 * distinct colours at rest to 1,278 while that lasted. A texture the renderer
 * samples itself cannot be resampled behind its back.
 *
 * This is where this file parts company with PoETools'. The tree wants a mip
 * chain: its icons are photographic, they minify to a fifth of their size, and
 * without one they crawl. Here minification never goes below about 0.4x (the
 * view floor fits an 800px-tall map to the window's height), the art is flat
 * colour with hard edges, and a mip chain would average exactly the edges the
 * art is made of. `mipNearest`, `trilinear` and the bias that goes with them
 * are not ported.
 *
 * `wrapS: 'repeat'` is for art that tiles along a bar — the 16x10 link trail,
 * whose quad runs u from 0 to len/16. Everything else clamps.
 */
export function createTexture(gl, source, { wrapS = 'clamp', wrapT = 'clamp' } = {}) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  // straight alpha in, straight alpha out: the blend is SRC_ALPHA /
  // ONE_MINUS_SRC_ALPHA, which is what the browser composites these same webp
  // files with today. Premultiplying here would darken every soft edge on the
  // 80px glow.
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  const wrap = (w) => (w === 'repeat' ? gl.REPEAT : gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap(wrapS));
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap(wrapT));
  return tex;
}

/**
 * Pack loaded images into one sheet, so the whole map above the background is
 * one texture and a layer is one draw call.
 *
 * Why pack at all, when 27 textures would be 27 cheap draws: the marker layer
 * has to keep DOM ORDER. Each marker is a glow, then its flourish, then its
 * pin, then its ring, then its skull, and the next marker's glow goes over the
 * last one's pin — an 80px glow reaches its neighbours. Drawing texture by
 * texture would put every glow under every pin, which is a different picture.
 * One sheet means one buffer in exactly the order the DOM had, and the question
 * never arises.
 *
 * Straight into the texture with texSubImage2D, never through a 2D canvas: a
 * canvas stores premultiplied and hands back unpremultiplied, and that round
 * trip loses low bits on exactly the soft alpha the glow is made of. The driver
 * decodes each image itself here, the same as it would for a texture of its own.
 *
 * Shelf-packed tallest first, which is enough for 27 rectangles and leaves the
 * sheet under 2048 wide — the smallest MAX_TEXTURE_SIZE WebGL 2 guarantees.
 *
 * `gutter` is 2 for the same reason build/build.py's GUTTER is 2: a NEAREST tap
 * at a cell's edge must land in transparency and not in the next cell.
 *
 * @param entries `[name, HTMLImageElement][]`
 * @returns {{ tex, w, h, cell: Map<string, {x,y,w,h}> }}
 */
export function packSheet(gl, entries, { maxW = 2048, gutter = 2 } = {}) {
  const items = entries.filter(([, img]) => img)
    .map(([name, img]) => ({ name, img, w: img.naturalWidth, h: img.naturalHeight }))
    .sort((a, b) => b.h - a.h || b.w - a.w);
  const cell = new Map();
  let x = 0, y = 0, rowH = 0, w = 0;
  for (const it of items) {
    if (x + it.w > maxW && x > 0) { x = 0; y += rowH + gutter; rowH = 0; }
    cell.set(it.name, { x, y, w: it.w, h: it.h });
    x += it.w + gutter;
    w = Math.max(w, x - gutter);
    rowH = Math.max(rowH, it.h);
  }
  const h = y + rowH;
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, w, h); // one level: NEAREST, no chain
  for (const it of items) {
    const c = cell.get(it.name);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, c.x, c.y, gl.RGBA, gl.UNSIGNED_BYTE, it.img);
  }
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return { tex, w, h, cell };
}

export function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null); // a missing sheet must not hang the caller
    img.src = url;
  });
}

/**
 * Load a `{ name: url }` map of images in parallel.
 *
 * `onProgress` fires per image, load or failure alike — counting only successes
 * lets one 404 hang a loading state forever.
 * `alive()` lets a component that unmounted mid-load say so.
 *
 * @returns {Promise<[string, HTMLImageElement][]>} in the order `urls` gave
 */
export async function loadAll(urls, { onProgress, alive = () => true } = {}) {
  const names = Object.keys(urls);
  const imgs = await Promise.all(names.map(async (name) => {
    const img = await loadImage(urls[name]);
    onProgress?.(name, !!img);
    return img;
  }));
  if (!alive()) return [];
  return names.map((name, i) => [name, imgs[i]]).filter(([, img]) => img);
}

/** free a packed sheet, or a bare texture */
export function freeTexture(gl, t) {
  if (gl && t) gl.deleteTexture(t.tex ?? t);
  return null;
}
