'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import JobCard from '@/components/JobCard'
import { Job, ScraperHealth } from '@/lib/types'
import { Search, Filter, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import clsx from 'clsx'
import RefreshButton from '@/components/RefreshButton'

const SOURCES = [
  'All', 'workday', 'greenhouse', 'lever', 'iimjobs',
  'foundit', 'naukrigulf', 'instahyre', 'cutshort', 'gmail'
]

interface Props {
  initialJobs: Job[]
  newCount: number
  appliedCount: number
  scraperHealth: ScraperHealth[]
  userName: string
}

export default function DashboardClient({
  initialJobs, newCount, appliedCount, scraperHealth, userName
}: Props) {
  const [jobs, setJobs]           = useState<Job[]>(initialJobs)
  const [search, setSearch]       = useState('')
  const [sourceFilter, setSource] = useState('All')
  const [showNew, setShowNew]     = useState(false)
  const [showSaved, setShowSaved] = useState(false)

  const handleUpdate = (id: string, updates: Partial<Job>) => {
    setJobs(prev => prev.map(j => j.id === id ? { ...j, ...updates } : j))
  }

  const filtered = jobs.filter(job => {
    if (job.is_dismissed) return false
    if (showNew && !job.is_new) return false
    if (showSaved && !job.is_saved) return false
    if (sourceFilter !== 'All') {
      const src = job.source.startsWith('gmail') ? 'gmail' : job.source
      if (src !== sourceFilter) return false
    }
    if (search) {
      const q = search.toLowerCase()
      return (
        job.job_title.toLowerCase().includes(q) ||
        job.company.toLowerCase().includes(q) ||
        (job.location || '').toLowerCase().includes(q)
      )
    }
    return true
  })

  const errorCount = scraperHealth.filter(h => h.status === 'error').length
  const warnCount  = scraperHealth.filter(h => h.status === 'warning').length

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 p-6 max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Job Feed</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
              Welcome back, {userName.split(' ')[0]}. {newCount > 0 ? `${newCount} new jobs since last visit.` : 'All caught up!'}
            </p>
          </div>
          <RefreshButton />
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'New Today',  value: newCount,     color: 'text-indigo-600' },
            { label: 'Applied',    value: appliedCount, color: 'text-green-600'  },
            { label: 'In Feed',    value: filtered.length, color: 'text-slate-700' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
              <div className={clsx('text-2xl font-bold', color)}>{value}</div>
              <div className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{label}</div>
            </div>
          ))}
        </div>

        {/* Scraper health warning */}
        {(errorCount > 0 || warnCount > 0) && (
          <div className={clsx(
            'flex items-center gap-2 px-4 py-3 rounded-lg mb-4 text-sm',
            errorCount > 0 ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
          )}>
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {errorCount > 0
              ? `${errorCount} scraper${errorCount > 1 ? 's' : ''} failing — some sources may be missing.`
              : `${warnCount} scraper${warnCount > 1 ? 's' : ''} unstable — checking for issues.`
            }
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search title, company, location..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700
                         text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 rounded-lg text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Quick filters */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowNew(!showNew)}
              className={clsx(
                'px-3 py-2 rounded-lg text-xs font-medium border transition-colors',
                showNew
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-300'
              )}
            >
              New Only
            </button>
            <button
              onClick={() => setShowSaved(!showSaved)}
              className={clsx(
                'px-3 py-2 rounded-lg text-xs font-medium border transition-colors',
                showSaved
                  ? 'bg-amber-500 text-white border-amber-500'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-amber-300'
              )}
            >
              Saved
            </button>
          </div>
        </div>

        {/* Source filter pills */}
        <div className="flex gap-1.5 flex-wrap mb-5">
          {SOURCES.map(src => (
            <button
              key={src}
              onClick={() => setSource(src)}
              className={clsx(
                'px-2.5 py-1 rounded-full text-xs font-medium transition-colors border',
                sourceFilter === src
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-300'
              )}
            >
              {src === 'All' ? 'All Sources' : src}
            </button>
          ))}
        </div>

        {/* Job list */}
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No jobs match your filters</p>
            <p className="text-sm mt-1">Runs daily at 6am IST — or hit “Refresh Now” above</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(job => (
              <JobCard key={job.id} job={job} onUpdate={handleUpdate} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
