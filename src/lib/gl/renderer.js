// The one program, and the uniform plumbing it needs, behind one method. A
// component that uses this never touches `gl` for drawing — it builds batches
// (geometry.js) and asks for them to be drawn in an order.
//
// Every draw is counted, because "how many draw calls is a frame" is the whole
// claim of the port and it should be a number on the page rather than a belief.
// On this map a frame is four: the background, the props, the links, the
// markers — against the 450 positioned elements the compositor used to walk.
//
// There are two of these, one per canvas, because the names have to sit between
// the links and the markers (the DOM paints .tag before .node, and an 80px glow
// covers the label above it). A canvas cannot be split by a DOM layer, so the
// map, the props and the links are three draws on an opaque canvas under the
// labels and the marker layer is one draw on a see-through canvas over them.

import { createProgram } from './program.js';
import { SPRITE_VERT, SPRITE_FRAG } from './shaders.js';

export class Renderer {
  /** @throws if the program fails to compile or link — the caller falls back */
  constructor(gl) {
    this.gl = gl;
    this.sprite = createProgram(gl, SPRITE_VERT, SPRITE_FRAG, 'sprite');
    this.vw = 0;
    this.vh = 0;
    this.dpr = 1;
    this.draws = 0;
  }

  /**
   * Start a frame: viewport, clear colour, source-over on premultiplied colour.
   *
   * `clear` is [r, g, b] or [r, g, b, a]; the marker canvas clears to
   * transparent so the labels and the links below it show through, the base
   * canvas to the page's own background because the map does not always fill
   * its stage.
   *
   * ONE / ONE_MINUS_SRC_ALPHA, not SRC_ALPHA / ONE_MINUS_SRC_ALPHA: the shader
   * hands over premultiplied colour, which is the only blend that stacks
   * translucent sprites correctly into a see-through buffer AND is what the
   * compositor expects back from one. See SPRITE_FRAG.
   */
  begin({ w, h, dpr, clear }) {
    const gl = this.gl;
    this.vw = w;
    this.vh = h;
    this.dpr = dpr;
    this.draws = 0;
    gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
    if (clear) {
      gl.clearColor(clear[0], clear[1], clear[2], clear[3] ?? 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
    }
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  end() {
    this.gl.bindVertexArray(null);
    return this.draws;
  }

  /**
   * Sprite batches, in the order given — and the order given is the picture.
   * Nothing here sorts, groups or reorders: the marker layer arrives in the
   * order the DOM had it, glow before flourish before pin before ring before
   * skull, node by node, and that is how it is drawn.
   */
  sprites(view, batches, { straight = true } = {}) {
    if (!batches?.length) return;
    const gl = this.gl, p = this.sprite;
    gl.useProgram(p.program);
    gl.uniform2f(p.u('uViewport'), this.vw, this.vh);
    gl.uniform3f(p.u('uView'), view[0], view[1], view[2]);
    gl.uniform1i(p.u('uTex'), 0);
    // straight: the art, whose alpha is straight on disk. Not straight: a group
    // target this renderer filled itself, which is already premultiplied.
    gl.uniform1f(p.u('uStraight'), straight ? 1 : 0);
    gl.activeTexture(gl.TEXTURE0);
    let last = null;
    for (const b of batches) {
      if (!b || !b.count) continue;
      if (b.tex !== last) {
        gl.bindTexture(gl.TEXTURE_2D, b.tex);
        last = b.tex;
      }
      gl.bindVertexArray(b.vao);
      // `first` lets one buffer be drawn as a run, which is how a marker that
      // has to be composited on its own is slotted back into DOM order without
      // its neighbours being rebuilt into batches of their own
      gl.drawArrays(gl.TRIANGLES, b.first ?? 0, b.count);
      this.draws++;
    }
  }

  destroy() {
    this.sprite?.free();
    this.sprite = null;
  }
}

/** '#rrggbb' -> [r, g, b] in 0..1 */
export const rgb = (hex) => [
  parseInt(hex.slice(1, 3), 16) / 255,
  parseInt(hex.slice(3, 5), 16) / 255,
  parseInt(hex.slice(5, 7), 16) / 255,
];
