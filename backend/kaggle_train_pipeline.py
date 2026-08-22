"""
kaggle_train_pipeline.py

Trains AND tests directly on the real Kaggle "Spotting Cheaters" dataset,
using a genuinely disjoint split -- no game appears in both sets. This
replaces our synthetic generator as the primary training source, since we
found it doesn't represent realistic (partial) cheating well enough.

Usage:
    python3 kaggle_train_pipeline.py Games.csv /opt/homebrew/bin/stockfish \
        --train_per_class 15 --test_per_class 10 --seed 7
"""

import argparse
import os
import random
import tempfile

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, confusion_matrix

from engine_analysis import analyze_game
from features import windowed_features
from kaggle_validate import build_candidates, pgn_move_count, SKIP_PLIES

FEATURES = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
            "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]


def analyze_candidate(c: dict, engine_path: str) -> dict:
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
        results = analyze_game(tmp_path, engine_path, skip_plies=SKIP_PLIES)
        if c["color"] not in results:
            return None
        r = results[c["color"]]
        row = {
            "row_idx": c["row_idx"],
            "color": c["color"],
            "label": c["label"],
            "top1_match_rate": r["top1_match_rate"],
            "avg_centipawn_loss": r["avg_centipawn_loss"],
        }
        row.update(windowed_features(r["cp_loss_sequence"]))
        return row
    finally:
        os.unlink(tmp_path)


def process_batch(candidates: list, engine_path: str, tag: str) -> list:
    rows = []
    for i, c in enumerate(candidates):
        row = analyze_candidate(c, engine_path)
        if row is None:
            print(f"  [{tag} {i+1}/{len(candidates)}] row {c['row_idx']}: skipped (no moves after skip)")
            continue
        rows.append(row)
        print(f"  [{tag} {i+1}/{len(candidates)}] row {c['row_idx']} {c['color']}: "
              f"label={c['label']} match={row['top1_match_rate']}% cp_loss={row['avg_centipawn_loss']}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("engine_path")
    parser.add_argument("--train_per_class", type=int, default=15)
    parser.add_argument("--test_per_class", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out_train", default="kaggle_train.csv")
    parser.add_argument("--out_test", default="kaggle_test.csv")
    args = parser.parse_args()

    random.seed(args.seed)

    df = pd.read_csv(args.csv_path)
    candidates = build_candidates(df)
    candidates = [c for c in candidates if pgn_move_count(c["pgn_moves"]) > SKIP_PLIES + 10]

    clean = [c for c in candidates if c["label"] == 0]
    cheat = [c for c in candidates if c["label"] == 1]
    random.shuffle(clean)
    random.shuffle(cheat)

    n_train, n_test = args.train_per_class, args.test_per_class
    # Disjoint slices -- train and test never share a row, by construction.
    train_candidates = clean[:n_train] + cheat[:n_train]
    test_candidates = clean[n_train:n_train + n_test] + cheat[n_train:n_train + n_test]
    random.shuffle(train_candidates)
    random.shuffle(test_candidates)

    print(f"Analyzing {len(train_candidates)} TRAIN games...")
    train_rows = process_batch(train_candidates, args.engine_path, "train")
    print(f"\nAnalyzing {len(test_candidates)} TEST games (held out, disjoint from train)...")
    test_rows = process_batch(test_candidates, args.engine_path, "test")

    train_df = pd.DataFrame(train_rows)
    test_df = pd.DataFrame(test_rows)
    train_df.to_csv(args.out_train, index=False)
    test_df.to_csv(args.out_test, index=False)
    print(f"\nSaved {len(train_df)} train rows -> {args.out_train}")
    print(f"Saved {len(test_df)} test rows -> {args.out_test}")

    # Internal CV on the training set, same as train_classifier.py
    X_train, y_train = train_df[FEATURES], train_df["label"]
    model = LogisticRegression()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(model, X_train, y_train, cv=cv,
                                 scoring=["accuracy", "precision", "recall", "f1"])
    print("\n=== CV on Kaggle TRAINING data ===")
    for metric in ["accuracy", "precision", "recall", "f1"]:
        print(f"{metric:10s}: {cv_results[f'test_{metric}'].mean():.3f}")

    # The real test: fit on train, evaluate on genuinely held-out test rows
    model.fit(X_train, y_train)
    X_test, y_test = test_df[FEATURES], test_df["label"]
    preds = model.predict(X_test)

    print("\n=== HELD-OUT Kaggle TEST results (trained on Kaggle, tested on different Kaggle rows) ===")
    print(classification_report(y_test, preds, target_names=["clean", "cheater"]))
    cm = confusion_matrix(y_test, preds)
    print("Confusion matrix:")
    print(f"                 predicted clean   predicted cheater")
    print(f"  actual clean   {cm[0][0]:>15d}   {cm[0][1]:>17d}")
    print(f"  actual cheater {cm[1][0]:>15d}   {cm[1][1]:>17d}")

    print("\n=== Learned coefficients ===")
    for feature, coef in zip(FEATURES, model.coef_[0]):
        print(f"  {feature:22s}: {coef:+.4f}")


if __name__ == "__main__":
    main()
