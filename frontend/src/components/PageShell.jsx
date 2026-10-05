import { Link } from "../router";
import ThemeToggle from "./ThemeToggle";
import SiteFooter from "./SiteFooter";

// Shared frame for the legal pages and the 404 page.
export default function PageShell({ theme, onThemeChange, children }) {
  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 flex items-center justify-between">
          <Link
            to="/"
            className="font-body text-sm font-medium text-ink/70 underline-offset-4 hover:text-ink hover:underline"
          >
            &larr; Back to ChessGuard
          </Link>
          <ThemeToggle theme={theme} onChange={onThemeChange} />
        </div>
        <main>{children}</main>
        <SiteFooter />
      </div>
    </div>
  );
}

export function H1({ children }) {
  return <h1 className="font-display text-4xl font-medium tracking-tight text-ink">{children}</h1>;
}
export function H2({ children }) {
  return <h2 className="mt-9 font-display text-xl font-medium text-ink">{children}</h2>;
}
export function P({ children }) {
  return <p className="mt-3 font-body text-sm leading-relaxed text-ink/80">{children}</p>;
}
export function UL({ children }) {
  return <ul className="mt-3 list-disc space-y-1.5 pl-5 font-body text-sm leading-relaxed text-ink/80">{children}</ul>;
}
