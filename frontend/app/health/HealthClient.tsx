'use client'

import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import Sidebar from '@/components/Sidebar'
import clsx from 'clsx'

interface HealthRow {
  id: string
  source: string
  last_run_at: string | null
  last_success_at: string | null
  last_job_count: number | null
  consecutive_failures: number | null
  last_error: string | null
  status: 'ok' | 'warning' | 'error' | null
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'never'
  const mins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000)
  if (isNaN(mins) || mins < 0) return 'never'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 48) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const STATUS_META = {
  ok:      { icon: CheckCircle,   cls: 'text-green-600 dark:text-green-500',  label: 'OK' },
  warning: { icon: AlertTriangle, cls: 'text-amber-600 dark:text-amber-500',  label: 'Warning' },
  error:   { icon: XCircle,       cls: 'text-red-600 dark:text-red-500',      label: 'Error' },
} as const

export default function HealthClient({ rows, prev = {} }: { rows: HealthRow[]; prev?: Record<string, number> }) {
  const failing = rows.filter(r => r.status === 'error').length

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8 max-w-4xl">
        <div className="flex items-center gap-2 mb-1">
          <Activity className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Scraper Health</h1>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          {rows.length === 0
            ? 'No health data yet — populates after the first scraper run.'
            : failing > 0
              ? `${failing} source${failing > 1 ? 's' : ''} failing — the feed may be missing their jobs.`
              : 'All sources healthy.'}
        </p>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Last run</th>
                <th className="px-4 py-3 font-medium text-right">Jobs</th>
                <th className="px-4 py-3 font-medium text-right">Trend</th>
                <th className="px-4 py-3 font-medium">Last error</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const meta = STATUS_META[r.status || 'ok'] || STATUS_META.ok
                const Icon = meta.icon
                return (
                  <tr key={r.id} className="border-b border-slate-50 dark:border-slate-800/50 last:border-0">
                    <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200 capitalize">{r.source}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('flex items-center gap-1.5 text-xs font-medium', meta.cls)}>
                        <Icon className="w-3.5 h-3.5" /> {meta.label}
                        {(r.consecutive_failures || 0) > 1 && ` (×${r.consecutive_failures})`}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">{timeAgo(r.last_run_at)}</td>
                    <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300 tabular-nums">
                      {r.last_job_count ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-xs tabular-nums">
                      {(() => {
                        const p = prev[r.source]
                        const c = r.last_job_count
                        if (p === undefined || c === null || c === undefined) return <span className="text-slate-300 dark:text-slate-600">—</span>
                        const d = c - p
                        if (d === 0) return <span className="text-slate-400">=</span>
                        return <span className={d > 0 ? 'text-green-600 dark:text-green-500' : 'text-amber-600 dark:text-amber-500'}>{d > 0 ? '▲' : '▼'} {Math.abs(d)}</span>
                      })()}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 max-w-[16rem] truncate" title={r.last_error || undefined}>
                      {r.last_error || '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
