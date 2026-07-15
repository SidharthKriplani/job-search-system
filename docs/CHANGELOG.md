# CHANGELOG — lineage

Dated log of meaningful changes, newest first. Format: what + why.

---

## 2026-07-15 (l) — new source research + Instahyre; raised run timeouts

Researched more sources empirically (probed live, kept only real India value):
- **Instahyre** (India tech board, JSON API) — ADDED as a connector (~420 India
  jobs: Sprinklr, Avaamo, …). Best-effort: it rate-limits datacenter IPs, so it
  degrades gracefully to 0 when blocked (never breaks the run). Domain=tech.
- **Rejected as noise** (verified low India value): The Muse (3 India / 160),
  RemoteOK (3/100), Jobicy, Himalayas — all global-remote APIs whose "India" is
  mostly US-remote that would pollute the feed.
- **Dead/changed APIs**: cutshort, wellfound, YC work-at-a-startup.
- **SmartRecruiters**: probed Freshworks/Zomato/Swiggy/Razorpay/Meesho — none on
  SR (they use other ATS). No easy expansion there.
Verdict: the accessible India sources are now tapped; the big remaining volume
(Naukri) stays recaptcha-walled.

Timeouts raised (more sources = longer full runs): daily.yml 45->60 min,
harvest 30->45, RefreshButton poll cap 30->45 min.


## 2026-07-15 (k) — scraper audit: raised harvested-board cap (recovers India coverage)

Empirically audited every connector. Findings:
- greenhouse/ashby: pull full boards, healthy — BUT capped at 400 harvested
  boards each. The excluded band (rank 400-900) held 514 India jobs across 86
  boards (SonicWall, CloudSEK, DevRev, Cialfo…). Raised MAX_HARVESTED_PER_ATS
  400 -> 1000: board-only India jobs ~3000 -> 3507, board fetch 65s -> 116s (fine).
- workday: verified NOT truncated — pulls all India-searched results per tenant
  (PwC 144, none hit the 150 cap). Optimal.
- oracle / smartrecruiters: pull all; small (few curated firms) — headroom is
  adding more finance tenants (needs live verification, marginal).
- lever: structurally thin — probed 34 known Indian companies, only 1 on Lever
  with 0 India roles. Indian firms don't use Lever; not worth expanding.
- jobspy (k-1) + adzuna (k-2): already maximised.
Verdict: scrapers now near their practical India best; remaining gap is
structural (Naukri recaptcha-walled).


## 2026-07-15 (j) — Adzuna scaled (pagination + finance/tech queries)

Correction: Adzuna WAS live in prod (aggregators 538 vs 138 keyless) — the keys
are set. But it was under-configured:
- **Page 1 only** → now fetches ADZUNA_PAGES (default 4) pages/query (50/page),
  stopping early when a query runs out. ~4x the depth per query.
- **Generic queries** → finance + tech India-relevant set (data scientist,
  equity research, credit analyst, fp&a, …).
- max_days_old 14 → 30. 1.2s pacing to respect the free tier (25/min, 250/day);
  aggregators is one nightly fetch unit so total calls stay well under the cap.
Estimated: ~400 → ~1,000-1,500 India jobs with salary data.


## 2026-07-15 (i) — India coverage: jobspy scaled 6-7x (the real "too few postings" fix)

Diagnosed the thin feed: the 71k pool is only ~4% India-located (2,996 jobs) —
Greenhouse/Ashby are US/global tech. The India-native source (jobspy) was
throttled. Live-verified fixes:
- **jobspy per_term 25 -> 60** (Indeed returns 80/term; we were leaving 3x on
  the table).
- **LinkedIn enabled** (JOBSPY_SITES "indeed" -> "indeed,linkedin") — LinkedIn
  returns ~80 India jobs/term and wasn't being used at all.
- **Finance + tech India-relevant default terms** (data scientist, equity
  research, credit analyst, fp&a, …) replacing the generic ones.
- Verified yield: 3 terms x 2 sites @60 = 360 jobs/85s → full 16-term set ≈
  1,500-1,900 India jobs vs 250 before (6-7x).
- Fixed a NaN leak (company/title showing literal "nan" from empty pandas cells).
- Confirmed dead ends (won't chase): Naukri = recaptcha-walled, Glassdoor/Google
  = broken via jobspy.

NEXT India lever (needs your action, free): enable **Adzuna** — get a free key at
developer.adzuna.com and add ADZUNA_APP_ID / ADZUNA_APP_KEY as GitHub secrets.
The connector already handles it (skips cleanly without a key); it adds India
breadth + salary data.


## 2026-07-15 (h) — feed filters + sort (Position / Company / Location / Board)

Server-side faceted filtering (correct across the WHOLE feed, not just the
loaded page):
- **Canonical buckets** (`utils/normalize.py`): every job gets a `position`
  (title → Data Scientist / Equity Research Analyst / … / Other) and
  `location_city` (raw → Bangalore / Mumbai / Remote / Overseas / …) stamped at
  write time (`_enrich_facets` on all upsert paths). All fuzzy naming-approx
  logic in one place. Stored columns → exact, fast filtering + clean dropdowns.
- **Dynamic options** (`get_feed_facets` RPC + `/api/facets`): dropdowns show
  only the boards / positions / locations / top-60 companies actually present
  in the user's feed, each with a count. One RLS-scoped round-trip.
- **Feed route**: multi-select `.in_()` filters for position/company/location
  (board already existed) + `sort` = Best match (relevance, default) | Date
  posted (posted_date desc, nulls last).
- **UI**: `FacetSelect` multi-select dropdowns (company searchable) + a sort
  select, wired to re-query server-side; facets refresh after a manual Refresh.

Manual step: re-run supabase/schema.sql (adds position/location_city columns +
get_feed_facets function). Idempotent.


## 2026-07-15 (g) — domain-aware source routing (finance + tech)

Sources are now tagged finance / tech / general (registry.unit_domain):
Workday finance GCCs + Oracle + SmartRecruiters = finance; curated
Greenhouse/Lever/Ashby = tech; harvested + jobspy + aggregators = general.
- **Fetch prioritisation**: collect_jobs(priority_domains=…) orders the domains
  the night's active users need FIRST, so relevant boards are never starved by
  a job timeout. main.py derives priority from user industries/roles.
- **Provenance scoring**: each job carries source_domain; filter gives a small
  (~5-6% weight) boost when the board's domain matches the user's sector — a
  finance job from a finance-GCC board outranks a keyword-only match from a
  generic board (verified: Morgan Stanley/Oracle ranks above an identical
  generic-source copy). Persisted on job_feed + jobs_pool so resync keeps it.
- Run report + logs now show pool domain mix (e.g. finance 1020 / tech 12k /
  general 58k — quantifies the known finance-coverage gap).

⚠️ Manual step: re-run supabase/schema.sql (adds source_domain columns). Idempotent.


## 2026-07-15 (f) — adversarial audit: 14 fixes (3 self-inflicted this session)

Ran a 3-front adversarial audit (Python pipeline / frontend+security / ops).
Fixed, most severe first:

CRITICAL
- **Digest re-emailed old jobs as "new" forever** — get_existing_job_keys was
  un-paginated (PostgREST 1000-row cap on a 24k feed). Now paginated.
- **Pool matches invisible in feed** — resync's mixed upsert batches wrote pool
  rows with is_applied/is_saved = NULL, and the feed uses .eq(is_applied,false)
  which excludes NULL. Pool candidates now carry explicit False flags.

HIGH
- **gmail_tokens exposed OAuth refresh token to the browser** — the user SELECT
  policy made the gmail.modify refresh token readable via the anon key. Dropped;
  table is now service-role only (UI uses user_profiles.gmail_connected).
- **6 duplicate digests/reminders per night** — process_user runs in all 6
  shards; digest+reminders+resync now gated to once/day via an atomic claim.
- **Wall-clock shard index** — a delayed cron computed the wrong shard (one
  doubled, one skipped). BATCH_INDEX now derived from the cron string that fired.
- **No concurrency guard** — manual "Refresh Now" could overlap a scheduled
  shard and race job_feed writes. daily.yml now has a serialized concurrency group.
- **get_gmail_token crashed** the whole per-user pass when a connected user had
  no token row (maybe_single→None). Guarded.
- **jobspy zeroed on any salary-less row** — int(NaN) escaped the per-term try
  and killed the whole source. NaN-guarded.

MEDIUM
- **Supabase egress ~6×** — the 14MB full-feed resync read ran every shard;
  now once/day (gated with digest). Big free-tier saver.
- **Digest HTML injection** — scraped titles/URLs interpolated unescaped into
  email HTML. All fields escaped; job_url restricted to http(s).
- **Embeddings head/tail score incomparability** — partial rerank deflated head
  scores below the untouched tail. Now reranks the full shortlist or skips.

LOW
- RefreshButton watchdog setTimeout never cleared → could flip a healthy run to
  "error". Stored in a ref and cleared in stop().
- harvest commit died if the tuning report was missing; placeholder reports now
  tracked, commit uses -A + rebase-retry.

Known/accepted (documented, not yet fixed): job_feed still O(users×matches) —
500MB tier ~8-12 broad users (SCALING.md Stage-2 refactor); all-users resync
re-reads pool per user (rare, manual only); Actions minutes ~cap on a PRIVATE
repo (public = free).

---

## 2026-07-15 (e) — product pass: instant onboarding, feedback loop, ops alarms

1. **jobs_pool persistence + instant onboarding** — the nightly pool is now
   stored (jobs_pool, last_seen_at). resync sources candidates from stored feed
   ∪ pool, so a NEW user who saves a profile gets a feed in ~a minute from last
   night's pool — no scrape wait. Pool pruned at 14d unseen.
2. **Capped-source cleanup (cap-safe)** — workday/oracle/smartrecruiters rows
   unseen in jobs_pool for 7 days are removed (same-run absence proves nothing
   for capped listings; a week does).
3. **Ops alarms** — run_history table + pool-drop alarm (pool < 50% of recent
   median → _pool health warning + report flag); canary profile match check
   every run (_canary health row) — catches "green run, broken matching".
4. **Health trends** — scraper_health_history (append-only) + trend column on
   /health; dashboard empty-state now says when sources are failing instead of
   blaming the user's profile.
5. **Digest sharpened** — top 10 only, stats strip (new/follow-ups/stale),
   no empty sends. Adzuna predicted salaries labeled "(est.)".
6. **Feedback→tuning loop v1** — weekly scripts/feedback_report.py aggregates
   feed_feedback → docs/TUNING_REPORT.md (by reason/source/title, flags
   confident-but-wrong ≥0.7 rejections). Committed by the weekly workflow.
7. **Referral ranking** — LinkedIn import list ranks connections by live
   openings at their company ("4 openings" beats "in your feed").

⚠️ Manual step: re-run supabase/schema.sql (adds jobs_pool, run_history,
scraper_health_history). Idempotent.

---

## 2026-07-15 (d) — refresh UX desync (user-reported) + cleanup cap-safety

**"App refresh works for 3 minutes but the backend job runs longer — a 2nd
refresh started."** Root causes, all in RefreshButton/API:
- `EXPECTED_SEC=210` promised ~3.5 min; real full runs take 7–10+ min → 600.
- A 6-minute give-up timer flipped the button back to idle MID-RUN — inviting
  the duplicate refresh the user saw. Removed; polling now runs to actual
  completion (30-min cap).
- `/api/scrape` had no concurrency guard → now returns 409 with the active
  run's URL; the button ATTACHES to that run instead of starting another.
  Status route prefers the active run; on page load the button auto-attaches
  to any run already in progress (reload can no longer bypass the guard).
- Cap-safety (proactive): dead-job cleanup now only trusts greenhouse/lever/
  ashby (complete listings). Workday/Oracle are capped per company and
  smartrecruiters paginates — absence there ≠ closed.

---

## 2026-07-15 (c) — six product improvements (post-blocker hardening)

1. **Dead-job cleanup** — `cleanup_closed_jobs()`: ATS-source rows absent from
   the current pool are deleted when their company's board fetch succeeded
   (saved/applied rows kept; gmail/jobspy/aggregators exempt — their listings
   are partial by nature). The feed no longer accumulates dead links.
2. **Run report** — every daily run writes sanitized `docs/LAST_RUN.md`
   (shard, source summary, per-user matched/new/removed, errors) and the
   workflow commits it `[skip ci]` with a rebase-retry for sharded races.
   Any future "why is it broken" starts with `git pull`, not a PAT.
3. **Relevance feedback** — new `feed_feedback` table (RLS: insert/view own) +
   a "Not relevant → why" menu on JobCard (wrong role/location/seniority/
   company/stale/other). The raw signal for tuning the matcher.
4. **Embeddings rerank ON** — `USE_EMBEDDINGS=1` in daily.yml + fastembed
   install + model cache. Semantic rerank of the keyword shortlist.
5. **Scraper-health page** — `/health` lists per-source status, last run,
   job count, failures, last error. Sidebar link added.
6. **Naukri credentials feature REMOVED** — naukri_refresh.py deleted,
   workflow step dropped, schema now DROPs the plaintext password columns.

⚠️ Requires one manual step: re-run `supabase/schema.sql` in the Supabase SQL
editor (adds feed_feedback, drops naukri columns). Idempotent, no data loss.

---

## 2026-07-15 (b) — LIVE BLOCKER CLOSED: first observed end-to-end production run

Ran the real pipeline on GitHub Actions with live secrets via a temporary
self-reporting diag workflow (report committed back over git). Result:
**24,466 jobs upserted to the live feed (23,987 new) — the feed is populated.**
Root causes of the "0 jobs" era, now explained:
- Shivali has NO active user_profiles row (Active users: 1 = Sidharth only) —
  her empty feed was a missing-profile issue, not scraping/matching.
- Resend digest fails 403 (sender domain unverified) — needs Resend dashboard.
- Gmail parser fails `invalid_client` — GOOGLE_CLIENT_ID/SECRET point to a
  missing GCP OAuth client. Needs Google console.

Fixes from observing the run under real load:
- `greenhouse.py`: location {"name": None} crashed `.lower()` and silently
  killed entire boards → guarded.
- `age_out_new_flags`: single UPDATE hit statement timeout (57014) on a big
  feed → batched (id pages of 500).
- `get_user_feed_rows`: PostgREST 1000-row default cap silently truncated
  resync on large feeds → paginated with .range().
- Registry: doordash→doordashusa (459 jobs), benchling Greenhouse→Ashby (50).

---

## 2026-07-15 — full-project health pass (cloud sandbox audit + fixes)

Verified live from a clean environment: full ingest run pulled **70,314 jobs**
(greenhouse 60,301 / ashby 27,243 / workday 1,059 / oracle 224 / smartrecruiters
111 / jobspy 250 / aggregators 139); finance profile matched 16k+, incl. JPMorgan
Mumbai equity research. Frontend `tsc --noEmit` clean + `next build` succeeds.
schema.sql applied twice against a real Postgres 16 (stubbed auth schema) — fully
idempotent, all 8 tables, signup trigger creates profile + 3 templates, job_feed
upsert conflict path correct. Conclusion: the code pipeline is healthy end-to-end;
the "0 jobs live" blocker is deploy/infra (Actions log still unread — needs repo access).

Fixes shipped in this pass:
- **Staleness cutoff** (`utils/filter.py`): postings older than `MAX_JOB_AGE_DAYS`
  (default 90) are dropped up front — the live pool carried 2019-dated postings
  (7,587 dropped on a real run). Undated jobs kept (neutral recency). New test.
- **`is_new` now ages out** (`utils/supabase_client.py` `age_out_new_flags` +
  `main.py`): rows older than 24h get `is_new=false` at the start of each user's
  daily pass, so the dashboard "New Today" stat is honest (was write-once TRUE).
- **Registry hygiene** (`ingest/registry.py`), live-verified: mux moved Lever→Ashby;
  cresta moved Ashby→Greenhouse (added, 103 jobs); voiceflow, romerolabs,
  clipboardhealth, statsig dead on all 3 ATSes → removed.
- Tests: 23 green (added stale-drop regression test).

---

## 2026-06-23 (c) — finance is ONE connected market (stop forcing front/back office)

The repeated "front office vs back office" pain was a modelling error: finance_ib
(front), finance_ops (back), finance_risk (middle) were rigid silos with no
cross-links, so an IB-research résumé fell into one silo and missed the rest —
empty feed, user forced to manually re-pick roles every time.
- `role_graph.py` `expand_roles` + `roleGraph.ts` `expandRoleKeywords`: the three
  finance families are now **cross-linked** at weight 0.45 (`_FINANCE_FAMILIES`).
  Within-family neighbours still rank highest; the whole finance-analytics space
  (credit research, FP&A, ops, risk) is now reachable from any finance role.
- Verified: Shivali's UNCHANGED "investment banking analyst" target now matches
  **24 real India finance roles** (JPMorgan Global Research-Credit Strategy,
  Wholesale Credit Risk, FP&A, Citi, WNS Credit Management) with zero re-picking.
- Updated the test that asserted the old rigid separation → now asserts the
  connected behaviour (back-office appears, exact role still ranks above). 22 green.

---

## 2026-06-23 (b) — two new ATS-platform connectors: Oracle + SmartRecruiters

Per-PLATFORM connectors (not per-company scrapers) — each adds many finance firms.
- **Oracle Recruiting Cloud** (`ingest/connectors/oracle.py`): public JSON,
  `keyword=India`. Registry: EXL (124 India roles!), JPMorgan (Wholesale Credit
  Risk Analyst, FP&A, Valuation Controller — Mumbai), Jefferies. Verified live
  through our connector; working apply URLs.
- **SmartRecruiters** (`ingest/connectors/smartrecruiters.py`): public API,
  `country=in`. Registry: WNS (Credit/Market-Research analysts), NielsenIQ
  (Analyst-Banking, data science). Verified live.
- Wired into `ingest/run.py` as concurrent units; `SOURCE_LABELS` updated.
- Probe verdict logged: the Darwinbox IB-research KPOs (Evalueserve/Acuity/CRISIL)
  are behind a Cloudflare captcha — NOT HTTP-pullable; Naukri/Gmail is their only
  route. Moody's/EY (SuccessFactors), MSCI (iCIMS), BNP (Taleo) also not cleanly
  pullable.
- Tests: 22 green (added registry-shape guards for the new connectors).

---

## 2026-06-23 — India-targeted Workday fetch + bank IB-research GCCs

The real coverage fix for Shivali's niche (offshore IB-research/analytics support).
- **Workday connector now searches India directly** (`searchText="India"` instead
  of `""`). It was fetching the first ~40 GLOBAL jobs and discarding non-India, so
  on huge boards the India roles were never reached (Citi returned 0 India). After
  the fix: Citi 0→33 India/page, Morgan Stanley 8→37, State Street 15 — multiplies
  India yield across EVERY Workday tenant. Configurable via `WORKDAY_SEARCH_TEXT`.
- **Added 4 verified bank IB-research/markets-analytics GCCs**: Citi (wd5/2),
  Morgan Stanley (wd5/External), Bank of America Continuum India (ghr/wd1), FactSet
  (wd108). Verified through our own connector — Citi/MS return real India
  capital-markets / risk-analytics / FP&A roles (her market).
- **Honest limit:** the Indian-HQ IB-research KPOs (Evalueserve, Acuity, CRISIL,
  SG Analytics, Aranca, TresVista) are on Darwinbox/custom with NO public API —
  they need the Naukri/Gmail channel, not ATS pulls. Logged for the next lever.

---

## 2026-06-22 (l) — honest empty state + IB precision; coverage finding

- **Coverage finding (the key one):** probed our live finance Workday sources for
  India — they return retail-banking sales, ops, risk, and tech (Sales Manager–
  Premium Banking, Credit Risk AVP, Liquidity Ops, Data Scientist-Banking), NOT
  front-office Investment Banking (M&A/ECM/equity research). So an "investment
  banking analyst" target correctly returns ~0 — those roles aren't in our ATS/
  Workday pool at all; they live on iimjobs/Naukri (Gmail channel). This is a
  DATA gap, not a matching bug.
- **Empty state rewritten:** when a profiled user has 0 matches, the feed now says
  why (niche/front-office roles come from Naukri/iimjobs → connect Gmail) with a
  Settings link, instead of the useless "runs daily at 6am".
- **Precision:** `ROLE_PASS` 0.33 → 0.40 so a single shared word out of a 3-word
  role no longer qualifies ("Premium Banking" no longer matches "investment
  banking analyst"). Verified; 18 tests still green.

---

## 2026-06-22 (k) — audit fixes (résumé/seniority/guard)

Ran a deep audit of the recent résumé/seniority/finance/guard changes. Fixed the
real ones; one flagged "critical" was a false alarm (verified against the code).
- **H1 — résumé no longer corrupts target_roles.** Upload used to inject detected
  roles into `target_roles` (full-weight, sticky, append-only). Now it only saves
  `resume_text` + level; the résumé drives the feed via `effectiveRoles` /
  Python `resume_roles` (down-weighted, as designed). Detected roles shown as info.
- **H2/H3 — seniority detection hardened.** Was inflated by stray words anywhere
  ("supported the MD" → director; "12 years of company history" → senior). Now:
  title cues only from the résumé HEADER (~first 520 chars), years prefer an
  "N years of experience/in …" phrase, and when title & years disagree by >1 rung
  we trust years. Verified: Shivali → Lead; junior-who-mentions-MD → Mid.
- **C2 — read-guard phrase cap 22 → 50.** A single finance family is ~27 phrases;
  the old cap silently truncated real neighbours.
- **M1 — un-saving from the Saved view** now removes the card + decrements the count.
- **C1 (false alarm, NOT changed):** the audit claimed the TS guard hides back-office
  finance the Python matcher keeps. Checked `filter.py:277` — Python's hard filter
  gates the sector net behind `industries_set` too, so it ALSO drops back-office for
  a role-only IB target. TS and Python already agree; left as-is + added a test that
  locks the front/back-office separation.
- Tests: 18 pytest green, `tsc` clean.

---

## 2026-06-22 (j) — no-profile firehose fix

A profile with no target roles + no industries used to dump the entire ~40k-job
database (the "investment-banker shows 39k engineers" rage moment — root cause was
an empty profile, not bad matching). Now: `page.tsx` + `/api/feed` detect an empty
profile and return nothing + a `needsProfile` flag; the dashboard shows a clean
"Tell us what you're looking for — upload your résumé or add roles in Settings"
state with a CTA. The feed can never show the unfiltered firehose again.

---

## 2026-06-22 (i) — safety net: test suite + CI gate + staging discipline

The regression net that should have existed all along.
- `tests/` — pytest suite locking in every bug we fixed (investment-banker≠engineers,
  AI-engineer specificity, role neighbourhood, salary INR parsing, India-default +
  Indianapolis-not-India, null-profile no-crash, résumé-drives-search, seniority
  ranking, back-office family). 17 tests, all green. Writing them caught one stale
  test assumption (M&A tokenization).
- `.github/workflows/ci.yml` — runs `pytest` + `tsc --noEmit` on every push/PR (the
  two classes that kept breaking: matching regressions + frontend build/type errors).
- `scripts/check.sh` — one-command local pre-push gate (same checks).
- `pytest.ini` — pythonpath config so `pytest` just works from root.
- RUNBOOK: documented the branch → Vercel preview → promote staging flow + tests.

---

## 2026-06-22 (h) — seniority / rung awareness (explicit in the résumé-upload flow)

Résumé upload now detects your LEVEL, shows it, and ranks the feed to it.
- `frontend/lib/seniority.ts` `seniorityFromText` — pulls years + the highest
  title rung (Analyst→Associate→Senior→Lead/VP→Director/MD) from the résumé. On
  upload, Settings shows a "🎯 Lead / VP · ~8 yrs" chip and stores `seniority_level`
  + `experience_years`.
- `utils/role_graph.py` — `job_level(title)`, `user_level(profile)`, `level_fit()`
  (over-qualified penalised harder than a stretch). `filter.py` adds a `lvl`
  scoring component (weight 0.12) + reasons "Right seniority" / "Below your level".
- Schema: `seniority_level TEXT` (idempotent ADD COLUMN — re-run schema.sql).
- Verified on a real IB résumé (Shivali, Team Lead/8 yrs → level Lead): VP-level
  M&A role tops the feed; Analyst role pushed below VP/MD. `tsc` clean.

---

## 2026-06-22 (g) — back-office + middle-office finance role families

The 18 Workday boards added are India-GCC-heavy → mostly MIDDLE + BACK office.
But the role graph was front-office-only (IB/PE/ER), so those jobs had no role
neighbourhood to match. Added two families (Python + TS mirror):
- `finance_ops` (back office): fund accountant/accounting/administration, ops
  analyst, reconciliations, settlements, securities ops, custody, corporate
  actions, KYC/AML, transaction monitoring, regulatory/financial reporting, GL.
- `finance_risk` (middle office): market/credit/operational risk, model
  validation/risk, product control, valuation control, compliance, financial
  crime, internal audit, treasury ops.
Plus back/middle-office sector keywords + aliases (kyc, aml, recon, ops, market
risk…). Kept SEPARATE from front-office `finance_ib` (no cross edges) so a
back-office target doesn't pull IB roles and vice-versa.
Verified: "fund accountant" → fund accounting/AML/settlements (front-office IB +
engineers dropped). `tsc --noEmit` clean.

---

## 2026-06-22 (f) — finance coverage: verified finance Workday tenants

Finance is a different labour market — traditional finance (banks, finance-data,
GCC/KPO) doesn't use Greenhouse/Lever/Ashby; it's on Workday + company portals.
Added **18 research-verified finance Workday boards** to `ingest/registry.WORKDAY`,
each confirmed live with India roles: State Street (~349 India), Deutsche Bank
(~264), LSEG (~227), Wells Fargo (~221), PwC (~210), Visa, Northern Trust,
Morningstar, BlackRock, Nasdaq, S&P Global, Barclays, Synchrony, Broadridge,
Fiserv, Fidelity, Capital One, FIS. Verified end-to-end through our own connector
(State Street → 15 India roles in a 40-job sample: Middle Office VP, Compliance…).

Excluded (not on standard Workday CXS — noted for future): Moody's, MSCI, Fitch,
HSBC (Eightfold), Amex/JPM/BNY (Oracle), KPMG/EY/Deloitte (Oracle/SuccessFactors/
custom), UBS/Nomura/StanChart/Macquarie (own portals).

_Still open:_ front-office India IB/PE/equity-research (iimjobs/Naukri) — those have
no ATS API; the path is Gmail alerts (parsers exist) — document for users. Future:
pass a Workday India location facet to fetch India directly instead of filtering.

---

## 2026-06-22 (e) — résumé upload + résumé drives the search

- **Upload PDF/DOCX** (`frontend/lib/parseResume.ts`, deps `pdfjs-dist` + `mammoth`):
  parsed in-browser to text; Settings gets an upload dropzone above the textarea.
- **Résumé drives WHICH jobs appear, not just ranking:** on upload we detect roles
  in the résumé (`rolesFromText` in `roleGraph.ts` / `roles_from_text` in
  `role_graph.py`) and **add them to Target Roles** (shown as chips, removable) so
  the existing matcher + read-guard use them. Backend `filter_and_score` also
  augments expansion with résumé-derived roles at 0.9× (so a résumé-only profile
  still produces a feed). Résumé text continues to boost ranking (résumé overlap).
- Verified: a résumé with no target roles surfaces Data Scientist/ML/Analyst and
  drops finance/security; `tsc --noEmit` clean with the new deps.
- ⚠️ Heads-up: `next@14.2.3` has a flagged security advisory — worth bumping to a
  patched 14.2.x.

---

## 2026-06-22 (d) — mobile-responsive

- **Navigation:** the fixed 224px sidebar is now `hidden md:flex`. On mobile:
  a fixed top bar (logo + theme toggle + sign out) and a fixed bottom tab nav
  (4 items, icon+label). `ThemeToggle` gained a `compact` icon-only mode.
- **Layout:** every page `<main>` → `px-4 pt-20 pb-24 md:p-6` so content clears the
  mobile top bar + bottom nav; added `w-full`. Bottom nav respects
  `safe-area-inset-bottom` (notch phones).
- **Headers:** dashboard + referrals headers stack on mobile; RefreshButton is
  `w-full sm:w-60`; referral action buttons shrink their labels on small screens.
- Verified with a real `tsc --noEmit` (0 errors).

---

## 2026-06-22 (c) — real verification pass (ran the actual toolchain)

Stopped relying on brace-counts; installed deps in the sandbox and ran the real
compilers. Found + fixed 2 genuine runtime crashes.

- Ran `tsc --noEmit` over the whole frontend → 0 errors (this is the exact check
  that kept failing on Vercel; green now with the tsconfig target fix).
- Imported all 18 Python modules → clean (the 3 that failed were sandbox-missing
  libs only).
- **Filter crash bugs (fixed):** `filter_and_score` / `deduplicate_across_sources`
  threw on (a) a job with a NULL `job_title`/`company`/`location`, and (b) a
  profile whose `target_roles`/`locations`/`industries` is NULL — which is the
  real state for a freshly-signed-up user (the DB trigger inserts only
  id/email/name, leaving those columns NULL). `main.py` catches per-user errors
  and continues, so this silently gave new users an empty feed. Guarded every
  field with `or []` / `or ""`. Verified: 8 nasty-input cases, 0 crashes.

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
