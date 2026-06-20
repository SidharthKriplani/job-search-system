import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Trigger a fast, scrape-free RESYNC of the signed-in user's feed against their
 * current profile (GitHub Actions `resync.yml`). Called right after the user
 * saves Settings, so changing the target role re-matches the existing feed in
 * ~30–60s instead of waiting for the full 2–3 min scrape.
 *
 * Reuses the same GITHUB_DISPATCH_TOKEN / repo env as /api/scrape. No cooldown:
 * resync does no scraping, so it's cheap to run on every save.
 */
export async function POST() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })
  }

  const token = process.env.GITHUB_DISPATCH_TOKEN
  if (!token) {
    // Resync is best-effort; the next scrape will reconcile anyway.
    return NextResponse.json(
      { ok: false, error: 'Resync not configured (GITHUB_DISPATCH_TOKEN missing).' },
      { status: 503 }
    )
  }
  const owner    = process.env.GITHUB_REPO_OWNER    || 'SidharthKriplani'
  const repo     = process.env.GITHUB_REPO_NAME     || 'job-search-system'
  const branch   = process.env.GITHUB_DEFAULT_BRANCH || 'main'

  try {
    const resp = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/resync.yml/dispatches`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: branch, inputs: { user_id: user.id } }),
      }
    )
    if (resp.status === 204) {
      return NextResponse.json({ ok: true, message: 'Re-matching your feed…' })
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
