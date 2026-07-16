import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'
import { expandLocations } from '@/lib/locationScope'

/**
 * Filter options for the dashboard = live facets ∪ cumulative dictionary.
 *
 *  - get_feed_facets RPC: distinct values in THIS user's active feed, with
 *    counts (unchanged).
 *  - facet_terms: the CUMULATIVE dictionary (companies/locations/positions
 *    ever seen in the pool). Terms absent from the live feed are appended
 *    with count 0 — so the filter list only ever expands, and selecting a
 *    0-count company triggers the careers-page fallback in the feed.
 *  - refresh_facet_terms(): fire-and-forget; self-throttled to 12h in SQL,
 *    so calling it on every facet load is safe and keeps the dictionary
 *    current without any scheduler wiring.
 *
 * Settings-scope contract (2026-07-16): when the profile has `locations` set
 * (and `scopeOff=1` is not passed), the LOCATION options are trimmed to the
 * profile's boundary — both the live options and the dictionary merge — so
 * the filter UI can't offer values the feed would refuse anyway. Positions
 * keep their live-feed options (already role-scoped by ingest); companies
 * keep the full dictionary on purpose — 0-count companies power the
 * careers-page fallback, which is an explicit product feature.
 */
const MAX_ZERO_TERMS = 400 // per kind — keeps the payload sane as the dict grows

export async function GET(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const scopeOff = new URL(req.url).searchParams.get('scopeOff') === '1'

  const minScore = Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)
  const [{ data, error }, { data: prof }] = await Promise.all([
    supabase.rpc('get_feed_facets', { p_user: user.id, p_min_score: minScore }),
    supabase.from('user_profiles').select('locations').eq('user_id', user.id).maybeSingle(),
  ])
  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })

  // Keep the dictionary fresh (no await needed for correctness; SQL throttles).
  supabase.rpc('refresh_facet_terms').then(() => {}, () => {})

  // Merge cumulative terms (count 0) under the live options.
  let terms: { kind: string; value: string }[] = []
  try {
    const { data: t } = await supabase.from('facet_terms').select('kind,value')
    terms = t || []
  } catch { /* dictionary optional — live facets still work */ }

  const merge = (live: { value: string; count: number }[], kind: string) => {
    const have = new Set((live || []).map(o => o.value))
    const extra = terms
      .filter(t => t.kind === kind && !have.has(t.value))
      .map(t => ({ value: t.value, count: 0 }))
      .sort((a, b) => a.value.localeCompare(b.value))
      .slice(0, MAX_ZERO_TERMS)
    return [...(live || []), ...extra]
  }

  // Location boundary: trim location OPTIONS to the profile's scope.
  let locations = merge(data?.locations, 'location')
  let locationScoped = false
  const profileLocs = (prof?.locations || []).filter(Boolean)
  if (!scopeOff && profileLocs.length) {
    const allCities = locations.map(o => o.value)
    const allowed = new Set(expandLocations(profileLocs, allCities).map(s => s.toLowerCase()))
    if (allowed.size) {
      locations = locations.filter(o => allowed.has(o.value.toLowerCase()))
      locationScoped = true
    }
    // No matches (typo'd settings) → leave options unscoped; the feed route
    // reports `locations_unmatched` for the same case.
  }

  return NextResponse.json({
    ok: true,
    boards:    data?.boards || [],                     // boards stay live-only
    positions: merge(data?.positions, 'position'),
    locations,
    companies: merge(data?.companies, 'company'),
    locationScoped,
  })
}
