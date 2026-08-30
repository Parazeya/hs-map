// Context creation and the one piece of per-frame bookkeeping that is not
// drawing: keeping the drawing buffer the same size as the element.
//
// Copied from PoETools' src/lib/gl/context.js; the only change is the comment
// on `alpha`, because this canvas does not always cover its own stage.

/**
 * A WebGL 2 context, or null when the browser has none. Callers are expected to
 * fall back rather than fail — WebGL 2 is missing on old iOS, on blocklisted
 * drivers, and whenever a user has disabled hardware acceleration.
 *
 * `alpha: false` matters: an opaque drawing buffer skips the compositor's
 * per-frame blend against the page. The map does not always fill its stage —
 * zoomed out on a wide window there is ground either side of it — so the caller
 * clears to the page's own background colour rather than leaving it see-through.
 *
 * `antialias: false`, unlike the tree: nothing here has a geometric edge to
 * smooth. Every quad is axis-aligned pixel art except the 54 rotated link bars,
 * and those are cut out of a texture, not stroked. MSAA on a full-screen buffer
 * costs fill rate for nothing.
 */
export function createContext(canvas, opts = {}) {
  try {
    return canvas.getContext('webgl2', { antialias: false, alpha: false, ...opts });
  } catch {
    return null;
  }
}

/** does this browser have WebGL 2 at all? (used to pick a renderer up front) */
export function hasWebGL2() {
  if (typeof document === 'undefined') return false;
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2');
    // hand the context straight back: probing must not hold one of the browser's
    // small pool of live contexts open for the rest of the session
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
    return !!gl;
  } catch {
    return false;
  }
}

/**
 * Match the drawing buffer to the element, at a capped device-pixel ratio —
 * cheap phones report 2.5–3x and would allocate a huge backing store for no
 * visible gain, and fill cost scales with its area.
 *
 * The canvas is sized in CSS pixels by stylesheet and in device pixels here;
 * everything else in the renderer works in CSS pixels, so `dpr` only ever
 * appears where a real pixel is what matters.
 *
 * @returns {{ w: number, h: number, dpr: number }} size in CSS pixels
 */
export function sizeCanvas(canvas, container, maxDpr = 2) {
  const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
  const w = container.clientWidth, h = container.clientHeight;
  const bw = Math.round(w * dpr), bh = Math.round(h * dpr);
  if (canvas.width !== bw || canvas.height !== bh) {
    canvas.width = bw;
    canvas.height = bh;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
  }
  return { w, h, dpr };
}
