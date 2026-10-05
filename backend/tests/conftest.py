"""
Test fixtures. app.py loads model/model.joblib at import time, so the
fixture below builds a tiny stand-in model in a temp directory and imports
app from there. Tests never need Stockfish, the network, or the real model:
fetch_recent_games and score_pgn_text are replaced with fakes.
"""
import importlib
import json
import os
import sys

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEATURES = [
    "top1_match_rate", "avg_centipawn_loss", "max_window_match_rate",
    "min_window_avg_cp_loss", "perfect_move_frac", "longest_perfect_streak",
]


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    work = tmp_path_factory.mktemp("work")
    (work / "model").mkdir()
    X = pd.DataFrame(
        [[20, 90, 10, 80, 0.0, 0], [30, 70, 20, 60, 0.1, 1],
         [80, 10, 90, 5, 0.6, 9], [90, 5, 100, 2, 0.8, 12]],
        columns=FEATURES)
    joblib.dump(LogisticRegression().fit(X, [0, 0, 1, 1]), work / "model" / "model.joblib")
    (work / "model" / "model_features.json").write_text(json.dumps(FEATURES))

    old_cwd = os.getcwd()
    os.chdir(work)
    sys.path.insert(0, BACKEND_DIR)
    try:
        yield importlib.import_module("app")
    finally:
        os.chdir(old_cwd)
        sys.path.remove(BACKEND_DIR)


@pytest.fixture
def client(app_module):
    from fastapi.testclient import TestClient
    app_module.CACHE.clear()
    app_module.LIMITER.clear()
    return TestClient(app_module.app)


def make_game(white, black, end_time, with_clock=True):
    clk = " {[%clk 0:05:00]}" if with_clock else ""
    return {"pgn": f'[White "{white}"]\n[Black "{black}"]\n\n1. e4{clk} e5{clk}',
            "end_time": end_time, "time_control": "600"}


def fake_scores(pgn_text):
    """Stands in for score_pgn_text: parses the two player names out of the PGN."""
    names = {}
    for line in pgn_text.splitlines():
        if line.startswith("[White "):
            names["white"] = line.split('"')[1]
        if line.startswith("[Black "):
            names["black"] = line.split('"')[1]
    side = lambda name, p: {"player": name, "moves_analyzed": 30,
                            "features": {"top1_match_rate": 50.0}, "cheat_probability": p}
    return {"white": side(names["white"], 0.2), "black": side(names["black"], 0.9)}
