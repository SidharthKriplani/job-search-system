# PLAN — job_feed normalization cutover (ROADMAP "NOW" #3)

_Prepared 2026-07-15. SQL ready in `supabase/migrations/2026-07-16-user-job-matches.sql`._

## The shape of it

`jobs_pool` already IS the canonical deduped jobs table (UNIQUE(source,
source_job_id), written by `upsert_pool_jobs` every run). So this migration is
NOT a rebuild — it adds the thin per-user pointer table and swaps read/write
paths over in stages:

```
today:   job_feed(user × full job row)            ~2,500 rows/user × ~full job
target:  jobs_pool(canonical) ←FK— user_job_matches(user, job_id, score, flags)
```

Storage math: a match row is ~100 bytes vs a ~1KB job_feed row → ~10× headroom
on the same Supabase tier, and resync updates stop rewriting job text entirely.

## Stages (each independently shippable + reversible)

**Stage 0 — run the SQL (safe anytime).**
Run `supabase/migrations/2026-07-16-user-job-matches.sql` in the Supabase SQL
editor. Non-destructive, idempotent: creates `user_job_matches` (+RLS),
backfills from `job_feed`, creates read-compat view `user_feed_v`. job_feed
untouched. Verify: `SELECT count(*) FROM user_job_matches;` ≈ job_feed count.

**Stage 1 — dual-write (python only).**
In `utils/supabase_client.py`: `upsert_jobs()` additionally upserts
(user_id, job_id, score, reasons, flags) into `user_job_matches` by looking up
job_id from the pool keys it already computes; flag updates (save/apply/dismiss
route) write both tables. Feed reads unchanged. Run 2-3 nights; compare counts
in `docs/LAST_RUN.md`. Rollback = remove the extra writes.

**Stage 2 — reads cut over (frontend).**
Point feed/facets reads at `user_feed_v` (same columns as job_feed — table→view
one-word change), including `get_feed_facets` RPC (change its FROM clause).
Saved/apply/dismiss mutations target `user_job_matches` by `id` (the view
exposes the match id as `id`). Deploy to a Vercel preview, click through feed +
filters + tracker, then promote. Rollback = point reads back at job_feed
(dual-write kept both current).

**Stage 3 — stop writing job_feed.**
Remove job_feed writes from `upsert_jobs` / resync / cap_user_feed (cap logic
moves to user_job_matches: keep saved/applied + top-N by score). Keep the table
a few days as archive.

**Stage 4 — drop.**
`DROP TABLE job_feed;` + remove from schema.sql. Then flip
`WORKDAY_INCLUDE_HARVESTED=1` in daily.yml — the +193 harvested Workday
tenants (~25k rows/run) are what this migration buys headroom for.

## Code touchpoints (complete list)

| File | Change |
|---|---|
| `utils/supabase_client.py` | `upsert_jobs` dual-write → then matches-only; flag mutations |
| `main.py` (`resync_user`, `process_user`, `cap_user_feed`) | write/prune against user_job_matches |
| `supabase/schema.sql` | fold the migration in (idempotent) once stable |
| `get_feed_facets` RPC | FROM job_feed → user_feed_v |
| frontend feed API route(s) | table job_feed → view user_feed_v; mutations → user_job_matches |
| `/health`, digest queries | any job_feed reference → user_feed_v |

## Gotchas (found while writing the SQL)

- `upsert_jobs()` falls back to `md5(job_url)` when source_job_id is empty —
  job_feed already stores that effective key, so the backfill join lines up.
  Gmail-parsed jobs (user-specific sources) go into the pool via backfill 2a.
- `user_feed_v` uses `security_invoker = true` so RLS on user_job_matches
  applies to the anon/authenticated client. Verify your Postgres version
  supports it (PG15+; Supabase does).
- `is_new` semantics: today reset by resync; with dual-write, set it in the
  matches upsert exactly as job_feed's (same expression), or digests double-count.
- Closed-job cleanup deletes by pool key — with FK ON DELETE CASCADE, deleting
  a jobs_pool row auto-removes matches. That REPLACES the per-user cleanup loop.

## Why not executed in this session

Needs live Supabase (secrets) + a Vercel preview to click through Stage 2.
Run Stage 0 yourself now (safe); Stages 1-4 are one focused session with the
app in front of you.
