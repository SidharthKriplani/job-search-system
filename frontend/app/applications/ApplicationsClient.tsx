'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import { Application, ApplicationStage, STAGE_COLORS } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import { Plus, ExternalLink, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

// Defined once at module level — used by both the main component and AppCard
const ALL_STAGES: ApplicationStage[] = [
  'Not Applied', 'Applied', 'Application Acknowledged', 'Recruiter Screening',
  'HM Interview Scheduled', 'HM Interview Done', 'Technical Round Scheduled',
  'Technical Round Done', 'Case Study / Assignment', 'Final Round Scheduled',
  'Final Round Done', 'Reference Check', 'Background Check', 'Offer Verbal',
  'Offer Written', 'Offer Negotiating', 'Offer Accepted', 'Rejected', 'Withdrawn', 'Ghosted',
]

const STAGE_GROUPS: { label: string; stages: ApplicationStage[] }[] = [
  { label: 'Sourcing',      stages: ['Not Applied'] },
  { label: 'Applied',       stages: ['Applied', 'Application Acknowledged'] },
  { label: 'Screening',     stages: ['Recruiter Screening'] },
  {
    label: 'Interviewing',
    stages: [
      'HM Interview Scheduled', 'HM Interview Done',
      'Technical Round Scheduled', 'Technical Round Done',
      'Case Study / Assignment', 'Final Round Scheduled', 'Final Round Done',
    ],
  },
  {
    label: 'Offer',
    stages: ['Reference Check', 'Background Check', 'Offer Verbal', 'Offer Written', 'Offer Negotiating', 'Offer Accepted'],
  },
  { label: 'Closed', stages: ['Rejected', 'Withdrawn', 'Ghosted'] },
]

interface Props {
  initialApplications: Application[]
  userId: string
}

export default function ApplicationsClient({ initialApplications, userId }: Props) {
  const supabase = createClient()
  const [apps, setApps]           = useState<Application[]>(initialApplications)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newApp, setNewApp]       = useState<Partial<Application>>({ stage: 'Not Applied', priority: 'medium' })
  const [saving, setSaving]       = useState(false)

  const updateStage = async (id: string, stage: ApplicationStage) => {
    await supabase
      .from('applications')
      .update({ stage, date_stage_updated: new Date().toISOString().split('T')[0] })
      .eq('id', id)
    setApps(prev => prev.map(a => a.id === id ? { ...a, stage } : a))
  }

  const addApplication = async () => {
    if (!newApp.company || !newApp.job_title) return
    setSaving(true)
    const { data } = await supabase
      .from('applications')
      .insert({
        ...newApp,
        user_id: userId,
        date_applied: newApp.date_applied || new Date().toISOString().split('T')[0],
      })
      .select()
      .single()
    if (data) setApps(prev => [data as Application, ...prev])
    setNewApp({ stage: 'Not Applied', priority: 'medium' })
    setShowAddModal(false)
    setSaving(false)
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Applications</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">{apps.length} total · 18-stage tracker</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Application
          </button>
        </div>

        {/* Stage groups */}
        <div className="space-y-6">
          {STAGE_GROUPS.map(group => {
            const groupApps = apps.filter(a => (group.stages as string[]).includes(a.stage))
            if (groupApps.length === 0) return null
            return (
              <div key={group.label}>
                <div className="flex items-center gap-2 mb-2">
                  <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{group.label}</h2>
                  <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs rounded-full">
                    {groupApps.length}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {groupApps.map(app => (
                    <AppCard key={app.id} app={app} onStageChange={updateStage} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {apps.length === 0 && (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <p className="font-medium">No applications yet</p>
            <p className="text-sm mt-1">Add one manually or click "Mark Applied" on a job card</p>
          </div>
        )}
      </main>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 border border-transparent dark:border-slate-800 rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="font-bold text-lg text-slate-900 dark:text-slate-100 mb-4">Add Application</h2>
            <div className="space-y-3">
              {([
                { key: 'job_title', label: 'Job Title', required: true },
                { key: 'company',   label: 'Company',   required: true },
                { key: 'job_url',   label: 'Job URL',   required: false },
                { key: 'location',  label: 'Location',  required: false },
              ] as { key: keyof Application; label: string; required: boolean }[]).map(({ key, label, required }) => (
                <div key={String(key)}>
                  <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1 block">
                    {label}{required && ' *'}
                  </label>
                  <input
                    type="text"
                    value={(newApp[key] as string) || ''}
                    onChange={e => setNewApp(p => ({ ...p, [key]: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg text-sm
                               focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              ))}
              <div>
                <label className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1 block">Stage</label>
                <select
                  value={newApp.stage}
                  onChange={e => setNewApp(p => ({ ...p, stage: e.target.value as ApplicationStage }))}
                  className="w-full px-3 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-lg text-sm
                             focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {ALL_STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={addApplication}
                disabled={saving || !newApp.company || !newApp.job_title}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm
                           font-medium rounded-lg disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── AppCard ─────────────────────────────────────────────────────────────────

function AppCard({
  app,
  onStageChange,
}: {
  app: Application
  onStageChange: (id: string, stage: ApplicationStage) => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate">{app.job_title}</p>
          <p className="text-slate-600 dark:text-slate-400 text-xs mt-0.5">{app.company}</p>
        </div>
        <span className={clsx(
          'text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 whitespace-nowrap',
          STAGE_COLORS[app.stage]
        )}>
          {app.stage}
        </span>
      </div>

      {app.location && (
        <p className="text-slate-400 text-xs mt-2">{app.location}</p>
      )}
      {app.follow_up_date && (
        <p className="text-xs text-amber-600 mt-1.5">Follow-up: {app.follow_up_date}</p>
      )}

      <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800">
        {app.job_url && (
          <a
            href={app.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-indigo-600 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}

        {/* Stage quick-change */}
        <div className="relative ml-auto">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
          >
            Move stage <ChevronDown className="w-3 h-3" />
          </button>
          {open && (
            <div className="absolute right-0 top-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-10
                            max-h-48 overflow-y-auto w-52">
              {ALL_STAGES.map(s => (
                <button
                  key={s}
                  onClick={() => { onStageChange(app.id, s); setOpen(false) }}
                  className={clsx(
                    'w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors',
                    s === app.stage && 'font-semibold text-indigo-600 dark:text-indigo-400'
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
