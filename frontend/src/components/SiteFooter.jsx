import { Link } from "../router";
import { SITE } from "../config";

const pill =
  "rounded-full border border-board-dark/25 px-4 py-1.5 font-body text-xs font-medium text-ink " +
  "transition-colors hover:bg-board-dark/5 outline-none focus-visible:ring-2 focus-visible:ring-felt/50";

export default function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-board-dark/10 pt-6 pb-24 text-center">
      <p className="mx-auto max-w-lg font-body text-xs leading-relaxed text-ink/70">
        ChessGuard is a student project built by {SITE.author} for learning and portfolio
        purposes. It is not endorsed by, affiliated with, or sponsored by Chess.com or any
        other third party.
      </p>
      <p className="mt-3 font-data text-[11px] uppercase tracking-wide text-ink/70">
        React &middot; Tailwind &middot; FastAPI &middot; scikit-learn &middot; Stockfish
      </p>
      <nav aria-label="Legal and links" className="mt-5 flex flex-wrap items-center justify-center gap-2">
        <Link to="/privacy" className={pill}>
          Privacy Policy
        </Link>
        <Link to="/terms" className={pill}>
          Terms of Service
        </Link>
        <a href={SITE.github} target="_blank" rel="noopener noreferrer" className={pill}>
          Source on GitHub
        </a>
      </nav>
    </footer>
  );
}
