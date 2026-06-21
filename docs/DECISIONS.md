# DECISIONS — why we built it this way

Lightweight decision records. Append new ones; don't rewrite old ones (if a
decision is reversed, add a new entry that supersedes it).

---

### D15 — `tsconfig` target es2017 to kill the build-error class (2026-06-22)
The frontend `tsconfig.json` had no `target` → defaulted to ES5, so the
type-checker rejected every Set/Map iteration. We patched call sites twice
(`Array.from`) before fixing the root cause: set `target: es2017` +
`downlevelIteration`. **Lesson:** fix the config, not the symptom. Verified with a
real `tsc --noEmit` run (0 errors) — brace-counting is not a build check.

### D14 — Enforce the role at feed READ time, not just at scrape time (2026-06-22)
`match_score` is computed by the async backend; the feed page reads stored rows,
so a profile change shows stale jobs until a re-filter runs. We added a read-time
guard (`frontend/lib/feedFilter.ts` + `roleGraph.ts`) that filters the feed query
itself to the role's neighbourhood/sector keywords. **Why:** correctness must not
depend on backend timing. **Precision:** distinctive SINGLE words match
title+company only; full PHRASES match title+desc+company; ambiguous words
(equity/capital/trading…) only count inside a phrase — so "Trading Systems
Engineer" can't slip into a finance feed.

### D13 — Curated role-family graph + sector layer; field-dependent (2026-06-22)
Roles are a weighted NEIGHBOURHOOD, not a point (`utils/role_graph.py`). Curated
(not LLM) because it's transparent and doubles as the seed of the competence-engine
moat. **Field-dependent:** finance auto-activates a sector keyword net (titles are
non-standard); tech does not (titles are standardised → the title graph carries it).
Sector is its own axis (Industries field) so "any finance role" works. LLM expansion
is the eventual upgrade (D9 lineage). The TS read-guard mirrors the Python graph —
kept roughly in sync by hand (acceptable: guard is a coarse net, backend is truth).

### D12 — LinkedIn connection graph: user CSV import only, no API/scraping (2026-06-21)
Deep research verdict: no worldwide compliant API exposes a member's connection
graph (DMA API is EU-only; Connections API is Partner-locked). OSS scrapers
(tomquirk/linkedin-api, StaffSpy) violate LinkedIn §8.2 and risk bans; Proxycurl was
sued shut (2025). **Decision:** the user's own `Connections.csv` export is the only
consented path. Email is opt-in (~70% blank) → match on name + company. This is
also how every legit relationship-intelligence vendor does it.

### D11 — India-default location filtering (2026-06-22)
This is an India-focused product, so the overseas-drop applies even when the user
hasn't set a location (previously it only applied with locations set, so the feed
filled with US/Mexico/London jobs). India / remote / any preferred location always
win. Heuristic foreign-hint list (full names, not 2-letter codes) to avoid nuking
Indian listings. Trade-off: surfaces India coverage scarcity honestly rather than
masking it with foreign noise.

### D10 — Own the layer; OSS only as commodity plumbing (2026-06-20)
Build the product (the automation, the competence engine, the integration fabric,
the data, the UX) **ourselves, in our own repos** — do NOT depend on third-party
GitHub agents/tools for anything that *is* the product. Each property (JSS, PAL,
MSL, GenAI) is built to readiness independently, then integrated into the Career OS
on our terms (shared identity + profile + deep links).
**Refinement (important):** "own the layer" ≠ "rewrite every library." Use OSS for
pure commodity plumbing (React, FastEmbed, an LLM runtime, raw scraping) where
reinventing adds zero moat. The OSS catalogue (`OSS-building-blocks.md`) is therefore
a *"learn-from / commodity-to-reuse / do-NOT-rebuild"* map — **not a dependency list.**
The line: own the differentiator + the automation logic; rent the plumbing.
**Sequencing:** build in parallel to readiness, but lock the integration contracts
(shared profile/identity) EARLY so the eventual integration is cheap.

### D9 — Prefix-stem matching, not stemmer lib or LLM (yet) (2026-06-20)
Tokens stem to a 5-char prefix so word-forms unify (science/scientist→"scien").
**Why:** real stemmers (Porter) don't unify science/scientist either; LLM/embeddings
do but are deferred. Prefix-stem is a cheap 80% fix. Limits: no synonyms/typos.

### D8 — Scale via concurrency + sharding now; global-jobs refactor later (2026-06-20)
Two axes stress different parts (breadth → ingestion/storage; users → matching/
duplication). **Now:** concurrent fetch + sharded hourly batches (Stage 1). **Later,
deliberately:** split per-user `job_feed` into a global `jobs` table + `user_matches`
join (Stage 2) when the O(users×pool) wall bites. **Why:** don't pay the migration
complexity before it's needed; concurrency+sharding buys runway. Full map in
`docs/SCALING.md`.

### D7 — Live run status over fire-and-forget (2026-06-20)
The refresh button polls the actual GitHub run and shows queued/running/done/
failed. **Why:** an idle "wait 2-3 min and reload" gives no confidence and no
failure diagnosis. Real status doubles as a self-service debugging tool.

### D6 — Pin the entire Supabase dependency stack (2026-06-20)
`requirements.txt` pins `httpx`, `gotrue`, `postgrest`, `storage3`, `supafunc`,
`realtime` alongside `supabase`. **Why:** `supabase==2.3.4` leaves sub-deps
unpinned, so CI can resolve an incompatible `httpx` and crash. Pinning a
verified-good combo makes builds reproducible. _Trade-off:_ versions are old;
revisit if we upgrade `supabase`.

### D5 — ATS source APIs over portal scraping (2026-06-20) ★ foundational
The data layer pulls from official ATS APIs (Greenhouse/Lever/Ashby/Workday) +
aggregator APIs (Adzuna/Remotive/Arbeitnow) + user-consented Gmail. **No HTML
scraping of job boards.** **Why:** scraping Naukri/LinkedIn/Indeed breaks within
weeks (anti-bot, shifting DOM, ToS). ATS APIs are public JSON meant to be called,
and surface jobs *before* they hit portals. This is the project's moat: a
company→ATS registry + ingestion engine that doesn't rot.

### D4 — Shared pool fetched once per run, filtered per user (2026-06-20)
`main.py` calls `collect_jobs()` once, reuses the pool for all users; only Gmail
is per-user. **Why:** ATS/aggregator data is global — pulling it per user wastes
calls and time.

### D3 — Refactor the existing repo, not a fresh one (2026-06-20)
The ingestion engine was built inside the existing app. **Why:** reuse the
working dashboard, DB schema, and auth; the value is the data layer, not a
rewrite.

### D2 — Broad coverage (any role / any geo) as the first wedge (2026-06-20)
The engine is profile-agnostic; the registry/defaults target broad coverage.
**Why:** maximises reach via aggregators + dense ATS boards. _Known tension:_
the seed registry is US-tech-heavy, so finance/India profiles match little until
the registry is expanded and Adzuna India is enabled. Revisit if the primary
user stays finance-focused.

### D1 — LinkedIn/Naukri via Gmail alerts, never scraped (2026-06-19)
These two come only through user-consented Gmail parsing. **Why:** scraping them
risks account bans, and the account *is* the user's professional identity.

### D0 — Intelligence layer is the differentiator, deferred until go-live (2026-06-20)
Per-job fit score, CTC-to-ask, tailored resume, interview prep = the real
product. **Why deferred:** worthless bolted onto a pipeline that has never run
end-to-end in production. Build it *after* the daily loop produces real jobs.
