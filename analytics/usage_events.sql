-- Run once in the Supabase SQL editor (Project > SQL Editor > New query).
-- Stores one anonymous row per analysis request: no usernames, no IPs.

create table if not exists public.usage_events (
  id               bigint generated always as identity primary key,
  created_at       timestamptz not null default now(),
  outcome          text        not null,             -- 'ok' or an error code
  games_requested  int         not null,
  games_analyzed   int         not null default 0,
  cache_hit        boolean     not null default false,
  duration_ms      int         not null,
  is_example       boolean     not null default false,
  is_owner         boolean     not null default false
);

create index if not exists usage_events_created_at_idx
  on public.usage_events (created_at);

-- Lock the table down. With RLS on and NO policies, the public (anon) key can
-- neither read nor write it. Only the server's secret key can, because the
-- secret key bypasses RLS. This is what keeps the data private.
alter table public.usage_events enable row level security;
