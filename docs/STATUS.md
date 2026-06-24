# STATUS — current state

_Last updated: 2026-06-23_

The single source of truth for where the project is **right now**. Update this
after every meaningful change.

## ⚠️ TOP OPEN BLOCKER (read first)

**The live feed shows 0 jobs for the finance test user (Shivali) even after a
Refresh — but the matching is proven correct in the sandbox.** Everything below
("relevance works", "sources work") is verified in local tests; the gap is the
LIVE scrape pipeline, which we have never actually observed. Next action:
**read the GitHub Actions run log** ("Daily Job Scraper" → "Run job scrapers"
step) — specifically the `=== SOURCE SUMMARY ===` block and any traceback /
"exit code 1". That log distinguishes the four candidate causes:
(a) latest code not deployed to the Action (connectors absent from SOURCE SUMMARY),
(b) sources ran but returned 0, (c) jobs pulled but "upserted 0" (DB/schema),
(d) `Active users: 0` (profile row not found), or a crash. Do NOT ship more
matching changes until the log is read — the matching is not the problem.

## Phase

**Live; relevance + finance coverage are now strong in tests, but blocked on a
live-pipeline visibility gap (above).** The feed, tracker, referrals, résumé
flow, seniority, and a real test/CI gate all exist. Current focus: get eyes on
the live scrape and close the deploy/DB gap that keeps producing empty feeds.

## Capabilities built to date (the journey)

- **M1 ✅ Jobs live** — durable ingestion engine; real feeds of thousands of jobs.
- **Data foundation** — ATS-source engine: Greenhouse/Lever/Ashby + **Workday**
  (27 tenants incl. 18 finance GCCs) + **Oracle Recruiting Cloud** (EXL/JPMorgan/
  Jefferies) + **SmartRecruiters** (WNS/NielsenIQ) + **JobSpy** (Indeed/Naukri
  India) + aggregators (Remotive/Arbeitnow/**Adzuna India**) + user Gmail. No
  fragile portal scraping. Curated boards ∪ our **Common Crawl harvester**.
  **Workday + Oracle now fetch India directly** (`searchText`/`keyword=India`)
  instead of sampling global-then-discarding (D19) — Citi 0→33 India, etc.
  Connectors are per-PLATFORM, not per-company (D17), so each scales to more firms.
- **M2 ✅ Relevance (rebuilt)** — profile-driven filter with a curated
  **role-family graph** (`utils/role_graph.py`): a target role expands into a
  weighted neighbourhood (Data Scientist → ML/Analytics; Investment Banker →
  IB/M&A/PE/equity research), plus a **sector/domain layer** (finance, fintech,
  …) wired to the Industries field. Field-dependent: finance auto-activates the
  sector keyword net; tech rides the title graph. **Finance is now ONE connected
  market** — front/middle/back-office families are cross-linked (D16), so an
  IB-research profile surfaces credit research / FP&A / ops, not an empty feed.
  Mirrored Python (`role_graph.py`) ↔ TS read-guard (`roleGraph.ts`).
- **Résumé drives the search** — upload PDF/DOCX (parsed in-browser), roles +
  seniority detected and shown; résumé text drives matching via `effectiveRoles`
  (TS) / `resume_roles` (Python). Detection is suggest-not-inject (D20): it no
  longer overwrites typed target_roles. Seniority detection hardened (header-only
  title cues, experience-phrase years, prefer-years on conflict).
- **M3 ✅ Scoring** — JD-aware, weighted by neighbourhood closeness, with
  human-readable reasons ("Related role: …", "Finance sector"). Generic-word and
  stem-collision bugs fixed; salary parsing handles absolute-INR (Adzuna).
- **M4 🟡 Intelligence** — Stage 1: résumé capture + free heuristic résumé match;
  free embeddings rerank is built but **opt-in** (`USE_EMBEDDINGS`). Stage 2 (LLM
  synonym/competence) deferred.
- **M5 ✅ Application tracker** — feed "Mark Applied" creates a tracker row;
  18-stage pipeline, editable cards (notes, next action, recruiter, follow-up,
  priority), optimistic moves + rollback, delete, overdue highlights. Applied
  jobs leave the feed.
- **M5b ✅ Referrals** — LinkedIn `Connections.csv` import (compliant path):
  in-browser parse → match against feed/tracker companies → bulk-import to the
  referral pipeline.
- **Frontend** — dark mode; fast nav; **server-side feed search + source filter +
  pagination** ("Load more"); honest stat tiles; **Refresh Now** with an eased
  progress bar + coffee hint that **auto-populates the feed the moment the run
  finishes**; read-time role guard so the feed always reflects the current role.
- **Reliability** — idempotent schema with RLS + unique constraints; null-guards
  in the filter; `tsconfig` target fixed (build-error class closed); project spine
  in `docs/`.
- **✅ Test/CI safety net (NEW)** — `tests/` pytest suite (22 tests) locking in
  every fixed bug; `.github/workflows/ci.yml` runs pytest + `tsc --noEmit` on every
  push; `scripts/check.sh` local pre-push gate; staging = branch → Vercel preview →
  merge. This is the floor that stops silent regressions.
- **No-profile guard** — an empty profile shows a "set up your roles / upload
  résumé" state, never the 40k-job firehose. Résumé counts as a profile.

## At a glance

| | |
|---|---|
| **Live app** | https://job-search-system-zeta.vercel.app |
| **Repo** | https://github.com/SidharthKriplani/job-search-system (branch `main`) |
| **Repo path (local)** | `~/Documents/Professional/BreakLabs/career-os/job-search-system` _(moved 2026-06-22 from `…/GitHub/upskill platforms (4)/…`)_ |
| **Supabase** | project `dnczgcrgaczjhinrplpy` (ap-southeast-1) |
| **Hosting** | Vercel (frontend, auto-deploys on push) · GitHub Actions (daily scraper, weekly harvest, on-save resync) |

## What works (verified)

- **Ingestion engine** — live, thousands of deduped jobs from ATS + aggregators +
  Gmail, zero portal scraping.
- **Relevance** — role-graph expansion + sector layer verified with unit tests
  (Data Scientist surfaces ML/Analytics; Investment Banker surfaces finance;
  unrelated Engineers dropped; foreign jobs dropped by India-default).
- **Feed** — server-side search/filter/pagination; applied/dismissed leave the
  feed; counts honest; auto-reload on refresh completion.
- **Tracker + Referrals** — create/edit/delete with error rollback; CSV import.
- **Build/verify** — `tsc --noEmit` clean across frontend; all Python modules
  import; filter survives null/garbage input (8 edge cases, 0 crashes).

## Workflows (GitHub Actions)

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `daily.yml` | cron (hourly window) + manual / "Refresh Now" | scrape shared pool, per-user filter + upsert, resync, digest |
| `resync.yml` | on profile save (`/api/resync`) | re-filter STORED feed to current profile, no scraping (~30–60s) |
| `harvest.yml` | weekly | Common Crawl → refresh `ingest/data/*_companies.json` |

## Env / secrets checklist

GitHub Actions secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GOOGLE_CLIENT_ID`/`_SECRET`,
`RESEND_API_KEY` (sender domain unverified → digest won't send yet), `NEXT_PUBLIC_APP_URL`,
`ADZUNA_APP_ID`/`_KEY` (India + salary breadth).
Vercel env: `NEXT_PUBLIC_SUPABASE_URL`/`_ANON_KEY`, `GITHUB_DISPATCH_TOKEN` (powers Refresh + Resync).

## Known issues / open gaps

- **LIVE FEED EMPTY (top blocker)** — see the banner at the top. Matching is
  correct in tests; the live scrape isn't landing finance jobs. Blocked on reading
  the run log.
- **India finance coverage — sources now broad, but KPOs are walled.** Verified +
  added: 18 finance Workday GCCs, Oracle (EXL/JPMorgan/Jefferies), SmartRecruiters
  (WNS/NielsenIQ). The Indian IB-research KPOs Shivali most wants — **Evalueserve,
  Acuity, CRISIL** — run on **Darwinbox behind a Cloudflare captcha → NOT
  HTTP-pullable.** Moody's/EY (SuccessFactors), MSCI (iCIMS), BNP (Taleo) also not
  cleanly pullable. **Their only route is Naukri/iimjobs via consented Gmail** —
  that's the next real coverage lever (D18 thesis: don't out-aggregate Naukri).
- **Daily run "exit code 1"** annotation — still undiagnosed; part of the live
  blocker above. The run log will reveal it.
- **Gmail title↔URL pairing by index** can mismatch on messy alert emails (parser
  rework needed; lower priority).
- **Matching is keyword/stem + curated graph** — no true synonym understanding yet
  (that's the deferred LLM/embeddings Stage 2). Role graph is only as broad as the
  seeded families.
- `scraper_health` is global (per-source), not per-user.
- Legacy `scrapers/` HTML portal modules remain but are out of the pipeline.

## Things I can't verify from the sandbox (need live data/secrets)

- Real Supabase queries against real rows; RLS behaviour with multiple users.
- Gmail parser against real alert emails.
- End-to-end GitHub Action behaviour (the exit-code-1).
