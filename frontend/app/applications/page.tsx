import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import ApplicationsClient from './ApplicationsClient'

export default async function ApplicationsPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  const { data: applications } = await supabase
    .from('applications')
    .select('*')
    .eq('user_id', user.id)
    .order('updated_at', { ascending: false })

  return <ApplicationsClient initialApplications={applications || []} userId={user.id} />
}
