import PageShell, { H1, H2, P, UL } from "../components/PageShell";
import usePageMeta from "../hooks/usePageMeta";
import { SITE } from "../config";

export default function Privacy({ theme, onThemeChange }) {
  usePageMeta("Privacy Policy | ChessGuard");
  return (
    <PageShell theme={theme} onThemeChange={onThemeChange}>
      <article>
        <H1>Privacy Policy</H1>
        <P>Last updated {SITE.policiesUpdated}.</P>
        <P>
          ChessGuard is a student project by {SITE.author}, built for learning and as a
          portfolio piece. This page explains, in plain language, what the site does with
          your information.
        </P>

        <H2>The short version</H2>
        <UL>
          <li>There are no accounts, no sign-up, and no ads.</li>
          <li>The only thing you give the site is a Chess.com username that you type in.</li>
          <li>The site counts anonymous page views, with no cookies and no personal profiles, so the author can see roughly how many people use it.</li>
          <li>The server keeps an anonymous usage log (counts, timing and outcomes) that contains no usernames and no IP addresses.</li>
          <li>Nothing you enter is sold or shared for marketing.</li>
        </UL>

        <H2>What happens when you analyze an account</H2>
        <P>
          The username and options you enter (number of games, sort order) are sent to the
          ChessGuard server. The server asks the public Chess.com API for that player&rsquo;s
          recent games, reviews each game with a chess engine, and sends the results back
          to your browser. Because the request comes from our server, Chess.com sees the
          server&rsquo;s address, not yours.
        </P>
        <P>
          Results are kept in the server&rsquo;s memory for about ten minutes so that a
          repeated request is fast, then discarded. The results themselves are not written
          to a database. Game data comes from Chess.com&rsquo;s public API and describes
          publicly visible games.
        </P>

        <H2>Analytics</H2>
        <P>
          The site uses Vercel Web Analytics to count page views. It reports aggregate
          information such as the page visited, the referring site, browser, device type,
          and country. It is designed to work without cookies and without following you
          across other websites. Only the site&rsquo;s author can see these numbers, and they
          are used to understand how the project is used. The ChessGuard server does not
          log or store the usernames you enter beyond the short-lived cache described above.
        </P>

        <H2>Usage statistics</H2>
        <P>
          Each time an analysis is requested, the server saves one anonymous record in a
          database so the author can measure how the project performs. A record contains
          only: the time, how many games were requested and analyzed, whether the answer
          came from the cache, how long it took, and whether it succeeded or which kind of
          error occurred. It does not contain the username you entered, your IP address, or
          the results. Only the site&rsquo;s author can read these records.
        </P>

        <H2>Cookies and local storage</H2>
        <P>ChessGuard does not set cookies. It stores one small value in your browser&rsquo;s local storage:</P>
        <UL>
          <li>
            <code>chessguard-theme</code>: whether you chose day or night mode.
          </li>
        </UL>
        <P>These stay on your device. You can delete them any time by clearing your site data.</P>

        <H2>Third parties</H2>
        <UL>
          <li>
            <strong>Chess.com</strong> provides the public game data, as described above.
          </li>
          <li>
            <strong>Google Fonts</strong> serves the site&rsquo;s typefaces. Your browser requests
            the font files directly from Google, so Google receives your IP address and
            browser details under its own privacy policy.
          </li>
          <li>
            <strong>Supabase</strong> stores the anonymous usage records described above.
          </li>
          <li>
            <strong>Vercel</strong> hosts the website and <strong>Render</strong> hosts the analysis
            server. Like most hosts, they may keep standard request logs (such as IP address and
            timestamps) under their own policies.
          </li>
        </UL>

        <H2>Children</H2>
        <P>ChessGuard is not directed at children under 13, and it does not knowingly collect personal information from them.</P>

        <H2>Your choices and contact</H2>
        <P>
          Because the site keeps no accounts or stored profiles, there is nothing to download
          or delete on our side beyond the short-lived memory cache and the anonymous usage records,
          which cannot be traced back to you. For any question about
          this policy, email{" "}
          <a className="underline underline-offset-2 hover:text-ink" href={`mailto:${SITE.contactEmail}`}>
            {SITE.contactEmail}
          </a>
          .
        </P>

        <H2>Changes</H2>
        <P>If this policy changes, the date at the top will change with it.</P>
      </article>
    </PageShell>
  );
}
