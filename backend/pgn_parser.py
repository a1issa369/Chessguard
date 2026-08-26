"""
pgn_parser.py

A minimal, hand-rolled PGN (Portable Game Notation) parser.

We're building this ourselves once so you understand the raw format before
we swap in the `python-chess` library for real move validation later. PGN
has two parts:

1. Tag pairs: metadata like [White "..."] [WhiteElo "..."] etc.
2. Movetext: the actual moves, optionally annotated with things like
   {[%clk 0:09:58]} which is the player's remaining clock time right
   after making that move. THIS clock data is the raw signal we'll use
   to detect suspiciously consistent (engine-like) move timing.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedGame:
    tags: dict = field(default_factory=dict)
    # list of (move_san, clock_seconds) for every half-move, in order
    moves: list = field(default_factory=list)


def _clock_to_seconds(clock_str: str) -> float:
    """Convert 'H:MM:SS' -> total seconds."""
    h, m, s = clock_str.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_pgn(pgn_text: str) -> ParsedGame:
    game = ParsedGame()

    # --- Part 1: tag pairs ---
    # Lines look like: [White "suspicious_player99"]
    tag_pattern = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
    for match in tag_pattern.finditer(pgn_text):
        key, value = match.groups()
        game.tags[key] = value

    # --- Part 2: movetext ---
    # Strip the tag section out, leaving just the moves + annotations.
    movetext = tag_pattern.sub("", pgn_text).strip()

    # Each half-move looks like:  Nf3 {[%clk 0:09:57]}
    # We ignore move numbers (e.g. "10.") since they're not moves themselves.
    move_pattern = re.compile(
        r'([a-zA-Z0-9\-\+\#=OoQKNBR]+)\s*(?:\{\[%clk\s+([\d:\.]+)\]\})?'
    )

    for token in movetext.split():
        # skip move-number markers like "1." or "10."
        if re.fullmatch(r'\d+\.', token):
            continue
        if token in ("1-0", "0-1", "1/2-1/2", "*"):
            continue
        # This simple splitter won't correctly grab the {[%clk]} part since
        # it's separated by whitespace as its own tokens ({[%clk, 0:09:58]}).
        # So instead, let's re-parse the whole movetext with regex directly.
        pass

    # Cleaner approach: regex over the full movetext string at once.
    full_pattern = re.compile(
        r'(?:\d+\.\s*)?'                      # optional move number
        r'([a-zA-Z][a-zA-Z0-9\-\+\#=]*|O-O-O|O-O)'  # the SAN move itself
        r'\s*(?:\{\[%clk\s+([\d:\.]+)\]\})?'  # optional clock annotation
    )
    for san, clk in full_pattern.findall(movetext):
        if san in ("1-0", "0-1", "1/2-1/2", "*", ""):
            continue
        seconds = _clock_to_seconds(clk) if clk else None
        game.moves.append((san, seconds))

    return game


def move_times_used(game: ParsedGame, player: str) -> list:
    """
    Convert raw clock *remaining* values into time *used* per move for one
    player ('white' or 'black').

    IMPORTANT: TimeControl can be "base+increment" (e.g. "60+1" = 60s base,
    +1s added back to your clock after every move you make). If we ignore
    the increment, our "time used" math comes out too low or even negative,
    since some of what looks like clock recovery is really just the
    increment being credited back. So: time_used = prev_clock - clk + increment.
    """
    tc = game.tags.get("TimeControl", "600")
    if "+" in tc:
        base_str, incr_str = tc.split("+")
        increment = float(incr_str)
    else:
        base_str, increment = tc, 0.0
    start_seconds = float(base_str)

    idx_offset = 0 if player == "white" else 1

    player_clocks = [
        clk for i, (_, clk) in enumerate(game.moves)
        if i % 2 == idx_offset and clk is not None
    ]

    times_used = []
    prev_clock = start_seconds
    for clk in player_clocks:
        used = prev_clock - clk + increment
        times_used.append(round(max(used, 0.0), 1))  # clamp: can't think negative time
        prev_clock = clk
    return times_used


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "sample_games/sample1.pgn"

    with open(path) as f:
        pgn_text = f.read()

    game = parse_pgn(pgn_text)

    print(f"Parsing: {path}")
    print("Tags:", game.tags)
    print(f"\nTotal half-moves parsed: {len(game.moves)}")
    print("First 5 (move, clock_remaining_seconds):", game.moves[:5])

    base_time = float(game.tags.get("TimeControl", "600").split("+")[0])
    if base_time < 180:
        print(f"\n⚠️  Base time is {base_time}s, this is a bullet/hyperbullet "
              f"game. Move-time variance is naturally compressed here and is "
              f"a weak cheat signal on its own; better suited to rapid/blitz "
              f"games (600s+).")

    white_times = move_times_used(game, "white")
    black_times = move_times_used(game, "black")

    print(f"\n{game.tags.get('White')}'s seconds spent per move:", white_times)
    print(f"{game.tags.get('Black')}'s seconds spent per move:  ", black_times)
