// Every GLSL program the renderer uses, in one file.
//
// For this map that is one program. PoETools carries three — sprite, line and
// circle — because the tree strokes connectors and draws discs; here the 54
// links are bars of the game's own trail texture, so they are sprites with a
// rotation and a repeating u, and nothing on the map is a circle at all. The
// line and circle programs are not ported.
//
// They live here rather than inside a component for the reason the tree's do: a
// shader is a STRING until a driver compiles it, so `vite build` passes with a
// syntax error in one, and keeping the VERT/FRAG pair together in one module is
// what lets a gate compile both on a real context.
//
// Shared conventions, unchanged from the tree:
//   uViewport — canvas size in CSS pixels
//   uView     — (ox, oy, scaling); world -> screen is (p + ox,oy) / scaling, so
//               panning and zooming are a uniform write and never a rebuild.
//               The map's own view is (x, y, k) with screen = p*k + (x,y);
//               View.setCss converts, see view.js.

/**
 * World-space quad, per-vertex corner offset in world units.
 *
 * The corner offset is written by the CPU already rotated and already scaled,
 * which is how this map gets the two things the tree never needed:
 *   - the 54 link bars, each rotated about the node it leaves from;
 *   - a marker piece that GROWS on hover (--pin-k 1 -> 1.15), which is four
 *     numbers in a buffer and not a uniform, a second batch or a second program.
 *
 * aAlpha is per-vertex and not a uniform because one batch holds the whole
 * marker layer in DOM order — a glow at .55 over one node and an opaque pin
 * over the next — and that order is what has to be preserved. See renderer.js.
 */
export const SPRITE_VERT = `#version 300 es
  layout(location=0) in vec2 aPos;      // sprite centre, world units
  layout(location=1) in vec2 aCorner;   // corner offset from it, world units
  layout(location=2) in vec2 aUV;
  layout(location=3) in float aAlpha;
  uniform vec2 uViewport;
  uniform vec3 uView;
  out vec2 vUV;
  out float vAlpha;
  void main() {
    vec2 screen = (aPos + uView.xy) / uView.z + aCorner / uView.z;
    vec2 clip = vec2(screen.x / uViewport.x * 2.0 - 1.0, 1.0 - screen.y / uViewport.y * 2.0);
    gl_Position = vec4(clip, 0.0, 1.0);
    vUV = aUV;
    vAlpha = aAlpha;
  }`;

// alpha only, never a colour multiply: every fade on this map is a CSS
// `opacity` on straight-alpha art (--glow-a .55, .node.faded .45), and opacity
// scales the source's alpha rather than darkening its rgb. Multiplying rgb as
// well would turn a half-faded marker grey against the map instead of
// translucent over it.
//
// The colour leaves here PREMULTIPLIED — rgb * a — and the renderer blends
// ONE / ONE_MINUS_SRC_ALPHA rather than SRC_ALPHA / ONE_MINUS_SRC_ALPHA. That
// is not a preference: the marker layer draws on a canvas of its own with
// `alpha: true`, because the names have to sit between the links and the
// markers and a DOM label cannot be sandwiched inside one canvas. A
// see-through drawing buffer is handed to the compositor as premultiplied, and
// stacking translucent sprites into a STRAIGHT-alpha buffer with SRC_ALPHA
// blending gets the alpha channel wrong anyway — it writes a*a where `over`
// wants a. Over an opaque buffer the two are the same picture, so both
// canvases use the one that is right for both.
//
// The textures are still uploaded straight (see textures.js): premultiplying
// eight-bit art at upload loses the low bits the 80px glow is made of, and
// doing it here costs one multiply on a texel that is already in a register.
//
// Fully transparent texels are discarded rather than blended, the tree's reason
// unchanged: an atlas cell's gutter must not darken what is already behind it.
//
// No uBias and no mip chain here — this is pixel art sampled NEAREST, which is
// the whole point of the port (see textures.js), and there is no level to bias.
// No uClip either: nothing on this map is drawn through a keyhole.
//
// uStraight says which kind of texture is bound: 1 for the art, whose alpha is
// straight on disk, and 0 for the group target (target.js), whose colour the
// renderer premultiplied on the way in and must not premultiply twice. That
// target exists because CSS `opacity` on a marker fades the WHOLE marker as one
// picture — see scene.js — and a group has to be composited before it is faded.
export const SPRITE_FRAG = `#version 300 es
  precision highp float;
  in vec2 vUV;
  in float vAlpha;
  uniform sampler2D uTex;
  uniform float uStraight;
  out vec4 outColour;
  void main() {
    vec4 c = texture(uTex, vUV);
    if (c.a < 0.004) discard;
    outColour = vec4(c.rgb * mix(1.0, c.a, uStraight), c.a) * vAlpha;
  }`;
