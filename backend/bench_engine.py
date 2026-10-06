"""Times the real analysis on a sample game.
Usage (from backend/):  python3 bench_engine.py sample_games/sample1.pgn /opt/homebrew/bin/stockfish
Run it once on the old engine_analysis.py (git stash) and once on the new one,
and compare the timings and the printed numbers."""
import sys
import time

from engine_analysis import analyze_game

pgn, sf = sys.argv[1], sys.argv[2]
t = time.perf_counter()
res = analyze_game(pgn, sf)
dt = time.perf_counter() - t
for color, r in res.items():
    print(color, r["player"], r["moves_analyzed"], "moves",
          "top1", r["top1_match_rate"], "acpl", r["avg_centipawn_loss"])
print(f"elapsed: {dt:.1f}s")
