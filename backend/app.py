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

import hmac
import json
import os
import tempfile
import time
from typing import Literal
import urllib.error

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine_analysis import analyze_game
from features import windowed_features
from guards import ConcurrencyGate, RateLimiter, TTLCache
from fetch_games import fetch_recent_games
from usage import UsageLogger

# Set this to wherever Stockfish lives on YOUR machine if different.
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")

MODEL = joblib.load("model/model.joblib")
with open("model/model_features.json") as f:
    FEATURES = json.load(f)

app = FastAPI(title="ChessGuard API")

# Allow the local dev servers plus, in production, whatever frontend
# domain is set via env var (e.g. your Vercel deployment URL). Comma-
# separated so you can list more than one if needed.
_extra_origins = os.environ.get("FRONTEND_ORIGINS", "")
ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"] + [
    o.strip() for o in _extra_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PgnRequest(BaseModel):
    pgn: str


class UsernameRequest(BaseModel):
    username: str = Field(min_length=1, max_length=25, pattern=r"^[A-Za-z0-9_-]+$")
    max_games: int = Field(3, ge=1, le=10)  # engine analysis is slow
    sort_order: Literal["recent", "earliest"] = "recent"


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


def _analyze_username_uncached(req: UsernameRequest):
    try:
        games = fetch_recent_games(req.username, months=4)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise HTTPException(status_code=404, detail={
                "code": "USER_NOT_FOUND",
                "message": f"No Chess.com account named '{req.username}'."})
        raise HTTPException(status_code=502, detail={
            "code": "UPSTREAM_ERROR",
            "message": f"Chess.com returned an error ({e.code}). Try again shortly."})
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "code": "UPSTREAM_ERROR",
            "message": f"Could not reach Chess.com: {e}"})

    if not games:
        raise HTTPException(status_code=404, detail={"code": "NO_GAMES",
                                                            "message": f"No games found for '{req.username}'."})

    # Only games with clock data and non-bullet time controls are usable --
    # same filtering logic we used building our own training data.
    usable = [g for g in games if g.get("pgn") and "%clk" in g["pgn"]]

    # Chess.com's archive returns games oldest -> newest, so the END of the
    # list is "most recent" and the START is "earliest" -- no re-sorting
    # needed, just pick which end to slice from.
    if req.sort_order == "earliest":
        selected = usable[:req.max_games]
    else:
        selected = usable[-req.max_games:]

    if not selected:
        raise HTTPException(status_code=404, detail={
            "code": "NO_USABLE_GAMES",
            "message": "No recent games with clock data found. Try a player who plays rapid or blitz, not bullet."})

    results = []
    for g in selected:
        try:
            side_results = score_pgn_text(g["pgn"])
        except Exception as e:
            # Don't 500 the whole request over one bad game -- but DO log
            # it, otherwise every game silently disappearing looks
            # identical to "no games found" from the outside.
            print(f"Skipping a game due to analysis error: {e}")
            continue

        # Find the requested player's side AND their opponent's name, so
        # the UI can show "playerA vs playerB" instead of just one name.
        own, opponent_name = None, "Unknown"
        for color, r in side_results.items():
            if r["player"].lower() == req.username.lower():
                own = r
            else:
                opponent_name = r["player"]

        if own is not None:
            results.append({
                "end_time": g.get("end_time"),
                "time_control": g.get("time_control"),
                "opponent": opponent_name,
                **own,
            })

    return {"username": req.username, "games_analyzed": len(results), "results": results}


# ---------------------------------------------------------------------------
# Guards around the expensive endpoint (see guards.py for the reasoning).
# ---------------------------------------------------------------------------
CACHE = TTLCache(ttl_seconds=int(os.environ.get("CACHE_TTL_SECONDS", "600")))
LIMITER = RateLimiter(limit=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "6")), window_seconds=60)
GATE = ConcurrencyGate(max_concurrent=int(os.environ.get("MAX_CONCURRENT_ANALYSES", "2")))
# Lowers the per-request game cap on slow hosts (the schema still allows up to 10).
MAX_GAMES_LIMIT = int(os.environ.get("MAX_GAMES_LIMIT", "10"))

# Anonymous usage logging (see usage.py). Does nothing unless SUPABASE_URL and
# SUPABASE_SECRET_KEY are set. EXAMPLE_USERNAME marks the "Try an example"
# account; OWNER_KEY lets the author tag their own curl tests (header
# X-ChessGuard-Owner) so they can be excluded from the stats.
USAGE = UsageLogger.from_env()
EXAMPLE_USERNAME = os.environ.get("EXAMPLE_USERNAME", "Nitrobeast705").lower()
OWNER_KEY = os.environ.get("OWNER_KEY", "")


def _is_owner(request: Request) -> bool:
    supplied = request.headers.get("x-chessguard-owner", "")
    return bool(OWNER_KEY) and hmac.compare_digest(supplied, OWNER_KEY)


def _log_usage(**event) -> None:
    try:
        USAGE.record(**event)
    except Exception as e:  # never let logging affect a response
        print(f"usage logging failed: {e}")


def _client_ip(request: Request) -> str:
    # Behind Render's proxy the real client is in X-Forwarded-For. This is
    # best-effort (a client can spoof it); GATE is the hard protection.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _analyze_with_guards(req: UsernameRequest, request: Request):
    """Returns (result, served_from_cache)."""
    if req.max_games > MAX_GAMES_LIMIT:
        raise HTTPException(status_code=400, detail={
            "code": "TOO_MANY_GAMES",
            "message": f"This server analyzes at most {MAX_GAMES_LIMIT} games per request."})

    key = (req.username.lower(), req.max_games, req.sort_order)

    cached = CACHE.get(key)
    if cached is not None:
        return cached, True

    if not LIMITER.allow(_client_ip(request)):
        raise HTTPException(status_code=429, detail={
            "code": "RATE_LIMITED",
            "message": "Too many requests. Please wait a minute and try again."})

    if not GATE.acquire():
        raise HTTPException(status_code=429, detail={
            "code": "BUSY",
            "message": "The analyzer is busy with other requests. Try again in a minute."})
    try:
        result = _analyze_username_uncached(req)
    finally:
        GATE.release()

    if result["games_analyzed"] > 0:
        CACHE.set(key, result)
    return result, False


@app.post("/analyze/username")
def analyze_username(req: UsernameRequest, request: Request):
    started = time.perf_counter()
    outcome, games_analyzed, cache_hit = "ok", 0, False
    try:
        result, cache_hit = _analyze_with_guards(req, request)
        games_analyzed = result["games_analyzed"]
        if games_analyzed == 0:
            outcome = "NO_RESULTS"  # every selected game failed to analyze
        return result
    except HTTPException as e:
        detail = e.detail
        outcome = detail.get("code", "ERROR") if isinstance(detail, dict) else "ERROR"
        raise
    except Exception:
        outcome = "INTERNAL_ERROR"
        raise
    finally:
        _log_usage(
            outcome=outcome,
            games_requested=req.max_games,
            games_analyzed=games_analyzed,
            cache_hit=cache_hit,
            duration_ms=int((time.perf_counter() - started) * 1000),
            is_example=req.username.lower() == EXAMPLE_USERNAME,
            is_owner=_is_owner(request),
        )
