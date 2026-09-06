"""The quests the Bounty Board hands out, as the game words them.

The board stands in Tarethiel and posts the day's work — `bounty_board_quest`
is "View Daily Quest" — and what it can post is a fixed set. The game does not
list that set outright: `bountyBoardFirstQuestId` and `bountyBoardQuestAmount`
are variables the code fills in, and nothing in the data holds their values.

Their names give the shape, though — a first id and a count, so the board's
quests are a run — and `translationsQuest.csv` marks the run out itself. The
file keeps its own groups, a bracketed line above each: `[MAIN QUEST]`,
`[HELL 5 QUESTS]`, `[Halloween dailies]`, and the one read here. It is named
for Valhalla after the update that put the board up rather than after the town
the board stands in.

That section holds more than the board, the Book of Soulforge pages having been
filed into it later. What tells them apart is `quest_dialog_<id>`, the line the
board itself prints: thirteen quests carry one, they run 440 to 452 without a
gap, and no quest anywhere else in the table has one at all. So the rule below
is that pair — the heading, and a dialog line — rather than a list typed out
here.

Quests that read like the board's and are not: the WANTED series at 1250 is
`[HELL 5 QUESTS]`, given by an NPC in Hell (`dialog_hell*`), and Lilith, Abyssal
Terror Awakened and The Fall of Darkness each come off a chain of their own.

Everything else about them — the name, the brief, every objective — is read out
of the same file in all eleven languages, as zone and item names are everywhere
on this site.
"""
import io
import re

#: The file's own heading for the group the board's quests are filed under.
SECTION = "[Valhalla dailies]"

#: A walkthrough for a quest, by the id the game files it under.
#:
#: All thirteen are Cpfuzzy's, whose `[Daily]` series is thirteen videos and
#: covers exactly the run read out above — which is the rule confirmed by
#: somebody who plays the game rather than reads its files.
#:
#: A bare YouTube id rather than a URL: the page wraps it in a
#: `youtube-nocookie` embed, and an id cannot smuggle a tracking query in with
#: it. The embedded player names its own author, so the credit rides along.
VIDEOS = {
    440: "9ks7fO1oo7Y",   # River Raider
    441: "uCw5hbQy_hs",   # The Golden Heist
    442: "aoYEWZl8p2s",   # Naga Treasury
    443: "hsgwcqEWXRY",   # The Crown of Surtr
    444: "E-95YuevnC8",   # Grim Skull
    445: "NhnT_RURSaI",   # WANTED: Xor
    446: "SOQUI_hrgT8",   # Anitas Amulet
    447: "PurjuyWXqgM",   # Awful Abominations
    448: "tc36cRjWMzw",   # To The Tower!
    449: "9kzWEW8Uvt0",   # Njal Must Die!
    450: "X7GI8P-qeUk",   # Security Measures
    451: "BLL4CY7NOBA",   # Hellpiercer
    452: "f7xDPfLswO0",   # The False Prophet Defenestration
}

#: What the game's text carries that a web page cannot show.
#:
#: `[c_coin]` and `[c_reset]` open and close a colour, `[input_use]` stands for
#: whatever key the reader has bound, and `[var,hourLeft]` is filled in as it is
#: printed. None of the three means anything here, and left in they read as
#: rubble in the middle of a sentence.
MARKUP = re.compile(r"\[[^\]]*\]")

#: A quest's own dialogue line, which is what marks it as the board's.
DIALOG = re.compile(r"quest_dialog_(\d+)$")


def slug(text):
    """A stable handle for a quest, for the address bar and for a video to hang
    off. Off the English name, because that is the one that does not move."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def clean(text):
    return MARKUP.sub("", text or "").replace("  ", " ").strip()


def read(game):
    """Every row of the quest table, keyed, with each language beside it, and
    the bracketed heading each row was filed under."""
    rows, under, heading = {}, {}, None
    with io.open(game / "translationsQuest.csv", encoding="utf-8", errors="replace") as fh:
        langs = fh.readline().rstrip("\n").split("|")[1:]
        for line in fh:
            p = line.rstrip("\n").split("|")
            key = p[0].strip()
            if not key:
                continue
            if key.startswith("["):
                heading = key
                continue
            if len(p) < 2:
                continue
            under[key] = heading
            said = {lang: clean(v) for lang, v in zip(langs, p[1:]) if clean(v)}
            if said:
                rows[key] = said
    return langs, rows, under


def board(under):
    """The ids the board posts, in the order the file lists them.

    Taken off the headings rather than off the text, so a quest whose dialogue
    is written in no language yet still counts: what is being read here is that
    the line exists, not what it says.
    """
    found = [
        int(m.group(1))
        for key, heading in under.items()
        if heading == SECTION and (m := DIALOG.match(key))
    ]
    if not found:
        raise SystemExit(f"no quest carries a dialog line under {SECTION}")
    return found


def collect(game):
    """The board's quests, in the order the file lists them.

    A quest's brief comes in up to three wordings — keyboard, controller and
    touch, keyed `_2` and `_3` — and they differ only in which button they name.
    The first is the one taken; the others say the same thing to a different
    hand.
    """
    langs, rows, under = read(game)
    out = []
    for qid in board(under):
        name = rows.get(f"quest_name_{qid}")
        if not name:
            continue
        goals = []
        for i in range(1, 10):
            goal = rows.get(f"quest_objective_{qid}_{i}")
            if goal:
                goals.append(goal)
        out.append({
            "id": qid,
            "key": slug(name.get("en", str(qid))),
            "name": name,
            "brief": rows.get(f"quest_description_{qid}") or {},
            "goals": goals,
            # `VIDEOS` above, and None until one is found. The page draws the
            # place for it either way, so a quest without one reads as "not yet"
            # rather than as broken.
            "video": VIDEOS.get(qid),
        })
    return langs, out
