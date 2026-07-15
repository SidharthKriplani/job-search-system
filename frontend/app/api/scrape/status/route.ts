import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

/**
 * Returns the status of the most recent daily.yml workflow run, so the UI can
 * show live progress (queued → in_progress → completed) instead of a blind wait.
 * Uses the same GITHUB_DISPATCH_TOKEN as the trigger route.
 */
export async function GET() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ ok: false, error: 'Not authenticated' }, { status: 401 })
  }

  const token = process.env.GITHUB_DISPATCH_TOKEN
  if (!token) {
    return NextResponse.json({ ok: false, error: 'Not configured' }, { status: 503 })
  }
  const owner    = process.env.GITHUB_REPO_OWNER    || 'SidharthKriplani'
  const repo     = process.env.GITHUB_REPO_NAME     || 'job-search-system'
  const workflow = process.env.GITHUB_WORKFLOW_FILE || 'daily.yml'

  try {
    const gh = (qs: string) => fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/runs?${qs}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
        cache: 'no-store',
      }
    )
    // Prefer an ACTIVE run (in_progress, then queued) so the UI can attach to
    // it even after a page reload; fall back to the most recent run.
    let run: any = null
    for (const st of ['in_progress', 'queued']) {
      const r = await gh(`status=${st}&per_page=1`)
      if (r.ok) { run = ((await r.json()).workflow_runs || [])[0]; if (run) break }
    }
    if (!run) {
      const resp = await gh('per_page=1')
      if (!resp.ok) {
        return NextResponse.json({ ok: false, error: `GitHub ${resp.status}` }, { status: 502 })
      }
      run = (((await resp.json()).workflow_runs) || [])[0]
    }
    if (!run) {
      return NextResponse.json({ ok: true, status: 'none' })
    }
    return NextResponse.json({
      ok: true,
      status: run.status,            // queued | in_progress | completed
      conclusion: run.conclusion,    // success | failure | cancelled | null
      html_url: run.html_url,
      created_at: run.created_at,
      run_started_at: run.run_started_at,
    })
  } catch (err: any) {
    return NextResponse.json({ ok: false, error: err?.message || 'Request failed' }, { status: 500 })
  }
}
