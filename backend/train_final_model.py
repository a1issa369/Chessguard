import json
import os

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

FEATURES = ["top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
            "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak"]


def main():
    train_df = pd.read_csv("data/kaggle_train.csv")
    test_df = pd.read_csv("data/kaggle_test.csv")
    combined = pd.concat([train_df, test_df], ignore_index=True)

    print(f"Training final model on {len(combined)} total labeled examples "
          f"({sum(combined['label']==0)} clean, {sum(combined['label']==1)} cheater)")

    X, y = combined[FEATURES], combined["label"]
    model = LogisticRegression()
    model.fit(X, y)

    os.makedirs("model", exist_ok=True)
    joblib.dump(model, "model/model.joblib")
    with open("model/model_features.json", "w") as f:
        json.dump(FEATURES, f)

    print("Saved model/model.joblib and model/model_features.json")


if __name__ == "__main__":
    main()
