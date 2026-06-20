# SCALING — the staged playbook

How the architecture must evolve as we grow. The key insight: **two independent
axes stress different parts of the system.**

- **Breadth** (sources / boards / jobs-per-run) stresses **ingestion + storage**.
- **Depth** (number of users) stresses **matching + storage duplication**.

So "200 boards + 1000 users" and "50 boards + 200 users" hit *different* walls.
This doc maps the stages and the technique each one forces.

---

## The bottlenecks, by where they bite

| Pressure | What breaks | Symptom |
|----------|-------------|---------|
| More boards | sequential fetch time; run timeout; IP throttling | run takes too long / gets blocked |
| More jobs/run | memory; Supabase write volume; DB growth | slow upserts, storage bloat |
| More users | O(users × pool) recompute; per-user job copies | matching slow, storage explodes |
| Older data | unbounded `job_feed` | stale feed, big DB |

---

## Stages

### Stage 0 — NOW  (~70 boards · ~5 users · ~5–10k jobs/run)
Single daily run → fetch all sources sequentially → shared pool → filter per user
→ per-user copies in `job_feed`. **Works.** No real bottleneck yet; run time creeping.

### Stage 1 — ~150 boards · ~20 users  (~30–50k jobs/run)
**Wall:** run time (sequential fetch) brushes the GitHub Actions window; IP
throttling starts.
**Technique (BUILDING NOW):**
- **Concurrent fetch** — thread-pool the per-board/per-tenant fetches (pure I/O).
  Turns a ~30-min sequential crawl into ~2–3 min.
- **Sharded scheduled batches** — split the fetch units into N shards, one per
  hourly run (midnight→6am). Each run adds to the pool; feed is complete by 6am.
- Per-source caps already in place (Workday 150/co, JobSpy per-term).

### Stage 2 — ~300+ boards · ~50–100 users  (~100–200k jobs/run)
**Wall:** the **O(users × pool)** trap — every run filters the whole pool for
every user and stores a *separate copy* of each matched job per user. Storage and
recompute both explode.
**Technique (the keystone refactor):**
- **Decouple ingest from match.** Global **`jobs`** table (each job stored ONCE,
  deduped by `(source, source_job_id)`) + **`user_matches`** join
  `(user_id, job_id, score, reasons)`. Storage drops from O(users×jobs) to
  O(jobs)+O(matches).
- **Incremental matching** — only score jobs that are *new to that user*, not the
  whole pool every run. (A new job → matched to all users once; a new user →
  backfilled once.)
- **Staleness prune** — age jobs out at ~30–45 days (soft; `posted_date` too
  unreliable for a hard cut). Bounds the DB, keeps the feed fresh.

### Stage 3 — ~500+ boards / ~1000+ users  (~500k+ jobs)
**Wall:** GitHub Actions free minutes exhausted; single-Postgres write contention;
matching 1000 users (even incrementally) is heavy; one egress IP isn't enough.
**Technique:**
- **Move ingestion off GitHub Actions** to a worker + queue (Render/Railway/Fly
  cron worker, or a task queue). Matrix/parallel shards.
- **Proxy rotation / API budgets** for scrapers (JobSpy) to survive at volume.
- **Async or batched DB writes**; connection pooling.
- **Matching via the database, not Python loops** — Postgres full-text search
  (or a precomputed index) to shortlist, instead of scoring every row in Python.

### Stage 4 — real product, many thousands of users
**Wall:** match cost, freshness SLA, dedup quality, $$$.
**Technique:**
- **Embeddings + ANN index** (pgvector / dedicated) — embed each job once;
  per-user match = vector similarity (sub-linear), not keyword loops. Solves the
  synonym/typo problem too.
- **LLM only reranks/explains the top-K per user** — never the whole pool. This
  is why the two-stage design exists.
- Streaming ingestion, caching, multi-region, **source-health alerting**,
  horizontal workers.

---

## Cross-cutting techniques (each one scales up a level as we grow)

| Concern | Stage 0–1 | Stage 2–3 | Stage 4 |
|---------|-----------|-----------|---------|
| Concurrency | thread pool | matrix shards / async | distributed workers + queue |
| Sharding | registry slices per hourly run | + parallel matrix | queue-driven |
| Storage | per-user `job_feed` | **global `jobs` + `user_matches`** | + vector index |
| Matching | Python keyword/stem loops | DB FTS shortlist | embeddings/ANN + LLM rerank top-K |
| Dedup | upsert ON CONFLICT | global job key | fuzzy/near-dup detection |
| Freshness | scrape daily | staleness prune | expiry + removal detection |
| Anti-block | per-host caps | spread + proxies | proxy pools + API budgets |
| Observability | `scraper_health` table | health UI + alerts | full alerting/on-call |

---

## Guiding principle
**Don't migrate early.** Each stage's technique is *complexity* — adopt it when
the matching wall actually bites, not before. Concurrency + sharding (Stage 1)
buys a lot of runway on the current schema; the global-jobs refactor (Stage 2) is
the deliberate next milestone for when users/breadth demand it.
