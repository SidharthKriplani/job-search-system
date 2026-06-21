# RUNBOOK — operations & troubleshooting

How to deploy, run, and fix the things we've already hit.

**Local repo path:** `~/Documents/Professional/BreakLabs/career-os/job-search-system`
_(moved 2026-06-22 from `…/GitHub/upskill platforms (4)/job-search-system`)._

## Architecture (one diagram)

```
GitHub Actions
  ├─ daily.yml   (cron window / manual / "Refresh Now")  → python main.py  [full scrape]
  ├─ resync.yml  (on profile save via /api/resync)        → python main.py [RESYNC_ONLY=1, no scrape]
  └─ harvest.yml (weekly)                                  → ingest.harvester  [refresh company lists]
  main.py:
       ├─ ingest.collect_jobs()      ← ATS APIs (Greenhouse/Lever/Ashby/Workday) + aggregators  [once]
       ├─ per user: deep-copy pool + Gmail → filter_and_score (role graph + sector) → dedup → upsert → resync → digest
       └─ writes scraper_health
Supabase (Postgres + Auth + RLS): user_profiles, gmail_tokens, job_feed,
  applications, referral_pipeline, message_templates, contacts, scraper_health
Vercel (Next.js): /dashboard /applications /referrals /settings
  + /api/scrape[/status]  /api/resync  /api/feed (server-side search/pagination)
Relevance: utils/role_graph.py (Python, source of truth) ↔ frontend/lib/roleGraph.ts
  (read-guard mirror — keep roughly in sync).
```

## Run the scraper

- **Manual (UI):** dashboard → **Refresh Now** (needs `GITHUB_DISPATCH_TOKEN`).
  On completion the feed auto-reloads (no manual refresh).
- **Manual (GitHub):** repo → Actions → Daily Job Scraper → Run workflow.
- **Local:** set env vars, then `python main.py`.
- **Resync only (no scrape):** `RESYNC_ONLY=1 TARGET_USER_ID=<uuid> python main.py`
  — re-filters a user's stored feed to their current profile. Fired automatically
  on profile save via `/api/resync` → `resync.yml`.
- **Engine only (no DB):** `python -m ingest.run` — prints source counts + samples.

## Tests & CI (the safety gate)

The thing that catches regressions before you (or prod) do.

- **Run locally before every push:** `./scripts/check.sh` (pytest + frontend tsc).
- **CI:** `.github/workflows/ci.yml` runs the same on every push/PR — `pytest`
  (matching engine) + `tsc --noEmit` (the exact check Vercel fails on). If CI is
  red, the change is broken — fix it before promoting.
- **Tests live in `tests/`** and lock in the bugs we already fixed (investment
  banker ≠ engineers, salary INR parsing, India-default, null-profile crash,
  résumé-drives-search, seniority ranking, back-office family). Add a test
  whenever you fix a bug so it can't come back.

## Staging discipline (catch the deploy gap)

Most "works in code, broken on screen" pain is the gap between a correct commit
and the live app. Close it with branch → preview → promote:

1. Work on a branch (e.g. `dev`), not `main`.
2. Push it → CI runs, and **Vercel auto-builds a Preview URL** (separate from prod).
3. Click through the preview; confirm the actual behaviour.
4. Only then merge `dev` → `main` (which deploys to production).

DB changes: ideally a **separate Supabase project for staging** so migrations are
tested before prod (recommended, not yet set up). Until then, `schema.sql` is
idempotent/additive, so re-running on prod is low-risk — but run it on staging
first once that exists.

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
   backfills `user_profiles`, tightens RLS, adds unique indexes). **Re-run it
   whenever you pull schema changes** — it de-dupes existing rows first.
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
→ Usually coverage, not a bug. `filter_and_score` drops jobs that don't match the
role neighbourhood, and now also drops clearly-foreign non-remote jobs by default
(India-focused, D11). So e.g. "investment banker" can be honestly near-empty until
India finance sources are added. Fix: add companies to `ingest/registry.py`,
enable Adzuna India, and add India finance feeds. To see whether it's coverage vs
a filter bug, run `python -m ingest.run` (raw counts, no filter).

**Vercel build fails: "Type 'Set' can only be iterated … target 'es2015' or higher"**
→ `frontend/tsconfig.json` must have `"target": "es2017"` + `"downlevelIteration": true`
(D15). Without a target it defaults to ES5 and rejects Set/Map iteration. To catch
this BEFORE pushing: `cd frontend && npm install && npx tsc --noEmit`.

**A specific user sees an empty feed while others are fine**
→ Was a crash on NULL profile fields (`target_roles`/`industries`/`locations`) for
users whose row was created by the signup trigger (those columns NULL). Fixed with
`or []` guards in `filter_and_score` (CHANGELOG 06-22 (c)). If it recurs, check the
run log for a per-user exception (main.py catches and continues).

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
