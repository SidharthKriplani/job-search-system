'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw, Check, AlertCircle, ExternalLink, Coffee } from 'lucide-react'
import clsx from 'clsx'

type State = 'idle' | 'running' | 'done' | 'error'

// A typical end-to-end run (queue + full scrape + filter + upsert + embeddings)
// lands around here — measured from real production runs, not hoped. The bar
// eases toward 95% by this point and snaps to 100% only on true completion.
const EXPECTED_SEC = 600 // ~10 min
// Absolute polling cap. If a run exceeds this we stop polling but KEEP the
// button disabled-looking state honest via the status text + log link.
const MAX_POLL_MS = 30 * 60_000

function fmt(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function RefreshButton({ onDone }: { onDone?: () => void | Promise<void> }) {
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

  // Attach to an ALREADY-RUNNING run (started by a previous click, another tab,
  // or the nightly cron) — with elapsed time taken from the run itself. This is
  // what stops a page reload from offering a second concurrent refresh.
  const attach = (runStartedAt?: string | null, url?: string | null) => {
    stop()
    const startMs = runStartedAt ? new Date(runStartedAt).getTime() : Date.now()
    startedRef.current = startMs
    if (url) setRunUrl(url)
    setState('running')
    setElapsed(Math.max(0, Math.floor((Date.now() - startMs) / 1000)))
    setStatusText('Attached to the running scrape…')
    timerRef.current = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedRef.current) / 1000)),
      1000
    )
    pollRef.current = setInterval(poll, 5000)
    setTimeout(poll, 1500)
    setTimeout(() => {
      if (pollRef.current) {
        stop()
        setState('error')
        setStatusText('Run exceeded 30 min — open the log to see why.')
      }
    }, MAX_POLL_MS)
  }

  // On mount: if a run is already active, attach instead of sitting idle.
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/scrape/status', { cache: 'no-store' })
        const d = await r.json()
        if (d.ok && (d.status === 'in_progress' || d.status === 'queued')) {
          attach(d.run_started_at || d.created_at, d.html_url)
        }
      } catch { /* fine — stay idle */ }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
          setStatusText('Completed — loading new jobs…')
          // Pull the fresh feed into view immediately (no manual reload). Fall
          // back to a server refresh if no handler was provided.
          if (onDone) { Promise.resolve(onDone()).then(() => setStatusText('Feed updated.')) }
          else router.refresh()
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
      if (res.status === 409 && data.alreadyRunning) {
        // A run is already going — attach to IT rather than erroring or
        // (worse) starting a duplicate.
        attach(data.run_started_at, data.html_url)
        return
      }
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
      // Poll until ACTUAL completion (capped) — never flip back to idle while
      // the backend is still running; that invites a duplicate refresh.
      setTimeout(() => {
        if (pollRef.current) {
          stop()
          setState('error')
          setStatusText('Run exceeded 30 min — open the log to see why.')
        }
      }, MAX_POLL_MS)
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
    <div className="flex flex-col items-end gap-1.5 w-full sm:w-60">
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
                  ? `Full scrape takes ~10 min — about ${fmt(remaining)} to go (estimate).`
                  : 'Wrapping up — waiting for the run to confirm…'}
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
