// Lightweight skeleton shown instantly (via loading.tsx) while a route's
// server data loads. Keeps the sidebar-width column so content doesn't jump.
export default function PageSkeleton({ title }: { title?: string }) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar placeholder (matches real Sidebar width) */}
      <aside className="w-56 min-h-screen bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 hidden sm:block" />

      <main className="flex-1 p-6">
        <div className="h-6 w-40 rounded bg-slate-200 dark:bg-slate-800 animate-pulse" />
        {title && <span className="sr-only">{title}</span>}
        <div className="mt-2 h-4 w-64 rounded bg-slate-100 dark:bg-slate-800/60 animate-pulse" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800/60 animate-pulse" />
          ))}
        </div>

        <div className="space-y-3 mt-6">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="h-24 rounded-xl bg-slate-100 dark:bg-slate-800/60 animate-pulse" />
          ))}
        </div>
      </main>
    </div>
  )
}
