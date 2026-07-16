'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from '@/components/Sidebar'
import JobCard from '@/components/JobCard'
import { Job, ScraperHealth } from '@/lib/types'
import { Search, Filter, AlertCircle, CheckCircle, Clock, Bookmark, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import RefreshButton from '@/components/RefreshButton'
import FacetSelect, { FacetOption } from '@/components/FacetSelect'

interface Props {
  initialJobs: Job[]
  newCount: number
  totalCount: number
  feedLimit: number
  appliedCount: number
  scraperHealth: ScraperHealth[]
  userName: string
  availableSources?: string[]
  needsProfile?: boolean
}

export default function DashboardClient({
  initialJobs, newCount, totalCount, feedLimit, appliedCount, scraperHealth, userName,
  availableSources, needsProfile,
}: Props) {
  const [jobs, setJobs]           = useState<Job[]>(initialJobs)
  const [search, setSearch]       = useState('')
  const [showNew, setShowNew]     = useState(false)
  const [showSaved, setShowSaved] = useState(false)

  // Facet filters (server-side, multi-select) + sort.
  const [fPosition, setFPosition] = useState<Set<string>>(new Set())
  const [fCompany,  setFCompany]  = useState<Set<string>>(new Set())
  const [fLocation, setFLocation] = useState<Set<string>>(new Set())
  const [fBoard,    setFBoard]    = useState<Set<string>>(new Set())
  const [sort, setSort]           = useState<'relevance' | 'date' | 'added'>('relevance')
  const [facets, setFacets]       = useState<{ positions: FacetOption[]; companies: FacetOption[]; locations: FacetOption[]; boards: FacetOption[] }>(
    { positions: [], companies: [], locations: [], boards: [] })
  const [saved, setSaved_]        = useState<any[]>([])
  const [showSavedMenu, setShowSavedMenu] = useState(false)
  const savedMenuRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!showSavedMenu) return
    const onDoc = (e: MouseEvent) => {
      if (savedMenuRef.current && !savedMenuRef.current.contains(e.target as Node)) setShowSavedMenu(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [showSavedMenu])

  const loadSaved = useCallback(async () => {
    try {
      const d = await fetch('/api/saved-searches', { cache: 'no-store' }).then(r => r.json())
      if (d.ok) setSaved_(d.searches)
    } catch { /* ignore */ }
  }, [])
  useEffect(() => { loadSaved() }, [loadSaved])

  const saveCurrentSearch = async () => {
    const parts = [
      search, ...Array.from(fPosition), ...Array.from(fLocation),
      ...Array.from(fBoard), ...Array.from(fCompany),
    ].filter(Boolean)
    const name = parts.slice(0, 3).join(' · ') || 'All jobs'
    const filters = {
      q: search,
      board: Array.from(fBoard), position: Array.from(fPosition),
      company: Array.from(fCompany), location: Array.from(fLocation),
    }
    await fetch('/api/saved-searches', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, filters }),
    })
    loadSaved()
  }

  const applySaved = (sv: any) => {
    const f = sv.filters || {}
    setSearch(f.q || '')
    setFBoard(new Set(f.board || [])); setFPosition(new Set(f.position || []))
    setFCompany(new Set(f.company || [])); setFLocation(new Set(f.location || []))
    setShowSavedMenu(false)
  }

  const deleteSaved = async (id: string) => {
    await fetch(`/api/saved-searches?id=${id}`, { method: 'DELETE' })
    loadSaved()
  }

  // Load dynamic filter options once (and after a refresh brings new jobs).
  const loadFacets = useCallback(async () => {
    try {
      const d = await fetch('/api/facets', { cache: 'no-store' }).then(r => r.json())
      if (d.ok) setFacets({ positions: d.positions, companies: d.companies, locations: d.locations, boards: d.boards || [] })
    } catch { /* non-blocking */ }
  }, [])
  useEffect(() => { loadFacets() }, [loadFacets])

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
  const isFiltered = !!search || scope !== 'all' || fPosition.size > 0 || fCompany.size > 0 || fLocation.size > 0 || fBoard.size > 0

  const boardOptions: FacetOption[] = facets.boards.length
    ? facets.boards
    : (availableSources || []).filter(x => x !== 'All').map(v => ({ value: v, count: 0 }))

  const fetchPage = useCallback(async (offset: number): Promise<{ jobs: Job[]; total: number } | null> => {
    const p = new URLSearchParams({ q: search, scope, sort, offset: String(offset), limit: '50' })
    if (fBoard.size)    p.set('board',    Array.from(fBoard).join(','))
    if (fPosition.size) p.set('position', Array.from(fPosition).join(','))
    if (fCompany.size)  p.set('company',  Array.from(fCompany).join(','))
    if (fLocation.size) p.set('location', Array.from(fLocation).join(','))
    try {
      const r = await fetch(`/api/feed?${p.toString()}`, { cache: 'no-store' })
      const d = await r.json()
      if (!d.ok) return null
      return { jobs: d.jobs as Job[], total: d.total as number }
    } catch { return null }
  }, [search, scope, sort, fPosition, fCompany, fLocation, fBoard])

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
    }, search ? 300 : 0)   // debounce typing; instant for pill/facet toggles
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
    loadFacets()
    setLoading(false)
  }, [fetchPage, nTotal, isFiltered, loadFacets])

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
    // In the Saved view, un-saving a job should drop it from the list + count.
    if (scope === 'saved' && updates.is_saved === false) {
      setJobs(prev => prev.filter(j => j.id !== id))
      setQueryTotal(t => Math.max(0, t - 1))
    }
  }

  const filtered = jobs.filter(job => {
    if (job.is_dismissed) return false
    if (job.is_applied) return false   // applied jobs live in the tracker, not the feed
    return true
  })

  const errorCount = scraperHealth.filter(h => h.status === 'error').length
  const warnCount  = scraperHealth.filter(h => h.status === 'warning').length

  // No profile yet → guide setup instead of dumping the whole job database.
  if (needsProfile) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 max-w-4xl w-full px-4 pt-20 pb-24 md:p-6">
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-6">Job Feed</h1>
          <div className="text-center py-20 px-6 border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl">
            <Search className="w-10 h-10 mx-auto mb-4 text-slate-300 dark:text-slate-600" />
            <p className="font-semibold text-slate-800 dark:text-slate-100">Tell us what you're looking for</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1.5 max-w-md mx-auto">
              Your feed is personalised to your roles — so we don't flood you with everything.
              Upload your résumé (we'll detect your roles &amp; level), or add target roles in Settings.
            </p>
            <a href="/settings"
               className="inline-flex items-center gap-2 mt-5 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors">
              Go to Settings →
            </a>
          </div>
        </main>
      </div>
    )
  }

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

        {/* Facet filters + sort */}
        <div className="flex gap-2 flex-wrap items-center mb-5">
          <FacetSelect label="Board"    options={boardOptions}     selected={fBoard}    onChange={setFBoard} searchable />
          <FacetSelect label="Position" options={facets.positions} selected={fPosition} onChange={setFPosition} />
          <FacetSelect label="Company"  options={facets.companies} selected={fCompany}  onChange={setFCompany} searchable />
          <FacetSelect label="Location" options={facets.locations} selected={fLocation} onChange={setFLocation} />
          {(fPosition.size || fCompany.size || fLocation.size || fBoard.size) > 0 && (
            <button
              onClick={() => { setFBoard(new Set()); setFPosition(new Set()); setFCompany(new Set()); setFLocation(new Set()) }}
              className="text-xs text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 underline"
            >
              Clear filters
            </button>
          )}
          {isFiltered && (
            <button onClick={saveCurrentSearch}
              className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
              <Bookmark className="w-3.5 h-3.5" /> Save search
            </button>
          )}
          {saved.length > 0 && (
            <div className="relative" ref={savedMenuRef}>
              <button onClick={() => setShowSavedMenu(v => !v)}
                className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-indigo-600">
                <Bookmark className="w-3.5 h-3.5" /> Saved ({saved.length})
              </button>
              {showSavedMenu && (
                <div className="absolute z-20 mt-1 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1">
                  {saved.map(sv => (
                    <div key={sv.id} className="flex items-center gap-1 px-1">
                      <button onClick={() => applySaved(sv)}
                        className="flex-1 text-left px-2 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 rounded truncate">
                        {sv.name}
                      </button>
                      <button onClick={() => deleteSaved(sv.id)} title="Delete"
                        className="p-1.5 text-slate-400 hover:text-red-500">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                  <p className="px-3 pt-1.5 pb-1 text-[10px] text-slate-400 border-t border-slate-100 dark:border-slate-800 mt-1">
                    You'll get these in your daily email when new jobs match.
                  </p>
                </div>
              )}
            </div>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            <span className="text-xs text-slate-400 dark:text-slate-500">Sort</span>
            <select
              value={sort}
              onChange={e => setSort(e.target.value as 'relevance' | 'date' | 'added')}
              className="px-2.5 py-2 rounded-lg text-xs font-medium bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="relevance">Best match</option>
              <option value="date">Date posted</option>
              <option value="added">Recently added</option>
            </select>
          </div>
        </div>

        {/* Job list */}
        {loading ? (
          <div className="text-center py-16 text-slate-400 dark:text-slate-500">
            <Clock className="w-8 h-8 mx-auto mb-3 opacity-30 animate-pulse" />
            <p className="text-sm">Searching your feed…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 px-6 text-slate-400 dark:text-slate-500">
            <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
            {isFiltered ? (
              <>
                <p className="font-medium text-slate-600 dark:text-slate-300">No jobs match these filters</p>
                <p className="text-sm mt-1">Try clearing the search or source filter.</p>
              </>
            ) : (
              <>
                <p className="font-medium text-slate-600 dark:text-slate-300">No jobs match your roles yet</p>
                {errorCount > 0 ? (
                  <p className="text-sm mt-1.5 max-w-md mx-auto">
                    <strong>{errorCount} data source{errorCount > 1 ? 's are' : ' is'} currently failing</strong> —
                    that may be why the feed is empty, not your profile.
                    Check <a href="/health" className="text-indigo-600 dark:text-indigo-400 hover:underline">Health</a> before
                    changing your roles.
                  </p>
                ) : (
                  <p className="text-sm mt-1.5 max-w-md mx-auto">
                    We haven't found roles matching your profile in our current sources.
                    Niche / front-office roles (e.g. investment banking, consulting) mostly come from
                    <strong> Naukri &amp; iimjobs</strong> — connect Gmail in Settings to pull those alerts.
                    Or broaden your target roles.
                  </p>
                )}
                <a href="/settings" className="inline-block mt-4 text-indigo-600 dark:text-indigo-400 text-sm hover:underline">
                  Adjust roles / connect Gmail →
                </a>
              </>
            )}
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">
              Showing {filtered.length} of {queryTotal} matches{sort === 'date' ? ', newest posting first' : sort === 'added' ? ', newest in your feed first' : ', ranked by fit'}.
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
