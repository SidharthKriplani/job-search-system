# CHANGELOG — lineage

Dated log of meaningful changes, newest first. Format: what + why.

---

## 2026-06-22 (b) — precision pass: India-default + tighter read-guard + tsconfig

- **Root-cause fix for the repeated build failures:** `frontend/tsconfig.json` had
  no `target`, so it defaulted to ES5 and the type-checker rejected every Set/Map
  iteration. Set `target: es2017` + `downlevelIteration` — the whole class is gone.
- **India by default:** the overseas-drop now applies even when no location is set
  (this is an India-focused product), and `_FOREIGN_HINTS` is broadened (Mexico,
  London-area, EU, APAC, etc.). Verified: finance roles in SF/Mexico/London drop,
  Mumbai ones stay.
- **Precision read-guard:** the guard was letting engineers in via broad finance
  words ("Trading Systems Engineer" on "trading"). Rewrote `expandRoleKeywords` to
  split distinctive SINGLES (matched on title+company only) from high-precision
  PHRASES (title+desc+company); ambiguous singles (equity/capital/credit/trading…)
  only count inside a phrase; the broad sector net is added only when industries
  are explicitly set. Verified: Financial Analyst / IB Analyst kept, Design/Service/
  Trading Engineer dropped.

_Note:_ India finance-role coverage in the DB is still thin (most finance postings
come from global ATS boards) — removing the foreign noise makes that scarcity
visible. Next: add India finance sources.

---

## 2026-06-22 — role-family graph + sector layer (relevance neighbourhood)

A target role is now a weighted NEIGHBOURHOOD, not a point, plus a domain/sector
search axis. This is also the seed of the competence map (role→role edges).

- `utils/role_graph.py` — curated families (data/ml, software, product, design,
  finance_ib [dense + aliases], marketing, sales, consulting), alias resolution
  (ib→investment banker, ds→data scientist…), and sector keyword sets. `expand_roles`
  returns {role: weight} (target 1.0, neighbours decayed); `sectors_for` /
  `sector_keywords` power the domain net. Field-dependent by design: finance/etc.
  auto-activate the sector keyword net (non-standard titles), tech does NOT (titles
  are standardised — the title graph carries it).
- `utils/filter.py` — scoring now expands the role into its neighbourhood and
  ranks by weighted closeness; exact role ranks highest, adjacent roles show a
  "Related role: …" reason. Sector match (`Finance sector`) is its own signal and
  lets "any finance role" work with no title set. Verified: Data Scientist surfaces
  ML/Analytics; Investment Banker surfaces IB/M&A/PE/equity-research; unrelated
  Engineers dropped.
- `frontend/lib/roleGraph.ts` + `feedFilter.ts` — the read-time guard is now
  graph-aware (expands to neighbour + sector keywords across title/desc/company),
  so adjacent roles aren't excluded at read-time while gross mismatches still are.
  (Mirror of the Python graph — keep roughly in sync.)

---

## 2026-06-21 (g) — feed auto-populates the moment Refresh finishes

- User complaint: after Refresh completes, the feed didn't change until a manual
  reload. Cause: after the pagination rewrite the feed list is client-fetched, but
  run-completion only did `router.refresh()` (server props), which the client list
  state ignored — completion and feed-population were disconnected.
- Fix: `RefreshButton` takes an `onDone` callback; `DashboardClient.reloadFeed()`
  re-pulls the feed + "New" count the instant the run reports completed (with one
  short retry in case the DB write lands a beat later). No manual reload.

---

## 2026-06-21 (f) — read-time role guard (stale off-role rows can't show)

- Root cause of "investment banker → Engineers": `match_score` is computed by the
  backend at scrape time; changing the role leaves stored rows stale until an async
  re-filter runs, and the feed just read those rows. The relevance fix was correct
  but couldn't take effect without a backend run.
- Fix: `frontend/lib/feedFilter.ts` `roleOrFilter()` — the feed query + counts
  (`/api/feed`, `dashboard/page.tsx`) now require each shown job's title or
  description to contain a significant word from a target role. Off-role rows are
  excluded at query time, independent of backend prune timing. Deterministic.

---

## 2026-06-21 (e) — cleared the deferred audit items

- **Feed pagination + server-side search/filter.** New `frontend/app/api/feed`
  route; search, source, and New/Saved now query Postgres (not just the loaded
  200), with a "Load more" button. Stat tiles use live counters; source pills are
  derived from sources actually present. Fixes the "filter only sees 200" + "can't
  reach matches beyond 200" gaps.
- **Stemmer collisions.** Added `_STEM_OVERRIDES` so marketing≠marketplace and
  product≠production, while science↔scientist still merge (5-char prefix kept).
- **Gmail recency.** `_iso_date()` parses the RFC-2822 email Date header to
  YYYY-MM-DD; previously `date_str[:10]` produced "Mon, 02 Ju" so every Gmail job
  scored neutral recency.

---

## 2026-06-21 (d) — deep multi-pass bug audit + fixes

Three parallel deep audits (frontend, Python pipeline, schema/RLS/contracts).
Critical + High + cheap Medium fixed. See `docs/AUDITS.md` (v2) for the full list.
Highlights:
- **Critical:** fixed cross-user score contamination (shared job dicts mutated
  across users) and a latent total-batch-loss (`experience_required` whitelisted
  but absent from `job_feed`).
- **High:** salary parser now keeps Adzuna India absolute-INR salaries; location
  matching is token-based (no "Indianapolis"=India, no dropping Bangalore jobs
  that mention foreign teams); `delete_jobs` is user-scoped; all optimistic
  mutations check errors + roll back; dashboard counts refresh after mutations;
  `job_feed` INSERT RLS tightened; `scraper_health` no longer world-readable.
- **Medium:** referral template `.replaceAll`; unique index stops duplicate
  applications; overdue-date compare normalized; React key + badge fallbacks.
- Schema gained an idempotent `DO $$` block to retrofit unique constraints
  (re-run `supabase/schema.sql` to apply the new RLS + indexes).

---

## 2026-06-21 (c) — fast resync on profile change + LinkedIn referral import

### Profile changes now re-match the feed in ~1 min (not 3-min scrape)
- The stale-feed problem ("investment banker" still showed Engineers) was because
  the resync only ran INSIDE a full scrape. Extracted `resync_user()` in `main.py`
  and added a **RESYNC_ONLY** fast path (`TARGET_USER_ID` scopes to one user) that
  re-filters the STORED feed against the current profile with **no scraping**.
- New `.github/workflows/resync.yml` (workflow_dispatch, user_id input) + new
  `frontend/app/api/resync/route.ts`. Saving Settings now calls `/api/resync`, so
  changing your target role prunes/re-scores the existing feed within ~30–60s.
- Requires the new `filter.py` to be deployed for the prune to be correct.

### Referral import from LinkedIn Connections.csv (the compliant path)
- `referrals/ReferralsClient.tsx` — "Import from LinkedIn" button + modal:
  in-browser CSV parse (handles LinkedIn's preamble lines, quoted commas, missing
  emails), matches each connection's company against the user's feed/tracker
  companies (legal-suffix-stripping fuzzy match), pre-selects "in your feed"
  matches, and bulk-inserts into `referral_pipeline` (connection_type
  linkedin_1st). De-dupes against existing contacts.
- `referrals/page.tsx` passes `feedCompanies` (distinct job_feed + applications
  companies). No schema change (referral_pipeline already exists).
- _Why this design:_ per deep research, no compliant API exposes a user's
  connection graph worldwide; the user's own data export is the only consented
  path, and email is opt-in (~70% blank) so we match on name + company.

---

## 2026-06-21 (b) — relevance + feed-honesty fixes (from live testing)

### Relevance: multi-word roles no longer collapse to generic words
- `utils/filter.py` — the résumé tokenizer dropped <4-char words, so the role
  **"ai engineer"** silently became just **"engineer"** → every Security/Backend/
  Service/Automation Engineer matched at 97%. New `_mstems()` keeps 2+ char role
  words (ai/ml/qa/ux). New `_GENERIC_ROLE_STEMS` guard: a generic word
  (engineer/manager/analyst…) can no longer qualify a multi-word role on its own —
  the distinctive word must also be present. Verified: 7-job test now keeps only
  the real AI/Data roles, drops the generic-Engineer noise.
- Fixed latent `NameError` in the industry block (`text` was undefined).

### Location now actually filters
- When the user sets location prefs, clearly-overseas **non-remote** jobs are
  dropped (`_FOREIGN_HINTS`, conservative full-name list). Bangalore profile no
  longer shows New York jobs. India + remote + unclassifiable are always kept.

### Feed honesty + applied UX
- `dashboard/page.tsx` + `DashboardClient.tsx` — "New Today" → "New" (it's
  since-last-visit, not today); "In Feed" now shows the TRUE total, not the page
  size; added "Showing top N of M". Feed limit 100 → 200. **Applied jobs are
  excluded from the feed** (they live in the tracker) — fixes a job showing
  "Mark Applied" after it was already applied.
- `settings/SettingsClient.tsx` — "Saved!" persists until the next edit instead
  of reverting on a 2.5s timer.

_Note:_ existing feed rows were scored by the old loose filter; they get
re-scored/pruned on the next scrape run (main.py resync). A manual Refresh after
deploy cleans them up.

---

## 2026-06-21

### Application tracker built up (M5 — jobs now flow into the tracker)
- `frontend/components/JobCard.tsx` — "Mark Applied" now flags the feed row **and**
  inserts a row into the `applications` table (user_id, job_feed_id, company, title,
  url, location, source, stage='Applied', date_applied=today). Guarded against
  duplicates (skips insert if a row already exists for that `job_feed_id`).
  Best-effort: tracker insert failure never blocks the feed flag.
- `frontend/app/applications/ApplicationsClient.tsx` — `AppCard` rewritten with an
  expandable edit panel (notes, next action, recruiter, follow-up date, priority),
  optimistic `updateApp`/`deleteApp` handlers, delete-with-confirm, and display of
  `date_applied` + overdue follow-up highlight. `updateStage` is now optimistic.
- _Why:_ the tracker was the missing half of the loop — applying to a job from the
  feed now auto-populates the 18-stage tracker; cards are fully editable. No schema
  change (applications table already exists in `supabase/schema.sql`).

---

## 2026-06-20

### Own the registry: Common Crawl harvester (replaces Feashliaa dependency)
- `ingest/harvester.py` — discovers ATS company slugs (Greenhouse/Lever/Ashby) from
  **Common Crawl** (public, open), VERIFIES each is live, and writes our own
  `ingest/data/{ats}_companies.json`. Proven: 1 CDX page → 1,665 candidates → verified
  → live boards (Relativity 304, IBKR 176, Instacart, Flexport, SoFi…).
- Connectors now use `registry.all_greenhouse()/all_lever()/all_ashby()` = curated ∪
  harvested (deduped, capped by `MAX_HARVESTED_PER_ATS`). New weekly
  `.github/workflows/harvest.yml` refreshes + commits the lists.
- _Why:_ own our data layer (D10/D11) — license-clean (vs Feashliaa CC-BY-NC),
  regenerable, and the path to thousands of boards without a 3rd-party dependency.

### GRAND-VISION: tie into the Labs ecosystem (Career OS)
- `docs/GRAND-VISION.md` — the job-search-system is the "GET HIRED" half; the Labs
  (Product Analytics Lab, ML Systems Lab, GenAI Lab) are the "GET READY" half. The
  Labs are the retention layer job-search lacks; the job feed gives prep a target.
  Closed loop: job → gap → route to exact Lab room → readiness ↑ → realistic-shot ↑
  → apply → interview-sim → offer. Connect via shared identity + one profile
  (extend `user_profiles`) + deep links — loosely coupled, don't merge runtimes.
  PAL's JD→study-plan generator is already the bridge.

### Feashliaa company-list mine (→167 boards) + VISION doc
- Mined the Feashliaa/job-board-aggregator slug list (95k slugs, CC BY-NC, mined
  with attribution / non-commercial); live-verified a batch → +16 boards (Curaleaf,
  Crunchyroll, Cribl, Dandy, D2L, Cresco…). Registry now 167. The full list is the
  path to thousands (data-file + verify-promote), gated by the Stage-2 scaling refactor.
- `docs/VISION.md` — the product is a **career copilot, not a job board**: discover →
  match → decide → prepare → **reach (find email + LLM outreach + tailored résumé +
  send via your Gmail)** → apply → referral → interview prep → negotiate → career-OS.
  The "what after jobs" outreach stage is the flagship differentiator.

### Free semantic matching (FastEmbed) + OSS building-blocks catalogue
- `utils/embeddings.py` — opt-in local embeddings (FastEmbed/ONNX, no API, no
  torch). Re-ranks the keyword-filtered shortlist by *meaning*: "ML Engineer" ≈
  "Data Scientist" (verified: boosted a 20%-keyword job to 48% on semantics).
  Off by default; enable with `USE_EMBEDDINGS=1` + `requirements-embeddings.txt`
  (kept separate so default runs stay lean). Tags matches with "Semantic match".
- `docs/OSS-building-blocks.md` — curated open-source tools mapped to the journey
  (JobSpy, FastEmbed, job-board-aggregator/OpenPostings for 20k+ company slugs,
  Ollama, Reactive Resume, Pyxis/email-finder, JobSync) with adopt/borrow/skip
  verdicts. Standout next: the ATS company-list repos to bulk-expand the registry.

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
