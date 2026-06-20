# CHANGELOG — lineage

Dated log of meaningful changes, newest first. Format: what + why.

---

## 2026-06-20

### Live scrape status (UX)
- Rebuilt the "Refresh Now" button to poll the GitHub run and show real status
  (queued → running with ticking timer → completed/failed) + a direct run-log
  link. Added `frontend/app/api/scrape/status/route.ts`.
- _Why:_ the button was fire-and-forget — an idle screen with "wait and reload".
  Now the user sees each step and gets self-service failure diagnosis.

### Fixed CI dependency crash
- Pinned the full Supabase dependency stack in `requirements.txt`
  (`httpx==0.25.2`, `gotrue==2.9.1`, `postgrest`, `storage3`, `supafunc`,
  `realtime`). Hardened `main.py` to give a clear message if `user_profiles`
  can't be read.
- _Why:_ the GitHub run crashed with `TypeError: Client.__init__() got an
  unexpected keyword argument 'proxy'` — `supabase==2.3.4` left sub-deps
  unpinned, so CI resolved an incompatible httpx. Verified the pinned combo
  installs + constructs the client.

### Manual scrape trigger
- Added `POST /api/scrape` (GitHub `workflow_dispatch`) + the "Refresh Now"
  button. Requires `GITHUB_DISPATCH_TOKEN` in Vercel.
- _Why:_ let the user trigger the daily scraper from the UI to test, instead of
  the GitHub Actions tab.

### ATS-source ingestion engine (the foundation)
- Built `ingest/` — connectors for Greenhouse, Lever, Ashby (company ATS APIs)
  and Remotive/Arbeitnow/Adzuna (aggregators), a company→ATS registry, normalize
  + dedup, orchestrator + CLI. Refactored `main.py` to fetch this shared pool
  once per run and filter per user. Removed the 10 fragile HTML portal scrapers
  from the pipeline (files kept as legacy). Proven live: **4,309 deduped jobs**.
- _Why:_ portal scraping broke constantly; "no data → no product". ATS/aggregator
  APIs are official, stable, and don't break on site redesigns.

### Dark mode
- `darkMode: 'class'` + no-flash theme bootstrap + sidebar toggle + dark variants
  across all pages/components.

### Navigation latency fix
- Parallelised the dashboard's 4 sequential Supabase queries (`Promise.all`),
  parallelised settings/referrals, added `loading.tsx` skeletons, switched
  settings reads to `maybeSingle()`.
- _Why:_ tab switches hung on sequential server round-trips.

### Code audit + fixes
- Read the whole repo, ran the pipeline in a sandbox. Fixed: digest re-sending
  the whole feed daily (now new-only via `get_existing_job_keys`); salary parser
  inflating GCC monthly pay into bogus LPA; `schema.sql` made idempotent; signup
  trigger now creates the `user_profiles` row + backfills (email/password users
  were invisible to the scraper); `naukri_refresh.py` guarded against missing
  columns. Full detail in root `AUDIT.md`.
