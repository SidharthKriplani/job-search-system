/**
 * Read-time role guard for the feed.
 *
 * match_score is computed by the backend against whatever profile was active at
 * scrape time. When you change your target role, those stored rows are stale
 * until a backend re-filter runs (async, not guaranteed instantly). To make the
 * feed ALWAYS reflect the current role, we additionally require each shown job's
 * title or description to contain at least one significant word from a target
 * role. This deterministically drops gross mismatches (e.g. Engineers when your
 * role is "investment banker") without waiting on any backend job.
 *
 * Returns a PostgREST `.or()` filter string, or null when there are no roles
 * (then no guard is applied).
 */
export function roleOrFilter(roles: string[] | null | undefined): string | null {
  if (!roles || roles.length === 0) return null
  const words = new Set<string>()
  for (const r of roles) {
    for (const w of (r || '').toLowerCase().split(/\s+/)) {
      const clean = w.replace(/[^a-z0-9]/g, '')
      if (clean.length >= 3) words.add(clean)   // skip "ai"/"of" etc.; backend handles nuance
    }
  }
  if (words.size === 0) return null
  const parts: string[] = []
  for (const w of Array.from(words).slice(0, 12)) {
    parts.push(`job_title.ilike.%${w}%`)
    parts.push(`description_snippet.ilike.%${w}%`)
  }
  return parts.join(',')
}
