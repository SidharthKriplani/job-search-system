# Research — ATS platform expansion (2026-07-15)

Follow-up to `RESEARCH-india-coverage.md`. A cross-session scraping audit found
which ATS *platforms* the engine had no connector for, despite live India
postings on them. This doc records what was adopted, what's queued, and the
per-platform recipes.

## Adopted this session (shipped)

| Platform | Endpoint | Result |
|---|---|---|
| **Workable** | `GET apply.workable.com/api/v1/widget/accounts/{slug}?details=true` | Connector + 240 harvested live boards (2,948 candidates found; rest verify on future weekly harvests) |
| **BambooHR** | `GET {slug}.bamboohr.com/careers/list` | Connector + 309 harvested live companies. List API has no JD/posted-date (kept N+1-free) |
| **Jooble** | `POST jooble.org/api/{key}` | In `aggregators.py`, env-gated (`JOOBLE_API_KEY` — free at jooble.org/api/about) |
| **Workday (harvested)** | CXS POST per (tenant, wd, site) triple | `harvest_workday()` mined + verified 193 tenants → `data/workday_companies.json`, **gated OFF** by `WORKDAY_INCLUDE_HARVESTED` |

Smoke test (workable + bamboohr through the orchestrator): 12,472 raw →
7,464 deduped; 227 India-located today. India share grows as the harvester
accumulates India slugs — the discovery is domain-wide, not geo-targeted.

**Why the Workday gate:** `workday.SEARCH_TEXT="India"` is a loose ranker, not
a filter — a US-only tenant (e.g. cvshealth, 17k jobs) still returns rows. ~190
harvested tenants ≈ +25k mostly-non-India rows/run on a 95k pool that already
needs the `jobs` + `user_job_matches` normalization (ROADMAP NOW). Flip the flag
after that migration.

## Queued — enterprise platforms (one per session, prove-or-kill)

Order by expected India yield per engineering hour. Rule: seed 5–10
hand-verified India tenants, ship, watch `/health` for 3 runs, **kill if <500
India jobs/run**.

1. **Phenom** — dominant India enterprise career-site engine (NTT, Avantor,
   Dover). No uniform endpoint: each tenant's careers site exposes
   `POST /widgets` (`{"ddoKey":"refineSearch","country":"in",...}`). Needs a
   DevTools capture recipe per tenant, like the `registry.WORKDAY` comment.
2. **Eightfold** — `GET {tenant}.eightfold.ai/api/apply/v2/jobs?domain={domain}
   &start=0&num=100&location=India`. Clean JSON; registry tuples need
   (tenant, domain, display). Seen live: paypal.eightfold.ai.
3. **iCIMS** — `careers-{slug}.icims.com` search JSON (per-tenant quirks).
   Seen live: careers-bridgenext.icims.com.
4. **Taleo** (Oracle legacy, ≠ ORC) — `{tenant}.taleo.net/careersection/rest/
   jobboard/searchjobs` POST. Only for specific high-value tenants (uhg/Optum).
5. **SuccessFactors** — messiest JSON; unlocks FMCG/manufacturing
   (Nestlé/ITC/Unilever-type India employers). Do last.

## Rejected / deferred

- **Amazon.jobs** (`/en/search.json`) — custom ATS, huge India employer, but
  JobSpy + foundit already backfill Amazon postings. Only worth a connector for
  Amazon-complete coverage.
- **SerpApi Google-for-Jobs** — the only way to reach career sites touching no
  ATS API, but paid per search. Revisit after the free surface is exhausted.
- Consultancy custom career sites (HCLTech, Wipro, Cognizant, Accenture) —
  bespoke, no shared API; reached via JobSpy/foundit.
- One-off niche ATSes (Njoyn, Rippling ATS, TalentRecruit, PeopleHum) — too
  low-volume. Extra remote boards (RemoteOK, Himalayas) — Remotive/Arbeitnow
  cover the India-relevant slice.

## Ops notes

- Weekly harvest default targets now: greenhouse, lever, ashby, **workable,
  bamboohr**. Workday harvest is explicit: `python -m ingest.harvester workday`.
- Harvester CDX fetch now retries + salvages partial reads (the CC index drops
  chunked responses mid-stream routinely).
- New env: `WORKABLE_MAX_PER_COMPANY` (500), `BAMBOOHR_MAX_PER_COMPANY` (200),
  `JOOBLE_API_KEY`/`JOOBLE_QUERIES`/`JOOBLE_LOCATION`/`JOOBLE_PAGES`,
  `WORKDAY_INCLUDE_HARVESTED` (0).
