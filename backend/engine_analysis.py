"""
engine_analysis.py

The core anti-cheat feature: replay a game move-by-move, ask Stockfish for
its evaluation and top move at each position BEFORE the human moves, then
compare. This produces two features per player per game:

  - top1_match_rate: % of moves that matched Stockfish's #1 choice
  - avg_centipawn_loss: average "points" lost vs. the best available move
    (a centipawn = 1/100th of a pawn's value; 0 = played the best move
    every time, 300+ = regularly blundering)

Requires:
  pip install chess
  brew install stockfish   (or any UCI engine binary)

Usage:
    python3 engine_analysis.py sample_games/nitrobeast705_10.pgn /opt/homebrew/bin/stockfish
"""

import sys
import chess
import chess.pgn
import chess.engine


# How hard Stockfish "thinks" per position. Higher = more accurate but
# slower. depth=12 is a reasonable balance for a first pass — a few hundred
# ms per move. Cranking this to 20+ gives more reliable numbers but a
# 40-move game could take minutes instead of seconds.
ANALYSIS_DEPTH = 12


def score_to_centipawns(score: chess.engine.PovScore, mate_score: int = 1000) -> int:
    """
    Stockfish scores are either a centipawn number OR 'mate in N moves'.
    We need a single comparable number, so we treat any forced mate as
    a huge centipawn value (with sign preserved) rather than a special case.
    """
    return score.pov(score.turn).score(mate_score=mate_score)


def analyze_game(pgn_path: str, engine_path: str, depth: int = ANALYSIS_DEPTH,
                  skip_plies: int = 0) -> dict:
    """
    skip_plies: number of half-moves to fast-forward through (pushing moves,
    but NOT scoring them) before starting analysis. Needed when the early
    part of a game isn't relevant to what you're trying to measure -- e.g.
    the Kaggle cheating dataset's first 10 full moves (20 plies) are real
    human moves with no cheat/clean label, so scoring them would dilute
    the per-player averages with irrelevant data.
    """
    with open(pgn_path) as f:
        game = chess.pgn.read_game(f)

    if game is None:
        raise ValueError(f"Could not parse a game from {pgn_path}")

    board = game.board()
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    stats = {
        chess.WHITE: {"matches": 0, "total": 0, "cp_losses": []},
        chess.BLACK: {"matches": 0, "total": 0, "cp_losses": []},
    }

    try:
        for ply_index, move in enumerate(game.mainline_moves()):
            mover_color = board.turn

            if ply_index < skip_plies:
                board.push(move)
                continue

            # Ask Stockfish: what's best here, and what's it worth?
            info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
            best_move = info_before["pv"][0]
            best_score_cp = score_to_centipawns(info_before["score"])

            # Did the human match the engine's top pick?
            matched = (move == best_move)

            # If not, how much worse was their move? Push it, re-evaluate,
            # and compare from the SAME player's perspective.
            board.push(move)
            if matched:
                cp_loss = 0
            else:
                info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
                # info_after's score is from the opponent's perspective now
                # (it's their turn), so flip sign to get it back to the mover.
                played_score_cp = -score_to_centipawns(info_after["score"])
                cp_loss = max(0, best_score_cp - played_score_cp)

            stats[mover_color]["total"] += 1
            stats[mover_color]["matches"] += int(matched)
            stats[mover_color]["cp_losses"].append(cp_loss)

    finally:
        engine.quit()

    results = {}
    for color, label in [(chess.WHITE, "white"), (chess.BLACK, "black")]:
        s = stats[color]
        if s["total"] == 0:
            continue
        results[label] = {
            "player": game.headers.get("White" if color == chess.WHITE else "Black"),
            "moves_analyzed": s["total"],
            "top1_match_rate": round(100 * s["matches"] / s["total"], 1),
            "avg_centipawn_loss": round(sum(s["cp_losses"]) / s["total"], 1),
            "cp_loss_sequence": s["cp_losses"],  # raw per-move values, for windowed features
        }
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 engine_analysis.py <path_to.pgn> <path_to_stockfish_binary>")
        sys.exit(1)

    pgn_path, engine_path = sys.argv[1], sys.argv[2]
    print(f"Analyzing {pgn_path} at depth {ANALYSIS_DEPTH}... (this can take 10-60s)")
    results = analyze_game(pgn_path, engine_path)

    for color, r in results.items():
        print(f"\n{r['player']} ({color}):")
        print(f"  Moves analyzed:     {r['moves_analyzed']}")
        print(f"  Top-1 match rate:   {r['top1_match_rate']}%")
        print(f"  Avg centipawn loss: {r['avg_centipawn_loss']}")
