<script>
  import { ART, asset, nameOf } from './lib/map.js';

  let {
    data,
    lang,
    active = $bindable(null),    // clicked, and stays without the pointer
    hovered = $bindable(null),   // under the pointer
    matches = null,
  } = $props();

  /**
   * How far the wheel may take it.
   *
   * The floor is not a number but the fit itself: zooming out past the point
   * where the map fills the window's height only buys empty ground around it.
   * The ceiling is three, at which a marker's 24 pixels are 72 and the art is
   * as coarse as it is worth looking at — five turned a 2902-wide map into a
   * 14,510-wide one to no purpose.
   */
  const MAX = 3;
  const floor = () => (stage ? stage.clientHeight / data.map.h : 0.4);
  /** How far past an edge the map may be dragged, so the rim is not glued shut. */
  const SLACK = 60;
  /**
   * What the two shelves cover, top and bottom.
   *
   * The map is fitted to the window's full height, so those bands hide a strip
   * of it at each end. Rather than shrink the map to fit between them, the
   * vertical travel is opened up the same way the horizontal already was: it
   * can be pulled down to bring the top out from under the bosses, and up to
   * bring the bottom out from under the chests.
   */
  const SHELF_TOP = 84, SHELF_BOTTOM = 84;

  let stage = $state(null);
  let view = $state({ x: 0, y: 0, k: 1 });
  let dragging = $state(false);

  const searching = $derived(matches !== null);

  /**
   * The paths between markers, each as a line to lay the dash along.
   *
   * The route is chosen in the build — the game draws no such lines any more,
   * see build.py's `route` — and this only turns a pair of rooms into a bar of
   * the right length at the right angle. The dash repeats inside it, so a path
   * is one element rather than the thirty sprites the game would have placed.
   */
  const paths = $derived.by(() => {
    const at = Object.fromEntries(data.nodes.map((n) => [n.room, n]));
    // Centre to centre, and under the markers. They were held clear of them for
    // a while, which left every path floating between two rings; in the game a
    // path runs into the ring and stops where the art covers it.
    return data.links.flatMap(([a, b]) => {
      const p = at[a], q = at[b];
      if (!p || !q) return [];
      const dx = q.x - p.x, dy = q.y - p.y;
      return [{
        key: a + '|' + b, a, b,
        x: p.x, y: p.y,
        len: Math.hypot(dx, dy),
        turn: Math.atan2(dy, dx),
      }];
    });
  });


  /** Keep the map over the window: it may overhang, but not sail away. */
  function clamped(v) {
    if (!stage) return v;
    const vw = stage.clientWidth, vh = stage.clientHeight;
    const w = data.map.w * v.k, h = data.map.h * v.k;

    const x = w <= vw
      ? (vw - w) / 2                                        // narrower than the window: centred
      : Math.min(SLACK, Math.max(vw - w - SLACK, v.x));

    // The two ends of the travel: the map's top edge level with the top shelf,
    // and its bottom edge level with the bottom one. Which of the two is the
    // upper bound depends on whether the map is taller than the gap between
    // them, so both are worked out and then sorted.
    const a = SHELF_TOP;
    const b = vh - SHELF_BOTTOM - h;
    const lo = Math.min(a, b) - SLACK;
    const hi = Math.max(a, b) + SLACK;
    return { k: v.k, x, y: Math.min(hi, Math.max(lo, v.y)) };
  }

  /**
   * Fill the window's height.
   *
   * Fitting both ways shrank the map to a strip: it is 2902 by 800, so the
   * width is what has to give. The game does the same — you see a tall slice of
   * it and travel sideways.
   */
  export function fit() {
    if (!stage) return;
    const k = Math.min(MAX, floor());
    view = clamped({ k, x: (stage.clientWidth - data.map.w * k) / 2, y: 0 });
  }

  $effect(() => {
    fit();
    const onResize = () => (view = clamped(view));
    addEventListener('resize', onResize);
    return () => removeEventListener('resize', onResize);
  });

  /** Bring a marker to the middle, for when the panel points at one. */
  export function focusOn(node) {
    if (!stage) return;
    const k = Math.min(MAX, Math.max(view.k, 1.4));
    view = clamped({
      k,
      x: stage.clientWidth / 2 - node.x * k,
      y: stage.clientHeight / 2 - node.y * k,
    });
  }

  /** Zoom about a point, keeping whatever is under it where it is. */
  function zoomAt(px, py, factor) {
    const k = Math.max(floor(), Math.min(MAX, view.k * factor));
    if (k === view.k) return;
    view = clamped({
      k,
      x: px - (px - view.x) * (k / view.k),
      y: py - (py - view.y) * (k / view.k),
    });
  }

  function onwheel(e) {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }

  let drag = null;
  let pressed = null;       // the marker a press started on; see up()
  function down(e) {
    if (e.button !== 0) return;
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, ox: view.x, oy: view.y, moved: 0 };
    stage.setPointerCapture(e.pointerId);
    dragging = true;
  }
  function move(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
    view = clamped({ ...view, x: drag.ox + dx, y: drag.oy + dy });
  }
  function up(e) {
    if (!drag || e.pointerId !== drag.id) return;
    // A press that went nowhere is a click, and it is decided here rather than
    // on the marker, because the marker never hears its own.
    //
    // The stage captures the pointer on the way down — that is what lets a drag
    // carry on past the edge of whatever it started on — and a captured pointer
    // sends its pointerup, and with it the click, to the element holding the
    // capture. So every click on a marker was delivered to the stage, which
    // read it as a press on empty space and let the active one go: "click a
    // marker to keep it" did nothing at all, from the day the drag was written.
    //
    // `pressed` is the marker the press started on, recorded while the pointer
    // was still being routed normally.
    if (drag.moved < 4) {
      active = pressed && active?.room !== pressed.room ? pressed : null;
    }
    pressed = null;
    drag = null;
    dragging = false;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="stage"
  class:dragging
  bind:this={stage}
  onwheel={onwheel}
  onpointerdown={down}
  onpointermove={move}
  onpointerup={up}
  onpointercancel={up}
>
  <div class="world" style="transform: translate({view.x}px, {view.y}px) scale({view.k})">
    <img class="map" src={asset('img/map.png')} width={data.map.w} height={data.map.h} alt="" draggable="false">

    <!-- under the markers, and before them, so a path never covers one -->
    {#each paths as p (p.key)}
      <span
        class="link"
        style="
          left: {p.x}px; top: {p.y}px; width: {p.len}px;
          height: {data.linkTile[1]}px; margin-top: {-data.linkTile[1] / 2}px;
          transform: rotate({p.turn}rad);
          background-image: url({asset('img/link.png')});
        "
      ></span>
    {/each}

    {#each data.nodes as node (node.room)}
      {@const on = active?.room === node.room}
      {@const lit = on || hovered?.room === node.room}
      {@const hit = matches?.has(node.room)}
      <button
        class="node"
        class:lit
        class:on
        class:hit
        class:faded={searching && !hit}
        style="left: {node.x}px; top: {node.y}px"
        title={nameOf(node, lang)}
        aria-label={nameOf(node, lang)}
        aria-pressed={on}
        onpointerenter={() => (hovered = node)}
        onpointerleave={() => (hovered = null)}
        onpointerdown={() => (pressed = node)}
        onclick={(e) => {
          // The keyboard's path, and only it: a click from a pointer is handled
          // in up() and never arrives here. `detail` is 0 when no pointer was
          // involved, which is what Enter and Space on a focused button send.
          if (e.detail !== 0) return;
          active = on ? null : node;
        }}
      >
        <!-- the game's own glow and its twelve-frame flourish, rather than a
             drop-shadow: a filter on any marker forces the whole scaled layer,
             all sixty-three of them, to be rasterised again, and the rest of
             the map visibly flickers every time the pointer moves -->
        <img class="glow" src={asset('img/glow.png')} alt="" draggable="false">
        {#if on || hit}<span class="fx"></span>{/if}
        <img class="pin" src={asset(`img/${ART[node.kind]}.png`)} alt="" draggable="false">
        <!-- The act boss stands at the end of its act, and the game marks that
             on its own map screen with this skull. Only the mark is here: the
             boss and what it drops are in the tooltip, where there is room to
             read them. -->
        {#if node.boss}
          <img class="skull" src={asset('img/skull.png')} alt="" draggable="false">
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .stage {
    position: absolute;
    inset: 0;
    cursor: grab;
    touch-action: none;
    overscroll-behavior: none;
  }
  .stage.dragging { cursor: grabbing; }

  .world {
    position: absolute;
    transform-origin: 0 0;
    will-change: transform;
  }

  .map {
    display: block;
    image-rendering: pixelated;
    user-select: none;
  }

  /* One bar per path with the game's trail segment repeating inside it. */
  .link {
    /* the height comes from the tile the build cut, so the two cannot drift */
    position: absolute;
    transform-origin: 0 50%;
    background-repeat: repeat-x;
    background-position: left center;
    image-rendering: pixelated;
    pointer-events: none;
  }


  /* Placed by its centre, which is what the game stores. The hit area is
     deliberately wider than the art, so a 24px marker is not something to be
     chased with a mouse. */
  .node {
    position: absolute;
    width: 34px;
    height: 34px;
    margin: -17px 0 0 -17px;
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }

  /* Each piece is centred on the marker by hand rather than by a grid.
     A grid track is sized by its largest item, and the glow is 80px inside a
     34px button: the track grew to 80, everything in it was centred on 40
     instead of 17, and the whole marker sat down and to the right of the place
     you had to point at. */
  .node > * {
    position: absolute;
    top: 50%;
    left: 50%;
    pointer-events: none;
    image-rendering: pixelated;
  }

  .pin {
    transform: translate(-50%, -50%);
    transition: transform .1s ease-out;
  }

  /* Above the marker rather than on it: the dungeon door is what you click, and
     a skull across it hides which door it is. */
  .skull {
    transform: translate(-50%, -168%);
    transition: transform .1s ease-out;
  }
  .node.lit .skull, .node.on .skull { transform: translate(-50%, -190%); }
  /* A search can light thirty markers at once. They get the size, not the
     glow — thirty glows is a red wash with the map somewhere underneath. */
  .node.lit .pin,
  .node.hit .pin { transform: translate(-50%, -50%) scale(1.15); }

  /* The glow needs a layer of its own, and the reason is worth keeping.
     Fading it is an opacity transition on a child of the map, and the map is one
     composited layer holding a 2902px image and everything on it. While that
     transition ran, the layer was rasterised again at the live scale — so every
     marker on the map turned crisp for a tenth of a second and went soft again
     the moment it ended. Pointing at one zone made the whole map flinch.
     Measured rather than guessed at: a 320x220 patch 640px from the cursor
     changed 343 pixels mid-transition and none once the glow was promoted.
     Sixty-three 80px layers is what that costs, and it is worth it. */
  .glow {
    opacity: 0;
    transform: translate(-50%, -50%) scale(.6);
    transition: opacity .14s ease-out, transform .14s ease-out;
    will-change: opacity;
  }
  .node.lit .glow { opacity: .55; transform: translate(-50%, -50%) scale(.8); }
  .node.on .glow { opacity: .85; transform: translate(-50%, -50%) scale(1); }

  /* Mapscreen_Zone_Effect_spr: 12 frames of 137x113, the game plays it at 6fps */
  .fx {
    width: 137px;
    height: 113px;
    background: url('/img/fx-zone.12x6.png') 0 0 / 1644px 113px no-repeat;
    transform: translate(-50%, -50%);
    animation: fx 2s steps(12) infinite;
  }
  @keyframes fx { to { background-position-x: -1644px; } }

  .node:focus-visible { outline: 2px solid var(--hot); border-radius: 50%; }

  /* while a search is running, everything that does not match steps back */
  /* enough to recede, not so much that the map reads as switched off */
  .node.faded { opacity: .45; transition: opacity .15s; }

  @media (prefers-reduced-motion: reduce) {
    .fx { animation: none; }
    .pin, .glow { transition: none; }
  }
</style>
