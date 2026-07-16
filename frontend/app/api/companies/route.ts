import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Company directory lookup — powers the careers-page fallback when a company
 * filter matches no open roles. ?names=a,b returns careers_url +
 * last_open_role_at per company (from the `companies` dictionary table,
 * seeded by the ATS detector + refreshed nightly from the pool).
 */
export async function GET(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })

  const names = (new URL(req.url).searchParams.get('names') || '')
    .split(',').map(x => x.trim()).filter(Boolean).slice(0, 20)
  if (!names.length) return NextResponse.json({ ok: true, companies: [] })

  const { data, error } = await supabase
    .from('companies')
    .select('canonical_name, careers_url, ats_platform, last_open_role_at')
    .in('canonical_name', names)
  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })

  const found = new Map((data || []).map(c => [c.canonical_name, c]))
  const companies = names.map(n => found.get(n) || {
    canonical_name: n,
    careers_url: `https://www.google.com/search?q=${encodeURIComponent(`"${n}" careers`)}`,
    ats_platform: null,
    last_open_role_at: null,
  })
  return NextResponse.json({ ok: true, companies })
}
