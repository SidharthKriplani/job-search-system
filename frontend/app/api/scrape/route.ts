import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Manually trigger the daily scraper (GitHub Actions `daily.yml`) from the UI.
 *
 * The scraper lives in GitHub Actions, so the only way to start it from the
 * browser is GitHub's workflow_dispatch API. That requires a token.
 *
 * Required Vercel env vars:
 *   GITHUB_DISPATCH_TOKEN  — a fine-grained PAT with "Actions: read & write"
 *                            on the job-search-system repo (keep secret, no
 *                            NEXT_PUBLIC_ prefix).
 * Optional (sensible defaults):
 *   GITHUB_REPO_OWNER      — default "SidharthKriplani"
 *   GITHUB_REPO_NAME       — default "job-search-system"
 *   GITHUB_WORKFLOW_FILE   — default "daily.yml"
 *   GITHUB_DEFAULT_BRANCH  — default "main"
 *   ADMIN_EMAILS           — comma list exempt from the cooldown
 *                            (default "sidharthkriplani@gmail.com")
 *   REFRESH_COOLDOWN_HOURS — non-admin manual-refresh cooldown (default 12)
 */
export async function POST() {
  // 1. Require an authenticated user.
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })
  }

  // 1b. Rate-limit manual refresh (repeated scraping is wasteful). Admins exempt.
  const adminEmails = (process.env.ADMIN_EMAILS || 'sidharthkriplani@gmail.com')
    .split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
  const isAdmin = !!user.email && adminEmails.includes(user.email.toLowerCase())
  const cooldownH = Number(process.env.REFRESH_COOLDOWN_HOURS || 12)
  if (!isAdmin) {
    const { data: prof } = await supabase
      .from('user_profiles').select('last_manual_refresh').eq('user_id', user.id).maybeSingle()
    const lastMs = prof?.last_manual_refresh ? new Date(prof.last_manual_refresh).getTime() : 0
    if (lastMs && (Date.now() - lastMs) < cooldownH * 3600_000) {
      const nextAt = new Date(lastMs + cooldownH * 3600_000)
      return NextResponse.json({
        ok: false,
        error: `You've already refreshed recently. Next manual refresh around ${nextAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}. The feed also updates automatically overnight.`,
      }, { status: 429 })
    }
  }

  // 2. Read config.
  const token = process.env.GITHUB_DISPATCH_TOKEN
  if (!token) {
    return NextResponse.json(
      { ok: false, error: 'Scrape trigger not configured. Add GITHUB_DISPATCH_TOKEN in Vercel env vars.' },
      { status: 503 }
    )
  }
  const owner    = process.env.GITHUB_REPO_OWNER   || 'SidharthKriplani'
  const repo     = process.env.GITHUB_REPO_NAME    || 'job-search-system'
  const workflow = process.env.GITHUB_WORKFLOW_FILE || 'daily.yml'
  const branch   = process.env.GITHUB_DEFAULT_BRANCH || 'main'

  // 3. Fire workflow_dispatch.
  try {
    const resp = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: branch, inputs: { debug: 'false' } }),
      }
    )

    // GitHub returns 204 No Content on success.
    if (resp.status === 204) {
      // Stamp the cooldown clock (best-effort; don't fail the request if it errors).
      try {
        await supabase.from('user_profiles')
          .update({ last_manual_refresh: new Date().toISOString() })
          .eq('user_id', user.id)
      } catch { /* ignore */ }
      return NextResponse.json({ ok: true, message: 'Scraper started. Jobs usually appear within 2–3 minutes — reload then.' })
    }

    const text = await resp.text()
    return NextResponse.json(
      { ok: false, error: `GitHub responded ${resp.status}: ${text.slice(0, 200)}` },
      { status: 502 }
    )
  } catch (err: any) {
    return NextResponse.json({ ok: false, error: err?.message || 'Request failed' }, { status: 500 })
  }
}
