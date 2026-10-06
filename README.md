# ChessGuard

[![CI](https://github.com/a1issa369/Chessguard/actions/workflows/ci.yml/badge.svg)](https://github.com/a1issa369/Chessguard/actions/workflows/ci.yml)

**Live demo: [chessguard.me](https://chessguard.me)** (free hosting, so the
first request after a quiet period can take about a minute to wake the server)

A full-stack fair-play (cheat) detection system for online chess, built to
explore the same core problem that shows up in fraud detection and
anomaly detection more broadly: **spotting behavior that deviates from a
normal baseline, using engine correlation as a proxy signal.**

Given a Chess.com username, ChessGuard fetches recent games, analyzes
every move against Stockfish, and produces a fair-play risk score for each
game, shown in a React dashboard backed by a FastAPI and scikit-learn
service. It is a student project and its scores are statistical estimates,
not proof that anyone cheated.

## Why this project

Fraud and anomaly detection systems generally work the same way: define
what "normal" looks like, measure deviation from it, and be honest about
where your detector breaks down. Chess cheat detection is a clean,
self-contained version of that problem: a ground-truth "best move" is
available at every position (from a chess engine), which makes it possible
to build, test, and honestly evaluate a real anomaly detection pipeline
end to end.

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

One caveat worth stating plainly: the final held-out test set is only 20
games, so 90% carries wide error bars. It shows the right lesson (match
your training data to the real distribution), not a production-grade
accuracy claim.

## Architecture

```
Chess.com API --> PGN parsing --> Stockfish analysis --> feature extraction
   --> logistic regression --> FastAPI (cache, rate limit, concurrency cap)
   --> React dashboard
```

- **`pgn_parser.py`**: hand-rolled PGN parser (move-time extraction)
- **`fetch_games.py`**: Chess.com public API client
- **`engine_analysis.py`**: per-move Stockfish evaluation, engine top-move
  match rate, centipawn loss
- **`features.py`**: windowed/rolling features for catching intermittent
  cheating
- **`guards.py`**: result cache, per-client rate limiter, and a concurrency
  cap that protect the CPU-heavy endpoint
- **`generate_synthetic_cheaters.py`**: Stockfish self-play data generator
  (early-stage training data, superseded by real Kaggle data)
- **`build_dataset.py`**, **`kaggle_validate.py`**,
  **`kaggle_train_pipeline.py`**: dataset construction and validation
- **`train_final_model.py`**, **`app.py`**: model training and the FastAPI
  serving layer
- **`frontend/`**: React, Tailwind CSS and Vite dashboard

## Engineering practices

- **Automated tests and CI.** More than 80 tests (pytest for the API and
  helpers, Vitest and Testing Library for the UI) run on every push through
  GitHub Actions. API tests replace Chess.com and Stockfish with fakes, so
  they run in under a second.
- **Structured errors.** The API returns machine-readable codes
  (`USER_NOT_FOUND`, `BUSY`, ...) that the UI turns into toast notifications,
  instead of parsing error strings.
- **Input validation on both sides.** Usernames are restricted to Chess.com's
  character set because they are placed inside a URL, which also blocks path
  tricks like `../`. Game count is bounded to 1 through 10.
- **Protecting an expensive endpoint.** Each analysis runs Stockfish, so the
  server caches results for ten minutes, rate-limits clients, and caps
  concurrent analyses so a burst of traffic gets a friendly "busy" message
  instead of freezing the server.
- **Security headers.** HSTS, a strict Content-Security-Policy, and no
  secrets in the browser bundle (the only `VITE_` values are public).
- **Accessibility and polish.** Keyboard focus rings, labeled controls,
  WCAG-checked contrast, reduced-motion support, day and night themes,
  responsive down to phone width, and a custom 404 page.

## Performance: why a game takes about a minute

Judging whether a move was engine-like requires knowing the best move, so
for every move in a game Stockfish searches the position 12 moves deep
(depth 12) and the result is compared with what the player actually did.
A 44-move game is about 88 half-moves, and each move that is not the
engine's top choice needs a second search to measure how much worse it was,
so one game is on the order of 130 searches.

- **It is a hosting budget, not a design limit.** A short 20-half-move
  sample analyzes in about 1.4 seconds on my laptop. The free Render tier
  gives the service about a tenth of a CPU core, and a one-game request
  measured 48.7 seconds there. The site says so up front.
- **Depth is tied to the model.** The classifier was trained on depth-12
  features. Lowering the depth would be faster but would shift the inputs
  and quietly make the scores less reliable, so the depth stays fixed.
- **An optimization I tested and rejected.** The position after one move is
  searched again as the "before" position of the next, so reusing the first
  result cuts searches by roughly a third. I benchmarked it against the
  original on a sample game and the features moved (for example, one
  side's top-1 match rate went from 100% to 90%), because a repeated search
  with a warm hash can choose a different near-equal best move. A change
  that alters model inputs is not a free speedup, so I reverted it.
- **Mitigations that are in place.** Results are cached for ten minutes,
  requests are capped at 3 games and rate-limited, and the page warns about
  the wait and pings the server on load to wake it early.
- **What would actually fix it.** More CPU (a paid instance), or moving
  analysis to an async job queue with progress polling so the wait does not
  block the page.

## API

| Endpoint | Purpose |
|---|---|
| `GET /` | Health check |
| `POST /analyze/username` | Fetch and score a player's recent games |
| `POST /analyze/pgn` | Score a single pasted PGN |

Error codes from `/analyze/username`: `USER_NOT_FOUND` (404), `NO_GAMES`
(404), `NO_USABLE_GAMES` (404), `UPSTREAM_ERROR` (502), `BUSY` (429),
`RATE_LIMITED` (429), plus a 422 for invalid input.

## Running it locally

### Backend

```bash
cd backend
pip install -r requirements.txt
brew install stockfish   # or your platform's equivalent

python3 train_final_model.py     # trains and saves the model
uvicorn app:app --reload --port 8000
```

Set `STOCKFISH_PATH` if Stockfish isn't at `/opt/homebrew/bin/stockfish`.
Retraining from the Kaggle data also needs `pip install -r requirements-train.txt`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Tests

```bash
cd backend && pip install -r requirements-dev.txt && python3 -m pytest -q
cd frontend && npm test
```

## Deployment

The backend runs as a Docker container (Render) and the frontend as a static
build (Vercel).

| Where | Setting | Value |
|---|---|---|
| Render | Root directory | `backend` |
| Render | `FRONTEND_ORIGINS` | comma-separated site origins, for example `https://chessguard.me,https://www.chessguard.me` |
| Render | `MAX_CONCURRENT_ANALYSES` | `1` on a free single-CPU instance |
| Render | `MAX_GAMES_LIMIT` | `3` on a free instance (about a minute per game) |
| Render | `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | optional: turns on anonymous usage logging (see `analytics/`) |
| Render | `OWNER_KEY` | optional: a secret that lets the author's own curl tests be excluded from usage stats |
| Vercel | Root directory | `frontend` |
| Vercel | `VITE_API_BASE` | the Render service URL (HTTPS) |
| Vercel | `VITE_SITE_URL` | the public site URL, for example `https://chessguard.me` |
| Vercel | `VITE_MAX_GAMES` | `3`, matching the Render limit |

`VITE_SITE_URL` fills in the social-preview tags and generates
`sitemap.xml` and `robots.txt` at build time.

## Usage statistics

The server writes one anonymous row per analysis request (outcome, games
requested and analyzed, cache hit, duration) to a Supabase table. There is no
field for a username or IP address, writes happen off the request path and can
never fail a request, and the table is locked down with row level security so
only the server's secret key can touch it. `analytics/usage_events.sql` creates
the table and `analytics/usage_stats.sql` holds the queries behind numbers such
as cache hit rate and median and p95 seconds per game.

## Limitations and future work

- Trained on a modest sample (50 real labeled games). The source dataset
  has about 49,000 games, and scaling up would likely improve robustness.
- Only two engineered feature families (move-match-rate and centipawn-loss
  based). A production system would likely add opening-book detection,
  account-level behavioral history, and multi-game aggregation.
- Analysis is synchronous and depth-12 Stockfish is slow, so a production
  version would move it to an async job queue with polling.
- The cache and rate limiter live in one server's memory. Running several
  instances would need a shared store such as Redis.
- Free hosting sleeps when idle, so the first request after a quiet period
  can take about a minute (the page pings the server on load to reduce this).

## License

MIT
