import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

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
 */
const MAX_ZERO_TERMS = 400 // per kind — keeps the payload sane as the dict grows

export async function GET() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const minScore = Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)
  const { data, error } = await supabase.rpc('get_feed_facets', { p_user: user.id, p_min_score: minScore })
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

  return NextResponse.json({
    ok: true,
    boards:    data?.boards || [],                     // boards stay live-only
    positions: merge(data?.positions, 'position'),
    locations: merge(data?.locations, 'location'),
    companies: merge(data?.companies, 'company'),
  })
}
