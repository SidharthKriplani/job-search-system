# AUDITS — audit log

Record each audit: date, scope, headline findings, and a link to the detailed
report. Newest first.

---

## 2026-06-22 — Real-toolchain verification pass
**Scope:** stopped trusting brace-counts; installed deps in the sandbox and ran the
actual compilers/imports + filter edge-cases.
**Findings:**
- `tsc --noEmit` over the whole frontend → **0 errors** (the exact check Vercel was
  failing on; green after the `tsconfig` target fix, D15).
- All 18 Python modules import cleanly (3 initial failures were sandbox-missing libs).
- **2 real crash bugs fixed:** `filter_and_score` / `deduplicate_across_sources`
  threw on NULL job fields and on NULL profile fields (`target_roles`/`industries`/
  `locations`) — the real state for new-signup rows from the DB trigger — silently
  giving new users an empty feed. Null-guarded; 8 nasty-input cases now pass clean.
**Can't verify from sandbox (need live data/secrets):** real Supabase queries/RLS,
Gmail parser on real emails, end-to-end GitHub Action (the non-fatal exit-code-1).

---

## 2026-06-21 — Deep multi-pass audit (v2)
**Scope:** three parallel deep passes — (1) frontend data-flow/auth/UX,
(2) Python pipeline (ingest/filter/main/supabase), (3) data contracts + schema +
RLS + API routes. ~60 findings triaged; Critical/High fixed this round.

**Critical (fixed):**
- **Cross-user score contamination.** `main.py` reused the shared job pool across
  users with only `list(shared_pool)` (shallow), while `filter_and_score` /
  `embeddings.rerank` mutate `match_score`/`match_reasons` in place — so one user's
  scores leaked onto the shared dicts other users were scored from. → deep-copy
  per user (`[dict(j) for j in shared_pool]`). Verified isolated.
- **Latent total-batch-loss.** `JOB_FEED_COLUMNS` whitelisted `experience_required`,
  a column that doesn't exist in `job_feed`; if ever emitted, Supabase rejects the
  whole 100-row batch silently. → removed from whitelist.

**High (fixed):**
- **Salary parser discarded every Adzuna India salary** — the `v>500` guard nuked
  absolute annual INR (e.g. "1200000-1800000"). → magnitude-aware: ≥1e5 ⇒ /1e5 LPA,
  500–99,999 ⇒ unknown, <500 ⇒ already LPA. Tested.
- **Location false positives** — substring matching made "Indianapolis" read as
  India and dropped Bangalore jobs that merely mention a foreign team. → token-based
  `_is_india()`; India/remote/preferred override the foreign-drop. Tested.
- **`delete_jobs` had no user scoping** under the service key (RLS bypassed). →
  optional `user_id` predicate, passed in resync.
- **Optimistic mutations swallowed DB errors** across applications, referrals,
  job feed — a rejected write showed success then vanished on reload. → error
  checks + rollback + alert on every mutation.
- **Dashboard stat tiles went stale** after client mutations. → `router.refresh()`
  when a job leaves the feed.
- **`job_feed` INSERT policy was `WITH CHECK (TRUE)`** — any signed-in user could
  insert rows into another user's feed. → `auth.uid() = user_id`.
- **`scraper_health` was world-readable** (leaked `last_error` traces to anon). →
  authenticated-only.

**Medium (fixed):**
- Referral message template used `.replace` (first match only) → `.replaceAll`
  (was pasting literal `{company}` into real outreach).
- Duplicate applications on double-click / two tabs → DB unique index
  `(user_id, job_feed_id)` + client double-fire guard.
- Overdue follow-up compared a possibly-timestamp string to a date → normalized.
- `match_reasons` used as React keys (collision) → keyed with index.
- Unknown stage/status rendered an unstyled badge → fallback colors.
- Schema couldn't retrofit unique constraints onto pre-existing tables → idempotent
  `DO $$` block adds them (+ de-dupes existing rows first).

**Known/Deferred — now mostly cleared (see CHANGELOG 2026-06-21 (e)):**
- ✅ Feed pagination + server-side search/source/filter (`/api/feed` + Load more).
- ✅ `_stem` collisions (override table: marketing≠marketplace, product≠production).
- ✅ Gmail dates parsed to ISO so recency works.
- ✅ Source pills derived from sources present.
- ⏳ Still open: Gmail title↔URL pairing by index (parse per-block) — needs a
  rework of the per-portal parsers; lower priority.

---

## 2026-06-20 — Full code audit (v1)
**Scope:** entire repo read; pipeline run in a sandbox; static + dynamic checks.
**Detailed report:** root [`AUDIT.md`](../AUDIT.md).

**Headline findings (all fixed):**
- Daily digest re-sent the entire feed every day (`get_seen_job_ids` defined but
  never used). → now new-only.
- Salary parser turned GCC monthly pay into bogus LPA (e.g. "AED 25000/month" →
  275 LPA), corrupting scores and the salary floor. → returns 0 (unknown) for
  monthly amounts.
- `schema.sql` not idempotent (re-run failed on existing policies) — the root of
  the "partially applied schema". → fully idempotent now.
- Signup trigger created `message_templates` but **not** a `user_profiles` row, so
  email/password users were invisible to the scraper. → combined trigger +
  backfill.
- `naukri_refresh.py` queried non-existent columns. → guarded + columns added.

**Verified false alarms (already correct):**
- Scrapers were all try/except-wrapped; field names consistent end-to-end; all 3
  Supabase server clients import `CookieOptions`; no React component-in-component.
  (The handoff's "scraper pattern" doc was wrong, not the code.)

**Not verifiable from here (needed live access):** live Supabase table state,
real GitHub Actions run, live-app screenshots, Resend domain status.

---

## How to log the next audit
Add a dated section above with: scope, method, findings (fixed vs open), and a
link to any standalone report. Keep findings one line each.
