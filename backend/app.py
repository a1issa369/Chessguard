"""
app.py

FastAPI backend for ChessGuard. Two endpoints:

  POST /analyze/username  -- fetch a Chess.com player's recent games and
                              score each one
  POST /analyze/pgn       -- score a single pasted PGN directly (useful
                              for testing without hitting the Chess.com API)

Run locally with:
    uvicorn app:app --reload --port 8000

Requires:
    pip install fastapi uvicorn joblib
    (pandas, scikit-learn, python-chess already installed)
"""

import json
import os
import tempfile

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine_analysis import analyze_game
from features import windowed_features
from fetch_games import fetch_recent_games

# Set this to wherever Stockfish lives on YOUR machine if different.
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")

MODEL = joblib.load("model/model.joblib")
with open("model/model_features.json") as f:
    FEATURES = json.load(f)

app = FastAPI(title="ChessGuard API")

# Allow the React dev server (localhost:5173 for Vite, 3000 for CRA) to
# call this API from the browser. In production you'd lock this down to
# your actual frontend's domain instead of allowing everything.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PgnRequest(BaseModel):
    pgn: str


class UsernameRequest(BaseModel):
    username: str
    max_games: int = 3  # engine analysis is slow -- keep this small for a live demo


def score_pgn_text(pgn_text: str) -> dict:
    """Runs a single PGN through the full feature pipeline + model, for
    BOTH sides, and returns per-side results."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pgn", delete=False) as tmp:
        tmp.write(pgn_text)
        tmp_path = tmp.name

    try:
        analysis = analyze_game(tmp_path, STOCKFISH_PATH)
    finally:
        os.unlink(tmp_path)

    side_results = {}
    for color, r in analysis.items():
        feature_row = {
            "top1_match_rate": r["top1_match_rate"],
            "avg_centipawn_loss": r["avg_centipawn_loss"],
        }
        feature_row.update(windowed_features(r["cp_loss_sequence"]))

        # Build the feature vector in the EXACT order the model expects --
        # this is what model_features.json is for. We wrap it in a
        # DataFrame with matching column names (not a bare list) because
        # the model was TRAINED on a DataFrame with named columns --
        # scikit-learn warns about this mismatch otherwise, and matching
        # it properly is more robust than silencing the warning.
        X = pd.DataFrame([feature_row])[FEATURES]
        cheat_probability = MODEL.predict_proba(X)[0][1]

        side_results[color] = {
            "player": r["player"],
            "moves_analyzed": r["moves_analyzed"],
            "features": feature_row,
            "cheat_probability": round(float(cheat_probability), 3),
        }
    return side_results


@app.get("/")
def health_check():
    return {"status": "ok", "model_features": FEATURES}


@app.post("/analyze/pgn")
def analyze_pgn(req: PgnRequest):
    try:
        return score_pgn_text(req.pgn)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not analyze PGN: {e}")


@app.post("/analyze/username")
def analyze_username(req: UsernameRequest):
    try:
        games = fetch_recent_games(req.username, months=1)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch games for "
                             f"'{req.username}': {e}")

    if not games:
        raise HTTPException(status_code=404, detail=f"No games found for '{req.username}'")

    # Only games with clock data and non-bullet time controls are usable --
    # same filtering logic we used building our own training data.
    usable = [g for g in games if g.get("pgn") and "%clk" in g["pgn"]]
    usable = usable[-req.max_games:]  # most recent N

    if not usable:
        raise HTTPException(status_code=404,
                             detail="No recent games with clock data found "
                                    "(try a player who plays rapid/blitz, not bullet)")

    results = []
    for g in usable:
        try:
            side_results = score_pgn_text(g["pgn"])
        except Exception as e:
            continue  # skip any game that fails to parse/analyze rather than 500ing the whole request

        # Only report the requested player's side, not their opponent's
        for color, r in side_results.items():
            if r["player"].lower() == req.username.lower():
                results.append({
                    "end_time": g.get("end_time"),
                    "time_control": g.get("time_control"),
                    **r,
                })

    return {"username": req.username, "games_analyzed": len(results), "results": results}
