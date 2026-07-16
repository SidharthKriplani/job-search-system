'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, Search } from 'lucide-react'
import clsx from 'clsx'

export interface FacetOption { value: string; count: number }

/**
 * A compact multi-select dropdown for one facet (board / position / company /
 * location). Options + counts are dynamic (from /api/facets). Searchable when
 * the list is long (companies). Selection is a Set of values; onChange returns
 * the new selection so the parent can re-query the feed server-side.
 */
export default function FacetSelect({
  label, options, selected, onChange, searchable = false,
}: {
  label: string
  options: FacetOption[]
  selected: Set<string>
  onChange: (next: Set<string>) => void
  searchable?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  const shown = searchable && q
    ? options.filter(o => o.value.toLowerCase().includes(q.toLowerCase()))
    : options

  const toggle = (v: string) => {
    const next = new Set(selected)
    next.has(v) ? next.delete(v) : next.add(v)
    onChange(next)
  }

  const count = selected.size
  const disabled = options.length === 0

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => !disabled && setOpen(o => !o)}
        disabled={disabled}
        className={clsx(
          'flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-colors whitespace-nowrap',
          count > 0
            ? 'bg-indigo-600 text-white border-indigo-600'
            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-300',
          disabled && 'opacity-40 cursor-not-allowed'
        )}
      >
        {label}{count > 0 && ` · ${count}`}
        <ChevronDown className="w-3.5 h-3.5" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-60 max-h-72 overflow-hidden bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg flex flex-col">
          {searchable && (
            <div className="p-2 border-b border-slate-100 dark:border-slate-800 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                autoFocus value={q} onChange={e => setQ(e.target.value)}
                placeholder={`Search ${label.toLowerCase()}…`}
                className="w-full pl-7 pr-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded text-slate-900 dark:text-slate-100 focus:outline-none"
              />
            </div>
          )}
          {count > 0 && (
            <button onClick={() => onChange(new Set())}
              className="text-left px-3 py-1.5 text-xs text-indigo-600 dark:text-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800 border-b border-slate-100 dark:border-slate-800">
              Clear ({count})
            </button>
          )}
          <div className="overflow-y-auto">
            {shown.length === 0 ? (
              <p className="px-3 py-3 text-xs text-slate-400 text-center">No options</p>
            ) : shown.map(o => (
              <button key={o.value} onClick={() => toggle(o.value)}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-left">
                <span className={clsx('w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0',
                  selected.has(o.value) ? 'bg-indigo-600 border-indigo-600' : 'border-slate-300 dark:border-slate-600')}>
                  {selected.has(o.value) && <Check className="w-2.5 h-2.5 text-white" />}
                </span>
                <span className={clsx('flex-1 truncate', o.count === 0 && 'text-slate-400 dark:text-slate-500')}>{o.value}</span>
                <span className="text-slate-400 dark:text-slate-500 tabular-nums">{o.count === 0 ? '—' : o.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
