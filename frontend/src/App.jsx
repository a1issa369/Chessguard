import { useState } from "react";
import { analyzeUsername } from "./api";
import GameCard from "./components/GameCard";
import { FairPlayBarSkeleton } from "./components/FairPlayBar";

export default function App() {
  const [username, setUsername] = useState("");
  const [maxGames, setMaxGames] = useState(3);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim()) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const data = await analyzeUsername(username.trim(), maxGames);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-14">
      <div className="mx-auto max-w-2xl">
        <header className="animate-rise-in mb-10 text-center">
          <p className="font-data text-xs uppercase tracking-[0.2em] text-ink/70">
            Fair-Play Analysis
          </p>
          <h1 className="mt-2 font-display text-5xl font-medium tracking-tight text-ink">
            ChessGuard
          </h1>
          <p className="mt-2 font-body text-sm text-ink/70">
            Engine-correlation scoring for Chess.com accounts, move by move.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="mb-10 flex gap-2 rounded-lg border border-board-dark/20 bg-white/60 p-2 shadow-sm"
        >
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Chess.com username"
            className="flex-1 rounded-md bg-transparent px-3 py-2 font-body text-sm text-ink
                       placeholder:text-ink/50 outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
          />
          <input
            type="number"
            min={1}
            max={10}
            value={maxGames}
            onChange={(e) => setMaxGames(Number(e.target.value))}
            title="Number of recent games to analyze"
            className="w-16 rounded-md border border-board-dark/15 bg-transparent px-2 py-2
                       text-center font-data text-sm text-ink outline-none focus-visible:ring-2 focus-visible:ring-felt/50"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-felt px-5 py-2 font-body text-sm font-medium text-paper
                       transition-colors hover:bg-felt/90 disabled:cursor-not-allowed disabled:opacity-50
                       outline-none focus-visible:ring-2 focus-visible:ring-felt focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </form>

        {loading && (
          <div className="space-y-4">
            <p className="font-body text-sm text-ink/70">
              Running a Stockfish review of each move — this can take a minute.
            </p>
            {[0, 1, 2].map((i) => (
              <div key={i} className="rounded-lg border border-board-dark/15 bg-white/60 p-6 shadow-sm">
                <FairPlayBarSkeleton />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-oxblood/30 bg-oxblood/[0.06] px-4 py-3 font-body text-sm text-oxblood">
            Couldn&rsquo;t analyze &ldquo;{username}&rdquo;: {error}
          </div>
        )}

        {!loading && !error && !results && (
          <div className="rounded-lg border border-dashed border-board-dark/25 px-6 py-10 text-center">
            <p className="font-body text-sm text-ink/70">
              Enter a Chess.com username above to run a fair-play review of
              their recent rapid/blitz games.
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
            {results.results.map((game, i) => (
              <GameCard key={i} game={game} style={{ animationDelay: `${i * 80}ms` }} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
