// lib/locationScope.ts — turn freeform profile locations ("Bengaluru",
// "Delhi NCR", "remote") into the canonical `location_city` values the feed
// RPCs filter on (exact `= ANY(p_locations)` match).
//
// Contract (see DECISIONS.md): populated settings are the OUTER BOUNDARY of
// the feed — facet filters may only narrow within it. Empty settings = no
// boundary. The expansion is done against the cumulative location dictionary
// (facet_terms kind='location'), so it self-heals as new cities appear
// (dictionary refresh is throttled ~12h; a brand-new city can lag one cycle).

const ALIAS: Record<string, string[]> = {
  bengaluru: ['bangalore'],
  bangalore: ['bengaluru'],
  gurgaon: ['gurugram'],
  gurugram: ['gurgaon'],
  mumbai: ['bombay', 'navi mumbai'],
  bombay: ['mumbai'],
  delhi: ['new delhi'],
  'new delhi': ['delhi'],
  'delhi ncr': ['delhi', 'new delhi', 'noida', 'gurugram', 'gurgaon', 'ghaziabad', 'faridabad'],
  ncr: ['delhi', 'new delhi', 'noida', 'gurugram', 'gurgaon'],
  hyderabad: ['secunderabad'],
  chennai: ['madras'],
  kolkata: ['calcutta'],
  remote: ['remote', 'work from home', 'wfh', 'anywhere'],
}

function norm(s: string): string {
  return (s || '').toLowerCase().trim()
}

/** Does one freeform profile location match one canonical city value? */
export function matchCity(profileLoc: string, city: string): boolean {
  const a = norm(profileLoc)
  const b = norm(city)
  if (!a || !b) return false
  if (b.includes(a) || a.includes(b)) return true
  for (const alias of ALIAS[a] || []) {
    if (b.includes(alias)) return true
  }
  return false
}

/**
 * Expand profile locations against the known city dictionary.
 * Returns the matching canonical city values ([] = nothing matched — callers
 * should then NOT constrain, and surface a "locations unmatched" note instead
 * of silently emptying the feed).
 */
export function expandLocations(profileLocs: string[], cities: string[]): string[] {
  const out = new Set<string>()
  const locs = (profileLocs || []).filter(Boolean)
  if (!locs.length) return []
  for (const c of cities || []) {
    for (const p of locs) {
      if (matchCity(p, c)) { out.add(c); break }
    }
  }
  return Array.from(out)
}

/**
 * One-stop server helper: read the location dictionary and expand the
 * profile's locations against it. `supabase` is a server client.
 */
export async function scopedLocationsFor(
  supabase: any,
  profileLocations: string[] | null | undefined,
): Promise<{ scoped: string[]; active: boolean; unmatched: boolean }> {
  const locs = (profileLocations || []).filter(Boolean)
  if (!locs.length) return { scoped: [], active: false, unmatched: false }
  let cities: string[] = []
  try {
    const { data } = await supabase.from('facet_terms').select('value').eq('kind', 'location')
    cities = (data || []).map((r: { value: string }) => r.value)
  } catch { /* dictionary unavailable → treat as unmatched (no constraint) */ }
  const scoped = expandLocations(locs, cities)
  // active=false when nothing matched: constraining to zero known cities would
  // blank the feed on a typo — surface it instead (scopeNote in the API).
  return { scoped, active: scoped.length > 0, unmatched: scoped.length === 0 }
}
