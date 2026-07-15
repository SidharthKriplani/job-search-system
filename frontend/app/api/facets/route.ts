import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Dynamic filter options for the dashboard — the distinct boards, positions,
 * locations, and top companies actually present in THIS user's active feed,
 * with counts. One DB round-trip via the get_feed_facets RPC (RLS-scoped).
 */
export async function GET() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const minScore = Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)
  const { data, error } = await supabase.rpc('get_feed_facets', { p_user: user.id, p_min_score: minScore })
  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })

  return NextResponse.json({
    ok: true,
    boards:    data?.boards    || [],
    positions: data?.positions || [],
    locations: data?.locations || [],
    companies: data?.companies || [],
  })
}
