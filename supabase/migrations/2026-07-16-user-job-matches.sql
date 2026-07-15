-- ============================================================================
-- NORMALIZATION MIGRATION — phase 1 of the job_feed split (ROADMAP "NOW" #3)
--
-- Insight: jobs_pool ALREADY IS the canonical deduped jobs table
-- (UNIQUE(source, source_job_id), maintained by upsert_pool_jobs each run).
-- So normalization = add the thin per-user pointer table and cut reads over.
--
--   job_feed  (user_id × full job row, ~2500/user)          -- today
--   jobs_pool (canonical) + user_job_matches (thin pointers) -- target
--
-- THIS FILE IS NON-DESTRUCTIVE AND IDEMPOTENT:
--   * creates user_job_matches (+ indexes + RLS)
--   * backfills it from existing job_feed rows (ON CONFLICT DO NOTHING)
--   * creates a read-compat view user_feed_v that looks like job_feed
--   * does NOT drop or stop writing job_feed — cutover is a code change,
--     staged per docs/PLAN-normalization.md. Run this any number of times.
-- ============================================================================

-- 1) The thin pointer table ---------------------------------------------------
CREATE TABLE IF NOT EXISTS user_job_matches (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id        UUID NOT NULL REFERENCES jobs_pool(id)  ON DELETE CASCADE,

    -- per-user state (everything user-specific lives HERE, nothing job-specific)
    match_score   FLOAT DEFAULT 0,
    match_reasons JSONB DEFAULT '[]',
    is_new        BOOLEAN NOT NULL DEFAULT TRUE,
    is_applied    BOOLEAN NOT NULL DEFAULT FALSE,
    is_saved      BOOLEAN NOT NULL DEFAULT FALSE,
    is_dismissed  BOOLEAN NOT NULL DEFAULT FALSE,

    matched_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_ujm_user            ON user_job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_ujm_user_score      ON user_job_matches(user_id, match_score DESC);
CREATE INDEX IF NOT EXISTS idx_ujm_job             ON user_job_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_ujm_new             ON user_job_matches(user_id) WHERE is_new = TRUE;

ALTER TABLE user_job_matches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users read own matches"    ON user_job_matches;
DROP POLICY IF EXISTS "Users update own matches"  ON user_job_matches;
DROP POLICY IF EXISTS "Users insert own matches"  ON user_job_matches;
DROP POLICY IF EXISTS "Users delete own matches"  ON user_job_matches;
CREATE POLICY "Users read own matches"
    ON user_job_matches FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own matches"
    ON user_job_matches FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users insert own matches"
    ON user_job_matches FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users delete own matches"
    ON user_job_matches FOR DELETE USING (auth.uid() = user_id);
-- scraper uses service-role key → bypasses RLS, unaffected.

-- 2) Backfill from job_feed ---------------------------------------------------
-- 2a. Jobs that exist in a user's feed but not in jobs_pool (old rows from
--     before the pool existed, gmail-parsed jobs, etc.) → add to the pool.
--     NOTE: upsert_jobs() falls back to md5(job_url) when source_job_id is
--     empty; job_feed rows already store that effective key, so the join on
--     (source, source_job_id) lines up.
INSERT INTO jobs_pool (source, source_job_id, job_title, company, location,
                       salary_range, job_url, description_snippet, posted_date,
                       job_type, seniority, source_domain, position, location_city)
SELECT DISTINCT ON (f.source, f.source_job_id)
       f.source, f.source_job_id, f.job_title, COALESCE(f.company, ''), f.location,
       f.salary_range, f.job_url, f.description_snippet, f.posted_date,
       f.job_type, f.seniority, f.source_domain, f.position, f.location_city
FROM job_feed f
WHERE f.source_job_id IS NOT NULL AND f.source_job_id <> ''
ON CONFLICT (source, source_job_id) DO NOTHING;

-- 2b. Pointer rows for every (user, job) pair currently in job_feed.
INSERT INTO user_job_matches (user_id, job_id, match_score, match_reasons,
                              is_new, is_applied, is_saved, is_dismissed, matched_at)
SELECT f.user_id, p.id, f.match_score, f.match_reasons,
       COALESCE(f.is_new, TRUE), COALESCE(f.is_applied, FALSE),
       COALESCE(f.is_saved, FALSE), COALESCE(f.is_dismissed, FALSE),
       f.scraped_at
FROM job_feed f
JOIN jobs_pool p ON p.source = f.source AND p.source_job_id = f.source_job_id
ON CONFLICT (user_id, job_id) DO NOTHING;

-- 3) Read-compat view ----------------------------------------------------------
-- Looks like job_feed (same columns) so read paths can switch with a one-word
-- table→view change while writes still dual-target during the staged cutover.
CREATE OR REPLACE VIEW user_feed_v AS
SELECT m.id,
       m.user_id,
       p.job_title, p.company, p.location, p.salary_range, p.job_url,
       p.description_snippet, p.posted_date, p.source, p.source_job_id,
       p.job_type, NULL::TEXT AS experience_required, p.seniority,
       p.source_domain, p.position, p.location_city,
       m.is_new, m.is_applied, m.is_saved, m.is_dismissed,
       m.match_score, m.match_reasons,
       m.matched_at AS scraped_at, m.matched_at AS created_at
FROM user_job_matches m
JOIN jobs_pool p ON p.id = m.job_id;

-- Views run with the invoker's rights here; RLS on user_job_matches scopes
-- rows to auth.uid() automatically for anon/authenticated clients.
ALTER VIEW user_feed_v SET (security_invoker = true);

-- 4) Sanity checks (run manually, expect both counts to be close; the gap =
--    job_feed rows whose (source, source_job_id) no longer exists in the pool):
--   SELECT count(*) FROM job_feed;
--   SELECT count(*) FROM user_job_matches;
--   SELECT count(*) FROM user_feed_v WHERE user_id = '<your-uuid>';
