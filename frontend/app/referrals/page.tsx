import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import ReferralsClient from './ReferralsClient'

export default async function ReferralsPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/')

  const [{ data: referrals }, { data: templates }, { data: feedRows }, { data: appRows }] = await Promise.all([
    supabase
      .from('referral_pipeline')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false }),
    supabase
      .from('message_templates')
      .select('*')
      .eq('user_id', user.id)
      .eq('template_type', 'linkedin_referral'),
    // Companies the user has live jobs at — used to flag "you know someone here".
    supabase
      .from('job_feed')
      .select('company')
      .eq('user_id', user.id)
      .eq('is_dismissed', false),
    supabase
      .from('applications')
      .select('company')
      .eq('user_id', user.id),
  ])

  // De-duped list of companies that matter to this user (feed + tracker).
  const feedCompanies = Array.from(new Set(
    [...(feedRows || []), ...(appRows || [])]
      .map(r => (r.company || '').trim())
      .filter(Boolean)
  ))

  return (
    <ReferralsClient
      initialReferrals={referrals || []}
      templates={templates || []}
      userId={user.id}
      feedCompanies={feedCompanies}
    />
  )
}
