"""
train_classifier.py

Trains a logistic regression classifier to distinguish "clean" vs
"cheater-like" chess games based on two engine-correlation features.

Requires:
    pip install pandas scikit-learn

Usage:
    python3 train_classifier.py dataset.csv
"""

import sys

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import confusion_matrix, classification_report


FEATURES = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
            "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]
LABEL = "label"


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "dataset.csv"
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} rows: {sum(df[LABEL] == 0)} clean, "
          f"{sum(df[LABEL] == 1)} cheater\n")

    X = df[FEATURES]
    y = df[LABEL]

    model = LogisticRegression()

    # 5-fold stratified CV: "stratified" means each fold keeps roughly the
    # same clean/cheater ratio as the full dataset -- important with
    # imbalanced classes, otherwise a fold could randomly end up with
    # almost no cheater examples and give a misleading score.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    scoring = ["accuracy", "precision", "recall", "f1"]
    results = cross_validate(model, X, y, cv=cv, scoring=scoring)

    print("=== 5-Fold Cross-Validation Results ===")
    for metric in scoring:
        scores = results[f"test_{metric}"]
        print(f"{metric:10s}: {scores.mean():.3f}  (per-fold: {[round(s,2) for s in scores]})")

    # Now fit on ALL the data to inspect learned coefficients and produce
    # a confusion matrix on the training data itself. NOTE: this confusion
    # matrix is on training data, so it's optimistic -- the CV numbers
    # above are the trustworthy estimate of real-world performance.
    model.fit(X, y)
    print("\n=== Learned coefficients (fit on full dataset) ===")
    for feature, coef in zip(FEATURES, model.coef_[0]):
        direction = "higher -> more cheater-like" if coef > 0 else "higher -> more clean-like"
        print(f"  {feature:20s}: {coef:+.4f}  ({direction})")

    preds = model.predict(X)
    print("\n=== Confusion matrix (on training data -- optimistic, see CV above) ===")
    cm = confusion_matrix(y, preds)
    print(f"                 predicted clean   predicted cheater")
    print(f"  actual clean   {cm[0][0]:>15d}   {cm[0][1]:>17d}")
    print(f"  actual cheater {cm[1][0]:>15d}   {cm[1][1]:>17d}")

    print("\n" + classification_report(y, preds, target_names=["clean", "cheater"]))


if __name__ == "__main__":
    main()
