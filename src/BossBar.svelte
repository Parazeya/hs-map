<script>
  import { asset } from './lib/map.js';

  // Two shelves, because there are two different things here.
  //
  // Along the top, the bosses the map has nowhere to put: the summoned fights,
  // and the two that are keyed like act bosses without being one — Grimbone,
  // who belongs to Niflhel, and the Sheep King, who belongs to Sheeponia.
  // Neither zone has a marker. The act bosses themselves are gone from here:
  // they stand at the end of their act, on the dungeon the map already draws.
  //
  // Along the bottom, everything else that is not a place: chests, mimics, the
  // rift, the pillar. They drop things too, and they are not bosses.
  // `lit` is the set that drops the item being read in the menu, if one is.
  // Everything else dims, the same way the map's markers do, so a glance says
  // where the thing comes from without reading a single name.
  let { data, hovered = $bindable(null), lit = null, controls } = $props();

  const BOX = 64;

  // Everything with drops, picture or not. Filtering on the picture meant a
  // source the art could not be found for — Sheeponia, the Eternal Battlefield
  // — vanished from the page entirely, which is a worse answer than a label.
  const bosses = $derived(
    Object.entries(data.bosses).filter(([, b]) => b.kind === 'uber' || b.kind === 'other'),
  );
  const sources = $derived(
    Object.entries(data.bosses).filter(([, b]) => b.kind === 'source'),
  );
</script>

<!-- `class="shelf {where}"` looked tidier and did not work: Svelte cannot see a
     class name that is built at run time, so it took `.top` and `.bottom` for
     dead rules and removed them — and both shelves stacked at the top. -->
{#snippet shelf(rows, atTop)}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="shelf"
    class:top={atTop}
    class:bottom={!atTop}
    onpointerleave={() => (hovered = null)}
  >
    {#each rows as [name, it] (name)}
      {@const box = it.icon}
      {@const k = box ? Math.min(1, BOX / Math.max(box[2], box[3])) : 1}
      <button
        class="cell"
        class:on={hovered === name}
        class:hit={lit?.has(name)}
        class:faded={lit && !lit.has(name)}
        class:inferno={it.inferno_only}
        title={name}
        aria-label={name}
        onpointerenter={() => (hovered = name)}
      >
        {#if box}
          <span
            class="art"
            style="
              width: {box[2]}px; height: {box[3]}px;
              background-image: url({asset('img/bosses.webp')});
              background-position: {-box[0]}px {-box[1]}px;
              background-size: {data.bossSheet.w}px {data.bossSheet.h}px;
              transform: translate(-50%, -50%) scale({k});
            "
          ></span>
        {:else}
          <span class="named">{name}</span>
        {/if}
      </button>
    {/each}
    <!-- the page's own controls ride the top row, where the title bar used to be -->
    {#if atTop && controls}<span class="controls">{@render controls()}</span>{/if}
  </div>
{/snippet}

{@render shelf(bosses, true)}
{@render shelf(sources, false)}

<style>
  .shelf {
    position: absolute;
    left: 0; right: 0;
    z-index: 8;
    display: flex;
    gap: 3px;
    align-items: center;
    overflow-x: auto;
    /* Dark enough to read a portrait against, clear enough to see the map
       through: the two rows take a fifth of the height between them, and
       opaque they took it away entirely. Not a gradient — over one, the lower
       half of every portrait sat on lighter ground and the row read as
       standing behind the map. */
    background: rgb(19 12 23 / 0.72);
    backdrop-filter: blur(2px);
  }
  .top {
    top: 0;
    padding: 6px 10px;
    border-bottom: 1px solid var(--edge);
  }
  .bottom {
    bottom: 0;
    padding: 6px 10px;
    border-top: 1px solid var(--edge);
  }

  .controls {
    margin-left: auto;
    display: flex;
    gap: 8px;
    align-items: center;
    padding-left: 12px;
  }


  .cell {
    position: relative;
    flex: none;
    width: 70px;
    height: 70px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: 6px;
    background: none;
    cursor: pointer;
  }
  .cell:hover, .cell.on { border-color: var(--hot); background: #ffffff10; }
  .cell.hit { border-color: var(--hot); background: #ffffff14; }
  /* the same settle the map's markers use, so the two shelves and the map read
     as one answer rather than three things snapping at once */
  .cell.faded { opacity: .3; transition: opacity .15s; }
  .cell:focus-visible { outline: none; border-color: var(--hot); }

  /* the ones that only give anything up on the hardest difficulty */
  .cell.inferno { border-color: #6b2a14; }
  .cell.inferno:hover, .cell.inferno.on { border-color: #ff8a4a; }

  /* the ones with no art in the game, said in words instead */
  .named {
    display: block;
    padding: 0 4px;
    color: var(--dim);
    font-size: 10px;
    line-height: 1.15;
    text-align: center;
    overflow-wrap: anywhere;
  }
  .cell:hover .named, .cell.on .named { color: var(--ink); }

  .art {
    position: absolute;
    top: 50%;
    left: 50%;
    image-rendering: pixelated;
    background-repeat: no-repeat;
    pointer-events: none;
  }
</style>
