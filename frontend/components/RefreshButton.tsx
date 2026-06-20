'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw, Check, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

type State = 'idle' | 'running' | 'done' | 'error'

export default function RefreshButton() {
  const router = useRouter()
  const [state, setState] = useState<State>('idle')
  const [msg, setMsg] = useState<string | null>(null)

  const trigger = async () => {
    setState('running')
    setMsg(null)
    try {
      const res = await fetch('/api/scrape', { method: 'POST' })
      const data = await res.json()
      if (data.ok) {
        setState('done')
        setMsg(data.message || 'Scraper started.')
        // Refresh server data shortly after, then again a bit later.
        setTimeout(() => router.refresh(), 8000)
        setTimeout(() => { router.refresh(); setState('idle') }, 30000)
      } else {
        setState('error')
        setMsg(data.error || 'Failed to start scraper.')
      }
    } catch (e: any) {
      setState('error')
      setMsg(e?.message || 'Network error.')
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={trigger}
        disabled={state === 'running'}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-60',
          state === 'error'
            ? 'bg-red-600 hover:bg-red-700 text-white'
            : state === 'done'
            ? 'bg-green-600 text-white'
            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
        )}
      >
        {state === 'running'
          ? <><RefreshCw className="w-4 h-4 animate-spin" /> Starting…</>
          : state === 'done'
          ? <><Check className="w-4 h-4" /> Started</>
          : state === 'error'
          ? <><AlertCircle className="w-4 h-4" /> Retry</>
          : <><RefreshCw className="w-4 h-4" /> Refresh Now</>}
      </button>
      {msg && (
        <span className={clsx(
          'text-xs max-w-xs text-right',
          state === 'error' ? 'text-red-600 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'
        )}>
          {msg}
        </span>
      )}
    </div>
  )
}
