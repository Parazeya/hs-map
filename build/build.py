"""Build the site's data and art from one verified Extractor generation.

Items, marker positions, talents and source text are read from HS_DATA_BUNDLE.
Textures are read from the installed game only after its file hashes match the
manifest. External reference additions are recorded separately in provenance.

    python build/build.py
"""

import json
import os
import hashlib
import math
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path

# Item names carry characters a Windows console's default code page cannot
# encode, and printing one killed the run after every file was already written.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import bosses
import bounty
import encyclopedia
import words as vocabulary
import icons
import langsplit
import said
import gear
import item_grant_slots
import item_effects
import item_conditions
import reference_sources
import reference_sets
import reference_zones
import skills as skilltree
import suits
import portraits
import unholy
from data_bundle import Bundle, BundleError, MAP_MARKER_EXCLUSIONS, attach_exclusive_sources, configured_game, item_records, tables_from_items, verify_item_coverage, verify_map_marker_sources
from publication import BuildLock, publish, recover

HERE = Path(__file__).resolve().parent.parent
TRACKER = Path(os.environ.get("HS_TRACKER", HERE.parent / "HeroSiege")).resolve()
# Restore interrupted active data even when the next requested bundle is
# absent or stale. Input validation must not strand a half-installed site.
if __name__ == "__main__" and not os.environ.get("HS_MAP_OUTPUT"):
    with BuildLock(HERE):
        recover(HERE / "public")
GAME = configured_game()
BUNDLE = Bundle(Path(os.environ.get("HS_DATA_BUNDLE", HERE.parent / "HeroSiege Extractor/out/bundle")), GAME)
SOURCE = BUNDLE.source()
reference_hash = hashlib.sha256()
for reference_file in sorted((HERE / "build" / "planner").rglob("*.json")):
    reference_hash.update(reference_file.relative_to(HERE / "build" / "planner").as_posix().encode())
    reference_hash.update(reference_file.read_bytes())
SOURCE["reference"] = {"name": "HSPlanner", "sha256": reference_hash.hexdigest(), "verified_for_game_build": False}
CHEST_REFERENCE = reference_sources.catalogue()
SOURCE["reference_chest_drops"] = CHEST_REFERENCE["reference"]
SET_REFERENCE = reference_sets.catalogue()
SOURCE['reference_item_sets'] = SET_REFERENCE['reference']
ZONE_REFERENCE = reference_zones.catalogue()
SOURCE["reference_zone_drops"] = ZONE_REFERENCE["reference"]
AURA_SLOTS = item_grant_slots.discover(GAME / "Hero_Siege.exe", next(
    (row["sha256"] for row in BUNDLE.game["files"] if row["path"] == "Hero_Siege.exe"), None))
SOURCE["item_aura_slots"] = {key: AURA_SLOTS[key] for key in
    ("profile", "source_sha256", "certificate_sha256")} if AURA_SLOTS else {"status": "unsupported"}
ITEM_EFFECTS = item_effects.discover(GAME / 'Hero_Siege.exe', next(
    (row['sha256'] for row in BUNDLE.game['files'] if row['path']=='Hero_Siege.exe'),None), next(
    (row['sha256'] for row in BUNDLE.game['files'] if row['path']=='data.win'),None))
SOURCE['item_effects'] = {key: ITEM_EFFECTS[key] for key in
    ('profile','source_sha256','data_win_sha256','certificate_sha256')} if ITEM_EFFECTS else {'status':'unsupported'}
ITEM_CONDITIONS=item_conditions.discover(GAME/'Hero_Siege.exe', next(
    (row['sha256'] for row in BUNDLE.game['files'] if row['path']=='Hero_Siege.exe'),None),next(
    (row['sha256'] for row in BUNDLE.game['files'] if row['path']=='data.win'),None))
SOURCE['item_conditions']={key:ITEM_CONDITIONS[key] for key in
    ('profile','source_sha256','data_win_sha256','certificate_sha256')} if ITEM_CONDITIONS else {'status':'unsupported'}
RAW_ITEMS = BUNDLE.read("items")
TALENT_ROWS = BUNDLE.read("talents")
ASSETS = BUNDLE.read("assets", {})
ITEM_ICONS = ASSETS.get("item_icons", {}) if isinstance(ASSETS, dict) else {}
os.environ["HERO_SIEGE_BIN"] = str(GAME)

sys.path.insert(0, str(TRACKER / "tools"))
from datawin import DataWin           # noqa: E402
import numpy as np
from PIL import Image                 # noqa: E402

STAGING_ONLY = bool(os.environ.get("HS_MAP_OUTPUT"))
OUTPUT = (Path(os.environ["HS_MAP_OUTPUT"]).resolve() if STAGING_ONLY else
          Path(tempfile.mkdtemp(prefix=".hs-map-stage-", dir=HERE)))
IMG = OUTPUT / "img"

#: How every picture the pages load is written.
#:
#: Lossless WebP, which for pixel art is the same image in a third of the bytes:
#: the map background falls from 1252 KB to 453, the item sheet from 1130 to 466.
#: Measured against the alternatives — PNG at its highest compression came out
#: *larger* than what Pillow writes by default, and lossy WebP at q90 was worse
#: than lossless, because sharp edges are exactly what a lossy codec spends
#: bytes on. A settled map page went from 2.62 MB over the wire to under one.
def picture(im, path):
    im.save(path.with_suffix(".webp"), lossless=True, quality=100, method=6)
DATA = OUTPUT / "data"
DIAGNOSTICS = OUTPUT / "diagnostics"
IMG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)
DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
if STAGING_ONLY:
    favicon = HERE / "public" / "favicon.png"
    target = OUTPUT / favicon.name
    if favicon.is_file() and favicon.resolve() != target.resolve():
        shutil.copy2(favicon, target)


# ── the art ──────────────────────────────────────────────────────────────────
def art():
    dw = DataWin(GAME / "data.win")
    def cut(name, idx=0):
        return dw.frame_image(dw.sprites[name]["frames"][idx])

    bg = cut("Map_Screen_spr")
    picture(bg, IMG / "map.png")

    def unlit(im):
        """Give an additive sprite the alpha a browser needs.

        The glow and the flourish are drawn by the game with additive blending,
        so their art is opaque and their "nothing" is black — put on a page as
        they are, each one is a black square with a coloured blob in it, and a
        search that lights thirty markers paints thirty black squares over the
        map. Reading the alpha out of the brightness gets the same picture
        without asking the browser for a blend mode, which would put every
        marker back on its own compositing layer — the thing that made the map
        flicker in the first place.
        """
        px = im.convert("RGBA").load()
        out = Image.new("RGBA", im.size)
        o = out.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = px[x, y]
                o[x, y] = (r, g, b, min(a, max(r, g, b)))
        return out

    # frame 1 is the opened state, 0 the unopened, 2 the padlock, 4 the ring the
    # game draws under the cursor
    for out, (spr, frame) in {
        "node": ("Mapscreen_Zone_spr", 1),
        "node-dim": ("Mapscreen_Zone_spr", 0),
        "node-ring": ("Mapscreen_Zone_spr", 4),
        # Every marker sprite carries its own ring at its own size: 24px for a
        # zone and a boss dungeon, 26 for the big zone and the town. One ring for
        # all of them sat inside the rim of the wider two.
        "node-ring-big": ("Mapscreen_Zone_Big_spr", 4),
        "town": ("Mapscreen_Zone_Town_spr", 1),
        "dungeon": ("Mapscreen_Zone_Boss_Dungeon_spr", 1),
        # The zone at the end of an act, which the game draws bigger and in
        # purple rather than blue — 26px against 24 — because it is the one that
        # opens onto the act's boss dungeon. `Mapscreen_Zone_Big_Satanic_spr`
        # sits beside it in the game, which is what says "Big" is the kind of
        # zone and not a state it happens to be in.
        "node-big": ("Mapscreen_Zone_Big_spr", 1),
        "satanic": ("Mapscreen_Zone_Satanic_spr", 1),
        "glow": ("Mapscreen_Zone_Light_Glow_spr", 0),
        "chosen": ("Mapscreen_Chosen_Big_spr", 0),
        "skull": ("Mapscreen_Skull_spr", 0),
    }.items():
        im = cut(spr, frame)
        if out in ADDITIVE:
            im = unlit(im)
        picture(im, IMG / f"{out}.png")

    # The map screen has no mark for an ordinary dungeon, because the game has
    # nowhere to put one: `Dungeon_Entrance_obj` stands in no room at all — an
    # entrance is placed as a zone is generated, so which zone holds one is not
    # a fact until it is played. What a player does see is the minimap's own
    # mark, and that is the honest picture of a thing any zone can get.
    #
    # It is not on the map screen's page, so it goes the long way round, the way
    # the boss portraits do. Cut from the wrong page it came out a transparent
    # 22 by 22.
    picture(dw.sprite_frames("Minimap_Dungeon_spr")[0], IMG / "dungeonmark.png")

    tile = trail(cut)
    strips(dw, cut, unlit)
    return dw, bg.width, bg.height, tile, props(dw, cut, bg)


def patches(moves, cell=16):
    """The moving pixels grouped into a few rectangles, coarsely.

    Whole pixels would give a hundred specks; a 16-pixel grid gives the two or
    three places a thing actually animates in, which is what this is for.
    """
    h, w = moves.shape
    rows, cols = (h + cell - 1) // cell, (w + cell - 1) // cell
    grid = np.zeros((rows, cols), dtype=bool)
    for r in range(rows):
        for c in range(cols):
            grid[r, c] = moves[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell].any()
    seen = np.zeros_like(grid)
    boxes = []
    for r in range(rows):
        for c in range(cols):
            if not grid[r, c] or seen[r, c]:
                continue
            stack, cells = [(r, c)], []
            seen[r, c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < rows and 0 <= nx < cols and grid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys = [y for y, _ in cells]
            xs = [x for _, x in cells]
            boxes.append((min(xs) * cell, min(ys) * cell,
                          min(w, (max(xs) + 1) * cell), min(h, (max(ys) + 1) * cell)))
    return boxes


#: Transparent columns between one frame of a prop's strip and the next. See
#: where the sheet is built for what they are for.
GUTTER = 2

def drawn_at(dw, names):
    """Verified prop corners from the same generation as the item data."""
    current = BUNDLE.read("map", {})
    found = {name: [] for name in names}
    width, height = current.get("width"), current.get("height")
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        raise BundleError("Map dataset has no dimensions for its prop coordinates")
    for row in current.get("props", []):
        name = row.get("sprite")
        if name not in found:
            continue
        if (row.get("source") or {}).get("kind") != "decoded":
            raise BundleError(f"Map prop {name} has no current code evidence")
        x, y = row.get("left"), row.get("top")
        if not all(type(value) in (int, float) and math.isfinite(value) for value in (x, y)):
            raise BundleError(f"Map prop {name} has incomplete coordinates")
        if name not in dw.sprites:
            raise BundleError(f"Map prop {name} is absent from the verified game's sprites")
        frame = dw.tpag[dw.sprites[name]["frames"][0]]
        w, h = frame["bound"]
        if not (0 <= x and x + w <= width and 0 <= y and y + h <= height):
            raise BundleError(f"Map prop {name} lies outside the current map")
        found[name].append((int(x), int(y)))
    return found


def props(dw, cut, bg):
    """The map's own animated decorations, and where each one stands.

    The game's map screen is not still: a skull blinks over Act 3, five torches
    burn along the Act 5 road, a windmill turns, fire runs round a caldera.
    Where each one stands is nowhere in the data file — the map screen is a UI
    object built in code, so there are no room coordinates — and it is read out
    of the executable instead, by `drawn_at`. Every position on this page is
    that reading: not a search, but the numbers the game itself hands
    `draw_sprite_ext`.

    The picture is the second witness, and an independent one. The artist also
    pasted most of these props into the background art at their first frame, so
    where that happened the same pixels are in both pictures. Ranking every
    offset on the whole 2902x800 map by how much of a prop's unchanging art it
    holds, six of the nine come first — and the torch's five places are the five
    best of 2,181,060, with the sixth-best holding less than half as much. That
    is a search which knows nothing about the code agreeing with the code, five
    times over on one sprite.

    The paste was made by hand and can sit a pixel off the draw, so the anchor
    is nudged onto the paste wherever the paste can be seen; see `anchor`.

    What gets drawn follows from the same reading. Where the background already
    holds a prop's still art there is no reason to paint it again and every
    reason not to: the Act 8 rune circle is 4,500 moving pixels in an 800x800
    sprite, and drawn whole it covered the window and took the map with it. So
    the only pixels drawn are the ones the background does not already show —
    everything that moves, plus any still art that was never painted in. For the
    skull and the two big Act 8 pieces that is the moving part alone; for the
    crater's swirl, the windmill's sails and the torches' flames, which the
    artist left out of the map, it is nearly the whole frame, and those frames
    are 18x45 to 339x249 rather than 800x800.

    Left out: Map_Prop_09_spr, which has one frame and is in the background
    whole. Map_Screen_Act_8_Expansion_spr, Map_Screen_Act_9_Expansion_spr and
    Map_Screen_Border_spr, which are named by no code anywhere in the 282 MB
    executable — not as an asset, not as a string — so nothing in the game draws
    them. The Act 8 one is nevertheless *in* the background: cut into 64
    hundred-pixel tiles and matched one tile at a time, 19 of them land byte for
    byte at the same offset, (1048,0), and no other offset takes more than one.
    The artist baked half of that sprite into the map art, which is why it is on
    this page already, as background. Its animation is not, because nothing
    plays it.
    """
    key = np.asarray(bg.convert("RGB"), dtype=np.uint8)
    key = (key[:, :, 0].astype(np.uint32) << 16 | key[:, :, 1].astype(np.uint32) << 8
           | key[:, :, 2])
    flat = np.asarray(bg.convert("RGB"), dtype=np.int16)
    tall, wide = flat.shape[:2]

    def held(art, still, x, y):
        """Which of a prop's unchanging pixels the background already shows at (x, y).

        The same tolerance this map has always been checked against: a pixel
        counts as held only where its three channels together differ by 8 or
        less, which on this art means the same colour.
        """
        h, w = still.shape
        if x < 0 or y < 0 or x + w > wide or y + h > tall:
            return np.zeros_like(still)
        return (np.abs(art - flat[y:y + h, x:x + w]).sum(axis=2) <= 8) & still

    def rivals(art, still, x, y):
        """How many places on the whole map hold as much of this still art as (x, y).

        One is the answer that means something: this art, in this arrangement,
        fits here and nowhere else in 2,902 by 800. Two hundred and forty still
        pixels spread evenly are enough to tell — the torch has only 189 in all
        and comes back unique.
        """
        h, w = still.shape
        ys, xs = np.nonzero(still)
        take = np.linspace(0, len(ys) - 1, min(240, len(ys))).astype(int)
        ys, xs = ys[take], xs[take]
        rows, cols = tall - h + 1, wide - w + 1
        tally = np.zeros((rows, cols), dtype=np.int32)
        for dy, dx in zip(ys.tolist(), xs.tolist()):
            c = int(art[dy, dx, 0]) << 16 | int(art[dy, dx, 1]) << 8 | int(art[dy, dx, 2])
            tally += (key[dy:dy + rows, dx:dx + cols] == c)
        return int((tally >= tally[y, x]).sum()), len(ys)

    #: How much held art is a fact rather than a coincidence, and so how much it
    #: takes to move a prop off the place its own code gives it. Measured on
    #: this map: 125 held pixels of the torch is the single best place of
    #: 2,181,060, while 23 of the crater's swirl are matched by 5,473 other
    #: places and 10 of the windmill's post by 783. A hundred sits well inside
    #: that gap.
    ANCHOR = 100

    def anchor(art, still, x, y):
        """The pixel within one of the draw whose background holds most of the art.

        The shipped background is a hand-placed copy of what the code draws and
        it lands a pixel out: one right of the code for the skull, one right and
        one down for four others, one down for all five torches. The only
        runtime terms in the game's own sum are both written zero, so that pixel
        is not the game's, it is the paste — and sitting on the paste is what
        keeps a prop from doubling its own baked edge.
        """
        tries = [(int(held(art, still, x + dx, y + dy).sum()), -(abs(dx) + abs(dy)),
                  x + dx, y + dy)
                 for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
        most, _, bx, by = max(tries)
        return (bx, by) if most >= ANCHOR else (x, y)

    out = []
    every = sorted({row["sprite"] for row in BUNDLE.read("map", {}).get("props", [])})
    places = drawn_at(dw, every)
    for spr in every:
        if not places[spr]:
            print(f"note: {spr} is named by no code in the game, so nothing draws it")
            continue
        frames = dw.sprites[spr]["frames"]
        shots = [np.asarray(cut(spr, i).convert("RGBA"), dtype=np.int16)
                 for i in range(len(frames))]
        art = shots[0][:, :, :3]
        h, w = art.shape[:2]
        solid = np.ones((h, w), dtype=bool)
        for s in shots:
            solid &= s[:, :, 3] > 250
        moves = np.zeros((h, w), dtype=bool)
        for s in shots[1:]:
            moves |= np.abs(s - shots[0]).sum(axis=2) > 12
        still = solid & ~moves

        at, need = [], moves.copy()
        for x, y in places[spr]:
            x, y = anchor(art, still, x, y)
            at.append((x, y))
            # Whatever the background does not already show has to be drawn or
            # half the prop is missing. Where one sprite stands in five places on
            # different ground, the union serves them all: a pixel drawn over the
            # identical pixel underneath changes nothing.
            need |= still & ~held(art, still, x, y)
        show = max(at, key=lambda p: held(art, still, *p).sum())
        keeps = int(held(art, still, *show).sum())
        same, probes = rivals(art, still, *show)
        witness = (f"the background holds {keeps} of its {int(still.sum())} still pixels"
                   + (", the only place on the map that does" if same == 1 else
                      f", and {same - 1} other places hold as many of the {probes} checked,"
                      f" so the picture cannot speak for it"))
        if not need.any():
            print(f"note: {spr} has {len(frames)} frame(s) and {witness} — nothing left to draw")
            continue

        # The rate the artist gave the sprite. The game does not read it: all
        # thirteen draws pass a sub-image of their own, one counter that the
        # Step event advances by the 0.15 at 14F1A62D8 every step — so the props
        # run in lockstep, at 0.15 times whatever the player set the frame rate
        # to (there is an option for it, UiUpOptionsVideoFps). With no one rate
        # to copy, the sprite's own 6 stands, and all nine agree on it.
        fps = int(dw.sprites[spr]["speed"]) or 6
        name = spr[:-4].lower().replace("map_prop_", "prop").replace("map_screen_", "")
        # One box around everything is not enough: a prop can change in two
        # places far apart — the Act 8 expansion in a rune circle and a sparkle
        # above the peaks — and a rectangle holding both is 43% of the sprite for
        # 1.6% of it moving. So the pixels are grouped and each group placed on
        # its own.
        boxes = patches(need)
        for k, box in enumerate(boxes):
            bw, bh = box[2] - box[0], box[3] - box[1]
            # A transparent gutter between the frames, and the page steps by the
            # wider figure while its window stays the frame.
            #
            # The strip slides behind a clipping box and the whole map is drawn
            # at a fractional scale, so the box's left edge lands mid-pixel and
            # the compositor samples what is beside the frame — the right-hand
            # column of the frame before it, which showed up as a hairline down
            # the left of the burning skull. Two columns of nothing there means
            # the worst it can sample is nothing.
            step = bw + GUTTER
            sheet = Image.new("RGBA", (step * len(frames), bh))
            for i in range(len(frames)):
                sheet.paste(cut(spr, i).crop(box), (step * i, 0))
            piece = name if k == 0 else f"{name}-{k}"
            picture(sheet, IMG / f"{piece}.png")
            out.append({"art": piece, "w": bw, "h": bh, "step": step, "n": len(frames),
                        "fps": fps, "at": [[x + box[0], y + box[1]] for x, y in at]})
        share = 100 * sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes) / (w * h)
        print(f"prop     {spr} — {len(at)} place(s) from the game's code, {len(frames)} frames "
              f"at {fps}/s; {witness}; draws {len(boxes)} piece(s), {share:.0f}% of {w}x{h}")
    return out


def trail(cut):
    """The dash the paths between zones are laid with, and its lit twin.

    `Mapscreen_Line_spr` is a solid 16 by 8 block, not a dash — the gap is in the
    code that places it. `Map_Zone_Line_obj`'s create event carries one number,
    32, which is what the spacing has to be for a 16-wide block: half tile, half
    nothing. So the tile is built at that width here and the page repeats it,
    which is the same picture without asking the browser to place 900 sprites.

    Nothing in the game draws these any more. The object that would is compiled
    in and never created: its index appears nowhere in the executable, as a
    constant or a name, and the sprite is referenced only from its own two event
    handlers. See the README — the paths on this page are the game's art laid
    along a route the game itself no longer draws.
    """
    size = None
    for frame, out in ((0, "link"),):
        mark = cut("Mapscreen_Line_spr", frame)
        # Laid end to end, not spaced. The 32 in the line object's create event
        # is not a gap: every column of this sprite is identical and the picture
        # is in its rows — three of gradient over four of its own shadow, which
        # is a trail seen from above, and a trail with holes in it is a dotted
        # line, which is not what the art is.
        #
        # The cold frame, which is the one the game draws. There are two, the
        # same trail in two hues, and the warm one was tried here first on a bad
        # reading: (88, 48, 102) is only the sprite's third row, its highlight,
        # and comparing that alone against ground of (95, 55, 90) said the cold
        # trail would be invisible. The rows around it are (30, 17, 35) and
        # (10, 6, 12). What the eye gets is a dark line with a lit edge along
        # its top, which is exactly how it looks in the game.
        tile = Image.new("RGBA", mark.size)
        tile.alpha_composite(mark)
        picture(tile, IMG / f"{out}.png")
        size = tile.size
    return size


#: sprites the game draws with additive blending, so their black is nothing
ADDITIVE = {"glow", "chosen"}


def strips(dw, cut, unlit):
    """The animated pieces, laid out as one row so CSS can step through them.

    The game plays these; a still map next to it looks switched off. Each
    sprite's own playback speed is written into the name, so the page does not
    have to be told what to guess: `<name>.<frames>x<fps>.png`.
    """
    for spr, out in (("Mapscreen_Zone_Effect_spr", "fx-zone"),
                     ("Mapscreen_Zone_Satanic_Glow_spr", "fx-satanic")):
        frames = dw.sprites[spr]["frames"]
        fps = int(dw.sprites[spr]["speed"]) or 6
        first = cut(spr, 0)
        # The same transparent gutter the props carry, for the same reason: the
        # strip slides behind a clipping box, the box is centred on a marker
        # with a half-pixel translate, and without two empty columns the edge
        # samples the frame beside it and draws a hairline.
        step = first.width + GUTTER
        sheet = Image.new("RGBA", (step * len(frames), first.height))
        for i in range(len(frames)):
            sheet.paste(unlit(cut(spr, i)), (step * i, 0))
        picture(sheet, IMG / f"{out}.{len(frames)}x{fps}.png")
        print(f"strip    {out} — {len(frames)} frames of {first.width}x{first.height} "
              f"at {fps}/s, laid out every {step}px; WorldMap.svelte carries these numbers")


# ── the names, in every language the game ships ──────────────────────────────
def zone_names():
    rows = {}
    with open(source_csv("translationsZone"), encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("|")
        langs = head[1:]
        for line in fh:
            p = line.rstrip("\n").split("|")
            if len(p) < 2:
                continue
            rows[p[0]] = {lang: val for lang, val in zip(langs, p[1:]) if val}
    return langs, rows


# ── what the tracker knows about items ───────────────────────────────────────
def source_csv(name):
    """Source text included in the same verified export as the numeric data."""
    if name not in BUNDLE.datasets:
        raise BundleError(f"Extractor bundle is missing required source table {name}")
    return BUNDLE.path(name)


def current_words():
    return vocabulary.Words(paths=[BUNDLE.path(name) for name in BUNDLE.datasets
                                   if name.startswith("translations") and BUNDLE.path(name).suffix.lower() == ".csv"])


def tracker_tables():
    # Keep the historical call site name while removing the second generated
    # copy of the numbers from the input chain.
    _, rooms = zone_names()
    return tables_from_items(RAW_ITEMS, rooms)


def route(nodes):
    """The paths between markers, as pairs of rooms.

    The game does not draw these. `Map_Zone_Line_obj` exists, has a create event,
    a step and a draw, and is the only thing in the game that touches the line
    sprite — and nothing anywhere creates it. So there is no route to recover,
    only one to choose, and this is the one the map itself argues for: an act in
    the order it is played, its town first, its five zones by number, its boss
    dungeon last.

    That the order is also the shape is what makes it more than a guess. Laid out
    this way the longest step inside acts I to VIII is 152 px on a map 2902 wide,
    and the middle one is 89 — the chain hugs the terrain it is drawn on, which a
    wrong order would not.

    Acts are left unjoined to each other. Those gaps run 111 to 732 px with
    nothing under them, and act VIII has no town on the map at all to join to.
    """
    def act_of(n):
        m = re.match(r"Town_(\d\d)", n["room"])
        return n["act"] or (int(m.group(1)) if m else None)

    def step(n):
        if n["kind"] == "town":
            return -1
        if "Boss" in n["room"]:
            return 99
        return int(n["room"][7:9])

    acts = {}
    for n in nodes:
        a = act_of(n)
        if a:
            acts.setdefault(a, []).append(n)

    out = []
    for a in sorted(acts):
        chain = sorted(acts[a], key=step)
        out += [[x["room"], y["room"]] for x, y in zip(chain, chain[1:])]
    return out


def types_said(say, items):
    """Each item type in the eleven, from the game's own `item_type_*` rows."""
    out = {}
    for rec in items.values():
        kind = rec.get("type")
        if kind and kind not in out:
            told = say.by_key.get("item_type_" + re.sub(r"[^a-z]", "", kind.lower()))
            if told:
                out[kind] = told
    return out


def codex(dw, raw_items, langs, tables):
    """The encyclopedia's own data and its own sheet of icons.

    A sheet apart from the map's, on purpose. The map draws 931 things and this
    draws every one the game defines; sharing would make the map page carry two
    thousand icons to show a tooltip. The bytes are duplicated and the map stays
    quick, which is the better trade for two pages that are read separately.
    """
    every = {icons.tidy((it.get("metadata") or {}).get("name"))
             for it in raw_items if (it.get("metadata") or {}).get("name")}
    every.discard("")
    place, missing, sheet, guessed, chosen = icons.build(
        dw, raw_items, every, IMG / "codex.png", told=ITEM_ICONS)

    say = current_words()
    # What a potion grants, read out of the game beside the items themselves
    talent_rows = TALENT_ROWS
    # Current numeric grants require the native map-key contract. Reference
    # names remain separate evidence and cannot repair a missing native key.
    kit_data = gear.read(HERE / "build" / "planner" / "gear")
    said_by = {}
    for t in talent_rows:
        told = say.by_key.get(f"talent_name_{t['key']}") or {}
        if told.get("en"):
            said_by.setdefault(gear.flat(told["en"]), t)
    named_talent = {}
    for key, bonuses in gear.grants(kit_data, {
            (r["metadata"] or {}).get("tkey"): {"names": {"en": (r["metadata"] or {}).get("name")}}
            for r in raw_items if (r.get("metadata") or {}).get("tkey")}).items():
        if len(bonuses) != 1:
            continue
        got = said_by.get(gear.flat(bonuses[0][0]))
        if got:
            named_talent[key] = got

    talent_id_contract = (BUNDLE.read("coverage", {}) or {}).get("native_talent_id_contract")
    talent_id_source_sha256 = next((row["sha256"] for row in BUNDLE.game["files"]
                                   if row["path"] == "Hero_Siege.exe"), None)
    items, vocab, kits = encyclopedia.build(
        raw_items, source_csv("translationsItem"), langs, place, icons.tidy, tables, say,
        talent_rows, named_talent, BUNDLE.read("stats", {}),
        talent_id_contract=talent_id_contract, talent_id_source_sha256=talent_id_source_sha256,
        item_aura_slot_contract=AURA_SLOTS, item_effect_contract=ITEM_EFFECTS,item_condition_contract=ITEM_CONDITIONS)
    (DIAGNOSTICS / "item-record-coverage.json").write_text(
        json.dumps(verify_item_coverage(raw_items, items), indent=2), encoding="utf-8")
    attach_exclusive_sources(raw_items, items, BUNDLE.read("drop_sources"))

    # What the game calls each stat, joined on meaning — see words.Words.stats
    told = say.stats([v["sid"] for v in vocab])
    for v in vocab:
        if told.get(v["sid"]):
            v["names"] = told[v["sid"]]
    seen = sum(v["n"] for v in vocab)
    named = sum(v["n"] for v in vocab if v.get("names"))
    print(f"stats    {len(told)} of {len(vocab)} named by the game, which is "
          f"{named} of {seen} stat lines a reader meets ({100 * named // seen}%)")

    # What the game states about an item that the datamined tables leave out:
    # whether a stat is a percentage, how many sockets it rolls, and what a set
    # gives for wearing more of it
    told_unit = gear.units(kit_data, vocab, items, lambda k: say.by_key.get(k))
    for v in vocab:
        if told_unit.get(v["sid"]) == "percent" and not v.get("unit") and v.get('unitSource')!='native_item_effect':
            v["unit"] = "%"
            v["unitSource"] = "reference"
    fitted = gear.sets(kit_data, kits, lambda k: say.by_key.get(k), told_unit)
    set_names = {names['en']: names for key, names in say.by_key.items()
                 if key.endswith('setname') and names.get('en')}
    set_coverage = reference_sets.merge(items, kits, SET_REFERENCE, set_names)
    (DIAGNOSTICS / 'reference-set-coverage.json').write_text(
        json.dumps(set_coverage, ensure_ascii=False, indent=2), encoding='utf-8')
    fitted = sum(bool(kit.get('bonuses')) for kit in kits.values())
    for kit in kits.values():
        if kit.get("bonuses"):
            kit.setdefault('provenance', {}).setdefault('bonuses', 'reference')
    reference_units = {v["sid"] for v in vocab if v.get("unitSource") == "reference"}
    for item in item_records(items):
        all_stats = item.get("stats", []) + [row for group in item.get("more", []) for row in group["stats"]]
        if any(row["sid"] in reference_units for row in all_stats):
            item.setdefault("reference", []).append("stat units")

    # Preserve external suggestions as reference evidence. They never become
    # a current native grant or replace an unresolved numeric reference.
    by_said = {}
    for t in talent_rows:
        told = say.by_key.get(f"talent_name_{t['key']}") or {}
        if told.get("en"):
            by_said.setdefault(gear.flat(told["en"]), t)
    named_skill = 0
    aura_names = {gear.flat(row['name']) for row in kit_data['granted'] if row.get('aura')}
    for key, bonuses in gear.grants(kit_data, items).items():
        current = {gear.flat((grant.get("names") or {}).get("en") or "")
                   for grant in items[key].get("grants") or []}
        suggestions = []
        for skill, level in bonuses:
            got = by_said.get(gear.flat(skill))
            if not got or gear.flat(skill) in current:
                continue
            span = level if len(level) == 2 else [level[0], None]
            suggestion = encyclopedia.spoken(got, span, lambda k: say.by_key.get(k))
            suggestion['kind'] = 'aura' if gear.flat(skill) in aura_names else 'skill'
            suggestions.append(suggestion)
        if suggestions:
            items[key]["reference_grants"] = suggestions
            items[key].setdefault("reference", []).append("granted skill")
            named_skill += 1
    print(f"grants   {sum(1 for r in items.values() if r.get('grants'))} items name the talent "
          f"they grant; {named_skill} other records keep separate planner suggestions")
    reference_sources.merge_records(items, CHEST_REFERENCE)
    print(f"gear     {sum(1 for v in vocab if v.get('unit') == '%')} of {len(vocab)} stats are "
          f"percentages, {fitted} of {len(kits)} sets say what they give")

    out = {"source": SOURCE, "langs": langs, "sheet": {"w": sheet[0], "h": sheet[1]},
           "words": {**said.SAID, **say.vocab()}, "types": types_said(say, items),
           "stats": vocab, "sets": kits, "items": items,
           "unholy": unholy.labelled(say, BUNDLE.read("unholy"))}
    with_stats = sum(1 for r in items.values() if r.get("stats") or r.get("more"))
    with_lore = sum(1 for r in items.values() if r.get("lore"))
    print(f"codex    {len(items)} items, {with_stats} with stats, {with_lore} with lore, "
          f"{len(vocab)} distinct stats, {len(kits)} sets")
    print(f"         icons {len(place)} cut into a {sheet[0]}x{sheet[1]} sheet, "
          f"{len(missing)} without one")
    rows = squeeze(out)

    # Which class an item is for, argued from what its stats do — after the
    # squeeze, so a stat line names itself by its place in the vocabulary
    profiles = suits.profile(talent_rows, HERE / "build" / "planner")
    suits.tag(items, profiles, [v["sid"] for v in vocab])
    borne = gear.auras(kit_data, items, [v["sid"] for v in vocab])
    suits.report(items, profiles)
    print(f"         {borne} carry an aura, which is nobody's in particular")
    out["classes"] = [{"id": c, "names": class_said(say, c)} for c in sorted(profiles)]
    out["about"] = suits.words(lambda k: say.by_key.get(k))

    report(langsplit.write(out, langs, DATA / "codex.json"))
    print(f"squeeze  {rows} stat lines say their name and unit by number now")

    # The class trees, out of the same table the potions' talents come from
    subs = [l.split("|")[0] for l in
            source_csv("translationsSubTalent").read_text("utf-8", "replace").splitlines() if l.strip()]
    tree, bound, wanted, known, loose = skilltree.build(
        talent_rows, subs, lambda k: say.by_key.get(k), langs, HERE / "build" / "planner",
        talent_type_contract=(BUNDLE.read("coverage", {}) or {}).get("native_talent_type_contract"),
        talent_type_source_sha256=talent_id_source_sha256,
        talent_type_inheritance_contract=(BUNDLE.read("coverage", {}) or {}).get("native_talent_type_inheritance_contract"),
        talent_defaults_contract=(BUNDLE.read("coverage", {}) or {}).get("talent_constructor_defaults_contract"),
        talent_type_inventory=BUNDLE.game["files"], talent_id_contract=talent_id_contract)
    for c in tree["classes"]:
        c["names"] = class_said(say, c["id"])
    tree["words"] = {**said.SAID, **say.vocab()}
    tree["source"] = SOURCE
    boxes, nodes, sheet_size, iconless, faces, blank = skilltree.art(
        dw, talent_rows, IMG / "skills.png", HERE / "build" / "planner")
    tree["nodes"] = nodes
    tree["faces"] = faces
    for key, s in tree["skills"].items():
        if key in boxes:
            s["icon"] = boxes[key]
    tree["sheet"] = {"w": sheet_size[0], "h": sheet_size[1]}
    print(f"         icons {len(boxes)} cut into a {sheet_size[0]}x{sheet_size[1]} sheet, "
          f"{len(iconless)} without one")
    print(f"         nodes {sum(len([x for x in v if x]) for v in faces['at'].values())} "
          f"cut into a {faces['w']}x{faces['h']} sheet"
          + (f", {len(blank)} trees without art" if blank else ""))
    skilltree.report(tree, bound, wanted, known, loose)
    report(langsplit.write(tree, langs, DATA / "skills.json"))


def class_said(say, name):
    """What the game calls a class, in every language it says it in.

    The keys disagree with themselves: some classes are keyed as one word and
    some as two — `stormWeaver` beside `demon_slayer` — and a class our tables
    call `Stormweaver` matches neither by lowering it. What both sides do agree
    on is the English name, which is the other way the game's tables are
    indexed, so a key that misses is asked for again by what it says.
    """
    return (say.by_key.get(name.lower())
            or say.by_english.get(vocabulary.squash(name))
            or {"en": name})


def squeeze(out):
    """Take out of the file what the file already says somewhere else.

    Four things were written twice. Each item repeated its own dictionary key
    (55 KB) and its English name (43 KB) beside `names.en`. Every one of the
    8678 stat lines carried the stat's English `text` and its `unit` (226 KB),
    both of which the `stats` vocabulary at the root already holds under the
    same `sid` — checked: not one of the 8678 disagreed with it. And the `sid`
    itself is a long identifier repeated up to 379 times, so a line names its
    stat by its index into that vocabulary instead (137 KB).

    Together 461 KB of the raw 2237, and `hydrate` in src/codex/Codex.svelte
    puts all four back on arrival so nothing downstream knows the difference.
    """
    at = {v["sid"]: i for i, v in enumerate(out["stats"])}
    lines = 0
    for it in item_records(out["items"]):
        it.pop("key", None)
        if it.get("name") == (it.get("names") or {}).get("en"):
            it.pop("name", None)
        for row in [*it.get("stats", []),
                    *(r for m in it.get("more") or [] for r in m["stats"])]:
            row.pop("text", None)
            row.pop("unit", None)
            row["sid"] = at[row["sid"]]
            lines += 1
    return lines


def report(made):
    """What a reader downloads, which is the only size that matters."""
    kb = langsplit.over_the_wire
    worst = max(made[1:], key=lambda p: p.stat().st_size)
    print(f"written  {made[0]}  ({made[0].stat().st_size // 1024} KB, "
          f"{kb(made[0])} KB gzipped) + {len(made) - 1} languages")
    print(f"         a first visit is {kb(made[0])} KB in English and "
          f"{kb(made[0]) + kb(worst)} KB at worst ({worst.suffixes[0][1:]})")


# ── a room name to the code the drop tables use ──────────────────────────────
def zone_code(room):
    """`Act_01_04` is zone `1-4`; a boss dungeon of act 1 is `1-BD`.

    The drop tables say which act and which zone, not which room, so the two
    have to be joined on that. Towns and the cabin drop nothing and get None.
    """
    m = re.fullmatch(r"Act_(\d\d)_(\d\d)", room)
    if m:
        return f"{int(m.group(1))}-{int(m.group(2))}"
    m = re.match(r"Act_(\d\d)_Boss(?:_Dungeon)?", room)
    if m:
        return f"{int(m.group(1))}-BD"
    return None




#: The dungeon each zone opens onto, and the key that opens it.
#:
#: Twenty-six of the forty-six zones have one, and every one of them is locked:
#: the door stands in the zone and asks for a key. That is why nothing in the
#: game's own data lines up with which zones have a dungeon — the preset chunk
#: tagged `dngSpawner` covers only nineteen of these twenty-six, and one of the
#: nineteen (3-3) is not on this list at all.
#:
#: So it is written down rather than derived, from the community's own list at
#: hero-siege-helper.vercel.app/dungeons, and checked against the game where it
#: could be: 8-1 Gladsheim Halls, 8-2 Naga Temple and 8-3 Muspelheim were all
#: three confirmed in play, and 1-2 was confirmed to have none.
#:
#: The room is the dungeon's first floor, which is what the game names — a
#: deeper one is "Ancient City Level 2" and the same place. `dungeon_title`
#: takes the floor number back off.
#:
#: The key is spelled as the game spells it, so its name can be looked up in the
#: game's own item table and said in all eleven languages. Not as the site's item
#: list spells it: Treasure Key and Boreal Key are in the game and not in that
#: list, because nothing has ever recorded them dropping.
KEY_DUNGEONS = {
    "1-1": ("Rat_Den_01_rm", "Smelly Cheese"),
    "1-3": ("Pumpkin_Cellar_01_rm", "Cellar Key"),
    "1-4": ("Black_Tower_01_rm", "Tower Key"),
    "2-1": ("Frozen_Cellar_01_rm", "Frosted Key"),
    "2-5": ("Ancient_City_01_rm", "Ancient Key"),
    "3-2": ("Sand_Cave_01_rm", "Shovel Key"),
    "3-3": ("Forgotten_City_01_rm", "Mystic Key"),
    "3-5": ("Cauflax_Tomb_01_rm", "Tomb Key"),
    "4-1": ("Old_Copper_Mine_01_rm", "Copper Key"),
    "4-2": ("Abandoned_Mine_01_rm", "Rusted Key"),
    "4-5": ("Devils_Hole_01_rm", "Devil's Key"),
    "5-1": ("Fuji_Crater_01_rm", "Pickaxe"),
    "5-2": ("Underground_Garden_01_rm", "Garden Key"),
    "5-3": ("Kaojin_Temple_01_rm", "Battle Key"),
    "5-5": ("Temple_Trapdoor_01_rm", "Golden Key"),
    "6-1": ("Unmarked_Grave_01_rm", "Axe Key"),
    "6-4": ("Arm_Storage_01_rm", "Storage Key"),
    "7-2": ("Distorted_Horizons_01_rm", "Warp Key"),
    "8-1": ("Gladsheim_Halls_01_rm", "Valor Key"),
    "8-2": ("Naga_Temple_01_rm", "Naga Scale Key"),
    "8-3": ("Muspelheim_01_rm", "Magma Key"),
    "8-5": ("Niflhel_01_rm", "Helflame Torch"),
    "9-1": ("Act_09_Wasp_Nest_rm", "Hive Key"),
    "9-2": ("Act_09_Treasure_Dungeon_rm", "Treasure Key"),
    "9-3": ("Act_09_Monster_Dungeon_rm", "Tablet of Parasite"),
    "9-4": ("Act_09_Boreal_Dungeon_rm", "Boreal Key"),
}

#: What each language puts before a floor number. The game names a dungeon's
#: floors and not the dungeon, so "Ancient City Level 1" has to lose its tail
#: to be a label — and losing only the digit would leave "Ancient City Level".
LEVEL_WORDS = (
    "level", "lvl", "уровень", "ур", "nivel", "niveau", "poziom", "nível",
    "taso", "ebene", "レベル", "레벨", "层", "等级",
)


def dungeon_title(room, names):
    """The dungeon's name, without the floor number the game hangs off it.

    Per language, because word order is: German writes the level word where
    English does not, and a language that does not number at all is left alone.
    """
    out = {}
    for lang, said in (names.get(room) or {}).items():
        text = re.sub(r"[\s:.\-–—]*\d+$", "", said).strip()
        head = text.rsplit(" ", 1)
        if len(head) == 2 and head[1].strip(".").lower() in LEVEL_WORDS:
            text = head[0].strip()
        out[lang] = text or said
    return out


def dungeon_nodes(nodes, per_code, t, say, names):
    """A marker for the dungeon each zone that has one opens onto.

    Which zones those are, and what they open onto, is `KEY_DUNGEONS`. There
    used to be one marker per act instead, standing beside the act's boss
    dungeon, because nothing here knew where a dungeon was — and one mark for a
    whole act reads as though any zone in it might hold one.

    What falls in one is still known only per act: the drop tables are written
    `4-D` and never `4-2-D`, and no individual dungeon is ever named as a
    source. So every dungeon of an act carries that act's list, which is the
    whole of what the game says about it.

    It stands beside its zone, on whichever side has the most room — counting
    the markers already placed, or two neighbouring zones would put theirs in
    the same spot. Never above: that is where the zone's name is. It carries no
    name on the map for the same reason; the panel names it.
    """
    made = []
    for node in nodes:
        act, code = node["act"], node["code"]
        if code not in KEY_DUNGEONS or not act:
            continue
        room, key = KEY_DUNGEONS[code]
        drops = sorted(per_code.get(f"{act}-D", []), key=lambda name: (
            -(t["TIER_BY_NAME"].get(name) or 0), t["DROP_RATE"].get(name, 1 << 40)))
        # 24px of zone marker and 22 of this leave 7px of daylight at 30.
        away = 30
        placed = [o for o in nodes if o is not node] + made
        near = lambda x, y: min((abs(o["x"] - x) + abs(o["y"] - y)) for o in placed)
        x, y = max(
            ((node["x"] + away, node["y"]), (node["x"] - away, node["y"]),
             (node["x"], node["y"] + away)),
            key=lambda c: near(*c))
        made.append({
            "room": room,
            "x": x,
            "y": y,
            "kind": "dungeons",
            "code": f"{act}-D",
            "act": act,
            "name": dungeon_title(room, names),
            "drops": drops,
            "source": {"kind": "inferred", "method": "display_offset_from_native_zone_marker",
                       "anchor_room": node["room"], "offset": {"x": x - node["x"], "y": y - node["y"]},
                       "reference": {"kind": "reference", "name": "Hero Siege Helper dungeon catalogue",
                                     "url": "https://hero-siege-helper.vercel.app/dungeons", "verified_for_game_build": False}},
            # The English name, with the rest of the languages put in `words`
            # below rather than on the record: `langsplit` moves a node's `name`
            # into the per-language files and leaves everything else in English,
            # and `words` is already one file per language. Not an item id
            # either — two of the twenty-six keys are in the game's item table
            # and in no drop table, so there is no item record to point at.
            "key": key,
        })
    return made


def main():
    (DIAGNOSTICS / "extraction-coverage.json").write_text(json.dumps({
        "source": SOURCE,
        "coverage": BUNDLE.read("coverage"),
        "drop_sources": BUNDLE.read("drop_sources"),
        "map": (BUNDLE.read("map", {}) or {}).get("coverage"),
        "missing_datasets": [name for name in ("map", "drop_sources", "unholy", "stats", "assets") if name not in BUNDLE.datasets],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    dw, w, h, tile, decor = art()
    langs, names = zone_names()
    t = tracker_tables()

    # item -> the zone codes it falls in
    per_code = {}
    for item, codes in t["DROP_ZONES"].items():
        for c in codes:
            per_code.setdefault(c, []).append(item)

    nodes = []
    map_data = BUNDLE.read("map", {})
    if not map_data.get("nodes"):
        raise BundleError("Extractor bundle has no verified map nodes; rebuild the map dataset")
    if (map_data.get("width"), map_data.get("height")) != (w, h):
        raise BundleError("Extractor map coordinates and current background dimensions do not match")
    for r in map_data["nodes"]:
        room = r["room"]
        if room in MAP_MARKER_EXCLUSIONS:
            continue
        code = zone_code(room)
        kind = ("town" if room.startswith("Town")
                else "dungeon" if "Boss" in room
                else "zone")
        drops = sorted(per_code.get(code, []), key=lambda n: (
            -(t["TIER_BY_NAME"].get(n) or 0), t["DROP_RATE"].get(n, 1 << 40)))
        nodes.append({
            "room": room,
            "x": int(float(r["x"])),
            "y": int(float(r["y"])),
            "kind": kind,
            "code": code,
            "act": int(room[4:6]) if room.startswith("Act_") else None,
            "name": names.get(room, {}),
            "drops": drops,
            "source": r.get("source"),
        })

    # The last zone of each act is the one its boss dungeon opens off, and the
    # game marks it: bigger, and purple. Its own kind rather than a flag on the
    # record, because both drawing paths pick a marker's art by kind and the
    # canvas one keeps one box per kind. It is still a zone, and `KIND` says so.
    last = {}
    for n in nodes:
        if n["kind"] == "zone" and n["act"]:
            step = int(n["room"][7:9])
            if step > last.get(n["act"], (-1, None))[0]:
                last[n["act"]] = (step, n)
    for _, n in last.values():
        n["kind"] = "gate"

    links = route(nodes)

    # Every item the tables say anything about, not only the ones a marker
    # carries: the panel is for looking things up, and "drops from a Crystal
    # Chest, nowhere on the map" is an answer worth being able to give.
    known = set(t["DROP_RATE"]) | set(t["DROP_PLACES"]) | set(t["DROP_ZONES"])
    items = {}
    for name in sorted(known):
        rarity = t["RARITY_BY_NAME"].get(name)
        # an item off a scale the tables do not read claims nothing
        if not rarity:
            continue
        items[name] = {
            "rarity": rarity,
            "tier": t["TIER_BY_NAME"].get(name),
            "rate": t["DROP_RATE"].get(name),
            "chase": t["DROP_CHASE"].get(name),
            "places": t["DROP_PLACES"].get(name, []),
            "zones": t["DROP_ZONES"].get(name, []),
        }

    # the icons, cut from the game and packed into one sheet
    raw_items = RAW_ITEMS
    place, missing, sheet, guessed, from_sprite = icons.build(
        dw, raw_items, set(items), IMG / "items.png", told=ITEM_ICONS)
    for name, box in place.items():
        if name in items:
            items[name]["icon"] = box
    # written out for the same reason the bosses' choices are: a name-matched
    # icon is an argument, and an argument should be readable
    (DIAGNOSTICS / "icons-chosen.json").write_text(
        json.dumps(dict(sorted(from_sprite.items())), ensure_ascii=False, indent=1),
        encoding="utf-8")

    # what the game itself says, folded in before anything is grouped
    # Item dropPlaces is part of the verified export. Independent historical
    # game_drops.json files are not input to a current-build publication.

    # Before the bosses are gathered: a boss's own list says whether each thing
    # it drops is Inferno-only, and for a name the game gave us by mechanism
    # rather than by place that answer is the item's.
    inferno = bosses.mark_inferno(items)
    split_minded = bosses.disagrees_about_inferno(items)

    who = bosses.collect(items)
    reference_chest_edges = reference_sources.merge_map(items, who, CHEST_REFERENCE)
    print(f"sources  {reference_chest_edges} published chest entries retained as unverified reference data")
    listed = bosses.game_list(source_csv("translationsEnemy"))
    for name, row in who.items():
        row["kind"] = bosses.classify(name, listed, row["kind"])

    # An act boss stands at the end of its act, in a dungeon the map already
    # draws a marker for. It goes on that marker rather than on a shelf: the
    # shelf is for the fights the map has nowhere to put. See bosses.ACT_OF for
    # how each one's act was established.
    by_act = {}
    for n in nodes:
        if n["kind"] == "dungeon":
            assert n["act"] not in by_act, f'two dungeons in act {n["act"]}'
            by_act[n["act"]] = n
    for name, row in who.items():
        if row["kind"] == "act":
            by_act[bosses.ACT_OF[name.lower()]]["boss"] = name

    # There is no portrait set in the game, so these are asked of the objects,
    # picked by name where that fails, and written out as a labelled sheet as
    # well — to be looked at, not trusted. Everything gets one: the act bosses
    # need a face on the map for the same reason the others need one on a shelf.
    faces, faceless, face_sheet, chosen = portraits.build(
        dw, list(who), IMG / "bosses.png", contact_png=DIAGNOSTICS / "bosses-contact.png")
    for boss, box in faces.items():
        who[boss]["icon"] = box
    # written out so the choice can be argued with rather than taken on trust
    (DIAGNOSTICS / "chosen.json").write_text(
        json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")

    # What the game calls each of these, in the eleven it ships. Only what it
    # actually carries — a name it has none for stays in English, and the count
    # below says how many that is.
    say = current_words()
    # After the chain of a run is drawn, so they join nothing — a dungeon is not
    # a step on the way through an act — and after the vocabulary is up, which
    # is what gives them their names.
    nodes += dungeon_nodes(nodes, per_code, t, say, names)
    restored = reference_zones.merge_map(items, nodes, ZONE_REFERENCE)
    print(f"sources  {restored} published zone entries retained as unverified reference data")
    marker_coverage = verify_map_marker_sources(map_data["nodes"], nodes)
    SOURCE["map_markers"] = {key: value for key, value in marker_coverage.items() if key != "references"}
    (DIAGNOSTICS / "map-marker-coverage.json").write_text(
        json.dumps(marker_coverage, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, it in items.items():
        told = say.of(name)
        if told:
            it["names"] = told
    for name, row in who.items():
        told = say.of(name)
        if told:
            row["names"] = told
    for n in nodes:
        n["drops"] = n["drops"]          # untouched; names ride on the items
    # The place strings the cards list are not all shelf entries — the tables
    # write "Uber Reaper (Inferno Difficulty)" where the shelf says "Shade of
    # Death (Uber Reaper)" — so each distinct one is looked up on its own.
    spoken = {}
    for it in items.values():
        for where in it.get("places") or []:
            if where and where not in spoken:
                told = say.of(where)
                if told:
                    spoken[where] = told

    print(f"words    {sum(1 for i in items.values() if i.get('names'))} of {len(items)} items and "
          f"{sum(1 for b in who.values() if b.get('names'))} of {len(who)} sources named in 11 languages")
    print(f"         {len(spoken)} of the place strings on the cards are named too")
    if say.missed:
        rest = sorted(say.missed)
        print(f"         {len(rest)} the game has no name for, e.g. {', '.join(rest[:4])}")

    # the private notes the build passed between its own steps do not go out
    for it in items.values():
        it.pop("_machinery", None)

    codex(dw, raw_items, langs, t)

    # The Bounty Board's own page. Its quests are named and worded by the game
    # in all eleven languages; which quests are the board's is the one thing
    # written down, and build/bounty.py says on what evidence.
    board_langs, quests = bounty.collect(GAME, source_csv("translationsQuest"))
    board = {
        "source": SOURCE,
        "langs": board_langs,
        "words": {**said.SAID, **say.vocab()},
        "quests": quests,
    }
    report(langsplit.write(board, board_langs, DATA / "bounty.json"))
    goals = sum(len(q["goals"]) for q in quests)
    print(f"bounty   {len(quests)} quests off the board, {goals} objectives")

    out = {
        "source": SOURCE,
        "map": {"w": w, "h": h},
        "bosses": who,
        "bossSheet": {"w": face_sheet[0], "h": face_sheet[1]},
        "langs": langs,
        "tiers": t["TIER_LETTERS"],
        "sheet": {"w": sheet[0], "h": sheet[1]},
        # …and the keys the dungeons ask for, which the game names in its item
        # table whether or not anything has recorded one dropping.
        "words": {**said.SAID, **say.vocab(),
                  **{k: v for _, k in KEY_DUNGEONS.values() if (v := say.of(k))}},
        "places": spoken,
        "nodes": nodes,
        "links": links,
        "linkTile": list(tile),
        "props": decor,
        "items": items,
    }
    made = langsplit.write(out, langs, DATA / "map.json")

    placed = sum(1 for n in nodes if n["drops"])
    print(f"map      {w}x{h}")
    print(f"nodes    {len(nodes)}  ({placed} of them drop something)")
    print(f"items    {len(items)} with a rarity, {sum(1 for i in items.values() if i['zones'])} of them tied to a zone")
    print(f"names    {len(langs)} languages: {', '.join(langs)}")
    kinds = {k: sum(1 for b in who.values() if b["kind"] == k)
             for k in ("uber", "act", "source", "other")}
    print(f"         {kinds['uber']} summoned, {kinds['act']} act bosses (already on the map), "
          f"{kinds['source']} chests and the like, {kinds['other']} other")
    print(f"bosses   {len(who)} that drop something; "
          f"{sum(1 for b in who.values() if b['inferno_only'])} only on Inferno")
    print(f"faces    {len(faces)} bosses drawn, {len(faceless)} without: {chr(44).join(faceless) or chr(45)}")
    (DATA / "source.json").write_text(json.dumps(SOURCE, ensure_ascii=False, indent=2), encoding="utf-8")
    BUNDLE.validate_game(GAME)
    print(f"inferno  {inferno} items fall nowhere but on Inferno")
    for name, places in split_minded:
        print(f"         {name} is stated both ways: {places}")
    print(f"icons    {len(place)} cut into a {sheet[0]}x{sheet[1]} sheet, {len(missing)} without one")
    if guessed:
        print(f"         {len(guessed)} matched by nearest name, e.g. {guessed[0]}")
    if missing:
        print(f"         no sprite for: {', '.join(missing[:6])}{' …' if len(missing) > 6 else ''}")
    report(made)


if __name__ == "__main__":
    if STAGING_ONLY:
        main()
    else:
        with BuildLock(HERE):
            recover(HERE / "public")
            main()
            publish(OUTPUT, HERE / "public")
            # All generated directories were moved. This is only the empty
            # staging directory created above, never a recursive deletion.
            OUTPUT.rmdir()
