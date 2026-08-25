import { useEffect, useState } from "react";

// Thresholds mirror the exact decision boundaries the model/UI uses to
// bucket a score into Clean / Worth Reviewing / High Risk (see verdict()
// in GameCard.jsx). Drawing them as literal tick marks on the bar means
// this structural detail encodes something real about how the system
// decides, not just decoration.
const REVIEW_THRESHOLD = 0.4;
const FLAG_THRESHOLD = 0.75;

function verdictColor(p) {
  if (p >= FLAG_THRESHOLD) return "var(--color-oxblood)";
  if (p >= REVIEW_THRESHOLD) return "var(--color-brass)";
  return "var(--color-felt)";
}

export default function FairPlayBar({ probability }) {
  // Animate the fill in on mount rather than snapping straight to its
  // final width -- one deliberate motion moment, not scattered effects.
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const id = requestAnimationFrame(() => setWidth(probability * 100));
    return () => cancelAnimationFrame(id);
  }, [probability]);

  return (
    <div className="w-full">
      <div className="mb-1.5 flex justify-between font-data text-[10px] uppercase tracking-widest text-ink/40">
        <span>Human</span>
        <span>Engine</span>
      </div>

      <div className="relative h-2.5 rounded-full bg-board-light">
        {/* Decision-boundary ticks -- real thresholds, not ornament */}
        <div
          className="absolute top-0 h-full w-px bg-board-dark/25"
          style={{ left: `${REVIEW_THRESHOLD * 100}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-board-dark/25"
          style={{ left: `${FLAG_THRESHOLD * 100}%` }}
        />

        <div
          className="h-full rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${width}%`, backgroundColor: verdictColor(probability) }}
        />

        {/* Marker */}
        <div
          className="absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 -translate-x-1/2 rounded-full
                     border-2 border-paper shadow-sm transition-[left] duration-700 ease-out"
          style={{ left: `${width}%`, backgroundColor: verdictColor(probability) }}
        />
      </div>
    </div>
  );
}

export function FairPlayBarSkeleton() {
  return (
    <div className="w-full">
      <div className="mb-1.5 flex justify-between font-data text-[10px] uppercase tracking-widest text-ink/20">
        <span>Human</span>
        <span>Engine</span>
      </div>
      <div className="h-2.5 animate-pulse rounded-full bg-board-light" />
    </div>
  );
}
