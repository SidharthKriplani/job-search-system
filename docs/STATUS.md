# STATUS — current state

_Last updated: 2026-07-15 (late — through foundit/Recruitee/Workday-tenant adds)_

The single source of truth for where the project is **right now**. Update this
after every meaningful change.

## ✅ Phase: LIVE and MULTI-USER

The product works end-to-end for real users. Friends sign in (Google + email),
get a personalised India-focused feed with working filters and sort, save
searches, and get email digests. The month-long "0 jobs" era is closed; the
signup-blocking trigger bug is fixed; India source coverage expanded ~4–5×.

## At a glance

| | |
|---|---|
| **Live app** | https://job-search-system-zeta.vercel.app |
| **Repo** | https://github.com/SidharthKriplani/job-search-system (branch `main`, **public**) |
| **Supabase** | project `dnczgcrgaczjhinrplpy` (ap-southeast-1) |
| **Hosting** | Vercel (frontend, auto-deploy on push) · GitHub Actions (daily scraper, weekly harvest, on-save resync) |

## What works (verified live)

- **Auth** — Google sign-in is scope-free (no "unverified app" wall); email/password
  with a set/reset-password flow; the `handle_new_user` trigger is bulletproofed
  (wrapped in EXCEPTION handlers) so signup can never 500 again. Multiple friends
  signed in successfully.
- **Ingestion** — ~74k jobs/run from greenhouse, ashby, lever, **workday (66
  tenants** — India-searched finance GCCs + global India offices), oracle,
  smartrecruiters, jobspy (Indeed **+ LinkedIn**), adzuna (paginated, finance/tech
  India queries), **recruitee**, instahyre (best-effort), and **foundit / Monster
  India** — the largest single India source (~2.7k India jobs/run, the Naukri
  alternative that isn't recaptcha-walled). India coverage went from ~3k to
  ~4–5× deeper this session: jobspy 250→~1.8k, adzuna ~400→~1.2k, foundit ~2.7k,
  +39 Workday tenants (~690 India), Recruitee (~130), +48 mined greenhouse/lever
  boards, harvested-cap 400→1000.
- **Matching** — role-graph + sector + résumé + seniority + **source-domain
  provenance** (a finance job from a finance board outranks a generic keyword
  match). Read-time relevance floor (0.45) on the default feed; dropped when the
  user searches/filters so they can dig below it.
- **Feed UI** — server-side search + faceted filters (Board / Position / Company /
  Location, dynamic options with counts via `get_feed_facets` RPC) + sort
  (relevance | date). Position/location are normalised buckets. Dead-link cleanup.
- **Saved searches + alerts** — save a filter set; the digest reports new matches.
- **Tracker + Referrals** — 18-stage application tracker; LinkedIn CSV referral
  import ranked by live openings per company.
- **Ops** — `/health` page (per-source status + trend); run reports committed to
  `docs/LAST_RUN.md`; pool-drop alarm + canary matching check each run.

## Known gaps / open items

- **Data-model normalization (the one real ceiling).** `job_feed` still stores one
  row per (user, job). `cap_user_feed` (2500/user) + trimmed descriptions bound it,
  but past ~10 heavy users the right fix is `jobs` (canonical) + `user_job_matches`
  (thin pointers). See ROADMAP.
- **Naukri / iimjobs** — recaptcha-walled (re-confirmed 3 ways incl. the direct
  jobapi/v3/search → 406 from datacenter IPs). Only reachable via the opt-in Gmail
  connect. **foundit (Monster India) now covers most of this gap** — comparable
  India volume, no wall. Other India boards (iimjobs/hirist/shine/cutshort) have
  no usable API from our infra.
- **Google verification** — not completed (needs a domain you own; vercel.app can't
  be verified). Not needed — sign-in is scope-free so there's no warning anyway.
- **Instahyre** — rate-limits datacenter IPs; contributes when unblocked, else 0.

## Manual steps that must be kept in sync (Supabase SQL)

Re-running the full `supabase/schema.sql` is idempotent and applies all of these.
It adds/updates: `jobs_pool`, `run_history`, `scraper_health_history`,
`feed_feedback`, `saved_searches`; the `source_domain` / `position` /
`location_city` columns + `get_feed_facets` RPC; the bulletproof `handle_new_user`
trigger; the gmail_tokens service-role-only policy; NULL-flag heals.

## Things not verifiable from the sandbox (need live data/secrets)

- Live Supabase table sizes / egress under real multi-user load.
- Gmail parser against real alert emails (now opt-in).
- Instahyre / LinkedIn reliability from GitHub Actions IPs over repeated runs
  (watch `/health` + `docs/LAST_RUN.md`).
