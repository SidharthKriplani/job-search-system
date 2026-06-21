# STATUS — current state

_Last updated: 2026-06-22_

The single source of truth for where the project is **right now**. Update this
after every meaningful change.

## Phase

**Live and iterating on relevance + reliability.** The feed produces real jobs
(~5,000+ per user), the tracker and referrals work, and we've done a deep
multi-pass bug audit + a real-toolchain verification pass. Current focus: making
matching trustworthy (role graph + sectors) and India coverage.

## Capabilities built to date (the journey)

- **M1 ✅ Jobs live** — durable ingestion engine; real feeds of thousands of jobs.
- **Data foundation** — ATS-source engine (Greenhouse/Lever/Ashby/**Workday**) +
  **JobSpy** (Indeed/Naukri India) + aggregators (Remotive/Arbeitnow/**Adzuna
  India**) + user Gmail. No fragile portal scraping. Curated ATS boards ∪ our own
  **Common Crawl harvester** (`ingest/harvester.py`, weekly `harvest.yml`).
- **M2 ✅ Relevance (rebuilt)** — profile-driven filter with a curated
  **role-family graph** (`utils/role_graph.py`): a target role expands into a
  weighted neighbourhood (Data Scientist → ML/Analytics; Investment Banker →
  IB/M&A/PE/equity research), plus a **sector/domain layer** (finance, fintech,
  …) wired to the Industries field. Field-dependent: finance auto-activates the
  sector keyword net; tech rides the title graph.
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

- **India finance-role coverage is thin** — most finance postings come from global
  ATS boards; after the India-default foreign-drop, finance searches may return
  few results. Next: add India finance sources (Naukri/foundit finance, Indian
  fintech ATS). _This is the top relevance gap._
- **Daily run shows a non-fatal "exit code 1"** annotation while still writing
  jobs — likely a per-source or Resend (unverified domain) error caught in the
  loop. Need the run log to pin down.
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
