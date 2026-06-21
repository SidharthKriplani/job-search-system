import { expandRoleKeywords, rolesFromText } from './roleGraph'

/**
 * The roles that should drive the feed: explicitly-set target roles UNION the
 * roles detected in the résumé. Keeps the read-guard consistent with the backend
 * matcher (which also derives roles from the résumé) — so a user who only has a
 * résumé saved still gets a personalised feed, not the "set up your profile" wall.
 */
export function effectiveRoles(
  targetRoles: string[] | null | undefined,
  resumeText: string | null | undefined,
): string[] {
  const set = new Set((targetRoles || []).map(r => r.toLowerCase()).filter(Boolean))
  for (const r of rolesFromText(resumeText || '')) set.add(r)
  return Array.from(set)
}

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
  const { singles, phrases } = expandRoleKeywords(roles, industries)
  if (singles.length === 0 && phrases.length === 0) return null
  const clean = (w: string) => w.replace(/[,()]/g, ' ')
  const parts: string[] = []
  // Phrases are high-precision → match across title, description, company.
  // Cap is generous: a single finance family is ~27 phrases; truncating silently
  // dropped neighbours the matcher kept. PostgREST handles many OR terms fine.
  for (const p of phrases.slice(0, 50)) {
    const s = clean(p)
    parts.push(`job_title.ilike.%${s}%`)
    parts.push(`description_snippet.ilike.%${s}%`)
    parts.push(`company.ilike.%${s}%`)
  }
  // Singles are noisier → restrict to title + company (skip descriptions).
  for (const w of singles.slice(0, 12)) {
    const s = clean(w)
    parts.push(`job_title.ilike.%${s}%`)
    parts.push(`company.ilike.%${s}%`)
  }
  return parts.join(',')
}
