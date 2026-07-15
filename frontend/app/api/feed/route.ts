import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'
import { effectiveRoles } from '@/lib/feedFilter'

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
  const source   = url.searchParams.get('source') || 'All'
  const scope    = url.searchParams.get('scope') || 'all'
  const position = url.searchParams.get('position') || ''
  const company  = url.searchParams.get('company') || ''
  const location = url.searchParams.get('location') || ''
  const sort     = url.searchParams.get('sort') || 'relevance'
  const offset = Math.max(0, parseInt(url.searchParams.get('offset') || '0', 10) || 0)
  const limit  = Math.min(100, parseInt(url.searchParams.get('limit') || String(PAGE), 10) || PAGE)

  // Roles = explicit target roles UNION roles detected in the résumé.
  const { data: prof } = await supabase
    .from('user_profiles').select('target_roles, industries, resume_text').eq('user_id', user.id).maybeSingle()
  const roles = effectiveRoles(prof?.target_roles, prof?.resume_text)

  // No profile → no firehose. Return empty + a flag the UI uses to prompt setup.
  if (!(roles.length || prof?.industries?.length)) {
    return NextResponse.json({ ok: true, jobs: [], total: 0, needsProfile: true })
  }

  let query = supabase
    .from('job_feed')
    .select('*', { count: 'exact' })
    .eq('user_id', user.id)
    .eq('is_dismissed', false)
    .eq('is_applied', false)

  // No read-time role .or() — see dashboard/page.tsx: rows are already matched
  // by the backend; the heavy ILIKE OR blew the statement timeout → empty feed.
  if (scope === 'new')   query = query.eq('is_new', true)
  if (scope === 'saved') query = query.eq('is_saved', true)

  if (source !== 'All') {
    if (source === 'gmail') query = query.ilike('source', 'gmail%')
    else                    query = query.eq('source', source)
  }
  // Facet filters (exact bucket values from get_feed_facets). Comma = multi-select.
  const multi = (v: string) => v.split(',').map(x => x.trim()).filter(Boolean)
  const pos = multi(position); if (pos.length) query = query.in('position', pos)
  const loc = multi(location); if (loc.length) query = query.in('location_city', loc)
  const co  = multi(company);  if (co.length)  query = query.in('company', co)

  if (q) {
    // Escape commas/parens that would break PostgREST's or() filter grammar.
    const safe = q.replace(/[,()]/g, ' ')
    query = query.or(`job_title.ilike.%${safe}%,company.ilike.%${safe}%,location.ilike.%${safe}%`)
  }

  // Sort: relevance (match score) or newest (date posted). posted_date can be
  // null (undated), so push nulls last and tie-break by scraped_at.
  if (sort === 'date') {
    query = query.order('posted_date', { ascending: false, nullsFirst: false })
                 .order('scraped_at', { ascending: false })
  } else {
    query = query.order('match_score', { ascending: false })
                 .order('scraped_at', { ascending: false })
  }
  const { data, count, error } = await query.range(offset, offset + limit - 1)

  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, jobs: data || [], total: count || 0 })
}
