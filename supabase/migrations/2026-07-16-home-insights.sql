-- ============================================================================
-- HOME INSIGHTS RPC — one round-trip powering the /home dashboard.
-- Idempotent. SECURITY DEFINER (reads global tables run_history /
-- scraper_health_history / jobs_pool; nothing user-specific in here — the
-- personal tiles are queried RLS-scoped by the page itself).
-- ============================================================================
CREATE OR REPLACE FUNCTION get_home_insights()
RETURNS JSONB
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
SELECT jsonb_build_object(

  -- Pool size per day, last 30 days (max across the night's shards)
  'pool_curve', COALESCE((
    SELECT jsonb_agg(jsonb_build_object('d', d, 'v', v) ORDER BY d)
    FROM (
      SELECT date_trunc('day', run_at)::date AS d, MAX(pool_size) AS v
      FROM run_history
      WHERE run_at > NOW() - INTERVAL '30 days' AND pool_size > 0
      GROUP BY 1
    ) t), '[]'::jsonb),

  -- Jobs upserted per day, last 30 days
  'added_curve', COALESCE((
    SELECT jsonb_agg(jsonb_build_object('d', d, 'v', v) ORDER BY d)
    FROM (
      SELECT date_trunc('day', run_at)::date AS d, SUM(total_upserted) AS v
      FROM run_history
      WHERE run_at > NOW() - INTERVAL '30 days'
      GROUP BY 1
    ) t), '[]'::jsonb),

  -- Latest job count per source (most recent run of each source)
  'sources', COALESCE((
    SELECT jsonb_agg(jsonb_build_object('source', source, 'v', job_count) ORDER BY job_count DESC)
    FROM (
      SELECT DISTINCT ON (source) source, job_count
      FROM scraper_health_history
      ORDER BY source, run_at DESC
    ) t WHERE job_count > 0), '[]'::jsonb),

  -- Top hiring companies this week (from the global pool)
  'top_companies', COALESCE((
    SELECT jsonb_agg(jsonb_build_object('k', company, 'v', n) ORDER BY n DESC)
    FROM (
      SELECT company, COUNT(*) n FROM jobs_pool
      WHERE last_seen_at > NOW() - INTERVAL '7 days' AND company <> ''
      GROUP BY company ORDER BY n DESC LIMIT 10
    ) t), '[]'::jsonb),

  -- Top role buckets this week
  'top_positions', COALESCE((
    SELECT jsonb_agg(jsonb_build_object('k', position, 'v', n) ORDER BY n DESC)
    FROM (
      SELECT position, COUNT(*) n FROM jobs_pool
      WHERE last_seen_at > NOW() - INTERVAL '7 days' AND position IS NOT NULL AND position <> ''
      GROUP BY position ORDER BY n DESC LIMIT 8
    ) t), '[]'::jsonb),

  'pool_total', (SELECT COUNT(*) FROM jobs_pool),
  'generated_at', NOW()
);
$$;
GRANT EXECUTE ON FUNCTION get_home_insights() TO authenticated;
