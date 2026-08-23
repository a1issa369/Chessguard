"""
train_final_model.py

Trains the FINAL model for deployment, using ALL labeled Kaggle data we've
collected (train + test combined). We already reported honest held-out
metrics in kaggle_train_pipeline.py -- that evaluation already happened,
so it's standard practice to now retrain on everything available before
shipping, rather than throwing away 20 good labeled examples.

Saves:
    model.joblib        -- the fitted classifier
    model_features.json -- exact feature name + order the model expects,
                            so the API can't accidentally feed features
                            in the wrong order (a silent, nasty bug class)
"""

import json

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

FEATURES = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
            "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]


def main():
    train_df = pd.read_csv("kaggle_train.csv")
    test_df = pd.read_csv("kaggle_test.csv")
    combined = pd.concat([train_df, test_df], ignore_index=True)

    print(f"Training final model on {len(combined)} total labeled examples "
          f"({sum(combined['label']==0)} clean, {sum(combined['label']==1)} cheater)")

    X, y = combined[FEATURES], combined["label"]
    model = LogisticRegression()
    model.fit(X, y)

    joblib.dump(model, "model.joblib")
    with open("model_features.json", "w") as f:
        json.dump(FEATURES, f)

    print("Saved model.joblib and model_features.json")


if __name__ == "__main__":
    main()
