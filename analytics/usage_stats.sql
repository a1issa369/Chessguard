-- Run any of these in the Supabase SQL editor. All of them exclude your own
-- testing (is_owner). Delete any stray test rows by hand if needed:
--   delete from usage_events where created_at < '2026-10-06';

-- 1. Headline numbers
select
  count(*)                                                         as requests,
  count(*) filter (where outcome = 'ok')                           as successful_requests,
  coalesce(sum(games_analyzed) filter (where outcome = 'ok'), 0)   as games_reviewed,
  coalesce(sum(games_analyzed) filter (where outcome = 'ok' and not cache_hit), 0)
                                                                   as games_run_through_stockfish,
  round(100.0 * count(*) filter (where cache_hit)
        / nullif(count(*) filter (where outcome = 'ok'), 0), 1)    as cache_hit_pct,
  count(*) filter (where is_example)                               as example_requests,
  round(100.0 * count(*) filter (where outcome not in ('ok', 'TOO_MANY_GAMES', 'RATE_LIMITED', 'BUSY', 'USER_NOT_FOUND', 'NO_GAMES', 'NO_USABLE_GAMES'))
        / nullif(count(*), 0), 1)                                  as server_error_pct
from usage_events
where not is_owner;

-- 2. Speed: seconds per game for fresh (not cached) analyses
select
  count(*)                                                         as fresh_requests,
  round((percentile_cont(0.5) within group (order by duration_ms::numeric / games_analyzed) / 1000)::numeric, 1)
                                                                   as median_seconds_per_game,
  round((percentile_cont(0.95) within group (order by duration_ms::numeric / games_analyzed) / 1000)::numeric, 1)
                                                                   as p95_seconds_per_game
from usage_events
where not is_owner and outcome = 'ok' and not cache_hit and games_analyzed > 0;

-- 3. Outcomes, including error rates
select outcome, count(*) as n,
       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from usage_events
where not is_owner
group by outcome
order by n desc;

-- 4. Requests per day
select date_trunc('day', created_at at time zone 'America/Los_Angeles')::date as day,
       count(*) as requests,
       coalesce(sum(games_analyzed) filter (where outcome = 'ok'), 0) as games_reviewed
from usage_events
where not is_owner
group by 1
order by 1 desc;
