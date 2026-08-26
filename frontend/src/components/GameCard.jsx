import FairPlayBar from "./FairPlayBar";

const REVIEW_THRESHOLD = 0.4;
const FLAG_THRESHOLD = 0.75;

function verdict(cheatProbability) {
  // Where these lines sit is a policy choice, not a model output --
  // logistic regression gives a continuous probability; deciding what
  // counts as "worth a human look" trades false accusations against
  // missed cheaters (see the precision/recall discussion in the project
  // write-up).
  if (cheatProbability >= FLAG_THRESHOLD) {
    return { label: "High Risk", fg: "text-oxblood", border: "border-oxblood/30", bg: "bg-oxblood/[0.06]" };
  }
  if (cheatProbability >= REVIEW_THRESHOLD) {
    return { label: "Worth Reviewing", fg: "text-brass-ink", border: "border-brass/30", bg: "bg-brass/[0.08]" };
  }
  return { label: "Clean", fg: "text-felt", border: "border-felt/30", bg: "bg-felt/[0.06]" };
}

function formatTimestamp(unixSeconds) {
  if (!unixSeconds) return "Unknown date";
  return new Date(unixSeconds * 1000)
    .toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    .toUpperCase();
}

const FEATURES = [
  { key: "top1_match_rate", label: "Engine match rate", unit: "%" },
  { key: "avg_centipawn_loss", label: "Avg. centipawn loss", unit: "" },
  { key: "max_window_match_rate", label: "Peak 10-move match", unit: "%" },
  { key: "min_window_avg_cp_loss", label: "Best 10-move stretch", unit: "" },
  { key: "perfect_move_frac", label: "Near-perfect move share", unit: "" },
  { key: "longest_perfect_streak", label: "Longest perfect streak", unit: "" },
];

export default function GameCard({ game, style }) {
  const v = verdict(game.cheat_probability);
  const percent = Math.round(game.cheat_probability * 100);

  return (
    <div
      className="animate-rise-in rounded-lg border border-board-dark/15 bg-surface p-6 shadow-sm"
      style={style}
    >
      <div className="mb-3 flex items-center justify-between gap-4">
        <p className="font-body text-sm font-medium text-ink">
          {game.player}
          <span className="mx-1.5 font-data text-xs text-ink/50">vs</span>
          {game.opponent}
        </p>
        <span
          className={`shrink-0 rounded-full border px-3 py-1 font-body text-xs font-semibold uppercase tracking-wide ${v.fg} ${v.border} ${v.bg}`}
        >
          {v.label} &middot; {percent}%
        </span>
      </div>

      <div className="mb-4 border-b border-board-dark/10 pb-4 font-data text-[11px] uppercase tracking-wide text-ink/70">
        {formatTimestamp(game.end_time)}
        <span className="mx-2 text-ink/20">&middot;</span>
        {game.time_control ?? "unknown tc"}
        <span className="mx-2 text-ink/20">&middot;</span>
        {game.moves_analyzed} moves
      </div>

      <FairPlayBar probability={game.cheat_probability} />

      <dl className="mt-5 grid grid-cols-2 gap-x-8 gap-y-2.5">
        {FEATURES.map(({ key, label, unit }) => (
          <div key={key} className="flex items-baseline justify-between gap-2">
            <dt className="font-body text-xs text-ink/70">{label}</dt>
            <dd className="font-data text-sm text-ink">
              {game.features[key]}
              {unit}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
