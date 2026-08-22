"""
kaggle_validate.py

Validates our classifier against real ground-truth labels from the
"Spotting Cheaters" Kaggle dataset (Stockfish vs. Maia bot games).

Key design decisions, worth understanding:

1. The first 10 full moves (20 plies) in every game are REAL HUMAN moves
   pulled from Lichess -- not bot-generated, no cheat label applies. We
   skip these (skip_plies=20) so our features only reflect the labeled
   bot-generated portion of the game.

2. The cheat label is a fraction, not always 0 or 1 -- a "cheating" side
   uses Stockfish on SOME moves with some probability, not necessarily
   every move. We only keep clearly-labeled examples for a clean
   validation set: cheat_frac == 0 (pure Maia, label=clean) or
   cheat_frac >= 0.5 (majority Stockfish, label=cheater). Games in
   between are ambiguous and excluded -- a modeling choice, not a bug.

Requires: pip install pandas scikit-learn (already installed from earlier)

Usage:
    python3 kaggle_validate.py Games.csv /opt/homebrew/bin/stockfish \
        --n_per_class 10 --dataset_csv ../dataset.csv
"""

import argparse
import os
import random
import tempfile

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, classification_report

from engine_analysis import analyze_game
from features import windowed_features

SKIP_PLIES = 20  # first 10 full moves are real human moves, not bot-generated


def cheat_fraction(bitstring: str) -> float:
    if not bitstring or pd.isna(bitstring):
        return 0.0
    return sum(c == "1" for c in bitstring) / len(bitstring)


def build_candidates(df: pd.DataFrame) -> list:
    """Returns a list of dicts, one per (game, color) side, with a clear label."""
    candidates = []
    for idx, row in df.iterrows():
        for color, cheat_col in [("white", "Liste cheat white"), ("black", "Liste cheat black")]:
            frac = cheat_fraction(row[cheat_col])
            if frac == 0.0:
                label = 0
            elif frac >= 0.5:
                label = 1
            else:
                continue  # ambiguous, skip
            candidates.append({
                "row_idx": idx,
                "color": color,
                "cheat_frac": frac,
                "label": label,
                "pgn_moves": row["Game"],
                "score": row["Score"],
            })
    return candidates


def pgn_move_count(pgn_moves: str) -> int:
    # crude ply estimate: count tokens that aren't move numbers or the result
    tokens = pgn_moves.split()
    return sum(1 for t in tokens if not t.rstrip(".").isdigit()
               and t not in ("1-0", "0-1", "1/2-1/2", "*"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("engine_path")
    parser.add_argument("--n_per_class", type=int, default=10)
    parser.add_argument("--dataset_csv", default="../dataset.csv",
                         help="Our original training CSV, to fit the model on")
    parser.add_argument("--out", default="kaggle_validation_results.csv")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    df = pd.read_csv(args.csv_path)
    candidates = build_candidates(df)
    # need enough moves left after skipping 20 plies to be worth analyzing
    candidates = [c for c in candidates if pgn_move_count(c["pgn_moves"]) > SKIP_PLIES + 10]

    clean = [c for c in candidates if c["label"] == 0]
    cheat = [c for c in candidates if c["label"] == 1]
    print(f"Eligible candidates: {len(clean)} clean, {len(cheat)} cheater "
          f"(before sampling)")

    random.shuffle(clean)
    random.shuffle(cheat)
    sample = clean[:args.n_per_class] + cheat[:args.n_per_class]
    random.shuffle(sample)

    print(f"Analyzing {len(sample)} sampled games at depth 12 "
          f"(skipping first {SKIP_PLIES} plies each)... this will take a while.")

    rows = []
    for i, c in enumerate(sample):
        header = (
            f'[Event "Kaggle Cheat Dataset"]\n'
            f'[White "white_side"]\n[Black "black_side"]\n'
            f'[Result "{c["score"]}"]\n\n'
        )
        pgn_text = header + c["pgn_moves"] + "\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as tmp:
            tmp.write(pgn_text)
            tmp_path = tmp.name

        try:
            results = analyze_game(tmp_path, args.engine_path, skip_plies=SKIP_PLIES)
            if c["color"] not in results:
                print(f"  [{i+1}/{len(sample)}] row {c['row_idx']} {c['color']}: "
                      f"no moves left after skip, skipping")
                continue
            r = results[c["color"]]
            row = {
                "row_idx": c["row_idx"],
                "color": c["color"],
                "true_label": c["label"],
                "cheat_frac": round(c["cheat_frac"], 2),
                "top1_match_rate": r["top1_match_rate"],
                "avg_centipawn_loss": r["avg_centipawn_loss"],
            }
            row.update(windowed_features(r["cp_loss_sequence"]))
            rows.append(row)
            print(f"  [{i+1}/{len(sample)}] row {c['row_idx']} {c['color']}: "
                  f"true_label={c['label']} match={r['top1_match_rate']}% "
                  f"cp_loss={r['avg_centipawn_loss']}")
        finally:
            os.unlink(tmp_path)

    val_df = pd.DataFrame(rows)
    val_df.to_csv(args.out, index=False)
    print(f"\nSaved {len(val_df)} validation rows to {args.out}")

    # --- Fit our model on OUR original data, test on THIS external data ---
    train_df = pd.read_csv(args.dataset_csv)
    features = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
                "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]
    model = LogisticRegression()
    model.fit(train_df[features], train_df["label"])

    preds = model.predict(val_df[features])
    print("\n=== External validation: trained on OUR data, tested on Kaggle data ===")
    print(classification_report(val_df["true_label"], preds,
                                 target_names=["clean", "cheater"]))
    cm = confusion_matrix(val_df["true_label"], preds)
    print("Confusion matrix:")
    print(f"                 predicted clean   predicted cheater")
    print(f"  actual clean   {cm[0][0]:>15d}   {cm[0][1]:>17d}")
    print(f"  actual cheater {cm[1][0]:>15d}   {cm[1][1]:>17d}")


if __name__ == "__main__":
    main()
