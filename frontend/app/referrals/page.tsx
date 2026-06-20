import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import ReferralsClient from './ReferralsClient'

export default async function ReferralsPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  const { data: referrals } = await supabase
    .from('referral_pipeline')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })

  const { data: templates } = await supabase
    .from('message_templates')
    .select('*')
    .eq('user_id', user.id)
    .eq('template_type', 'linkedin_referral')

  return (
    <ReferralsClient
      initialReferrals={referrals || []}
      templates={templates || []}
      userId={user.id}
    />
  )
}
