'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { Lock, Eye, EyeOff } from 'lucide-react'

export default function ResetPassword() {
  const supabase = createClient()
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [ready, setReady]       = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [done, setDone]         = useState(false)

  // The recovery link puts a session in place; confirm we have one.
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setReady(!!data.session))
  }, [supabase])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    setLoading(true); setError(null)
    const { error } = await supabase.auth.updateUser({ password })
    setLoading(false)
    if (error) { setError(error.message); return }
    setDone(true)
    setTimeout(() => { window.location.href = '/dashboard' }, 1500)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-4">
      <div className="w-full max-w-md px-8 py-10 bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl shadow-2xl">
        <div className="flex items-center gap-2 mb-6">
          <Lock className="w-5 h-5 text-indigo-400" />
          <h1 className="text-white font-bold text-lg">Set your password</h1>
        </div>

        {done ? (
          <p className="text-green-400 text-sm">Password set. Taking you to your dashboard…</p>
        ) : !ready ? (
          <p className="text-slate-400 text-sm">
            Open this page from the “set password” link in your email. If you got here directly,
            request a new link from the sign-in page.
          </p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-slate-400 text-xs">Choose a password — you can then sign in with email too (Google still works).</p>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="New password"
                className="w-full px-3 py-2.5 bg-white/10 border border-white/10 text-white placeholder-slate-500 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {error && <p className="text-red-400 text-xs">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm disabled:opacity-60">
              {loading ? 'Saving…' : 'Set password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
