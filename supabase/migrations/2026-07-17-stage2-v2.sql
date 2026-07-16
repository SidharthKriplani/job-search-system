-- ============================================================================
-- STAGE 2 v2 — reads via SECURITY DEFINER functions (measured: 24 ms vs the
-- view's 4,687 ms). Run ONCE right before deploying the feed-v2b branch.
-- Idempotent. Requires: user-job-matches + stage2-cutover migrations already ran.
-- ============================================================================

-- 0) Re-sync user flags from job_feed (prod wrote flags there during the
--    revert window). Same statement as stage2; safe to repeat.
UPDATE user_job_matches m
SET is_new       = COALESCE(f.is_new, m.is_new),
    is_applied   = COALESCE(f.is_applied, m.is_applied),
    is_saved     = COALESCE(f.is_saved, m.is_saved),
    is_dismissed = COALESCE(f.is_dismissed, m.is_dismissed),
    updated_at   = NOW()
FROM job_feed f
JOIN jobs_pool p ON p.source = f.source AND p.source_job_id = f.source_job_id
WHERE m.user_id = f.user_id AND m.job_id = p.id;

-- 1) Filtered, sorted, paginated feed page. SECURITY DEFINER: bypasses the
--    RLS+view planner trap; the user is hard-bound via auth.uid() inside.
CREATE OR REPLACE FUNCTION get_user_feed_page(
  p_q          TEXT    DEFAULT '',
  p_scope      TEXT    DEFAULT 'all',      -- all | new | saved
  p_boards     TEXT[]  DEFAULT '{}',
  p_positions  TEXT[]  DEFAULT '{}',
  p_companies  TEXT[]  DEFAULT '{}',
  p_locations  TEXT[]  DEFAULT '{}',
  p_min_score  FLOAT   DEFAULT 0,          -- 0 = no floor (narrowed views)
  p_sort       TEXT    DEFAULT 'relevance',-- relevance | date | added
  p_limit      INT     DEFAULT 50,
  p_offset     INT     DEFAULT 0
)
RETURNS SETOF user_feed_v
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
DECLARE
  uid UUID := auth.uid();
BEGIN
  IF uid IS NULL THEN RETURN; END IF;
  RETURN QUERY
  SELECT m.id, m.user_id,
         p.job_title, p.company, p.location, p.salary_range, p.job_url,
         p.description_snippet, p.posted_date, p.source, p.source_job_id,
         p.job_type, NULL::TEXT, p.seniority,
         p.source_domain, p.position, p.location_city,
         m.is_new, m.is_applied, m.is_saved, m.is_dismissed,
         m.match_score, m.match_reasons,
         m.matched_at, m.matched_at
  FROM user_job_matches m
  JOIN jobs_pool p ON p.id = m.job_id
  WHERE m.user_id = uid
    AND m.is_dismissed = FALSE AND m.is_applied = FALSE
    AND (p_scope <> 'new'   OR m.is_new   = TRUE)
    AND (p_scope <> 'saved' OR m.is_saved = TRUE)
    AND (p_min_score <= 0 OR m.match_score >= p_min_score)
    AND (cardinality(p_boards)    = 0 OR p.source        = ANY(p_boards))
    AND (cardinality(p_positions) = 0 OR p.position      = ANY(p_positions))
    AND (cardinality(p_companies) = 0 OR p.company       = ANY(p_companies))
    AND (cardinality(p_locations) = 0 OR p.location_city = ANY(p_locations))
    AND (p_q = '' OR p.job_title ILIKE '%' || p_q || '%'
                  OR p.company   ILIKE '%' || p_q || '%'
                  OR p.location  ILIKE '%' || p_q || '%')
  ORDER BY
    CASE WHEN p_sort = 'relevance' THEN m.match_score END DESC NULLS LAST,
    CASE WHEN p_sort = 'date'      THEN p.posted_date END DESC NULLS LAST,
    CASE WHEN p_sort = 'added'     THEN m.matched_at  END DESC NULLS LAST,
    m.match_score DESC, m.matched_at DESC
  LIMIT p_limit OFFSET p_offset;
END $$;
GRANT EXECUTE ON FUNCTION get_user_feed_page(TEXT,TEXT,TEXT[],TEXT[],TEXT[],TEXT[],FLOAT,TEXT,INT,INT) TO authenticated;

-- 2) Matching total for pagination labels + stat tiles.
CREATE OR REPLACE FUNCTION get_user_feed_total(
  p_q          TEXT    DEFAULT '',
  p_scope      TEXT    DEFAULT 'all',
  p_boards     TEXT[]  DEFAULT '{}',
  p_positions  TEXT[]  DEFAULT '{}',
  p_companies  TEXT[]  DEFAULT '{}',
  p_locations  TEXT[]  DEFAULT '{}',
  p_min_score  FLOAT   DEFAULT 0
)
RETURNS BIGINT
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT COUNT(*)
  FROM user_job_matches m
  JOIN jobs_pool p ON p.id = m.job_id
  WHERE m.user_id = auth.uid()
    AND m.is_dismissed = FALSE AND m.is_applied = FALSE
    AND (p_scope <> 'new'   OR m.is_new   = TRUE)
    AND (p_scope <> 'saved' OR m.is_saved = TRUE)
    AND (p_min_score <= 0 OR m.match_score >= p_min_score)
    AND (cardinality(p_boards)    = 0 OR p.source        = ANY(p_boards))
    AND (cardinality(p_positions) = 0 OR p.position      = ANY(p_positions))
    AND (cardinality(p_companies) = 0 OR p.company       = ANY(p_companies))
    AND (cardinality(p_locations) = 0 OR p.location_city = ANY(p_locations))
    AND (p_q = '' OR p.job_title ILIKE '%' || p_q || '%'
                  OR p.company   ILIKE '%' || p_q || '%'
                  OR p.location  ILIKE '%' || p_q || '%');
$$;
GRANT EXECUTE ON FUNCTION get_user_feed_total(TEXT,TEXT,TEXT[],TEXT[],TEXT[],TEXT[],FLOAT) TO authenticated;

-- 3) Facets rebuilt the same way (the stage2 version reads the slow view —
--    it is timing out quietly in prod right now). Same signature; p_user is
--    ignored in favour of auth.uid() so a caller can never read another user.
CREATE OR REPLACE FUNCTION get_feed_facets(p_user UUID, p_min_score FLOAT DEFAULT 0.45)
RETURNS JSONB
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  WITH f AS (
    SELECT p.source, p.company, p.position, p.location_city
    FROM user_job_matches m
    JOIN jobs_pool p ON p.id = m.job_id
    WHERE m.user_id = auth.uid()
      AND m.is_dismissed = FALSE AND m.is_applied = FALSE
      AND m.match_score >= p_min_score
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

-- Timing sanity (impersonated): both should be tens of ms.
--   EXPLAIN (ANALYZE) SELECT * FROM get_user_feed_page('', 'all', '{}','{}','{}','{}', 0.45, 'relevance', 50, 0);
--   EXPLAIN (ANALYZE) SELECT get_user_feed_total('', 'all', '{}','{}','{}','{}', 0.45);
