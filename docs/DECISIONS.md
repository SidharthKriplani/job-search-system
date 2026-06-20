# DECISIONS — why we built it this way

Lightweight decision records. Append new ones; don't rewrite old ones (if a
decision is reversed, add a new entry that supersedes it).

---

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
