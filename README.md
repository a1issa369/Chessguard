# ChessGuard

A full-stack fair-play (cheat) detection system for online chess, built to
explore the same core problem that shows up in fraud detection and
anomaly detection more broadly: **spotting behavior that deviates from a
normal baseline, using engine correlation as a proxy signal.**

Given a Chess.com username, ChessGuard fetches recent games, analyzes
every move against a chess engine, and produces a fair-play risk score
for that player -- surfaced through a React dashboard backed by a
FastAPI + scikit-learn service.

## Why this project

Fraud and anomaly detection systems generally work the same way: define
what "normal" looks like, measure deviation from it, and be honest about
where your detector breaks down. Chess cheat detection is a clean,
self-contained version of that same problem -- there's a ground-truth
"best move" available at every position (from a chess engine), which
makes it possible to build, test, and honestly evaluate a real anomaly
detection pipeline end to end.

## Key technical finding

The most interesting result in this project wasn't the final accuracy
number -- it was a generalization failure, and the process of diagnosing
it:

1. A classifier trained on **synthetic** cheating data (engine self-play)
   scored 83% accuracy in cross-validation.
2. Validated against a real, independently-labeled dataset (Kaggle's
   ["Spotting Cheaters"](https://www.kaggle.com/datasets/brieucdandoy/chess-cheating-dataset)
   Stockfish-vs-Maia bot games), accuracy dropped to 65%.
3. Adding richer "windowed" features (to catch intermittent, not just
   constant, cheating) *improved* the synthetic-data CV score to 85% --
   but dropped real-world accuracy further, to 50%. Better performance
   on your own validation set while performance drops on independent
   data is the classic signature of overfitting to dataset-specific
   artifacts rather than the true underlying signal.
4. The actual fix wasn't a better model or more features -- it was
   training on realistic data. Retraining directly on a properly
   disjoint train/test split of the real Kaggle dataset brought accuracy
   on genuinely held-out data to **90%**.

Full details, numbers, and reasoning are in
[`backend/NOTES.md`](backend/NOTES.md) *(optional: add a written case
study here)*.

## Architecture

```
Chess.com API ──▶ PGN parsing ──▶ Stockfish engine analysis ──▶ feature
                                   extraction ──▶ logistic regression
                                   classifier ──▶ FastAPI ──▶ React dashboard
```

- **`pgn_parser.py`** -- hand-rolled PGN parser (move-time extraction)
- **`fetch_games.py`** -- Chess.com public API client
- **`engine_analysis.py`** -- per-move Stockfish evaluation, engine
  top-move match rate, centipawn loss
- **`features.py`** -- windowed/rolling features for catching
  intermittent cheating
- **`generate_synthetic_cheaters.py`** -- Stockfish self-play synthetic
  data generator (early-stage training data; superseded by real Kaggle
  data, see finding above)
- **`build_dataset.py`**, **`kaggle_validate.py`**,
  **`kaggle_train_pipeline.py`** -- dataset construction and validation
- **`train_final_model.py`**, **`app.py`** -- production model training
  and FastAPI serving layer
- **`frontend/`** -- React + Tailwind dashboard

## Tech stack

Python, FastAPI, scikit-learn, pandas, python-chess, Stockfish, React,
Tailwind CSS, Vite.

## Running it locally

### Backend

```bash
cd backend
pip install -r requirements.txt
brew install stockfish   # or your platform's equivalent

python3 train_final_model.py     # trains and saves the model
uvicorn app:app --reload --port 8000
```

Set `STOCKFISH_PATH` as an environment variable if Stockfish isn't at
`/opt/homebrew/bin/stockfish`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Limitations / future work

- Trained on a modest sample (50 real labeled games) -- the source
  dataset has ~49,000 games available, and scaling up training data
  would likely improve robustness further.
- Only two engineered feature families (move-match-rate and
  centipawn-loss based); a production system would likely add opening
  -book detection, account-level behavioral history, and multi-game
  aggregation.
- Analysis is currently synchronous and depth-12 Stockfish evaluation is
  slow (multiple seconds per game); a production version would move
  this to an async job queue.

## License

MIT
