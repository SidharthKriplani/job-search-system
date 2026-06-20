# STATUS — current state

_Last updated: 2026-06-20_

The single source of truth for where the project is **right now**. Update this
after every meaningful change.

## Capabilities built to date (the journey)

- **M1 ✅ Jobs live** — durable ingestion engine; first real feed (4,359 jobs).
- **Data foundation** — ATS-source engine (Greenhouse/Lever/Ashby/**Workday**) +
  **JobSpy** (all-India: Indeed/Naukri) + aggregators (Remotive/Arbeitnow/Adzuna)
  + user Gmail. No fragile portal scraping. ~70 verified ATS boards + 5 Workday
  tenants + JobSpy.
- **M2 🟡 Relevance** — India companies seeded; profile-driven filtering; Adzuna
  India ready (needs keys).
- **M3 ✅ Scoring** — JD-aware, profile-driven, **prefix-stem** matching
  (science≈scientist), with human-readable reasons; scores spread meaningfully.
- **M4 🟡 Intelligence** — Stage 1 done: résumé capture + free heuristic résumé
  matching. Stage 2 (LLM) deferred.
- **Frontend** — dark mode, fast nav, live "Refresh Now" run-status, job-age +
  metadata cards, résumé box in Settings.
- **Reliability** — idempotent schema; deps fixed (supabase 2.31); loud upsert
  errors; project spine in `docs/`.
- **Scaling plan** — `docs/SCALING.md` (staged); **building now:** concurrent +
  sharded ingestion (Stage 1).

## At a glance

| | |
|---|---|
| **Live app** | https://job-search-system-zeta.vercel.app |
| **Repo** | https://github.com/SidharthKriplani/job-search-system (branch `main`) |
| **Supabase** | project `dnczgcrgaczjhinrplpy` (ap-southeast-1) |
| **Hosting** | Vercel (frontend, auto-deploys on push) · GitHub Actions (daily scraper) |
| **Phase** | Foundation built & proven. **Go-live in progress** — not yet producing real jobs on screen. |

## What works

- **Ingestion engine** (`ingest/`) — proven live: one run pulled **4,309 deduped
  jobs** from Greenhouse + Lever + Ashby + aggregators, zero credentials, zero
  scraping. This is the durable data foundation.
- **Frontend** — deployed with dark mode, faster navigation (parallel queries +
  loading skeletons), and a **live "Refresh Now"** button that triggers the
  GitHub run and shows real status (queued → running → done/failed + log link).
- **Auth** — Google OAuth + email/password via Supabase. Sign-in → dashboard works.
- **Pipeline code** — `main.py` fetches the shared pool once, filters per user,
  upserts, sends digest. Verified end-to-end in a sandbox with mocked Supabase.

## What's blocking "jobs on screen"

The scraper run must succeed AND have somewhere to write AND a profile to match.
Resolved and outstanding:

- ✅ **Dependency crash** (`httpx 'proxy'` TypeError) — fixed by **upgrading** the
  Supabase stack to `supabase==2.31.0` (verified: client constructs + all our
  queries work). _(An earlier pin to httpx 0.25.2 was backwards and is corrected.)_
- ⬜ **Schema not confirmed applied.** `supabase/schema.sql` is now idempotent and
  creates/backfills `user_profiles`. **Must be re-run once** in the Supabase SQL
  editor. Until then the run likely reports `Active users: 0`.
- ⬜ **Profile not filled.** Even with a profile row, Settings (target roles,
  locations, salary floor) should be set so matching is meaningful.
- ⚠️ **Coverage gap (expected).** The company registry is currently US-tech-heavy
  (Stripe, Databricks, Ramp…). A finance/India-targeted profile will match few of
  those. Fix later: seed finance/India companies + enable Adzuna India.

## Env / secrets checklist

GitHub Actions secrets (repo → Settings → Secrets → Actions):

| Secret | Needed for | Status |
|--------|-----------|--------|
| `SUPABASE_URL` | scraper DB | set (client constructed in CI) |
| `SUPABASE_SERVICE_KEY` | scraper DB (service role) | set |
| `GOOGLE_CLIENT_ID` / `_SECRET` | Gmail parse | set |
| `RESEND_API_KEY` | digest email | set (sender domain unverified — email won't send yet) |
| `NEXT_PUBLIC_APP_URL` | email links | ⚠️ verify it's the `-zeta` URL |
| `ADZUNA_APP_ID` / `_KEY` | India + salary breadth | optional, **not set** |

Vercel env vars:

| Var | Needed for | Status |
|-----|-----------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` / `_ANON_KEY` | frontend | set |
| `GITHUB_DISPATCH_TOKEN` | "Refresh Now" button | **set** (button works) |

## Immediate next steps (in order)

1. Confirm `requirements.txt` + `main.py` deps fix is pushed; re-run the workflow.
2. Read the run log. If `Active users: 0` → run `supabase/schema.sql`.
3. Fill in Settings profile.
4. Re-run → confirm jobs appear in the dashboard.
5. Then: address coverage (registry + Adzuna) and start the intelligence layer.

## Known issues / debt

- `scraper_health` is global (per-source), not per-user — counts can over-state
  failures with multiple users. Low impact.
- `is_new` never resets → "New Today" counts all un-applied jobs, not today's.
- No scraper-health UI yet (table exists, dashboard shows only a banner).
- Legacy `scrapers/` HTML portal modules remain in the repo but are **out of the
  pipeline** (kept for reference; can be deleted later).
