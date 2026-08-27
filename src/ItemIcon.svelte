<script>
  import { asset } from './lib/map.js';

  // `from` names the sheet: the map packs the 931 things that drop somewhere,
  // the codex packs every item the game defines, and they are separate files.
  let { item, sheet, box = 26, from = 'img/items.webp' } = $props();

  // The icons are packed into one sheet: one request for nine hundred of them.
  // Each is drawn at its own size and scaled down only if it does not fit, so
  // a ring stays a ring rather than being blown up to fill the slot.
  const at = $derived(item?.icon ?? null);
  const scale = $derived(at ? Math.min(1, box / Math.max(at[2], at[3])) : 1);
</script>

<span class="slot" style="width: {box}px; height: {box}px">
  {#if at}
    <span
      class="art"
      style="
        width: {at[2]}px; height: {at[3]}px;
        background-image: url({asset(from)});
        background-position: {-at[0]}px {-at[1]}px;
        background-size: {sheet.w}px {sheet.h}px;
        transform: translate(-50%, -50%) scale({scale});
      "
    ></span>
  {/if}
</span>

<style>
  .slot {
    position: relative;
    flex: none;
    display: block;
  }
  .art {
    position: absolute;
    top: 50%;
    left: 50%;
    image-rendering: pixelated;
    background-repeat: no-repeat;
  }
</style>
