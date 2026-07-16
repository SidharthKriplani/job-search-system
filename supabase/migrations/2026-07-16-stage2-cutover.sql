-- ============================================================================
-- NORMALIZATION STAGE 2 — reads cut over to user_feed_v / user_job_matches.
-- Run ONCE, right before deploying the feed-v2 frontend (preview or prod).
-- Idempotent. Prereq: 2026-07-16-user-job-matches.sql already ran.
-- ============================================================================

-- 1) Bring user flags current AS OF NOW (the prod UI kept writing them to
--    job_feed during the dual-write window; matches carried scores only).
UPDATE user_job_matches m
SET is_new       = COALESCE(f.is_new, m.is_new),
    is_applied   = COALESCE(f.is_applied, m.is_applied),
    is_saved     = COALESCE(f.is_saved, m.is_saved),
    is_dismissed = COALESCE(f.is_dismissed, m.is_dismissed),
    updated_at   = NOW()
FROM job_feed f
JOIN jobs_pool p ON p.source = f.source AND p.source_job_id = f.source_job_id
WHERE m.user_id = f.user_id AND m.job_id = p.id;

-- 2) get_feed_facets now reads the view (same shape; RLS via security_invoker
--    on the view scopes rows to the caller).
CREATE OR REPLACE FUNCTION get_feed_facets(p_user UUID, p_min_score FLOAT DEFAULT 0.45)
RETURNS JSONB
LANGUAGE sql STABLE SECURITY INVOKER AS $$
  WITH f AS (
    SELECT source, company, position, location_city
    FROM user_feed_v
    WHERE user_id = p_user AND is_dismissed = FALSE AND is_applied = FALSE
      AND COALESCE(match_score, 0) >= p_min_score
  )
  SELECT jsonb_build_object(
    'boards', COALESCE((SELECT jsonb_agg(jsonb_build_object('value', v, 'count', c) ORDER BY c DESC)
                        FROM (SELECT source v, count(*) c FROM f WHERE source IS NOT NULL GROUP BY source) a), '[]'::jsonb),
    'positions', COALESCE((SELECT jsonb_agg(jsonb_build_object('value', v, 'count', c) ORDER BY c DESC)
                        FROM (SELECT position v, count(*) c FROM f WHERE position IS NOT NULL GROUP BY position) b), '[]'::jsonb),
    'locations', COALESCE((SELECT jsonb_agg(jsonb_build_object('value', v, 'count', c) ORDER BY c DESC)
                        FROM (SELECT location_city v, count(*) c FROM f WHERE location_city IS NOT NULL GROUP BY location_city) d), '[]'::jsonb),
    'companies', COALESCE((SELECT jsonb_agg(jsonb_build_object('value', v, 'count', c) ORDER BY c DESC)
                        FROM (SELECT company v, count(*) c FROM f WHERE company IS NOT NULL AND company <> '' GROUP BY company ORDER BY count(*) DESC LIMIT 60) e), '[]'::jsonb)
  );
$$;
GRANT EXECUTE ON FUNCTION get_feed_facets(UUID, FLOAT) TO authenticated;

-- 3) applications.job_feed_id now stores a user_job_matches id (the feed's
--    row id after cutover). Drop the FK to job_feed — the column becomes a
--    plain UUID pointer (existing values stay valid as historical references).
DO $$
DECLARE c RECORD;
BEGIN
  FOR c IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'applications'::regclass
      AND confrelid = 'job_feed'::regclass
  LOOP
    EXECUTE format('ALTER TABLE applications DROP CONSTRAINT %I', c.conname);
  END LOOP;
END $$;

-- 4) The view exposes user-flag columns from user_job_matches; make sure the
--    authenticated role can UPDATE those flags (RLS policies from the first
--    migration already scope to own rows).
GRANT SELECT ON user_feed_v TO authenticated;
GRANT UPDATE (is_new, is_applied, is_saved, is_dismissed, updated_at)
  ON user_job_matches TO authenticated;

-- Sanity:
--   SELECT count(*) FROM user_feed_v;                         -- ≈ job_feed active count
--   SELECT get_feed_facets('<your-uuid>');                     -- returns jsonb

-- 5) CRITICAL (added after prod incident 2026-07-16): user_feed_v runs
--    security_invoker, so the authenticated role must be able to SELECT from
--    BOTH sides of the join. user_job_matches had a policy; jobs_pool only had
--    the service-role policy -> the join returned 0 rows -> empty feed.
DROP POLICY IF EXISTS "pool readable" ON jobs_pool;
CREATE POLICY "pool readable" ON jobs_pool FOR SELECT TO authenticated USING (true);
