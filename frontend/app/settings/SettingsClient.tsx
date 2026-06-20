'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import { UserProfile } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import { CheckCircle, Mail, Save, Plus, X } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  initialProfile: UserProfile | null
  userId: string
  gmailConnected: boolean
  gmailConnectedAt: string | null
}

export default function SettingsClient({ initialProfile, userId, gmailConnected, gmailConnectedAt }: Props) {
  const supabase = createClient()

  const [profile, setProfile] = useState<Partial<UserProfile>>(initialProfile || {
    target_roles: [],
    locations: [],
    industries: [],
    target_companies: [],
    exclude_companies: [],
    salary_floor: 0,
    experience_years: 0,
  })

  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [newRole, setNewRole] = useState('')
  const [newLocation, setNewLocation] = useState('')
  const [newIndustry, setNewIndustry] = useState('')
  const [newExclude, setNewExclude] = useState('')

  const saveProfile = async () => {
    setSaving(true)
    await supabase.from('user_profiles').upsert({
      ...profile,
      user_id: userId,
    }, { onConflict: 'user_id' })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const addTo = (field: keyof UserProfile, value: string, setter: (v: string) => void) => {
    if (!value.trim()) return
    setProfile(p => ({ ...p, [field]: [...((p[field] as string[]) || []), value.trim()] }))
    setter('')
  }

  const removeFrom = (field: keyof UserProfile, index: number) => {
    setProfile(p => ({ ...p, [field]: (p[field] as string[]).filter((_, i) => i !== index) }))
  }

  const TagList = ({
    field, items, input, setInput, placeholder
  }: {
    field: keyof UserProfile
    items: string[]
    input: string
    setInput: (v: string) => void
    placeholder: string
  }) => (
    <div>
      <div className="flex flex-wrap gap-2 mb-2">
        {items.map((item, i) => (
          <span key={i} className="flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-full">
            {item}
            <button onClick={() => removeFrom(field, i)} className="hover:text-red-500">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addTo(field, input, setInput)}
          placeholder={placeholder}
          className="flex-1 px-3 py-1.5 border border-slate-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={() => addTo(field, input, setInput)}
          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-600 text-sm transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6 max-w-2xl">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">Settings</h1>
          <p className="text-slate-500 text-sm mt-0.5">Configure your search profile — scrapers use these daily.</p>
        </div>

        {/* Gmail Connection */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 mb-5">
          <h2 className="font-semibold text-slate-900 mb-1">Gmail Connection</h2>
          <p className="text-slate-500 text-sm mb-4">
            Connect Gmail to read your job alert emails from Naukri, LinkedIn, iimjobs, and others automatically.
          </p>

          {gmailConnected ? (
            <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">Gmail connected</p>
                {gmailConnectedAt && (
                  <p className="text-xs text-green-600">Last synced: {new Date(gmailConnectedAt).toLocaleDateString()}</p>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-3">
                <Mail className="w-4 h-4 flex-shrink-0" />
                <p className="text-sm">Gmail not connected — job alert emails won't be parsed.</p>
              </div>
              <p className="text-xs text-slate-400 mb-3">
                Sign out and sign back in with Google to grant Gmail access. Make sure to approve the Gmail permission when prompted.
              </p>
            </div>
          )}
        </div>

        {/* Search Profile */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
          <h2 className="font-semibold text-slate-900">Search Profile</h2>

          {/* Target Roles */}
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">
              Target Roles <span className="text-slate-400 font-normal">(keywords matched against job titles)</span>
            </label>
            <TagList
              field="target_roles"
              items={profile.target_roles || []}
              input={newRole}
              setInput={setNewRole}
              placeholder="e.g. research manager, team lead analytics"
            />
          </div>

          {/* Locations */}
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">
              Preferred Locations
            </label>
            <TagList
              field="locations"
              items={profile.locations || []}
              input={newLocation}
              setInput={setNewLocation}
              placeholder="e.g. Hyderabad, Bangalore, Remote, Dubai"
            />
          </div>

          {/* Salary + Experience */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">
                Salary Floor (LPA)
              </label>
              <input
                type="number"
                value={profile.salary_floor || 0}
                onChange={e => setProfile(p => ({ ...p, salary_floor: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. 25"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">
                Years of Experience
              </label>
              <input
                type="number"
                value={profile.experience_years || 0}
                onChange={e => setProfile(p => ({ ...p, experience_years: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g. 8"
              />
            </div>
          </div>

          {/* Industries */}
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">
              Industries <span className="text-slate-400 font-normal">(affects which category portals to scrape)</span>
            </label>
            <TagList
              field="industries"
              items={profile.industries || []}
              input={newIndustry}
              setInput={setNewIndustry}
              placeholder="e.g. BFSI, Consulting, KPO, Strategy"
            />
          </div>

          {/* Exclude Companies */}
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-2">
              Exclude Companies
            </label>
            <TagList
              field="exclude_companies"
              items={profile.exclude_companies || []}
              input={newExclude}
              setInput={setNewExclude}
              placeholder="e.g. Previous Company Ltd"
            />
          </div>

          {/* Save */}
          <button
            onClick={saveProfile}
            disabled={saving}
            className={clsx(
              'flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors',
              saved
                ? 'bg-green-600 text-white'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white',
              saving && 'opacity-70'
            )}
          >
            {saved ? (
              <><CheckCircle className="w-4 h-4" /> Saved!</>
            ) : (
              <><Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Profile'}</>
            )}
          </button>
        </div>
      </main>
    </div>
  )
}
