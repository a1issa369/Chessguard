import PageShell, { H1, H2, P, UL } from "../components/PageShell";
import usePageMeta from "../hooks/usePageMeta";
import { SITE } from "../config";

export default function Terms({ theme, onThemeChange }) {
  usePageMeta("Terms of Service | ChessGuard");
  return (
    <PageShell theme={theme} onThemeChange={onThemeChange}>
      <article>
        <H1>Terms of Service</H1>
        <P>Last updated {SITE.policiesUpdated}.</P>
        <P>
          By using ChessGuard you agree to these terms. If you do not agree, please do not
          use the site.
        </P>

        <H2>About this project</H2>
        <P>
          ChessGuard is a student project by {SITE.author}, made for education and
          portfolio purposes. It is not a commercial service. It is not endorsed by,
          affiliated with, or sponsored by Chess.com or any other third party, and all
          trademarks belong to their owners.
        </P>

        <H2>Results are estimates, not accusations</H2>
        <P>
          ChessGuard compares a player&rsquo;s moves with a chess engine and produces a
          statistical estimate. High engine agreement can happen for honest reasons, such as
          well-known opening theory, forced positions, or a very strong player having a
          good day. A score is not proof that anyone cheated, and it is far from a verdict.
        </P>
        <P>
          Only Chess.com&rsquo;s own fair play team can make decisions about an account. If
          you suspect cheating, report it to them directly.
        </P>

        <H2>Acceptable use</H2>
        <UL>
          <li>Do not use ChessGuard to harass, shame, or publicly accuse any player.</li>
          <li>Do not send automated or high-volume traffic. The server enforces request limits to stay available for everyone.</li>
          <li>Do not attempt to disrupt, overload, or probe the service for weaknesses.</li>
        </UL>

        <H2>Third-party data</H2>
        <P>
          Game data comes from Chess.com&rsquo;s public API. Its availability, accuracy, and
          terms are outside this project&rsquo;s control.
        </P>

        <H2>No warranty</H2>
        <P>
          The site is provided &ldquo;as is&rdquo;, without warranties of any kind. It runs
          on free hosting, so it may be slow to start, change, or go offline at any time
          without notice.
        </P>

        <H2>Limitation of liability</H2>
        <P>
          To the extent permitted by law, the author is not liable for any loss or damage
          arising from your use of the site or from decisions made using its results.
        </P>

        <H2>Changes and contact</H2>
        <P>
          These terms may be updated, and the date above will change when they are. Questions can
          go to{" "}
          <a className="underline underline-offset-2 hover:text-ink" href={`mailto:${SITE.contactEmail}`}>
            {SITE.contactEmail}
          </a>
          .
        </P>
      </article>
    </PageShell>
  );
}
