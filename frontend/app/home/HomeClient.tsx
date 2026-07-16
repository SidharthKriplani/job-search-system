'use client'

import { useMemo, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import { ArrowRight, TrendingUp } from 'lucide-react'

/**
 * Insights home. Chart method per the dataviz procedure: single-hue series
 * (indigo #4f46e5 light / #6366f1 dark — validator-passed on both surfaces),
 * 2px lines, 4px rounded bar ends anchored to the baseline, 2px gaps between
 * fills, recessive grid, text in slate ink (never series color), hover
 * tooltips on every plot, no legends (every chart is single-series and the
 * title names it).
 */

type Pt = { d: string; v: number }
type KV = { k?: string; source?: string; v: number }

const SERIES = 'fill-indigo-600 dark:fill-indigo-500'
const SERIES_STROKE = 'stroke-indigo-600 dark:stroke-indigo-500'

function Card({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</p>
      {sub && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{sub}</p>}
      <div className="mt-3">{children}</div>
    </div>
  )
}

/** Area+line with crosshair tooltip. Single series — no legend by design. */
function AreaChart({ data, fmt }: { data: Pt[]; fmt?: (n: number) => string }) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 560, H = 160, PAD = { l: 6, r: 6, t: 12, b: 20 }
  const f = fmt || ((n: number) => n.toLocaleString('en-IN'))
  const pts = useMemo(() => {
    if (!data?.length) return []
    const vs = data.map(p => p.v)
    const min = Math.min(...vs), max = Math.max(...vs)
    const span = max - min || 1
    return data.map((p, i) => ({
      x: PAD.l + (i * (W - PAD.l - PAD.r)) / Math.max(data.length - 1, 1),
      y: PAD.t + (1 - (p.v - min) / span) * (H - PAD.t - PAD.b),
      ...p,
    }))
  }, [data])
  if (!pts.length) return <p className="text-xs text-slate-400 py-8 text-center">No data yet — accrues from nightly runs.</p>

  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ')
  const area = `${line} L${pts[pts.length - 1].x},${H - PAD.b} L${pts[0].x},${H - PAD.b} Z`
  const hp = hover != null ? pts[hover] : null
  const last = pts[pts.length - 1]

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full"
           onMouseLeave={() => setHover(null)}
           onMouseMove={e => {
             const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
             const x = ((e.clientX - r.left) / r.width) * W
             let best = 0, bd = Infinity
             pts.forEach((p, i) => { const d = Math.abs(p.x - x); if (d < bd) { bd = d; best = i } })
             setHover(best)
           }}>
        {/* recessive grid: 3 horizontal lines */}
        {[0.25, 0.5, 0.75].map(t => (
          <line key={t} x1={PAD.l} x2={W - PAD.r}
                y1={PAD.t + t * (H - PAD.t - PAD.b)} y2={PAD.t + t * (H - PAD.t - PAD.b)}
                className="stroke-slate-100 dark:stroke-slate-800" strokeWidth="1" />
        ))}
        <path d={area} className={SERIES} opacity="0.12" />
        <path d={line} fill="none" className={SERIES_STROKE} strokeWidth="2" strokeLinejoin="round" />
        {/* direct label on the latest point (selective, not every point) */}
        <circle cx={last.x} cy={last.y} r="3" className={SERIES} />
        <text x={Math.min(last.x, W - 60)} y={Math.max(last.y - 8, 10)}
              className="fill-slate-500 dark:fill-slate-400" fontSize="10" textAnchor="end">{f(last.v)}</text>
        {/* crosshair */}
        {hp && <>
          <line x1={hp.x} x2={hp.x} y1={PAD.t} y2={H - PAD.b}
                className="stroke-slate-300 dark:stroke-slate-600" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx={hp.x} cy={hp.y} r="4" className={SERIES}
                  strokeWidth="2" style={{ stroke: 'var(--tw-ring-color, #fff)' }} />
        </>}
        {/* x labels: first + last date only */}
        <text x={PAD.l} y={H - 6} fontSize="10" className="fill-slate-400 dark:fill-slate-500">{data[0].d.slice(5)}</text>
        <text x={W - PAD.r} y={H - 6} fontSize="10" textAnchor="end" className="fill-slate-400 dark:fill-slate-500">{data[data.length - 1].d.slice(5)}</text>
      </svg>
      {hp && (
        <div className="absolute pointer-events-none px-2 py-1 rounded-md text-xs bg-slate-900 text-slate-100 dark:bg-slate-100 dark:text-slate-900 shadow"
             style={{ left: `${(hp.x / W) * 100}%`, top: 0, transform: 'translate(-50%,-110%)' }}>
          <span className="opacity-70">{hp.d}</span> · <span className="font-semibold">{f(hp.v)}</span>
        </div>
      )}
    </div>
  )
}

/** Daily bars with per-bar hover. 4px rounded tops, 2px gaps, baseline-anchored. */
function BarChart({ data, fmt }: { data: Pt[]; fmt?: (n: number) => string }) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 560, H = 140, PAD = { l: 6, r: 6, t: 10, b: 20 }
  const f = fmt || ((n: number) => n.toLocaleString('en-IN'))
  if (!data?.length) return <p className="text-xs text-slate-400 py-8 text-center">No data yet — accrues from nightly runs.</p>
  const max = Math.max(...data.map(p => p.v), 1)
  const bw = Math.max((W - PAD.l - PAD.r) / data.length - 2, 2)   // 2px gap between fills
  const hp = hover != null ? data[hover] : null
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" onMouseLeave={() => setHover(null)}>
        {data.map((p, i) => {
          const h = Math.max((p.v / max) * (H - PAD.t - PAD.b), 1.5)
          const x = PAD.l + i * ((W - PAD.l - PAD.r) / data.length)
          return (
            <g key={p.d}>
              {/* invisible full-height hit target, wider than the mark */}
              <rect x={x} y={PAD.t} width={bw + 2} height={H - PAD.t - PAD.b} fill="transparent"
                    onMouseEnter={() => setHover(i)} />
              <rect x={x} y={H - PAD.b - h} width={bw} height={h} rx="3"
                    className={SERIES} opacity={hover === i ? 1 : 0.85} />
            </g>
          )
        })}
        <text x={PAD.l} y={H - 6} fontSize="10" className="fill-slate-400 dark:fill-slate-500">{data[0].d.slice(5)}</text>
        <text x={W - PAD.r} y={H - 6} fontSize="10" textAnchor="end" className="fill-slate-400 dark:fill-slate-500">{data[data.length - 1].d.slice(5)}</text>
      </svg>
      {hp && hover != null && (
        <div className="absolute pointer-events-none px-2 py-1 rounded-md text-xs bg-slate-900 text-slate-100 dark:bg-slate-100 dark:text-slate-900 shadow"
             style={{ left: `${((PAD.l + (hover + 0.5) * ((W - PAD.l - PAD.r) / data.length)) / W) * 100}%`, top: 0, transform: 'translate(-50%,-110%)' }}>
          <span className="opacity-70">{hp.d}</span> · <span className="font-semibold">{f(hp.v)}</span>
        </div>
      )}
    </div>
  )
}

/** Labeled horizontal bar list — identity via the row label, magnitude via one hue. */
function HBarList({ items, linkPrefix }: { items: KV[]; linkPrefix?: string }) {
  if (!items?.length) return <p className="text-xs text-slate-400 py-6 text-center">No data yet.</p>
  const max = Math.max(...items.map(i => i.v), 1)
  return (
    <div className="space-y-1.5">
      {items.map(it => {
        const label = it.k ?? it.source ?? '?'
        const row = (
          <div className="group grid grid-cols-[7rem_1fr_3.5rem] items-center gap-2" title={`${label}: ${it.v.toLocaleString('en-IN')}`}>
            <span className="text-xs text-slate-600 dark:text-slate-300 truncate">{label}</span>
            <div className="h-3.5 rounded-r-[4px] bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div className="h-full rounded-r-[4px] bg-indigo-600 dark:bg-indigo-500 group-hover:opacity-100 opacity-85 transition-opacity"
                   style={{ width: `${Math.max((it.v / max) * 100, 1.5)}%` }} />
            </div>
            <span className="text-xs tabular-nums text-slate-500 dark:text-slate-400 text-right">{it.v.toLocaleString('en-IN')}</span>
          </div>
        )
        return linkPrefix
          ? <Link key={label} href={`${linkPrefix}${encodeURIComponent(label)}`} className="block hover:bg-slate-50 dark:hover:bg-slate-800/60 rounded px-1 -mx-1">{row}</Link>
          : <div key={label}>{row}</div>
      })}
    </div>
  )
}

export default function HomeClient({ userName, newCount, feedCount, savedCount, appliedTotal, funnel, insights }: {
  userName: string
  newCount: number; feedCount: number; savedCount: number; appliedTotal: number
  funnel: Record<string, number>
  insights: any
}) {
  const poolCurve: Pt[]  = insights.pool_curve || []
  const addedCurve: Pt[] = insights.added_curve || []
  const sources: KV[]    = (insights.sources || []).slice(0, 12)
  const topCos: KV[]     = insights.top_companies || []
  const topPos: KV[]     = insights.top_positions || []
  const funnelItems: KV[] = Object.entries(funnel).map(([k, v]) => ({ k, v: v as number }))

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 max-w-5xl w-full px-4 pt-20 pb-24 md:p-6">
        <div className="mb-6 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Home</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">
              Welcome back, {userName.split(' ')[0]}. Here's your market at a glance.
            </p>
          </div>
          <Link href="/dashboard"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors">
            Open feed <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Personal stat tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'New for you', value: newCount },
            { label: 'In your feed', value: feedCount },
            { label: 'Saved', value: savedCount },
            { label: 'Applications', value: appliedTotal },
          ].map(t => (
            <div key={t.label} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 tabular-nums">{t.value.toLocaleString('en-IN')}</div>
              <div className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">{t.label}</div>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <Card title="Job pool over time"
                sub={`All sources combined · ${Number(insights.pool_total || 0).toLocaleString('en-IN')} jobs tracked today`}>
            <AreaChart data={poolCurve} />
          </Card>
          <Card title="Jobs added per night" sub="Fresh postings ingested by the nightly runs">
            <BarChart data={addedCurve} />
          </Card>
          <Card title="Where the jobs come from" sub="Latest run, per source">
            <HBarList items={sources} />
          </Card>
          <Card title="Top hiring companies" sub="Most open roles seen this week — click to filter your feed">
            <HBarList items={topCos} linkPrefix="/dashboard?company=" />
          </Card>
          <Card title="Hot roles this week" sub="Most-posted role buckets across the market">
            <HBarList items={topPos} />
          </Card>
          <Card title="Your application funnel" sub="Where your applications stand">
            {appliedTotal === 0
              ? <p className="text-xs text-slate-400 py-6 text-center">
                  Nothing tracked yet — hit <span className="font-medium">Mark Applied</span> on a job to start the funnel.
                </p>
              : <HBarList items={funnelItems} />}
          </Card>
        </div>

        <p className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 mt-6">
          <TrendingUp className="w-3.5 h-3.5" />
          Repost-rate and skill-density insights appear here as the new tracking accrues data (started {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}).
        </p>
      </main>
    </div>
  )
}
