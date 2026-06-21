import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import { roleOrFilter, effectiveRoles } from '@/lib/feedFilter'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  const FEED_LIMIT = 200

  // Read-time role guard so the feed always reflects the CURRENT target role,
  // even before a backend re-filter prunes stale rows.
  const { data: prof } = await supabase
    .from('user_profiles').select('target_roles, industries, resume_text').eq('user_id', user.id).maybeSingle()
  // Roles = explicit target roles UNION roles detected in the résumé.
  const roles = effectiveRoles(prof?.target_roles, prof?.resume_text)
  const roleFilter = roleOrFilter(roles, prof?.industries)

  // Only show "set up your profile" when we truly have nothing to go on.
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

  const feedQ    = () => {
    let q = supabase.from('job_feed').select('*')
      .eq('user_id', user.id).eq('is_dismissed', false).eq('is_applied', false)
    if (roleFilter) q = q.or(roleFilter)
    return q
  }
  const countQ   = (extra?: (q: any) => any) => {
    let q = supabase.from('job_feed').select('*', { count: 'exact', head: true })
      .eq('user_id', user.id).eq('is_dismissed', false).eq('is_applied', false)
    if (roleFilter) q = q.or(roleFilter)
    return extra ? extra(q) : q
  }

  const [
    { data: jobs },
    { count: newCount },
    { count: totalCount },
    { count: appliedCount },
    { data: scraperHealth },
  ] = await Promise.all([
    feedQ()
      .order('match_score', { ascending: false })
      .order('scraped_at', { ascending: false })
      .limit(FEED_LIMIT),
    countQ(q => q.eq('is_new', true)),
    countQ(),
    supabase
      .from('applications')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id),
    supabase
      .from('scraper_health')
      .select('*')
      .order('source'),
  ])

  // Source pills reflect what's actually in the feed (gmail_* collapses to gmail).
  const presentSources = Array.from(new Set(
    (jobs || []).map(j => (j.source || '').startsWith('gmail') ? 'gmail' : j.source).filter(Boolean)
  )).sort()
  const availableSources = ['All', ...presentSources]

  return (
    <DashboardClient
      initialJobs={jobs || []}
      newCount={newCount || 0}
      totalCount={totalCount || 0}
      feedLimit={FEED_LIMIT}
      appliedCount={appliedCount || 0}
      scraperHealth={scraperHealth || []}
      userName={user.user_metadata?.full_name || user.email || 'there'}
      availableSources={availableSources}
    />
  )
}
