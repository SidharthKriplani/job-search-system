import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import { effectiveRoles } from '@/lib/feedFilter'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  const FEED_LIMIT = 200
  const MIN_SCORE = Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)

  const { data: prof } = await supabase
    .from('user_profiles').select('target_roles, industries, resume_text').eq('user_id', user.id).maybeSingle()
  const roles = effectiveRoles(prof?.target_roles, prof?.resume_text)

  const needsProfile = !(roles.length || prof?.industries?.length)
  if (needsProfile) {
    return (
      <DashboardClient
        initialJobs={[]} newCount={0} totalCount={0} feedLimit={FEED_LIMIT}
        appliedCount={0} scraperHealth={[]}
        userName={user.user_metadata?.full_name || user.email || 'there'}
        availableSources={['All']} needsProfile
      />
    )
  }

  // Stage 2 v2: reads via SECURITY DEFINER RPCs (user_job_matches x jobs_pool,
  // caller bound to auth.uid() inside) — measured ~24 ms; the RLS-view path
  // blew the statement timeout. See supabase/migrations/2026-07-17-stage2-v2.sql.
  const base = { p_q: '', p_scope: 'all', p_boards: [], p_positions: [], p_companies: [], p_locations: [], p_min_score: MIN_SCORE }
  const [
    { data: jobs },
    { data: newCount },
    { data: totalCount },
    { count: appliedCount },
    { data: scraperHealth },
  ] = await Promise.all([
    supabase.rpc('get_user_feed_page', { ...base, p_sort: 'relevance', p_limit: FEED_LIMIT, p_offset: 0 }),
    supabase.rpc('get_user_feed_total', { ...base, p_scope: 'new' }),
    supabase.rpc('get_user_feed_total', base),
    supabase
      .from('applications')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id),
    supabase
      .from('scraper_health')
      .select('*')
      .order('source'),
  ])

  const presentSources = Array.from(new Set(
    (jobs || []).map((j: any) => (j.source || '').startsWith('gmail') ? 'gmail' : j.source).filter(Boolean)
  )).sort() as string[]
  const availableSources = ['All', ...presentSources]

  return (
    <DashboardClient
      initialJobs={jobs || []}
      newCount={Number(newCount) || 0}
      totalCount={Number(totalCount) || 0}
      feedLimit={FEED_LIMIT}
      appliedCount={appliedCount || 0}
      scraperHealth={scraperHealth || []}
      userName={user.user_metadata?.full_name || user.email || 'there'}
      availableSources={availableSources}
    />
  )
}
