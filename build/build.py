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
import sys
from pathlib import Path

import against_game
import bosses
import encyclopedia
import words as vocabulary
import icons
import merge_game
import portraits

HERE = Path(__file__).resolve().parent.parent
TRACKER = Path(r"e:\Workspace\HeroSiege")
GAME = Path(r"F:\Games\Steam\steamapps\common\HeroSiege\bin")

sys.path.insert(0, str(TRACKER / "tools"))
from datawin import DataWin           # noqa: E402
import yytex                          # noqa: E402
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
    return dw, bg.width, bg.height, tile


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
        sheet = Image.new("RGBA", (first.width * len(frames), first.height))
        for i in range(len(frames)):
            sheet.paste(unlit(cut(spr, i)), (first.width * i, 0))
        picture(sheet, IMG / f"{out}.{len(frames)}x{fps}.png")


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

    items, vocab, kits = encyclopedia.build(
        raw_items, GAME / "translationsItem.csv", langs, place, icons.tidy, tables)

    say = vocabulary.Words(GAME)
    # What the game calls each stat, joined on meaning — see words.Words.stats
    told = say.stats([v["sid"] for v in vocab])
    for v in vocab:
        if told.get(v["sid"]):
            v["names"] = told[v["sid"]]
    seen = sum(v["n"] for v in vocab)
    named = sum(v["n"] for v in vocab if v.get("names"))
    print(f"stats    {len(told)} of {len(vocab)} named by the game, which is "
          f"{named} of {seen} stat lines a reader meets ({100 * named // seen}%)")

    out = {"langs": langs, "sheet": {"w": sheet[0], "h": sheet[1]},
           "words": say.vocab(), "types": types_said(say, items),
           "stats": vocab, "sets": kits, "items": items}
    path = DATA / "codex.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    with_stats = sum(1 for r in items.values() if r.get("stats") or r.get("more"))
    with_lore = sum(1 for r in items.values() if r.get("lore"))
    print(f"codex    {len(items)} items, {with_stats} with stats, {with_lore} with lore, "
          f"{len(vocab)} distinct stats, {len(kits)} sets")
    print(f"         icons {len(place)} cut into a {sheet[0]}x{sheet[1]} sheet, "
          f"{len(missing)} without one")
    print(f"written  {path}  ({path.stat().st_size // 1024} KB)")


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
    dw, w, h, tile = art()
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
        "words": say.vocab(),
        "places": spoken,
        "nodes": nodes,
        "links": links,
        "linkTile": list(tile),
        "items": items,
    }
    (DATA / "map.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

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
    print(f"written  {DATA / 'map.json'}  ({(DATA / 'map.json').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
