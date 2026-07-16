-- ============================================================================
-- DATA FLYWHEELS — skills corpus + repost fingerprints
-- Idempotent, non-destructive. Run once in the Supabase SQL editor, then set
-- INGEST_SKILLS=1 in the daily workflow env (already wired).
--
-- Longitudinal data starts accruing the day this ships — repost rates, skill
-- density, and posting-lifetime stats all read from these tables later.
-- ============================================================================

-- 1) Skills corpus (extracted from FULL JDs at ingest, before snippet trim)
ALTER TABLE jobs_pool ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]';
CREATE INDEX IF NOT EXISTS idx_jobs_pool_skills ON jobs_pool USING GIN (skills);

-- 2) Job fingerprints — one row per (company × normalized title × city).
--    Tracks how often the "same job" appears, disappears, and REAPPEARS
--    (repost = reappearance after a gap; churn/ghost-job signal).
CREATE TABLE IF NOT EXISTS job_fingerprints (
    fingerprint     TEXT PRIMARY KEY,          -- md5(company|title_norm|city)
    company         TEXT NOT NULL,
    title_norm      TEXT NOT NULL,
    location_city   TEXT,
    position        TEXT,                       -- canonical role bucket
    first_seen_at   TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ DEFAULT NOW(),
    times_seen      INT  DEFAULT 1,             -- distinct nights observed
    reappearances   INT  DEFAULT 0,             -- returns after >GAP_DAYS absence
    last_gap_days   INT,                        -- length of the latest absence
    open_days       INT  DEFAULT 0              -- cumulative days observed open
);
CREATE INDEX IF NOT EXISTS idx_fp_company   ON job_fingerprints(company);
CREATE INDEX IF NOT EXISTS idx_fp_position  ON job_fingerprints(position);
CREATE INDEX IF NOT EXISTS idx_fp_reposts   ON job_fingerprints(reappearances) WHERE reappearances > 0;

ALTER TABLE job_fingerprints ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "fingerprints readable" ON job_fingerprints;
CREATE POLICY "fingerprints readable" ON job_fingerprints FOR SELECT TO authenticated USING (true);
-- writes come from the service-role key (bypasses RLS)

-- Sanity after a few nights:
--   SELECT count(*) FROM job_fingerprints;
--   SELECT company, title_norm, reappearances, last_gap_days
--   FROM job_fingerprints WHERE reappearances > 0 ORDER BY reappearances DESC LIMIT 20;
