'use client'

import { useState } from 'react'
import { MapPin, DollarSign, Calendar, ExternalLink, Bookmark, X, CheckCircle } from 'lucide-react'
import { Job, SOURCE_LABELS } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import clsx from 'clsx'

interface Props {
  job: Job
  onUpdate?: (id: string, updates: Partial<Job>) => void
}

export default function JobCard({ job, onUpdate }: Props) {
  const supabase = createClient()
  const [saving, setSaving] = useState(false)
  const scorePct = Math.round((job.match_score || 0) * 100)
  const scoreColor =
    scorePct >= 70 ? 'bg-green-100 text-green-700' :
    scorePct >= 40 ? 'bg-amber-100 text-amber-700' :
                     'bg-slate-100 text-slate-500'

  const update = async (updates: Partial<Job>) => {
    setSaving(true)
    await supabase.from('job_feed').update(updates).eq('id', job.id)
    onUpdate?.(job.id, updates)
    setSaving(false)
  }

  const markApplied = () => update({ is_applied: true, is_new: false })
  const dismiss     = () => update({ is_dismissed: true })
  const toggleSave  = () => update({ is_saved: !job.is_saved })

  if (job.is_dismissed) return null

  return (
    <div className={clsx(
      'bg-white border rounded-xl p-4 transition-all hover:shadow-md',
      job.is_new ? 'border-indigo-200' : 'border-slate-200',
      job.is_applied && 'opacity-60'
    )}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Title + new badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={job.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-slate-900 hover:text-indigo-700 text-sm leading-snug"
            >
              {job.job_title}
            </a>
            {job.is_new && !job.is_applied && (
              <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">New</span>
            )}
            {job.is_applied && (
              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Applied
              </span>
            )}
          </div>

          {/* Company + source */}
          <p className="text-slate-700 text-sm font-medium mt-0.5">{job.company}</p>

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {job.location && (
              <span className="flex items-center gap-1 text-slate-500 text-xs">
                <MapPin className="w-3 h-3" /> {job.location}
              </span>
            )}
            {job.salary_range && (
              <span className="flex items-center gap-1 text-slate-500 text-xs">
                <DollarSign className="w-3 h-3" /> {job.salary_range}
              </span>
            )}
            {job.posted_date && (
              <span className="flex items-center gap-1 text-slate-400 text-xs">
                <Calendar className="w-3 h-3" /> {job.posted_date}
              </span>
            )}
            <span className="text-slate-400 text-xs">{SOURCE_LABELS[job.source] || job.source}</span>
          </div>

          {/* Match reasons */}
          {job.match_reasons?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {job.match_reasons.map(r => (
                <span key={r} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Score badge */}
        <div className={clsx('flex-shrink-0 px-2 py-1 rounded-lg text-xs font-bold', scoreColor)}>
          {scorePct}%
        </div>
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100">
        <a
          href={job.job_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700
                     text-white text-xs font-medium rounded-lg transition-colors"
        >
          <ExternalLink className="w-3 h-3" /> View Job
        </a>

        {!job.is_applied && (
          <button
            onClick={markApplied}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 hover:bg-green-100
                       text-green-700 text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            <CheckCircle className="w-3 h-3" /> Mark Applied
          </button>
        )}

        <button
          onClick={toggleSave}
          disabled={saving}
          className={clsx(
            'p-1.5 rounded-lg transition-colors disabled:opacity-50',
            job.is_saved
              ? 'bg-amber-100 text-amber-600 hover:bg-amber-200'
              : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
          )}
          title={job.is_saved ? 'Unsave' : 'Save'}
        >
          <Bookmark className="w-3.5 h-3.5" fill={job.is_saved ? 'currentColor' : 'none'} />
        </button>

        <button
          onClick={dismiss}
          disabled={saving}
          className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors disabled:opacity-50 ml-auto"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
