# Hero Siege — where things drop

An interactive map of Hero Siege, drawn with the game's own art, with every
zone's drops on hover — and a codex of every item beside it.

The art and numeric facts come from the game. Generated data and diagnostics
retain source and uncertainty metadata; player-facing cards show item information.

## Where the pieces come from

**The map** is `Map_Screen_spr`, 2902×800 in the current build. Its texture page
is resolved through SPRT/TPAG and decoded from embedded TXTR or the game's
external texture file. The markers are
`Mapscreen_Zone_spr`, `…_Town_spr` and `…_Boss_Dungeon_spr`, five frames each,
which are the states the game picks between: unopened, opened, locked, chosen,
and the ring it draws under the cursor.

**The 64 marker positions** are the game's own. They are not in `data.win` —
they are compiled into the YYC code, in the closure the map screen keeps in its
`m_SetupMap` slot, which emits two integer literals and a room reference per
marker. The Extractor locates the closure by its registered script names and
reads its current room references and coordinates. The site consumes those
records from the manifest, including their source evidence. The values are marker
**centres** in the background sprite's pixel space. Historical independent
comparison notes remain in `tools/map/` in the Tracker repository.

Every native marker is retained, including the Cabin. The site also displays
26 dungeon shortcuts from a community catalogue. Their zone associations are
unverified reference data and their positions are schematic offsets beside
native markers. Each data record carries an explicit
reference and inferred-coordinate provenance. `diagnostics/map-marker-coverage.json`
checks native coverage and lists these additional markers separately.

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

**What drops where** comes directly from a verified HeroSiege Extractor bundle.
Its manifest identifies the game files and hashes every dataset. The site reads
items and talents from that same bundle rather than from separate Tracker files.
Unresolved numeric values and separate item records survive the build. Reference
catalogue additions carry their source and are marked as unverified for the
selected game build.

## Building it

The second full item review restored 69 set definitions and membership for
253 records from the saved published catalogue, retaining reference provenance
and matching exact item keys, types and compatible rarities. Native membership
and item facts take precedence. Current translations supply all 69 Russian set
names; 65 sets retain 167 bonus steps and 288 lines. Four published definitions
have membership only, so their bonus amounts remain unspecified.
The review compares all 11,392 original statements directly with the immutable
Extractor input, checks native item metadata, atlas bounds, Unholy pools and
rune recipes, and renders every card in EN/RU at a narrow card width.
Evidence: `tools/perf/item-recheck-20261120-consistency.json` and
`tools/perf/item-recheck-20261120-source-audit.json`.

Conditional item previews retain each native outer key as a separate outcome.
Azazel's Despair has nine named Soulgem outcomes; Signet of Shadows has six
damage variants, including Physical (selector zero). Gem King's Garb and
Cleaver retain seven pristine gem outcomes each, Dreadnought has Sapphire/Ruby,
and Wraith's Cloak has five elemental variants. The selector filters stats and
granted effects together; All variants shows each outcome in its own section.
Socket bonuses are shown per matching socket. Damage names describe each
item's actual stat family rather than a global damage-type enumeration.
The source-bound profile is `build/native-item-conditions-26297349.json`;
the full catalog and every conditional choice are checked in
`tools/perf/item-conditions-20261120-render.html`.
All 4,024 EN/RU card renders and 72 individual condition selections passed,
alongside 37 Node and 93 Python tests. Current evidence is in
`tools/perf/item-conditions-20261120-consistency.json`.

The full 20 November item-effect audit checks all 2,012 current records and
preserves every original operand, variant and conditional channel. Seven event
families resolve 284 triggered effects: the first operand selects the talent,
the second is its level, and the third is its percentage chance. Source-bound
class restrictions, flasks, projectile modifiers, subskills, deferred damage and
special Codex selectors are rendered by their actual roles. Base weapon reach
and damage spread remain in mechanics metadata. The raw magnitude of stat473
is retained without inventing a healing unit; the confirmed Bone Spirit healing
capability is displayed. Random skill flags do not become fixed talent IDs.

The profile is build/native-item-effects-26297349.json (46 exact native spans,
53 constants, EXE and data.win identity). The all-record browser harness at
tools/perf/full-item-effects-20261120-render.html mounts every card in EN/RU;
4,024 renders passed, with no unidentified effect rows. Tests: 33 Node, 85 Python.
Full evidence: tools/perf/full-item-effects-20261120-consistency.json.

The local test stand runs from this checkout with `npm run dev` at
`http://127.0.0.1:5180/hs-map/` (`npm run dev -- --host 127.0.0.1` binds it to
the local machine). Stop the stand with Ctrl+C before a coordinated data
installation on Windows, then start it again. Generated site and staging
directories are excluded from the development watcher.

Seven item skill slots and five aura slots are resolved through the source-bound
`build/native-item-aura-slots-26297349.json` profile and current native talent IDs.
Skill bonuses use a plus sign; aura levels and holder-only restrictions are
separate. Random skill selections retain their ranges, and relics retain all ten
rank values. Conditional runeword grants stay attached to their original channel.
Unknown, duplicated or incomplete operands remain in the stat list. Every
consumed operand survives in the grant's source_stats. Current grants take
precedence in cards; older catalogue suggestions are used when no current grant
is available and are always retained in the data. Search includes grant names.

The published map's lost source connections are retained in
`build/reference/published-chest-drops-20261120.json`. They include Crystal
Chest, Dungeon Chest and four other affected source groups. Their data records
identify them as unverified reference information; they do not replace current
item rates, declared locations or already verified source connections.

The 20 November general item-grant pass covers 298 base skill entries and 23 base
auras, plus 31 skills and 13 auras in conditional channels. The audit preserves
2,012 records, 10,211 previous stat statements and all 918 current map items.
Validation: 32 Node tests, 76 Python tests, EN/RU browser checks, a 480px relic
card and the compiled Tracker web package. Evidence is under
`tools/perf/all-item-grants-20261120-*`.

Rebuilding the data needs the game, a current Extractor bundle, Python 3.10+
and the Tracker checkout's texture-reading utilities. By default the checkouts
are siblings and the bundle is at `../HeroSiege Extractor/out/bundle`.
Set `HS_DATA_BUNDLE`, `HERO_SIEGE_BIN` and `HS_TRACKER` to override them. Steam
libraries are searched when no game path is supplied. A changed game file or
dataset hash stops the build before generation.
The npm commands use `PYTHON`, otherwise the sibling Extractor's `.venv` when
present, then `python` from `PATH`.

```bash
npm install
python -m pip install -r requirements.txt
npm run data     # read the game, write public/data and public/img
npm run dev      # http://localhost:5180/hs-map/
npm run build    # into docs/, which is what GitHub Pages serves
npm test
npm run test:data
```

`HS_MAP_OUTPUT` directs generated `data/` and `img/` into a staging folder for
verification without replacing `public/`. `data/source.json` records the source
fingerprint and reference catalogue digest used for that generation. Existing
`game_drops.json`, `item_icons.json` and `unholy.json` snapshots are not used as
fallbacks for a current export.

The ordinary data command also generates into staging. After validation it
promotes `data/`, `img/` and `diagnostics/` together with a recovery journal;
failed publication restores the previous directories. A later run recovers an
interrupted publication before starting. To compile or preview staged assets,
set `HS_MAP_PUBLIC_DIR` to that staging directory (or keep `HS_MAP_OUTPUT` set)
when running Vite. The same directory is used for asset hashes and `publicDir`.

The map renders pixel art at one sample per CSS pixel while text keeps the
screen's native resolution. Dragging uses cached viewport dimensions, pauses
hover cards and avoids uploading unchanged marker geometry. At rest the
animation clock wakes at the art's six-frame rate instead of polling every
display frame; hidden tabs stop that clock.

`npm run package:tracker` compiles the current data and map into a private
candidate, verifies its source fingerprint and assets, then installs it under
the sibling Tracker checkout's `public/hs-map`. Set `HS_TRACKER` or pass
`-- --tracker <checkout>` to change that checkout. `-- --dry` retains a candidate
without installation. The copy has a file/hash manifest, a publisher lock,
rollback, and recovery of interrupted directory swaps. It does not publish to
GitHub Pages. Rebuild Tracker after packaging so its local map and OBS mirror
contain the same files. A standalone data refresh also needs packaging;
the coordinated Extractor refresh includes it automatically.

The Extractor's `scripts/refresh-all.mjs` now includes `Tracker/public/hs-map`
in its cross-project transaction. That refresh needs no separate packaging
command; rebuild Tracker afterwards. `package:tracker` is still useful for
standalone map-code changes, and takes the same data/package locks.

The embedded map opts into a bounded state bridge with
`?mode=source|mirror&parentOrigin=<encoded exact local origin>`. Messages use
`channel: 'hs-map'`, `version: 1`, a nonnegative safe integer `revision`, and
`type: 'ready' | 'state' | 'apply'`. Only messages from the configured parent
window and exact origin are accepted; HTTP localhost, 127.0.0.1 and
tauri.localhost origins are allowed. Ordinary browser visits have no bridge.
State has these exact fields:

```js
{
  camera: { center: [0.5, 0.5], scale: 1.35 },
  viewport: { width: 1920, height: 1080 },
  selection: { roomId: null },
  presentation: { query: '', lang: 'en', source: null }
}
```

Camera centre is normalized to map dimensions and scale is CSS pixels per map
pixel. Viewport is the full map document, including its sidebar. The OBS parent
sizes its mirror document to the source viewport and letterboxes that document;
it does not stretch the world to another aspect ratio. Room, language and source
keys must exist in the bundled data. A room and a boss/source cannot both be
pinned. Source changes are coalesced to at most 30 posts per second. A source
restored with `apply` sends one resulting state with a revision above the applied
revision; parents must not send ordinary source states back to that source.
Mirrors emit `ready` only, accept state, and disable interaction.

The shared state covers the map camera, pinned room/source, search and language.
Hover/cursor tooltips, item sheets, codex/planner navigation and arbitrary browser
content are outside this map-view protocol.

The bounded Chrome compositor audit is recorded in
`tools/perf/evidence-2026-11-15.json`. It identifies the deployed and local asset
hashes and reports actual Chromium input-to-presentation events, not GPU load
percentages or only JavaScript callback time. The public site still needs an
explicit remote publication to receive these local changes.

`vite.config.js` sets `base` to `/hs-map/` because Pages serves a project site
under the repository's name. Set `BASE_PATH=/` to build for a root-served host.

## Sprites

Used with the developer's permission, given for this site.
