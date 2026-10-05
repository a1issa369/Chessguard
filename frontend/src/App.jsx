import { useEffect, useMemo, useRef, useState } from "react";
import { analyzeUsername, MAX_GAMES, warmUpServer } from "./api";
import { trackEvent } from "./analytics";
import { SITE } from "./config";
import { toastForError } from "./errors";
import { validateUsername } from "./validation";
import usePageMeta from "./hooks/usePageMeta";
import GameCard from "./components/GameCard";
import { FairPlayBarSkeleton } from "./components/FairPlayBar";
import SiteFooter from "./components/SiteFooter";
import ThemeToggle from "./components/ThemeToggle";
import ToastStack, { useToasts } from "./components/ToastStack";

export default function App({ theme, onThemeChange }) {
  usePageMeta("ChessGuard | Chess.com Fair-Play Analysis");

  const [username, setUsername] = useState("");
  const [fieldError, setFieldError] = useState(null);
  const [maxGames, setMaxGames] = useState(3);
  const [sortOrder, setSortOrder] = useState("recent");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState(null);
  const { toasts, push, dismiss } = useToasts();
  const inputRef = useRef(null);

  useEffect(() => {
    warmUpServer();
  }, []);

  // Free hosting sleeps when idle, so the first request can take a while.
  // After 8 seconds, tell the visitor why instead of leaving them guessing.
  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return undefined;
    }
    const timer = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timer);
  }, [loading]);

  // Re-sorting re-orders the games we already fetched, instantly, with no
  // new request. The backend's sort_order controls WHICH games are analyzed;
  // this only controls display order.
  const sortedResults = useMemo(() => {
    if (!results) return [];
    const arr = [...results.results];
    arr.sort((a, b) => (sortOrder === "earliest" ? a.end_time - b.end_time : b.end_time - a.end_time));
    return arr;
  }, [results, sortOrder]);

  function gamesLimitToast(message) {
    push({ kind: "warning", title: `Up to ${MAX_GAMES} games at a time`, message });
  }

  async function run(rawName) {
    const problem = validateUsername(rawName);
    if (problem) {
      setFieldError(problem);
      inputRef.current?.focus();
      return;
    }
    const name = rawName.trim();

    if (!Number.isInteger(maxGames) || maxGames < 1 || maxGames > MAX_GAMES) {
      gamesLimitToast(
        `Each game gets a full Stockfish review, so the limit is ${MAX_GAMES}. Pick a number from 1 to ${MAX_GAMES}.`
      );
      setMaxGames((n) => Math.min(MAX_GAMES, Math.max(1, Math.round(Number(n)) || 1)));
      return;
    }

    setFieldError(null);
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const data = await analyzeUsername(name, maxGames, sortOrder);
      setResults(data);
      trackEvent("analysis_completed", { games: data.games_analyzed });
    } catch (err) {
      const toast = toastForError(err, name);
      if (toast) push(toast);
      else setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    run(username);
  }

  function handleExample() {
    setUsername(SITE.exampleUsername);
    trackEvent("example_clicked");
    run(SITE.exampleUsername);
  }

  function handleCountChange(e) {
    const raw = e.target.value;
    if (raw === "") return setMaxGames("");
    const n = Number(raw);
    if (n > MAX_GAMES) {
      setMaxGames(MAX_GAMES);
      gamesLimitToast(`Each game gets a full Stockfish review, so the limit is ${MAX_GAMES}. Set the count to ${MAX_GAMES}.`);
    } else {
      setMaxGames(n);
    }
  }

  return (
    <div className="min-h-screen px-4 py-14">
      <div className="mx-auto max-w-2xl">
        <div className="mb-2 flex justify-end">
          <ThemeToggle theme={theme} onChange={onThemeChange} />
        </div>

        <header className="animate-rise-in mb-10 text-center">
          <p className="font-data text-xs uppercase tracking-[0.2em] text-ink/70">Fair Play Analysis</p>
          <h1 className="mt-2 font-display text-5xl font-medium tracking-tight text-ink">ChessGuard</h1>
          <p className="mt-2 font-body text-sm text-ink/70">
            Engine-correlation scoring for Chess.com accounts, move by move.
          </p>
        </header>

        <main>
          <form
            onSubmit={handleSubmit}
            noValidate
            className="flex flex-wrap gap-2 rounded-lg border border-board-dark/20 bg-surface p-2 shadow-sm"
          >
            <label htmlFor="username" className="sr-only">
              Chess.com username
            </label>
            <input
              id="username"
              ref={inputRef}
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (fieldError) setFieldError(null);
              }}
              placeholder="Chess.com username"
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              aria-invalid={fieldError ? "true" : undefined}
              aria-describedby={fieldError ? "username-error" : undefined}
              className="min-w-[10rem] flex-1 rounded-md bg-transparent px-3 py-2 font-body text-sm text-ink
                         placeholder:text-ink/50 outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
            />
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              title="Which games to analyze"
              aria-label="Which games to analyze"
              className="rounded-md border border-board-dark/15 bg-transparent px-2 py-2
                         font-body text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
            >
              <option value="recent">Most recent</option>
              <option value="earliest">Earliest</option>
            </select>
            <input
              type="number"
              inputMode="numeric"
              min={1}
              max={MAX_GAMES}
              value={maxGames}
              onChange={handleCountChange}
              title="Number of games to analyze"
              aria-label="Number of games to analyze"
              className="w-16 rounded-md border border-board-dark/15 bg-transparent px-2 py-2
                         text-center font-data text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-md bg-felt px-5 py-2 font-body text-sm font-medium text-paper
                         transition-colors hover:bg-felt/90 disabled:cursor-not-allowed disabled:opacity-50
                         outline-none focus-visible:ring-2 focus-visible:ring-felt focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            >
              {loading ? "Analyzing…" : "Analyze"}
            </button>
          </form>

          {fieldError && (
            <p id="username-error" role="alert" className="mt-2 px-1 font-body text-sm text-oxblood">
              {fieldError}
            </p>
          )}

          <p className="mb-6 mt-3 px-1 text-center font-body text-xs text-ink/70">
            No account handy?{" "}
            <button
              type="button"
              onClick={handleExample}
              disabled={loading}
              className="font-medium text-ink underline underline-offset-2 hover:text-felt disabled:opacity-50
                         outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
            >
              Try an example
            </button>
          </p>

          {loading && (
            <div className="space-y-4" aria-live="polite">
              <p className="font-body text-sm text-ink/70">
                Running a Stockfish review of each move, which can take a minute.
              </p>
              {slow && (
                <p className="font-body text-sm text-ink/70">
                  Still working. The server runs on free hosting and may be waking up, which can add up to a minute
                  on the first request.
                </p>
              )}
              {[0, 1, 2].map((i) => (
                <div key={i} className="rounded-lg border border-board-dark/15 bg-surface p-6 shadow-sm">
                  <FairPlayBarSkeleton />
                </div>
              ))}
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-oxblood/30 bg-oxblood/[0.06] px-4 py-3 font-body text-sm text-oxblood"
            >
              {error}
            </div>
          )}

          {!loading && !error && !results && (
            <div className="rounded-lg border border-dashed border-board-dark/25 px-6 py-10 text-center">
              <p className="font-body text-sm text-ink/70">
                Enter a Chess.com username above to run a fair-play review of their recent rapid and blitz games.
              </p>
            </div>
          )}

          {results && (
            <div className="space-y-4">
              <p className="font-data text-xs uppercase tracking-wide text-ink/70">
                {results.games_analyzed} game{results.games_analyzed === 1 ? "" : "s"} analyzed
                <span className="mx-2 text-ink/20">&middot;</span>
                {results.username}
              </p>
              {sortedResults.map((game, i) => (
                <GameCard key={`${game.end_time}-${i}`} game={game} style={{ animationDelay: `${i * 80}ms` }} />
              ))}
              <p className="font-body text-xs text-ink/70">
                Scores are statistical estimates, not proof of cheating.
              </p>
            </div>
          )}
        </main>

        <SiteFooter />
      </div>

      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
