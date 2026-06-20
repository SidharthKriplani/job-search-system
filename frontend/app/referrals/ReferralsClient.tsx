'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import { ReferralContact } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import { Plus, Linkedin, Mail, X, Copy, Check } from 'lucide-react'
import clsx from 'clsx'

const STATUS_COLORS: Record<string, string> = {
  identified:      'bg-slate-100 text-slate-600',
  message_drafted: 'bg-blue-100 text-blue-700',
  message_sent:    'bg-violet-100 text-violet-700',
  responded:       'bg-amber-100 text-amber-700',
  call_scheduled:  'bg-orange-100 text-orange-700',
  referred:        'bg-green-100 text-green-700',
  not_responding:  'bg-red-50 text-red-600',
  declined:        'bg-slate-100 text-slate-400',
}

const STATUS_LABELS: Record<string, string> = {
  identified:      'Identified',
  message_drafted: 'Draft Ready',
  message_sent:    'Sent',
  responded:       'Responded',
  call_scheduled:  'Call Scheduled',
  referred:        'Referred ✓',
  not_responding:  'No Response',
  declined:        'Declined',
}

interface Props {
  initialReferrals: ReferralContact[]
  templates: any[]
  userId: string
}

export default function ReferralsClient({ initialReferrals, templates, userId }: Props) {
  const supabase = createClient()
  const [referrals, setReferrals] = useState(initialReferrals)
  const [showModal, setShowModal] = useState(false)
  const [newContact, setNewContact] = useState<Partial<ReferralContact>>({ status: 'identified' })
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const defaultTemplate = templates.find(t => t.is_default)?.body || ''

  const addContact = async () => {
    if (!newContact.contact_name || !newContact.company) return
    setSaving(true)
    const { data } = await supabase.from('referral_pipeline').insert({
      ...newContact,
      user_id: userId,
    }).select().single()
    if (data) setReferrals(prev => [data, ...prev])
    setNewContact({ status: 'identified' })
    setShowModal(false)
    setSaving(false)
  }

  const updateStatus = async (id: string, status: string) => {
    await supabase.from('referral_pipeline').update({ status }).eq('id', id)
    setReferrals(prev => prev.map(r => r.id === id ? { ...r, status: status as any } : r))
  }

  const copyMessage = (contact: ReferralContact) => {
    const msg = defaultTemplate
      .replace('{name}', contact.contact_name)
      .replace('{role}', 'the relevant role')
      .replace('{company}', contact.company)
    navigator.clipboard.writeText(msg)
    setCopiedId(contact.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const byStatus = (status: string) => referrals.filter(r => r.status === status)

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6 max-w-5xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Referral Pipeline</h1>
            <p className="text-slate-500 text-sm mt-0.5">{referrals.length} contacts · track outreach from identification to referral</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Contact
          </button>
        </div>

        {/* Pipeline stages */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {['identified', 'message_sent', 'responded', 'referred'].map(status => (
            <div key={status} className="bg-white border border-slate-200 rounded-xl p-3">
              <div className={clsx('inline-flex px-2 py-0.5 rounded-full text-xs font-medium mb-1.5', STATUS_COLORS[status])}>
                {STATUS_LABELS[status]}
              </div>
              <p className="text-2xl font-bold text-slate-900">{byStatus(status).length}</p>
            </div>
          ))}
        </div>

        {/* Contact cards */}
        <div className="space-y-2">
          {referrals.map(contact => (
            <div key={contact.id} className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-900 text-sm">{contact.contact_name}</span>
                    <span className="text-slate-400 text-xs">at</span>
                    <span className="font-medium text-slate-700 text-sm">{contact.company}</span>
                    {contact.contact_role && (
                      <span className="text-slate-500 text-xs">· {contact.contact_role}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 mt-2">
                    {contact.contact_linkedin && (
                      <a href={contact.contact_linkedin} target="_blank" rel="noopener noreferrer"
                         className="text-blue-500 hover:text-blue-700 text-xs flex items-center gap-1">
                        <Linkedin className="w-3 h-3" /> LinkedIn
                      </a>
                    )}
                    {contact.contact_email && (
                      <a href={`mailto:${contact.contact_email}`}
                         className="text-slate-500 hover:text-slate-700 text-xs flex items-center gap-1">
                        <Mail className="w-3 h-3" /> Email
                      </a>
                    )}
                    {contact.follow_up_date && (
                      <span className="text-amber-600 text-xs">Follow-up: {contact.follow_up_date}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Copy message button */}
                  {defaultTemplate && (
                    <button
                      onClick={() => copyMessage(contact)}
                      className={clsx(
                        'p-1.5 rounded-lg transition-colors text-xs',
                        copiedId === contact.id
                          ? 'bg-green-50 text-green-600'
                          : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                      )}
                      title="Copy referral message"
                    >
                      {copiedId === contact.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}

                  {/* Status selector */}
                  <select
                    value={contact.status}
                    onChange={e => updateStatus(contact.id, e.target.value)}
                    className={clsx(
                      'text-xs font-medium px-2 py-1 rounded-full border-0 focus:ring-2 focus:ring-indigo-500',
                      STATUS_COLORS[contact.status]
                    )}
                  >
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {contact.notes && (
                <p className="text-slate-500 text-xs mt-2 border-t border-slate-100 pt-2">{contact.notes}</p>
              )}
            </div>
          ))}
        </div>

        {referrals.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p className="font-medium">No referral contacts yet</p>
            <p className="text-sm mt-1">Add connections you're planning to reach out to for referrals</p>
          </div>
        )}
      </main>

      {/* Add Contact Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="font-bold text-lg text-slate-900 mb-4">Add Referral Contact</h2>
            <div className="space-y-3">
              {[
                { key: 'contact_name',     label: 'Name', required: true },
                { key: 'company',          label: 'Company', required: true },
                { key: 'contact_role',     label: 'Their Role' },
                { key: 'contact_linkedin', label: 'LinkedIn URL' },
                { key: 'contact_email',    label: 'Email' },
                { key: 'notes',            label: 'Notes / How you know them' },
              ].map(({ key, label, required }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-slate-600 mb-1 block">
                    {label}{required && ' *'}
                  </label>
                  <input
                    type="text"
                    value={(newContact as any)[key] || ''}
                    onChange={e => setNewContact(p => ({ ...p, [key]: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm
                               focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowModal(false)}
                className="flex-1 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                Cancel
              </button>
              <button onClick={addContact} disabled={saving || !newContact.contact_name || !newContact.company}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm
                           font-medium rounded-lg disabled:opacity-50 transition-colors">
                {saving ? 'Saving...' : 'Add Contact'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
