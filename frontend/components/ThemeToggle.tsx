'use client'

import { useEffect, useState } from 'react'
import { Sun, Moon } from 'lucide-react'

export default function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [dark, setDark] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    setDark(document.documentElement.classList.contains('dark'))
  }, [])

  const toggle = () => {
    const next = !dark
    setDark(next)
    const root = document.documentElement
    if (next) root.classList.add('dark')
    else root.classList.remove('dark')
    try { localStorage.setItem('theme', next ? 'dark' : 'light') } catch {}
  }

  // Avoid hydration mismatch: render a stable placeholder until mounted.
  if (compact) {
    return (
      <button
        onClick={toggle}
        aria-label="Toggle dark mode"
        className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700
                   dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
      >
        {mounted && dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </button>
    )
  }

  return (
    <button
      onClick={toggle}
      aria-label="Toggle dark mode"
      className="flex items-center gap-2.5 px-3 py-2 w-full rounded-lg text-sm font-medium
                 text-slate-500 hover:bg-slate-50 hover:text-slate-700
                 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
    >
      {mounted && dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      {mounted && dark ? 'Light Mode' : 'Dark Mode'}
    </button>
  )
}
