<script>
  import { ART, asset, nameOf } from './lib/map.js';
  import { hasWebGL2 } from './lib/gl/index.js';
  import { createScene } from './lib/gl/scene.js';
  import { untrack } from 'svelte';

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

  // The four elements this component holds on to. They are $state because that
  // is what `bind:this` wants — Svelte warns at build time otherwise — and not
  // because anything re-runs when they arrive: each is written once, while the
  // DOM is being created, and every read of them happens after that.
  let stage = $state(null);
  let world = $state(null);       // its transform is written straight; see setView
  let base = $state(null);        // the opaque canvas, under the names
  let over = $state(null);        // the see-through one, over them
  let dragging = $state(false);

  /**
   * WHICH RENDERER DRAWS THE MAP, and why there are two of them.
   *
   * Hovering a marker made Chrome re-rasterise the whole scaled map layer with
   * a different filter — 43% of the frames of a hover-leave-hover cycle, 42,891
   * pixels page-wide each time, the pixel art drawn smoothed and then snapping
   * back. `image-rendering: pixelated` is a request the compositor does not
   * have to honour, and nine things tried at the CSS level did not move it by a
   * single frame. So the pictures are drawn by a renderer of our own, where the
   * sampling is ours to choose (src/lib/gl/).
   *
   * The DOM map below is not dead code and not a second implementation kept
   * warm: it is what this page still is on a machine with no WebGL 2, and what
   * it becomes if a shader will not link or a context is lost. `drawn` is the
   * one switch, decided before the first render so a browser that can do it
   * never builds the 433 elements only to throw them away, and flipped to 'dom'
   * by `giveUp` if anything downstream fails.
   */
  let drawn = $state(hasWebGL2() ? 'gl' : 'dom');
  let scene = null;
  /** the marker under the pointer, for the cursor only; see the .over rule */
  let overMarker = $state(false);
  /**
   * The marker a press just focused, if a press is what focused it.
   *
   * A button focused by a pointer does not match `:focus-visible` and shows no
   * ring — but one focused from a script does, and on the GL path the focus IS
   * from a script (see up()). Without this, clicking a marker put a purple ring
   * round it that clicking one has never drawn. It is cleared by the blur that
   * moving focus anywhere else fires, so the first Tab away shows the ring
   * again on whatever it lands on.
   */
  let tapped = $state(null);

  /**
   * How many draw calls a frame is, where a person can see it.
   *
   * That number is the whole claim of this port and it should not have to be
   * taken on faith. It is on the page while the dev server is running, and on
   * the built site for anyone who asks for it with #draws — a reader who did
   * not ask sees the same map they saw before, which is the other rule.
   */
  const SHOW_COUNT = import.meta.env.DEV
    || (typeof location !== 'undefined' && location.hash.includes('draws'));
  let count = $state('');

  const searching = $derived(matches !== null);

  /**
   * The paths between markers, each as a line to lay the dash along.
   *
   * The route is chosen in the build — the game draws no such lines any more,
   * see build.py's `route` — and this only turns a pair of rooms into a bar of
   * the right length at the right angle. The dash repeats inside it, so a path
   * is one element rather than the thirty sprites the game would have placed.
   *
   * Only the DOM path reads this, and a derived that nothing reads is never
   * computed, so the GL page does not pay for it.
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

  /**
   * Where the map sits, and it is a plain object rather than $state.
   *
   * It is rewritten on every pointermove of a drag, and the only thing that
   * ever reads it is `.world`'s transform — one string, written here. As
   * reactive state that write would go through the effect graph sixty times a
   * second to arrive at the same place, and on the GL path it would also be
   * read back by whatever ran next, forcing the layout the write invalidated.
   */
  let view = { x: 0, y: 0, k: 1 };

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
   * Move the map, once, to somewhere the clamp allows.
   *
   * The labels and the 72 keyboard targets ride inside `.world` and travel on
   * its transform exactly as they always have — 11px text under a scale(k) and
   * not `font-size: 11*k px`, which would re-hint and re-shape every name at
   * every step of the wheel. The canvas underneath is the same view as a
   * uniform, so a drag is one style write and one uniform and nothing else.
   */
  function setView(v) {
    view = clamped(v);
    if (world) world.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.k})`;
    scene?.setView(view.x, view.y, view.k);
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
    setView({ k, x: (stage.clientWidth - data.map.w * k) / 2, y: 0 });
  }

  $effect(() => {
    fit();
    // Re-clamp, and NOT re-fit: a reader who has zoomed in keeps their zoom.
    // The drawing buffers are the ResizeObserver's job, below.
    const onResize = () => setView(view);
    addEventListener('resize', onResize);
    return () => removeEventListener('resize', onResize);
  });

  /** Bring a marker to the middle, for when the panel points at one. */
  export function focusOn(node) {
    if (!stage) return;
    const k = Math.min(MAX, Math.max(view.k, 1.4));
    setView({
      k,
      x: stage.clientWidth / 2 - node.x * k,
      y: stage.clientHeight / 2 - node.y * k,
    });
  }

  /** Zoom about a point, keeping whatever is under it where it is. */
  function zoomAt(px, py, factor) {
    const k = Math.max(floor(), Math.min(MAX, view.k * factor));
    if (k === view.k) return;
    setView({
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

  // ── the canvas, and the way back to the DOM ────────────────────────────────
  /**
   * Hand the page to the DOM map and say why.
   *
   * SkillTreeGL takes an `onfallback` for this; here the fallback is the markup
   * below, so the switch is all that is needed. Whatever the reason, the reader
   * gets the map — the same markers, names, tooltips and clicks — and not an
   * error or an empty stage.
   */
  function giveUp(why) {
    console.warn(`hs-map: drawing the map in the DOM instead — ${why}`);
    scene?.destroy();
    scene = null;
    drawn = 'dom';
  }

  $effect(() => {
    if (drawn !== 'gl' || !base || !over || !stage) return;
    // untracked, because `data` is a deep proxy and `speak()` writes a name
    // into every node record when the reader picks another language — reading
    // it as a dependency would rebuild the whole scene eleven times over
    untrack(() => {
      try {
        scene = createScene({
          data, base, over, stage, asset,
          onFail: giveUp,
          onCount: (line) => (count = line),
        });
      } catch (e) {
        giveUp(e.message);
        return;
      }
      scene.setView(view.x, view.y, view.k);
      scene.setState({ hovered, active, matches, dragging });
    });
    // Both drawing buffers and the canvas's own place on screen, whenever the
    // stage's box changes — the window resizing, and the sidebar becoming a
    // drawer at 46rem, which moves the stage without the window moving at all.
    // It fires once on observation, which is the first measurement.
    const ro = new ResizeObserver(() => scene?.resize());
    ro.observe(stage);
    return () => { ro.disconnect(); scene?.destroy(); scene = null; };
  });

  // Everything the picture is drawn from, in one place. It fires when one of
  // the four changes and not once a frame: the transitions they start are the
  // renderer's own business from there.
  $effect(() => {
    scene?.setState({ hovered, active, matches, dragging });
  });

  /**
   * What the measuring harnesses read.
   *
   * They mask the props out of a whole-frame comparison and name a changed
   * pixel by what it fell on, and on this path there is no `.prop` or `.link`
   * element for getBoundingClientRect to find. The markers and the names still
   * are elements, so those come from the DOM exactly as they did.
   */
  $effect(() => {
    if (drawn !== 'gl' || !scene) return;
    window.__gl = () => scene?.stats();
    window.__boxes = () => {
      const out = scene ? scene.boxes() : [];
      for (const [sel, kind] of [['.tag', 'tag'], ['.node', 'node']])
        for (const e of stage.querySelectorAll(sel)) {
          const r = e.getBoundingClientRect();
          if (r.width && r.height) out.push({ kind, x: r.x, y: r.y, w: r.width, h: r.height });
        }
      return { boxes: out, vw: innerWidth, vh: innerHeight };
    };
    return () => { delete window.__gl; delete window.__boxes; };
  });

  // ── pointer ────────────────────────────────────────────────────────────────
  let drag = null;
  let pressed = null;       // the marker a press started on; see up()

  function down(e) {
    if (e.button !== 0) return;
    // On the GL path the press is picked here, because there is no element
    // under the pointer to hear its own pointerdown. It is the same fact
    // either way: which marker the press started on.
    //
    if (scene) pressed = scene.pick(e);
    drag = { id: e.pointerId, x: e.clientX, y: e.clientY, ox: view.x, oy: view.y, moved: 0 };
    stage.setPointerCapture(e.pointerId);
    dragging = true;
  }

  function move(e) {
    if (drag && e.pointerId === drag.id) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
      setView({ ...view, x: drag.ox + dx, y: drag.oy + dy });
    }
    if (!scene) return;
    // After the pan, not before: the markers move under a still pointer during
    // a drag, and the DOM map's buttons fire their own enter and leave as they
    // pass beneath it. A scan over 72 boxes is what that cost instead.
    const hit = scene.pick(e);
    overMarker = !!hit;
    if (hit !== hovered) hovered = hit;
  }

  function leave() {
    if (drag || !scene) return;
    overMarker = false;
    hovered = null;
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
    // was still being routed normally on the DOM path, and picked in down() on
    // the GL one.
    if (drag.moved < 4) {
      active = pressed && active?.room !== pressed.room ? pressed : null;
    }
    // The button is focused by hand on the GL path, because pressing one no
    // longer can: it is pointer-events: none there, so the press lands on the
    // stage, which is a plain div, and the browser moves focus to the body —
    // after which Tab carries on from the top of the page rather than from the
    // marker just touched. Pressing a marker on the DOM path leaves it focused
    // and this is what that costs here.
    //
    // On the way UP and not on the way down: the browser's own focus move is
    // the press's default action and it undoes anything done earlier in the
    // same event, microtask or not. `preventScroll` because `main` scrolls, and
    // a focus that scrolled it would move the map out from under the pointer.
    if (scene && pressed) {
      world?.querySelector(`.node[data-room="${pressed.room}"]`)?.focus({ preventScroll: true });
      // AFTER the focus, not before: focusing one button blurs another, and
      // that blur clears this on its way past.
      tapped = pressed.room;
    }
    pressed = null;
    drag = null;
    dragging = false;
  }

  /**
   * Enter and Space on a focused marker, and only those.
   *
   * On the DOM path a click from a pointer is handled in up() and never arrives
   * here; `detail` is 0 when no pointer was involved, which is what the
   * keyboard sends. On the GL path the button is pointer-events: none until it
   * is focused, so nothing but the keyboard can reach it at all — the test
   * stays because the rule is the same rule.
   */
  function press(e, node) {
    if (e.detail !== 0) return;
    active = active?.room === node.room ? null : node;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="stage"
  class:dragging
  class:gl={drawn === 'gl'}
  class:over={overMarker}
  bind:this={stage}
  onwheel={onwheel}
  onpointerdown={down}
  onpointermove={move}
  onpointerleave={leave}
  onpointerup={up}
  onpointercancel={up}
>
  {#if drawn === 'gl'}
    <!-- Two of them, because the names have to sit between the links and the
         markers: the DOM paints every .tag before every .node, so a marker's
         80px glow covers the label above it and tints it. A canvas cannot be
         split by a DOM layer, so the map, the props and the links are on this
         one and the marker art is on the see-through one over the names. -->
    <canvas class="art" bind:this={base}></canvas>
  {/if}

  <!-- The size is written on, and it is not decoration. In the DOM path the
       map <img> is the one in-flow child and its 2902x800 is what gave this
       element a box; with the picture on a canvas there is no in-flow child
       left, and a `will-change: transform` layer with no box of its own has its
       bounds worked out from 135 absolutely positioned children on every frame
       of a drag. That cost 193ms of Layerize in a 150-step drag against the DOM
       path's 58, and the whole drag 228ms against 86 — more than the port saves
       everywhere else. With the box back it is 57ms. -->
  <div
    class="world"
    bind:this={world}
    style="width: {data.map.w}px; height: {data.map.h}px; transform: translate(0px, 0px) scale(1)"
  >
    {#if drawn === 'dom'}
      <img class="map" src={asset('img/map.webp')} width={data.map.w} height={data.map.h} alt="" draggable="false">

      <!-- The map's own decorations, playing where the game plays them: the
           places are the constants the game's own code hands draw_sprite_ext,
           read out of the executable by the build. Eight sprites in twenty
           places — a skull that blinks over Act 3, five torches along the Act 5
           road, a windmill, a ring of light that drops into the socket the map
           art leaves for it, a train's smoke, a whirlpool, a ghost.

           Each carries only what the background does not already hold: the
           moving part where the artist baked the still art in underneath, the
           whole frame where he did not. So one of these sits exactly over the
           still copy of itself and the next stands on bare map, and both are
           right. -->
      {#each data.props ?? [] as prop (prop.art)}
        {#each prop.at as spot (spot[0] + ':' + spot[1])}
          <span
            class="prop"
            style="
              left: {spot[0]}px; top: {spot[1]}px;
              width: {prop.w}px; height: {prop.h}px;
              background-image: url({asset(`img/${prop.art}.webp`)});
              background-size: {(prop.step ?? prop.w) * prop.n}px {prop.h}px;
              animation-duration: {(prop.n / prop.fps).toFixed(3)}s;
              animation-timing-function: steps({prop.n});
              --last: {-(prop.step ?? prop.w) * prop.n}px;
            "
          ></span>
        {/each}
      {/each}

      <!-- under the markers, and before them, so a path never covers one -->
      {#each paths as p (p.key)}
        <span
          class="link"
          style="
            left: {p.x}px; top: {p.y}px; width: {p.len}px;
            height: {data.linkTile[1]}px; margin-top: {-data.linkTile[1] / 2}px;
            transform: rotate({p.turn}rad);
            background-image: url({asset('img/link.webp')});
          "
        ></span>
      {/each}
    {/if}

    <!-- The names, the way the game's own map screen carries them: above the
         marker, in the language the page is set to. They ride inside the world,
         so they pan and zoom with it — the scale never falls below fitting the
         map to the window's height, so they never shrink out of reading.

         They are text, they are translated into eleven languages, they can be
         selected and they are read aloud, and none of that belongs in a
         texture. They stay DOM on both paths. -->
    <!-- Not the dungeons of an act: theirs stands beside the boss dungeon it
         belongs to, and two names that close is a smudge rather than a label.
         The marker is the game's own and says what it is; the panel names it. -->
    {#each data.nodes.filter((n) => n.kind !== 'dungeons') as node (node.room)}
      <span
        class="tag"
        class:high={node.boss}
        class:faded={searching && !matches?.has(node.room)}
        style="left: {node.x}px; top: {node.y}px"
      >{nameOf(node, lang)}</span>
    {/each}

    {#each data.nodes as node (node.room)}
      {@const on = active?.room === node.room}
      {@const lit = on || hovered?.room === node.room}
      {@const hit = matches?.has(node.room)}
      <!-- A real button on both paths, and on the GL one that is ALL it is:
           the art is on the canvas and the pointer is answered by a scan over
           72 boxes, so nothing here is hit-tested, restyled or promoted while
           the pointer moves. What it still is, is the thing Tab reaches, the
           thing that carries the name a screen reader says and whether it is
           pressed, and the thing the measuring harnesses take their boxes
           from. -->
      <button
        class="node"
        class:lit
        class:on
        class:hit
        class:faded={searching && !hit}
        class:tap={tapped === node.room}
        style="left: {node.x}px; top: {node.y}px"
        data-room={node.room}
        aria-label={nameOf(node, lang)}
        aria-pressed={on}
        onpointerenter={drawn === 'dom' ? () => (hovered = node) : null}
        onpointerleave={drawn === 'dom' ? () => (hovered = null) : null}
        onpointerdown={drawn === 'dom' ? () => (pressed = node) : null}
        onblur={() => (tapped = null)}
        onclick={(e) => press(e, node)}
      >
        {#if drawn === 'dom'}
          <!-- the game's own glow and its twelve-frame flourish, rather than a
               drop-shadow: a filter on any marker forces the whole scaled layer,
               all sixty-three of them, to be rasterised again, and the rest of
               the map visibly flickers every time the pointer moves -->
          <img class="glow" src={asset('img/glow.webp')} alt="" draggable="false">
          <!-- Under the pointer too, not only once something is clicked or found.
               The game's map has almost nothing that moves — five frames of a
               marker are its states, not an animation, and what does move there
               is the fog over unopened zones and the satanic zone. This is the
               second of those, and it is the one thing here that can play
               without saying something untrue. -->
          {#if on || hit || lit}
            <span class="fx" style="background-image: url({asset('img/fx-zone.12x6.webp')})"></span>
          {/if}
          <img class="pin" src={asset(`img/${ART[node.kind]}.webp`)} alt="" draggable="false">
          <!-- The ring the game draws around the marker under its own cursor —
               frame 4 of the marker sprite, cut out with the rest and then never
               put on anything. Over the marker rather than under it: it is the
               same 24 px across, so behind the pin it was invisible. -->
          <img class="ring" src={asset('img/node-ring.webp')} alt="" draggable="false">
          <!-- The act boss stands at the end of its act, and the game marks that
               on its own map screen with this skull. Only the mark is here: the
               boss and what it drops are in the tooltip, where there is room to
               read them. -->
          {#if node.boss}
            <img class="skull" src={asset('img/skull.webp')} alt="" draggable="false">
          {/if}
        {/if}
      </button>
    {/each}
  </div>

  {#if drawn === 'gl'}
    <canvas class="art marks" bind:this={over}></canvas>
    {#if SHOW_COUNT && count}<p class="draws">{count}</p>{/if}
  {/if}
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
  /* The DOM map gets this from `.node { cursor: pointer }` on the button under
     the pointer, which answers whether a drag is running or not — so this rule
     comes after `.dragging` and wins the same way. */
  .stage.over { cursor: pointer; }

  /* Both stretched over the stage and never scaled: the view is a uniform
     inside them, so a pan moves no pixels of theirs. Nothing points at them —
     the stage hears the pointer and asks the scene what is under it. */
  .art {
    position: absolute;
    inset: 0;
    display: block;
    pointer-events: none;
  }
  /* the see-through one, over the names */
  .marks { z-index: 1; }

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

  /* On the canvas path the button is a keyboard target and nothing else.
     Pointer-events off, so the browser stops hit-testing 72 of these on every
     mouse move and the stage answers instead; and the fade taken off, because
     it is a composited opacity transition on up to 63 elements at once and
     there is no longer anything inside them for it to fade. What a reader sees
     is the marker on the canvas, which fades by its own alpha. */
  .stage.gl .node { pointer-events: none; cursor: default; }
  /* `cursor: pointer` and not just the events, because giving this one button
     its events back also makes it the element the browser asks about the
     cursor — and `cursor: default` above then answers for it. The marker under
     the pointer would show an arrow from the moment it was clicked or tabbed
     to, on the map's primary gesture, and nowhere else. */
  .stage.gl .node:focus-visible { pointer-events: auto; cursor: pointer; }
  .stage.gl .node.faded { opacity: 1; transition: none; }
  /* the ring a press must not draw — see `tapped` */
  .stage.gl .node.tap:focus-visible { outline: none; }

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

  /* Every hover move on a marker — the pin's pop, the skull's lift, the glow
     and the ring — goes through a registered custom property instead of
     straight at `transform` and `opacity`, and that indirection is the fix for
     the shimmer the whole map used to show.

     Chrome composites a transition of transform or opacity: it lifts the
     element onto a layer of its own for as long as the transition runs and
     rebuilds the page's layer list twice, once up and once down. `.world` sits
     at whatever scale fits the map to the window's height — 805/800 = 1.00625
     on this screen — and everything inside it is `image-rendering: pixelated`,
     so each rebuild lands the nearest-neighbour sampling grid on different rows
     and columns. Every marker on the map is redrawn a little differently for
     the length of the transition and then snaps back, and a pointer crossing
     five markers does it five times. That is what was being seen.

     A custom property cannot be composited — there is no compositor-side
     `--pin-k` — so the transition runs on the main thread, the transform is
     recomputed per frame as an ordinary style change, and the layer list never
     moves. The values, durations and easing are the ones that were here
     before, so the animation is unchanged.

     Over a ten-second pointer sweep across five markers at hand speed,
     counting markers more than 260px from the cursor that are off their
     resting pixels — tooltip hidden so it cannot be credited, markers that a
     prop crosses left out: five or more of them wrong in 36% of frames and
     121,733 changed pixels in all, against 2% and 14,931 with this in place.
     Deleting the four transitions outright gives 8,393, and what stands
     between that floor and this is the marker the pointer has just left, still
     fading out on purpose.

     These are the fallback path's rules now, and every value in them is
     reproduced number for number by the renderer (src/lib/gl/scene.js) so that
     the two paths draw the same hover. */
  @property --pin-k   { syntax: '<number>'; inherits: false; initial-value: 1; }
  @property --skull-y { syntax: '<number>'; inherits: false; initial-value: -168; }
  @property --glow-a  { syntax: '<number>'; inherits: false; initial-value: 0; }
  @property --glow-k  { syntax: '<number>'; inherits: false; initial-value: .6; }
  @property --ring-a  { syntax: '<number>'; inherits: false; initial-value: 0; }
  @property --ring-k  { syntax: '<number>'; inherits: false; initial-value: .8; }

  .pin {
    transform: translate(-50%, -50%) scale(var(--pin-k));
    transition: --pin-k .1s ease-out;
  }

  /* Above the marker rather than on it: the dungeon door is what you click, and
     a skull across it hides which door it is. */
  .skull {
    transform: translate(-50%, calc(var(--skull-y) * 1%));
    transition: --skull-y .1s ease-out;
  }
  .node.lit .skull, .node.on .skull { --skull-y: -190; }
  /* A search can light thirty markers at once. They get the size, not the
     glow — thirty glows is a red wash with the map somewhere underneath. */
  .node.lit .pin,
  .node.hit .pin { --pin-k: 1.15; }

  /* No will-change here or on the ring below, and the reason it went is worth
     as much as the reason it came. It was put here because fading a glow made
     the whole map flinch: the transition runs on a child of the one composited
     layer that holds the 2902px image, that layer was rasterised again at the
     live scale, and a 320x220 patch 640px from the cursor changed 343 pixels
     mid-transition — none once the glow was promoted.

     That has inverted, and the same test is what says so. Headful on a real
     GPU, six runs in both orders: with will-change:opacity that far patch
     changes 372 pixels mid-transition, and with it gone, zero. Chrome promoted
     these itself for as long as a transition ran, so the declaration bought
     nothing while it mattered, and 144 permanent layers the rest of the time.
     Chrome rebuilds its layer list over all 223 of them on every frame of a
     pan, and that was the whole cost of panning this map: 9.0ms of main-thread
     work per frame against 1.0ms without it, Layerize 878ms of the 1080ms a
     120-frame drag spends against 38ms, 52ms per frame against 4.2ms on a CPU
     throttled 4x, and 108 dropped frames in a two-second drag at 144Hz against
     none. The floor — the map image alone, everything else hidden — is 0.74ms,
     so what is left is 0.3ms above nothing at all.

     Nothing on a marker is promoted at all any more, because the transitions
     above go through custom properties: LayerTree over a whole hover reads a
     flat 8 composited layers, from before the pointer arrives to after it
     leaves, against 8 rising to 27 and falling back on the way in and 8 to 26
     on the way out with transform and opacity transitions in their place.

     They were also softening the art. A promoted layer is scaled by the
     compositor, which does not honour image-rendering: pixelated, so every
     marker was drawn smoothed over a map that is not: a 40px box round one pin
     held 514 distinct colours with the declaration and 258 without, and its
     edges go from blurred to hard. That is the one visible change here, and it
     is worth looking at once — 9,437 of the 1,440,000 pixels on screen differ,
     and a mask of them is the 72 pins and 7 skulls and nothing else. The map
     behind them is identical.

     .world's will-change: transform above stays, and it is not the same kind of
     hint: one layer for the one element whose transform is rewritten every
     frame, against 144 for markers that are only ever read. Taking it off as
     well measured the same to within noise here — 1.07ms a frame against 1.00,
     no Paint events either way — so there is nothing to win by touching a hint
     that is telling the truth. */

  /* Opacity goes through a custom property as well, and it is not the junior
     partner: moving only the transform halves across left 25,507 changed
     pixels far from the cursor, and moving the opacity halves too took it to
     14,931. A composited opacity transition rebuilds the layer list exactly as
     a composited transform one does. */
  .glow {
    opacity: var(--glow-a);
    transform: translate(-50%, -50%) scale(var(--glow-k));
    transition: --glow-a .14s ease-out, --glow-k .14s ease-out;
  }

  .ring {
    opacity: var(--ring-a);
    transform: translate(-50%, -50%) scale(var(--ring-k));
    transition: --ring-a .12s ease-out, --ring-k .12s ease-out;
  }
  .node.lit .ring, .node.on .ring { --ring-a: 1; --ring-k: 1; }
  .node.lit .glow { --glow-a: .55; --glow-k: .8; }
  .node.on .glow { --glow-a: .85; --glow-k: 1; }

  /* Mapscreen_Zone_Effect_spr: 12 frames of 137x113, the game plays it at 6fps */
  /* A background scrolled inside a box, and NOT a strip sliding on a
     transform, which is where this went and came back from.

     A transform animation is a composited layer and costs the main thread
     nothing: twenty of these idled at 0.0ms against 69.4ms and 396 paints
     every three seconds this way. But a composited layer is re-rastered
     whenever the page rebuilds its layer list, and it lands on a different
     subpixel each time — so hovering any marker, which adds one element to the
     map, made all twenty shimmer at once. Measured with every animation paused
     and the tooltip hidden, so nothing was meant to change at all: 6,234
     pixels changed away from the cursor as layers, 77 as a background.

     Panning costs the same either way — 95.0ms against 96.1ms over the same
     150-step drag — so the whole trade is idle cost against a visible shimmer,
     and the shimmer loses. Containment, will-change and a promotion of the box
     instead of the strip were all tried against the same measurement and not
     one of them moved it.

     The frames still carry the 2px gutter GUTTER puts between them: the box's
     edge samples its neighbour the same way the strip's did. */
  .prop {
    position: absolute;
    background-repeat: no-repeat;
    image-rendering: pixelated;
    pointer-events: none;
    animation-name: prop;
    animation-iteration-count: infinite;
  }
  @keyframes prop { to { background-position-x: var(--last); } }

  /* Nothing animates while the map is being dragged, and `animation: none`
     rather than a pause because the point is to give the layer back.

     A running transform animation is a composited layer, and twenty of them
     inside a parent that is itself being translated are rasterised again on
     every frame of the drag: a 150-step drag costs 339ms of main thread with
     them running, 327ms with them merely paused — a pause keeps the layer —
     and 80ms with the animation gone, which is what the same drag costs with
     the props not drawn at all. 177 raster tasks against 4.

     Six frames a second of flicker is not what anyone is looking at while they
     drag, so it stops, and the twenty layers go with it. The renderer does the
     same thing for the same reason: a drag parks every prop and the flourish on
     frame 0, so the twenty re-synchronise when it ends exactly as they do here. */
  .stage.dragging .prop,
  .stage.dragging .fx { animation: none; }

  /* The zone effect, scrolled as a background exactly as the props are, and
     for the reason recorded there: a strip sliding on a transform is a
     composited layer, and a composited layer is re-rastered every time the
     page rebuilds its layer list. This one is created and destroyed on every
     hover, so it kept re-rastering while the pointer rested — with the pointer
     parked on one marker and nothing else free to move, 206 pixels more than
     200px away from it flipped between one frame and the next over a two-
     second hold, and 0 do with the animation on `background-position`. The
     links are 1px bars and took the worst of it.

     The sheet is 137x113 twelve times, laid out every 139px — 137 and the
     two-pixel gutter — so the strip is 1668 wide, and `strips()` in
     build/build.py prints those numbers on every build so a sprite that
     changes size is noticed here.

     The sprite's URL comes from the markup rather than from here because a
     CSS `url('/img/...')` is only rewritten to sit under the site's base path
     by the build: in the dev server it is a 404, which is why this element was
     invisible — and unmeasurable — in every test until now. `asset()` is what
     the other seven images on this map already go through. */
  .fx {
    width: 137px;
    height: 113px;
    transform: translate(-50%, -50%);
    background-position: 0 0;
    background-size: 1668px 113px;
    background-repeat: no-repeat;
    animation: fx 2s steps(12) infinite;
  }
  @keyframes fx { to { background-position-x: -1668px; } }

  .node:focus-visible { outline: 2px solid var(--hot); border-radius: 50%; }

  /* while a search is running, everything that does not match steps back */
  /* enough to recede, not so much that the map reads as switched off */
  .node.faded { opacity: .45; transition: opacity .15s; }

  /* An outline rather than a shadow: the map is busy and a name over it needs
     to be readable on light sand and on dark rock alike. Four offsets, not a
     filter — a filter on this layer is what made the whole map flinch once. */
  .tag {
    position: absolute;
    transform: translate(-50%, -100%);
    margin-top: -14px;
    white-space: nowrap;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: .2px;
    /* Warm grey rather than white, and the outline eased off its full black:
       at full strength each name read as a sticker laid over the map instead of
       something written on it. */
    color: #cfc0b2;
    text-shadow:
      1px 0 0 #1a121fcc, -1px 0 0 #1a121fcc, 0 1px 0 #1a121fcc, 0 -1px 0 #1a121fcc,
      1px 1px 0 #1a121fcc, -1px 1px 0 #1a121fcc,
      1px -1px 0 #1a121fcc, -1px -1px 0 #1a121fcc;
    pointer-events: none;
    user-select: none;
  }
  /* Clear of the skull, on the seven markers that carry one: the name sat where
     the skull is and read "King<skull>omb". */
  .tag.high { margin-top: -30px; }
  .tag.faded { opacity: .3; transition: opacity .15s; }

  /* Only there when it was asked for, and above the bottom shelf rather than
     under it — the shelves are 84px tall and sit on a z-index the stage cannot
     reach, so at bottom: 10px this was invisible. */
  .draws {
    position: absolute;
    left: 10px;
    bottom: 94px;
    z-index: 2;
    margin: 0;
    padding: 5px 8px;
    font: 12px/1.4 ui-monospace, monospace;
    color: #cfc0b2;
    background: rgba(16, 10, 19, .82);
    border: 1px solid var(--edge);
    border-radius: 6px;
    pointer-events: none;
    user-select: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .fx, .prop { animation: none; }
    .pin, .glow { transition: none; }
  }
</style>
