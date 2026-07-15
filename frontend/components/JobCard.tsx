'use client'

import { useState } from 'react'
import { MapPin, DollarSign, Calendar, Clock, Briefcase, BarChart3, ExternalLink, Bookmark, X, CheckCircle, ThumbsDown } from 'lucide-react'
import { Job, SOURCE_LABELS } from '@/lib/types'
import { createClient } from '@/lib/supabase'
import clsx from 'clsx'

interface Props {
  job: Job
  onUpdate?: (id: string, updates: Partial<Job>) => void
}

// Relative age, e.g. "today", "3d ago", "2w ago".
function timeAgo(dateStr: string | null): { label: string; stale: boolean } | null {
  if (!dateStr) return null
  const then = new Date(dateStr).getTime()
  if (isNaN(then)) return null
  const days = Math.floor((Date.now() - then) / 86400000)
  if (days < 0) return null
  const label =
    days === 0 ? 'today'
    : days === 1 ? 'yesterday'
    : days < 7 ? `${days}d ago`
    : days < 30 ? `${Math.floor(days / 7)}w ago`
    : `${Math.floor(days / 30)}mo ago`
  return { label, stale: days > 21 }
}

function prettyType(t: string | null): string | null {
  if (!t) return null
  const map: Record<string, string> = {
    full_time: 'Full-time', part_time: 'Part-time', contract: 'Contract', internship: 'Internship',
  }
  return map[t] || null
}

const FEEDBACK_REASONS: { key: string; label: string }[] = [
  { key: 'wrong_role',      label: 'Wrong role' },
  { key: 'wrong_location',  label: 'Wrong location' },
  { key: 'wrong_seniority', label: 'Wrong seniority' },
  { key: 'wrong_company',   label: 'Company not for me' },
  { key: 'stale',           label: 'Posting looks dead' },
  { key: 'other',           label: 'Other' },
]

export default function JobCard({ job, onUpdate }: Props) {
  const supabase = createClient()
  const [saving, setSaving] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
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

  // Mark applied: flag the feed row AND create a tracker row so the job flows
  // into the application tracker. Guarded against double-fire + duplicate rows.
  const markApplied = async () => {
    if (saving || job.is_applied) return  // ignore repeat clicks / already applied
    await update({ is_applied: true, is_new: false })
    try {
      const { data: existing } = await supabase
        .from('applications')
        .select('id')
        .eq('job_feed_id', job.id)
        .limit(1)
      if (existing && existing.length > 0) return
      await supabase.from('applications').insert({
        user_id:      job.user_id,
        job_feed_id:  job.id,
        company:      job.company,
        job_title:    job.job_title,
        job_url:      job.job_url,
        location:     job.location,
        source:       job.source,
        stage:        'Applied',
        date_applied: new Date().toISOString().split('T')[0],
      })
    } catch {
      /* tracker insert is best-effort; the feed flag already succeeded */
    }
  }
  const dismiss     = () => update({ is_dismissed: true })
  const toggleSave  = () => update({ is_saved: !job.is_saved })

  // "Not relevant" = dismiss + record WHY. The reasons are the raw signal for
  // tuning the matcher (role graph weights, location rules, seniority fit).
  const notRelevant = async (reason: string) => {
    setShowFeedback(false)
    try {
      await supabase.from('feed_feedback').insert({
        user_id:     job.user_id,
        job_id:      job.id,
        job_title:   job.job_title,
        company:     job.company,
        source:      job.source,
        match_score: job.match_score,
        reason,
      })
    } catch { /* feedback is best-effort; the dismiss below still applies */ }
    await update({ is_dismissed: true })
  }

  if (job.is_dismissed) return null

  return (
    <div className={clsx(
      'bg-white dark:bg-slate-900 border rounded-xl p-4 transition-all hover:shadow-md dark:hover:shadow-black/40',
      job.is_new ? 'border-indigo-200 dark:border-indigo-500/30' : 'border-slate-200 dark:border-slate-800',
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
              className="font-semibold text-slate-900 dark:text-slate-100 hover:text-indigo-700 dark:hover:text-indigo-400 text-sm leading-snug"
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
          <p className="text-slate-700 dark:text-slate-300 text-sm font-medium mt-0.5">{job.company}</p>

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
            {(() => {
              const age = timeAgo(job.posted_date)
              return age ? (
                <span className={clsx(
                  'flex items-center gap-1 text-xs',
                  age.stale ? 'text-amber-600 dark:text-amber-500' : 'text-slate-400 dark:text-slate-500'
                )}>
                  <Clock className="w-3 h-3" /> {age.label}
                </span>
              ) : null
            })()}
            {prettyType(job.job_type) && (
              <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500 text-xs">
                <Briefcase className="w-3 h-3" /> {prettyType(job.job_type)}
              </span>
            )}
            {job.seniority && (
              <span className="flex items-center gap-1 text-slate-400 dark:text-slate-500 text-xs capitalize">
                <BarChart3 className="w-3 h-3" /> {job.seniority}
              </span>
            )}
            <span className="text-slate-400 dark:text-slate-500 text-xs">{SOURCE_LABELS[job.source] || job.source}</span>
          </div>

          {/* Match reasons */}
          {job.match_reasons?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {job.match_reasons.map((r, i) => (
                <span key={`${r}-${i}`} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs rounded">
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
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
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

        <div className="relative ml-auto flex items-center gap-1">
          <button
            onClick={() => setShowFeedback(v => !v)}
            disabled={saving}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 transition-colors disabled:opacity-50"
            title="Not relevant — tell us why"
          >
            <ThumbsDown className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={dismiss}
            disabled={saving}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 transition-colors disabled:opacity-50"
            title="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>

          {showFeedback && (
            <div className="absolute right-0 bottom-8 z-10 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1">
              <p className="px-3 py-1 text-xs font-medium text-slate-400 dark:text-slate-500">Not relevant because…</p>
              {FEEDBACK_REASONS.map(r => (
                <button
                  key={r.key}
                  onClick={() => notRelevant(r.key)}
                  className="w-full text-left px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  {r.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
