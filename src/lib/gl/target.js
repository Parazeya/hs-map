// An off-screen colour buffer the renderer can draw into and then draw FROM.
//
// One thing on this map needs it, and it is not an effect: `.node.faded` is
// `opacity: .45` on the marker's BUTTON, and a CSS opacity on an element with
// children composites the children first and fades the result. Drawing the same
// pieces one at a time at .45 each is a different picture wherever two of them
// overlap — the glow under a marker's own pin stops being hidden by it and
// washes the pin red. Measured on the live page, with an item peeked in the
// panel and the active marker not among its zones: 386 pixels of one marker,
// the blue orb reading dark red.
//
// So a marker that is faded and has more than one piece is composited here
// first, at its own alphas, and then drawn once at the fade. That is what the
// browser does, in the order it does it.
//
// Nothing else in the port needs a second pass, which is why this is nine lines
// of state and not a framebuffer stack.

/**
 * A texture the size of the drawing buffer, with a framebuffer pointing at it.
 *
 * Drawing-buffer size and not the marker's box, so the blit back is a
 * full-screen quad whose corners land on the texture's corners exactly — a
 * NEAREST tap then reads the texel it wrote, with no half-pixel to round. The
 * cost of the full size is paid in a scissor instead: the clear, the group and
 * the blit are all clipped to the one marker's box.
 */
export function createTarget(gl, w, h) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, w, h);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (!ok) {
    gl.deleteFramebuffer(fb);
    gl.deleteTexture(tex);
    return null; // the caller draws without grouping rather than not at all
  }
  return { tex, fb, w, h };
}

/** free one; returns null so callers can assign */
export function freeTarget(gl, t) {
  if (gl && t) {
    gl.deleteFramebuffer(t.fb);
    gl.deleteTexture(t.tex);
  }
  return null;
}
