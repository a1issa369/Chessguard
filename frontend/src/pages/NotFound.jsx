import PageShell, { H1, P } from "../components/PageShell";
import usePageMeta from "../hooks/usePageMeta";
import { Link } from "../router";

export default function NotFound({ theme, onThemeChange }) {
  usePageMeta("Page not found | ChessGuard", { noindex: true });
  return (
    <PageShell theme={theme} onThemeChange={onThemeChange}>
      <div className="py-10 text-center">
        <p className="font-data text-xs uppercase tracking-[0.2em] text-ink/70">Error 404</p>
        <H1>That square is empty</H1>
        <P>The page you were looking for does not exist or has moved.</P>
        <Link
          to="/"
          className="mt-6 inline-block rounded-md bg-felt px-5 py-2 font-body text-sm font-medium text-paper
                     hover:bg-felt/90 outline-none focus-visible:ring-2 focus-visible:ring-felt focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
        >
          Back to ChessGuard
        </Link>
      </div>
    </PageShell>
  );
}
