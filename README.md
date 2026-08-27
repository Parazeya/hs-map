# Hero Siege — where things drop

An interactive map of Hero Siege, drawn with the game's own art, with every
zone's drops on hover — and a codex of every item beside it.

The art and the numbers all come out of the game. Nothing is traced, redrawn or
typed in by hand.

## Where the pieces come from

**The map** is `Map_Screen_spr`, 2902×800, cut from `gui_mapscreen_tex_0.yytex`
— GameMaker's own custom QOI, decoded byte-exactly. The markers are
`Mapscreen_Zone_spr`, `…_Town_spr` and `…_Boss_Dungeon_spr`, five frames each,
which are the states the game picks between: unopened, opened, locked, chosen,
and the ring it draws under the cursor.

**The 64 marker positions** are the game's own. They are not in `data.win` —
they are compiled into the YYC code, in the closure the map screen keeps in its
`m_SetupMap` slot, which emits two integer literals and a room reference per
marker. They were recovered by disassembling that function, four times over by
four different methods against both the Windows and Linux builds; all four agree
on every one of the 64. The values are marker **centres** in the background
sprite's own pixel space. See `tools/map/` in the tracker repository for the
extraction and its notes.

**The paths between markers** are the one thing on the page the game does not
draw. `Map_Zone_Line_obj` is compiled in — a create event, a step and a draw, and
it is the only thing in the game that touches `Mapscreen_Line_spr` — but nothing
anywhere creates it: its object index appears in the executable neither as a
constant nor as a name, and it stands in no room. The same search finds
`UI_Map_Zone_Button_obj`, the marker, referenced from three of the map screen's
closures, which is what makes the silence about the line meaningful rather than a
failure to look.

So the trail is the game's and the route is ours. `Mapscreen_Line_spr` is 16×8
and every column of it is identical: the picture is in the rows — three of
gradient over four of its own shadow, a rope seen from above — so it is laid end
to end rather than spaced. Of its two hues the warm one is used, because the cold
one is (88, 48, 102) against ground of (82, 46, 81) under act I and could not be
seen at all.

The route is each act in the order it is played: town first, five zones by
number, boss dungeon last. That the order is also the shape is the argument for
it — laid out this way the longest step inside acts I–VIII is 152 px on a map
2902 wide, and the middle one is 89. Acts are left unjoined: those gaps run 111
to 732 px with nothing under them, and act VIII has no town on the map to join.

**The zone names** are `translationsZone.csv` from the game folder, keyed by room
name, in the eleven languages it ships: en, fi, pt, ru, zh, ja, ko, de, fr, sp,
pl.

**What drops where** comes from the [HS Tracker](https://github.com/Parazeya/hs-tracker)
project's `src/items.js`, which that project builds from the same executable —
drop rates, in-zone chase rates, rarities and tiers.

## Building it

Rebuilding the data needs a copy of the game and the tracker checked out beside
this; `build/build.py` names both paths at the top.

```bash
npm install
npm run data     # read the game, write public/data and public/img
npm run dev      # http://localhost:5180/hs-map/
npm run build    # into docs/, which is what GitHub Pages serves
```

`vite.config.js` sets `base` to `/hs-map/` because Pages serves a project site
under the repository's name. Set `BASE_PATH=/` to build for a root-served host.

## Sprites

Used with the developer's permission, given for this site.
