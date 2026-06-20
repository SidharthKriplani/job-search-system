import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import SettingsClient from './SettingsClient'

export default async function SettingsPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  // Parallel + maybeSingle() so a missing row returns null instead of throwing.
  const [{ data: profile }, { data: gmailToken }] = await Promise.all([
    supabase
      .from('user_profiles')
      .select('*')
      .eq('user_id', user.id)
      .maybeSingle(),
    supabase
      .from('gmail_tokens')
      .select('updated_at')
      .eq('user_id', user.id)
      .maybeSingle(),
  ])

  return (
    <SettingsClient
      initialProfile={profile}
      userId={user.id}
      gmailConnected={!!gmailToken}
      gmailConnectedAt={gmailToken?.updated_at || null}
    />
  )
}
