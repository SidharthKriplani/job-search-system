import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import HealthClient from './HealthClient'

export const dynamic = 'force-dynamic'

export default async function HealthPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/')

  const [{ data: rows }, { data: history }] = await Promise.all([
    supabase.from('scraper_health').select('*').order('source'),
    supabase.from('scraper_health_history')
      .select('source, run_at, job_count')
      .order('run_at', { ascending: false })
      .limit(400),
  ])

  // Previous count per source (2nd most recent history row) for the trend column.
  const prev: Record<string, number> = {}
  const seen: Record<string, number> = {}
  for (const h of history || []) {
    seen[h.source] = (seen[h.source] || 0) + 1
    if (seen[h.source] === 2) prev[h.source] = h.job_count
  }

  return <HealthClient rows={rows || []} prev={prev} />
}
