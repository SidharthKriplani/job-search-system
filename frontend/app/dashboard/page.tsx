import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import DashboardClient from './DashboardClient'

export default async function DashboardPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  // Fetch initial job feed (last 7 days, not dismissed, sorted by match_score)
  const { data: jobs } = await supabase
    .from('job_feed')
    .select('*')
    .eq('user_id', user.id)
    .eq('is_dismissed', false)
    .gte('scraped_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
    .order('match_score', { ascending: false })
    .order('scraped_at', { ascending: false })
    .limit(100)

  // Stats
  const { count: newCount } = await supabase
    .from('job_feed')
    .select('*', { count: 'exact', head: true })
    .eq('user_id', user.id)
    .eq('is_new', true)
    .eq('is_dismissed', false)

  const { count: appliedCount } = await supabase
    .from('applications')
    .select('*', { count: 'exact', head: true })
    .eq('user_id', user.id)

  const { data: scraperHealth } = await supabase
    .from('scraper_health')
    .select('*')
    .order('source')

  return (
    <DashboardClient
      initialJobs={jobs || []}
      newCount={newCount || 0}
      appliedCount={appliedCount || 0}
      scraperHealth={scraperHealth || []}
      userName={user.user_metadata?.full_name || user.email || 'there'}
    />
  )
}
