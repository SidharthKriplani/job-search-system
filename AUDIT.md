# Job Search System — Audit & Fix Report

_Audit date: 2026-06-20. Method: read every file in the repo, compile-checked all
Python, and ran the data pipeline (filter → score → dedup → digest) in a sandbox
with mocked I/O to confirm real (not theoretical) behavior._

---

## TL;DR

The codebase is in better shape than the handoff implies. The scrapers are all
correctly try/except-wrapped (one broken scraper cannot kill the run), field
names are **consistent** across scrapers, filter, digest, schema, and the
frontend types (the handoff's "scraper pattern" doc listing `title`/`url`/
`salary_min` is the thing that's wrong — the real code uses
`job_title`/`job_url`/`salary_range` everywhere). The frontend's two
most-feared bugs (a component defined inside a component, and missing
`CookieOptions` imports) are **not present** — they were already fixed in code.

The real bugs were in **data correctness and the SQL schema**. Those are fixed
below. The remaining items need your live credentials and are listed as a
checklist.

---

## Part A — Bugs fixed in this pass (code)

### 1. Daily digest re-sent the *entire* feed every day  ⚠️ data correctness
`main.py` set `new_jobs_for_digest = [j for j in unique if True]` — i.e. every
matched job, every day, regardless of whether the user had already seen it. The
helper `get_seen_job_ids()` existed but was never called.
**Fix:** added `get_existing_job_keys(user_id)` and wired `main.py` to diff the
scraped jobs against what's already in `job_feed` (mirroring the same
`source_job_id` fallback the upsert uses). The digest now contains only
genuinely new jobs. _Verified in sandbox: picks 1 of 2 when 1 already exists._

### 2. Salary parser inflated GCC monthly pay into bogus LPA  ⚠️ scoring
`_extract_salary_lpa("AED 25000-30000/month")` returned **275 "LPA"**, which (a)
made every GCC job falsely clear the salary floor and (b) added a false
"Salary 275L meets floor" match reason.
**Fix:** monthly/raw-currency amounts (any value > 500) now return `0.0`
("salary unknown"), so the salary filter is skipped rather than wrong.
_Verified: now returns 0.0; `"30-40 LPA"` still correctly returns 35.0._

### 3. schema.sql was not idempotent — root cause of the partial apply  ⚠️ critical
Re-running the schema failed with "policy already exists" because policies,
triggers, and indexes had no `DROP ... IF EXISTS` / `IF NOT EXISTS`. That's why
the DB ended up half-applied.
**Fix:** rewrote `supabase/schema.sql` to be fully re-runnable — every policy
and trigger is `DROP ... IF EXISTS` first, indexes use `IF NOT EXISTS`,
functions use `CREATE OR REPLACE`. **It never drops a table, so no data is
lost.** You can now paste-and-run it safely as many times as you like.

### 4. Signup created templates but NOT a profile row  ⚠️ critical
The old `on_auth_user_created` trigger inserted `message_templates` but never a
`user_profiles` row. Result: **email/password signups were invisible to the
scraper** (`get_active_users()` only reads `user_profiles`) until they manually
saved Settings.
**Fix:** new `handle_new_user()` trigger creates the profile **and** seeds
templates, idempotently. Added a one-time **backfill** that creates profile rows
for any existing `auth.users` missing one. (This also reconciles the divergent
"hotfix" trigger mentioned in the handoff.)

### 5. naukri_refresh.py crashed on missing columns
It selected `naukri_email`/`naukri_password`, which didn't exist in the schema,
so the query raised every run (masked only by `continue-on-error` in CI).
**Fix:** added the two opt-in columns to the schema (`ADD COLUMN IF NOT EXISTS`)
and wrapped the query in try/except so it degrades gracefully.

### 6. Email digest fallback URL was a placeholder
Changed the `NEXT_PUBLIC_APP_URL` code fallback from `yourapp.vercel.app` to the
real `job-search-system-zeta.vercel.app`. **Note:** the GitHub Actions *secret*
is also wrong (`job-search-system.vercel.app`, missing `-zeta`) — fix that too
(Part B #4).

---

## Part B — Needs your live credentials (I can't reach these from here)

These require your Supabase / GitHub / Vercel / Resend logins. Do them in order.

1. **Deploy the pending frontend fixes** (cursor fix + friendly errors are in
   the code but not pushed):
   ```bash
   cd "job-search-system"
   rm -f .git/index.lock
   git add -A
   git commit -m "Fix data pipeline (digest, salary), idempotent schema + profile trigger"
   git push origin main
   ```
2. **Re-run `supabase/schema.sql`** in the Supabase SQL Editor (now safe to
   re-run). Then verify all 8 tables exist:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' ORDER BY table_name;
   ```
   Expect: applications, contacts, gmail_tokens, job_feed, message_templates,
   referral_pipeline, scraper_health, user_profiles.
3. **Disable email confirmation** (Supabase → Authentication → Providers →
   Email → turn off "Confirm email"), or email/password users get stuck.
4. **Fix the `NEXT_PUBLIC_APP_URL` GitHub secret** → `https://job-search-system-zeta.vercel.app`.
5. **Verify the Resend sender domain** — `utils/email_digest.py` sends `from:
   jobs@jobsearchsystem.app` (override with `DIGEST_FROM_EMAIL`). Resend rejects
   any `from:` whose domain you haven't verified. Either verify that domain or
   set `DIGEST_FROM_EMAIL` to a verified one (e.g. `onboarding@resend.dev` for
   testing).
6. **Fill in your profile in Settings**, then **GitHub → Actions → Run
   workflow**, and read the full log. Confirm jobs land in the dashboard.
7. **Confirm a `gmail_tokens` row exists** (Supabase → Table Editor) so the
   Gmail parser has a token to use.
8. **Enable the "Refresh Now" button** — add a Vercel env var
   `GITHUB_DISPATCH_TOKEN` = a GitHub fine-grained PAT with **Actions: read &
   write** on the `job-search-system` repo. Optional overrides:
   `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`, `GITHUB_WORKFLOW_FILE` (default
   `daily.yml`), `GITHUB_DEFAULT_BRANCH` (default `main`). Without the token the
   button returns a clear "not configured" message instead of doing anything.

---

## Part A.2 — UI pass (added after the first audit)

- **Dark mode** — `darkMode: 'class'` in Tailwind, a no-flash theme bootstrap in
  `layout.tsx`, a `ThemeToggle` in the Sidebar (persists to localStorage,
  respects OS preference), and dark variants across the Dashboard, Settings,
  Applications, Referrals, Sidebar, JobCard, and modals.
- **"Refresh Now" button** on the Dashboard — triggers the scraper from the UI
  via a new authenticated route `POST /api/scrape`, which calls GitHub's
  `workflow_dispatch`. **Requires one new env var** (see Part B #8). After a
  click it auto-refreshes the feed at ~8s and ~30s.
- **Tab-switch latency** — the dashboard ran 4 Supabase queries sequentially;
  now they run in parallel via `Promise.all` (settings/referrals too). Added
  `loading.tsx` skeletons so navigation paints instantly instead of hanging on
  the server. Settings now uses `maybeSingle()` so a missing row can't throw.

## Part C — Recommended improvements (not done yet — your call)

- **`scraper_health` is global, not per-user.** It's keyed on `source` only and
  written once per user per run, so with 5 users `consecutive_failures` can
  over-count and flip a healthy scraper to "error". Low impact; fix by writing
  health once per run (aggregate) instead of per user.
- **No scraper-health UI.** The table exists and the dashboard shows a
  count-only banner; there's no page listing which sources failed and why.
- **`is_new` is never reset**, so the dashboard "New Today" stat counts every
  un-applied job ever, not today's. Consider a daily reset or a
  `seen_at`-based definition.
- **Workday coverage is thin.** Many `wd5` subdomains/paths in
  `scrapers/workday.py` are guesses and will 404 (handled safely → empty). Worth
  verifying the high-value ones (HSBC, JPMC, Goldman) against real API URLs.
- **Mobile responsiveness** — layouts are desktop-first; the sidebar doesn't
  collapse well on small screens.
- **Security:** Naukri credentials are stored as plaintext columns. If you keep
  that feature, encrypt them or use Supabase Vault; don't rely on "encrypted at
  rest" alone for a recoverable password.

---

## What I verified vs. assumed

- **Verified by running:** all Python compiles; filter/score/dedup correct;
  salary fix; new-only digest selection; digest sends gracefully with no Resend
  key; scraper failsafe pattern.
- **Verified by reading:** field-name consistency end-to-end; all 3 Supabase
  server clients import `CookieOptions`; no component-in-component; all scrapers
  wrap network calls and never raise to the runner.
- **Not verifiable here (needs your access):** live Supabase table state, the
  actual GitHub Actions run, live-app screenshots, Resend domain status. See
  Part B.
