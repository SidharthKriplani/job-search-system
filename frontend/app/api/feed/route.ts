import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Server-side feed query — so search, source filter, and "New/Saved" run against
 * the WHOLE feed in Postgres, not just the first 200 rows loaded in the browser.
 * Also powers "Load more" pagination via offset/limit.
 *
 * Query params: q, source, scope (all|new|saved), offset, limit.
 */
const PAGE = 50

export async function GET(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const url    = new URL(req.url)
  const q      = (url.searchParams.get('q') || '').trim()
  const source = url.searchParams.get('source') || 'All'
  const scope  = url.searchParams.get('scope') || 'all'
  const offset = Math.max(0, parseInt(url.searchParams.get('offset') || '0', 10) || 0)
  const limit  = Math.min(100, parseInt(url.searchParams.get('limit') || String(PAGE), 10) || PAGE)

  let query = supabase
    .from('job_feed')
    .select('*', { count: 'exact' })
    .eq('user_id', user.id)
    .eq('is_dismissed', false)
    .eq('is_applied', false)

  if (scope === 'new')   query = query.eq('is_new', true)
  if (scope === 'saved') query = query.eq('is_saved', true)

  if (source !== 'All') {
    if (source === 'gmail') query = query.ilike('source', 'gmail%')
    else                    query = query.eq('source', source)
  }

  if (q) {
    // Escape commas/parens that would break PostgREST's or() filter grammar.
    const safe = q.replace(/[,()]/g, ' ')
    query = query.or(`job_title.ilike.%${safe}%,company.ilike.%${safe}%,location.ilike.%${safe}%`)
  }

  const { data, count, error } = await query
    .order('match_score', { ascending: false })
    .order('scraped_at', { ascending: false })
    .range(offset, offset + limit - 1)

  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, jobs: data || [], total: count || 0 })
}
