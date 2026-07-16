import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import HomeClient from './HomeClient'

/**
 * Home = insights. Market-wide series come from one get_home_insights() RPC
 * (run_history / scraper_health_history / jobs_pool); the personal tiles and
 * funnel are RLS-scoped queries. The feed itself lives at /dashboard.
 */
export default async function HomePage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/')

  const MIN_SCORE = Number(process.env.NEXT_PUBLIC_MIN_FEED_SCORE || 0.45)

  const countQ = (extra?: (q: any) => any) => {
    const q = supabase.from('job_feed').select('*', { count: 'exact', head: true })
      .eq('user_id', user.id).eq('is_dismissed', false).eq('is_applied', false)
      .gte('match_score', MIN_SCORE)
    return extra ? extra(q) : q
  }

  const [
    { data: insights },
    { count: newCount },
    { count: feedCount },
    { count: savedCount },
    { data: apps },
    { data: salaryBands },
  ] = await Promise.all([
    supabase.rpc('get_home_insights'),
    countQ(q => q.eq('is_new', true)),
    countQ(),
    countQ(q => q.eq('is_saved', true)),
    supabase.from('applications').select('stage').eq('user_id', user.id),
    // CTC benchmarks: all-city rollups ('' city), biggest samples first.
    supabase.from('salary_stats')
      .select('position, n, p25, p50, p75')
      .eq('location_city', '')
      .order('n', { ascending: false })
      .limit(8),
  ])

  // Collapse the 18 tracker stages into a 5-step funnel.
  const buckets = { Applied: 0, Screening: 0, Interviewing: 0, Offer: 0, Closed: 0 }
  for (const a of apps || []) {
    const s = a.stage as string
    if (['Applied', 'Application Acknowledged'].includes(s)) buckets.Applied++
    else if (['Recruiter Screening', 'HM Interview Scheduled'].includes(s)) buckets.Screening++
    else if (['HM Interview Done', 'Technical Round Scheduled', 'Technical Round Done',
              'Case Study / Assignment', 'Final Round Scheduled', 'Final Round Done',
              'Reference Check', 'Background Check'].includes(s)) buckets.Interviewing++
    else if (['Offer Verbal', 'Offer Written', 'Offer Negotiating', 'Offer Accepted'].includes(s)) buckets.Offer++
    else if (['Rejected', 'Withdrawn', 'Ghosted'].includes(s)) buckets.Closed++
    else buckets.Applied++  // 'Not Applied' and stragglers
  }

  return (
    <HomeClient
      userName={user.user_metadata?.full_name || user.email || 'there'}
      newCount={newCount || 0}
      feedCount={feedCount || 0}
      savedCount={savedCount || 0}
      appliedTotal={(apps || []).length}
      funnel={buckets}
      insights={insights || {}}
      salaryBands={salaryBands || []}
    />
  )
}
