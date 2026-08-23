"""
generate_synthetic_cheaters.py

Generates synthetic "cheater" games by having Stockfish play (mostly)
itself. We add a `sloppiness` knob so games aren't a cartoonish 100%
engine-match every time -- real engine-assisted cheaters usually deviate
occasionally (lag, overconfidence on "obvious" moves, trying to look human).

For each move:
  - with probability (1 - sloppiness): play Stockfish's #1 choice
  - with probability sloppiness: play a random LEGAL move instead
    (crude stand-in for "human deviation" -- good enough to avoid every
    synthetic game being a trivial 100%/0cp giveaway)

Usage:
    python3 generate_synthetic_cheaters.py /opt/homebrew/bin/stockfish \
        --num_games 10 --sloppiness 0.15 --max_moves 40 \
        --out sample_games/synthetic
"""

import argparse
import glob
import os
import random

import chess
import chess.pgn
import chess.engine


def generate_one_game(engine, max_moves: int, sloppiness: float, depth: int) -> chess.pgn.Game:
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Synthetic Cheater Game"
    game.headers["White"] = "engine_cheater_sim"
    game.headers["Black"] = "engine_cheater_sim"
    game.headers["Result"] = "*"

    node = game

    for _ in range(max_moves * 2):  # *2 because max_moves = full moves, not half-moves
        if board.is_game_over():
            break

        if random.random() < sloppiness:
            move = random.choice(list(board.legal_moves))
        else:
            result = engine.play(board, chess.engine.Limit(depth=depth))
            move = result.move

        node = node.add_variation(move)
        board.push(move)

    game.headers["Result"] = board.result()
    return game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("engine_path", help="Path to Stockfish binary")
    parser.add_argument("--num_games", type=int, default=10)
    parser.add_argument("--sloppiness", type=float, default=0.15,
                         help="Probability of a random (non-engine) move per ply, 0-1")
    parser.add_argument("--max_moves", type=int, default=40,
                         help="Max full moves per game")
    parser.add_argument("--depth", type=int, default=12,
                         help="Stockfish search depth for move selection. "
                              "MUST match the depth used in engine_analysis.py's "
                              "ANALYSIS_DEPTH, or match-rate comparisons will be "
                              "meaningless (a shallow-search move judged by a "
                              "deeper search looks like a false 'deviation').")
    parser.add_argument("--out", default="sample_games/synthetic")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Don't overwrite existing synthetic games from a previous batch --
    # find the highest existing index and continue from there.
    existing = glob.glob(os.path.join(args.out, "synthetic_cheater_*.pgn"))
    existing_indices = []
    for path in existing:
        stem = os.path.splitext(os.path.basename(path))[0]
        try:
            existing_indices.append(int(stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            pass
    start_index = max(existing_indices, default=-1) + 1

    engine = chess.engine.SimpleEngine.popen_uci(args.engine_path)

    try:
        for offset in range(args.num_games):
            i = start_index + offset
            print(f"Generating synthetic game {offset+1}/{args.num_games} "
                  f"(index={i}, sloppiness={args.sloppiness}, depth={args.depth})...")
            game = generate_one_game(engine, args.max_moves, args.sloppiness, args.depth)
            path = os.path.join(args.out, f"synthetic_cheater_{i}.pgn")
            with open(path, "w") as f:
                print(game, file=f)
    finally:
        engine.quit()

    print(f"\nDone. Saved {args.num_games} synthetic games to '{args.out}/'.")


if __name__ == "__main__":
    main()
