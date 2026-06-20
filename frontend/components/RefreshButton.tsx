'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw, Check, AlertCircle, ExternalLink, Coffee } from 'lucide-react'
import clsx from 'clsx'

type State = 'idle' | 'running' | 'done' | 'error'

// A typical end-to-end run (queue + scrape + filter) lands around here. The bar
// eases toward this ceiling but never claims 100% until the run actually finishes,
// so the estimate guiding the user is honest about being an estimate.
const EXPECTED_SEC = 210 // ~3.5 min

function fmt(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function RefreshButton() {
  const router = useRouter()
  const [state, setState] = useState<State>('idle')
  const [statusText, setStatusText] = useState<string | null>(null)
  const [runUrl, setRunUrl] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)

  const startedRef = useRef(0)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stop = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (timerRef.current) clearInterval(timerRef.current)
    pollRef.current = null
    timerRef.current = null
  }
  useEffect(() => stop, [])

  const poll = async () => {
    try {
      const r = await fetch('/api/scrape/status', { cache: 'no-store' })
      const d = await r.json()
      if (!d.ok) return
      if (d.html_url) setRunUrl(d.html_url)

      // Is this run ours? (created at/after we clicked, minus a small buffer)
      const created = d.created_at ? new Date(d.created_at).getTime() : 0
      const ours = created >= startedRef.current - 30000

      if (!ours || d.status === 'none') {
        setStatusText('Queued — waiting for the run to start…')
        return
      }
      if (d.status === 'completed') {
        stop()
        if (d.conclusion === 'success') {
          setState('done')
          setStatusText('Completed — refreshing your feed…')
          router.refresh()
          setTimeout(() => { setState('idle'); setStatusText(null) }, 6000)
        } else {
          setState('error')
          setStatusText(`Run ${d.conclusion || 'failed'} — open the log to see why`)
        }
      } else {
        setStatusText(d.status === 'queued' ? 'Queued…' : 'Running the scraper…')
      }
    } catch {
      /* transient — keep polling */
    }
  }

  const trigger = async () => {
    stop()
    setState('running')
    setRunUrl(null)
    setElapsed(0)
    setStatusText('Starting run…')
    startedRef.current = Date.now()
    try {
      const res = await fetch('/api/scrape', { method: 'POST' })
      const data = await res.json()
      if (!data.ok) {
        setState('error')
        setStatusText(data.error || 'Failed to start scraper.')
        return
      }
      timerRef.current = setInterval(
        () => setElapsed(Math.floor((Date.now() - startedRef.current) / 1000)),
        1000
      )
      pollRef.current = setInterval(poll, 5000)
      setTimeout(poll, 2500) // first check quickly
      // Safety cap: stop after 6 minutes
      setTimeout(() => {
        if (pollRef.current) {
          stop()
          setState('idle')
          setStatusText('Still running — check the run log if jobs don’t appear.')
        }
      }, 360000)
    } catch (e: any) {
      setState('error')
      setStatusText(e?.message || 'Network error.')
    }
  }

  const label =
    state === 'running' ? `Running ${fmt(elapsed)}`
    : state === 'done'  ? 'Done'
    : state === 'error' ? 'Retry'
    : 'Refresh Now'

  const Icon =
    state === 'running' ? <RefreshCw className="w-4 h-4 animate-spin" />
    : state === 'done'  ? <Check className="w-4 h-4" />
    : state === 'error' ? <AlertCircle className="w-4 h-4" />
    : <RefreshCw className="w-4 h-4" />

  // Eased progress: fast at first, asymptotes toward 95% by EXPECTED_SEC, then
  // snaps to 100% only when the run truly completes.
  const pct =
    state === 'done'    ? 100
    : state === 'running' ? Math.min(95, Math.round((1 - Math.exp(-elapsed / (EXPECTED_SEC / 2.5))) * 100))
    : 0
  const remaining = Math.max(0, EXPECTED_SEC - elapsed)

  return (
    <div className="flex flex-col items-end gap-1.5 w-60">
      <button
        onClick={trigger}
        disabled={state === 'running'}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-80 self-end',
          state === 'error' ? 'bg-red-600 hover:bg-red-700 text-white'
          : state === 'done' ? 'bg-green-600 text-white'
          : 'bg-indigo-600 hover:bg-indigo-700 text-white'
        )}
      >
        {Icon}
        {label}
      </button>

      {(state === 'running' || state === 'done') && (
        <div className="w-full">
          <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all duration-700 ease-out',
                state === 'done' ? 'bg-green-500' : 'bg-indigo-500'
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          {state === 'running' && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-slate-500 dark:text-slate-400">
              <Coffee className="w-3.5 h-3.5 flex-shrink-0" />
              <span>
                {remaining > 30
                  ? `Good time for a coffee — about ${fmt(remaining)} left.`
                  : 'Almost there — finishing up…'}
              </span>
            </div>
          )}
        </div>
      )}

      {statusText && (
        <div className="flex items-center gap-2 text-xs max-w-xs text-right">
          <span className={clsx(state === 'error' ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400')}>
            {statusText}
          </span>
          {runUrl && (
            <a
              href={runUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap"
            >
              run log <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}
    </div>
  )
}
