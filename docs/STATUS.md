# STATUS — current state

_Last updated: 2026-07-17 (settings-scope contract shipped to frontend)_

The single source of truth for where the project is **right now**. Update this
after every meaningful change.

## ✅ Phase: LIVE and MULTI-USER

The product works end-to-end for real users. Friends sign in (Google + email),
get a personalised India-focused feed with working filters and sort, save
searches, and get email digests. The month-long "0 jobs" era is closed; the
signup-blocking trigger bug is fixed; sources have been expanded ~3×.

## Latest change

**Settings-scope contract (frontend)** — profile `locations` now bound the feed
end-to-end: initial render, `/api/feed` re-queries, and the Location facet
options all inherit the boundary; UI filters can only narrow within it. New
"Browse all locations" session override, scope chips row, and over-constraint
diagnostics ("0 inside your locations — N exist elsewhere"). Roles were already
binding (ingest scoring + read-guard); salary_floor remains scoring-side only
(no hard filter — the feed RPCs have no salary param yet). See CHANGELOG
2026-07-17 and DECISIONS D31.

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
- **Ingestion** — ~95k jobs/run from greenhouse, ashby, lever, workday (India-
  searched finance GCCs), oracle, smartrecruiters, recruitee, foundit (Monster
  India), **workable (NEW — 240 harvested + curated boards)**, **bamboohr (NEW —
  309 harvested companies)**, **phenom (NEW — 7 tenants: NTT/Mastercard/DuPont/Danaher/ThermoFisher/GSK/GE-Aero, ~700+ India jobs)**,
  **smartrecruiters expanded 2→38 companies (~2.3k India postings: Bosch, Nagarro, …)**,
  jobspy (Indeed **+ LinkedIn**), adzuna (paginated,
  finance/tech India queries), jooble (NEW, needs free `JOOBLE_API_KEY`), and
  instahyre (India, best-effort), **kula (Cashfree/Plum/CleverTap)**, **successfactors CSB (7 Indian IT majors, ~663 India jobs)**, **jobvite (NEW — 28 verified tenants, ~1,000 jobs)**, and **zoho_recruit (NEW — 10 India tenants with full JDs)**. Workable+bamboohr smoke: +7.4k deduped jobs.
  India coverage ~tripled this session (jobspy 250→~1.8k, adzuna ~400→~1.2k, +48
  India company boards mined from the OpenJobs dataset, +harvested-cap 400→1000).
  Harvester now also mines workable/bamboohr weekly, and 193 verified Workday
  tenants sit in `data/workday_companies.json` behind `WORKDAY_INCLUDE_HARVESTED`
  (off until the data-model normalization lands).
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
- **Naukri / iimjobs** — recaptcha-walled; only reachable via the opt-in Gmail
  connect (now available in Settings, but parsing quality unverified at scale).
- **Google verification** — not completed (needs a domain you own; vercel.app can't
  be verified). Not needed — sign-in is scope-free so there's no warning anyway.
- **Instahyre** — rate-limits datacenter IPs; contributes when unblocked, else 0.
- **Eightfold** — same class: 403s datacenter IPs; best-effort connector (paypal,
  juniper) contributes only if unblocked. Delist if /health shows 0 for a month.

## Manual steps that must be kept in sync (Supabase SQL)

**Pending once:** `supabase/migrations/2026-07-16-companies-facets.sql`
(companies dictionary + cumulative facet_terms — powers the careers-page
fallback and ever-expanding filters).


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
