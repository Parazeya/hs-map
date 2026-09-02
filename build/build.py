"""Build the map site's data and art out of the game.

Everything the page needs comes from two places and nothing is hand-typed:

  the game        the map background, the node sprites, and the zone names in
                  eleven languages (translationsZone.csv)
  the tracker     which items drop where, at what rate, and how the game grades
                  them — e:\\Workspace\\HeroSiege\\src\\items.js, itself built
                  from the game by that project's own extractor

The node positions come from tools/map/map_nodes.csv in the tracker, recovered
from the compiled code; see that file's header.

    python build/build.py
"""

import csv
import json
import re
import struct
import sys
from pathlib import Path

# Item names carry characters a Windows console's default code page cannot
# encode, and printing one killed the run after every file was already written.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import against_game
import bosses
import encyclopedia
import words as vocabulary
import icons
import langsplit
import said
import merge_game
import gear
import skills as skilltree
import suits
import portraits
import unholy

HERE = Path(__file__).resolve().parent.parent
TRACKER = Path(r"e:\Workspace\HeroSiege")
GAME = Path(r"F:\Games\Steam\steamapps\common\HeroSiege\bin")

sys.path.insert(0, str(TRACKER / "tools"))
from datawin import DataWin           # noqa: E402
import yytex                          # noqa: E402
import numpy as np
from PIL import Image                 # noqa: E402

IMG = HERE / "public" / "img"

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
DATA = HERE / "public" / "data"
IMG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)


# ── the art ──────────────────────────────────────────────────────────────────
def art():
    dw = DataWin()
    # The map screen has its own texture page, and naming the file outright is
    # the shortest way to it. Everything else — the boss portraits — goes the
    # long way round, through TGIN and whichever page the sprite landed on.
    page = yytex.decode_file(GAME / "gui_mapscreen_tex_0.yytex")

    def cut(name, idx=0):
        t = dw.tpag[dw.sprites[name]["frames"][idx]]
        x, y, w, h = t["src"]
        im = Image.new("RGBA", t["bound"])
        im.paste(page.crop((x, y, x + w, y + h)), t["render"])
        return im

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
        "town": ("Mapscreen_Zone_Town_spr", 1),
        "dungeon": ("Mapscreen_Zone_Boss_Dungeon_spr", 1),
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

#: Where the game's own code lives. The map screen is a UI object built in
#: code, not a room, so its props' places are constants in here and nowhere in
#: the data file.
EXE = GAME / "Hero_Siege.exe"

#: A double read out of .rdata: `movsd xmmN,[rip+rel32]`, with or without the
#: REX byte the upper eight registers need.
RIPLOAD = re.compile(rb"\xf2[\x40-\x4f]?\x0f\x10[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.S)

#: How far in front of a draw its two coordinates are written. Measured over
#: all thirteen: the y between 365 and 396 bytes back, the x between 182 and
#: 201, so half a kilobyte reaches both and nothing older.
REACH = 512


def sprite_table(dw):
    """Every sprite's index, size and origin, straight out of SPRT.

    `datawin` hands over the frames and the speed; the origin has to come from
    the record itself, because `draw_sprite_ext` places a sprite by its origin
    and this page places it by its corner. It is fields 12 and 13, after the six
    margins and the four flags: 21,67 for Map_Prop_01_spr, which is what
    `hse-extractor --mapprops` reads for the same sprite.
    """
    off, _ = dw.chunks["SPRT"]
    b = dw.raw
    n = struct.unpack_from("<I", b, off)[0]
    out = {}
    for i, p in enumerate(struct.unpack_from(f"<{n}I", b, off + 4)):
        name = dw.string(struct.unpack_from("<I", b, p)[0])
        w, h = struct.unpack_from("<ii", b, p + 4)
        ox, oy = struct.unpack_from("<ii", b, p + 48)
        out[name] = (i, w, h, ox, oy)
    return out


def drawn_at(dw, names):
    """Where the map screen's code draws each of these sprites: corners, in map pixels.

    The sprite names are not in the executable at all — searched as strings, all
    eleven come back zero. What is in it is the asset the compiler wrote in
    their place: `draw_sprite_ext` is handed an RValue whose low dword is the
    sprite's SPRT index and whose top half marks it an asset, so Map_Prop_01_spr
    at index 12552 is the eight bytes of 0100000100003108h, and that is unique
    enough to find every draw of it in 282 MB. Nine props come back as thirteen
    draws — Map_Prop_03_spr five times, the five torches.

    Each draw's place is two doubles in .rdata, loaded a few hundred bytes in
    front of the sprite: the y first, then the x, both added to the map's own
    scroll before the call. The pair is read in that order because the other
    order puts Map_Prop_08_spr at y=1277 on a map 800 tall.

    The same thirteen corners come out of `hse-extractor --mapprops`, which
    disassembles the event and reads the call's arguments properly rather than
    scanning for the loads in front of it. Two readers, one answer, to the pixel.
    """
    exe = EXE.read_bytes()
    pe = struct.unpack_from("<I", exe, 0x3c)[0]
    count = struct.unpack_from("<H", exe, pe + 6)[0]
    optional = struct.unpack_from("<H", exe, pe + 20)[0]
    secs = []
    for i in range(count):
        o = pe + 24 + optional + i * 40
        vsz, va, rsz, ra = struct.unpack_from("<IIII", exe, o + 8)
        secs.append((va, max(vsz, rsz), ra, rsz))

    def in_file(rva):
        for va, size, ra, rsz in secs:
            if va <= rva < va + size and rva - va < rsz:
                return ra + rva - va
        return None

    def rva_of(pos):
        for va, size, ra, rsz in secs:
            if ra <= pos < ra + rsz:
                return va + pos - ra
        return None

    table = sprite_table(dw)
    found = {}
    for name in names:
        i, w, h, ox, oy = table[name]
        asset = (0x0100000100000000 | i).to_bytes(8, "little")
        spots = []
        for site in re.finditer(re.escape(asset), exe):
            head = exe[site.start() - REACH:site.start()]
            reads = []
            for load in RIPLOAD.finditer(head):
                end = rva_of(site.start() - REACH + load.end())
                at = in_file(end + struct.unpack_from("<i", load.group(1))[0])
                if at is not None:
                    reads.append(struct.unpack_from("<d", exe, at)[0])
            if len(reads) < 2:
                raise SystemExit(f"{name}: a draw at {rva_of(site.start()):#x} with no place")
            y, x = reads[-2:]
            # A misread would put a prop somewhere it cannot be, and a prop in
            # the wrong place is worse than a prop missing, so say so and stop.
            if not (0 <= x - ox and x - ox + w <= 2902 and 0 <= y - oy and y - oy + h <= 800):
                raise SystemExit(f"{name}: read a place off the map, {x},{y}")
            spots.append((int(x) - ox, int(y) - oy))
        found[name] = spots
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
    every = [f"Map_Prop_0{i}_spr" for i in range(1, 10)]
    every += ["Map_Screen_Act_8_Expansion_spr", "Map_Screen_Act_9_Expansion_spr"]
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
    with open(GAME / "translationsZone.csv", encoding="utf-8") as fh:
        head = fh.readline().rstrip("\n").split("|")
        langs = head[1:]
        for line in fh:
            p = line.rstrip("\n").split("|")
            if len(p) < 2:
                continue
            rows[p[0]] = {lang: val for lang, val in zip(langs, p[1:]) if val}
    return langs, rows


# ── what the tracker knows about items ───────────────────────────────────────
def tracker_tables():
    text = (TRACKER / "src" / "items.js").read_text(encoding="utf-8")

    def grab(name):
        head = f"export const {name} = "
        s = text.index(head) + len(head)
        while text[s].isspace():
            s += 1
        close = "}" if text[s] == "{" else "]"
        j = text.index(close + ";", s)
        body = text[s:j + 1]
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # the small hand-written tables are ordinary JS, single quotes and
            # all; the big generated ones are already JSON
            return json.loads(re.sub(r"'([^']*)'", r'"\1"', body))

    return {n: grab(n) for n in
            ("DROP_ZONES", "DROP_PLACES", "DROP_RATE", "DROP_CHASE",
             "RARITY_BY_NAME", "TIER_BY_NAME", "TIER_LETTERS")}


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
        dw, raw_items, every, IMG / "codex.png")

    say = vocabulary.Words(GAME)
    # What a potion grants, read out of the game beside the items themselves
    talent_file = TRACKER / "tools" / "data" / "helper" / "talents.json"
    talent_rows, talents = [], {}
    if talent_file.exists():
        talent_rows = json.loads(talent_file.read_text("utf-8"))
        # keyed for the potions, which look a talent up by the item's own key;
        # the list is kept because two keys can share a lowercase spelling
        talents = {t["key"].lower(): t for t in talent_rows}
    # Read before the codex is built: an item that grants a talent names it by
    # a number, and how far our count of the talents runs from the game's can
    # only be told where something else names the same talent outright. The
    # planner does, for two hundred and more of them, spread across the whole
    # list — the potions alone pin two short stretches at the end of it.
    kit_data = gear.read(HERE / "build" / "planner" / "gear")
    said_by = {}
    for t in talent_rows:
        told = say.by_key.get(f"talent_name_{t['key']}") or {}
        if told.get("en"):
            said_by.setdefault(gear.flat(told["en"]), t)
    named_talent = {}
    for key, (skill, _) in gear.grants(kit_data, {
            (r["metadata"] or {}).get("tkey"): {"names": {"en": (r["metadata"] or {}).get("name")}}
            for r in raw_items if (r.get("metadata") or {}).get("tkey")}).items():
        got = said_by.get(gear.flat(skill))
        if got:
            named_talent[key] = got

    items, vocab, kits = encyclopedia.build(
        raw_items, GAME / "translationsItem.csv", langs, place, icons.tidy, tables, say, talents,
        named_talent)

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
        if told_unit.get(v["sid"]) == "percent" and not v.get("unit"):
            v["unit"] = "%"
    fitted = gear.sets(kit_data, kits, lambda k: say.by_key.get(k), told_unit)

    # An item names the talent it grants by a number whose count runs behind
    # the game's, which can only be read where the difference is pinned. The
    # planner names it outright, so where it does, that is what is used.
    by_said = {}
    for t in talent_rows:
        told = say.by_key.get(f"talent_name_{t['key']}") or {}
        if told.get("en"):
            by_said.setdefault(gear.flat(told["en"]), t)
    named_skill = 0
    for key, (skill, level) in gear.grants(kit_data, items).items():
        got = by_said.get(gear.flat(skill))
        if not got:
            continue
        # The range the item rolls the talent's level over is on the item and
        # the planner states one number, so ours is kept where it was read.
        was = (items[key].get("grants") or {}).get("levels")
        span = was or (level if len(level) == 2 else [level[0], None])
        items[key]["grants"] = encyclopedia.spoken(got, span, lambda k: say.by_key.get(k))
        named_skill += 1
    print(f"grants   {named_skill} items name the talent they grant by name, "
          f"{sum(1 for r in items.values() if r.get('grants'))} in all")
    print(f"gear     {sum(1 for v in vocab if v.get('unit') == '%')} of {len(vocab)} stats are "
          f"percentages, {fitted} of {len(kits)} sets say what they give")

    out = {"langs": langs, "sheet": {"w": sheet[0], "h": sheet[1]},
           "words": {**said.SAID, **say.vocab()}, "types": types_said(say, items),
           "stats": vocab, "sets": kits, "items": items,
           "unholy": unholy.labelled(say)}
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
            (GAME / "translationsSubTalent.csv").read_text("utf-8", "replace").splitlines() if l.strip()]
    tree, bound, wanted, known, loose = skilltree.build(
        talent_rows, subs, lambda k: say.by_key.get(k), langs, HERE / "build" / "planner")
    for c in tree["classes"]:
        c["names"] = class_said(say, c["id"])
    tree["words"] = {**said.SAID, **say.vocab()}
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
    for it in out["items"].values():
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


#: The acts as the drop tables spell them, which is how a dungeon's own place
#: name is keyed — "Act IV Dungeons".
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX"}


def dungeon_nodes(nodes, per_code, t, say):
    """One marker per act for its ordinary dungeons.

    The game marks them nowhere and could not: a zone is generated when it is
    entered — `Act_01_01` holds nothing at all in the file, against 618 objects
    in a town and 2,491 in a dungeon — and the entrance is placed then, so which
    zone gets one is not a fact the file has. What the file does have is the
    drop table, and it is written per act: `4-D`, never `4-2-D`, and no
    individual dungeon is ever named as a source. So one marker per act says
    exactly what is known and nothing more.

    It stands beside the act's boss dungeon, which is the act's other dungeon
    and already sits clear of the chain of zones. On whichever side has room.
    """
    made = []
    for node in nodes:
        act = node["act"]
        if node["kind"] != "dungeon" or not act:
            continue
        drops = sorted(per_code.get(f"{act}-D", []), key=lambda name: (
            -(t["TIER_BY_NAME"].get(name) or 0), t["DROP_RATE"].get(name, 1 << 40)))
        if not drops:
            continue
        # Close enough to read as the pair they are — both are dungeons of this
        # act — and not so close that the two marks touch: 24 px of boss dungeon
        # and 22 of this leave 7 px of daylight at 30. It carries no name on the
        # map, so there is no label to keep clear of anything.
        away = 30
        near = lambda x, y: min(
            (abs(o["x"] - x) + abs(o["y"] - y)) for o in nodes if o is not node)
        x = max((node["x"] + away, node["x"] - away), key=lambda c: near(c, node["y"]))
        y = node["y"]
        made.append({
            "room": f"Act_{act:02d}_Dungeons",
            "x": x,
            "y": y,
            "kind": "dungeons",
            "code": f"{act}-D",
            "act": act,
            "name": dungeon_name(act, say),
            "drops": drops,
        })
    return made


def dungeon_name(act, say):
    """"Act IV Dungeons" in the eleven languages the game ships.

    Act IX is not in the game's table — it names I through VIII and stops — so
    it borrows act VIII's wording and swaps the numeral. That keeps each
    language's own word order, which composing the name out of "act" and
    "dungeons" does not: German writes "Dungeons Akt VIII".
    """
    told = say.of(f"Act {ROMAN[act]} Dungeons")
    if told:
        return told
    borrowed = say.of("Act VIII Dungeons") or {}
    return {lang: text.replace("VIII", ROMAN[act]) for lang, text in borrowed.items()}


def main():
    dw, w, h, tile, decor = art()
    langs, names = zone_names()
    t = tracker_tables()

    # item -> the zone codes it falls in
    per_code = {}
    for item, codes in t["DROP_ZONES"].items():
        for c in codes:
            per_code.setdefault(c, []).append(item)

    nodes = []
    for r in csv.DictReader(open(TRACKER / "tools" / "map" / "map_nodes.csv", encoding="utf-8")):
        room = r["room"]
        # The cabin is where the game teaches you to play. It is a marker on the
        # map and nothing falls in it, so it is only a thing to click on and be
        # told nothing.
        if "Cabin" in room:
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
        })

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
    raw_items = json.load(open(TRACKER / "tools" / "data" / "helper" / "items.json", encoding="utf-8"))
    place, missing, sheet, guessed, from_sprite = icons.build(
        dw, raw_items, set(items), IMG / "items.png")
    for name, box in place.items():
        items[name]["icon"] = box
    # written out for the same reason the bosses' choices are: a name-matched
    # icon is an argument, and an argument should be readable
    (HERE / "build" / "icons-chosen.json").write_text(
        json.dumps(dict(sorted(from_sprite.items())), ensure_ascii=False, indent=1),
        encoding="utf-8")

    # what the game itself says, folded in before anything is grouped
    merge_game.fold(items, HERE / "build" / "game_drops.json")

    # Before the bosses are gathered: a boss's own list says whether each thing
    # it drops is Inferno-only, and for a name the game gave us by mechanism
    # rather than by place that answer is the item's.
    inferno = bosses.mark_inferno(items)
    split_minded = bosses.disagrees_about_inferno(items)

    who = bosses.collect(items)
    listed = bosses.game_list(GAME / "translationsEnemy.csv")
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
        dw, list(who), IMG / "bosses.png", contact_png=HERE / "build" / "bosses-contact.png")
    for boss, box in faces.items():
        who[boss]["icon"] = box
    # written out so the choice can be argued with rather than taken on trust
    (HERE / "build" / "chosen.json").write_text(
        json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")

    # What the game calls each of these, in the eleven it ships. Only what it
    # actually carries — a name it has none for stays in English, and the count
    # below says how many that is.
    say = vocabulary.Words(GAME)
    # After the chain of a run is drawn, so they join nothing — a dungeon is not
    # a step on the way through an act — and after the vocabulary is up, which
    # is what gives them their names.
    nodes += dungeon_nodes(nodes, per_code, t, say)

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

    out = {
        "map": {"w": w, "h": h},
        "bosses": who,
        "bossSheet": {"w": face_sheet[0], "h": face_sheet[1]},
        "langs": langs,
        "tiers": t["TIER_LETTERS"],
        "sheet": {"w": sheet[0], "h": sheet[1]},
        "words": {**said.SAID, **say.vocab()},
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
    against_game.report(HERE / "build" / "game_drops.json", who, items)
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
    main()
