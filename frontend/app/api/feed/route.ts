import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'
import { effectiveRoles } from '@/lib/feedFilter'

/**
 * Server-side feed query — Stage 2 v2: reads go through the SECURITY DEFINER
 * RPCs (get_user_feed_page / get_user_feed_total), which join
 * user_job_matches × jobs_pool with the caller hard-bound to auth.uid().
 * Measured at ~24 ms vs 4,687 ms for the RLS view — see
 * supabase/migrations/2026-07-17-stage2-v2.sql.
 *
 * Query params: q, board, position, company, location, scope (all|new|saved),
 * sort (relevance|date|added), offset, limit.
 */
const PAGE = 50

export async function GET(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const url    = new URL(req.url)
  const q        = (url.searchParams.get('q') || '').trim()
  const board    = url.searchParams.get('board') || ''
  const scope    = url.searchParams.get('scope') || 'all'
  const position = url.searchParams.get('position') || ''
  const company  = url.searchParams.get('company') || ''
  const location = url.searchParams.get('location') || ''
  const sort     = url.searchParams.get('sort') || 'relevance'
  const offset = Math.max(0, parseInt(url.searchParams.get('offset') || '0', 10) || 0)
  const limit  = Math.min(100, parseInt(url.searchParams.get('limit') || String(PAGE), 10) || PAGE)

  const { data: prof } = await supabase
    .from('user_profiles').select('target_roles, industries, resume_text').eq('user_id', user.id).maybeSingle()
  const roles = effectiveRoles(prof?.target_roles, prof?.resume_text)
  if (!(roles.length || prof?.industries?.length)) {
    return NextResponse.json({ ok: true, jobs: [], total: 0, needsProfile: true })
  }

  const multi = (v: string) => v.split(',').map(x => x.trim()).filter(Boolean)
  const boards = multi(board), pos = multi(position), cos = multi(company), locs = multi(location)

  // Relevance floor only on the unfiltered browse view (0 disables it in SQL).
  const narrowed = !!q || boards.length > 0 || pos.length > 0 || locs.length > 0 || cos.length > 0 || scope !== 'all'
  const minScore = narrowed ? 0 : Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)

  const filters = {
    p_q: q, p_scope: scope, p_boards: boards, p_positions: pos,
    p_companies: cos, p_locations: locs, p_min_score: minScore,
  }
  const [{ data: jobs, error: e1 }, { data: total, error: e2 }] = await Promise.all([
    supabase.rpc('get_user_feed_page', { ...filters, p_sort: sort, p_limit: limit, p_offset: offset }),
    supabase.rpc('get_user_feed_total', filters),
  ])

  const error = e1 || e2
  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, jobs: jobs || [], total: Number(total) || 0 })
}
