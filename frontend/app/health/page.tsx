import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import HealthClient from './HealthClient'

export const dynamic = 'force-dynamic'

export default async function HealthPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/')

  const { data: rows } = await supabase
    .from('scraper_health')
    .select('*')
    .order('source')

  return <HealthClient rows={rows || []} />
}
