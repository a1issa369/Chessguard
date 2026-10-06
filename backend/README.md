# JobHop

A Kanban-style internship/job application tracker with a friend system for
accountability. Cards move through color-coded stages (Wishlist → Applied →
OA/Assessment → Phone Screen → Onsite → Offer, or Rejected/Withdrawn), and
friends can view each other's profile: a GitHub-style activity calendar
(current year only), a Sankey diagram of how applications flow between
stages, an optional resume, and a monthly analytical score.

## Stack

- **Frontend**: React (Vite), Tailwind CSS, `@dnd-kit` for drag-and-drop,
  Chart.js + `chartjs-chart-sankey` for the flow diagram
- **Backend**: Supabase (Postgres, Auth, Storage, Edge Functions)
- **Validation**: zod on the client, `check` constraints in Postgres as a second line of defense

## Sankey flow chart

`src/components/SankeyFlowChart.jsx` visualizes every stage transition a
user's applications have made - not just "12 reached Onsite" like the bar
chart, but exactly which stage each one came from and where the rest
branched off to instead (e.g. straight to Rejected out of Applied, vs.
after a Phone Screen). It reads directly from `stage_history`
(`src/utils/sankeyData.js` aggregates the raw rows into `{from, to, flow}`
edges), and reuses each stage's existing color from `stageConfig.js` so the
diagram stays visually consistent with the Kanban board. It renders on
both the owner's own dashboard and on a friend's profile - the latter only
works once `supabase/migrations/003_stage_history_friend_access.sql` has
been run, since `stage_history` was owner-only until then.

## Setup

1. Create a Supabase project.
2. In the Supabase SQL editor, run `supabase/schema.sql` in full. This creates every
   table, index, RLS policy, and the storage bucket for resumes.
3. Copy `.env.example` to `.env` and fill in your project's URL and anon key.
4. `npm install`
5. `npm run dev`

Optional: deploy `supabase/functions/rate-limiter` as a scheduled Edge Function
to periodically prune the rate-limit log table (`supabase functions deploy
rate-limiter --schedule "0 */6 * * *"`).

## Authentication

Email/password only for now, via Supabase Auth. Signup requires a password
between `MIN_PASSWORD_LENGTH` and `MAX_PASSWORD_LENGTH` characters (8-15,
`src/utils/password.js`) with uppercase, lowercase, and a special character.
"Strong" on the meter means exactly those requirements are met - nothing
hidden - and the account can't be created until it is.

## Account deletion

Deleting an account requires Supabase's service role key, which must never
ship to the browser, so it's handled by an Edge Function instead of a direct
client call:

```
supabase functions deploy delete-account
```

The function verifies the caller's own session token, then deletes that
auth user - which cascades to `profiles`, `applications`, `stage_history`,
and `friendships` automatically via the `on delete cascade` foreign keys
already in the schema. The Settings page (`/settings`) calls this function
after the user types "DELETE" to confirm.

## Rate limiting - what's actually enforced today

- **Server-side, keyed by user (the real boundary for logged-in actions)**:
  `check_rate_limit()` in Postgres, wired into friend requests
  (15/hour/user via `create_friend_request()`). Any other write-heavy RPC
  can call the same function for the same protection.
- **Server-side, keyed by email (covers login/signup)**:
  `check_rate_limit_by_key()` in Postgres. Login and signup happen before a
  session exists, so there's no `auth.uid()` to key off yet - this variant
  keys off the email address being used instead. Signup is capped at
  3/hour/email, login at 5/15min/email. `AuthContext.jsx` calls this before
  ever calling `supabase.auth.signIn`/`signUp`, so a script hitting the auth
  endpoints directly still gets throttled - this is real enforcement, not a
  UI nicety. (Supabase Auth also has its own built-in abuse protection
  underneath this, independent of anything built here.)
- **Client-side (UX only, not security)**: `src/lib/rateLimiter.js` throttles
  the same actions locally in the browser before the request is even sent,
  purely so the UI feels responsive. A direct API call bypasses this layer
  entirely - the two Postgres functions above are what actually can't be
  bypassed.


## Architecture notes / talking points

- **Auth & RLS**: every table is locked down with Postgres Row Level Security.
  Applications are private by default; a narrow additional policy grants
  accepted friends `SELECT` access to `(id, created_at, stage)` only — the
  client only ever queries those columns for a friend's calendar, so
  recruiter contacts and notes never leave the owner's session even though
  the row-level policy technically permits the row.
- **Rate limiting**: enforced server-side via a Postgres function
  (`check_rate_limit`) that every write-heavy RPC calls first — friend
  requests are capped at 15/hour per user regardless of what the client
  does. The client also throttles locally (`src/lib/rateLimiter.js`) purely
  for instant UX feedback; that layer is not the security boundary.
- **Optimistic UI with rollback**: dragging a card across the board updates
  local state immediately, then confirms with the server; a failed write
  reverts the card to its previous column and surfaces an error.
- **Cursor-friendly design**: `created_at`/`user_id` are indexed on every
  table that gets queried by them, so list views stay fast as data grows;
  swap in `.range()` + a `created_at` cursor if lists get long enough to
  need pagination.
- **Defense in depth on input**: zod validates in the browser; Postgres
  `check` constraints validate again at the database boundary, so a bug or
  a direct API call can't insert a 10,000-character company name or an
  invalid stage value.

## Schema overview

- `profiles` — extends `auth.users`, includes `resume_url`
- `applications` — one row per job/internship card
- `stage_history` — one row per stage transition (powers the conversion chart)
- `friendships` — directed request rows with `pending` / `accepted` / `blocked`
- `rate_limit_log` — sliding-window log used by `check_rate_limit()`
- `monthly_scores` (view) — server-side mirror of the score formula in `src/utils/score.js`
