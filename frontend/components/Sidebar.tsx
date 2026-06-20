'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import {
  LayoutDashboard, Briefcase, Users, Settings,
  LogOut, Zap
} from 'lucide-react'
import clsx from 'clsx'
import ThemeToggle from './ThemeToggle'

const NAV = [
  { href: '/dashboard',     label: 'Job Feed',     icon: LayoutDashboard },
  { href: '/applications',  label: 'Applications', icon: Briefcase },
  { href: '/referrals',     label: 'Referrals',    icon: Users },
  { href: '/settings',      label: 'Settings',     icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router   = useRouter()
  const supabase = createClient()

  const signOut = async () => {
    await supabase.auth.signOut()
    router.push('/')
  }

  return (
    <aside className="w-56 min-h-screen bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-5 border-b border-slate-100 dark:border-slate-800">
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-slate-800 dark:text-slate-100 text-sm">Job Search</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Theme + Sign out */}
      <div className="p-3 border-t border-slate-100 dark:border-slate-800 space-y-0.5">
        <ThemeToggle />
        <button
          onClick={signOut}
          className="flex items-center gap-2.5 px-3 py-2 w-full rounded-lg text-sm
                     font-medium text-slate-500 hover:bg-slate-50 hover:text-slate-700
                     dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
