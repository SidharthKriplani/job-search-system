'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from '@/components/Sidebar'
import JobCard from '@/components/JobCard'
import { Job, ScraperHealth } from '@/lib/types'
import { Search, Filter, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import clsx from 'clsx'
import RefreshButton from '@/components/RefreshButton'

const DEFAULT_SOURCES = [
  'All', 'indeed', 'naukri', 'greenhouse', 'lever', 'ashby',
  'adzuna_in', 'remotive', 'gmail'
]

interface Props {
  initialJobs: Job[]
  newCount: number
  totalCount: number
  feedLimit: number
  appliedCount: number
  scraperHealth: ScraperHealth[]
  userName: string
  availableSources?: string[]
}

export default function DashboardClient({
  initialJobs, newCount, totalCount, feedLimit, appliedCount, scraperHealth, userName,
  availableSources,
}: Props) {
  const [jobs, setJobs]           = useState<Job[]>(initialJobs)
  const [search, setSearch]       = useState('')
  const [sourceFilter, setSource] = useState('All')
  const [showNew, setShowNew]     = useState(false)
  const [showSaved, setShowSaved] = useState(false)

  // Live counters (start from server, adjust as jobs leave the feed) so the stat
  // tiles stay honest without a full reload.
  const [nNew, setNNew]         = useState(newCount)
  const [nApplied, setNApplied] = useState(appliedCount)
  const [nTotal, setNTotal]     = useState(totalCount)

  // Server-driven query state: search/source/scope hit the DB (not just the
  // loaded slice), and "Load more" pages through everything.
  const [queryTotal, setQueryTotal] = useState(totalCount)
  const [loading, setLoading]       = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const scope = showNew ? 'new' : showSaved ? 'saved' : 'all'
  const isFiltered = !!search || sourceFilter !== 'All' || scope !== 'all'

  const SOURCES = availableSources && availableSources.length > 1 ? availableSources : DEFAULT_SOURCES

  const fetchPage = useCallback(async (offset: number): Promise<{ jobs: Job[]; total: number } | null> => {
    const p = new URLSearchParams({ q: search, source: sourceFilter, scope, offset: String(offset), limit: '50' })
    try {
      const r = await fetch(`/api/feed?${p.toString()}`, { cache: 'no-store' })
      const d = await r.json()
      if (!d.ok) return null
      return { jobs: d.jobs as Job[], total: d.total as number }
    } catch { return null }
  }, [search, sourceFilter, scope])

  // Re-query when search (debounced) / source / scope changes. Skip the very
  // first render — initialJobs already covers the default view.
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    setLoading(true)
    const t = setTimeout(async () => {
      const res = await fetchPage(0)
      if (res) { setJobs(res.jobs); setQueryTotal(res.total) }
      setLoading(false)
    }, search ? 300 : 0)   // debounce typing; instant for pill toggles
    return () => clearTimeout(t)
  }, [fetchPage, search])

  const loadMore = async () => {
    setLoadingMore(true)
    const res = await fetchPage(jobs.length)
    if (res) {
      setJobs(prev => [...prev, ...res.jobs])
      setQueryTotal(res.total)
    }
    setLoadingMore(false)
  }

  // Called the moment a manual Refresh finishes — re-pull the feed (and counts)
  // so new jobs appear immediately, no manual reload. Tries a couple of times in
  // case the DB write lands a beat after the run reports "completed".
  const reloadFeed = useCallback(async () => {
    setLoading(true)
    let res = await fetchPage(0)
    if (res && res.total === nTotal) {
      // Nothing new yet — give the DB write a moment and try once more.
      await new Promise(r => setTimeout(r, 2500))
      res = await fetchPage(0)
    }
    if (res) {
      setJobs(res.jobs)
      setQueryTotal(res.total)
      if (!isFiltered) setNTotal(res.total)
    }
    // Refresh the "New" tile from the server (a scrape doesn't change Applied).
    try {
      const n = await fetch('/api/feed?scope=new&limit=1', { cache: 'no-store' }).then(r => r.json())
      if (n?.ok) setNNew(n.total)
    } catch { /* best-effort */ }
    setLoading(false)
  }, [fetchPage, nTotal, isFiltered])

  const handleUpdate = (id: string, updates: Partial<Job>) => {
    const job = jobs.find(j => j.id === id)
    setJobs(prev => prev.map(j => j.id === id ? { ...j, ...updates } : j))
    // Adjust counters as a job leaves the feed (applied/dismissed).
    if (updates.is_applied || updates.is_dismissed) {
      setNTotal(t => Math.max(0, t - 1))
      setQueryTotal(t => Math.max(0, t - 1))
      if (job?.is_new) setNNew(n => Math.max(0, n - 1))
      if (updates.is_applied) setNApplied(n => n + 1)
    }
  }

  const filtered = jobs.filter(job => {
    if (job.is_dismissed) return false
    if (job.is_applied) return false   // applied jobs live in the tracker, not the feed
    return true
  })

  const errorCount = scraperHealth.filter(h => h.status === 'error').length
  const warnCount  = scraperHealth.filter(h => h.status === 'warning').length

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 max-w-4xl w-full px-4 pt-20 pb-24 md:p-6">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Job Feed</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
              Welcome back, {userName.split(' ')[0]}. {nNew > 0 ? `${nNew} new since your last visit.` : 'All caught up!'}
            </p>
          </div>
          <RefreshButton onDone={reloadFeed} />
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'New',     value: nNew,     color: 'text-indigo-600' },
            { label: 'Applied', value: nApplied, color: 'text-green-600'  },
            { label: 'In Feed', value: nTotal,   color: 'text-slate-700' },
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

          {/* Quick filters (mutually exclusive) */}
          <div className="flex gap-2">
            <button
              onClick={() => { setShowNew(!showNew); setShowSaved(false) }}
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
              onClick={() => { setShowSaved(!showSaved); setShowNew(false) }}
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
        {loading ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Clock className="w-8 h-8 mx-auto mb-3 opacity-30 animate-pulse" />
            <p className="text-sm">Searching your feed…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="font-medium">{isFiltered ? 'No jobs match these filters' : 'No jobs yet'}</p>
            <p className="text-sm mt-1">
              {isFiltered ? 'Try clearing the search or source filter.' : 'Runs daily at 6am IST — or hit “Refresh Now” above'}
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">
              Showing {filtered.length} of {queryTotal}{isFiltered ? ' matches' : ' matches, ranked by fit'}.
            </p>
            <div className="space-y-3">
              {filtered.map(job => (
                <JobCard key={job.id} job={job} onUpdate={handleUpdate} />
              ))}
            </div>
            {jobs.length < queryTotal && (
              <div className="text-center mt-5">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="px-5 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700
                             text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-60"
                >
                  {loadingMore ? 'Loading…' : `Load more (${queryTotal - jobs.length} left)`}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
