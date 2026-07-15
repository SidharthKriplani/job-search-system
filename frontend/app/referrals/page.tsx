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

  // Companies that matter to this user, with LIVE OPENING COUNTS — so the
  // import list can rank "3 connections at companies with 12 open matches"
  // above one-off overlaps.
  const companyCounts: Record<string, number> = {}
  for (const r of [...(feedRows || []), ...(appRows || [])]) {
    const c = (r.company || '').trim()
    if (!c) continue
    companyCounts[c] = (companyCounts[c] || 0) + 1
  }
  const feedCompanies = Object.keys(companyCounts)

  return (
    <ReferralsClient
      initialReferrals={referrals || []}
      templates={templates || []}
      userId={user.id}
      feedCompanies={feedCompanies}
      companyCounts={companyCounts}
    />
  )
}
