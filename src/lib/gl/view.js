// Pan, zoom, and the two coordinate questions everything else asks: where does
// this world point land on screen, and what is under the pointer.
//
// The view is deliberately a plain mutable object rather than reactive state,
// the tree's reason unchanged: it changes on every pointermove during a drag,
// and a reactive write there would invalidate the component's whole effect
// graph 60+ times a second when all that is needed is one uniform and a redraw.
//
// What is NOT ported is the tree's fit/centreOn/zoomBy. This map's pan and zoom
// have rules of their own — the floor is the fit itself, the ceiling is 3, the
// map may overhang by SLACK and be pulled out from under two 84px shelves — and
// those rules live with the map in WorldMap.svelte, where they are written down.
// Moving them here would be the one change a reader would notice.

export class View {
  /**
   * The map's own numbers are `{ x, y, k }`, where a world point lands at
   * `p * k + (x, y)` and k is 1 at native size. The shaders want
   * `(p + ox,oy) / scaling`. They are the same view: scaling = 1/k, ox = x/k.
   *
   * The conversion lives here, in one place, rather than in the shader, because
   * the shader is the tree's and should stay recognisably theirs — and because
   * every other renderer PoETools has already speaks (ox, oy, scaling).
   */
  constructor() {
    this.ox = 0;
    this.oy = 0;
    this.scaling = 1;
  }

  setCss(x, y, k) {
    this.scaling = 1 / k;
    this.ox = x * this.scaling;
    this.oy = y * this.scaling;
    return this;
  }

  /** the uniform the shader takes */
  get uniform() {
    return [this.ox, this.oy, this.scaling];
  }

  toScreen(x, y) {
    return [(x + this.ox) / this.scaling, (y + this.oy) / this.scaling];
  }

  toWorld(sx, sy) {
    return [sx * this.scaling - this.ox, sy * this.scaling - this.oy];
  }
}

/**
 * Pointer position in the canvas's own (layout px) coordinate space.
 *
 * With a CSS zoom applied to an ancestor, clientX and getBoundingClientRect are
 * in zoomed visual pixels while the canvas works in layout pixels — divide by
 * the effective zoom or every hit-test drifts by ~10% of the distance from the
 * canvas origin.
 */
export function pointerPos(canvas, e) {
  const rect = canvas.getBoundingClientRect();
  const z = rect.width / (canvas.clientWidth || 1) || 1;
  return { mx: (e.clientX - rect.left) / z, my: (e.clientY - rect.top) / z, z };
}

/**
 * The item under a screen point, testing a BOX in world units.
 *
 * A box and not the tree's radius, because that is what a reader has been
 * clicking: `.node` is a 34x34 button centred on the marker, inside `.world`,
 * so its hit area is 34 world units square and scales with the map. A circle of
 * radius 17 would quietly stop accepting the corners.
 *
 * The LAST match wins, because that is what the DOM does: two markers on this
 * map are 30 units apart (Act_01_Boss_Dungeon_03 and Act_01_Dungeons), their
 * 34-unit boxes overlap in a 4-unit band, and a click in that band goes to
 * whichever button comes later in document order — the later node.
 *
 * Hit-testing stays on the CPU, as the tree's does: it is a scan over 72 items
 * on a pointer move, which costs nothing next to what the browser used to spend
 * hit-testing 450 positioned elements and restyling the ones that matched.
 *
 * @param items  anything with world coordinates
 * @param at     `{ mx, my }` in CSS pixels
 * @param getXY  item -> [x, y] in world units
 * @param reach  half the box's side, in WORLD units
 */
export function pickBox(items, at, view, getXY, reach) {
  const [wx, wy] = view.toWorld(at.mx, at.my);
  let best = null;
  for (const it of items) {
    const [x, y] = getXY(it);
    if (Math.abs(wx - x) <= reach && Math.abs(wy - y) <= reach) best = it;
  }
  return best;
}
