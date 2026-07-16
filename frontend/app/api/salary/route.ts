import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Salary benchmarks (CTC-to-ask heuristic). Serves the whole salary_stats
 * table — it's small (positions × cities with n >= 5) and the dashboard
 * builds a lookup map client-side, so one fetch covers every card.
 * Cached per-request only; the table changes once a night.
 */
export async function GET() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const { data, error } = await supabase
    .from('salary_stats')
    .select('position, location_city, n, p25, p50, p75')
    .order('n', { ascending: false })
    .limit(2000)

  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, stats: data || [] })
}
