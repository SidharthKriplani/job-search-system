# CHANGELOG — lineage

Dated log of meaningful changes, newest first. Format: what + why.

---

## 2026-06-20

### Refresh rate-limit (admins exempt)
- `/api/scrape` now rate-limits manual refresh per user: a non-admin gets one
  refresh, then a cooldown (`REFRESH_COOLDOWN_HOURS`, default 12) before the next;
  the button shows when the next one is available. Admins (`ADMIN_EMAILS`, default
  the owner) are exempt. New `last_manual_refresh` column on `user_profiles`.
- _Why:_ repeated full scrapes are wasteful; the overnight sharded cron covers
  everyone automatically.

### Fixed: profile ↔ feed sync (Settings changes had no effect)
- `upsert_jobs` used `ignore_duplicates=True`, so re-runs never updated existing
  jobs' scores, and nothing pruned jobs that stopped matching a changed profile —
  the feed stayed frozen to the first scrape's profile.
- Fix: (1) upsert now UPDATES on conflict (re-scores; preserves is_applied/saved/
  dismissed since they're not in the payload); (2) a **re-sync pass** re-filters the
  *stored* feed against the current profile each run — drops jobs that no longer
  match (unless applied/saved), re-scores the rest. Works under sharding (operates
  on stored data, not the fetch). Verified: non-matching dropped, applied preserved.

### Coverage batch 3 → 151 verified boards
- +28 (Anthropic 373, Harvey 287, Adyen 201, Mistral 170, Workato 161, Sierra,
  Cresta, JetBrains, Qualtrics, Marqeta, Redis, Synthesia, Camunda…).
- **Learning:** Indian *consumer* startups are mostly NOT on Greenhouse/Lever/
  Ashby (they use Naukri / own ATS) — near-zero hit rate when probed. India-native
  breadth must come from **JobSpy (Indeed/Naukri) + Adzuna India**, not the ATS
  registry. ATS registry's value = global SaaS/AI/fintech with India GCCs.

### Coverage batch 2 → 123 verified boards
- +17 live-verified boards (Airwallex, ElevenLabs, Replit, Deepgram, Dataiku,
  Nium, Vonage, Contentful, Zapier, LiveKit, Sanity, Railway, GoCardless,
  Sendbird, Webflow, Descript, AssemblyAI). Registry: GH 66 · Ashby 41 · Lever 11
  · Workday 5 = 123 boards (concurrent fetch keeps run time flat as this grows).

### Scaling Stage 1: concurrent + sharded ingestion
- Rewrote `ingest/run.py` around flat "fetch units" (one per board/tenant) run
  **concurrently** in a thread pool (verified: a shard of ~10 boards = 1,328 jobs
  in 8.3s vs ~30s+ sequential).
- **Sharding:** `collect_jobs(shard_index, shard_total)` slices the units; `main.py`
  derives the shard from `BATCH_TOTAL` + UTC hour. `daily.yml` now runs **6 hourly
  batches (00:00–05:00 IST)** — each does one shard, so the full feed is assembled
  by ~6am without one giant run. Manual / "Refresh Now" runs stay full (BATCH_TOTAL=1).
- Full staged plan logged in `docs/SCALING.md`; architecture direction in DECISIONS (D8).

### Prefix-stem matching (word-form "semantic" fix, no LLM)
- Matching now stems tokens to a 5-char prefix so word-forms unify:
  science/scientist/scientific → "scien", analyst/analytics/analysis → "analy",
  manager/management → "manag". So "data science" matches "Data Scientist".
  Applied to the role hard-filter, role-fit scoring, and résumé overlap.
- Limits (honest): does NOT handle true synonyms (ML eng ≈ data scientist) or
  typos ("Dats Sciencc") — that needs Stage-2 LLM/embeddings. Case was already
  handled (everything lower-cased).

### M4 Stage 1: résumé capture + free heuristic résumé-matching
- **Résumé capture:** `resume_text` column on `user_profiles` (schema) + a
  paste-your-résumé textarea in Settings (saved with the profile).
- **Résumé-aware scoring:** `filter_and_score` now tokenises the résumé and adds
  a résumé-fit component (0.25 weight when a résumé is present) — jobs whose
  title+JD overlap the résumé rank higher, with a "Résumé match: x, y, z" reason.
  Verified: a qualitative "Research Associate" drops below a finance "Equity
  Research Associate" for a finance résumé, despite identical titles. Free, no API
  (Stage 2 LLM deep-read deferred per decision).

### Bulk registry expansion (~70 verified ATS boards)
- Added ~48 live-verified Greenhouse/Ashby boards (global SaaS w/ large India
  GCCs + Indian companies): Datadog, Snowflake, Okta, Twilio, Intercom, Notion,
  Plaid, Cohere, Handshake, slice, Sigmoid, Turing, and more.

### Workday connector + big registry expansion (India GCC jobs)
- New `ingest/connectors/workday.py` — pulls the CXS JSON API of big global firms
  that run large India GCCs. Verified tenants: NVIDIA, Salesforce, Mastercard,
  Adobe, Workday (~6,000 jobs total; India-located roles in Bangalore/Hyderabad/
  Pune/Noida). Capped per company via `WORKDAY_MAX_PER_COMPANY` (default 150).
- Registry expanded with verified boards: Greenhouse — PhonePe, HighRadius,
  MongoDB, Elastic, Rubrik; Ashby — Navi, Confluent, Temporal, Airbyte, Gainsight.
- All slugs/tenants verified live before adding (dead ones return 0, never crash).

### Fixed: Settings profile not persisting
- `saveProfile` spread the whole profile object into the upsert and never checked
  the error, so a failed save still flashed "Saved!" and nothing persisted across
  reloads. Now sends only editable columns, checks the error, and shows it.

### All-India coverage (JobSpy) + job-age/metadata on cards
- **JobSpy connector** (`ingest/connectors/jobspy.py`) — adopted `python-jobspy`
  as the primary all-India engine: scrapes Indeed/Naukri India across every field
  (broad cross-sector terms), failsafe-wrapped. Verified live. Reframes the
  product away from finance-only to general India coverage.
- **Adzuna** defaults broadened to India-first + cross-sector terms (was
  finance-weighted); still needs free `ADZUNA_APP_ID`/`_KEY`.
- **Job cards** now show relative **age** ("today / 3d ago / 2w ago", amber when
  stale >21d), **job type**, and **seniority** chips; added friendly source
  labels (Indeed/Naukri/Ashby/Adzuna…) and updated the source filter pills.
- Research captured in `docs/RESEARCH-india-coverage.md` (JobSpy, Adzuna, ATS
  company-list repos, Apify Naukri actors).

### M2 + M3: India coverage + JD-aware, profile-driven scoring
- **Registry:** added verified India-company boards — Postman, Groww, Druva
  (Greenhouse); Meesho, Zeta, Mindtickle, CRED (Lever). Real India breadth still
  wants Adzuna-India (free keys).
- **Scoring rewrite (`filter_and_score`):** the hard role filter now matches the
  title **or** the JD; the score is a weighted blend — title role-fit 0.30, **JD
  role-fit 0.25 (reads the description)**, industry-in-text 0.15, location 0.15
  (with India boost), salary 0.08, recency 0.07 — scored against the best-matching
  single target role, with human-readable reasons. Scores now spread and reflect
  the JD. Verified on a finance profile: 91/82/53/23 with the sales role filtered
  out (previously every job was a flat ~40%).

### Fixed: jobs never reached the DB (green-but-empty runs) ★
- The ingestion engine put a `remote` field on every job, but `job_feed` has no
  such column — so Supabase rejected every insert, `upsert_jobs` caught it and
  returned 0, and the run still exited green. Net effect: runs succeeded but
  wrote zero jobs (`total_jobs_in_db = 0` with an empty profile that should pass
  everything). Diagnosed via a one-row SQL check.
- _Fix:_ removed `remote` from the job dict (folded into `location`); added a
  `JOB_FEED_COLUMNS` whitelist in `upsert_jobs` that strips any stray key before
  insert; made a failed batch log loudly instead of silently. Verified the final
  upsert payload is a strict subset of `job_feed` columns.

### Live scrape status (UX)
- Rebuilt the "Refresh Now" button to poll the GitHub run and show real status
  (queued → running with ticking timer → completed/failed) + a direct run-log
  link. Added `frontend/app/api/scrape/status/route.ts`.
- _Why:_ the button was fire-and-forget — an idle screen with "wait and reload".
  Now the user sees each step and gets self-service failure diagnosis.

### Fixed CI dependency crash (`httpx 'proxy'` TypeError)
- **Upgraded** the Supabase stack to a verified-consistent set:
  `supabase==2.31.0`, `supabase-auth==2.31.0`, `supabase-functions==2.31.0`,
  `postgrest/storage3/realtime==2.31.0`, `httpx==0.28.1`, `websockets==15.0.1`.
  Hardened `main.py` to give a clear message if `user_profiles` can't be read.
- _Why:_ `supabase==2.3.4` was internally inconsistent — its sub-package calls
  `httpx(proxy=...)` but constrained httpx below 0.26 (which lacks `proxy`), so
  CI crashed with `TypeError: ... unexpected keyword argument 'proxy'`.
- _Correction:_ a first attempt pinned `httpx==0.25.2` — that was **backwards**
  (0.25 lacks `proxy`, so it kept crashing). The real fix is to *upgrade*, not
  pin down. Verified by constructing the client with a JWT-shaped key (a plain
  fake key short-circuits on "Invalid API key" before the httpx init, which is
  why the first verification was misleading) and by exercising every query the
  code builds against 2.31.0.

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
