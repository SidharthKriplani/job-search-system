# Ingestion engine — the data foundation

The durable replacement for the fragile HTML portal scrapers. Every source is an
**official JSON API** (an ATS or an aggregator) or **user-consented Gmail** — no
DOM scraping, no bot detection, no ToS grey zone. A site redesign cannot break it.

## Proven live

A single run (no credentials, no scraping) returned **4,309 deduped jobs**:

| Source       | What it is                              | Live count |
|--------------|------------------------------------------|-----------:|
| Greenhouse   | Public board API per company             |     ~3,995 |
| Ashby        | Public job-board API per company         |       ~977 |
| Lever        | Public postings API per company          |       ~136 |
| Aggregators  | Remotive + Arbeitnow (free, no key)      |       ~129 |
| **Total**    | after dedup                              |  **~4,309** |

## How it works

```
collect_jobs()                     # ingest/run.py — orchestrator
  ├─ greenhouse.fetch()            # iterate registry slugs → public API
  ├─ lever.fetch()
  ├─ ashby.fetch()
  └─ aggregators.fetch()           # Remotive + Arbeitnow + (optional) Adzuna
  → normalize (ingest/base.make_job)   # one schema, matches job_feed contract
  → deduplicate (ingest/dedup)         # by URL, then title+company
  → List[job dict]
```

`main.py` calls `collect_jobs()` **once per run** (the pool is global), records
per-source counts to `scraper_health`, then filters that pool **per user** with
`utils.filter.filter_and_score`. Gmail is read per user.

## Extending coverage (one line each)

Add a company to `ingest/registry.py`:

```python
GREENHOUSE = [ ("newco", "NewCo"), ... ]   # boards.greenhouse.io/newco
LEVER      = [ ("newco", "NewCo"), ... ]   # jobs.lever.co/newco
ASHBY      = [ ("newco", "NewCo"), ... ]   # jobs.ashbyhq.com/newco
```

A dead slug simply returns 0 jobs (shown in the run summary) — it never crashes.

## Adzuna (optional — adds India + salary data)

Get free keys at developer.adzuna.com, then set env vars (or GitHub/Vercel secrets):

```
ADZUNA_APP_ID, ADZUNA_APP_KEY
ADZUNA_COUNTRIES=in,gb,us           # default
ADZUNA_QUERIES=manager,analyst,...  # default
```

Unset → the connector skips cleanly.

## Run standalone

```bash
python -m ingest.run                # prints source summary + samples
python -m ingest.run --json out.json
```
