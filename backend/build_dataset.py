"""
build_dataset.py

Runs engine_analysis on every real game (trusted player = clean, label 0)
and every synthetic game (both sides = cheater sim, label 1), and writes
one row per player-in-game to a CSV for training.

Usage:
    python3 build_dataset.py \
        --real_dir sample_games \
        --real_username Nitrobeast705 \
        --synthetic_dir sample_games/synthetic \
        --engine_path /opt/homebrew/bin/stockfish \
        --out dataset.csv \
        --max_real_games 40
"""

import argparse
import csv
import glob
import os

from engine_analysis import analyze_game
from features import windowed_features


FEATURE_KEYS = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
                "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real_dir", required=True)
    parser.add_argument("--real_username", required=True,
                         help="Only rows for THIS player are trusted as "
                              "'clean' (label 0) -- we don't know the "
                              "opponent's history, so we skip them.")
    parser.add_argument("--synthetic_dir", required=True)
    parser.add_argument("--engine_path", required=True)
    parser.add_argument("--out", default="dataset.csv")
    parser.add_argument("--max_real_games", type=int, default=40,
                         help="Cap how many real games to process -- engine "
                              "analysis is slow, no need to run all 115 yet.")
    args = parser.parse_args()

    rows = []

    # --- Real games: only trust the known username's rows ---
    real_paths = sorted(glob.glob(os.path.join(args.real_dir, "*.pgn")))[:args.max_real_games]
    print(f"Processing {len(real_paths)} real games...")
    for path in real_paths:
        try:
            results = analyze_game(path, args.engine_path)
        except Exception as e:
            print(f"  Skipping {path}: {e}")
            continue
        for color, r in results.items():
            if r["player"].lower() == args.real_username.lower():
                row = {
                    "game_id": os.path.basename(path),
                    "player": r["player"],
                    "top1_match_rate": r["top1_match_rate"],
                    "avg_centipawn_loss": r["avg_centipawn_loss"],
                    "label": 0,
                }
                row.update(windowed_features(r["cp_loss_sequence"]))
                rows.append(row)
        print(f"  {path}: done ({len(rows)} rows so far)")

    # --- Synthetic games: both sides are the cheater sim ---
    synth_paths = sorted(glob.glob(os.path.join(args.synthetic_dir, "*.pgn")))
    print(f"Processing {len(synth_paths)} synthetic games...")
    for path in synth_paths:
        try:
            results = analyze_game(path, args.engine_path)
        except Exception as e:
            print(f"  Skipping {path}: {e}")
            continue
        for color, r in results.items():
            row = {
                "game_id": os.path.basename(path),
                "player": f"{r['player']}_{color}",
                "top1_match_rate": r["top1_match_rate"],
                "avg_centipawn_loss": r["avg_centipawn_loss"],
                "label": 1,
            }
            row.update(windowed_features(r["cp_loss_sequence"]))
            rows.append(row)
        print(f"  {path}: done ({len(rows)} rows so far)")

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "game_id", "player", "label"
        ] + FEATURE_KEYS)
        writer.writeheader()
        writer.writerows(rows)

    n_clean = sum(1 for r in rows if r["label"] == 0)
    n_cheat = sum(1 for r in rows if r["label"] == 1)
    print(f"\nWrote {len(rows)} rows to {args.out} ({n_clean} clean, {n_cheat} cheater)")


if __name__ == "__main__":
    main()
