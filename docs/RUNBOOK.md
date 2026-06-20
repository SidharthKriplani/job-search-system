# RUNBOOK — operations & troubleshooting

How to deploy, run, and fix the things we've already hit.

## Architecture (one diagram)

```
GitHub Actions (daily 6am IST / 00:30 UTC, or manual / "Refresh Now")
  └─ python main.py
       ├─ ingest.collect_jobs()      ← ATS APIs (Greenhouse/Lever/Ashby) + aggregators   [once per run]
       ├─ per user: + Gmail parse → filter_and_score → dedup → upsert_jobs → digest
       └─ writes scraper_health
Supabase (Postgres + Auth + RLS): user_profiles, gmail_tokens, job_feed,
  applications, referral_pipeline, message_templates, contacts, scraper_health
Vercel (Next.js): /dashboard /applications /referrals /settings  + /api/scrape[/status]
```

## Run the scraper

- **Manual (UI):** dashboard → **Refresh Now** (needs `GITHUB_DISPATCH_TOKEN`).
- **Manual (GitHub):** repo → Actions → Daily Job Scraper → Run workflow.
- **Local:** set env vars, then `python main.py`.
- **Engine only (no DB):** `python -m ingest.run` — prints source counts + samples.

## Deploy

- **Frontend:** push to `main` → Vercel auto-builds. Env-var changes need a manual
  **Redeploy** (Deployments → ⋯ → Redeploy).
- **Backend:** there's no separate deploy — GitHub Actions runs `main.py` from `main`.

## Environment variables

GitHub Actions secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `RESEND_API_KEY`, `NEXT_PUBLIC_APP_URL`, and optional
`ADZUNA_APP_ID` / `ADZUNA_APP_KEY`.

Vercel: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`GITHUB_DISPATCH_TOKEN` (fine-grained PAT, Actions: read & write on the repo).

## First-time go-live (do once, in order)

1. Push the latest code.
2. Run `supabase/schema.sql` in the Supabase SQL editor (idempotent; creates +
   backfills `user_profiles`).
3. Disable email confirmation: Supabase → Auth → Providers → Email (so signups
   don't get stuck).
4. Fill in Settings (roles, locations, salary floor).
5. Trigger a run; confirm jobs land in the dashboard.

## Troubleshooting (things we've hit)

**Run crashes: `TypeError: Client.__init__() got an unexpected keyword 'proxy'`**
→ Supabase dependency inconsistency. Fixed by upgrading to `supabase==2.31.0` +
matching deps in `requirements.txt`. Do NOT downgrade or pin httpx below 0.26
(older httpx lacks the `proxy` param that supabase-auth passes — that's what
causes this exact error). To re-verify any change, construct `create_client` with
a JWT-shaped key (a plain fake key short-circuits before the httpx init).

**Run logs `Active users: 0` (and 0 jobs)**
→ No `user_profiles` row. Run `supabase/schema.sql` (it backfills existing
auth users), and make sure the user's profile `is_active = true`.

**Run succeeds but very few / no jobs in the feed**
→ Coverage gap, not a bug. The registry is US-tech-heavy; `filter_and_score`
drops jobs that don't match the profile's target roles. Fix: add relevant
companies to `ingest/registry.py` and/or enable Adzuna for India + broaden the
profile.

**"Refresh Now" says "Scrape trigger not configured"**
→ Add `GITHUB_DISPATCH_TOKEN` in Vercel and **redeploy**.

**Digest email never arrives**
→ Resend requires a verified sender domain. Set `DIGEST_FROM_EMAIL` to a verified
domain (or use `onboarding@resend.dev` for testing). Does not block the dashboard.

**Schema re-run errors on "policy already exists"**
→ Shouldn't happen anymore — `schema.sql` is idempotent (drops policies/triggers
before recreating). If you edited it, keep that pattern.

## Add a company to the feed (one line)

In `ingest/registry.py`, append `(slug, "Display Name")` under the right ATS:
- Greenhouse → `boards.greenhouse.io/<slug>`
- Lever → `jobs.lever.co/<slug>`
- Ashby → `jobs.ashbyhq.com/<slug>`

A dead slug returns 0 jobs (shown in the run summary) — it never crashes.
