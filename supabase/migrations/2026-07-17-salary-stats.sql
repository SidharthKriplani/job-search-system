-- ============================================================================
-- SALARY STATS — CTC-to-ask heuristic. Aggregated nightly by
-- scripts/salary_stats.py from jobs_pool.salary_range (parsed to LPA).
-- location_city = '' is the all-city rollup per position. Idempotent.
-- ============================================================================

CREATE TABLE IF NOT EXISTS salary_stats (
  position       TEXT NOT NULL,
  location_city  TEXT NOT NULL DEFAULT '',   -- '' = all cities
  n              INT  NOT NULL,              -- sample size (priced postings)
  p25            FLOAT NOT NULL,             -- LPA
  p50            FLOAT NOT NULL,
  p75            FLOAT NOT NULL,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (position, location_city)
);

ALTER TABLE salary_stats ENABLE ROW LEVEL SECURITY;

-- Market-wide aggregates: readable by every signed-in user; only the pipeline
-- (service role) writes. Same policy shape as jobs_pool.
DROP POLICY IF EXISTS "salary stats readable" ON salary_stats;
CREATE POLICY "salary stats readable" ON salary_stats
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "Service role manages salary stats" ON salary_stats;
CREATE POLICY "Service role manages salary stats" ON salary_stats
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

GRANT SELECT ON salary_stats TO authenticated;
