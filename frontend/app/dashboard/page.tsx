import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  // Run all four reads in parallel instead of sequentially — this is the main
  // cause of the tab-switch latency (4 round-trips became 1 round-trip worth).
  const FEED_LIMIT = 200

  const [
    { data: jobs },
    { count: newCount },
    { count: totalCount },
    { count: appliedCount },
    { data: scraperHealth },
  ] = await Promise.all([
    // The feed itself: top matches, applied jobs excluded (they live in the tracker).
    supabase
      .from('job_feed')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_dismissed', false)
      .eq('is_applied', false)
      .order('match_score', { ascending: false })
      .order('scraped_at', { ascending: false })
      .limit(FEED_LIMIT),
    // "New" = genuinely new, not-yet-applied postings.
    supabase
      .from('job_feed')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('is_new', true)
      .eq('is_dismissed', false)
      .eq('is_applied', false),
    // Total matched jobs in the feed (so "In Feed" is the truth, not the page size).
    supabase
      .from('job_feed')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('is_dismissed', false)
      .eq('is_applied', false),
    supabase
      .from('applications')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id),
    supabase
      .from('scraper_health')
      .select('*')
      .order('source'),
  ])

  return (
    <DashboardClient
      initialJobs={jobs || []}
      newCount={newCount || 0}
      totalCount={totalCount || 0}
      feedLimit={FEED_LIMIT}
      appliedCount={appliedCount || 0}
      scraperHealth={scraperHealth || []}
      userName={user.user_metadata?.full_name || user.email || 'there'}
    />
  )
}
