import { expandRoleKeywords } from './roleGraph'

/**
 * Read-time role guard for the feed.
 *
 * match_score is computed by the backend against whatever profile was active at
 * scrape time. When you change your target role, those stored rows are stale
 * until a backend re-filter runs (async, not guaranteed instantly). To make the
 * feed ALWAYS reflect the current role, we require each shown job's title /
 * description / company to contain a keyword from the role's NEIGHBOURHOOD (via
 * the role graph) or its sector — so adjacent roles (ML Engineer for a Data
 * Scientist target) are kept while gross mismatches (Engineers for an Investment
 * Banker target) are dropped, with no wait on any backend job.
 *
 * Returns a PostgREST `.or()` filter string, or null when there's nothing to
 * guard on (then no guard is applied).
 */
export function roleOrFilter(
  roles: string[] | null | undefined,
  industries?: string[] | null,
): string | null {
  const keywords = expandRoleKeywords(roles, industries)
  if (keywords.length === 0) return null
  const parts: string[] = []
  for (const w of keywords.slice(0, 30)) {
    const safe = w.replace(/[,()]/g, ' ')
    parts.push(`job_title.ilike.%${safe}%`)
    parts.push(`description_snippet.ilike.%${safe}%`)
    parts.push(`company.ilike.%${safe}%`)
  }
  return parts.join(',')
}
